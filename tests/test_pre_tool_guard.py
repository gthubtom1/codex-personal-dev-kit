from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import pre_tool_guard  # noqa: E402


class PreToolGuardTests(unittest.TestCase):
    def assert_blocked(self, command: str) -> None:
        decision = pre_tool_guard.classify_command(command)
        self.assertTrue(decision.blocked, command)

    def assert_allowed(self, command: str) -> None:
        decision = pre_tool_guard.classify_command(command)
        self.assertFalse(decision.blocked, decision.reason)

    def test_blocks_destructive_and_remote_git(self) -> None:
        for command in (
            "git push origin main",
            "git -C repo merge feature",
            "git reset --hard HEAD~1",
            "git commit --amend --no-edit",
            "git tag v1.2.0",
            "pwsh -Command git clean -fd",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

        push = pre_tool_guard.classify_command("git push origin main")
        self.assertIn("feature_guard.py publish", push.reason)

    def test_blocks_publish_deploy_and_catastrophic_delete(self) -> None:
        for command in (
            "npm publish",
            "docker push example/app",
            "terraform apply",
            "kubectl delete deployment app",
            "Remove-Item -Recurse -Force C:\\",
            "npm install typescript -g",
            "npm --global install typescript",
            "pip install ruff",
            "pip --isolated install ruff",
            "python -m pip install ruff",
            "winget upgrade Git.Git",
            "winget --source winget upgrade Git.Git",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_local_development_commands(self) -> None:
        for command in (
            "git status -sb",
            "git tag --list --format='%(refname:short)'",
            "git tag -v v1.2.0",
            "git add app.js",
            "git commit -m 'checkpoint: feature'",
            "npm test",
            "terraform plan",
        ):
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_git_tag_read_only_flags_cannot_hide_a_mutation(self) -> None:
        for command in (
            "git tag --list --force v1.2.0",
            "git tag --format='%(refname:short)' --delete v1.2.0",
            "git tag --list --message release v1.2.0",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_blocked_high_risk_actions_do_not_delegate_raw_commands_to_beginner(self) -> None:
        for command in (
            "git pull origin main",
            "git worktree remove ../old-worktree",
            "gh release create v1.0.0",
            "winget install Git.Git",
            "pip install ruff",
            "npm publish",
        ):
            with self.subTest(command=command):
                decision = pre_tool_guard.classify_command(command)
                self.assertTrue(decision.blocked)
                reason = decision.reason.lower()
                self.assertNotIn("perform it manually", reason)
                self.assertNotIn("user must", reason)
                self.assertNotIn("ask the user to", reason)


if __name__ == "__main__":
    unittest.main()
