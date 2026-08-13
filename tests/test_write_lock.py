"""One checkout, one writer: the write lock must be a machine gate, not advice."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
FEATURE_GUARD_PATH = SCRIPT_ROOT / "feature_guard.py"
sys.path.insert(0, str(SCRIPT_ROOT))

import feature_guard  # noqa: E402


FEATURES = """# Feature Map

## Feature Inventory

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Toggle acceleration | Settings control -> save API -> worker | The saved setting controls processing. | test:tests/verify_features.py | critical | active |
"""


class WriteLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".codex").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        (self.root / "AGENTS.md").write_text("# Test project\n", encoding="utf-8")
        (self.root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
        (self.root / ".gitignore").write_text(".codex/current-change.json\n.codex/write-lock.json\n", encoding="utf-8")
        (self.root / "docs/FEATURES.md").write_text(FEATURES, encoding="utf-8")
        (self.root / "docs/STATUS.md").write_text("# Current Status\n\n## Next Action\n\nNothing.\n", encoding="utf-8")
        (self.root / "src/app.js").write_text("export const acceleration = true;\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests/verify_features.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def guard(self, *args: str, session: str) -> subprocess.CompletedProcess:
        """Run the guard CLI as a named writing session."""
        environment = dict(os.environ)
        environment["CODEX_WRITE_LOCK_SESSION"] = session
        return subprocess.run(
            [sys.executable, str(FEATURE_GUARD_PATH), *args, "--root", str(self.root)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )

    def start(self, session: str, objective: str = "Add a setting") -> subprocess.CompletedProcess:
        return self.guard("start", "--objective", objective, "--change", "F-002", session=session)

    def lock_file(self) -> Path:
        return self.root / feature_guard.WRITE_LOCK_RELATIVE

    def read_lock(self) -> dict:
        return json.loads(self.lock_file().read_text(encoding="utf-8"))

    def write_lock(self, lock: dict) -> None:
        self.lock_file().parent.mkdir(parents=True, exist_ok=True)
        self.lock_file().write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def dead_pid() -> int:
        finished = subprocess.Popen([sys.executable, "-c", "pass"])
        finished.wait()
        return finished.pid

    # --- the gate itself -------------------------------------------------

    def test_a_second_session_is_refused_and_told_who_holds_the_lock(self) -> None:
        first = self.start("session-a")
        self.assertEqual(first.returncode, 0, first.stderr)

        second = self.start("session-b", objective="Edit the same checkout")
        self.assertEqual(second.returncode, 1, "a second writer must be a hard failure, not a warning")
        self.assertNotIn("WARNING", second.stdout.upper())
        self.assertIn("another writer already holds the write lock", second.stderr)
        self.assertIn("label:session-a", second.stderr)
        self.assertIn("held:", second.stderr)
        self.assertIn("Add a setting", second.stderr)

    def test_the_refusal_keeps_the_first_sessions_contract_intact(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        before = (self.root / feature_guard.CONTRACT_RELATIVE).read_text(encoding="utf-8")
        self.assertEqual(self.start("session-b", objective="Steal the checkout").returncode, 1)
        after = (self.root / feature_guard.CONTRACT_RELATIVE).read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(self.read_lock()["holder"]["writer"], "label:session-a")

    def test_a_second_session_cannot_stage_or_cancel_the_first_sessions_change(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        (self.root / "src/app.js").write_text("export const acceleration = false;\n", encoding="utf-8")

        staged = self.guard("stage", "--path", "src/app.js", session="session-b")
        self.assertEqual(staged.returncode, 1)
        self.assertIn("another writer already holds the write lock", staged.stderr)

        cancelled = self.guard("cancel", session="session-b")
        self.assertEqual(cancelled.returncode, 1)
        self.assertIn("another writer already holds the write lock", cancelled.stderr)

    def test_the_owning_session_keeps_working_without_friction(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        (self.root / "src/app.js").write_text("export const acceleration = false;\n", encoding="utf-8")
        staged = self.guard("stage", "--path", "src/app.js", session="session-a")
        self.assertEqual(staged.returncode, 0, staged.stderr)

    def test_read_only_commands_never_touch_the_lock(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        for command in (["status"], ["versions"], ["lock-status"]):
            result = self.guard(*command, session="session-b")
            self.assertEqual(result.returncode, 0, f"{command} must not require the write lock: {result.stderr}")
        self.assertEqual(self.read_lock()["holder"]["writer"], "label:session-a")

    def test_lock_status_reports_the_holder_and_how_long(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        result = self.guard("lock-status", session="session-b")
        self.assertIn("label:session-a", result.stdout)
        self.assertIn("held:", result.stdout)

    # --- deadlock recovery ------------------------------------------------

    def test_a_lock_whose_process_is_gone_is_reclaimed_automatically(self) -> None:
        """A crashed writer must never lock the checkout forever."""
        self.assertEqual(self.start("session-a").returncode, 0)
        lock = self.read_lock()
        lock["holder"]["writer"] = "process:crashed"
        lock["holder"]["pid"] = self.dead_pid()
        lock["holder"]["pidStartedAt"] = None
        lock["holder"]["host"] = feature_guard.socket.gethostname()
        self.write_lock(lock)

        recovered = self.guard("cancel", session="session-b")
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        second = self.start("session-b", objective="Take over after the crash")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.read_lock()["holder"]["writer"], "label:session-b")

    def test_a_lock_nobody_renewed_expires_after_the_age_limit(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        lock = self.read_lock()
        stale = int(time.time()) - feature_guard.WRITE_LOCK_MAX_AGE_SECONDS - 60
        lock["acquiredEpoch"] = stale
        lock["renewedEpoch"] = stale
        self.write_lock(lock)

        self.assertEqual(self.guard("cancel", session="session-b").returncode, 0)
        self.assertEqual(self.start("session-b", objective="Take over a stale lock").returncode, 0)

    def test_a_fresh_lock_is_not_treated_as_stale(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        lock = self.read_lock()
        lock["renewedEpoch"] = int(time.time()) - (feature_guard.WRITE_LOCK_MAX_AGE_SECONDS // 2)
        self.write_lock(lock)
        self.assertEqual(self.start("session-b", objective="Too eager").returncode, 1)

    def test_a_corrupt_lock_file_does_not_wedge_the_checkout(self) -> None:
        self.lock_file().write_text("not json at all", encoding="utf-8")
        result = self.start("session-a")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_releasing_the_change_frees_the_checkout(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        self.assertEqual(self.guard("cancel", session="session-a").returncode, 0)
        self.assertFalse(self.lock_file().exists())
        self.assertEqual(self.start("session-b", objective="Next task").returncode, 0)

    def test_a_start_that_fails_does_not_leave_the_checkout_locked(self) -> None:
        rejected = self.guard("start", "--objective", "Bad", "--verify", "F-404", session="session-a")
        self.assertEqual(rejected.returncode, 1)
        self.assertFalse(self.lock_file().exists(), "a failed start must not strand the lock")
        self.assertEqual(self.start("session-b").returncode, 0)

    # --- force-unlock is deliberate, never reflexive ----------------------

    def test_force_unlock_must_name_the_current_holder(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        result = self.guard("force-unlock", "--confirm-holder", "999999", session="session-b")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must name the current holder", result.stderr)
        self.assertTrue(self.lock_file().exists())

    def test_force_unlock_refuses_while_that_writer_is_still_running(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        holder_pid = str(self.read_lock()["holder"]["pid"])
        result = self.guard("force-unlock", "--confirm-holder", holder_pid, session="session-b")
        self.assertEqual(result.returncode, 1)
        self.assertIn("still running", result.stderr)
        self.assertTrue(self.lock_file().exists())

    def test_force_unlock_breaks_a_lock_whose_writer_is_gone(self) -> None:
        self.assertEqual(self.start("session-a").returncode, 0)
        lock = self.read_lock()
        gone = self.dead_pid()
        lock["holder"]["writer"] = "process:gone"
        lock["holder"]["pid"] = gone
        lock["holder"]["host"] = feature_guard.socket.gethostname()
        self.write_lock(lock)
        result = self.guard("force-unlock", "--confirm-holder", str(gone), session="session-b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.lock_file().exists())

    # --- the liveness probe must not be destructive -----------------------

    def test_probing_a_live_process_reports_it_and_leaves_it_running(self) -> None:
        """os.kill(pid, 0) is not a probe on Windows: CPython routes it to TerminateProcess.

        This test fails loudly if the liveness check is ever "simplified" back
        into something that kills the process it is asking about.
        """
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            self.assertIs(feature_guard._process_is_running(child.pid), True)
            time.sleep(0.3)
            self.assertIsNone(child.poll(), "the liveness probe killed the process it was asked about")
            self.assertIs(feature_guard._process_is_running(child.pid), True)
            self.assertIsNone(child.poll(), "the liveness probe killed the process it was asked about")
        finally:
            child.kill()
            child.wait()

    def test_the_windows_probe_can_never_reach_os_kill(self) -> None:
        """A source-level pin, because os.kill is shorter and looks harmless.

        On Windows CPython sends every signal except CTRL_C_EVENT/CTRL_BREAK_EVENT
        to TerminateProcess, so os.kill(pid, 0) kills the process it claims to
        merely ask about. The runtime test above catches this only if the probe is
        actually exercised; this one fails the moment the code is written.
        """
        tree = ast.parse(FEATURE_GUARD_PATH.read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

        def os_kill_lines(name: str) -> list[int]:
            return [
                node.lineno
                for node in ast.walk(functions[name])
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "kill"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ]

        self.assertEqual(
            os_kill_lines("_windows_process_is_running"),
            [],
            "the Windows liveness probe must never call os.kill; it terminates the process",
        )

        kills = os_kill_lines("_process_is_running")
        self.assertTrue(kills, "the POSIX branch is expected to probe with os.kill")
        platform_checks = [
            node.lineno
            for node in ast.walk(functions["_process_is_running"])
            if isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and node.left.attr == "name"
            and any(isinstance(value, ast.Constant) and value.value == "nt" for value in node.comparators)
        ]
        self.assertTrue(platform_checks, "_process_is_running must branch on os.name before probing")
        self.assertLess(
            min(platform_checks),
            min(kills),
            "os.kill must stay unreachable on Windows: the platform check has to come first",
        )

    def test_probing_an_exited_process_reports_it_as_gone(self) -> None:
        self.assertIs(feature_guard._process_is_running(self.dead_pid()), False)

    def test_probing_a_nonsense_pid_is_never_an_exception(self) -> None:
        for value in (0, -1, None, "abc", True):
            self.assertIn(feature_guard._process_is_running(value), (False, None))

    # --- identity ---------------------------------------------------------

    def test_the_holder_is_the_session_not_the_short_lived_guard_process(self) -> None:
        """Every guard command is its own process; a pid holder would self-reclaim instantly."""
        self.assertEqual(self.start("session-a").returncode, 0)
        first = self.read_lock()["holder"]["writer"]
        self.assertEqual(self.guard("status", session="session-a").returncode, 0)
        (self.root / "src/app.js").write_text("export const acceleration = false;\n", encoding="utf-8")
        self.assertEqual(self.guard("stage", "--path", "src/app.js", session="session-a").returncode, 0)
        self.assertEqual(self.read_lock()["holder"]["writer"], first)
        self.assertNotIn(str(os.getpid()), first)

    def test_the_lock_stays_invisible_in_projects_that_never_added_the_ignore_line(self) -> None:
        """Every project that predates this change lacks the ignore line, and the guard
        must still not mistake its own lock file for unsaved user work."""
        (self.root / ".gitignore").write_text(".codex/current-change.json\n", encoding="utf-8")
        self.git("add", ".gitignore")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "older ignore file")

        self.assertEqual(self.start("session-a").returncode, 0)
        self.assertTrue(self.lock_file().exists())
        self.assertIn(".codex/write-lock.json", self.git("status", "--porcelain").stdout)

        relative = feature_guard.WRITE_LOCK_RELATIVE.as_posix()
        self.assertNotIn(relative, feature_guard._changed_files(self.root, None))
        self.assertNotIn(relative, feature_guard._staged_files(self.root))
        self.assertNotIn(relative, feature_guard._deleted_files(self.root, None))
        self.assertEqual([line for line in feature_guard._working_tree_status(self.root) if relative in line], [])

        (self.root / "src/app.js").write_text("export const acceleration = false;\n", encoding="utf-8")
        staged = self.guard("stage", "--path", "src/app.js", session="session-a")
        self.assertEqual(staged.returncode, 0, staged.stderr)

    def test_the_lock_content_does_not_move_the_project_fingerprint(self) -> None:
        before = feature_guard._content_fingerprint(self.root)
        feature_guard.acquire_write_lock(self.root, "hold the checkout")
        self.assertTrue(self.lock_file().exists())
        self.assertEqual(feature_guard._content_fingerprint(self.root), before)
        self.assertEqual(feature_guard._worktree_fingerprint(self.root), feature_guard._worktree_fingerprint(self.root))

    def test_the_lock_is_per_checkout(self) -> None:
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        self.assertEqual(self.start("session-a").returncode, 0)
        # A different checkout has its own lock file and is unaffected.
        self.assertFalse((Path(other.name) / feature_guard.WRITE_LOCK_RELATIVE).exists())
        feature_guard.acquire_write_lock(Path(other.name), "parallel worktree")
        self.assertTrue((Path(other.name) / feature_guard.WRITE_LOCK_RELATIVE).exists())
        self.assertEqual(self.read_lock()["holder"]["writer"], "label:session-a")


if __name__ == "__main__":
    unittest.main()
