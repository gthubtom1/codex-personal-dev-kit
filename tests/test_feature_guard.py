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
| F-001 | Toggle acceleration | Settings control -> save API -> worker | The saved setting controls processing. | test:tests/verify_features.py | critical | active |
| F-002 | Export a result | Export button -> API -> downloaded file | A valid file is downloaded. | test:tests/verify_features.py | standard | active |
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
        (self.root / "docs/VERSIONS.md").write_text(
            "# Versions\n\n| Version | User-visible result | Verification | Status |\n| --- | --- | --- | --- |\n| v1.0.0 | Baseline export | suite:all-tests | recoverable |\n",
            encoding="utf-8",
        )
        (self.root / "docs/STATUS.md").write_text(
            "# Current Status\n\n## Milestone\n\nKeep existing behavior.\n\n## Working State\n\nMain checkout is clean before the task.\n\n## Verified\n\nBaseline verification is available.\n\n## Current Risks\n\nExport behavior still needs a regression check.\n\n## Next Action\n\nVerify the export change.\n",
            encoding="utf-8",
        )
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = true;\n", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests/verify_features.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
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
        if any(path.replace("\\", "/") == "src/app.js" for path in paths) and not (self.root / "docs/STATUS.md").read_text(encoding="utf-8").startswith("# User draft"):
            status = self.root / "docs/STATUS.md"
            status.write_text(
                "# Current Status\n\n## Milestone\n\nExport slice verified.\n\n## Working State\n\nMain checkout contains the guarded slice.\n\n## Verified\n\nThe executable feature check passed.\n\n## Current Risks\n\nContinue checking adjacent behavior.\n\n## Next Action\n\nContinue the next accepted slice.\n",
                encoding="utf-8",
            )
            paths = (*paths, "docs/STATUS.md")
        return feature_guard.stage_paths(self.root, paths)

    def verify(self, *feature_ids: str) -> dict:
        return feature_guard.run_verification(
            self.root,
            feature_ids,
            [sys.executable, "tests/verify_features.py"],
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

    def test_native_edit_and_write_require_contract_and_cannot_edit_verified_snapshot(self) -> None:
        for tool_name in ("Edit", "Write"):
            output = self.hook(
                {
                    "cwd": str(self.root),
                    "hook_event_name": "PreToolUse",
                    "tool_name": tool_name,
                    "tool_input": {"file_path": str(self.root / "src/app.js")},
                }
            )
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

        verified_edit = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(self.root / "src/app.js")},
            }
        )
        self.assertEqual(verified_edit["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("reopen", verified_edit["hookSpecificOutput"]["permissionDecisionReason"])

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

    def test_feature_verification_rejects_inline_fake_success_and_requires_binding(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        with self.assertRaisesRegex(feature_guard.GuardError, "inline/no-op"):
            feature_guard.run_verification(self.root, ["F-001"], [sys.executable, "-c", "print('verification passed')"])
        with self.assertRaisesRegex(feature_guard.GuardError, "not bound to feature"):
            feature_guard.run_verification(self.root, ["F-001"], [sys.executable, "tests/other_check.py"])

    def test_windows_path_separator_is_normalized_for_feature_binding(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        run = feature_guard.run_verification(self.root, ["F-001"], [sys.executable, r"tests\verify_features.py"], timeout=30)
        self.assertTrue(run["passed"])

    def test_source_change_requires_current_status_document(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        feature_guard.stage_paths(self.root, ["src/app.js"])
        feature_guard.run_verification(self.root, ["F-001", "F-002"], [sys.executable, "tests/verify_features.py"], timeout=30)
        with self.assertRaisesRegex(feature_guard.GuardError, "STATUS.md was not updated"):
            feature_guard.complete_contract(self.root, [], [])

    def test_status_formatting_only_change_does_not_satisfy_freshness(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        status = self.root / "docs/STATUS.md"
        status.write_text(status.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        feature_guard.stage_paths(self.root, ["src/app.js"])
        feature_guard.stage_paths(self.root, ["docs/STATUS.md"])
        self.verify("F-001", "F-002")
        with self.assertRaisesRegex(feature_guard.GuardError, "formatting-only"):
            feature_guard.complete_contract(self.root, [], [])

    def test_template_placeholders_cannot_enter_first_feature_checkpoint(self) -> None:
        (self.root / "docs/PROJECT.md").write_text(
            "# Project\n\nNot yet confirmed. Describe the primary user and outcome.\n",
            encoding="utf-8",
        )
        (self.root / "docs/ARCHITECTURE.md").write_text(
            "# Architecture\n\nThe current system has not been mapped yet. Record the runtime path.\n",
            encoding="utf-8",
        )
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        status = self.root / "docs/STATUS.md"
        status.write_text(
            "# Current Status\n\n## Milestone\n\nExport slice verified.\n\n## Working State\n\nGuarded change is staged.\n\n## Verified\n\nExecutable feature check passed.\n\n## Current Risks\n\nKeep both behaviors covered.\n\n## Next Action\n\nReview the next accepted slice.\n",
            encoding="utf-8",
        )
        feature_guard.stage_paths(self.root, ["src/app.js", "docs/STATUS.md"])
        self.verify("F-001", "F-002")
        with self.assertRaisesRegex(feature_guard.GuardError, "Template placeholder remains"):
            feature_guard.complete_contract(self.root, [], [])

    def test_source_change_requires_all_active_features_in_a_large_catalog(self) -> None:
        rows = [
            "| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for index in range(1, 42):
            criticality = "critical" if index == 1 else "standard"
            rows.append(
                f"| F-{index:03d} | Capability {index} | src/app.js -> test | Result {index} | test:tests/verify_features.py | {criticality} | active |"
            )
        (self.root / "docs/FEATURES.md").write_text("# Feature Map\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001")
        with self.assertRaisesRegex(feature_guard.GuardError, "F-002"):
            feature_guard.complete_contract(self.root, [], [])

    def test_verified_content_must_be_saved_through_guard_checkpoint(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

        stop_before_checkpoint = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "Stop",
                "stop_hook_active": False,
            }
        )
        self.assertEqual(stop_before_checkpoint["decision"], "block")
        self.assertIn("local recovery point", stop_before_checkpoint["reason"])

        commit_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m checkpoint"},
            }
        )
        self.assertEqual(commit_hook["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("feature_guard.py checkpoint", commit_hook["hookSpecificOutput"]["permissionDecisionReason"])

        checkpoint = feature_guard.create_checkpoint(self.root, "save export improvement")
        self.assertEqual(checkpoint, self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(self.git("log", "-1", "--pretty=%s").stdout.strip(), "checkpoint: save export improvement")
        self.assertEqual(self.git("log", "-1", "--pretty=%an <%ae>").stdout.strip(), "Codex Dev Kit <codex-dev-kit@local.invalid>")
        self.assertFalse((self.root / ".codex/current-change.json").exists())

        stop_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "Stop",
                "stop_hook_active": False,
            }
        )
        self.assertIsNone(stop_hook)

    def test_new_contract_cannot_replace_verified_uncommitted_work(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

        with self.assertRaisesRegex(feature_guard.GuardError, "not been saved as a local recovery point"):
            self.start()

    def test_close_rejects_changes_after_verification(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        (self.root / "src/app.js").write_text("export const acceleration = false;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "changed after verification"):
            feature_guard.close_contract(self.root)

    def test_raw_commit_and_arbitrary_new_head_are_rejected(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])

        for unsafe_commit in (
            "git commit -m checkpoint && echo changed > src/app.js",
            "git commit -m checkpoint > commit.log",
            "git commit -am checkpoint",
            "git commit -m checkpoint src/app.js",
            "git commit --no-verify -m checkpoint",
        ):
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

    def test_rollback_returns_to_previous_version_with_a_new_commit(self) -> None:
        baseline_head = self.git("rev-parse", "HEAD").stdout.strip()
        baseline_tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        changed_checkpoint = feature_guard.create_checkpoint(self.root, "save export v2")

        rollback_checkpoint = feature_guard.rollback_last_checkpoint(self.root)
        self.assertNotEqual(rollback_checkpoint, changed_checkpoint)
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}").stdout.strip(), baseline_tree)
        self.assertEqual(self.git("log", "-1", "--pretty=%s").stdout.strip(), "checkpoint: return to previous version " + baseline_head[:8])
        self.assertEqual(self.git("status", "--porcelain").stdout.strip(), "")

    def test_formal_versions_create_immutable_local_tags_and_are_listed(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v1';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        checkpoint = feature_guard.create_checkpoint(self.root, "deliver v1")

        version, target = feature_guard.create_local_version(self.root, "v1.0")
        self.assertEqual(version, "v1.0.0")
        self.assertEqual(target, checkpoint)
        self.assertEqual(self.git("rev-parse", "v1.0.0^{commit}").stdout.strip(), checkpoint)
        self.assertEqual(feature_guard.list_local_versions(self.root)[0][0], "v1.0.0")
        with self.assertRaisesRegex(feature_guard.GuardError, "already exists"):
            feature_guard.create_local_version(self.root, "v1.0.0")

    def test_formal_version_can_mark_a_verified_historical_checkpoint(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v1';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        historical = feature_guard.create_checkpoint(self.root, "deliver v1")

        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        (self.root / "docs/STATUS.md").write_text(
            "# Current Status\n\n## Milestone\n\nVersion two is verified.\n\n## Working State\n\n"
            "The main checkout contains the second export behavior.\n\n## Verified\n\nThe feature suite passed.\n\n"
            "## Current Risks\n\nThe earlier checkpoint must remain identifiable.\n\n## Next Action\n\n"
            "Record the historical formal version.\n",
            encoding="utf-8",
        )
        feature_guard.stage_paths(self.root, ["src/app.js", "docs/STATUS.md"])
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        feature_guard.create_checkpoint(self.root, "deliver v2")

        version, target = feature_guard.create_local_version(self.root, "v1.0", target=historical)
        self.assertEqual((version, target), ("v1.0.0", historical))
        self.assertEqual(self.git("rev-parse", "v1.0.0^{commit}").stdout.strip(), historical)

    def test_historical_version_target_must_be_a_current_branch_checkpoint(self) -> None:
        self.git("checkout", "--orphan", "unrelated")
        self.git("rm", "-rf", ".")
        (self.root / "outside.txt").write_text("outside\n", encoding="utf-8")
        self.git("add", "outside.txt")
        self.git(
            "-c", f"user.name={feature_guard.CHECKPOINT_AUTHOR_NAME}",
            "-c", f"user.email={feature_guard.CHECKPOINT_AUTHOR_EMAIL}",
            "commit", "-m", "checkpoint: unrelated",
        )
        unrelated = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("checkout", "main")
        with self.assertRaisesRegex(feature_guard.GuardError, "current branch history"):
            feature_guard.create_local_version(self.root, "v1.0", target=unrelated)

    def test_restore_named_version_preserves_newer_history_and_complete_version_index(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v1';\n", encoding="utf-8")
        self.stage("src/app.js")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        v1_checkpoint = feature_guard.create_checkpoint(self.root, "deliver v1")
        feature_guard.create_local_version(self.root, "v1.0.0")
        v1_tree = self.git("rev-parse", "v1.0.0^{tree}").stdout.strip()

        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v2';\n", encoding="utf-8")
        versions = self.root / "docs/VERSIONS.md"
        versions.write_text(
            versions.read_text(encoding="utf-8") + "| v1.1.0 | Improved export | suite:all-tests | recoverable |\n",
            encoding="utf-8",
        )
        (self.root / "docs/STATUS.md").write_text(
            "# Current Status\n\n## Milestone\n\nFormal v1.1 export is verified.\n\n## Working State\n\nMain checkout contains the v1.1 slice.\n\n## Verified\n\nThe executable feature check passed for v1.1.\n\n## Current Risks\n\nKeep the earlier formal version recoverable.\n\n## Next Action\n\nConfirm the next milestone.\n",
            encoding="utf-8",
        )
        feature_guard.stage_paths(self.root, ["src/app.js", "docs/VERSIONS.md", "docs/STATUS.md"])
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        v2_checkpoint = feature_guard.create_checkpoint(self.root, "deliver v1.1")
        feature_guard.create_local_version(self.root, "v1.1")

        restored = feature_guard.restore_local_version(self.root, "v1.0")
        self.assertNotEqual(restored, v2_checkpoint)
        self.assertEqual(self.git("rev-parse", "HEAD^").stdout.strip(), v2_checkpoint)
        self.assertEqual(self.git("rev-parse", "v1.0.0^{commit}").stdout.strip(), v1_checkpoint)
        self.assertIn("v1.1.0", versions.read_text(encoding="utf-8"))
        self.assertEqual(self.git("diff", "--name-only", "v1.0.0", "HEAD").stdout.strip(), "docs/VERSIONS.md")
        self.assertEqual(self.git("status", "--porcelain").stdout.strip(), "")
        product_tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        self.assertNotEqual(product_tree, v1_tree)  # The durable version registry intentionally stays current.

    def test_formal_version_requires_clean_checkpoint_and_matching_registry(self) -> None:
        with self.assertRaisesRegex(feature_guard.GuardError, "verified Dev Kit checkpoint"):
            feature_guard.create_local_version(self.root, "v1.0")
        with self.assertRaisesRegex(feature_guard.GuardError, "look like"):
            feature_guard.normalize_version("release-one")

        guard_command = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": f"{sys.executable} {FEATURE_GUARD_PATH} versions --root ."},
            }
        )
        self.assertIsNone(guard_command)

    def test_formal_version_must_match_a_tracked_version_marker(self) -> None:
        self.start()
        (self.root / "src/app.js").write_text("export const acceleration = true;\nexport const exportFile = 'v1';\n", encoding="utf-8")
        (self.root / "VERSION").write_text("2.0.0\n", encoding="utf-8")
        self.stage("src/app.js", "VERSION")
        self.verify("F-001", "F-002")
        feature_guard.complete_contract(self.root, [], [])
        feature_guard.create_checkpoint(self.root, "deliver mismatched marker")

        with self.assertRaisesRegex(feature_guard.GuardError, "VERSION marker 2.0.0"):
            feature_guard.create_local_version(self.root, "v1.0.0")

    def test_rollback_refuses_unsaved_work_and_raw_git_revert(self) -> None:
        (self.root / "src/app.js").write_text("unsaved\n", encoding="utf-8")
        with self.assertRaisesRegex(feature_guard.GuardError, "unsaved changes"):
            feature_guard.rollback_last_checkpoint(self.root)

        revert_hook = self.hook(
            {
                "cwd": str(self.root),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git revert HEAD"},
            }
        )
        self.assertEqual(revert_hook["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("feature_guard.py rollback", revert_hook["hookSpecificOutput"]["permissionDecisionReason"])

    def test_rollback_refuses_a_user_commit_that_is_not_a_dev_kit_checkpoint(self) -> None:
        (self.root / "src/app.js").write_text("user change\n", encoding="utf-8")
        self.git("add", "src/app.js")
        self.git("-c", "user.name=User", "-c", "user.email=user@example.invalid", "commit", "-m", "user save")
        with self.assertRaisesRegex(feature_guard.GuardError, "not created by the Dev Kit checkpoint flow"):
            feature_guard.rollback_last_checkpoint(self.root)

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
