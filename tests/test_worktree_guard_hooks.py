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
    """New projects on a snapshot/watch host must ship the worktree hard-guard and
    the artifact watcher-exclusion, or the editor-freeze half of the fix silently
    returns for every project created later."""

    def test_project_template_ships_cursor_hook_and_watcher_exclude(self) -> None:
        for relative in (
            ".cursor/hooks.json",
            ".cursor/hooks/worktree_guard.py",
            ".vscode/settings.json",
        ):
            self.assertTrue((TEMPLATE_ROOT / relative).is_file(), relative)

    def test_hook_wires_before_shell_execution_to_the_guard(self) -> None:
        hooks = json.loads((TEMPLATE_ROOT / ".cursor/hooks.json").read_text(encoding="utf-8"))
        entries = hooks.get("hooks", {}).get("beforeShellExecution", [])
        self.assertTrue(entries)
        self.assertTrue(any("worktree_guard.py" in entry.get("command", "") for entry in entries))

    def test_watcher_exclude_covers_regenerated_artifacts(self) -> None:
        text = (TEMPLATE_ROOT / ".vscode/settings.json").read_text(encoding="utf-8")
        for token in ("files.watcherExclude", "__pycache__", "*.sqlite3", "*.db"):
            self.assertIn(token, text)


class CursorWorktreeGuardTests(unittest.TestCase):
    GUARD = TEMPLATE_ROOT / ".cursor/hooks/worktree_guard.py"

    def _run(self, payload: dict) -> str:
        result = subprocess.run(
            [sys.executable, str(self.GUARD)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        return (result.stdout or "").replace(" ", "")

    def test_blocks_worktree_inside_workspace(self) -> None:
        base = {"cwd": r"D:\proj", "workspace_roots": [r"D:\proj"]}
        for command in (
            "git worktree add .local/wt-x",
            "git worktree add -b wt/x wt-inside",
            "git status\ngit worktree add .local/wt-y",
        ):
            with self.subTest(command=command):
                self.assertIn('"permission":"deny"', self._run({"command": command, **base}))

    def test_blocks_inside_parent_folder_workspace(self) -> None:
        out = self._run(
            {"command": "git worktree add projects/p/.local/wt", "cwd": r"D:\ws", "workspace_roots": [r"D:\ws"]}
        )
        self.assertIn('"permission":"deny"', out)

    def test_allows_outside_and_read_only(self) -> None:
        base = {"cwd": r"D:\proj", "workspace_roots": [r"D:\proj"]}
        for command in (
            r"git worktree add ..\.proj-worktrees\wt-x",
            "git status",
            "git worktree list",
        ):
            with self.subTest(command=command):
                self.assertNotIn('"permission":"deny"', self._run({"command": command, **base}))


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
