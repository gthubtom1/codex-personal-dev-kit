#!/usr/bin/env python3
"""Protect accepted project behavior while Codex changes an existing project."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


CONTRACT_RELATIVE = Path(".codex/current-change.json")
FEATURE_MAP_RELATIVE = Path("docs/FEATURES.md")
STATUS_RELATIVE = Path("docs/STATUS.md")
PROJECT_CONFIG_RELATIVE = Path(".codex/config.toml")
RECOVERY_STATUS_MAX_CHARS = 1600
RECOVERY_PACKET_MAX_CHARS = 3600
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java",
    ".js", ".jsx", ".kt", ".php", ".py", ".rb", ".rs", ".scss", ".swift", ".ts",
    ".tsx", ".vue",
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


def read_feature_map(path: Path) -> dict[str, Feature]:
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
        raise GuardError("docs/FEATURES.md needs a Markdown table with an ID column.")

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
            raise GuardError(f"Duplicate feature ID in docs/FEATURES.md: {feature_id}")
        features[feature_id] = Feature(
            id=feature_id,
            capability=values.get("capability", ""),
            entry_points=values.get("entry_points", ""),
            expected_result=values.get("expected_result", ""),
            verification=values.get("verification", ""),
            criticality=values.get("criticality", ""),
            status=values.get("status", ""),
        )
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


def _required_verification_ids(root: Path, contract: dict, current: dict[str, Feature]) -> set[str]:
    required = set(contract.get("explicitVerificationIds", []))
    required.update(feature_id for feature_id in contract.get("changedFeatureIds", []) if feature_id in current and _is_active(current[feature_id]))
    if _source_changed(root, contract):
        required.update(feature.id for feature in current.values() if _is_active(feature) and _is_critical(feature))
    return required


def _evaluate(root: Path, contract: dict) -> tuple[list[str], list[str], set[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    current = read_feature_map(root / FEATURE_MAP_RELATIVE)
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

    return errors, warnings, _required_verification_ids(root, contract, current)


def _verification_still_matches(root: Path, contract: dict) -> bool:
    if contract.get("state") != "verified":
        return False
    current_fingerprint = _worktree_fingerprint(root)
    if current_fingerprint == contract.get("verifiedWorktreeFingerprint"):
        return True
    return (
        current_fingerprint == contract.get("baselineWorktreeFingerprint")
        and _git_head(root) != contract.get("baselineHead")
    )


def start_contract(root: Path, objective: str, changed: Sequence[str], verify: Sequence[str], allowed_delete: Sequence[str]) -> dict:
    objective = " ".join(objective.split())
    if not objective:
        raise GuardError("Objective must describe the user-visible outcome.")
    if len(objective) > 500:
        raise GuardError("Objective is too long; keep the current change contract under 500 characters.")

    existing = _read_contract(root)
    if existing and existing.get("state") == "open":
        raise GuardError("A change contract is already open. Resume it or cancel it only after restoring its baseline.")

    features = read_feature_map(root / FEATURE_MAP_RELATIVE)
    changed_ids = _split_values(changed)
    verify_ids = _split_values(verify)
    allowed_deleted = [value.replace("\\", "/").lstrip("./") for value in _split_values(allowed_delete)]
    active = {feature_id: feature for feature_id, feature in features.items() if _is_active(feature)}
    protected = {
        feature_id: feature.invariant()
        for feature_id, feature in active.items()
        if feature_id not in changed_ids
    }
    baseline_head = _git_head(root)
    contract = {
        "schemaVersion": 1,
        "state": "open",
        "objective": objective,
        "startedAt": _now(),
        "baselineHead": baseline_head,
        "baselineWorktreeFingerprint": _worktree_fingerprint(root),
        "baselineChangedFiles": sorted(_changed_files(root, baseline_head)),
        "baselineDeletedFiles": sorted(_deleted_files(root, baseline_head)),
        "changedFeatureIds": changed_ids,
        "explicitVerificationIds": verify_ids,
        "protectedFeatures": protected,
        "allowedDeletedFiles": sorted(allowed_deleted),
    }
    _write_contract(root, contract)
    return contract


def complete_contract(root: Path, verified: Sequence[str], evidence: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract:
        raise GuardError("No current change contract exists. Start one before editing.")
    if contract.get("state") not in {"open", "verified"}:
        raise GuardError("The current change contract is not open.")

    errors, warnings, required = _evaluate(root, contract)
    verified_ids = set(_split_values(verified))
    missing = required - verified_ids
    if missing:
        errors.append("Required feature verification was not recorded for: " + ", ".join(sorted(missing)))
    evidence_items = [" ".join(item.split()) for item in evidence if item.strip()]
    if _new_changes_exist(root, contract) and not evidence_items:
        errors.append("Record at least one test, build, browser, API, or repeatable manual verification result.")
    if errors:
        raise GuardError("\n".join(errors + [f"WARNING: {item}" for item in warnings]))

    contract.update(
        {
            "state": "verified",
            "verifiedAt": _now(),
            "verifiedFeatureIds": sorted(verified_ids),
            "verificationEvidence": evidence_items[:20],
            "verificationWarnings": warnings[:20],
            "verifiedHead": _git_head(root),
            "verifiedWorktreeFingerprint": _worktree_fingerprint(root),
        }
    )
    _write_contract(root, contract)
    return contract


def reopen_contract(root: Path) -> dict:
    contract = _read_contract(root)
    if not contract:
        raise GuardError("No current change contract exists.")
    contract["state"] = "open"
    for key in ("verifiedAt", "verifiedFeatureIds", "verificationEvidence", "verificationWarnings", "verifiedHead", "verifiedWorktreeFingerprint"):
        contract.pop(key, None)
    _write_contract(root, contract)
    return contract


def allow_deletions(root: Path, paths: Sequence[str]) -> dict:
    contract = _read_contract(root)
    if not contract or contract.get("state") != "open":
        raise GuardError("Open a current change contract before declaring intentional file deletions.")
    allowed = set(contract.get("allowedDeletedFiles", []))
    allowed.update(value.replace("\\", "/").lstrip("./") for value in _split_values(paths))
    contract["allowedDeletedFiles"] = sorted(allowed)
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
    _contract_path(root).unlink(missing_ok=True)


def _contract_summary(contract: dict) -> str:
    changed = ", ".join(contract.get("changedFeatureIds", [])) or "none declared"
    required = ", ".join(contract.get("explicitVerificationIds", [])) or "risk-derived at completion"
    return (
        f"Current change guard is {contract.get('state')}: {contract.get('objective')}. "
        f"Intentionally changed feature IDs: {changed}. Required/adjacent verification: {required}. "
        "Read docs/FEATURES.md before editing and keep protected behavior intact."
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
        "next action", "next actions", "下一步",
        "verified", "已验证",
    )
    selected: list[str] = []
    seen: set[str] = set()
    for name in preferred:
        normalized = _normalize_text(name)
        if normalized in sections and normalized not in seen:
            content = "\n".join(sections[normalized]).strip()
            if content:
                selected.append(_clip_text(content, 600))
                seen.add(normalized)

    if selected:
        return _clip_text("\n\n".join(selected), RECOVERY_STATUS_MAX_CHARS)

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
        "Always read AGENTS.md, docs/PROJECT.md, and docs/FEATURES.md before changing behavior. "
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
    return "feature_guard.py" in command and re.search(r"\b(start|status|complete|reopen|allow-delete|cancel|close)\b", command) is not None


def _is_git_commit(command: str) -> bool:
    return re.search(r"(?i)(?:^|[;&|]\s*)git(?:\.exe)?(?:\s+-[Cc]\s+\S+|\s+-c\s+\S+)*\s+commit\b", command) is not None


def _looks_like_mutation(command: str) -> bool:
    patterns = [
        r"(?i)\bgit(?:\.exe)?\s+(?:add|commit)\b",
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

        is_patch = tool_name == "apply_patch"
        is_commit = tool_name == "Bash" and _is_git_commit(command)
        is_mutation = is_patch or (tool_name == "Bash" and (_looks_like_mutation(command) or is_commit))
        if tool_name == "Bash" and _is_guard_command(command):
            return 0
        if not is_mutation:
            return 0
        if not contract:
            _deny("Start the Dev Kit current change contract before modifying this existing project. This records which accepted features must survive the change.")
            return 0
        if contract.get("state") == "verified" and not is_commit:
            _deny("The current change was already sealed for verification. Run feature_guard.py reopen before making another edit, then verify again.")
            return 0
        if is_commit:
            if contract.get("state") != "verified":
                _deny("Complete feature regression verification before creating the checkpoint commit.")
            elif not _verification_still_matches(root, contract):
                _deny("The project changed after feature verification. Reopen and complete the current change contract again before committing.")
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
        return 0

    if event == "SessionEnd":
        if contract and _verification_still_matches(root, contract):
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

    status = subparsers.add_parser("status", help="Inspect the current contract")
    status.add_argument("--root", default=".")
    status.add_argument("--json", action="store_true")

    complete = subparsers.add_parser("complete", help="Seal the current contract after regression checks")
    complete.add_argument("--root", default=".")
    complete.add_argument("--verified", action="append", default=[])
    complete.add_argument("--evidence", action="append", default=[])

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
            contract = start_contract(root, args.objective, args.change, args.verify, args.allow_delete)
            print(_contract_summary(contract))
        elif args.command == "status":
            _print_status(root, _read_contract(root), args.json)
        elif args.command == "complete":
            contract = complete_contract(root, args.verified, args.evidence)
            print("Feature guard verified. Evidence: " + "; ".join(contract.get("verificationEvidence", [])))
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
