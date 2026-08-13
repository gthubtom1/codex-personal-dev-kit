#!/usr/bin/env python3
"""Save and recover working-tree snapshots without ever touching the user's Git index.

WHAT THIS IS
    A rolling safety net for "I just lost the thing I was editing". Each snapshot
    is a real Git commit object parked under `refs/codex-wip/`, so the content is
    recoverable with ordinary Git commands, yet invisible to `git status`,
    `git log`, `git branch` and `git stash list`.

WHAT THIS IS NOT
    Not a backup. Not a formal checkpoint. Not a replacement for `feature_guard.py
    checkpoint`. It lives only inside this one local repository, so it dies with
    the disk. See "HONEST BOUNDARIES" below before relying on it.

WHY IT REFUSES TO TOUCH THE INDEX
    Staging is the user's workspace, and a background helper that stages files can
    sweep a half-finished edit into somebody else's commit. So this script never
    runs `git add` against the real index: untracked content is collected through a
    throwaway `GIT_INDEX_FILE`, and every run re-checks the staged fingerprint
    afterwards and fails loudly if it moved.

HONEST BOUNDARIES (measured on git 2.x, not assumed)
    - `git stash create` DOES rewrite `.git/index` — but only its stat cache. What
      is staged is unchanged: `git ls-files --stage` and the index tree are
      byte-identical across the call. Comparing raw index bytes is a misleading
      proxy; this script asserts the staged fingerprint instead.
    - Snapshots are anchored by a ref, so `git gc` will NOT collect them. They do
      not expire on their own. Retention is enforced by this script (default
      14 days, see --retain-days), not by Git.
    - Invisible to `git status`, `git log`, `git branch`, `git stash list`.
      Still visible to `git log --all`, `git for-each-ref` and `git fsck`.
    - `git stash create` captures tracked changes only. Untracked files are
      captured separately here; ignored files are never captured.

USAGE
    python workspace_snapshot.py snapshot [--root .] [--label <source>]
    python workspace_snapshot.py list     [--root .]
    python workspace_snapshot.py restore  --name <ref-or-suffix> --into <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence


WIP_REF_PREFIX = "refs/codex-wip/"
DEFAULT_RETAIN_DAYS = 14
LARGE_FILE_BYTES = 5 * 1024 * 1024
ADD_BATCH = 100
LABEL_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
# Any of these means Git is mid-operation. Snapshotting a half-applied rebase
# stores a state the user never had, so we skip instead.
IN_PROGRESS_MARKERS = (
    ("MERGE_HEAD", "a merge"),
    ("CHERRY_PICK_HEAD", "a cherry-pick"),
    ("REVERT_HEAD", "a revert"),
    ("BISECT_LOG", "a bisect"),
    ("rebase-merge", "a rebase"),
    ("rebase-apply", "a rebase or am"),
)


class SnapshotError(RuntimeError):
    """A refusal the caller should show to the user verbatim."""


def _run(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    merged = dict(os.environ)
    merged.update(env or {})
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=merged,
    )


def _out(result: subprocess.CompletedProcess, what: str) -> str:
    if result.returncode != 0:
        raise SnapshotError(result.stderr.strip() or result.stdout.strip() or what)
    return result.stdout.strip()


def require_repository(value: str) -> Path:
    """Resolve any Git working tree.

    Deliberately not restricted to Dev Kit managed projects: a safety net that
    refuses to run because `docs/FEATURES.md` is missing would be absent from
    exactly the scratch repositories where work is lost most often.
    """
    start = Path(value).expanduser().resolve()
    probe = start if start.is_dir() else start.parent
    result = _run(probe, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise SnapshotError(f"Not inside a Git working tree: {start}")
    return Path(result.stdout.strip()).resolve()


def _git_path(root: Path, name: str) -> Path:
    resolved = _out(_run(root, "rev-parse", "--git-path", name), f"Cannot resolve {name}.")
    candidate = Path(resolved)
    return candidate if candidate.is_absolute() else (root / candidate)


def in_progress_operation(root: Path) -> str | None:
    for marker, description in IN_PROGRESS_MARKERS:
        if _git_path(root, marker).exists():
            return description
    return None


def staged_fingerprint(root: Path) -> str:
    """Hash what is staged (mode, blob, stage, path) - not the index's stat cache."""
    listing = _run(root, "ls-files", "--stage")
    if listing.returncode != 0:
        raise SnapshotError(listing.stderr.strip() or "Unable to read the Git index.")
    return hashlib.sha256(listing.stdout.encode("utf-8")).hexdigest()


