from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
SNAPSHOT_PATH = SCRIPT_ROOT / "workspace_snapshot.py"
sys.path.insert(0, str(SCRIPT_ROOT))

import workspace_snapshot  # noqa: E402


def git(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    merged = dict(os.environ)
    merged.update(env or {})
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, env=merged,
    )


class WorkspaceSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.outside = Path(tempfile.mkdtemp()).resolve()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@local.invalid")
        git(self.root, "config", "user.name", "test")
        git(self.root, "config", "commit.gpgsign", "false")
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.root / "tracked.txt").write_text("committed\n", encoding="utf-8")
        (self.root / "staged.txt").write_text("committed\n", encoding="utf-8")
        git(self.root, "add", ".gitignore", "tracked.txt", "staged.txt")
        git(self.root, "commit", "-qm", "baseline")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def dirty(self) -> None:
        """A realistic mid-work state: worktree edit + staged edit + untracked + ignored."""
        (self.root / "tracked.txt").write_text("edited in worktree\n", encoding="utf-8")
        (self.root / "staged.txt").write_text("edited and staged\n", encoding="utf-8")
        git(self.root, "add", "staged.txt")
        (self.root / "untracked.txt").write_text("never committed\n", encoding="utf-8")
        (self.root / "ignored.txt").write_text("junk\n", encoding="utf-8")

    def index_state(self) -> tuple[str, str]:
        entries = git(self.root, "ls-files", "--stage").stdout
        tree = git(self.root, "write-tree").stdout.strip()
        return hashlib.sha256(entries.encode("utf-8")).hexdigest(), tree

    # ---- the iron rule -------------------------------------------------

    def test_snapshot_never_changes_what_is_staged(self) -> None:
        self.dirty()
        before_entries, before_tree = self.index_state()
        before_status = git(self.root, "status", "--porcelain=v1", "--untracked-files=all").stdout
        before_head = git(self.root, "rev-parse", "HEAD").stdout.strip()

        result = workspace_snapshot.create_snapshot(self.root)
        self.assertEqual(result["status"], "created")

        after_entries, after_tree = self.index_state()
        self.assertEqual(before_entries, after_entries, "Staged entries changed; the user's index was touched.")
        self.assertEqual(before_tree, after_tree, "The staged tree changed; the user's index was touched.")
        self.assertEqual(before_status, git(self.root, "status", "--porcelain=v1", "--untracked-files=all").stdout)
        self.assertEqual(before_head, git(self.root, "rev-parse", "HEAD").stdout.strip())

    def test_restore_never_changes_what_is_staged(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        before_entries, before_tree = self.index_state()
        workspace_snapshot.restore_snapshot(self.root, created["ref"], str(self.outside / "out"))
        after_entries, after_tree = self.index_state()
        self.assertEqual(before_entries, after_entries)
        self.assertEqual(before_tree, after_tree)

    # ---- what actually gets captured -----------------------------------

    def test_snapshot_captures_worktree_content_not_head_content(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        shown = git(self.root, "show", f"{created['commit']}:tracked.txt").stdout
        self.assertEqual(shown, "edited in worktree\n")

    def test_untracked_files_are_captured_and_ignored_files_are_not(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        destination = self.outside / "recovered"
        result = workspace_snapshot.restore_snapshot(self.root, created["ref"], str(destination))
        self.assertEqual((destination / "untracked.txt").read_text(encoding="utf-8"), "never committed\n")
        self.assertEqual(result["untrackedFiles"], 1)
        self.assertFalse((destination / "ignored.txt").exists(), "An ignored file was captured.")

    def test_restore_brings_back_a_file_deleted_from_the_worktree(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        (self.root / "untracked.txt").unlink()
        destination = self.outside / "rescue"
        workspace_snapshot.restore_snapshot(self.root, created["ref"], str(destination))
        self.assertEqual((destination / "untracked.txt").read_text(encoding="utf-8"), "never committed\n")

    # ---- refusals ------------------------------------------------------

    def test_skips_while_git_is_mid_operation(self) -> None:
        self.dirty()
        (self.root / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n", encoding="utf-8")
        result = workspace_snapshot.create_snapshot(self.root)
        self.assertEqual(result["status"], "skipped")
        self.assertIn("merge", result["reason"])
        self.assertEqual(workspace_snapshot.list_snapshots(self.root), [])

    def test_skips_a_clean_working_tree_instead_of_storing_an_empty_snapshot(self) -> None:
        result = workspace_snapshot.create_snapshot(self.root)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(workspace_snapshot.list_snapshots(self.root), [])

    def test_skips_a_repository_without_a_first_commit(self) -> None:
        fresh = Path(tempfile.mkdtemp()).resolve()
        git(fresh, "init", "-q")
        (fresh / "new.txt").write_text("x\n", encoding="utf-8")
        result = workspace_snapshot.create_snapshot(fresh)
        self.assertEqual(result["status"], "skipped")
        self.assertIn("first commit", result["reason"])

    def test_restore_refuses_a_non_empty_directory(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        occupied = self.outside / "occupied"
        occupied.mkdir(parents=True)
        (occupied / "mine.txt").write_text("do not clobber\n", encoding="utf-8")
        with self.assertRaises(workspace_snapshot.SnapshotError):
            workspace_snapshot.restore_snapshot(self.root, created["ref"], str(occupied))
        self.assertEqual((occupied / "mine.txt").read_text(encoding="utf-8"), "do not clobber\n")

    def test_restore_refuses_to_write_into_the_live_working_tree(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        with self.assertRaises(workspace_snapshot.SnapshotError):
            workspace_snapshot.restore_snapshot(self.root, created["ref"], str(self.root / "inside"))

    # ---- visibility and lifetime ---------------------------------------

    def test_snapshot_stays_out_of_everyday_git_output(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        commit = created["commit"]
        self.assertNotIn(commit, git(self.root, "log", "--format=%H").stdout)
        self.assertNotIn("codex-wip", git(self.root, "status").stdout)
        self.assertNotIn("codex-wip", git(self.root, "branch", "-a").stdout)
        self.assertEqual("", git(self.root, "stash", "list").stdout.strip())
        # Honest boundary: these two DO see it, and the docs say so.
        self.assertIn(commit, git(self.root, "log", "--all", "--format=%H").stdout)
        self.assertIn("codex-wip", git(self.root, "for-each-ref").stdout)

    def test_snapshot_survives_aggressive_garbage_collection(self) -> None:
        """A ref anchors the objects, so `git gc` cannot reclaim them."""
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root)
        self.assertEqual(0, git(self.root, "gc", "--prune=now", "--quiet").returncode)
        self.assertEqual("commit", git(self.root, "cat-file", "-t", created["commit"]).stdout.strip())

    def test_retention_removes_only_expired_snapshots_in_our_namespace(self) -> None:
        self.dirty()
        fresh = workspace_snapshot.create_snapshot(self.root)
        old_stamp = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S%z")
        aged = git(
            self.root, "commit-tree", f"{git(self.root, 'rev-parse', 'HEAD').stdout.strip()}^{{tree}}",
            "-m", "aged snapshot",
            env={"GIT_COMMITTER_DATE": old_stamp, "GIT_AUTHOR_DATE": old_stamp},
        ).stdout.strip()
        git(self.root, "update-ref", "refs/codex-wip/19990101T000000Z-old", aged)
        # Both of these are older than the window. Only ours may be deleted, so
        # age alone must never be enough to justify removing a ref.
        git(self.root, "update-ref", "refs/heads/ancient-branch", aged)
        git(self.root, "update-ref", "refs/tags/ancient-tag", aged)

        removed = workspace_snapshot.prune_expired(self.root, retain_days=14)

        self.assertEqual(removed, ["refs/codex-wip/19990101T000000Z-old"])
        remaining = [entry["ref"] for entry in workspace_snapshot.list_snapshots(self.root)]
        self.assertEqual(remaining, [fresh["ref"]], "Retention deleted a snapshot inside the window.")
        self.assertEqual(
            0, git(self.root, "rev-parse", "--verify", "refs/heads/ancient-branch").returncode,
            "Retention deleted an old branch that does not belong to it.",
        )
        self.assertEqual(
            0, git(self.root, "rev-parse", "--verify", "refs/tags/ancient-tag").returncode,
            "Retention deleted an old tag that does not belong to it.",
        )

    def test_retention_is_disabled_by_a_zero_window(self) -> None:
        self.dirty()
        workspace_snapshot.create_snapshot(self.root)
        old_stamp = (datetime.now(timezone.utc) - timedelta(days=900)).strftime("%Y-%m-%dT%H:%M:%S%z")
        aged = git(
            self.root, "commit-tree", f"{git(self.root, 'rev-parse', 'HEAD').stdout.strip()}^{{tree}}",
            "-m", "aged", env={"GIT_COMMITTER_DATE": old_stamp, "GIT_AUTHOR_DATE": old_stamp},
        ).stdout.strip()
        git(self.root, "update-ref", "refs/codex-wip/19990101T000000Z-old", aged)
        self.assertEqual(workspace_snapshot.prune_expired(self.root, retain_days=0), [])

    # ---- naming, oversized files, CLI ----------------------------------

    def test_reference_name_records_time_and_source(self) -> None:
        self.dirty()
        created = workspace_snapshot.create_snapshot(self.root, label="agent/session 7")
        suffix = created["ref"][len(workspace_snapshot.WIP_REF_PREFIX):]
        stamp, _, source = suffix.partition("-")
        datetime.strptime(stamp, "%Y%m%dT%H%M%SZ")
        self.assertEqual(source, "agent-session-7", "The source label must survive in the reference name.")

    def test_oversized_untracked_file_warns_and_can_be_skipped(self) -> None:
        self.dirty()
        (self.root / "big.bin").write_bytes(b"\0" * 2048)
        warned = workspace_snapshot.create_snapshot(self.root, large_bytes=1024)
        self.assertTrue(any("big.bin" in item for item in warned["warnings"]))

        (self.root / "second.txt").write_text("more work\n", encoding="utf-8")
        skipped = workspace_snapshot.create_snapshot(self.root, large_bytes=1024, skip_large=True)
        self.assertTrue(any("Skipped oversized" in item for item in skipped["warnings"]))
        destination = self.outside / "no-big"
        workspace_snapshot.restore_snapshot(self.root, skipped["ref"], str(destination))
        self.assertFalse((destination / "big.bin").exists(), "An excluded oversized file was captured anyway.")
        self.assertTrue((destination / "second.txt").exists(), "Skipping a big file dropped the small ones too.")

    def test_command_line_round_trip(self) -> None:
        self.dirty()
        taken = subprocess.run(
            [sys.executable, str(SNAPSHOT_PATH), "snapshot", "--root", str(self.root), "--label", "cli"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(taken.returncode, 0, taken.stderr)
        self.assertIn("Snapshot saved:", taken.stdout)

        listed = subprocess.run(
            [sys.executable, str(SNAPSHOT_PATH), "list", "--root", str(self.root)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertIn("codex-wip", listed.stdout)

        destination = self.outside / "cli-out"
        restored = subprocess.run(
            [sys.executable, str(SNAPSHOT_PATH), "restore", "--root", str(self.root),
             "--name", "cli", "--into", str(destination)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual((destination / "tracked.txt").read_text(encoding="utf-8"), "edited in worktree\n")

    def test_ambiguous_snapshot_name_is_refused_instead_of_guessed(self) -> None:
        self.dirty()
        first = workspace_snapshot.create_snapshot(self.root, label="same")
        # Same source, snapshotted twice: the label alone no longer identifies one.
        git(self.root, "update-ref", "refs/codex-wip/19990101T000000Z-same", first["commit"])
        with self.assertRaises(workspace_snapshot.SnapshotError) as refusal:
            workspace_snapshot.restore_snapshot(self.root, "same", str(self.outside / "ambiguous"))
        self.assertIn("matches 2 snapshots", str(refusal.exception))
        self.assertFalse((self.outside / "ambiguous").exists(), "A guess was written despite the ambiguity.")


if __name__ == "__main__":
    unittest.main()
