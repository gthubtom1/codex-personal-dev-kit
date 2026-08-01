from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
FEATURE_GUARD_PATH = SCRIPT_ROOT / "feature_guard.py"
sys.path.insert(0, str(SCRIPT_ROOT))

import feature_guard  # noqa: E402


FEATURES = """# Feature Map

## Feature Inventory

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Toggle acceleration | Settings control -> save API -> worker | The saved setting controls processing. | settings integration test | critical | active |
| F-002 | Export a result | Export button -> API -> downloaded file | A valid file is downloaded. | export integration test | standard | active |
"""


class FeatureGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".codex").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        (self.root / "AGENTS.md").write_text("# Test project\n", encoding="utf-8")
        (self.root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
        (self.root / ".gitignore").write_text(".codex/current-change.json\n", encoding="utf-8")
        (self.root / "docs/FEATURES.md").write_text(FEATURES, encoding="utf-8")
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = true;\n", encoding="utf-8")
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def hook(self, payload: dict) -> dict | None:
        result = subprocess.run(
            [sys.executable, str(FEATURE_GUARD_PATH), "hook"],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def start(self) -> dict:
        return feature_guard.start_contract(
            self.root,
            "Improve export without losing the acceleration setting",
            ["F-002"],
            ["F-001"],
            [],
        )

    def test_apply_patch_requires_contract(self) -> None:
        output = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "apply_patch",
                "tool_input": {"command": "*** Begin Patch"},
            }
        )
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_protected_feature_cannot_disappear(self) -> None:
        self.start()
        updated = "\n".join(line for line in FEATURES.splitlines() if "F-001" not in line) + "\n"
        (self.root / "docs/FEATURES.md").write_text(updated, encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "F-001 disappeared"):
            feature_guard.complete_contract(self.root, ["F-001", "F-002"], ["tests pass"])

    def test_unexpected_file_deletion_fails(self) -> None:
        self.start()
        (self.root / "src/app.js").unlink()
        with self.assertRaisesRegex(feature_guard.GuardError, "Unexpected tracked file deletion"):
            feature_guard.complete_contract(self.root, ["F-001", "F-002"], ["tests pass"])

    def test_critical_feature_verification_is_required(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "F-001"):
            feature_guard.complete_contract(self.root, ["F-002"], ["export tests pass"])

    def test_verified_content_can_be_staged_committed_and_stopped(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        feature_guard.complete_contract(self.root, ["F-001", "F-002"], ["settings and export tests pass"])

        self.git("add", "src/app.js")
        commit_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m checkpoint"},
            }
        )
        self.assertIsNone(commit_hook)
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "checkpoint")

        stop_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "Stop",
                "stop_hook_active": False,
            }
        )
        self.assertIsNone(stop_hook)
        feature_guard.close_contract(self.root)
        self.assertFalse((self.root / ".codex/current-change.json").exists())

    def test_close_rejects_changes_after_verification(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        feature_guard.complete_contract(self.root, ["F-001", "F-002"], ["settings and export tests pass"])
        (self.root / "src/app.js").write_text("export const acceleration = false;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "changed after verification"):
            feature_guard.close_contract(self.root)

    def test_open_contract_blocks_stop_and_restores_after_resume(self) -> None:
        self.start()
        stop_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "Stop",
                "stop_hook_active": False,
            }
        )
        self.assertEqual(stop_hook["decision"], "block")
        resume_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "SessionStart",
                "source": "compact",
            }
        )
        context = resume_hook["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Improve export", context)
        self.assertIn("F-002", context)


if __name__ == "__main__":
    unittest.main()
