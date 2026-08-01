#!/usr/bin/env python3
"""Read-only health audit for one explicitly selected software project."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from feature_guard import GuardError, is_active_feature, is_critical_feature, read_feature_catalog


SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "coverage", ".next", ".cache", "target", "__pycache__"}
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java", ".js", ".jsx",
    ".kt", ".php", ".py", ".rb", ".rs", ".scss", ".swift", ".ts", ".tsx", ".vue",
}
DOC_BUDGETS = {
    "AGENTS.md": ("bytes", 8192),
    "docs/PROJECT.md": ("lines", 200),
    "docs/FEATURES.md": ("lines", 250),
    "docs/ROADMAP.md": ("lines", 150),
    "docs/ARCHITECTURE.md": ("lines", 300),
    "docs/DESIGN.md": ("lines", 300),
    "docs/STATUS.md": ("lines", 150),
}
ACTIVE_PLAN_RELATIVE = Path(".codex/active-plan.md")
ACTIVE_PLAN_STALE_DAYS = 14
OVERSIZED_HISTORY_BYTES = 64 * 1024
OVERSIZED_DOCUMENT_BYTES = 128 * 1024
TEXT_DOCUMENT_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".adoc"}
HISTORY_NAME_PATTERN = re.compile(
    r"(?:development[-_ ]?(?:log|notes?|history|journal|document)|dev[-_ ]?(?:log|notes?|history)|chat[-_ ]?(?:log|history|transcript)|conversation[-_ ]?(?:log|history|transcript)|session[-_ ]?(?:log|notes?|history)|progress[-_ ]?log|ai[-_ ]?history|开发(?:日志|记录|文档|笔记|历史)|聊天(?:记录|日志|历史)|对话(?:记录|日志|历史)|会话(?:记录|日志|历史)|进度日志)",
    flags=re.IGNORECASE,
)
NEXT_ACTION_PATTERN = re.compile(r"(?im)^##\s+(?:next actions?|下一步)\s*$")


def git(root: Path, *args: str) -> tuple[int, str]:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return process.returncode, process.stdout.strip()


def iter_files(root: Path):
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in SKIP_DIRS]
        current_path = Path(current)
        for name in files:
            yield current_path / name


def finding(severity: str, code: str, message: str, path: str | None = None) -> dict:
    item = {"severity": severity, "code": code, "message": message}
    if path:
        item["path"] = path
    return item


def status_has_next_action(text: str) -> bool:
    match = NEXT_ACTION_PATTERN.search(text)
    if not match:
        return False
    remainder = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", remainder)
    body = remainder[: next_heading.start()] if next_heading else remainder
    meaningful = " ".join(line.strip().lstrip("-* ") for line in body.splitlines() if line.strip())
    return bool(meaningful) and meaningful.lower() not in {"not yet confirmed", "none", "n/a", "待确认", "无"}


def audit(root: Path) -> dict:
    findings: list[dict] = []
    metrics: dict = {}
    required_docs = [
        ("AGENTS.md",),
        ("docs/PROJECT.md",),
        ("docs/FEATURES.md",),
        ("docs/ROADMAP.md",),
        ("docs/ARCHITECTURE.md", "docs/DESIGN.md"),
        ("docs/STATUS.md",),
    ]
    for alternatives in required_docs:
        if not any((root / relative).is_file() for relative in alternatives):
            findings.append(finding("P2", "missing-project-context", "Long-term project context file is missing.", alternatives[0]))

    for relative, (kind, budget) in DOC_BUDGETS.items():
        path = root / relative
        if not path.is_file():
            continue
        if kind == "bytes":
            value = path.stat().st_size
        else:
            value = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if value > budget:
            split_hint = " Keep the main file as a domain index and split stable details by domain." if relative in {"docs/FEATURES.md", "docs/ARCHITECTURE.md", "docs/DESIGN.md"} else ""
            findings.append(finding("P2", "document-budget", f"Current-state document exceeds its {budget} {kind} budget ({value}). Remove stale or duplicate content before appending.{split_hint}", relative))

    status_path = root / "docs/STATUS.md"
    if status_path.is_file():
        status_text = status_path.read_text(encoding="utf-8", errors="replace")
        if not status_has_next_action(status_text):
            findings.append(finding("P2", "status-next-action-missing", "STATUS.md needs one concrete Next Action so a fresh Codex task can resume without reading old chats.", "docs/STATUS.md"))

    feature_map = root / "docs/FEATURES.md"
    if feature_map.is_file():
        try:
            features = read_feature_catalog(root)
            active_features = [feature for feature in features.values() if is_active_feature(feature)]
            metrics["feature_count"] = len(features)
            metrics["active_feature_count"] = len(active_features)
            metrics["critical_feature_count"] = sum(1 for feature in active_features if is_critical_feature(feature))
            if not active_features:
                findings.append(finding("P2", "feature-map-empty", "No accepted active feature is recorded yet. Confirm the first real user journey before broad implementation.", "docs/FEATURES.md"))
            for feature in active_features:
                if not feature.entry_points.strip():
                    findings.append(finding("P2", "feature-entry-missing", f"Active feature {feature.id} does not record its connected UI/API/background path.", feature.source))
                if not feature.verification.strip() or feature.verification.strip().lower() in {"not yet confirmed", "待确认"}:
                    severity = "P1" if is_critical_feature(feature) else "P2"
                    findings.append(finding(severity, "feature-verification-missing", f"Active feature {feature.id} has no repeatable verification entry.", feature.source))
        except GuardError as exc:
            findings.append(finding("P1", "feature-map-invalid", str(exc), "docs/FEATURES.md"))

    current_change = root / ".codex/current-change.json"
    change_state: str | None = None
    if current_change.is_file():
        try:
            change_state = json.loads(current_change.read_text(encoding="utf-8")).get("state", "unknown")
            severity = "P2" if change_state == "open" else "P3"
            findings.append(finding(severity, "current-change-present", f"A {change_state} temporary change contract remains. Resume or finish that task before unrelated edits.", ".codex/current-change.json"))
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(finding("P1", "current-change-invalid", f"Temporary change contract is unreadable: {exc}", ".codex/current-change.json"))

    active_plan = root / ACTIVE_PLAN_RELATIVE
    if active_plan.is_file():
        age_days = max(0, (datetime.now(timezone.utc).timestamp() - active_plan.stat().st_mtime) / 86400)
        metrics["active_plan_age_days"] = round(age_days, 1)
        if change_state != "open" or age_days > ACTIVE_PLAN_STALE_DAYS:
            findings.append(finding("P2", "stale-active-plan", "The single temporary active plan is stale or has no open change contract. Delete it after transferring current facts to STATUS.md.", ACTIVE_PLAN_RELATIVE.as_posix()))

    all_files = list(iter_files(root))
    source_sizes = []
    relative_names = []
    for path in all_files:
        relative = path.relative_to(root).as_posix()
        relative_names.append(relative)
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        history_match = HISTORY_NAME_PATTERN.search(relative)
        if size > OVERSIZED_HISTORY_BYTES and history_match:
            findings.append(finding("P2", "oversized-history-log", f"This {size}-byte development/chat history is too large for project memory. Keep current facts in STATUS/features/architecture and let Git retain history.", relative))
        elif relative.startswith("docs/") and path.suffix.lower() in TEXT_DOCUMENT_SUFFIXES and size > OVERSIZED_DOCUMENT_BYTES:
            findings.append(finding("P2", "oversized-document", f"This {size}-byte text document is too large for fast project recovery. Keep a concise index/current-state file and split durable details by stable domain.", relative))
        if path.suffix.lower() in SOURCE_EXTENSIONS:
            try:
                source_sizes.append((size, relative))
            except OSError:
                pass
    metrics["largest_source_files"] = [
        {"path": path, "bytes": size} for size, path in sorted(source_sizes, reverse=True)[:10]
    ]

    manifests = {name for name in relative_names if name in {"package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts"}}
    js_locks = [name for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb") if name in relative_names]
    if "package.json" in manifests and not js_locks:
        findings.append(finding("P2", "missing-lockfile", "package.json exists without a recognized JavaScript lockfile."))
    if len(js_locks) > 1:
        findings.append(finding("P2", "multiple-lockfiles", f"Multiple JavaScript lockfiles found: {', '.join(js_locks)}."))

    test_markers = [name for name in relative_names if any(part.lower() in {"test", "tests", "spec", "specs", "__tests__"} for part in Path(name).parts)]
    if manifests and not test_markers:
        findings.append(finding("P2", "tests-not-located", "No conventional test directory was found. Confirm how behavior is verified."))

    adr_root = root / "docs/adr"
    if adr_root.is_dir():
        decisions = [
            path for path in adr_root.glob("*.md")
            if path.name.lower() not in {"index.md", "0000-decision-template.md"}
        ]
        metrics["adr_count"] = len(decisions)
        if len(decisions) >= 3 and not (adr_root / "INDEX.md").is_file():
            findings.append(finding("P3", "adr-index-missing", "Add docs/adr/INDEX.md so current decisions can be found without scanning every ADR.", "docs/adr/INDEX.md"))
        if len(decisions) > 30:
            findings.append(finding("P2", "adr-index-large", "The ADR collection is large. Group the index by stable domain and mark superseded decisions; do not merge ADR history into one giant file.", "docs/adr/INDEX.md"))

    git_code, git_root = git(root, "rev-parse", "--show-toplevel")
    metrics["is_git_repository"] = git_code == 0
    if git_code != 0:
        findings.append(finding("P1", "git-missing", "The project is not a Git repository, so checkpoints and Worktrees are unavailable."))
    else:
        status_code, status = git(root, "status", "--short")
        metrics["working_tree_entries"] = len(status.splitlines()) if status_code == 0 and status else 0
        branch_code, branch = git(root, "status", "-sb")
        metrics["branch_status"] = branch.splitlines()[0] if branch_code == 0 and branch else "unknown"
        worktree_code, worktrees = git(root, "worktree", "list", "--porcelain")
        worktree_count = sum(1 for line in worktrees.splitlines() if line.startswith("worktree ")) if worktree_code == 0 else 0
        metrics["worktree_count"] = worktree_count
        if worktree_count > 10:
            findings.append(finding("P3", "worktree-count", f"The repository has {worktree_count} Worktrees. Review stale background work and disk use."))

        tracked_code, tracked = git(root, "ls-files")
        if tracked_code == 0:
            risky = []
            for name in tracked.splitlines():
                lower = Path(name).name.lower()
                if lower in {".env", "id_rsa", "id_ed25519", "credentials.json"} or lower.endswith((".pem", ".p12", ".pfx", ".key")):
                    if lower not in {".env.example", ".env.sample"}:
                        risky.append(name)
            if risky:
                findings.append(finding("P0", "sensitive-files-tracked", f"Potential secret-bearing files are tracked: {', '.join(risky[:10])}."))
        ignore_code, _ = git(root, "check-ignore", ".codex/current-change.json")
        if ignore_code != 0:
            findings.append(finding("P1", "change-contract-not-ignored", ".codex/current-change.json must stay local and out of Git history.", ".gitignore"))
        plan_ignore_code, _ = git(root, "check-ignore", ACTIVE_PLAN_RELATIVE.as_posix())
        if plan_ignore_code != 0:
            findings.append(finding("P1", "active-plan-not-ignored", ".codex/active-plan.md must stay temporary and out of Git history.", ".gitignore"))

    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["code"], item.get("path", "")))
    return {"root": str(root), "findings": findings, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Explicit project root to audit")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.add_argument("--fail-on", choices=("P0", "P1", "P2", "P3"), help="Return nonzero when this severity or worse is present")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Project root does not exist: {root}")
    if root == Path(root.anchor):
        parser.error("Refusing to audit a filesystem root; select one project directory")

    report = audit(root)
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        if report["findings"]:
            for item in report["findings"]:
                location = f" [{item['path']}]" if item.get("path") else ""
                print(f"{item['severity']} {item['code']}{location}: {item['message']}")
        else:
            print("No audit findings.")
        print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[item["severity"]] <= threshold for item in report["findings"]):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