def untracked_paths(root: Path) -> list[str]:
    """Untracked but not ignored. `--exclude-standard` keeps node_modules out."""
    listing = _run(root, "ls-files", "--others", "--exclude-standard", "-z")
    if listing.returncode != 0:
        raise SnapshotError(listing.stderr.strip() or "Unable to list untracked files.")
    return [item for item in listing.stdout.split("\0") if item]


def changed_tracked_paths(root: Path) -> list[str]:
    listing = _run(root, "diff", "--name-only", "-z", "HEAD")
    if listing.returncode != 0:
        return []
    return [item for item in listing.stdout.split("\0") if item]


def oversized(root: Path, paths: Sequence[str], limit: int) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for relative in paths:
        candidate = root / relative
        try:
            size = candidate.stat().st_size
        except OSError:
            continue
        if size > limit:
            found.append((relative, size))
    return sorted(found, key=lambda item: item[1], reverse=True)


def _build_untracked_commit(root: Path, paths: Sequence[str]) -> str | None:
    """Record untracked files through a throwaway index; the real one is never opened."""
    if not paths:
        return None
    handle, temporary = tempfile.mkstemp(prefix="codex-wip-", suffix=".index")
    os.close(handle)
    # Git requires the temp index to be absent rather than empty-but-existing.
    Path(temporary).unlink(missing_ok=True)
    env = {"GIT_INDEX_FILE": temporary}
    try:
        for start in range(0, len(paths), ADD_BATCH):
            batch = paths[start:start + ADD_BATCH]
            added = _run(root, "add", "--force", "--", *batch, env=env)
            if added.returncode != 0:
                raise SnapshotError(added.stderr.strip() or "Unable to record untracked files.")
        tree = _out(_run(root, "write-tree", env=env), "Unable to write the untracked tree.")
    finally:
        Path(temporary).unlink(missing_ok=True)
    return _out(
        _run(root, "commit-tree", tree, "-m", "codex-wip untracked files"),
        "Unable to record the untracked snapshot.",
    )


def _commit_snapshot(root: Path, tree: str, parents: Sequence[str], message: str) -> str:
    args = ["commit-tree", tree]
    for parent in parents:
        args += ["-p", parent]
    args += ["-m", message]
    return _out(_run(root, *args), "Unable to create the snapshot commit.")


def prune_expired(root: Path, retain_days: int) -> list[str]:
    """Delete only this script's own refs, only when older than the retention window."""
    if retain_days <= 0:
        return []
    listing = _run(
        root, "for-each-ref", "--format=%(refname)%09%(creatordate:unix)", WIP_REF_PREFIX
    )
    if listing.returncode != 0:
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retain_days)).timestamp()
    removed: list[str] = []
    for line in listing.stdout.splitlines():
        refname, _, created = line.partition("\t")
        if not refname.startswith(WIP_REF_PREFIX):
            continue
        try:
            created_at = float(created)
        except ValueError:
            continue
        if created_at >= cutoff:
            continue
        if _run(root, "update-ref", "-d", refname).returncode == 0:
            removed.append(refname)
    return removed


