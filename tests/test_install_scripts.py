from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/bootstrap/install.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL, "PowerShell is required")
class InstallScriptTests(unittest.TestCase):
    def run_install(self, codex_home: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(INSTALL_SCRIPT),
                "-CodexHome",
                str(codex_home),
                *arguments,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def test_preview_apply_preserve_custom_content_and_backup_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex-home"
            self.run_install(codex_home, "-Marketplace", "OWNER/codex-dev-kit", "-Ref", "v0.1.0")
            self.assertFalse(codex_home.exists())

            self.run_install(codex_home, "-Marketplace", "OWNER/codex-dev-kit", "-Ref", "v0.1.0", "-Apply")
            agents = codex_home / "AGENTS.md"
            self.assertIn("<!-- codex-dev-kit:start -->", agents.read_text(encoding="utf-8"))
            self.assertTrue((codex_home / "rules/codex-dev-kit.rules").is_file())
            self.assertTrue((codex_home / "agents/codex-kit-reviewer.toml").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/source.json").is_file())
            self.assertFalse((codex_home / "config.toml").exists())

            content = agents.read_text(encoding="utf-8")
            customized = "# My personal rule\n\n" + content.replace(
                "Assume the user is new to software development.",
                "OUTDATED MANAGED CONTENT.",
                1,
            )
            agents.write_text(customized, encoding="utf-8")
            self.run_install(codex_home, "-Marketplace", "OWNER/codex-dev-kit", "-Ref", "v0.1.0", "-Apply")

            updated = agents.read_text(encoding="utf-8")
            self.assertIn("# My personal rule", updated)
            self.assertNotIn("OUTDATED MANAGED CONTENT", updated)
            backups = list((codex_home / "backups/codex-dev-kit").rglob("AGENTS.md"))
            self.assertTrue(backups)
            self.assertIn("OUTDATED MANAGED CONTENT", backups[-1].read_text(encoding="utf-8"))

    def test_rejects_unpinned_marketplace_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_install(
                Path(directory) / "codex-home",
                "-Marketplace",
                "OWNER/codex-dev-kit",
                "-Ref",
                "main",
                expected=1,
            )
            self.assertIn("fixed release tag or commit", result.stdout)


if __name__ == "__main__":
    unittest.main()
