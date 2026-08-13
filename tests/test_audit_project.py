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
            (root / "docs/reference.md").write_text("x" * (audit_project.OVERSIZED_DOCUMENT_BYTES + 1), encoding="utf-8")
            for number in range(1, 4):
                (root / f"docs/adr/{number:04d}-decision.md").write_text(f"# ADR {number}\n", encoding="utf-8")
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("status-next-action-missing", codes)
            self.assertIn("stale-active-plan", codes)
            self.assertIn("oversized-history-log", codes)
            self.assertIn("oversized-document", codes)
            self.assertIn("adr-index-missing", codes)

    def test_reports_oversized_domain_and_adr_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/features").mkdir(parents=True)
            (root / "docs/adr").mkdir(parents=True)
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs/ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "docs/ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Current Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                """# Features

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Keep setting | Settings -> save | Setting remains available. | test:tests/check.py | critical | active |
""",
                encoding="utf-8",
            )
            (root / ".codex/config.toml").write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            (root / "docs/features/settings.md").write_text("# Settings\n" + ("detail\n" * 1001), encoding="utf-8")
            (root / "docs/adr/0001-large.md").write_text("# ADR\n" + ("detail\n" * 801), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("domain-document-budget", codes)
            self.assertIn("adr-document-budget", codes)

    def test_reports_broken_markdown_links_and_orphan_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir(parents=True)
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/INDEX.md").write_text(
                """# Map

- [Project](PROJECT.md)
- [Features](FEATURES.md)
- [Roadmap](ROADMAP.md)
- [Architecture](ARCHITECTURE.md)
- [Status](STATUS.md)
- [Missing](missing.md)
- [Bad anchor](PROJECT.md#does-not-exist)
""",
                encoding="utf-8",
            )
            (root / "docs/PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs/ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "docs/ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                """# Features

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Keep setting | Settings -> save | Setting remains available. | test:tests/check.py | critical | active |
""",
                encoding="utf-8",
            )
            (root / "docs/orphan.md").write_text("# Orphan\n", encoding="utf-8")
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("broken-document-link", codes)
            self.assertIn("broken-document-anchor", codes)
            self.assertIn("orphan-document", codes)
            self.assertEqual(report["metrics"]["broken_document_link_count"], 1)
            self.assertEqual(report["metrics"]["broken_document_anchor_count"], 1)
            self.assertEqual(report["metrics"]["orphan_document_count"], 1)

    def test_accepts_complete_document_navigation_and_ignores_external_or_code_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs/reference").mkdir(parents=True)
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/INDEX.md").write_text(
                """# Map

- [Project](PROJECT.md)
- [Features](FEATURES.md)
- [Roadmap](ROADMAP.md)
- [Architecture](ARCHITECTURE.md)
- [Status](STATUS.md)
- [Settings details](reference/settings.md)
""",
                encoding="utf-8",
            )
            (root / "docs/PROJECT.md").write_text(
                """# Project

See [the public reference](https://example.com).

```md
[This is an example](missing.md)
```
""",
                encoding="utf-8",
            )
            (root / "docs/ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "docs/ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/reference/settings.md").write_text("# Settings\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                """# Features

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Keep setting | Settings -> save | Setting remains available. | test:tests/check.py | critical | active |
""",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root)
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["metrics"]["broken_document_link_count"], 0)
            self.assertEqual(report["metrics"]["orphan_document_count"], 0)

    def test_dependency_free_package_does_not_require_lockfile_but_declared_dependencies_do(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                "# Features\n\n| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |\n| --- | --- | --- | --- | --- | --- | --- |\n| F-001 | Run | index | Works | test:tests/check.py | critical | active |\n",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            (root / "package.json").write_text('{"name":"no-deps","scripts":{"test":"node --test"}}\n', encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            codes = {item["code"] for item in audit_project.audit(root)["findings"]}
            self.assertNotIn("missing-lockfile", codes)

            (root / "package.json").write_text('{"name":"has-deps","dependencies":{"left-pad":"1.3.0"}}\n', encoding="utf-8")
            report = audit_project.audit(root)
            self.assertIn("missing-lockfile", {item["code"] for item in report["findings"]})

    def test_formal_tags_require_a_complete_versions_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                "# Features\n\n| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |\n| --- | --- | --- | --- | --- | --- | --- |\n| F-001 | Run | index | Works | test:tests/check.py | critical | active |\n",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "-C", str(root), "tag", "v1.0.0"], check=True)

            missing = audit_project.audit(root)
            self.assertIn("versions-index-missing", {item["code"] for item in missing["findings"]})
            (root / "docs/VERSIONS.md").write_text("# Versions\n\n| Version | Result | Verification | Status |\n| --- | --- | --- | --- |\n| v0.9.0 | Old | suite:all-tests | recoverable |\n", encoding="utf-8")
            incomplete = audit_project.audit(root)
            self.assertIn("versions-index-incomplete", {item["code"] for item in incomplete["findings"]})

    def test_reports_large_files_that_no_ignore_rule_covers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / ".codex").mkdir()
            (root / "assets").mkdir()
            (root / "local").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text("# Status\n\n## Next Action\n\nContinue.\n", encoding="utf-8")
            (root / "docs/FEATURES.md").write_text(
                "# Features\n\n| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |\n| --- | --- | --- | --- | --- | --- | --- |\n| F-001 | Run | index | Works | test:tests/check.py | critical | active |\n",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text(
                ".codex/current-change.json\n.codex/active-plan.md\nlocal/\n",
                encoding="utf-8",
            )
            (root / "assets/sample.bin").write_bytes(b"x" * 4096)
            (root / "local/scratch.bin").write_bytes(b"x" * 8192)
            (root / "docs/notes.md").write_text("# Notes\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            report = audit_project.audit(root, large_file_bytes=1024)
            reported = {item["path"] for item in report["findings"] if item["code"] == "large-unignored-file"}
            self.assertIn("assets/sample.bin", reported)
            self.assertNotIn("local/scratch.bin", reported)
            self.assertNotIn("docs/notes.md", reported)
            self.assertEqual(report["metrics"]["large_unignored_file_count"], 1)
            self.assertEqual(report["metrics"]["large_unignored_file_threshold_bytes"], 1024)

            unchanged = audit_project.audit(root)
            self.assertEqual([item for item in unchanged["findings"] if item["code"] == "large-unignored-file"], [])
            self.assertEqual((root / "assets/sample.bin").stat().st_size, 4096)
            self.assertEqual(
                (root / ".gitignore").read_text(encoding="utf-8"),
                ".codex/current-change.json\n.codex/active-plan.md\nlocal/\n",
            )

    def test_status_checkpoint_hash_is_reported_as_volatile_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / ".codex").mkdir()
            (root / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (root / "docs/STATUS.md").write_text(
                "# Status\n\n## Working State\n\n- Last checkpoint: abc1234.\n\n## Next Action\n\nContinue.\n",
                encoding="utf-8",
            )
            (root / "docs/FEATURES.md").write_text(
                "# Features\n\n| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |\n| --- | --- | --- | --- | --- | --- | --- |\n| F-001 | Run | index | Works | test:tests/check.py | critical | active |\n",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text(".codex/current-change.json\n.codex/active-plan.md\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            report = audit_project.audit(root)
            self.assertIn("status-volatile-checkpoint", {item["code"] for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