def create_snapshot(
    root: Path,
    label: str | None = None,
    retain_days: int = DEFAULT_RETAIN_DAYS,
    prune: bool = True,
    skip_large: bool = False,
    large_bytes: int = LARGE_FILE_BYTES,
) -> dict:
    blocked = in_progress_operation(root)
    if blocked:
        return {"status": "skipped", "reason": f"Git is in the middle of {blocked}."}
    if _run(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode != 0:
        return {"status": "skipped", "reason": "The repository has no first commit yet."}

    before = staged_fingerprint(root)
    head = _out(_run(root, "rev-parse", "HEAD"), "Unable to read HEAD.")

    untracked = untracked_paths(root)
    warnings: list[str] = []
    skipped_large: list[str] = []
    for relative, size in oversized(root, [*untracked, *changed_tracked_paths(root)], large_bytes):
        megabytes = size / (1024 * 1024)
        if skip_large and relative in untracked:
            skipped_large.append(relative)
            warnings.append(f"Skipped oversized untracked file ({megabytes:.1f} MB): {relative}")
        else:
            warnings.append(f"Large file captured ({megabytes:.1f} MB): {relative}")
    if skipped_large:
        untracked = [item for item in untracked if item not in set(skipped_large)]

    stash = _run(root, "stash", "create", "codex-wip")
    if stash.returncode != 0:
        raise SnapshotError(stash.stderr.strip() or "Unable to capture the working tree.")
    stash_commit = stash.stdout.strip()

    if not stash_commit and not untracked:
        return {"status": "skipped", "reason": "The working tree has no changes to capture."}

    if stash_commit:
        tree = _out(_run(root, "rev-parse", f"{stash_commit}^{{tree}}"), "Unable to read the snapshot tree.")
        index_commit = _run(root, "rev-parse", f"{stash_commit}^2")
        parents = [head] + ([index_commit.stdout.strip()] if index_commit.returncode == 0 else [])
    else:
        # Only untracked work exists; the tracked tree still matches HEAD.
        tree = _out(_run(root, "rev-parse", f"{head}^{{tree}}"), "Unable to read the HEAD tree.")
        parents = [head]

    untracked_commit = _build_untracked_commit(root, untracked)
    if untracked_commit:
        parents.append(untracked_commit)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source = LABEL_SAFE.sub("-", (label or os.environ.get("CODEX_WIP_LABEL") or "manual")).strip("-")
    refname = f"{WIP_REF_PREFIX}{stamp}-{source or 'manual'}"
    branch = _run(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip() or "(detached)"
    message = (
        f"codex-wip {stamp} from {source or 'manual'}\n\n"
        f"branch: {branch}\nhead: {head[:12]}\n"
        f"untracked files: {len(untracked)}\n"
        "Recover with: workspace_snapshot.py restore --name <ref> --into <dir>\n"
    )
    commit = _commit_snapshot(root, tree, parents, message)

    created = _run(root, "update-ref", refname, commit)
    if created.returncode != 0:
        raise SnapshotError(created.stderr.strip() or "Unable to park the snapshot reference.")

    after = staged_fingerprint(root)
    if before != after:
        # Never observed; kept as an executable statement of the iron rule.
        _run(root, "update-ref", "-d", refname)
        raise SnapshotError(
            "Aborted: the Git index changed while taking the snapshot. "
            "The snapshot was discarded so it cannot be blamed for the staged state."
        )

    return {
        "status": "created",
        "ref": refname,
        "commit": commit,
        "branch": branch,
        "untrackedCount": len(untracked),
        "warnings": warnings,
        "pruned": prune_expired(root, retain_days) if prune else [],
    }


def list_snapshots(root: Path) -> list[dict]:
    listing = _run(
        root,
        "for-each-ref",
        "--sort=-creatordate",
        "--format=%(refname)%09%(objectname)%09%(creatordate:iso-strict)%09%(contents:subject)",
        WIP_REF_PREFIX,
    )
    if listing.returncode != 0:
        raise SnapshotError(listing.stderr.strip() or "Unable to list snapshots.")
    entries: list[dict] = []
    for line in listing.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        entries.append({"ref": parts[0], "commit": parts[1], "created": parts[2], "subject": parts[3]})
    return entries


def resolve_snapshot_ref(root: Path, name: str) -> str:
    candidates = [entry["ref"] for entry in list_snapshots(root)]
    if name in candidates:
        return name
    prefixed = name if name.startswith(WIP_REF_PREFIX) else WIP_REF_PREFIX + name
    if prefixed in candidates:
        return prefixed
    matches = [ref for ref in candidates if ref.endswith(name)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SnapshotError(f"No snapshot matches {name!r}. List snapshots to see the exact names.")
    raise SnapshotError(f"{name!r} matches {len(matches)} snapshots; use the full reference name.")


def _extract_tree(root: Path, tree: str, destination: Path) -> int:
    """Materialize a tree through a throwaway index; the real index is never opened."""
    destination.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix="codex-wip-restore-", suffix=".index")
    os.close(handle)
    Path(temporary).unlink(missing_ok=True)
    env = {"GIT_INDEX_FILE": temporary}
    try:
        _out(_run(root, "read-tree", tree, env=env), "Unable to load the snapshot tree.")
        prefix = destination.as_posix().rstrip("/") + "/"
        _out(
            _run(root, "checkout-index", "--all", "--force", f"--prefix={prefix}", env=env),
            "Unable to write the snapshot files.",
        )
        listing = _run(root, "ls-files", "--stage", env=env)
        return len([line for line in listing.stdout.splitlines() if line.strip()])
    finally:
        Path(temporary).unlink(missing_ok=True)


def restore_snapshot(root: Path, name: str, into: str) -> dict:
    """Write a snapshot's content into a directory. Never into the live working tree."""
    refname = resolve_snapshot_ref(root, name)
    destination = Path(into).expanduser().resolve()
    if destination == root or root in destination.parents:
        raise SnapshotError(
            "Refusing to restore inside the working tree. Choose a directory outside it, "
            "then copy back only the files you actually want."
        )
    if destination.exists() and any(destination.iterdir()):
        raise SnapshotError(f"Refusing to overwrite a non-empty directory: {destination}")

    before = staged_fingerprint(root)
    commit = _out(_run(root, "rev-parse", refname), "Unable to resolve the snapshot.")
    tracked = _extract_tree(root, f"{commit}^{{tree}}", destination)

    untracked_count = 0
    parents = _out(_run(root, "rev-list", "--parents", "-n", "1", commit), "Unable to read parents").split()
    if len(parents) >= 4:
        untracked_count = _extract_tree(root, f"{parents[3]}^{{tree}}", destination)

    after = staged_fingerprint(root)
    if before != after:
        raise SnapshotError("Aborted: the Git index changed during restore.")
    return {
        "ref": refname,
        "commit": commit,
        "destination": str(destination),
        "trackedFiles": tracked,
        "untrackedFiles": untracked_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Park the current working tree as a recoverable snapshot")
    snapshot.add_argument("--root", default=".")
    snapshot.add_argument("--label", help="Where this snapshot came from; recorded in the reference name")
    snapshot.add_argument("--retain-days", type=int, default=DEFAULT_RETAIN_DAYS)
    snapshot.add_argument("--no-prune", action="store_true", help="Keep expired snapshots this run")
    snapshot.add_argument("--skip-large", action="store_true", help="Leave oversized untracked files out")
    snapshot.add_argument("--large-mb", type=float, default=LARGE_FILE_BYTES / (1024 * 1024))

    listing = subparsers.add_parser("list", help="Show recoverable snapshots, newest first")
    listing.add_argument("--root", default=".")

    restore = subparsers.add_parser("restore", help="Write one snapshot into an empty directory")
    restore.add_argument("--root", default=".")
    restore.add_argument("--name", required=True)
    restore.add_argument("--into", required=True)

    args = parser.parse_args()
    try:
        root = require_repository(args.root)
        if args.command == "snapshot":
            result = create_snapshot(
                root,
                label=args.label,
                retain_days=args.retain_days,
                prune=not args.no_prune,
                skip_large=args.skip_large,
                large_bytes=int(args.large_mb * 1024 * 1024),
            )
            for warning in result.get("warnings", []):
                print(f"WARNING: {warning}")
            if result["status"] == "skipped":
                print(f"No snapshot taken: {result['reason']}")
            else:
                print(f"Snapshot saved: {result['ref']} -> {result['commit'][:12]}")
                print(f"Recover with: workspace_snapshot.py restore --name {result['ref']} --into <empty-dir>")
            for pruned in result.get("pruned", []):
                print(f"Removed expired snapshot: {pruned}")
        elif args.command == "list":
            entries = list_snapshots(root)
            if not entries:
                print("No snapshots.")
            for entry in entries:
                print(f"{entry['created']}\t{entry['commit'][:12]}\t{entry['ref']}")
        elif args.command == "restore":
            result = restore_snapshot(root, args.name, args.into)
            print(f"Restored {result['ref']} into {result['destination']}")
            print(f"Tracked files: {result['trackedFiles']}; untracked files: {result['untrackedFiles']}")
            print("Nothing in your working tree or Git index was changed.")
    except SnapshotError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
