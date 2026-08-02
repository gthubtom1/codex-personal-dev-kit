#!/usr/bin/env python3
"""Cross-platform structural checks for Codex Personal Dev Kit."""

from __future__ import annotations

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
    "audit-codex-kit",
}


def main() -> int:
    kit_root = Path(__file__).resolve().parents[1]
    repo_root = kit_root.parents[1]
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

    version_path = repo_root / "VERSION"
    if not version_path.is_file() or not version_path.read_text(encoding="utf-8").strip():
        errors.append(f"Missing standalone VERSION marker: {version_path}")
    for relative in (
        "scripts/feature_guard.py",
        "scripts/pre_tool_guard.py",
        "scripts/audit_project.py",
        "scripts/merge-codex-config.ps1",
        "scripts/bootstrap/resolve-codex-cli.ps1",
        "assets/project-template/docs/INDEX.md",
        "assets/project-template/docs/adr/INDEX.md",
        "assets/workspace-template/.codex/config.toml",
    ):
        if not (kit_root / relative).is_file():
            errors.append(f"Missing required runtime file: {relative}")
    if not (repo_root / "docs/INDEX.md").is_file():
        errors.append(f"Missing Dev Kit documentation index: {repo_root / 'docs/INDEX.md'}")
    legacy_agents = list((kit_root / "assets/global-profile/agents").glob("codex-kit-*.toml"))
    if legacy_agents:
        errors.append("Standalone mode must not ship required custom agent files: " + ", ".join(path.name for path in legacy_agents))
    standalone_agents = kit_root / "assets/standalone/AGENTS.md"
    if not standalone_agents.is_file() or "{{WORKSPACE_AGENTS_PATH}}" not in standalone_agents.read_text(encoding="utf-8"):
        errors.append("Short standalone AGENTS template must point to the detailed mother-folder AGENTS.md")
    for config_path in (
        repo_root / ".codex/config.toml",
        kit_root / "assets/workspace-template/.codex/config.toml",
        kit_root / "assets/project-template/.codex/config.toml",
    ):
        if not config_path.is_file():
            errors.append(f"Missing native Codex config template: {config_path}")
            continue
        config_text = config_path.read_text(encoding="utf-8")
        if 'default_subagent_model = "gpt-5.6-luna"' not in config_text:
            errors.append(f"Default subagent model is not Luna: {config_path}")
        if 'default_subagent_reasoning_effort = "max"' not in config_text:
            errors.append(f"Default subagent reasoning is not max: {config_path}")
        concurrency = re.search(r"(?m)^max_concurrent_threads_per_session\s*=\s*(\d+)\s*$", config_text)
        if not concurrency or int(concurrency.group(1)) < 2:
            errors.append(f"Subagent concurrency must allow multiple agents: {config_path}")
        if re.search(r"(?m)^model\s*=", config_text):
            errors.append(f"Main conversation model must remain user-selectable: {config_path}")

    skill_root = kit_root / "skills"
    actual_skills = {path.name for path in skill_root.iterdir() if path.is_dir()}
    if actual_skills != SKILLS:
        errors.append(f"Unexpected skill set: {sorted(actual_skills)}")

    for name in sorted(SKILLS):
        root = skill_root / name
        skill_path = root / "SKILL.md"
        yaml_path = root / "agents/openai.yaml"
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

    text_suffixes = {".md", ".yaml", ".yml", ".json", ".toml", ".py", ".ps1", ".rules"}
    unresolved_marker = "[" + "TODO:"
    for path in repo_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if unresolved_marker in text or re.search(r"(?m)^TODO:\s", text):
            errors.append(f"Unresolved placeholder in {path}")

    if tomllib is not None:
        for path in kit_root.rglob("*.toml"):
            try:
                tomllib.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid TOML {path}: {exc}")

    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(repo_root / "tests"), "-p", "test_*.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if tests.returncode != 0:
        errors.append("Unit tests failed:\n" + tests.stdout)

    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors))
        return 1
    print("Dev Kit structural checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
