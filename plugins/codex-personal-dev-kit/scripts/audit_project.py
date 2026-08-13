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
from urllib.parse import unquote, urlparse

from feature_guard import GuardError, is_active_feature, is_critical_feature, read_feature_catalog


SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "coverage", ".next", ".cache", "target", "__pycache__"}
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java", ".js", ".jsx",
    ".kt", ".php", ".py", ".rb", ".rs", ".scss", ".swift", ".ts", ".tsx", ".vue", ".mjs", ".cjs",
    ".svelte", ".astro", ".sql", ".graphql", ".gql", ".json", ".yaml", ".yml", ".toml", ".xml",
}
DOC_BUDGETS = {
    "AGENTS.md": ("bytes", 8192),
    "docs/INDEX.md": ("lines", 120),
    "docs/PROJECT.md": ("lines", 200),
    "docs/FEATURES.md": ("lines", 250),
    "docs/ROADMAP.md": ("lines", 150),
    "docs/ARCHITECTURE.md": ("lines", 300),
    "docs/DESIGN.md": ("lines", 300),
    "docs/STATUS.md": ("lines", 150),
    "docs/VERSIONS.md": ("lines", 250),
}
DOMAIN_DOCUMENT_MAX_LINES = 1000
DOMAIN_DOCUMENT_MAX_BYTES = 128 * 1024
ADR_DOCUMENT_MAX_LINES = 800
ADR_DOCUMENT_MAX_BYTES = 64 * 1024
ACTIVE_PLAN_RELATIVE = Path(".codex/active-plan.md")
ACTIVE_PLAN_STALE_DAYS = 14
OVERSIZED_HISTORY_BYTES = 64 * 1024
OVERSIZED_DOCUMENT_BYTES = 128 * 1024
LARGE_UNIGNORED_FILE_BYTES = 50 * 1024 * 1024
LARGE_UNIGNORED_FILE_REPORT_LIMIT = 10
TEXT_DOCUMENT_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".adoc"}
HISTORY_NAME_PATTERN = re.compile(
    r"(?:development[-_ ]?(?:log|notes?|history|journal|document)|dev[-_ ]?(?:log|notes?|history)|chat[-_ ]?(?:log|history|transcript)|conversation[-_ ]?(?:log|history|transcript)|session[-_ ]?(?:log|notes?|history)|progress[-_ ]?log|ai[-_ ]?history|开发(?:日志|记录|文档|笔记|历史)|聊天(?:记录|日志|历史)|对话(?:记录|日志|历史)|会话(?:记录|日志|历史)|进度日志)",
    flags=re.IGNORECASE,
)
NEXT_ACTION_PATTERN = re.compile(r"(?im)^##\s+(?:next actions?|下一步)\s*$")
MARKDOWN_LINK_PATTERN = re.compile(
    r"(?<!\!)\[[^\]]*\]\(\s*(?P<target><[^>]+>|[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
MARKDOWN_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
HTML_ANCHOR_PATTERN = re.compile(r"(?i)(?:id|name)\s*=\s*[\"']([^\"']+)[\"']")
MARKDOWN_DOCUMENT_SUFFIXES = {".md", ".markdown"}
ORPHAN_DOCUMENT_EXCLUSIONS = {
    "docs/INDEX.md",
    "docs/adr/INDEX.md",
    "docs/adr/0000-decision-template.md",
}


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


def _markdown_anchor_slug(text: str) -> str:
    """Approximate GitHub-style heading anchors without requiring a renderer."""

    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{#([^\s}]+)\}", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text)


def _markdown_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        for explicit in HTML_ANCHOR_PATTERN.findall(line):
            anchors.add(unquote(explicit))
        heading = MARKDOWN_HEADING_PATTERN.match(line)
        if not heading:
            continue
        raw = heading.group(1)
        explicit = re.search(r"\{#([^\s}]+)\}", raw)
        if explicit:
            anchors.add(unquote(explicit.group(1)))
        slug = _markdown_anchor_slug(raw)
        if not slug:
            continue
        occurrence = counts.get(slug, 0)
        anchors.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
        counts[slug] = occurrence + 1
    return anchors


def _markdown_links(text: str) -> list[tuple[int, str]]:
    """Return (line number, target) pairs while ignoring fenced/inline code."""

    links: list[tuple[int, str]] = []
    in_fence = False
    fence_pattern = re.compile(r"^\s*(`{3,}|~{3,})")
    for line_number, line in enumerate(text.splitlines(), start=1):
        fence = fence_pattern.match(line)
        if fence:
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible = re.sub(r"`[^`]*`", "", line)
        for match in MARKDOWN_LINK_PATTERN.finditer(visible):
            target = match.group("target").strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            links.append((line_number, unquote(target)))
    return links


def _is_external_link(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme) or target.startswith("//")


def _markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in iter_files(root)
        if path.suffix.lower() in MARKDOWN_DOCUMENT_SUFFIXES
        and ("docs" in path.relative_to(root).parts or path.name in {"AGENTS.md", "README.md"})
    )


def _audit_markdown_navigation(root: Path) -> tuple[list[dict], dict]:
    """Check local Markdown links and report docs that have no incoming link."""

    findings: list[dict] = []
    markdown_files = _markdown_files(root)
    incoming: dict[Path, list[str]] = {}
    anchors_cache: dict[Path, set[str]] = {}
    local_link_count = 0
    broken_link_count = 0
    broken_anchor_count = 0

    for source in markdown_files:
        source_relative = source.relative_to(root).as_posix()
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, target in _markdown_links(text):
            if _is_external_link(target) or target.startswith("#") and not target[1:]:
                continue
            path_part, separator, fragment = target.partition("#")
            if not path_part:
                candidate = source
            else:
                candidate = (source.parent / path_part.replace("/", os.sep)).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                findings.append(
                    finding(
                        "P2",
                        "document-link-outside-root",
                        f"Local Markdown link points outside the audited project: {target}.",
                        f"{source_relative}:{line_number}",
                    )
                )
                broken_link_count += 1
                continue
            if not candidate.is_file():
                findings.append(
                    finding(
                        "P2",
                        "broken-document-link",
                        f"Markdown link target does not exist: {target}.",
                        f"{source_relative}:{line_number}",
                    )
                )
                broken_link_count += 1
                continue
            local_link_count += 1
            incoming.setdefault(candidate, []).append(source_relative)
            if separator and fragment:
                if candidate not in anchors_cache:
                    try:
                        anchors_cache[candidate] = _markdown_anchors(
                            candidate.read_text(encoding="utf-8", errors="replace")
                        )
                    except OSError:
                        anchors_cache[candidate] = set()
                if fragment not in anchors_cache[candidate]:
                    findings.append(
                        finding(
                            "P2",
                            "broken-document-anchor",
                            f"Markdown link anchor does not exist: {target}.",
                            f"{source_relative}:{line_number}",
                        )
                    )
                    broken_anchor_count += 1

    docs_root = root / "docs"
    index_path = docs_root / "INDEX.md"
    orphan_count = 0
    if docs_root.is_dir() and index_path.is_file():
        for document in sorted(docs_root.rglob("*.md")):
            relative = document.relative_to(root).as_posix()
            if relative in ORPHAN_DOCUMENT_EXCLUSIONS or any(
                part in {"history", "archive", "archives"} for part in document.relative_to(docs_root).parts
            ):
                continue
            if document not in incoming:
                findings.append(
                    finding(
                        "P3",
                        "orphan-document",
                        "Markdown document is not reachable from another Markdown document. Add it to the relevant index or remove it if it is not durable project knowledge.",
                        relative,
                    )
                )
                orphan_count += 1

    return findings, {
        "markdown_document_count": len(markdown_files),
        "local_document_link_count": local_link_count,
        "broken_document_link_count": broken_link_count,
        "broken_document_anchor_count": broken_anchor_count,
        "orphan_document_count": orphan_count,
    }


def _unignored_relative_paths(root: Path, is_git_repository: bool) -> list[str]:
    """List the paths no ignore rule covers, which is what a clone, checkpoint, or whole-project scan actually carries."""

    if not is_git_repository:
        return [path.relative_to(root).as_posix() for path in iter_files(root)]
    names: list[str] = []
    for arguments in (("ls-files",), ("ls-files", "--others", "--exclude-standard")):
        code, output = git(root, "-c", "core.quotePath=false", *arguments)
        if code != 0:
            continue
        names.extend(line for line in output.splitlines() if line)
    return names


def _audit_large_unignored_files(root: Path, threshold_bytes: int, is_git_repository: bool) -> tuple[list[dict], dict]:
    """Report heavy files before they slow down a clone or a scan, without touching them or any ignore rule."""

    measured: list[tuple[int, str]] = []
    for relative in dict.fromkeys(_unignored_relative_paths(root, is_git_repository)):
        path = root / relative
        try:
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
        except OSError:
            continue
        if size > threshold_bytes:
            measured.append((size, relative))
    measured.sort(reverse=True)
    reported = measured[:LARGE_UNIGNORED_FILE_REPORT_LIMIT]
    findings = [
        finding(
            "P2",
            "large-unignored-file",
            f"This {size}-byte file is above the {threshold_bytes}-byte report threshold and no ignore rule covers it, so every clone, checkpoint, and whole-project scan carries it. Confirm it belongs in the project before it becomes a recovery or context problem.",
            relative,
        )
        for size, relative in reported
    ]
    metrics = {
        "large_unignored_file_threshold_bytes": threshold_bytes,
        "large_unignored_file_count": len(measured),
        "large_unignored_files": [{"path": relative, "bytes": size} for size, relative in reported],
    }
    return findings, metrics


def audit(root: Path, large_file_bytes: int = LARGE_UNIGNORED_FILE_BYTES) -> dict:
    findings: list[dict] = []
    metrics: dict = {}
    required_docs = [
        ("AGENTS.md",),
        ("docs/INDEX.md",),
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

    domain_root = root / "docs/features"
    if domain_root.is_dir():
        for path in sorted(domain_root.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            size = path.stat().st_size
            if lines > DOMAIN_DOCUMENT_MAX_LINES or size > DOMAIN_DOCUMENT_MAX_BYTES:
                findings.append(
                    finding(
                        "P2",
                        "domain-document-budget",
                        f"Domain document exceeds its {DOMAIN_DOCUMENT_MAX_LINES} line/{DOMAIN_DOCUMENT_MAX_BYTES} byte budget ({lines} lines, {size} bytes). Split stable details by smaller domain or keep an index here.",
                        relative,
                    )
                )

    status_path = root / "docs/STATUS.md"
    if status_path.is_file():
        status_text = status_path.read_text(encoding="utf-8", errors="replace")
        if not status_has_next_action(status_text):
            findings.append(finding("P2", "status-next-action-missing", "STATUS.md needs one concrete Next Action so a fresh Codex task can resume without reading old chats.", "docs/STATUS.md"))
        if re.search(r"(?im)^\s*-?\s*Last checkpoint\s*:", status_text):
            findings.append(finding("P3", "status-volatile-checkpoint", "STATUS.md records a checkpoint identifier that becomes stale after the next documentation commit. Keep the current formal version here and query Git for the latest checkpoint.", "docs/STATUS.md"))

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
        elif (
            relative.startswith("docs/")
            and not relative.startswith("docs/features/")
            and not relative.startswith("docs/adr/")
            and path.suffix.lower() in TEXT_DOCUMENT_SUFFIXES
            and size > OVERSIZED_DOCUMENT_BYTES
        ):
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
        package_path = root / "package.json"
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            dependency_sections = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
            declared_dependencies = any(isinstance(package.get(section), dict) and package.get(section) for section in dependency_sections)
            if declared_dependencies:
                findings.append(finding("P2", "missing-lockfile", "package.json declares dependencies without a recognized JavaScript lockfile.", "package.json"))
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(finding("P1", "package-json-invalid", f"package.json could not be read: {exc}", "package.json"))
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
        for path in decisions:
            relative = path.relative_to(root).as_posix()
            lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            size = path.stat().st_size
            if lines > ADR_DOCUMENT_MAX_LINES or size > ADR_DOCUMENT_MAX_BYTES:
                findings.append(
                    finding(
                        "P2",
                        "adr-document-budget",
                        f"ADR exceeds its {ADR_DOCUMENT_MAX_LINES} line/{ADR_DOCUMENT_MAX_BYTES} byte budget ({lines} lines, {size} bytes). Split the decision or replace it with a concise current record; let Git retain history.",
                        relative,
                    )
                )

    navigation_findings, navigation_metrics = _audit_markdown_navigation(root)
    findings.extend(navigation_findings)
    metrics.update(navigation_metrics)

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
        tag_code, tags = git(root, "tag", "--list", "v[0-9]*")
        semantic_tags = [tag for tag in tags.splitlines() if re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", tag)] if tag_code == 0 else []
        versions_path = root / "docs/VERSIONS.md"
        if semantic_tags and not versions_path.is_file():
            findings.append(finding("P2", "versions-index-missing", "Formal local version tags exist but docs/VERSIONS.md is missing, so a beginner cannot identify versions by capability.", "docs/VERSIONS.md"))
        elif semantic_tags:
            versions_text = versions_path.read_text(encoding="utf-8", errors="replace")
            missing_rows = [tag for tag in semantic_tags if not re.search(rf"(?im)^\|\s*{re.escape(tag)}\s*\|", versions_text)]
            if missing_rows:
                findings.append(finding("P2", "versions-index-incomplete", "Formal versions are missing from docs/VERSIONS.md: " + ", ".join(missing_rows), "docs/VERSIONS.md"))
        ignore_code, _ = git(root, "check-ignore", ".codex/current-change.json")
        if ignore_code != 0:
            findings.append(finding("P1", "change-contract-not-ignored", ".codex/current-change.json must stay local and out of Git history.", ".gitignore"))
        plan_ignore_code, _ = git(root, "check-ignore", ACTIVE_PLAN_RELATIVE.as_posix())
        if plan_ignore_code != 0:
            findings.append(finding("P1", "active-plan-not-ignored", ".codex/active-plan.md must stay temporary and out of Git history.", ".gitignore"))

    large_findings, large_metrics = _audit_large_unignored_files(root, large_file_bytes, metrics["is_git_repository"])
    findings.extend(large_findings)
    metrics.update(large_metrics)

    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["code"], item.get("path", "")))
    return {"root": str(root), "findings": findings, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Explicit project root to audit")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.add_argument("--fail-on", choices=("P0", "P1", "P2", "P3"), help="Return nonzero when this severity or worse is present")
    parser.add_argument(
        "--large-file-bytes",
        type=int,
        default=LARGE_UNIGNORED_FILE_BYTES,
        help="Report every file above this size that no ignore rule covers",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Project root does not exist: {root}")
    if root == Path(root.anchor):
        parser.error("Refusing to audit a filesystem root; select one project directory")
    if args.large_file_bytes <= 0:
        parser.error("--large-file-bytes must be a positive number of bytes")

    report = audit(root, args.large_file_bytes)
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
