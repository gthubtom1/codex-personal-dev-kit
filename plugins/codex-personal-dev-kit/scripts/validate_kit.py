#!/usr/bin/env python3
"""Cross-platform structural checks for Codex Personal Dev Kit."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


SKILLS = {
    "codex-development-assistant",
    "onboard-codex-project",
    "prepare-codex-goal",
    "orchestrate-codex-team",
    "codex-safe-development",
    "manage-project-continuity",
    "research-and-reuse",
    "integrate-codex-projects",
    "audit-codex-kit",
}

def _unit_test_timeout_seconds() -> int:
    # The guard suite creates many real temporary repositories and full
    # contract cycles; 300 seconds started failing healthy runs once the
    # release-review and staging-protection tests landed.
    raw = os.environ.get("CODEX_DEV_KIT_TEST_TIMEOUT_SECONDS", "900")
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 900


UNIT_TEST_TIMEOUT_SECONDS = _unit_test_timeout_seconds()


def _check_obsolete_artifacts(kit_root: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    obsolete_paths = [
        repo_root / ".agents/plugins/marketplace.json",
        kit_root / ".codex-plugin",
        kit_root / "hooks",
        kit_root / "assets/project-template/.codex/hooks.json",
        kit_root / "assets/global-profile/rules",
    ]
    for path in obsolete_paths:
        if path.exists():
            errors.append(f"Obsolete Plugin/Hook/Rules artifact remains: {path}")
    return errors


def _check_required_files(kit_root: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    version_path = repo_root / "VERSION"
    if not version_path.is_file() or not version_path.read_text(encoding="utf-8").strip():
        errors.append(f"Missing standalone VERSION marker: {version_path}")
    for relative in (
        "scripts/feature_guard.py",
        "scripts/next_step.py",
        "scripts/pre_tool_guard.py",
        "scripts/resolve-skill.ps1",
        "scripts/audit_project.py",
        "scripts/merge-codex-config.ps1",
        "scripts/bootstrap/resolve-codex-cli.ps1",
        "assets/project-template/docs/INDEX.md",
        "assets/project-template/docs/VERSIONS.md",
        "assets/project-template/docs/adr/INDEX.md",
        "assets/workspace-template/.codex/config.toml",
    ):
        if not (kit_root / relative).is_file():
            errors.append(f"Missing required runtime file: {relative}")
    for relative in ("LICENSE", "THIRD_PARTY_NOTICES.md", "docs/INDEX.md", "docs/RESTORE.md", "docs/VERSIONS.md"):
        if not (repo_root / relative).is_file():
            errors.append(f"Missing Dev Kit distribution document: {repo_root / relative}")
    return errors


def _check_agents_templates(kit_root: Path) -> list[str]:
    errors: list[str] = []
    legacy_agents = list((kit_root / "assets/global-profile/agents").glob("codex-kit-*.toml"))
    if legacy_agents:
        errors.append("Standalone mode must not ship required custom agent files: " + ", ".join(path.name for path in legacy_agents))
    standalone_agents = kit_root / "assets/standalone/AGENTS.md"
    standalone_agents_text = standalone_agents.read_text(encoding="utf-8") if standalone_agents.is_file() else ""
    if not standalone_agents.is_file() or "{{WORKSPACE_AGENTS_PATH}}" not in standalone_agents_text:
        errors.append("Short standalone AGENTS template must point to the detailed mother-folder AGENTS.md")
    elif "{{CODEX_HOME}}" not in standalone_agents_text:
        errors.append("Short standalone AGENTS template must resolve Skill paths from the selected Codex home")
    elif not (
        "never prepend `.system`" in standalone_agents_text
        or "不要在 `skills` 和 Skill 名称之间擅自插入 `.system`" in standalone_agents_text
    ):
        errors.append("Short standalone AGENTS template must define exact Skill path resolution")
    workspace_agents = kit_root / "assets/workspace-template/AGENTS.md"
    workspace_agents_text = workspace_agents.read_text(encoding="utf-8") if workspace_agents.is_file() else ""
    required_workspace_tokens = {
        "{{WORKSPACE_NAME}}",
        "{{WORKSPACE_ROOT}}",
        "{{DEV_KIT_SKILLS_ROOT}}",
        "{{CODEX_HOME}}",
    }
    if not workspace_agents.is_file():
        errors.append("Missing detailed mother-folder AGENTS template")
    else:
        missing_tokens = sorted(required_workspace_tokens - set(re.findall(r"\{\{[^}]+\}\}", workspace_agents_text)))
        if missing_tokens:
            errors.append("Detailed AGENTS template is missing portable tokens: " + ", ".join(missing_tokens))
        for hardcoded in (r"D:\开发", r"C:\Users\Administrator"):
            if hardcoded in workspace_agents_text:
                errors.append(f"Detailed AGENTS template contains a machine-specific path: {hardcoded}")
        for heading in ("## 1. 用户合同", "## 4. Skill 调度总表", "## 8. Git、检查点和回退（用户无需操作）", "## 12. Codex 桌面高级设置的零基础规则"):
            if heading not in workspace_agents_text:
                errors.append(f"Detailed AGENTS template is missing canonical section: {heading}")
    return errors


def _check_config_templates(kit_root: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    for config_path in (
        repo_root / ".codex/config.toml",
        kit_root / "assets/global-profile/config.fragment.toml",
        kit_root / "assets/workspace-template/.codex/config.toml",
        kit_root / "assets/project-template/.codex/config.toml",
    ):
        if not config_path.is_file():
            errors.append(f"Missing native Codex config template: {config_path}")
            continue
        config_text = config_path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\s*\[agents\]\s*$", config_text) or re.search(
            r"(?m)^\s*(default_subagent_model|default_subagent_reasoning_effort|max_concurrent_threads_per_session|interrupt_message|multi_agent)\s*=",
            config_text,
        ):
            errors.append(f"Managed templates must not configure native subagents: {config_path}")
        if re.search(r"(?m)^model\s*=", config_text):
            errors.append(f"Main conversation model must remain user-selectable: {config_path}")
    return errors


def _check_skill_set(kit_root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = kit_root / "skills"
    actual_skills = {path.name for path in skill_root.iterdir() if path.is_dir()}
    if actual_skills != SKILLS:
        errors.append(f"Unexpected skill set: {sorted(actual_skills)}")
    return errors


def _check_skill_contents(kit_root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = kit_root / "skills"
    for name in sorted(SKILLS):
        root = skill_root / name
        skill_path = root / "SKILL.md"
        yaml_path = root / "agents/openai.yaml"
        # Missing required skill files are reported as errors, not left to raise
        # an unguarded read_text and abort the whole validator mid-way.
        if not skill_path.is_file():
            errors.append(f"{name}: missing SKILL.md")
            continue
        if not yaml_path.is_file():
            errors.append(f"{name}: missing agents/openai.yaml")
            continue
        skill_text = skill_path.read_text(encoding="utf-8")
        yaml_text = yaml_path.read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\n(.*?)\n---\n", skill_text, flags=re.DOTALL)
        if not frontmatter:
            errors.append(f"{name}: missing YAML frontmatter")
        else:
            keys = [line.split(":", 1)[0].strip() for line in frontmatter.group(1).splitlines() if ":" in line]
            if keys != ["name", "description"]:
                errors.append(f"{name}: frontmatter must contain only name and description")
            if f"name: {name}" not in frontmatter.group(1):
                errors.append(f"{name}: frontmatter name mismatch")
        if f"${name}" not in yaml_text:
            errors.append(f"{name}: default_prompt does not mention ${name}")
        if "Use -" in yaml_text:
            errors.append(f"{name}: default_prompt contains the old PowerShell-expanded skill name")
        for relative in re.findall(r"\]\((references/[^)]+)\)", skill_text):
            if not (root / relative).is_file():
                errors.append(f"{name}: missing linked reference {relative}")
    return errors


def _check_placeholders(repo_root: Path) -> list[str]:
    errors: list[str] = []
    text_suffixes = {".md", ".yaml", ".yml", ".json", ".toml", ".py", ".ps1", ".rules"}
    unresolved_marker = "[" + "TODO:"
    for path in repo_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if unresolved_marker in text or re.search(r"(?m)^TODO:\s", text):
            errors.append(f"Unresolved placeholder in {path}")
    return errors


def _check_toml(kit_root: Path) -> list[str]:
    errors: list[str] = []
    if tomllib is not None:
        for path in kit_root.rglob("*.toml"):
            try:
                tomllib.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid TOML {path}: {exc}")
    return errors


def _check_unit_tests(repo_root: Path) -> list[str]:
    errors: list[str] = []
    test_command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(repo_root / "tests"),
        "-p",
        "test_*.py",
    ]
    try:
        tests = subprocess.run(
            test_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=UNIT_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        errors.append(
            f"Unit tests timed out after {UNIT_TEST_TIMEOUT_SECONDS} seconds:\n{partial}"
        )
    else:
        if tests.returncode != 0:
            errors.append("Unit tests failed:\n" + tests.stdout)
    return errors


def build_check_groups(kit_root: Path, repo_root: Path) -> list:
    """The ordered, numbered structural check groups.

    Each check is a discrete named group so a crash in one is reported as that
    group aborting with the rest not run, instead of a bare traceback that
    cannot be told apart from "everything passed".
    """
    return [
        ("obsolete-artifacts", lambda: _check_obsolete_artifacts(kit_root, repo_root)),
        ("required-files", lambda: _check_required_files(kit_root, repo_root)),
        ("agents-templates", lambda: _check_agents_templates(kit_root)),
        ("config-templates", lambda: _check_config_templates(kit_root, repo_root)),
        ("skill-set", lambda: _check_skill_set(kit_root)),
        ("skill-contents", lambda: _check_skill_contents(kit_root)),
        ("placeholders", lambda: _check_placeholders(repo_root)),
        ("toml", lambda: _check_toml(kit_root)),
        ("unit-tests", lambda: _check_unit_tests(repo_root)),
    ]


def run_checks(groups) -> tuple[list[str], str]:
    """Run each check group in order, accounting for coverage.

    A validator that dies half-way through has not found nothing -- it has
    simply never run the rest of its checks. Track how many groups completed
    and, on an unexpected exception, which group aborted and how many never ran,
    so a crash can never be mistaken for a clean pass.
    """
    errors: list[str] = []
    total = len(groups)
    done = 0
    aborted_in: str | None = None
    for name, check in groups:
        try:
            errors.extend(check())
        except Exception as exc:
            aborted_in = name
            errors.append(f"Check group '{name}' aborted before finishing: {exc!r}")
            break
        done += 1
    not_run = total - done
    if aborted_in is not None:
        coverage = f"COVERAGE: {done}/{total}, aborted in {aborted_in}, {not_run} not run"
    else:
        coverage = f"COVERAGE: {done}/{total}, {not_run} not run"
    return errors, coverage


def main() -> int:
    kit_root = Path(__file__).resolve().parents[1]
    repo_root = kit_root.parents[1]
    errors, coverage = run_checks(build_check_groups(kit_root, repo_root))
    print(coverage)
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors))
        return 1
    print("Dev Kit structural checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
