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

    def run_install(
        self,
        codex_home: Path,
        workspace: Path,
        *arguments: str,
        expected: int = 0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        workspace.mkdir(parents=True, exist_ok=True)
        agents = workspace / "AGENTS.md"
        if not agents.exists():
            agents.write_text("# Detailed workspace instructions\n", encoding="utf-8")
        return self.run_script(
            INSTALL_SCRIPT,
            "-CodexHome",
            str(codex_home),
            "-WorkspaceRoot",
            str(workspace),
            *arguments,
            expected=expected,
            env=env,
        )

    def make_clean_source(self, root: Path) -> tuple[Path, str]:
        source_root = root / "source"
        source_plugin = source_root / "plugins/codex-personal-dev-kit"
        shutil.copytree(REPO_ROOT / "plugins/codex-personal-dev-kit", source_plugin)
        subprocess.run(["git", "-C", str(source_root), "init", "-b", "main"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(source_root), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "-C", str(source_root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        head = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        return source_root, head

    def test_preview_apply_preserve_custom_content_and_backup_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head)
            self.assertFalse(codex_home.exists())

            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")
            agents = codex_home / "AGENTS.md"
            self.assertIn("<!-- codex-dev-kit:start -->", agents.read_text(encoding="utf-8"))
            self.assertIn(str(workspace / "AGENTS.md"), agents.read_text(encoding="utf-8"))
            self.assertTrue((codex_home / "rules/codex-dev-kit.rules").is_file())
            self.assertFalse((codex_home / "agents/codex-kit-reviewer.toml").exists())
            self.assertTrue((codex_home / "skills/codex-development-assistant/SKILL.md").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/INDEX.md").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/scripts/feature_guard.py").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/source.json").is_file())
            self.assertFalse((codex_home / "config.toml").exists())
            source = json.loads((codex_home / "codex-dev-kit/source.json").read_text(encoding="utf-8"))
            self.assertEqual(source["sourceType"], "local")
            self.assertEqual(source["mode"], "standalone")
            self.assertEqual(source["ref"], head)
            self.assertEqual(source["version"], json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))["version"])

            content = agents.read_text(encoding="utf-8")
            customized = "# My personal rule\n\n" + content.replace(
                "The user is a complete software-development beginner.",
                "OUTDATED MANAGED CONTENT.",
                1,
            )
            agents.write_text(customized, encoding="utf-8")
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")

            updated = agents.read_text(encoding="utf-8")
            self.assertIn("# My personal rule", updated)
            self.assertNotIn("OUTDATED MANAGED CONTENT", updated)
            backups = list((codex_home / "backups/codex-dev-kit").rglob("AGENTS.md"))
            self.assertTrue(backups)
            self.assertIn("OUTDATED MANAGED CONTENT", backups[-1].read_text(encoding="utf-8"))

    def test_rejects_nonlocal_standalone_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_install(
                Path(directory) / "codex-home",
                Path(directory) / "workspace",
                "-Source",
                "OWNER/codex-dev-kit",
                expected=1,
            )
            self.assertIn("requires a local Git checkout", result.stdout)

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
            source_root, _ = self.make_clean_source(root)

            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Apply")
            result = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
            )
            self.assertIn("Standalone source metadata", result.stdout)
            self.assertIn("Local source HEAD", result.stdout)
            self.assertIn("Local source version", result.stdout)

            (source_root / "dirty.txt").write_text("dirty", encoding="utf-8")
            dirty_diagnosis = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
                expected=1,
            )
            self.assertIn("Local source working tree", dirty_diagnosis.stdout)
            dirty = self.run_install(
                root / "second-codex-home",
                workspace,
                "-Source",
                str(source_root),
                expected=1,
            )
            self.assertIn("uncommitted changes", dirty.stdout)

    def test_diagnose_detects_plugin_only_legacy_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, _ = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Apply")
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@custom-market installed, enabled 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )

            diagnosis = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertIn("Legacy Dev Kit Plugin not installed", diagnosis.stdout)
            self.assertRegex(diagnosis.stdout, r"Legacy Dev Kit Plugin not installed\s+False")

    def test_installed_update_reuses_saved_local_source_and_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")

            installed_update = codex_home / "codex-dev-kit/scripts/bootstrap/update.ps1"
            result = self.run_script(
                installed_update,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
            )
            self.assertIn("Preview only", result.stdout)
            source = json.loads((codex_home / "codex-dev-kit/source.json").read_text(encoding="utf-8"))
            self.assertEqual(source["source"], str(source_root))
            self.assertEqual(source["ref"], head)

    def test_installed_update_recovers_custom_workspace_root_from_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "custom-workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")
            agents = codex_home / "AGENTS.md"
            agents.write_text(agents.read_text(encoding="utf-8").replace(str(workspace / "AGENTS.md"), "D:\\wrong\\AGENTS.md"), encoding="utf-8")

            installed_update = codex_home / "codex-dev-kit/scripts/bootstrap/update.ps1"
            self.run_script(
                installed_update,
                "-CodexHome",
                str(codex_home),
                "-Apply",
            )

            updated_agents = agents.read_text(encoding="utf-8")
            self.assertIn(str(workspace / "AGENTS.md"), updated_agents)
            self.assertNotIn("D:\\wrong\\AGENTS.md", updated_agents)

    def test_legacy_install_requires_explicit_migration_and_backs_up_removed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            legacy_agent = codex_home / "agents/codex-kit-reviewer.toml"
            legacy_agent.parent.mkdir(parents=True)
            legacy_agent.write_text("name = \"codex-kit-reviewer\"\n", encoding="utf-8")
            legacy_source = codex_home / "codex-dev-kit/source.json"
            legacy_source.parent.mkdir(parents=True)
            legacy_source.write_text(
                json.dumps(
                    {
                        "marketplace": str(source_root),
                        "ref": head,
                        "marketplaceName": "codex-dev-kit",
                        "plugin": "codex-personal-dev-kit",
                    }
                ),
                encoding="utf-8",
            )
            global_hooks = codex_home / "hooks.json"
            global_hooks.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "commandWindows": "python C:/legacy/codex-dev-kit/scripts/feature_guard.py hook",
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            blocked = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                expected=1,
            )
            self.assertIn("Legacy Codex Dev Kit state was detected", blocked.stdout)
            self.assertTrue(legacy_agent.exists())
            self.assertTrue(global_hooks.exists())

            fake_codex = root / "codex.cmd"
            command_log = root / "codex-commands.log"
            fake_codex.write_text(
                '@echo %CODEX_HOME% %*>>"%CODEX_TEST_LOG%"\r\n'
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@codex-dev-kit installed, enabled 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )
            self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                "-MigrateLegacy",
                env={"CODEX_CLI": str(fake_codex), "CODEX_TEST_LOG": str(command_log)},
            )

            self.assertFalse(legacy_agent.exists())
            self.assertFalse(global_hooks.exists())
            installed_source = json.loads(legacy_source.read_text(encoding="utf-8"))
            self.assertEqual(installed_source["mode"], "standalone")
            commands = command_log.read_text(encoding="utf-8")
            self.assertIn("plugin remove codex-personal-dev-kit@codex-dev-kit", commands)
            self.assertIn(f"{codex_home} plugin remove codex-personal-dev-kit@codex-dev-kit", commands)
            backups = list((codex_home / "backups/codex-dev-kit").rglob("codex-kit-reviewer.toml"))
            self.assertTrue(backups)
            hook_backups = list((codex_home / "backups/codex-dev-kit").rglob("hooks.json"))
            self.assertTrue(hook_backups)

    def test_plugin_only_legacy_install_is_detected_without_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            workspace = root / "workspace"
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@codex-dev-kit installed, enabled 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )

            blocked = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertIn("legacy Plugin is still installed", blocked.stdout)
            self.assertFalse((codex_home / "codex-dev-kit/source.json").exists())

    def test_plugin_only_custom_marketplace_is_detected_without_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            workspace = root / "workspace"
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@private-market installed, enabled 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )

            blocked = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertIn("private-market", blocked.stdout)
            self.assertFalse((codex_home / "codex-dev-kit/source.json").exists())

    def test_not_installed_plugin_listing_does_not_block_install_or_diagnosis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            workspace = root / "workspace"
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@private-market not installed 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )

            self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                env={"CODEX_CLI": str(fake_codex)},
            )
            diagnosis = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertRegex(diagnosis.stdout, r"Legacy Dev Kit Plugin not installed\s+True")

    def test_damaged_global_agents_markers_stop_before_legacy_switch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            (codex_home / "AGENTS.md").write_text("<!-- codex-dev-kit:start -->\ndamaged\n", encoding="utf-8")
            legacy_agent = codex_home / "agents/codex-kit-reviewer.toml"
            legacy_agent.parent.mkdir()
            legacy_agent.write_text("name = \"legacy\"\n", encoding="utf-8")
            workspace = root / "workspace"
            fake_codex = root / "codex.cmd"
            command_log = root / "codex-commands.log"
            fake_codex.write_text(
                '@echo %*>>"%CODEX_TEST_LOG%"\r\n'
                '@if "%1 %2"=="plugin list" echo codex-personal-dev-kit@private-market installed, enabled 0.1.0 C:\\legacy\r\n'
                '@exit /b 0\r\n',
                encoding="ascii",
            )

            blocked = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                "-MigrateLegacy",
                expected=1,
                env={"CODEX_CLI": str(fake_codex), "CODEX_TEST_LOG": str(command_log)},
            )
            self.assertIn("incomplete or duplicate", blocked.stdout)
            self.assertTrue(legacy_agent.exists())
            self.assertNotIn("plugin remove", command_log.read_text(encoding="utf-8"))
            self.assertFalse((codex_home / "codex-dev-kit/source.json").exists())

    def test_legacy_migration_removes_only_dev_kit_hook_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            global_hooks = codex_home / "hooks.json"
            global_hooks.parent.mkdir(parents=True)
            global_hooks.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {"type": "command", "commandWindows": "python C:/legacy/codex-dev-kit/scripts/feature_guard.py hook"},
                                        {"type": "prompt", "prompt": "Preserve this user hook"},
                                    ],
                                }
                            ],
                            "SessionStart": [{"matcher": "*", "hooks": [{"type": "prompt", "prompt": "Also preserve this"}]}],
                        }
                    }
                ),
                encoding="utf-8",
            )
            fake_codex = root / "codex.cmd"
            fake_codex.write_text('@exit /b 0\r\n', encoding="ascii")

            self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                "-MigrateLegacy",
                env={"CODEX_CLI": str(fake_codex)},
            )

            preserved = json.loads(global_hooks.read_text(encoding="utf-8"))
            serialized = json.dumps(preserved)
            self.assertNotIn("feature_guard.py", serialized)
            self.assertIn("Preserve this user hook", serialized)
            self.assertIn("Also preserve this", serialized)
            self.assertTrue(list((codex_home / "backups/codex-dev-kit").rglob("hooks.json")))

    def test_ambiguous_hook_reference_stops_without_deleting_user_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            codex_home.mkdir()
            workspace = root / "workspace"
            global_hooks = codex_home / "hooks.json"
            original = {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "commandWindows": "python C:/tools/codex-dev-kit/custom_backup.py",
                                }
                            ],
                        }
                    ]
                }
            }
            global_hooks.write_text(json.dumps(original), encoding="utf-8")
            fake_codex = root / "codex.cmd"
            fake_codex.write_text('@exit /b 0\r\n', encoding="ascii")

            blocked = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
                "-MigrateLegacy",
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertIn("unrecognized legacy Dev Kit reference", blocked.stdout)
            self.assertEqual(json.loads(global_hooks.read_text(encoding="utf-8")), original)
            self.assertFalse((codex_home / "codex-dev-kit/source.json").exists())


if __name__ == "__main__":
    unittest.main()
