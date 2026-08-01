from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
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

    def test_reports_stale_plan_oversized_chat_log_missing_next_action_and_adr_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/adr").mkdir(parents=True)
            (root / "docs/history").mkdir(parents=True)
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs/ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "docs/ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Current Status\n\n## Milestone\n\nIn progress.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                """# Features

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Keep setting | Settings -> save | Setting remains available. | settings test | critical | active |
""",
                encoding="utf-8",
            )
            (root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
            active_plan = root / ".codex/active-plan.md"
            active_plan.write_text("# Old plan\n", encoding="utf-8")
            old = time.time() - (audit_project.ACTIVE_PLAN_STALE_DAYS + 1) * 86400
            active_plan.touch()
            os.utime(active_plan, (old, old))
            (root / "docs/history/development-notes.md").write_text("x" * (audit_project.OVERSIZED_HISTORY_BYTES + 1), encoding="utf-8")
            for number in range(1, 4):
                (root / f"docs/adr/{number:04d}-decision.md").write_text(f"# ADR {number}\n", encoding="utf-8")
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("status-next-action-missing", codes)
            self.assertIn("stale-active-plan", codes)
            self.assertIn("oversized-history-log", codes)
            self.assertIn("adr-index-missing", codes)


if __name__ == "__main__":
    unittest.main()
