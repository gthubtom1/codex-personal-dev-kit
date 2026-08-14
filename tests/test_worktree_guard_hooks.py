from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
TEMPLATE_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/assets/project-template"
sys.path.insert(0, str(SCRIPT_ROOT))

import pre_tool_guard  # noqa: E402


class ForcePushBypassTests(unittest.TestCase):
    """The classifier must not be defeated by a second command hidden behind a
    newline or a $()/backtick substitution. `feature_guard.py verify` runs the same
    classifier and then executes the command, so a bypass is a live force-push path."""

    def test_newline_joined_push_is_blocked(self) -> None:
        self.assertTrue(pre_tool_guard.classify_command("git status\ngit push --force origin main").blocked)
        self.assertTrue(pre_tool_guard.classify_command("git add .\ngit commit -m x\ngit push --force").blocked)

    def test_command_substitution_push_is_blocked(self) -> None:
        self.assertTrue(pre_tool_guard.classify_command("echo $(git push origin main)").blocked)
        self.assertTrue(pre_tool_guard.classify_command("echo `git push --force`").blocked)

    def test_nested_substitution_push_is_blocked(self) -> None:
        self.assertTrue(pre_tool_guard.classify_command("echo $(echo $(git push --force))").blocked)

    def test_newline_hidden_destructive_delete_is_blocked(self) -> None:
        # A catastrophic delete hidden after a newline must not slip past the
        # deletion scan (it runs after newline normalization).
        for command in (
            "echo hi\nrm -rf /",
            "echo x\nformat c:",
            "ls\nRemove-Item -Recurse -Force C:\\",
        ):
            with self.subTest(command=command):
                self.assertTrue(pre_tool_guard.classify_command(command).blocked)

    def test_ordinary_commands_still_allowed(self) -> None:
        self.assertFalse(pre_tool_guard.classify_command("git status\ngit diff").blocked)
        self.assertFalse(pre_tool_guard.classify_command("echo $(git rev-parse HEAD)").blocked)


class CursorHostAdaptationFilesTests(unittest.TestCase):
    """The project template must not inject host hooks or settings into onboarded
    projects; adaptation lives in prose rules plus the host's own settings."""

    def test_project_template_ships_no_host_hooks_or_settings(self) -> None:
        for relative in (
            ".cursor/hooks.json",
            ".cursor/hooks/worktree_guard.py",
            ".vscode/settings.json",
            ".codex/config.toml",
        ):
            self.assertFalse((TEMPLATE_ROOT / relative).exists(), relative)


class WorktreeRuleTextTests(unittest.TestCase):
    """The worktree-outside mandate is advisory prose on hosts without the hook, so
    its wording must not silently vanish from the rule surfaces (red-when-removed)."""

    SURFACES = (
        "README.md",
        "plugins/codex-personal-dev-kit/assets/project-template/AGENTS.md",
        "plugins/codex-personal-dev-kit/assets/workspace-template/AGENTS.md",
        "plugins/codex-personal-dev-kit/assets/standalone/AGENTS.md",
        "plugins/codex-personal-dev-kit/skills/orchestrate-codex-team/SKILL.md",
    )

    def test_each_surface_forbids_in_workspace_worktrees(self) -> None:
        for relative in self.SURFACES:
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(surface=relative):
                # Two mandate-specific tokens that both disappear if the rule is
                # removed: the in-workspace anti-pattern and the guarded outside path.
                self.assertIn(".local", text)
                self.assertIn("worktree-path", text)


if __name__ == "__main__":
    unittest.main()
