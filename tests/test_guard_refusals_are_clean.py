"""A guard refusal is a clean message to the user, never a Python traceback.

exe-product-lifecycle asserts "zero stack trace" on every refusal because a raw
Python traceback dumped at a zero-based user is unreadable and looks like a
crash rather than a decision. codex-dev-kit's guard raises ``GuardError`` with a
plain message and ``main()`` prints ``ERROR: ...`` with exit code 1. This proves
several deterministic refusals stay that way: a controlled non-zero exit with a
user-facing message and no ``Traceback (most recent call last)`` anywhere.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
FEATURE_GUARD_PATH = SCRIPT_ROOT / "feature_guard.py"

FEATURES = """# Feature Map

## Feature Inventory

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Toggle acceleration | Settings control -> save API -> worker | The saved setting controls processing. | test:tests/verify_features.py | critical | active |
"""

TRACEBACK_MARKER = "Traceback (most recent call last)"


class GuardRefusalsAreCleanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".codex").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "AGENTS.md").write_text("# Test project\n", encoding="utf-8")
        (self.root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
        (self.root / ".gitignore").write_text(".codex/current-change.json\n.codex/write-lock.json\n", encoding="utf-8")
        (self.root / "docs/FEATURES.md").write_text(FEATURES, encoding="utf-8")
        (self.root / "docs/STATUS.md").write_text("# Current Status\n\n## Next Action\n\nNothing.\n", encoding="utf-8")
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")

    def git(self, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def guard(self, *args: str) -> subprocess.CompletedProcess:
        environment = dict(os.environ)
        environment["CODEX_WRITE_LOCK_SESSION"] = "session-clean"
        return subprocess.run(
            [sys.executable, str(FEATURE_GUARD_PATH), *args, "--root", str(self.root)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, check=False,
        )

    def assertCleanRefusal(self, result: subprocess.CompletedProcess, label: str) -> None:
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertNotIn(TRACEBACK_MARKER, combined, f"{label} leaked a Python traceback:\n{combined}")
        self.assertEqual(result.returncode, 1, f"{label} should be a clean refusal (exit 1), got {result.returncode}:\n{combined}")
        self.assertIn("ERROR:", result.stderr, f"{label} should print a user-facing ERROR: message:\n{combined}")

    def test_complete_without_contract_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("complete"), "complete without contract")

    def test_stage_without_contract_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("stage", "--path", "docs/STATUS.md"), "stage without contract")

    def test_checkpoint_without_contract_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("checkpoint"), "checkpoint without contract")

    def test_verify_without_contract_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(
            self.guard("verify", "--feature", "F-001", "--", sys.executable, "tests/verify_features.py"),
            "verify without contract",
        )

    def test_illegal_version_name_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("version", "--name", "not-a-version"), "illegal version name")

    def test_restore_missing_version_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("restore-version", "--name", "v9.9.9"), "restore missing version")

    def test_force_unlock_without_a_lock_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("force-unlock", "--confirm-holder", "999999"), "force-unlock without a lock")

    def test_start_with_unknown_feature_is_a_clean_refusal(self) -> None:
        self.assertCleanRefusal(self.guard("start", "--objective", "x", "--verify", "F-404"), "start with unknown feature")

    def test_non_project_root_is_a_clean_refusal(self) -> None:
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        result = subprocess.run(
            [sys.executable, str(FEATURE_GUARD_PATH), "status", "--root", other.name],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertNotIn(TRACEBACK_MARKER, combined, f"non-project root leaked a traceback:\n{combined}")
        self.assertEqual(result.returncode, 1, f"non-project root should refuse cleanly:\n{combined}")
        self.assertIn("ERROR:", result.stderr, f"non-project root should print ERROR::\n{combined}")


if __name__ == "__main__":
    unittest.main()
