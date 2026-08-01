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

    for path in [repo_root / ".agents/plugins/marketplace.json", plugin_root / ".codex-plugin/plugin.json", plugin_root / "hooks/hooks.json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON {path}: {exc}")

    manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if manifest.get("name") != plugin_root.name:
        errors.append("Plugin folder and manifest name do not match")
    if not isinstance(manifest.get("interface", {}).get("defaultPrompt"), list):
        errors.append("interface.defaultPrompt must be an array")

    hooks = json.loads((plugin_root / "hooks/hooks.json").read_text(encoding="utf-8")).get("hooks", {})
    for event in ("SessionStart", "PreToolUse", "Stop", "SessionEnd"):
        if event not in hooks:
            errors.append(f"Missing required hook event: {event}")
    for relative in ("scripts/feature_guard.py", "hooks/pre_tool_guard.py", "scripts/audit_project.py"):
        if not (plugin_root / relative).is_file():
            errors.append(f"Missing required runtime file: {relative}")

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
