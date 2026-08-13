#!/usr/bin/env python3
"""Cursor `beforeShellExecution` hook: refuse a git worktree created inside the workspace.

Why this exists
---------------
Parallel-agent git worktrees created *inside* the opened workspace are watched,
indexed, and (on Cursor) re-packed into checkpoint snapshots on every file change.
Once they pile up they freeze the editor (measured: 100+ in-workspace worktrees, a
9.65 GB / 2-day checkpoint-snapshot blow-up). The kit already derives a safe path
*outside* the workspace (`feature_guard.py worktree-path` -> `../.<project>-worktrees/`),
but on Cursor nothing forces an agent to use it: the Codex `pre_tool_guard.py` speaks
the Codex/Claude hook protocol, not Cursor's, so it never runs here. This hook closes
that gap on Cursor.

Behavior
--------
It blocks ONLY `git worktree add <path>` when <path> resolves inside a watched
workspace root (or the current git repo). Everything else is allowed, so a bug here
can never brick the terminal (Cursor hooks fail-open by default; keep it that way).

Contract (Cursor docs)
----------------------
- stdin JSON carries at least `command` and `cwd`; usually `workspace_roots`.
- To block: print `{"permission":"deny","user_message":...,"agent_message":...}` and exit 0.
- To allow: exit 0 with no deny payload.
Self-contained (stdlib only) so it works in any project regardless of kit location.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

SEPARATORS = {";", "&", "&&", "|", "||"}
VALUE_FLAGS = {"-b", "-B", "--reason"}


def _segments(command: str) -> list[list[str]]:
    for sep in ("\r\n", "\r", "\n"):
        command = command.replace(sep, " ; ")
    # Windows paths use backslashes, but shlex(posix=True) treats "\" as an escape and
    # would mangle "..\\.proj-worktrees\\wt" into a bogus in-workspace-looking token.
    # This guard only compares paths, and os.path.normpath treats "/" and "\" the same
    # on Windows, so normalizing to "/" before lexing is safe and fixes the mangling.
    command = command.replace("\\", "/")
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in SEPARATORS or (token and set(token) <= {";", "&", "|"}):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _worktree_add_paths(command: str) -> list[str]:
    """Return the target path of every `git worktree add ...` found in the command."""
    paths: list[str] = []
    for segment in _segments(command):
        if not segment:
            continue
        base = os.path.basename(segment[0].strip("\"'")).lower()
        if base not in {"git", "git.exe"}:
            continue
        lowered = [token.lower() for token in segment[1:]]
        if "worktree" not in lowered:
            continue
        after = segment[1 + lowered.index("worktree") + 1 :]
        if not after or after[0].lower() != "add":
            continue
        args = after[1:]
        index = 0
        while index < len(args):
            token = args[index]
            if token == "--":
                index += 1
                continue
            if token.startswith("-"):
                index += 2 if token in VALUE_FLAGS else 1
                continue
            paths.append(token)
            break
    return paths


def _resolves_inside(target: str, roots: list[str], base: str) -> bool:
    try:
        candidate = Path(os.path.expanduser(target.strip("\"'")))
        anchor = Path(os.path.expanduser(base)) if base else Path.cwd()
        absolute = candidate if candidate.is_absolute() else anchor / candidate
        resolved = Path(os.path.normpath(str(absolute)))
    except (OSError, ValueError):
        return False
    for root in roots:
        try:
            resolved_root = Path(os.path.normpath(os.path.expanduser(root)))
        except (OSError, ValueError):
            continue
        if resolved == resolved_root or resolved_root in resolved.parents:
            return True
    return False


def _watched_roots(payload: dict) -> list[str]:
    roots: list[str] = []
    workspace_roots = payload.get("workspace_roots")
    if isinstance(workspace_roots, list):
        roots.extend(str(root) for root in workspace_roots if isinstance(root, str) and root)
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        roots.append(cwd)
        try:
            current = Path(cwd).resolve()
            for candidate in (current, *current.parents):
                if (candidate / ".git").exists():
                    roots.append(str(candidate))
                    break
        except (OSError, ValueError):
            pass
    if not roots:
        roots.append(os.getcwd())
    return roots


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    command = payload.get("command")
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    if not isinstance(command, str) or not command.strip():
        return 0

    roots = _watched_roots(payload)
    base = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
    for target in _worktree_add_paths(command):
        if _resolves_inside(target, roots, base):
            json.dump(
                {
                    "permission": "deny",
                    "user_message": (
                        "已拦截：worktree 不能建在工作区内部。工作区内的 worktree 会被 Cursor "
                        "监视/索引/检查点快照反复扫描，堆积后会拖慢甚至冻结编辑器。"
                    ),
                    "agent_message": (
                        "Blocked `git worktree add` into a path inside the opened workspace. "
                        "In-workspace worktrees are watched, indexed, and packed into checkpoint "
                        "snapshots on every change; piled up they freeze the editor. Get an "
                        "outside-the-workspace path from `python <dev-kit>/scripts/feature_guard.py "
                        "worktree-path --root . --name <label>` (it lands at "
                        "../.<project>-worktrees/<label>) and pass THAT to git worktree add. "
                        "Remove finished copies with guarded remove-worktree."
                    ),
                },
                sys.stdout,
                ensure_ascii=False,
            )
            sys.stdout.write("\n")
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
