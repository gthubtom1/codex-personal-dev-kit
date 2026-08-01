from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/bootstrap/install.ps1"
MARKETPLACE_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/bootstrap/install-marketplace.ps1"
DIAGNOSE_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/bootstrap/diagnose.ps1"
PLUGIN_MANIFEST = REPO_ROOT / "plugins/codex-personal-dev-kit/.codex-plugin/plugin.json"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL, "PowerShell is required")
class InstallScriptTests(unittest.TestCase):
    def run_script(
        self,
        script: Path,
        *arguments: str,
        expected: int = 0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                *arguments,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=process_env,
        )
        self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def run_install(self, codex_home: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess:
        return self.run_script(INSTALL_SCRIPT, "-CodexHome", str(codex_home), *arguments, expected=expected)

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
            source = json.loads((codex_home / "codex-dev-kit/source.json").read_text(encoding="utf-8"))
            self.assertEqual(source["sourceType"], "git")
            self.assertEqual(source["ref"], "v0.1.0")
            self.assertEqual(source["pluginVersion"], json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))["version"])

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

    def test_marketplace_install_uses_explicit_runnable_codex_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_codex = root / "codex.cmd"
            command_log = root / "codex-commands.log"
            fake_codex.write_text('@echo %*>>"%CODEX_TEST_LOG%"\r\n@exit /b 0\r\n', encoding="ascii")

            self.run_script(
                MARKETPLACE_SCRIPT,
                "-Marketplace",
                "OWNER/codex-dev-kit",
                "-Ref",
                "v0.1.0",
                "-Apply",
                env={"CODEX_CLI": str(fake_codex), "CODEX_TEST_LOG": str(command_log)},
            )

            commands = command_log.read_text(encoding="utf-8")
            self.assertIn("--version", commands)
            self.assertIn("plugin marketplace add OWNER/codex-dev-kit --ref v0.1.0", commands)
            self.assertIn("plugin add codex-personal-dev-kit@codex-dev-kit", commands)

    def test_local_marketplace_install_omits_git_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marketplace = root / "local-marketplace"
            (marketplace / ".agents/plugins").mkdir(parents=True)
            (marketplace / ".agents/plugins/marketplace.json").write_text('{"name":"codex-dev-kit","plugins":[]}', encoding="utf-8")
            fake_codex = root / "codex.cmd"
            command_log = root / "codex-commands.log"
            fake_codex.write_text('@echo %*>>"%CODEX_TEST_LOG%"\r\n@exit /b 0\r\n', encoding="ascii")

            self.run_script(
                MARKETPLACE_SCRIPT,
                "-Marketplace",
                str(marketplace),
                "-Apply",
                env={"CODEX_CLI": str(fake_codex), "CODEX_TEST_LOG": str(command_log)},
            )

            commands = command_log.read_text(encoding="utf-8")
            self.assertIn(f"plugin marketplace add {marketplace}", commands)
            self.assertNotIn("--ref", commands)

    def test_diagnose_detects_local_head_dirty_state_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marketplace = root / "marketplace"
            plugin_root = marketplace / "plugins/codex-personal-dev-kit/.codex-plugin"
            plugin_root.mkdir(parents=True)
            (marketplace / ".agents/plugins").mkdir(parents=True)
            (marketplace / ".agents/plugins/marketplace.json").write_text('{"name":"codex-dev-kit","plugins":[]}', encoding="utf-8")
            manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
            (plugin_root / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
            subprocess.run(["git", "-C", str(marketplace), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "-C", str(marketplace), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-C", str(marketplace), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            codex_home = root / "codex-home"
            self.run_install(codex_home, "-Marketplace", str(marketplace), "-Apply")
            cache = codex_home / f"plugins/cache/codex-dev-kit/codex-personal-dev-kit/{manifest['version']}"
            cache.mkdir(parents=True)
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1"=="--version" echo codex-test 1.0\r\n'
                f'@if "%1"=="plugin" if "%2"=="list" echo codex-personal-dev-kit installed, enabled {manifest["version"]}\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )
            result = self.run_script(DIAGNOSE_SCRIPT, "-CodexHome", str(codex_home), env={"CODEX_CLI": str(fake_codex)})
            self.assertIn("Local source HEAD", result.stdout)

            (marketplace / "dirty.txt").write_text("dirty", encoding="utf-8")
            dirty = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertIn("Local source working tree", dirty.stdout)


if __name__ == "__main__":
    unittest.main()
