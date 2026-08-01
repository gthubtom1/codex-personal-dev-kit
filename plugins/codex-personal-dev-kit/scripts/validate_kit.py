#!/usr/bin/env python3
"""Cross-platform structural checks for Codex Personal Dev Kit."""

from __future__ import annotations

import json
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
    plugin_root = Path(__file__).resolve().parents[1]
    repo_root = plugin_root.parents[1]
    errors: list[str] = []

    project_hooks_path = plugin_root / "assets/project-template/.codex/hooks.json"
    for path in [repo_root / ".agents/plugins/marketplace.json", plugin_root / ".codex-plugin/plugin.json", project_hooks_path]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON {path}: {exc}")

    manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if manifest.get("name") != plugin_root.name:
        errors.append("Plugin folder and manifest name do not match")
    if not isinstance(manifest.get("interface", {}).get("defaultPrompt"), list):
        errors.append("interface.defaultPrompt must be an array")

    hooks = json.loads(project_hooks_path.read_text(encoding="utf-8")).get("hooks", {})
    for event in ("SessionStart", "PreToolUse", "Stop", "SessionEnd"):
        if event not in hooks:
            errors.append(f"Missing required hook event: {event}")
    session_matchers = [str(item.get("matcher", "")) for item in hooks.get("SessionStart", [])]
    if not any("clear" in matcher for matcher in session_matchers):
        errors.append("SessionStart Hook must restore context after clear as well as startup/resume/compact")
    for entry in hooks.get("PreToolUse", []):
        matcher = str(entry.get("matcher", ""))
        if not matcher:
            continue
        try:
            compiled = re.compile(matcher)
        except re.error as exc:
            errors.append(f"Invalid PreToolUse matcher {matcher!r}: {exc}")
            continue
        if compiled.search("Agent") or compiled.search("spawn_agent"):
            errors.append("Project Hooks must not intercept Codex native subagent tools")
    if "mcpServers" in manifest or "apps" in manifest or (plugin_root / ".mcp.json").exists() or (plugin_root / ".app.json").exists():
        errors.append("This workflow-only Plugin must not add replacement MCP or app agent surfaces")
    for relative in (
        "scripts/feature_guard.py",
        "scripts/pre_tool_guard.py",
        "scripts/audit_project.py",
        "scripts/bootstrap/resolve-codex-cli.ps1",
    ):
        if not (plugin_root / relative).is_file():
            errors.append(f"Missing required runtime file: {relative}")
    if (plugin_root / "hooks/hooks.json").exists():
        errors.append("The optional Plugin must not bundle lifecycle Hooks; safeguards belong to project-local .codex/hooks.json")
    legacy_agents = list((plugin_root / "assets/global-profile/agents").glob("codex-kit-*.toml"))
    if legacy_agents:
        errors.append("Standalone mode must not ship required custom agent files: " + ", ".join(path.name for path in legacy_agents))
    if not (plugin_root / "INDEX.md").is_file():
        errors.append("Missing standalone Dev Kit INDEX.md")
    standalone_agents = plugin_root / "assets/standalone/AGENTS.md"
    if not standalone_agents.is_file() or "{{WORKSPACE_AGENTS_PATH}}" not in standalone_agents.read_text(encoding="utf-8"):
        errors.append("Short standalone AGENTS template must point to the detailed mother-folder AGENTS.md")
    for config_path in (
        plugin_root / "assets/workspace-template/.codex/config.toml",
        plugin_root / "assets/project-template/.codex/config.toml",
    ):
        if not config_path.is_file():
            errors.append(f"Missing native Codex config template: {config_path}")
            continue
        config_text = config_path.read_text(encoding="utf-8")
        if 'default_subagent_model = "gpt-5.6-luna"' not in config_text:
            errors.append(f"Subagent model is not pinned to gpt-5.6-luna: {config_path}")
        if 'default_subagent_reasoning_effort = "max"' not in config_text:
            errors.append(f"Subagent reasoning is not pinned to max: {config_path}")

    skill_root = plugin_root / "skills"
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
        for path in plugin_root.rglob("*.toml"):
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
