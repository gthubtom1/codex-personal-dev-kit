from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import feature_guard  # noqa: E402
import next_step  # noqa: E402


FEATURES = """# Feature Map

## Feature Inventory

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Toggle acceleration | Settings control -> save API -> worker | The saved setting controls processing. | test:tests/verify_features.py | critical | active |
"""

STATUS = (
    "# Current Status\n\n## Milestone\n\nKeep existing behavior.\n\n## Working State\n\n"
    "Main checkout is clean before the task.\n\n## Verified\n\nBaseline verification is available.\n\n"
    "## Current Risks\n\nAcceleration still needs a regression check.\n\n## Next Action\n\nVerify the change.\n"
)

STATUS_DONE = (
    "# Current Status\n\n## Milestone\n\nThe slice is verified.\n\n## Working State\n\n"
    "Main checkout contains the guarded slice.\n\n## Verified\n\nThe executable feature check passed.\n\n"
    "## Current Risks\n\nContinue checking adjacent behavior.\n\n## Next Action\n\nContinue the next slice.\n"
)


class NextStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)

    def scaffold(self) -> None:
        (self.root / ".codex").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / ".gitignore").write_text(".codex/current-change.json\n", encoding="utf-8")
        (self.root / "docs/FEATURES.md").write_text(FEATURES, encoding="utf-8")
        (self.root / "docs/STATUS.md").write_text(STATUS, encoding="utf-8")
        (self.root / "src/app.js").write_text("export const acceleration = true;\n", encoding="utf-8")
        (self.root / "tests/verify_features.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")

    def plan(self) -> str:
        return "\n".join(next_step.plan_next_steps(self.root))

    def test_reports_onboarding_before_any_edit_when_git_or_docs_are_missing(self) -> None:
        output = self.plan()
        self.assertIn("$onboard-codex-project", output)
        self.assertIn("Git 基线", output)

    def test_requires_a_contract_before_the_first_edit(self) -> None:
        self.scaffold()
        output = self.plan()
        self.assertIn("没有打开的变更契约", output)
        self.assertIn("start --root", output)
        self.assertIn("$research-and-reuse", output)

    def test_flags_unregistered_changes_before_recommending_a_contract(self) -> None:
        self.scaffold()
        (self.root / "src/app.js").write_text("export const acceleration = false;\n", encoding="utf-8")
        output = self.plan()
        self.assertIn("未登记的修改", output)
        self.assertIn("src/app.js", output)
        self.assertIn("--own-path", output)

    def test_guides_stage_verify_complete_and_checkpoint_in_order(self) -> None:
        self.scaffold()
        feature_guard.start_contract(self.root, "Adjust acceleration", ["F-001"], [], [], [])
        self.assertIn("stage --root", self.plan())

        (self.root / "src/app.js").write_text("export const acceleration = 'v2';\n", encoding="utf-8")
        (self.root / "docs/STATUS.md").write_text(STATUS_DONE, encoding="utf-8")
        feature_guard.stage_paths(self.root, ["src/app.js", "docs/STATUS.md"])
        output = self.plan()
        self.assertIn("verify --root", output)
        self.assertIn("--feature F-001", output)

        feature_guard.run_verification(self.root, ["F-001"], [sys.executable, "tests/verify_features.py"], timeout=30)
        self.assertIn("complete --root", self.plan())

        feature_guard.complete_contract(self.root, [], [])
        output = self.plan()
        self.assertIn("checkpoint --root", output)
        self.assertIn("还没有保存回退点", output)

    def test_flags_pending_formal_version_and_missing_release_review(self) -> None:
        self.scaffold()
        versions = "# Versions\n\n| Version | User-visible result | Verification | Status |\n| --- | --- | --- | --- |\n| v1.0.0 | Baseline | suite:all-tests | recoverable |\n"
        (self.root / "docs/VERSIONS.md").write_text(versions, encoding="utf-8")
        self.git("add", "docs/VERSIONS.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "record version row")
        output = self.plan()
        self.assertIn("v1.0.0 还没有本地标签", output)
        self.assertIn("RELEASE-REVIEW.md 缺失", output)
        self.assertIn("21 维终审", output)


if __name__ == "__main__":
    unittest.main()
