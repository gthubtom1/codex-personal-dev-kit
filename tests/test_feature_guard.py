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
        (self.root / "docs/STATUS.md").write_text(
            "# Current Status\n\n## Milestone\n\nKeep existing behavior.\n\n## Next Action\n\nVerify the export change.\n",
            encoding="utf-8",
        )
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

    def start(self, owned_paths: tuple[str, ...] = ()) -> dict:
        return feature_guard.start_contract(
            self.root,
            "Improve export without losing the acceleration setting",
            ["F-002"],
            ["F-001"],
            [],
            owned_paths,
        )

    def stage(self, *paths: str) -> dict:
        return feature_guard.stage_paths(self.root, paths)

    def verify(self, *feature_ids: str) -> dict:
        return feature_guard.run_verification(
            self.root,
            feature_ids,
            [sys.executable, "-c", "print('verification passed')"],
            timeout=30,
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
        self.stage("src/app.js")
        self.verify("F-002")
        with self.assertRaisesRegex(feature_guard.GuardError, "F-001"):
            feature_guard.complete_contract(self.root, [], [])

    def test_adjacent_feature_can_be_promoted_to_changed(self) -> None:
        self.start()
        updated = FEATURES.replace("| F-001 | Toggle acceleration |", "| F-001 | Control acceleration |")
        (self.root / "docs/FEATURES.md").write_text(updated, encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "Protected feature F-001 changed"):
            feature_guard.complete_contract(self.root, [], [])

        contract = feature_guard.declare_changed_features(self.root, ["F-001"])
        self.assertEqual(contract["changedFeatureIds"], ["F-001", "F-002"])
        self.assertNotIn("F-001", contract["explicitVerificationIds"])
        self.assertNotIn("F-001", contract["protectedFeatures"])

        self.stage("docs/FEATURES.md")
        self.verify("F-001", "F-002")
        completed = feature_guard.complete_contract(self.root, [], [])
        self.assertEqual(completed["state"], "verified")

    def test_free_form_evidence_cannot_replace_a_real_command(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        with self.assertRaisesRegex(feature_guard.GuardError, "successful recorded verification command"):
            feature_guard.complete_contract(self.root, ["F-001", "F-002"], ["tests pass"])

    def test_verification_command_cannot_hide_git_or_install_mutations(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        with self.assertRaisesRegex(feature_guard.GuardError, "may not mutate Git state"):
            feature_guard.run_verification(self.root, ["F-001"], ["git", "add", "src/app.js"])
        with self.assertRaisesRegex(feature_guard.GuardError, "installation"):
            feature_guard.run_verification(self.root, ["F-001"], ["pip", "install", "ruff"])

    def test_verified_content_can_be_staged_committed_and_stopped(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

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
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        (self.root / "src/app.js").write_text("export const acceleration = false;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "changed after verification"):
            feature_guard.close_contract(self.root)

    def test_composite_commit_and_arbitrary_new_head_are_rejected(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

        output = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m checkpoint && echo changed > src/app.js"},
            }
        )
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

        redirected = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m checkpoint > commit.log"},
            }
        )
        self.assertEqual(redirected["hookSpecificOutput"]["permissionDecision"], "deny")

        for unsafe_commit in ("git commit -am checkpoint", "git commit -m checkpoint src/app.js", "git commit --no-verify -m checkpoint"):
            with self.subTest(command=unsafe_commit):
                unsafe = self.hook(
                    {
                        "cwd": str(self.root),
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": unsafe_commit},
                    }
                )
                self.assertEqual(unsafe["hookSpecificOutput"]["permissionDecision"], "deny")

        (self.root / "src/app.js").write_text("export const acceleration = false;\nexport const exportFile = 'v3';\n", encoding="utf-8")
        self.git("add", "src/app.js")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "unverified")
        with self.assertRaisesRegex(feature_guard.GuardError, "changed after verification"):
            feature_guard.close_contract(self.root)

    def test_raw_git_add_is_blocked(self) -> None:
        self.start()
        output = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git add ."},
            }
        )
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("feature_guard.py stage", output["hookSpecificOutput"]["permissionDecisionReason"])

        compound = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": f"{sys.executable} {FEATURE_GUARD_PATH} status --root .; git add ."},
            }
        )
        self.assertEqual(compound["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_preexisting_user_change_requires_explicit_ownership(self) -> None:
        (self.root / "docs/STATUS.md").write_text("# User draft\n", encoding="utf-8")
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        with self.assertRaisesRegex(feature_guard.GuardError, "--own-path"):
            self.stage("docs/STATUS.md")

    def test_split_feature_maps_are_aggregated_and_duplicate_ids_fail(self) -> None:
        (self.root / "docs/features").mkdir()
        (self.root / "docs/FEATURES.md").write_text("# Feature Map\n\n- [Core](features/core.md)\n", encoding="utf-8")
        (self.root / "docs/features/core.md").write_text(FEATURES, encoding="utf-8")
        catalog = feature_guard.read_feature_catalog(self.root)
        self.assertEqual(set(catalog), {"F-001", "F-002"})
        (self.root / "docs/features/duplicate.md").write_text(FEATURES, encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "Duplicate feature ID F-001"):
            feature_guard.read_feature_catalog(self.root)

    def test_contract_can_declare_a_new_feature_id_before_adding_its_record(self) -> None:
        contract = feature_guard.start_contract(self.root, "Add a new user capability", ["F-003"], [], [], [])
        self.assertEqual(contract["changedFeatureIds"], ["F-003"])

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
        self.assertIn("Verify the export change", context)
        self.assertIn("Latest checkpoint", context)

    def test_session_start_without_contract_returns_bounded_current_facts(self) -> None:
        (self.root / "docs/STATUS.md").write_text(
            "# Current Status\n\n## Milestone\n\nReady.\n\n## Verified\n\n"
            + ("- old detail that should be capped\n" * 300)
            + "\n## Next Action\n\nBuild the next accepted slice.\n",
            encoding="utf-8",
        )
        output = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "SessionStart",
                "source": "startup",
            }
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No current change contract", context)
        self.assertIn("Build the next accepted slice", context)
        self.assertIn("branch main", context)
        self.assertLessEqual(len(context), feature_guard.RECOVERY_PACKET_MAX_CHARS)

    def test_session_end_preserves_verified_but_uncommitted_contract(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        output = self.hook({"cwd": str(self.root), "hook_event_name": "SessionEnd"})
        self.assertIsNone(output)
        self.assertTrue((self.root / ".codex/current-change.json").is_file())


if __name__ == "__main__":
    unittest.main()
