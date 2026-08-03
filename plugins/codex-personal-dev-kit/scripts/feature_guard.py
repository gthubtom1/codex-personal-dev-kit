#!/usr/bin/env python3
"""Protect accepted project behavior while Codex changes an existing project."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


CONTRACT_RELATIVE = Path(".codex/current-change.json")
FEATURE_MAP_RELATIVE = Path("docs/FEATURES.md")
FEATURE_MAP_DIRECTORY_RELATIVE = Path("docs/features")
STATUS_RELATIVE = Path("docs/STATUS.md")
PROJECT_CONFIG_RELATIVE = Path(".codex/config.toml")
RECOVERY_STATUS_MAX_CHARS = 1600
RECOVERY_NEXT_ACTION_MAX_CHARS = 700
RECOVERY_PACKET_MAX_CHARS = 3600
MAX_VERIFICATION_RUNS = 20
MAX_COMMAND_CHARS = 2000
MAX_CHECKPOINT_MESSAGE_CHARS = 240
CHECKPOINT_AUTHOR_NAME = "Codex Dev Kit"
CHECKPOINT_AUTHOR_EMAIL = "codex-dev-kit@local.invalid"
VERSIONS_RELATIVE = Path("docs/VERSIONS.md")
SEMVER_PATTERN = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java",
    ".js", ".jsx", ".kt", ".php", ".py", ".rb", ".rs", ".scss", ".swift", ".ts",
    ".tsx", ".vue", ".mjs", ".cjs", ".svelte", ".astro", ".sql", ".graphql", ".gql",
    ".json", ".yaml", ".yml", ".toml", ".xml",
}
TEMPLATE_PLACEHOLDER_PATTERNS = {
    "AGENTS.md": (
        r"(?im)^\s*-\s*(?:Install|Start|Test|Lint/type/build):\s*not confirmed\.\s*$",
    ),
    "docs/PROJECT.md": (
        r"(?im)^\s*Not yet confirmed\.",
        r"(?im)^\s*-\s*Current scope is not yet confirmed\.",
        r"(?im)^\s*Describe the primary user, their skill level, and the problem this project solves\.",
        r"(?im)^\s*State the user-visible result, not only the technology to build\.",
    ),
    "docs/FEATURES.md": (
        r"(?im)^\s*\|[^\n]*\|\s*Not yet confirmed\s*\|",
        r"(?im)^\s*\|[^\n]*\|\s*Not yet confirmed\s*$",
    ),
    "docs/ARCHITECTURE.md": (
        r"(?im)^\s*The current system has not been mapped yet\.",
        r"(?im)^\s*List modules by responsibility, their public interfaces, and allowed dependency direction\.",
        r"(?im)^\s*Describe the important path from user input to storage or output\.",
    ),
    "docs/STATUS.md": (
        r"(?im)^\s*Project onboarding is in progress\.\s*$",
        r"(?im)^\s*-\s*(?:Branch/worktree|Last checkpoint|Working tree):\s*not yet (?:recorded|inspected)\.\s*$",
        r"(?im)^\s*-\s*No project commands have been verified yet\.\s*$",
    ),
}
INACTIVE_STATUSES = {"planned", "retired", "removed", "deprecated", "not yet confirmed", "待确认", "规划中", "已停用"}
ACTIVE_STATUSES = {"active", "accepted", "stable", "verified", "当前", "已验收", "稳定"}
CRITICAL_VALUES = {"critical", "core", "high", "关键", "核心"}
HEADER_ALIASES = {
    "id": "id",
    "功能 id": "id",
    "feature id": "id",
    "user capability": "capability",
    "capability": "capability",
    "用户能力": "capability",
    "entry points / connected path": "entry_points",
    "entry points": "entry_points",
    "connected path": "entry_points",
    "入口与完整链路": "entry_points",
    "入口": "entry_points",
    "expected result": "expected_result",
    "预期结果": "expected_result",
    "verification": "verification",
    "验证": "verification",
    "criticality": "criticality",
    "重要性": "criticality",
    "status": "status",
    "状态": "status",
}


class GuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class Feature:
    id: str
    capability: str
    entry_points: str
    expected_result: str
    verification: str
    criticality: str
    status: str
    source: str = "docs/FEATURES.md"

    def invariant(self) -> dict[str, str]:
        return {
            "capability": _normalize_text(self.capability),
            "entry_points": _normalize_text(self.entry_points),
            "expected_result": _normalize_text(self.expected_result),
            "status": _normalize_text(self.status),
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _split_values(values: Sequence[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for item in value.split(","):
            normalized = item.strip()
            if normalized and normalized not in result:
                result.append(normalized)
    return result


def _run_git(root: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git_head(root: Path) -> str | None:
    result = _run_git(root, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def _resolve_project_root(start: Path, require_managed: bool = True) -> Path | None:
    start = start.expanduser().resolve()
    probe = start if start.is_dir() else start.parent
    result = _run_git(probe, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    root = Path(result.stdout.strip()).resolve()
    if require_managed and not (
        (root / FEATURE_MAP_RELATIVE).is_file()
        and (root / PROJECT_CONFIG_RELATIVE).is_file()
        and (root / "AGENTS.md").is_file()
    ):
        return None
    return root


def _require_root(value: str) -> Path:
    root = _resolve_project_root(Path(value), require_managed=True)
    if root is None:
        raise GuardError("Select one Dev Kit project Git repository with AGENTS.md, docs/FEATURES.md, and .codex/config.toml.")
    return root


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    body = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
    cells = re.split(r"(?<!\\)\|", body)
    return [cell.replace("\\|", "|").strip() for cell in cells]


def _read_feature_map(path: Path, *, allow_index_only: bool = False, source: str | None = None) -> dict[str, Feature]:
    if not path.is_file():
        raise GuardError(f"Feature map not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_index = -1
    headers: list[str] = []
    for index, line in enumerate(lines):
        cells = _split_markdown_row(line)
        normalized = [_normalize_text(cell) for cell in cells]
        mapped = [HEADER_ALIASES.get(item) for item in normalized]
        if "id" in mapped and "capability" in mapped:
            header_index = index
            headers = [HEADER_ALIASES.get(item, item) for item in normalized]
            break
    if header_index < 0:
        if allow_index_only:
            return {}
        raise GuardError(f"{source or path.as_posix()} needs a Markdown table with an ID column.")

    features: dict[str, Feature] = {}
    for line in lines[header_index + 2 :]:
        cells = _split_markdown_row(line)
        if not cells:
            break
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        values = {headers[index]: cells[index] if index < len(cells) else "" for index in range(len(headers))}
        feature_id = values.get("id", "").strip()
        if not feature_id:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", feature_id):
            raise GuardError(f"Invalid feature ID '{feature_id}'. Use a stable value such as F-014.")
        if feature_id in features:
            raise GuardError(f"Duplicate feature ID in {source or path.as_posix()}: {feature_id}")
        features[feature_id] = Feature(
            id=feature_id,
            capability=values.get("capability", ""),
            entry_points=values.get("entry_points", ""),
            expected_result=values.get("expected_result", ""),
            verification=values.get("verification", ""),
            criticality=values.get("criticality", ""),
            status=values.get("status", ""),
            source=source or path.as_posix(),
        )
    return features


def read_feature_map(path: Path) -> dict[str, Feature]:
    return _read_feature_map(path)


def _feature_map_paths(root: Path) -> list[Path]:
    paths = [root / FEATURE_MAP_RELATIVE]
    split_root = root / FEATURE_MAP_DIRECTORY_RELATIVE
    if split_root.is_dir():
        paths.extend(sorted(path for path in split_root.rglob("*.md") if path.is_file()))
    return paths


def read_feature_catalog(root: Path) -> dict[str, Feature]:
    features: dict[str, Feature] = {}
    sources: dict[str, str] = {}
    paths = _feature_map_paths(root)
    for index, path in enumerate(paths):
        source = path.relative_to(root).as_posix()
        current = _read_feature_map(path, allow_index_only=index == 0 and len(paths) > 1, source=source)
        for feature_id, feature in current.items():
            if feature_id in features:
                raise GuardError(f"Duplicate feature ID {feature_id} in {sources[feature_id]} and {source}.")
            features[feature_id] = feature
            sources[feature_id] = source
    if not features:
        raise GuardError("No feature records were found in docs/FEATURES.md or docs/features/**/*.md.")
    return features


def _is_active(feature: Feature) -> bool:
    status = _normalize_text(feature.status)
    return bool(status) and status not in INACTIVE_STATUSES


def _is_critical(feature: Feature) -> bool:
    return _normalize_text(feature.criticality) in CRITICAL_VALUES


def is_active_feature(feature: Feature) -> bool:
    return _is_active(feature)


def is_critical_feature(feature: Feature) -> bool:
    return _is_critical(feature)


def _changed_files(root: Path, baseline_head: str | None) -> set[str]:
    files: set[str] = set()
    if baseline_head:
        result = _run_git(root, "diff", "--name-only", baseline_head, "--")
        if result.returncode == 0:
            files.update(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())
    else:
        result = _run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
        if result.returncode == 0:
            files.update(line[3:].strip().replace("\\", "/") for line in result.stdout.splitlines() if len(line) > 3)
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard")
    if untracked.returncode == 0:
        files.update(line.strip().replace("\\", "/") for line in untracked.stdout.splitlines() if line.strip())
    return files


def _deleted_files(root: Path, baseline_head: str | None) -> set[str]:
    if baseline_head:
        result = _run_git(root, "diff", "--name-status", baseline_head, "--")
        if result.returncode == 0:
            return {
                parts[-1].replace("\\", "/")
                for line in result.stdout.splitlines()
                if (parts := line.split("\t")) and parts[0].startswith("D")
            }
    result = _run_git(root, "status", "--porcelain=v1")
    if result.returncode != 0:
        return set()
    return {line[3:].strip().replace("\\", "/") for line in result.stdout.splitlines() if line[:2] in {" D", "D "}}


def _staged_files(root: Path) -> set[str]:
    result = _run_git(root, "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB", "--")
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or "Unable to inspect the Git index.")
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def _index_tree(root: Path) -> str:
    result = _run_git(root, "write-tree")
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or "Unable to create a Git tree from the staged snapshot.")
    return result.stdout.strip()


def _content_fingerprint(root: Path) -> str:
    """Hash the index plus unstaged and untracked content; stays stable across a matching commit."""
    digest = hashlib.sha256()
    digest.update(_index_tree(root).encode("ascii"))
    unstaged = _run_git(root, "diff", "--binary", "--no-ext-diff", "--", text=False)
    if unstaged.returncode != 0:
        raise GuardError("Unable to fingerprint unstaged project content.")
    digest.update(unstaged.stdout)
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z", text=False)
    if untracked.returncode != 0:
        raise GuardError("Unable to fingerprint untracked project content.")
    for raw in sorted(item for item in untracked.stdout.split(b"\0") if item):
        relative = raw.decode("utf-8", errors="surrogateescape")
        path = root / relative
        digest.update(raw)
        try:
            digest.update(path.read_bytes() if path.is_file() else b"not-a-file")
        except OSError:
            digest.update(b"missing")
    return digest.hexdigest()


def _path_state(root: Path, relative: str) -> str:
    path = root / relative
    try:
        if path.is_symlink():
            return "symlink:" + os.readlink(path)
        if not path.exists():
            return "missing"
        if not path.is_file():
            return "not-a-file"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return f"file:{path.stat().st_size}:{digest}"
    except OSError as exc:
        return f"error:{exc.__class__.__name__}"


def _status_content_fingerprint(root: Path) -> str:
    """Hash meaningful STATUS content while ignoring formatting-only edits."""
    path = root / STATUS_RELATIVE
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    meaningful = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return hashlib.sha256(meaningful.encode("utf-8")).hexdigest()


def _status_quality_errors(root: Path) -> list[str]:
    path = root / STATUS_RELATIVE
    if not path.is_file():
        return ["docs/STATUS.md is missing."]
    text = path.read_text(encoding="utf-8", errors="replace")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current = _normalize_text(line[3:])
            sections[current] = []
        elif current is not None and line:
            sections[current].append(line)

    aliases = {
        "milestone": ("milestone", "current milestone", "里程碑", "当前里程碑"),
        "working": ("working state", "工作状态"),
        "verified": ("verified", "已验证"),
        "risks": ("current risks", "risks", "current limitations", "limitations", "当前风险", "当前限制"),
        "next": ("next action", "next actions", "下一步"),
    }
    errors: list[str] = []
    for label, names in aliases.items():
        content: list[str] = []
        for name in names:
            if name in sections:
                content = sections[name]
                break
        if not content:
            errors.append(f"docs/STATUS.md needs a non-empty {label} section.")
            continue
        normalized = _normalize_text(" ".join(content))
        if normalized in {"not yet confirmed", "none", "unknown", "tbd", "待确认", "无", "未知"}:
            errors.append(f"docs/STATUS.md {label} section is still a placeholder.")
    return errors


def _template_placeholder_errors(root: Path) -> list[str]:
    """Reject untouched project-template facts before a feature checkpoint."""
    errors: list[str] = []
    for relative, patterns in TEMPLATE_PLACEHOLDER_PATTERNS.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(re.search(pattern, text) for pattern in patterns):
            errors.append(
                f"Template placeholder remains in {relative}. Replace it with verified project facts before creating a feature checkpoint."
            )
    return errors


def _normalize_contract_path(root: Path, value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized or normalized in {".", "./"}:
        raise GuardError("Use explicit file paths; repository-wide pathspecs are not allowed.")
    if any(character in normalized for character in "*?[]{}"):
        raise GuardError(f"Wildcard pathspecs are not allowed in the change contract: {value}")
    candidate = Path(normalized)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", normalized):
        raise GuardError(f"Use a project-relative file path: {value}")
    resolved = (root / candidate).resolve(strict=False)
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise GuardError(f"Path escapes the selected project: {value}") from exc
    return relative.as_posix()


def _worktree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    diff = _run_git(root, "diff", "--binary", "HEAD", "--", text=False)
    digest.update(diff.stdout if diff.returncode == 0 else b"")
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z", text=False)
    if untracked.returncode == 0:
        for raw in sorted(item for item in untracked.stdout.split(b"\0") if item):
            relative = raw.decode("utf-8", errors="surrogateescape")
            path = root / relative
            digest.update(raw)
            try:
                stat = path.stat()
                digest.update(str(stat.st_size).encode("ascii"))
                if path.is_file() and stat.st_size <= 10 * 1024 * 1024:
                    digest.update(path.read_bytes())
            except OSError:
                digest.update(b"missing")
    return digest.hexdigest()


def _contract_path(root: Path) -> Path:
    return root / CONTRACT_RELATIVE


def _read_contract(root: Path) -> dict | None:
    path = _contract_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise GuardError(f"Invalid current change contract: {exc}") from exc
    if data.get("schemaVersion") != 1:
        raise GuardError("Unsupported current change contract version.")
    return data


def _write_contract(root: Path, contract: dict) -> None:
    path = _contract_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _new_changes_exist(root: Path, contract: dict) -> bool:
    return _git_head(root) != contract.get("baselineHead") or _worktree_fingerprint(root) != contract.get("baselineWorktreeFingerprint")


def _source_changed(root: Path, contract: dict) -> bool:
    current_files = _changed_files(root, contract.get("baselineHead"))
    return any(Path(name).suffix.lower() in SOURCE_EXTENSIONS for name in current_files)


def _snapshot_errors(root: Path, contract: dict) -> list[str]:
    errors: list[str] = []
    baseline_head = contract.get("baselineHead")
    if _git_head(root) != baseline_head:
        errors.append("Git HEAD changed before the verified checkpoint was created.")

    staged = _staged_files(root)
    declared_staged = set(contract.get("stagedPaths", []))
    unexpected_staged = staged - declared_staged
    missing_staged = declared_staged - staged
    if unexpected_staged:
        errors.append("The Git index contains paths not staged by the change guard: " + ", ".join(sorted(unexpected_staged)))
    if missing_staged:
        errors.append("Previously declared staged paths no longer match the Git index: " + ", ".join(sorted(missing_staged)))

    baseline_changed = set(contract.get("baselineChangedFiles", []))
    owned = set(contract.get("taskOwnedPaths", []))
    protected_staged = (set(contract.get("baselineStagedFiles", [])) & staged) - owned
    if protected_staged:
        errors.append("Pre-existing staged user work cannot enter this checkpoint: " + ", ".join(sorted(protected_staged)))
    mixed_baseline = (staged & baseline_changed) - owned
    if mixed_baseline:
        errors.append("Pre-existing changed paths require explicit --own-path ownership before staging: " + ", ".join(sorted(mixed_baseline)))

    current_changed = _changed_files(root, baseline_head)
    baseline_states = contract.get("baselinePathStates", {})
    task_delta: set[str] = set()
    for relative in current_changed | baseline_changed:
        if relative not in staged and relative in baseline_changed and _path_state(root, relative) == baseline_states.get(relative):
            continue
        if relative in staged:
            unstaged = _run_git(root, "diff", "--name-only", "--", relative)
            if unstaged.returncode != 0 or any(line.strip() for line in unstaged.stdout.splitlines()):
                errors.append(f"Staged path has additional unverified working-tree edits: {relative}")
            task_delta.add(relative)
        elif relative in current_changed or _path_state(root, relative) != baseline_states.get(relative):
            task_delta.add(relative)

    unstaged_task_delta = task_delta - staged
    if unstaged_task_delta:
        errors.append("Task changes must be staged through feature_guard.py stage before verification: " + ", ".join(sorted(unstaged_task_delta)))
    return errors


def _require_staged_snapshot(root: Path, contract: dict) -> tuple[str, str]:
    errors = _snapshot_errors(root, contract)
    if errors:
        raise GuardError("\n".join(errors))
    return _index_tree(root), _content_fingerprint(root)


def _required_verification_ids(root: Path, contract: dict, current: dict[str, Feature]) -> set[str]:
    required = set(contract.get("explicitVerificationIds", []))
    required.update(feature_id for feature_id in contract.get("changedFeatureIds", []) if feature_id in current and _is_active(current[feature_id]))
    if _source_changed(root, contract):
        # A source/config/schema change can disconnect an ordinary feature just
        # as easily as a critical one. Prefer complete active-feature coverage;
        # large catalogs may use a shared `suite:all-tests` marker or several
        # real commands, but they may not silently skip ordinary features.
        required.update(feature.id for feature in current.values() if _is_active(feature))
    return required


def _verification_markers(feature: Feature) -> list[str]:
    """Return machine-readable bindings from a feature's Verification cell.

    Human prose is still useful, but it is not enough to bind a command to a
    feature.  A marker such as ``test:tests/export.test.js`` or
    ``suite:unit`` gives the guard a stable, reviewable identity without
    executing arbitrary commands from project documentation.
    """
    value = feature.verification.strip()
    if not value or _normalize_text(value) in {"not yet confirmed", "待确认"}:
        return []
    markers = re.findall(r"(?i)(?:test|suite|command|check)\s*[:=]\s*([^\s,;|]+)", value)
    return [item.strip("`'\"").lower() for item in markers if item.strip("`'\"")]


def _verification_binding_error(features: dict[str, Feature], feature_ids: Sequence[str], rendered: str, command: Sequence[str]) -> str | None:
    if not feature_ids:
        return None

    lowered_command = rendered.lower().replace("\\", "/")
    base = re.split(r"[\\/]", command[0].strip('"\''))[-1].lower() if command else ""
    base = re.sub(r"\.(?:exe|cmd|bat)$", "", base)
    args = [item.lower() for item in command[1:]]
    inline = (
        (base in {"python", "python3", "py", "node", "deno"} and any(item in {"-c", "-e", "--eval"} for item in args[:2]))
        or (base in {"powershell", "pwsh"} and any(item in {"-command", "-c"} for item in args[:2]))
        or (base in {"cmd", "cmd.exe"} and any(item == "/c" for item in args[:2]) and any(item in {"echo", "ver", "true"} for item in args))
        or base in {"echo", "printf", "print", "true", "true.exe"}
    )
    if inline:
        return "Feature-bound verification cannot be an inline/no-op command; run the project's real test, check, build, or verification file."

    broad_suite = base in {"npm", "npm.cmd", "pnpm", "pnpm.cmd", "yarn", "yarn.cmd", "bun", "bun.exe", "pytest", "cargo", "go", "dotnet", "mvn", "gradle"}
    if base in {"python", "python3", "py"} and any(item in {"unittest", "pytest", "nose"} for item in args):
        broad_suite = True
    for feature_id in feature_ids:
        feature = features.get(feature_id)
        if feature is None:
            continue
        markers = _verification_markers(feature)
        if not markers:
            return f"Feature {feature_id} needs a machine-readable Verification marker such as test:tests/example.test.js or suite:unit before it can be verified."
        if any(marker.replace("\\", "/") in lowered_command for marker in markers):
            continue
        if broad_suite and any(marker.startswith(("suite", "unit", "integration", "e2e", "all")) for marker in markers):
            continue
        return f"Verification command is not bound to feature {feature_id}; include one declared marker ({', '.join(markers)}) or use its declared test file."
    return None


def _evaluate(root: Path, contract: dict) -> tuple[list[str], list[str], set[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    current = read_feature_catalog(root)
    changed_ids = set(contract.get("changedFeatureIds", []))
    protected = contract.get("protectedFeatures", {})

    for feature_id, baseline in protected.items():
        feature = current.get(feature_id)
        if feature is None:
            errors.append(f"Protected feature {feature_id} disappeared from docs/FEATURES.md.")
            continue
        for field, baseline_value in baseline.items():
            current_value = feature.invariant().get(field, "")
            if current_value != baseline_value:
                errors.append(f"Protected feature {feature_id} changed its {field}; declare it as intentionally changed or restore it.")

    for feature_id in changed_ids:
        feature = current.get(feature_id)
        if feature is None:
            errors.append(f"Changed feature {feature_id} is missing from docs/FEATURES.md.")
        elif _normalize_text(feature.status) not in ACTIVE_STATUSES:
            errors.append(f"Changed feature {feature_id} is not marked active/accepted/stable/verified.")

    baseline_deleted = set(contract.get("baselineDeletedFiles", []))
    allowed_deleted = set(contract.get("allowedDeletedFiles", []))
    unexpected_deleted = _deleted_files(root, contract.get("baselineHead")) - baseline_deleted - allowed_deleted
    if unexpected_deleted:
        errors.append("Unexpected tracked file deletion(s): " + ", ".join(sorted(unexpected_deleted)))

    for feature in current.values():
        if not _is_active(feature):
            continue
        if not feature.entry_points.strip():
            warnings.append(f"Active feature {feature.id} has no entry-point/connected-path record.")
        if not feature.verification.strip() or _normalize_text(feature.verification) in {"not yet confirmed", "待确认"}:
            warnings.append(f"Active feature {feature.id} has no usable verification entry.")

    required = _required_verification_ids(root, contract, current)
    for feature_id in sorted(required):
        feature = current.get(feature_id)
        if feature is not None and not _verification_markers(feature):
            errors.append(
                f"Required feature {feature_id} has no machine-readable Verification marker. "
                "Use a declaration such as test:tests/example.test.js or suite:unit."
            )
    return errors, warnings, required


def _verification_still_matches(root: Path, contract: dict) -> bool:
    if contract.get("state") != "verified":
        return False
    verified_tree = contract.get("verifiedIndexTree")
    verified_fingerprint = contract.get("verifiedContentFingerprint")
    if not verified_tree or not verified_fingerprint:
        return False
    try:
        if _index_tree(root) != verified_tree or _content_fingerprint(root) != verified_fingerprint:
            return False
    except GuardError:
        return False
    if _git_head(root) == contract.get("verifiedHead"):
        return True
    return _verification_is_committed(root, contract)


def _verification_is_committed(root: Path, contract: dict) -> bool:
    head = _git_head(root)
    if not head or head == contract.get("verifiedHead"):
        return False
    tree = _run_git(root, "rev-parse", "HEAD^{tree}")
    parents = _run_git(root, "rev-list", "--parents", "-n", "1", "HEAD")
    metadata = _run_git(root, "show", "-s", "--format=%an\x1f%ae\x1f%s", "HEAD")
    if tree.returncode != 0 or parents.returncode != 0 or metadata.returncode != 0:
        return False
    author_name, author_email, subject = (metadata.stdout.strip().split("\x1f", 2) + ["", "", ""])[:3]
    if author_name != CHECKPOINT_AUTHOR_NAME or author_email != CHECKPOINT_AUTHOR_EMAIL or not subject.lower().startswith("checkpoint:"):
        return False
    parent_ids = parents.stdout.strip().split()[1:]
    verified_head = contract.get("verifiedHead")
    expected_parents = [verified_head] if verified_head else []
    return tree.stdout.strip() == contract.get("verifiedIndexTree") and parent_ids == expected_parents


def _checkpoint_message(value: str | None, fallback: str) -> str:
    message = " ".join((value or fallback).split())
    if not message:
        raise GuardError("Checkpoint message must describe the saved outcome.")
    if not message.lower().startswith("checkpoint:"):
        message = "checkpoint: " + message
    if len(message) > MAX_CHECKPOINT_MESSAGE_CHARS:
        message = message[: MAX_CHECKPOINT_MESSAGE_CHARS - 3].rstrip() + "..."
    return message


def _commit_with_local_identity(root: Path, message: str) -> str:
    result = _run_git(
        root,
        "-c",
        f"user.name={CHECKPOINT_AUTHOR_NAME}",
        "-c",
        f"user.email={CHECKPOINT_AUTHOR_EMAIL}",
        "commit",
        "--no-gpg-sign",
        "-m",
        message,
    )
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or result.stdout.strip() or "Unable to create the local checkpoint.")
    head = _git_head(root)
    if not head:
        raise GuardError("Git did not report the new local checkpoint.")
    return head


def normalize_version(value: str) -> str:
    candidate = value.strip().lower()
    match = SEMVER_PATTERN.fullmatch(candidate)
    if not match:
        raise GuardError("Version must look like v1.2 or v1.2.3.")
    major, minor, patch = match.groups()
    return f"v{major}.{minor}.{patch or '0'}"


def _require_clean_version_operation(root: Path) -> str:
    contract = _read_contract(root)
    if contract:
        if contract.get("state") == "verified" and _verification_is_committed(root, contract):
            _contract_path(root).unlink(missing_ok=True)
        else:
            raise GuardError("Finish and save the current change before managing a formal version.")
    pending = _working_tree_status(root)
    if pending:
        preview = ", ".join(line[3:].strip() for line in pending[:8])
        suffix = " ..." if len(pending) > 8 else ""
        raise GuardError("The project has unsaved changes. Create a checkpoint before managing a formal version: " + preview + suffix)
    head = _git_head(root)
    if not head:
        raise GuardError("The project has no local checkpoint to mark as a formal version.")
    return head


def _require_dev_kit_checkpoint(root: Path, revision: str) -> None:
    metadata = _run_git(root, "show", "-s", "--format=%an\x1f%ae\x1f%s", revision)
    if metadata.returncode != 0:
        raise GuardError("Unable to inspect the candidate version checkpoint.")
    author_name, author_email, subject = (metadata.stdout.strip().split("\x1f", 2) + ["", "", ""])[:3]
    if author_name != CHECKPOINT_AUTHOR_NAME or author_email != CHECKPOINT_AUTHOR_EMAIL or not subject.lower().startswith("checkpoint:"):
        raise GuardError("Formal versions can only mark a verified Dev Kit checkpoint.")


def _resolve_version_target(root: Path, target: str | None, head: str) -> str:
    if not target:
        return head
    resolved = _run_git(root, "rev-parse", "--verify", f"{target}^{{commit}}")
    if resolved.returncode != 0:
        raise GuardError(f"Version target was not found: {target}")
    commit = resolved.stdout.strip()
    ancestor = _run_git(root, "merge-base", "--is-ancestor", commit, head)
    if ancestor.returncode != 0:
        raise GuardError("A historical formal version must point to a checkpoint in the current branch history.")
    return commit


def _package_version_at(root: Path, revision: str) -> str:
    package = _run_git(root, "show", f"{revision}:package.json")
    if package.returncode != 0:
        return ""
    try:
        data = json.loads(package.stdout)
    except json.JSONDecodeError as exc:
        raise GuardError(f"package.json at the selected version target is unreadable: {exc}") from exc
    return str(data.get("version", "")).strip()


def _plain_version_at(root: Path, revision: str) -> str | None:
    version = _run_git(root, "show", f"{revision}:VERSION")
    if version.returncode != 0:
        return None
    value = version.stdout.strip()
    if not value:
        raise GuardError("VERSION at the selected checkpoint is empty.")
    return value


def create_local_version(
    root: Path,
    version: str,
    message: str | None = None,
    target: str | None = None,
) -> tuple[str, str]:
    normalized = normalize_version(version)
    head = _require_clean_version_operation(root)
    target_commit = _resolve_version_target(root, target, head)
    _require_dev_kit_checkpoint(root, target_commit)
    versions_path = root / VERSIONS_RELATIVE
    if not versions_path.is_file():
        raise GuardError("docs/VERSIONS.md is required before creating a formal version.")
    versions_text = versions_path.read_text(encoding="utf-8", errors="replace")
    if not re.search(rf"(?im)^\|\s*{re.escape(normalized)}\s*\|", versions_text):
        raise GuardError(f"Record {normalized} in docs/VERSIONS.md before creating its local tag.")
    package_version = _package_version_at(root, target_commit)
    if package_version and package_version != normalized[1:]:
        raise GuardError(f"package.json version {package_version} at the selected checkpoint does not match {normalized}.")
    plain_version = _plain_version_at(root, target_commit)
    if plain_version is not None and plain_version != normalized[1:]:
        raise GuardError(f"VERSION marker {plain_version} at the selected checkpoint does not match {normalized}.")
    existing = _run_git(root, "rev-parse", "--verify", f"refs/tags/{normalized}")
    if existing.returncode == 0:
        raise GuardError(f"Local version {normalized} already exists and will not be moved or overwritten.")
    annotation = " ".join((message or f"local formal version {normalized}").split())
    created = _run_git(
        root,
        "-c",
        f"user.name={CHECKPOINT_AUTHOR_NAME}",
        "-c",
        f"user.email={CHECKPOINT_AUTHOR_EMAIL}",
        "tag",
        "--annotate",
        normalized,
        "--message",
        annotation,
        target_commit,
    )
    if created.returncode != 0:
        raise GuardError(created.stderr.strip() or created.stdout.strip() or "Unable to create the local version tag.")
    target = _run_git(root, "rev-parse", f"{normalized}^{{commit}}")
    if target.returncode != 0 or target.stdout.strip() != target_commit:
        raise GuardError("The local version tag was created but does not point to the selected verified checkpoint.")
    return normalized, target_commit


def list_local_versions(root: Path) -> list[tuple[str, str, str]]:
    result = _run_git(root, "for-each-ref", "--format=%(refname:short)\x1f%(objectname)\x1f%(subject)", "refs/tags")
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or "Unable to read local versions.")
    versions: list[tuple[tuple[int, int, int], str, str, str]] = []
    for line in result.stdout.splitlines():
        name, object_id, subject = (line.split("\x1f", 2) + ["", "", ""])[:3]
        try:
            normalized = normalize_version(name)
        except GuardError:
            continue
        major, minor, patch = (int(part) for part in normalized[1:].split("."))
        commit = _run_git(root, "rev-parse", f"{name}^{{commit}}")
        if commit.returncode == 0:
            versions.append(((major, minor, patch), normalized, commit.stdout.strip(), subject))
    versions.sort(key=lambda item: item[0], reverse=True)
    return [(name, commit, subject) for _, name, commit, subject in versions]


def _normalize_remote_url(value: str) -> str:
    normalized = value.strip().replace("\\", "/").rstrip("/")
    if normalized.lower().endswith(".git"):
        normalized = normalized[:-4]
    return normalized.lower()


def _remote_refs(root: Path, remote: str) -> dict[str, str]:
    result = _run_git(root, "ls-remote", "--heads", "--tags", remote)
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or result.stdout.strip() or f"Unable to inspect remote {remote}.")
    refs: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            refs[parts[1].strip()] = parts[0].strip()
    return refs


def publish_authorized_refs(
    root: Path,
    remote: str,
    branch: str,
    tags: Sequence[str],
    confirmed_remote_url: str,
) -> list[str]:
    """Push one exact branch and immutable formal tags after explicit user authorization."""
    head = _require_clean_version_operation(root)
    _require_dev_kit_checkpoint(root, head)
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", remote):
        raise GuardError("Use one explicit Git remote name such as origin.")
    branch_check = _run_git(root, "check-ref-format", "--branch", branch)
    if branch_check.returncode != 0:
        raise GuardError(f"Invalid branch name for guarded publishing: {branch}")
    current_branch = _run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if current_branch.returncode != 0 or current_branch.stdout.strip() != branch:
        raise GuardError(f"Guarded publishing requires the currently checked out branch {branch}.")
    branch_head = _run_git(root, "rev-parse", "--verify", f"refs/heads/{branch}")
    if branch_head.returncode != 0 or branch_head.stdout.strip() != head:
        raise GuardError("The selected branch does not point to the current verified checkpoint.")

    remote_url_result = _run_git(root, "remote", "get-url", remote)
    if remote_url_result.returncode != 0:
        raise GuardError(f"Git remote was not found: {remote}")
    actual_remote_url = remote_url_result.stdout.strip()
    if not confirmed_remote_url.strip() or _normalize_remote_url(actual_remote_url) != _normalize_remote_url(confirmed_remote_url):
        raise GuardError(
            "The confirmed remote URL does not match the configured remote. "
            f"Expected an exact confirmation for: {actual_remote_url}"
        )

    normalized_tags = [normalize_version(tag) for tag in _split_values(tags)]
    if not normalized_tags:
        raise GuardError("Guarded publishing requires at least one formal version tag.")
    versions_path = root / VERSIONS_RELATIVE
    versions_text = versions_path.read_text(encoding="utf-8", errors="replace") if versions_path.is_file() else ""
    local_targets: dict[str, str] = {}
    head_is_formal = False
    for tag in normalized_tags:
        if not re.search(rf"(?im)^\|\s*{re.escape(tag)}\s*\|", versions_text):
            raise GuardError(f"Formal version {tag} is missing from docs/VERSIONS.md.")
        object_type = _run_git(root, "cat-file", "-t", f"refs/tags/{tag}")
        if object_type.returncode != 0 or object_type.stdout.strip() != "tag":
            raise GuardError(f"{tag} must be an annotated formal tag created by the guarded version command.")
        target = _run_git(root, "rev-parse", f"refs/tags/{tag}^{{commit}}")
        if target.returncode != 0:
            raise GuardError(f"Unable to resolve local formal version {tag}.")
        target_commit = target.stdout.strip()
        _require_dev_kit_checkpoint(root, target_commit)
        ancestor = _run_git(root, "merge-base", "--is-ancestor", target_commit, head)
        if ancestor.returncode != 0:
            raise GuardError(f"Formal version {tag} is not in the current branch history.")
        local_targets[tag] = target_commit
        head_is_formal = head_is_formal or target_commit == head
    if not head_is_formal:
        raise GuardError("At least one authorized formal version tag must point to the current branch checkpoint.")

    before = _remote_refs(root, remote)
    for tag, target_commit in local_targets.items():
        remote_target = before.get(f"refs/tags/{tag}^{{}}") or before.get(f"refs/tags/{tag}")
        if remote_target and remote_target != target_commit:
            raise GuardError(f"Remote tag {tag} already exists at a different checkpoint and will not be moved.")

    refspecs = [f"refs/heads/{branch}:refs/heads/{branch}"] + [
        f"refs/tags/{tag}:refs/tags/{tag}" for tag in normalized_tags
    ]
    dry_run = _run_git(root, "push", "--dry-run", "--porcelain", "--atomic", remote, *refspecs)
    if dry_run.returncode != 0:
        raise GuardError(dry_run.stderr.strip() or dry_run.stdout.strip() or "Guarded publish dry-run failed.")
    pushed = _run_git(root, "push", "--porcelain", "--atomic", remote, *refspecs)
    if pushed.returncode != 0:
        raise GuardError(pushed.stderr.strip() or pushed.stdout.strip() or "Guarded publish failed.")

    after = _remote_refs(root, remote)
    if after.get(f"refs/heads/{branch}") != head:
        raise GuardError("Remote branch verification failed after publishing.")
    for tag, target_commit in local_targets.items():
        remote_target = after.get(f"refs/tags/{tag}^{{}}") or after.get(f"refs/tags/{tag}")
        if remote_target != target_commit:
            raise GuardError(f"Remote verification failed for formal version {tag}.")
    return [f"{remote}:{branch}", *normalized_tags]


def restore_local_version(root: Path, version: str, message: str | None = None) -> str:
    normalized = normalize_version(version)
    current_head = _require_clean_version_operation(root)
    target = _run_git(root, "rev-parse", f"refs/tags/{normalized}^{{commit}}")
    if target.returncode != 0:
        raise GuardError(f"Local version {normalized} was not found. List available versions before choosing a restore target.")
    target_commit = target.stdout.strip()
    target_tree = _run_git(root, "rev-parse", f"{target_commit}^{{tree}}")
    current_tree = _run_git(root, "rev-parse", f"{current_head}^{{tree}}")
    if target_tree.returncode != 0 or current_tree.returncode != 0:
        raise GuardError("Unable to inspect the selected version tree.")
    if target_tree.stdout.strip() == current_tree.stdout.strip():
        raise GuardError(f"The project already matches {normalized}.")
    branch = _run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode != 0 or not branch.stdout.strip():
        raise GuardError("Named-version restoration requires a normal local branch, not a detached HEAD.")
    restore_message = _checkpoint_message(message, f"restore formal version {normalized}")
    materialized = _run_git(root, "read-tree", "--reset", "-u", target_commit)
    if materialized.returncode != 0:
        _run_git(root, "read-tree", "--reset", "-u", current_head)
        raise GuardError(materialized.stderr.strip() or "Unable to materialize the selected version; the original checkout was restored.")
    try:
        keep_registry = _run_git(
            root,
            "restore",
            "--source",
            current_head,
            "--staged",
            "--worktree",
            "--",
            VERSIONS_RELATIVE.as_posix(),
        )
        if keep_registry.returncode != 0:
            raise GuardError("Unable to preserve the complete version index during restoration.")
        new_commit = _commit_with_local_identity(root, restore_message)
    except GuardError:
        _run_git(root, "read-tree", "--reset", "-u", current_head)
        raise
    differences = _run_git(root, "diff", "--name-only", target_commit, "HEAD", "--")
    allowed_difference = {VERSIONS_RELATIVE.as_posix()}
    actual_difference = {line.strip() for line in differences.stdout.splitlines() if line.strip()}
    if differences.returncode != 0 or not actual_difference.issubset(allowed_difference) or _working_tree_status(root):
        raise GuardError("The restoration checkpoint does not match the selected version apart from the preserved version index. Stop and inspect the repository.")
    return new_commit


def create_checkpoint(root: Path, message: str | None = None) -> str:
    contract = _read_contract(root)
    if not contract:
        raise GuardError("No verified current change exists to save as a local recovery point.")
    if contract.get("state") != "verified":
        raise GuardError("Complete feature regression verification before creating the local recovery point.")
    if _verification_is_committed(root, contract):
        head = _git_head(root)
        _contract_path(root).unlink(missing_ok=True)
        return head or ""
    if not _verification_still_matches(root, contract):
        raise GuardError("The project changed after verification. Reopen, recheck, and complete it again before saving a recovery point.")

    checkpoint = _commit_with_local_identity(
        root,
        _checkpoint_message(message, contract.get("objective", "verified change")),
    )
    if not _verification_is_committed(root, contract):
        raise GuardError("The new commit does not match the verified project snapshot. Keep the contract and inspect the commit before continuing.")
    _contract_path(root).unlink(missing_ok=True)
    return checkpoint


def _working_tree_status(root: Path) -> list[str]:
    result = _run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or "Unable to inspect the Git working tree.")
    return [line for line in result.stdout.splitlines() if line.strip()]


def rollback_last_checkpoint(root: Path, message: str | None = None) -> str:
    contract = _read_contract(root)
    if contract:
        if contract.get("state") == "verified" and _verification_is_committed(root, contract):
            _contract_path(root).unlink(missing_ok=True)
        else:
            raise GuardError("Finish or preserve the current change before returning to an earlier version.")

    pending = _working_tree_status(root)
    if pending:
        preview = ", ".join(line[3:].strip() for line in pending[:8])
        suffix = " ..." if len(pending) > 8 else ""
        raise GuardError(
            "The project has unsaved changes. Create a recovery point before rollback so nothing is lost: "
            + preview
            + suffix
        )

    head = _git_head(root)
    if not head:
        raise GuardError("There is no local version to return to.")
    metadata = _run_git(root, "show", "-s", "--format=%an\x1f%ae\x1f%s", head)
    if metadata.returncode != 0:
        raise GuardError("Unable to identify the latest local version.")
    author_name, author_email, subject = (metadata.stdout.strip().split("\x1f", 2) + ["", "", ""])[:3]
    if author_name != CHECKPOINT_AUTHOR_NAME or author_email != CHECKPOINT_AUTHOR_EMAIL or not subject.lower().startswith("checkpoint:"):
        raise GuardError("The latest commit was not created by the Dev Kit checkpoint flow; it will not be rolled back automatically. Keep the user's commit and ask for an explicit recovery decision.")
    parent = _run_git(root, "rev-parse", "HEAD^")
    if not head or parent.returncode != 0:
        raise GuardError("There is no earlier local version to return to.")
    parent_id = parent.stdout.strip()
    parent_tree = _run_git(root, "rev-parse", f"{parent_id}^{{tree}}")
    if parent_tree.returncode != 0:
        raise GuardError(parent_tree.stderr.strip() or "Unable to inspect the previous local version.")

    applied = _run_git(root, "revert", "--no-commit", head)
    if applied.returncode != 0:
        _run_git(root, "revert", "--abort")
        raise GuardError(
            "Git could not safely return to the previous version and restored the current one. "
            + (applied.stderr.strip() or applied.stdout.strip())
        )

    try:
        if _index_tree(root) != parent_tree.stdout.strip():
            raise GuardError("The rollback result did not exactly match the previous version.")
        if _run_git(root, "diff", "--name-only", "--").stdout.strip():
            raise GuardError("The rollback left unstaged file changes, so it was not saved.")
        checkpoint = _commit_with_local_identity(
            root,
            _checkpoint_message(message, f"return to previous version {parent_id[:8]}"),
        )
    except GuardError:
        _run_git(root, "revert", "--abort")
        raise

    committed_tree = _run_git(root, "rev-parse", "HEAD^{tree}")
    if committed_tree.returncode != 0 or committed_tree.stdout.strip() != parent_tree.stdout.strip():
        raise GuardError("The rollback commit was created, but its content does not exactly match the previous version. Inspect it before continuing.")
    return checkpoint


def start_contract(
    root: Path,
    objective: str,
    changed: Sequence[str],
    verify: Sequence[str],
    allowed_delete: Sequence[str],
    owned_paths: Sequence[str] = (),
) -> dict:
    objective = " ".join(objective.split())
    if not objective:
        raise GuardError("Objective must describe the user-visible outcome.")
    if len(objective) > 500:
        raise GuardError("Objective is too long; keep the current change contract under 500 characters.")

    existing = _read_contract(root)
    if existing:
        if existing.get("state") == "open":
            raise GuardError("A change contract is already open. Resume it or cancel it only after restoring its baseline.")
        if not _verification_is_committed(root, existing):
            raise GuardError("The previous verified change has not been saved as a local recovery point. Create its checkpoint before starting another change.")
        _contract_path(root).unlink(missing_ok=True)

    features = read_feature_catalog(root)
    changed_ids = _split_values(changed)
    verify_ids = _split_values(verify)
    invalid_changed_ids = [feature_id for feature_id in changed_ids if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", feature_id)]
    if invalid_changed_ids:
        raise GuardError("Invalid new feature ID(s): " + ", ".join(sorted(invalid_changed_ids)))
    unknown_verify_ids = set(verify_ids) - set(features)
    if unknown_verify_ids:
        raise GuardError("Unknown adjacent verification feature ID(s): " + ", ".join(sorted(unknown_verify_ids)))
    allowed_deleted = [_normalize_contract_path(root, value) for value in _split_values(allowed_delete)]
    task_owned = [_normalize_contract_path(root, value) for value in _split_values(owned_paths)]
    active = {feature_id: feature for feature_id, feature in features.items() if _is_active(feature)}
    protected = {
        feature_id: feature.invariant()
        for feature_id, feature in active.items()
        if feature_id not in changed_ids
    }
    baseline_head = _git_head(root)
    baseline_changed = sorted(_changed_files(root, baseline_head))
    contract = {
        "schemaVersion": 1,
        "state": "open",
        "objective": objective,
        "startedAt": _now(),
        "baselineHead": baseline_head,
        "baselineIndexTree": _index_tree(root),
        "baselineWorktreeFingerprint": _worktree_fingerprint(root),
        "baselineChangedFiles": baseline_changed,
        "baselinePathStates": {relative: _path_state(root, relative) for relative in baseline_changed},
        "baselineStagedFiles": sorted(_staged_files(root)),
        "baselineDeletedFiles": sorted(_deleted_files(root, baseline_head)),
        "baselineStatusState": _path_state(root, STATUS_RELATIVE.as_posix()),
        "baselineStatusContentFingerprint": _status_content_fingerprint(root),
        "changedFeatureIds": changed_ids,
        "explicitVerificationIds": verify_ids,
        "protectedFeatures": protected,
        "allowedDeletedFiles": sorted(allowed_deleted),
        "taskOwnedPaths": sorted(task_owned),
        "stagedPaths": [],
        "verificationRuns": [],
    }
    _write_contract(root, contract)
    return contract


def _clear_verification(contract: dict) -> None:
    for key in (
        "verifiedAt",
        "verifiedFeatureIds",
        "verificationEvidence",
        "verificationNotes",
        "verificationWarnings",
        "verifiedHead",
        "verifiedIndexTree",
        "verifiedContentFingerprint",
        "verifiedWorktreeFingerprint",
    ):
        contract.pop(key, None)


def stage_paths(root: Path, paths: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract or contract.get("state") != "open":
        raise GuardError("Open or reopen the current change contract before staging task files.")
    normalized = [_normalize_contract_path(root, value) for value in _split_values(paths)]
    if not normalized:
        raise GuardError("Stage at least one explicit project-relative file path.")
    for relative in normalized:
        if (root / relative).is_dir():
            raise GuardError(f"Stage explicit files, not a directory path: {relative}")

    baseline_changed = set(contract.get("baselineChangedFiles", []))
    owned = set(contract.get("taskOwnedPaths", []))
    mixed = (set(normalized) & baseline_changed) - owned
    if mixed:
        raise GuardError("These paths already contained user work at contract start; declare --own-path before editing them: " + ", ".join(sorted(mixed)))

    existing_staged = _staged_files(root)
    existing_allowed = set(contract.get("stagedPaths", [])) | owned
    existing_unexpected = existing_staged - existing_allowed
    if existing_unexpected:
        raise GuardError("The Git index already contains undeclared user work: " + ", ".join(sorted(existing_unexpected)))
    existing_protected = (set(contract.get("baselineStagedFiles", [])) & existing_staged) - owned
    if existing_protected:
        raise GuardError("Pre-existing staged user work must be unstaged before this checkpoint: " + ", ".join(sorted(existing_protected)))

    previous_tree = _index_tree(root)
    result = _run_git(root, "add", "--", *normalized)
    if result.returncode != 0:
        raise GuardError(result.stderr.strip() or "Git could not stage the declared task paths.")
    staged = _staged_files(root)
    allowed = set(normalized) | set(contract.get("stagedPaths", [])) | owned
    unexpected = staged - allowed
    if unexpected:
        _run_git(root, "read-tree", previous_tree)
        raise GuardError("The Git index contains undeclared paths; leave user work unstaged: " + ", ".join(sorted(unexpected)))
    protected_staged = (set(contract.get("baselineStagedFiles", [])) & staged) - owned
    if protected_staged:
        _run_git(root, "read-tree", previous_tree)
        raise GuardError("Pre-existing staged user work must be unstaged before this checkpoint: " + ", ".join(sorted(protected_staged)))

    contract["state"] = "open"
    contract["stagedPaths"] = sorted(staged)
    contract["verificationRuns"] = []
    _clear_verification(contract)
    _write_contract(root, contract)
    return contract


def _verification_command_error(command: Sequence[str]) -> str | None:
    if not command:
        return "Provide one executable verification command after --."
    rendered = subprocess.list2cmdline(command)
    if len(rendered) > MAX_COMMAND_CHARS:
        return f"Verification command exceeds {MAX_COMMAND_CHARS} characters."

    base = Path(command[0].strip('"\'')).name.lower()
    args = [item.lower() for item in command[1:]]
    if base in {"git", "git.exe"}:
        read_only = {"status", "diff", "show", "log", "rev-parse", "ls-files", "check-ignore", "branch", "worktree"}
        subcommand = next((item for item in args if not item.startswith("-")), "")
        if subcommand not in read_only:
            return "Verification commands may inspect Git but may not mutate Git state."
    if base in {"npm", "pnpm", "yarn", "bun"} and any(item in {"install", "i", "add", "remove", "uninstall", "publish"} for item in args[:2]):
        return "Dependency installation and publishing cannot be hidden inside a verification command."
    if base in {"pip", "pip3", "winget", "choco", "scoop"} and any(item in {"install", "upgrade", "uninstall"} for item in args[:2]):
        return "Global or dependency installation cannot be hidden inside a verification command."
    if base in {"python", "python3", "py"} and len(args) >= 2 and args[0] == "-m" and args[1] == "pip" and any(item in {"install", "uninstall"} for item in args[2:4]):
        return "Python package installation cannot be hidden inside a verification command."

    # Keep this import inside the standalone scripts directory.  The Dev Kit
    # deliberately ships no lifecycle Hook package; importing from a removed
    # ``plugins/.../hooks`` path made the no-Hook boundary misleading even
    # though the CLI happened to work because this file's directory was already
    # on ``sys.path``.
    scripts_root = Path(__file__).resolve().parent
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    from pre_tool_guard import classify_command  # type: ignore

    decision = classify_command(rendered)
    return decision.reason if decision.blocked else None


def run_verification(root: Path, feature_ids: Sequence[str], command: Sequence[str], timeout: int = 600) -> dict:
    contract = _read_contract(root)
    if not contract or contract.get("state") != "open":
        raise GuardError("Open or reopen the current change contract before running verification.")
    features = read_feature_catalog(root)
    verified_ids = _split_values(feature_ids)
    unknown = set(verified_ids) - set(features)
    if unknown:
        raise GuardError("Unknown verification feature ID(s): " + ", ".join(sorted(unknown)))
    command = list(command)
    command_error = _verification_command_error(command)
    if command_error:
        raise GuardError(command_error)
    timeout = max(1, min(int(timeout), 3600))
    before_tree, before_fingerprint = _require_staged_snapshot(root, contract)
    rendered = subprocess.list2cmdline(command)
    binding_error = _verification_binding_error(features, verified_ids, rendered, command)
    if binding_error:
        raise GuardError(binding_error)
    started = _now()
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
            errors="replace",
        )
        output = result.stdout or ""
        exit_code: int | str = result.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        exit_code = "timeout"

    snapshot_error = ""
    try:
        after_tree, after_fingerprint = _require_staged_snapshot(root, contract)
        if after_tree != before_tree or after_fingerprint != before_fingerprint:
            snapshot_error = "Project content or the Git index changed during verification."
    except GuardError as exc:
        after_tree, after_fingerprint = "", ""
        snapshot_error = str(exc)

    passed = exit_code == 0 and not snapshot_error
    run = {
        "command": rendered,
        "featureIds": sorted(verified_ids),
        "startedAt": started,
        "finishedAt": _now(),
        "exitCode": exit_code,
        "passed": passed,
        "indexTree": before_tree,
        "contentFingerprint": before_fingerprint,
    }
    runs = list(contract.get("verificationRuns", []))
    runs.append(run)
    contract["verificationRuns"] = runs[-MAX_VERIFICATION_RUNS:]
    _write_contract(root, contract)
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if not passed:
        reason = f"Verification failed with exit code {exit_code}."
        if snapshot_error:
            reason += " " + snapshot_error
        raise GuardError(reason)
    return run


def complete_contract(root: Path, verified: Sequence[str], evidence: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract:
        raise GuardError("No current change contract exists. Start one before editing.")
    if contract.get("state") != "open":
        raise GuardError("The current change contract is not open.")

    errors, warnings, required = _evaluate(root, contract)
    if _source_changed(root, contract):
        baseline_status = contract.get("baselineStatusState", "")
        current_status = _path_state(root, STATUS_RELATIVE.as_posix())
        if current_status == baseline_status:
            errors.append("Source behavior changed but docs/STATUS.md was not updated. Record the new verified state, current risks, and exactly one next action before creating a checkpoint.")
        elif _status_content_fingerprint(root) == contract.get("baselineStatusContentFingerprint", ""):
            errors.append("Source behavior changed but docs/STATUS.md only received formatting-only edits. Update meaningful milestone, verified result, risk, and next-action content before creating a checkpoint.")
        errors.extend(_status_quality_errors(root))
    if contract.get("changedFeatureIds") or _source_changed(root, contract):
        errors.extend(_template_placeholder_errors(root))
    if errors:
        raise GuardError("\n".join(errors + [f"WARNING: {item}" for item in warnings]))
    index_tree, content_fingerprint = _require_staged_snapshot(root, contract)
    successful_runs = [
        run
        for run in contract.get("verificationRuns", [])
        if run.get("passed")
        and run.get("exitCode") == 0
        and run.get("indexTree") == index_tree
        and run.get("contentFingerprint") == content_fingerprint
    ]
    actual_verified_ids = {
        feature_id
        for run in successful_runs
        for feature_id in run.get("featureIds", [])
    }
    claimed_ids = set(_split_values(verified))
    unsupported_claims = claimed_ids - actual_verified_ids
    if unsupported_claims:
        errors.append("Feature IDs were claimed without a successful recorded verification command: " + ", ".join(sorted(unsupported_claims)))
    missing = required - actual_verified_ids
    if missing:
        errors.append("Required feature verification lacks a successful recorded command for: " + ", ".join(sorted(missing)))
    if not successful_runs:
        errors.append("Run at least one verification command through feature_guard.py verify; free-form evidence text cannot seal a checkpoint.")
    notes = [" ".join(item.split()) for item in evidence if item.strip()]
    if errors:
        raise GuardError("\n".join(errors + [f"WARNING: {item}" for item in warnings]))

    evidence_items = [
        f"exit 0: {run['command']} [features: {', '.join(run.get('featureIds', [])) or 'none'}]"
        for run in successful_runs
    ]

    contract.update(
        {
            "state": "verified",
            "verifiedAt": _now(),
            "verifiedFeatureIds": sorted(actual_verified_ids),
            "verificationEvidence": evidence_items[-MAX_VERIFICATION_RUNS:],
            "verificationNotes": notes[:20],
            "verificationWarnings": warnings[:20],
            "verifiedHead": _git_head(root),
            "verifiedIndexTree": index_tree,
            "verifiedContentFingerprint": content_fingerprint,
            "verifiedWorktreeFingerprint": content_fingerprint,
        }
    )
    _write_contract(root, contract)
    return contract


def reopen_contract(root: Path) -> dict:
    contract = _read_contract(root)
    if not contract:
        raise GuardError("No current change contract exists.")
    contract["state"] = "open"
    contract["verificationRuns"] = []
    _clear_verification(contract)
    _write_contract(root, contract)
    return contract


def allow_deletions(root: Path, paths: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract or contract.get("state") != "open":
        raise GuardError("Open a current change contract before declaring intentional file deletions.")
    allowed = set(contract.get("allowedDeletedFiles", []))
    allowed.update(_normalize_contract_path(root, value) for value in _split_values(paths))
    contract["allowedDeletedFiles"] = sorted(allowed)
    _write_contract(root, contract)
    return contract


def declare_changed_features(root: Path, feature_ids: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract or contract.get("state") != "open":
        raise GuardError("Open or reopen the current change contract before declaring additional changed features.")
    declared = _split_values(feature_ids)
    if not declared:
        raise GuardError("Declare at least one feature ID that the current task now intends to change.")
    invalid = [feature_id for feature_id in declared if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", feature_id)]
    if invalid:
        raise GuardError("Invalid changed feature ID(s): " + ", ".join(sorted(invalid)))

    changed = set(contract.get("changedFeatureIds", []))
    changed.update(declared)
    contract["changedFeatureIds"] = sorted(changed)
    contract["explicitVerificationIds"] = sorted(set(contract.get("explicitVerificationIds", [])) - changed)
    protected = dict(contract.get("protectedFeatures", {}))
    for feature_id in declared:
        protected.pop(feature_id, None)
    contract["protectedFeatures"] = protected
    _write_contract(root, contract)
    return contract


def cancel_contract(root: Path) -> None:
    contract = _read_contract(root)
    if not contract:
        return
    if _new_changes_exist(root, contract):
        raise GuardError("Cannot cancel while the repository differs from the contract baseline. Preserve, commit, or restore the work first.")
    _contract_path(root).unlink(missing_ok=True)


def close_contract(root: Path) -> None:
    contract = _read_contract(root)
    if not contract:
        return
    if contract.get("state") != "verified":
        raise GuardError("Cannot close an open change contract. Complete its regression verification first.")
    if not _verification_still_matches(root, contract):
        raise GuardError("Cannot close because the project changed after verification. Reopen, recheck, and complete it again.")
    if not _verification_is_committed(root, contract):
        raise GuardError("Cannot close until the verified snapshot has a local checkpoint commit.")
    _contract_path(root).unlink(missing_ok=True)


def _contract_summary(contract: dict) -> str:
    changed = ", ".join(contract.get("changedFeatureIds", [])) or "none declared"
    required = ", ".join(contract.get("explicitVerificationIds", [])) or "risk-derived at completion"
    staged = len(contract.get("stagedPaths", []))
    successful_runs = sum(1 for run in contract.get("verificationRuns", []) if run.get("passed"))
    return _clip_text(
        f"Current change guard is {contract.get('state')}: {contract.get('objective')}. "
        f"Intentionally changed feature IDs: {changed}. Required/adjacent verification: {required}. "
        f"Guard-staged paths: {staged}; successful recorded verification commands: {successful_runs}. "
        "Read the FEATURES index and relevant docs/features domain maps before editing and keep protected behavior intact.",
        900,
    )


def _clip_text(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _status_recovery_summary(root: Path) -> str:
    path = root / STATUS_RELATIVE
    if not path.is_file():
        return "docs/STATUS.md is missing. Rebuild it from code, tests, Git, and the current request."

    text = path.read_text(encoding="utf-8", errors="replace")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current = _normalize_text(line[3:])
            sections.setdefault(current, [line])
        elif current is not None:
            sections[current].append(line)

    preferred = (
        "milestone", "current milestone", "里程碑", "当前里程碑",
        "working state", "工作状态",
        "current risks", "risks", "当前风险",
        "current limitations", "limitations", "当前限制",
        "blockers", "阻塞",
        "verified", "已验证",
    )
    selected: list[str] = []
    seen: set[str] = set()
    for name in preferred:
        normalized = _normalize_text(name)
        if normalized in sections and normalized not in seen:
            content = "\n".join(sections[normalized]).strip()
            if content:
                selected.append(_clip_text(content, 500))
                seen.add(normalized)

    next_action = ""
    for name in ("next action", "next actions", "下一步"):
        normalized = _normalize_text(name)
        if normalized in sections:
            next_action = _clip_text("\n".join(sections[normalized]).strip(), RECOVERY_NEXT_ACTION_MAX_CHARS)
            if next_action:
                break

    if selected or next_action:
        separator_cost = 2 if selected and next_action else 0
        other_budget = max(0, RECOVERY_STATUS_MAX_CHARS - len(next_action) - separator_cost)
        other = _clip_text("\n\n".join(selected), other_budget) if selected and other_budget else ""
        return "\n\n".join(item for item in (other, next_action) if item)

    compact = "\n".join(line for line in text.splitlines() if line.strip())
    return _clip_text(compact, RECOVERY_STATUS_MAX_CHARS)


def _git_recovery_summary(root: Path) -> tuple[str, str]:
    branch_result = _run_git(root, "branch", "--show-current")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    if not branch:
        head_result = _run_git(root, "rev-parse", "--short", "HEAD")
        branch = "detached at " + head_result.stdout.strip() if head_result.returncode == 0 else "unknown"

    status_result = _run_git(root, "status", "--short")
    if status_result.returncode == 0:
        changed_count = len([line for line in status_result.stdout.splitlines() if line.strip()])
        working_tree = "clean" if changed_count == 0 else f"{changed_count} changed entr{'y' if changed_count == 1 else 'ies'}"
    else:
        working_tree = "unknown"

    checkpoint_result = _run_git(root, "log", "-1", "--pretty=format:%h %s")
    checkpoint = checkpoint_result.stdout.strip() if checkpoint_result.returncode == 0 else "none"
    return f"branch {branch}; working tree {working_tree}", checkpoint


def _recovery_packet(root: Path, contract: dict | None) -> str:
    contract_context = _contract_summary(contract) if contract else "No current change contract is open. Start one before editing accepted project behavior."
    git_state, checkpoint = _git_recovery_summary(root)
    packet = (
        "Codex Dev Kit recovery packet (current facts only; do not search old chats first):\n"
        f"Change guard: {contract_context}\n"
        f"Git: {git_state}. Latest checkpoint: {checkpoint}.\n"
        f"STATUS (capped):\n{_status_recovery_summary(root)}\n"
        "Always read AGENTS.md, docs/PROJECT.md, docs/FEATURES.md, and the relevant docs/features domain maps before changing behavior. "
        "Read architecture, ADRs, roadmap, or runbook only when relevant. Do not create permanent chat or development logs."
    )
    return _clip_text(packet, RECOVERY_PACKET_MAX_CHARS)


def _deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )


def _is_guard_command(command: str) -> bool:
    if _has_shell_control(command):
        return False
    segments = _shell_segments(command)
    if len(segments) != 1:
        return False
    tokens = segments[0]
    script_index = next(
        (
            index
            for index, token in enumerate(tokens)
            if token.strip('"\'').replace("\\", "/").lower().endswith("/feature_guard.py")
            or token.strip('"\'').lower() == "feature_guard.py"
        ),
        None,
    )
    if script_index is None or script_index + 1 >= len(tokens):
        return False
    return tokens[script_index + 1].lower() in {
        "start", "status", "stage", "verify", "complete", "checkpoint", "rollback",
        "version", "versions", "restore-version", "publish", "reopen", "allow-delete", "cancel", "close",
    }


def _shell_segments(command: str) -> list[list[str]]:
    if "\n" in command or "\r" in command:
        return []
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except (TypeError, ValueError):
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and set(token) <= {";", "&", "|", "<", ">"}:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _has_shell_control(command: str) -> bool:
    if "\n" in command or "\r" in command:
        return True
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return any(token and set(token) <= {";", "&", "|", "<", ">"} for token in lexer)
    except (TypeError, ValueError):
        return True


def _git_subcommand_and_args(tokens: Sequence[str]) -> tuple[str | None, list[str]]:
    if not tokens or Path(tokens[0].strip('"\'')).name.lower() not in {"git", "git.exe"}:
        return None, []
    index = 1
    while index < len(tokens):
        lower = tokens[index].lower()
        if lower in {"-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if lower.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            index += 1
            continue
        if lower.startswith("-"):
            index += 1
            continue
        return lower, list(tokens[index + 1 :])
    return None, []


def _git_subcommand(tokens: Sequence[str]) -> str | None:
    return _git_subcommand_and_args(tokens)[0]


def _has_git_subcommand(command: str, expected: str) -> bool:
    return any(_git_subcommand(segment) == expected for segment in _shell_segments(command))


def _looks_like_mutation(command: str) -> bool:
    patterns = [
        r"(?i)\bgit(?:\.exe)?(?:\s+-[Cc]\s+\S+|\s+-c\s+\S+)*\s+(?:add|commit|reset|rm|mv|update-index)\b",
        r"(?i)\b(?:npm|pnpm|yarn|bun)\s+(?:install|add|remove|uninstall)\b",
        r"(?i)\b(?:pip|pip3|poetry|uv)\s+(?:install|add|remove|uninstall)\b",
        r"(?i)\b(?:cargo|dotnet)\s+(?:add|remove)\b",
        r"(?i)\b(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|Remove-Item|New-Item)\b",
        r"(?i)(?:^|[;&|]\s*)(?:sed\s+-i|perl\s+-pi|rm\b|mv\b|cp\b|mkdir\b|touch\b)",
        r"(?<![<>=])>(?![>=])",
    ]
    return any(re.search(pattern, command) for pattern in patterns)


def hook_main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        return 0
    root = _resolve_project_root(Path(payload.get("cwd") or Path.cwd()), require_managed=True)
    if root is None:
        return 0
    try:
        contract = _read_contract(root)
    except GuardError as exc:
        event = payload.get("hook_event_name")
        if event == "PreToolUse":
            _deny(str(exc))
        elif event == "Stop" and not payload.get("stop_hook_active"):
            json.dump({"decision": "block", "reason": str(exc)}, sys.stdout, ensure_ascii=False)
        return 0

    event = payload.get("hook_event_name")
    if event == "SessionStart":
        json.dump(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": _recovery_packet(root, contract)}},
            sys.stdout,
            ensure_ascii=False,
        )
        return 0

    if event == "PreToolUse":
        tool_name = payload.get("tool_name")
        tool_input = payload.get("tool_input") or {}
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if isinstance(command, list):
            command = " ".join(str(part) for part in command)
        if not isinstance(command, str):
            command = ""

        normalized_tool_name = str(tool_name or "").lower()
        is_file_edit = normalized_tool_name in {"apply_patch", "edit", "write"}
        is_commit = tool_name == "Bash" and _has_git_subcommand(command, "commit")
        is_revert = tool_name == "Bash" and _has_git_subcommand(command, "revert")
        is_mutation = is_file_edit or (tool_name == "Bash" and (_looks_like_mutation(command) or is_commit))
        if tool_name == "Bash" and _is_guard_command(command):
            return 0
        if tool_name == "Bash" and _has_git_subcommand(command, "add"):
            _deny("Do not run raw git add in a managed project. Stage explicit task files through feature_guard.py stage so pre-existing user work cannot enter the checkpoint.")
            return 0
        if is_commit:
            _deny("Do not run raw git commit in a managed project. Use feature_guard.py checkpoint after verification so the exact verified snapshot is saved with a local recovery identity.")
            return 0
        if is_revert:
            _deny("Do not run raw git revert for a beginner-managed rollback. Use feature_guard.py rollback so unsaved work is protected and the previous version remains recoverable.")
            return 0
        if not is_mutation:
            return 0
        if not contract:
            _deny("Start the Dev Kit current change contract before modifying this existing project. This records which accepted features must survive the change.")
            return 0
        if contract.get("state") == "verified":
            _deny("The current change was already sealed for verification. Run feature_guard.py reopen before making another edit, then verify again.")
            return 0
        return 0

    if event == "Stop":
        if not contract:
            return 0
        if payload.get("stop_hook_active"):
            return 0
        if contract.get("state") != "verified":
            json.dump(
                {
                    "decision": "block",
                    "reason": "Do not finish yet. The current change contract is still open. Compare the diff with docs/FEATURES.md, run the required old and new behavior checks, then complete the feature guard with concise evidence.",
                },
                sys.stdout,
                ensure_ascii=False,
            )
        elif not _verification_still_matches(root, contract):
            json.dump(
                {
                    "decision": "block",
                    "reason": "Do not finish yet. Files changed after the recorded regression verification. Reopen the feature guard, recheck affected behavior, and complete it again.",
                },
                sys.stdout,
                ensure_ascii=False,
            )
        elif not _verification_is_committed(root, contract):
            json.dump(
                {
                    "decision": "block",
                    "reason": "Do not finish yet. The verified change has not been saved as a local recovery point. Run feature_guard.py checkpoint --root . --message \"checkpoint: <outcome>\"; it uses a one-time local identity and does not create a new branch.",
                },
                sys.stdout,
                ensure_ascii=False,
            )
        return 0

    if event == "SessionEnd":
        if contract and _verification_still_matches(root, contract) and _verification_is_committed(root, contract):
            _contract_path(root).unlink(missing_ok=True)
        return 0
    return 0


def _print_status(root: Path, contract: dict | None, json_output: bool) -> None:
    if json_output:
        json.dump(contract or {"state": "none", "root": str(root)}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return
    if not contract:
        print("No current change contract.")
        return
    print(_contract_summary(contract))
    errors, warnings, required = _evaluate(root, contract)
    if required:
        print("Required verification IDs: " + ", ".join(sorted(required)))
    for item in errors:
        print("ERROR: " + item)
    for item in warnings:
        print("WARNING: " + item)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start or replace a verified current change contract")
    start.add_argument("--root", default=".")
    start.add_argument("--objective", required=True)
    start.add_argument("--change", action="append", default=[])
    start.add_argument("--verify", action="append", default=[])
    start.add_argument("--allow-delete", action="append", default=[])
    start.add_argument("--own-path", action="append", default=[])

    status = subparsers.add_parser("status", help="Inspect the current contract")
    status.add_argument("--root", default=".")
    status.add_argument("--json", action="store_true")

    stage = subparsers.add_parser("stage", help="Stage only explicit task-owned file paths")
    stage.add_argument("--root", default=".")
    stage.add_argument("--path", action="append", required=True)

    declare_change = subparsers.add_parser("declare-change", help="Promote an adjacent feature to an intentional current change")
    declare_change.add_argument("--root", default=".")
    declare_change.add_argument("--change", action="append", required=True)

    verify = subparsers.add_parser("verify", help="Run and bind one verification command to the staged snapshot")
    verify.add_argument("--root", default=".")
    verify.add_argument("--feature", action="append", default=[])
    verify.add_argument("--timeout", type=int, default=600)
    verify.add_argument("verification_command", nargs=argparse.REMAINDER)

    complete = subparsers.add_parser("complete", help="Seal the current contract after regression checks")
    complete.add_argument("--root", default=".")
    complete.add_argument("--verified", action="append", default=[])
    complete.add_argument("--evidence", action="append", default=[])

    checkpoint = subparsers.add_parser("checkpoint", help="Save the exact verified snapshot as a local recovery point")
    checkpoint.add_argument("--root", default=".")
    checkpoint.add_argument("--message")

    rollback = subparsers.add_parser("rollback", help="Return to the previous committed version with a new reversible checkpoint")
    rollback.add_argument("--root", default=".")
    rollback.add_argument("--message")

    version = subparsers.add_parser("version", help="Mark a verified checkpoint as a local formal version")
    version.add_argument("--root", default=".")
    version.add_argument("--name", required=True)
    version.add_argument("--message")
    version.add_argument("--target", help="Optional historical checkpoint in the current branch history")

    versions = subparsers.add_parser("versions", help="List local formal versions without changing the project")
    versions.add_argument("--root", default=".")

    restore_version = subparsers.add_parser("restore-version", help="Restore a named local version with a new reversible checkpoint")
    restore_version.add_argument("--root", default=".")
    restore_version.add_argument("--name", required=True)
    restore_version.add_argument("--message")

    publish = subparsers.add_parser("publish", help="Push one explicitly authorized branch and formal version set")
    publish.add_argument("--root", default=".")
    publish.add_argument("--remote", required=True)
    publish.add_argument("--branch", required=True)
    publish.add_argument("--tag", action="append", required=True)
    publish.add_argument("--confirm-remote-url", required=True)

    reopen = subparsers.add_parser("reopen", help="Reopen a verified contract before more edits")
    reopen.add_argument("--root", default=".")

    allow_delete = subparsers.add_parser("allow-delete", help="Declare an intentional tracked file deletion")
    allow_delete.add_argument("--root", default=".")
    allow_delete.add_argument("--path", action="append", required=True)

    cancel = subparsers.add_parser("cancel", help="Remove a contract only when its baseline is untouched")
    cancel.add_argument("--root", default=".")

    close = subparsers.add_parser("close", help="Remove a verified contract only when verification still matches")
    close.add_argument("--root", default=".")

    subparsers.add_parser("hook", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.command == "hook":
        return hook_main()

    try:
        root = _require_root(args.root)
        if args.command == "start":
            contract = start_contract(root, args.objective, args.change, args.verify, args.allow_delete, args.own_path)
            print(_contract_summary(contract))
        elif args.command == "status":
            _print_status(root, _read_contract(root), args.json)
        elif args.command == "stage":
            contract = stage_paths(root, args.path)
            print("Guard-staged paths: " + ", ".join(contract.get("stagedPaths", [])))
        elif args.command == "declare-change":
            contract = declare_changed_features(root, args.change)
            print("Intentionally changed feature IDs: " + ", ".join(contract.get("changedFeatureIds", [])))
        elif args.command == "verify":
            command = list(args.verification_command)
            if command[:1] == ["--"]:
                command = command[1:]
            run = run_verification(root, args.feature, command, args.timeout)
            print("Recorded verification: " + run["command"])
        elif args.command == "complete":
            contract = complete_contract(root, args.verified, args.evidence)
            print("Feature guard verified. Evidence: " + "; ".join(contract.get("verificationEvidence", [])))
        elif args.command == "checkpoint":
            checkpoint_id = create_checkpoint(root, args.message)
            print(f"Local recovery point created: {checkpoint_id[:12]}")
        elif args.command == "rollback":
            checkpoint_id = rollback_last_checkpoint(root, args.message)
            print(f"Returned to the previous version with recovery point: {checkpoint_id[:12]}")
        elif args.command == "version":
            version_name, checkpoint_id = create_local_version(root, args.name, args.message, args.target)
            print(f"Local formal version created: {version_name} -> {checkpoint_id[:12]}")
        elif args.command == "versions":
            available = list_local_versions(root)
            if not available:
                print("No local formal versions.")
            for version_name, checkpoint_id, subject in available:
                print(f"{version_name}\t{checkpoint_id[:12]}\t{subject}")
        elif args.command == "restore-version":
            checkpoint_id = restore_local_version(root, args.name, args.message)
            print(f"Restored {normalize_version(args.name)} with recovery point: {checkpoint_id[:12]}")
        elif args.command == "publish":
            published = publish_authorized_refs(root, args.remote, args.branch, args.tag, args.confirm_remote_url)
            print("Guarded remote publish verified: " + ", ".join(published))
        elif args.command == "reopen":
            print(_contract_summary(reopen_contract(root)))
        elif args.command == "allow-delete":
            contract = allow_deletions(root, args.path)
            print("Allowed tracked deletions: " + ", ".join(contract.get("allowedDeletedFiles", [])))
        elif args.command == "cancel":
            cancel_contract(root)
            print("Current change contract removed.")
        elif args.command == "close":
            close_contract(root)
            print("Verified current change contract closed.")
    except GuardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
