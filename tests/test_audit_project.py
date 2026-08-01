from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import audit_project  # noqa: E402


class AuditProjectTests(unittest.TestCase):
    def test_reports_missing_critical_verification_and_unignored_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / ".codex").mkdir()
            for relative in ("AGENTS.md", "docs/PROJECT.md", "docs/ROADMAP.md", "docs/ARCHITECTURE.md", "docs/STATUS.md"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Current\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                """# Features

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Keep setting |  | Setting remains available. | Not yet confirmed | critical | active |
""",
                encoding="utf-8",
            )
            (root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("feature-entry-missing", codes)
            self.assertIn("feature-verification-missing", codes)
            self.assertIn("change-contract-not-ignored", codes)


if __name__ == "__main__":
    unittest.main()
