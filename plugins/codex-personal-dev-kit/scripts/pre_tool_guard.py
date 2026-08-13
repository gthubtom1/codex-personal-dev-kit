#!/usr/bin/env python3
"""Project-local Codex PreToolUse guard for commands that must never run automatically."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Decision:
    blocked: bool
    reason: str = ""


SEPARATORS = {";", "&", "&&", "|", "||"}
SHELL_WRAPPERS = {"bash", "sh", "zsh", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe"}
PRIVILEGE_WRAPPERS = {"sudo", "doas"}
WORKTREE_ADD_VALUE_FLAGS = {"-b", "-B", "--reason"}


def _basename(token: str) -> str:
    return os.path.basename(token.strip('"\'')).lower()


def _lex(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except (TypeError, ValueError):
        return command.split()


def _segments(tokens: Sequence[str]) -> Iterable[list[str]]:
    current: list[str] = []
    for token in tokens:
        if token in SEPARATORS or (token and set(token) <= {";", "&", "|"}):
            if current:
                yield current
                current = []
            continue
        current.append(token)
    if current:
        yield current


def _strip_prefixes(tokens: Sequence[str]) -> list[str]:
    result = list(tokens)
    while result and (result[0] in {"&", "command"} or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*", result[0])):
        result.pop(0)
    while result and _basename(result[0]) in PRIVILEGE_WRAPPERS:
        result.pop(0)
    if result and _basename(result[0]) == "env":
        result.pop(0)
        while result and (result[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*", result[0])):
            result.pop(0)
    return result


def _nested_shell_script(tokens: Sequence[str]) -> str | None:
    if not tokens or _basename(tokens[0]) not in SHELL_WRAPPERS:
        return None
    lowered = [token.lower() for token in tokens]
    for flag in ("-c", "-lc", "/c", "-command", "--command"):
        if flag in lowered:
            index = lowered.index(flag)
            if index + 1 < len(tokens):
                return " ".join(tokens[index + 1 :])
    return None


def _git_subcommand(tokens: Sequence[str]) -> tuple[str | None, list[str]]:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        lower = token.lower()
        if lower in {"-c", "-C".lower(), "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if lower.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            index += 1
            continue
        if lower in {"--no-pager", "--paginate", "--bare", "--literal-pathspecs", "--no-optional-locks"}:
            index += 1
            continue
        if lower.startswith("-"):
            index += 1
            continue
        return lower, list(tokens[index + 1 :])
    return None, []


def _worktree_add_target(args: Sequence[str]) -> str | None:
    index = 1
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            continue
        if token.startswith("-"):
            index += 2 if token in WORKTREE_ADD_VALUE_FLAGS else 1
            continue
        return token
    return None


def _project_root() -> Path:
    """Locate the opened project at runtime instead of assuming any machine-specific layout."""

    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def _resolves_inside_project(target: str) -> bool:
    try:
        candidate = Path(os.path.expanduser(target.strip("\"'")))
        absolute = candidate if candidate.is_absolute() else Path.cwd() / candidate
        resolved = Path(os.path.normpath(str(absolute)))
        root = _project_root()
    except (OSError, ValueError):
        return False
    return resolved == root or root in resolved.parents


def _classify_git(tokens: Sequence[str]) -> Decision:
    subcommand, args = _git_subcommand(tokens)
    lowered_args = [arg.lower() for arg in args]
    if subcommand == "tag":
        mutating_flags = {
            "-a", "--annotate", "-s", "--sign", "-u", "--local-user", "-f", "--force",
            "-d", "--delete", "-m", "--message", "-f", "--file", "--cleanup", "--create-reflog",
        }
        read_only_mode = not args or any(
            arg in {"-l", "--list", "-v", "--verify", "--column", "--no-column", "--ignore-case"}
            or arg.startswith(("-n", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--sort=", "--format=", "--column="))
            for arg in lowered_args
        )
        mutating = any(arg in mutating_flags or any(arg.startswith(flag + "=") for flag in mutating_flags if flag.startswith("--")) for arg in lowered_args)
        if read_only_mode and not mutating:
            return Decision(False, "")
        return Decision(True, "Blocked raw git tag mutation. Formal local versions must use feature_guard.py version so the tag matches a verified checkpoint and docs/VERSIONS.md.")
    if subcommand in {"push", "pull", "merge", "rebase", "clean", "restore", "filter-branch", "filter-repo"}:
        if subcommand == "push":
            return Decision(True, "Blocked raw git push. After explicit user authorization, use feature_guard.py publish with the exact remote URL, branch, and formal tags.")
        if subcommand == "pull":
            return Decision(True, "Blocked raw git pull. After explicit authorization, use feature_guard.py sync for an exact remote/current-branch fetch and fast-forward-only update.")
        if subcommand in {"merge", "rebase"}:
            return Decision(True, "Blocked raw branch integration. Use feature_guard.py integrate for a clean linear fast-forward; divergent histories require a separately scoped conflict-resolution task.")
        if subcommand == "restore":
            return Decision(True, "Blocked raw git restore. Use feature_guard.py unstage for exact guard-staged paths, rollback/restore-version for committed recovery, or a separately protected content edit.")
        return Decision(True, f"Blocked raw git {subcommand}. This operation needs an explicit, tested guarded workflow; do not hand the raw Git command to a beginner.")
    if subcommand == "reset" and any(arg in {"--hard", "--merge", "--keep"} for arg in lowered_args):
        return Decision(True, "Blocked destructive git reset. Use a new branch or reversible commit instead.")
    if subcommand == "commit" and "--amend" in lowered_args:
        return Decision(True, "Blocked git commit --amend because it rewrites history. Create a new checkpoint commit.")
    if subcommand == "branch" and ("-D" in args or ("--delete" in lowered_args and "--force" in lowered_args)):
        return Decision(True, "Blocked forced branch deletion. Preserve the recovery point for user review.")
    if subcommand == "checkout" and ("--" in args or any(arg in {"-f", "--force"} for arg in lowered_args)):
        return Decision(True, "Blocked checkout that can discard working-tree changes.")
    if subcommand == "switch" and ("-C" in args or any(arg in {"--discard-changes"} for arg in lowered_args)):
        return Decision(True, "Blocked forced branch switch that can discard or replace work.")
    if subcommand == "stash" and lowered_args and lowered_args[0] in {"drop", "clear"}:
        return Decision(True, "Blocked deletion of Git stash recovery data.")
    if subcommand == "worktree" and lowered_args and lowered_args[0] in {"remove", "prune"}:
        return Decision(True, "Blocked raw Worktree removal. Use feature_guard.py remove-worktree; it requires an exact registered path, no modified/untracked/ignored files, and no unique commits.")
    if subcommand == "worktree" and lowered_args and lowered_args[0] == "add":
        target = _worktree_add_target(args)
        if target and _resolves_inside_project(target):
            return Decision(True, "Blocked a new parallel work copy inside the opened project. Ignore rules hide such a copy from the assistant that still has to read and write it. Take the path from feature_guard.py worktree-path --root . --name <label>, which derives a directory beside the project, and pass that to git worktree add.")
    if subcommand == "reflog" and lowered_args and lowered_args[0] in {"delete", "expire"}:
        return Decision(True, "Blocked deletion of Git reflog recovery history.")
    if subcommand == "gc" and any(arg.startswith("--prune") for arg in lowered_args):
        return Decision(True, "Blocked aggressive Git pruning that can remove recovery objects.")
    return Decision(False)


def _matches(tokens: Sequence[str], prefix: Sequence[str]) -> bool:
    lowered = [_basename(tokens[0])] + [token.lower() for token in tokens[1:]] if tokens else []
    return len(lowered) >= len(prefix) and lowered[: len(prefix)] == list(prefix)


def _classify_external(tokens: Sequence[str]) -> Decision:
    if not tokens:
        return Decision(False)
    base = _basename(tokens[0])
    args = [token.lower() for token in tokens[1:]]
    executable = tokens[0].strip('"\'').replace("\\", "/").lower()

    if base in {"npx", "bunx"} and args:
        return _classify_tokens(tokens[1:])
    if base == "pnpm" and args[:1] in (["exec"], ["dlx"]):
        return _classify_tokens(tokens[2:])
    if base == "yarn" and args[:1] == ["dlx"]:
        return _classify_tokens(tokens[2:])
    if base in {"python", "python3", "py"} and len(args) >= 3 and args[0] == "-m" and args[1] == "twine" and args[2] == "upload":
        return Decision(True, "Blocked raw package upload. Publishing requires separate explicit authorization and a tested guarded release workflow.")

    if base in {"winget", "choco", "scoop"} and any(arg in {"install", "upgrade", "update"} for arg in args[:4]):
        if base == "winget" and "install" in args[:4]:
            return Decision(True, "Blocked raw winget installation. After explicit package/version/scope authorization, use codex-safe-development/scripts/install_global_tool.py for an exact source check, install, and post-install verification.")
        return Decision(True, "Blocked raw global software installation or upgrade. Use the guarded exact-version winget installer when available; upgrades and other managers need a separately tested workflow.")
    if base in {"npm", "pnpm", "yarn", "bun"} and any(arg in {"install", "i", "add"} for arg in args[:4]) and any(arg in {"-g", "--global"} for arg in args):
        return Decision(True, "Blocked raw global JavaScript package installation. Prefer a project-local dependency; otherwise request scoped authorization and keep execution with the assistant.")
    if base == "yarn" and args[:2] == ["global", "add"]:
        return Decision(True, "Blocked automatic global JavaScript package installation.")
    if base in {"pip", "pip3", "pipx"} and any(arg in {"install", "upgrade", "uninstall"} for arg in args[:4]):
        return Decision(True, "Blocked ambiguous system-level Python package installation. Use an explicit project virtual environment or request scoped authorization; do not hand the command to a beginner.")
    if base in {"python", "python3", "py"} and len(args) >= 3 and args[:2] == ["-m", "pip"] and any(arg in {"install", "uninstall"} for arg in args[2:6]):
        explicit_venv = "/.venv/" in executable or "/venv/" in executable
        if not explicit_venv:
            return Decision(True, "Blocked Python package installation outside an explicit project virtual environment.")

    if base == "gh" and (args[:2] == ["pr", "merge"] or args[:1] == ["release"] or args[:2] == ["repo", "delete"]):
        return Decision(True, "Blocked raw GitHub mutation. It requires separate explicit authorization and a tested guarded PR/release/repository workflow; do not hand the command to a beginner.")
    if base in {"npm", "pnpm"} and args[:1] == ["publish"]:
        return Decision(True, "Blocked raw package publishing. It requires separate explicit authorization and a tested guarded release workflow.")
    if base == "yarn" and (args[:2] == ["npm", "publish"] or args[:1] == ["publish"]):
        return Decision(True, "Blocked raw package publishing. It requires separate explicit authorization and a tested guarded release workflow.")
    if base in {"cargo", "gem"} and args[:1] in (["publish"], ["push"]):
        return Decision(True, "Blocked raw package publishing. It requires separate explicit authorization and a tested guarded release workflow.")
    if base == "twine" and args[:1] == ["upload"]:
        return Decision(True, "Blocked raw package upload. It requires separate explicit authorization and a tested guarded release workflow.")
    if base == "docker" and args[:1] == ["push"]:
        return Decision(True, "Blocked raw container image publishing. It requires separate explicit authorization, immutable artifact identity, and a tested guarded release workflow.")

    blocked_prefixes = {
        "kubectl": {"apply", "delete", "replace", "patch", "rollout", "scale", "set"},
        "helm": {"install", "upgrade", "uninstall", "rollback"},
        "terraform": {"apply", "destroy", "import"},
        "tofu": {"apply", "destroy", "import"},
        "pulumi": {"up", "destroy", "import"},
        "vercel": {"deploy"},
        "netlify": {"deploy"},
        "firebase": {"deploy"},
        "flyctl": {"deploy"},
        "railway": {"up"},
        "serverless": {"deploy", "remove"},
    }
    if base in blocked_prefixes and args and args[0] in blocked_prefixes[base]:
        return Decision(True, f"Blocked automatic {base} {args[0]}. Prepare a preview or plan for user review instead.")
    if base == "aws" and args[:2] in (["cloudformation", "deploy"], ["cloudformation", "delete-stack"]):
        return Decision(True, "Blocked automatic AWS infrastructure mutation.")
    if base == "az" and args[:1] == ["deployment"]:
        return Decision(True, "Blocked automatic Azure deployment mutation.")
    if base == "gcloud" and "deploy" in args[:4]:
        return Decision(True, "Blocked automatic Google Cloud deployment.")
    if base in {"make", "task", "just"} and args and any(word in args[0] for word in ("deploy", "release", "publish", "prod-migrate", "infra-apply")):
        return Decision(True, "Blocked raw release or deployment task. It requires separate explicit authorization and a tested guarded environment-specific workflow.")
    if base in {"npm", "pnpm", "yarn", "bun"} and args[:1] == ["run"] and len(args) > 1 and any(word in args[1] for word in ("deploy", "release", "publish", "migrate:prod", "infra:apply")):
        return Decision(True, "Blocked release, production migration, or deployment script.")
    if base == "prisma" and args[:2] == ["migrate", "deploy"]:
        return Decision(True, "Blocked production-style Prisma migration. Prepare and review it without running it automatically.")
    if base == "supabase" and args[:2] == ["db", "push"]:
        return Decision(True, "Blocked remote database schema push.")
    return Decision(False)


def _classify_tokens(tokens: Sequence[str]) -> Decision:
    stripped = _strip_prefixes(tokens)
    if not stripped:
        return Decision(False)
    nested = _nested_shell_script(stripped)
    if nested is not None:
        return classify_command(nested)
    if _basename(stripped[0]) in {"git", "git.exe"}:
        return _classify_git(stripped)
    return _classify_external(stripped)


def _catastrophic_delete(command: str) -> Decision:
    patterns = [
        r"(?i)(?:^|[;&|]\s*)rm\s+-[^\r\n;&|]*r[^\r\n;&|]*f[^\r\n;&|]*\s+(?:/|~|\.\.?|[a-z]:[\\/])(?:\s|$)",
        r"(?i)\bRemove-Item\b(?=[^\r\n;&|]*-(?:Recurse|r)\b)(?=[^\r\n;&|]*-(?:Force|fo)\b)[^\r\n;&|]*(?:\s|^)(?:~|\.\.?|\.git|[a-z]:[\\/](?:\s|$))",
        r"(?i)(?:^|[;&|]\s*)(?:rmdir|rd)\s+/s\s+/q\s+[a-z]:\\(?:\s|$)",
        r"(?i)(?:^|[;&|]\s*)(?:format|diskpart|Clear-Disk|Initialize-Disk)(?:\s|$)",
    ]
    if any(re.search(pattern, command) for pattern in patterns):
        return Decision(True, "Blocked a catastrophic or difficult-to-recover deletion command.")
    return Decision(False)


def _extract_substitutions(command: str) -> list[str]:
    """Command substitutions hide a second command from a single-pass lexer."""
    results: list[str] = []
    results += re.findall(r"\$\(\s*(.+?)\s*\)", command, re.DOTALL)
    results += re.findall(r"`\s*(.+?)\s*`", command, re.DOTALL)
    return results


def classify_command(command: str, _depth: int = 0) -> Decision:
    deletion = _catastrophic_delete(command)
    if deletion.blocked:
        return deletion
    # A newline separates commands, but shlex(whitespace_split=True) folds it into
    # ordinary whitespace and would hide every command after the first line
    # (e.g. "git status\ngit push --force"). Normalize newlines to an explicit
    # separator the segmenter already understands before lexing.
    normalized = command.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ; ")
    for segment in _segments(_lex(normalized)):
        decision = _classify_tokens(segment)
        if decision.blocked:
            return decision
    # A nested command inside $( ... ) or backticks is invisible to the lexer above;
    # classify each substitution body too, so `echo $(git push --force)` is caught.
    if _depth < 4:
        for nested in _extract_substitutions(command):
            if nested.strip():
                decision = classify_command(nested, _depth + 1)
                if decision.blocked:
                    return decision
    return Decision(False)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    if not isinstance(command, str) or not command.strip():
        return 0

    decision = classify_command(command)
    if not decision.blocked:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": decision.reason,
        }
    }
    json.dump(output, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
