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
DIAGNOSE_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/bootstrap/diagnose.ps1"
RESOLVE_SKILL_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/resolve-skill.ps1"
VALIDATE_SCRIPT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts/validate-kit.ps1"
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
        source_root.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "VERSION", source_root / "VERSION")
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

            installed = self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")
            self.assertIn("Fully exit Codex Desktop", installed.stdout)
            self.assertIn("does not install or merge any native subagent", installed.stdout)
            agents = codex_home / "AGENTS.md"
            self.assertIn("<!-- codex-dev-kit:start -->", agents.read_text(encoding="utf-8"))
            self.assertIn(str(workspace / "AGENTS.md"), agents.read_text(encoding="utf-8"))
            self.assertFalse((codex_home / "rules/codex-dev-kit.rules").exists())
            self.assertFalse((codex_home / "agents/codex-kit-reviewer.toml").exists())
            self.assertTrue((codex_home / "skills/codex-development-assistant/SKILL.md").is_file())
            self.assertTrue((codex_home / "skills/research-and-reuse/SKILL.md").is_file())
            self.assertTrue((codex_home / "skills/integrate-codex-projects/SKILL.md").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/scripts/feature_guard.py").is_file())
            self.assertTrue((codex_home / "codex-dev-kit/source.json").is_file())
            self.assertFalse((codex_home / "config.toml").exists())
            source = json.loads((codex_home / "codex-dev-kit/source.json").read_text(encoding="utf-8"))
            self.assertEqual(source["sourceType"], "local")
            self.assertEqual(source["mode"], "standalone")
            self.assertEqual(source["ref"], head)
            self.assertEqual(source["version"], (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip())

            second = self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")
            agent_lines = [line for line in second.stdout.splitlines() if str(agents) in line]
            self.assertTrue(any("unchanged" in line for line in agent_lines), second.stdout)

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

    def test_install_never_inspects_or_mutates_existing_subagent_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "AGENTS.md").write_text(
                "- 子代理默认请求 `gpt-5.6-luna`。\n"
                "- 原生 agent list 不可用时不启动。\n",
                encoding="utf-8",
            )
            (workspace / ".codex").mkdir()
            config_path = workspace / ".codex/config.toml"
            config_path.write_text(
                '[agents]\n'
                'default_subagent_model = "gpt-5.6-luna"\n',
                encoding="utf-8",
            )

            before_agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
            before_config = config_path.read_text(encoding="utf-8")
            result = self.run_install(
                codex_home,
                workspace,
                "-Source",
                str(source_root),
                "-Ref",
                head,
                "-Apply",
            )

            self.assertNotIn("Legacy Luna", result.stdout)
            self.assertEqual(before_agents, (workspace / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertEqual(before_config, config_path.read_text(encoding="utf-8"))

    def test_validation_script_supports_standalone_runtime_layout(self) -> None:
        text = VALIDATE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("source.json", text)
        self.assertIn("Standalone runtime detected", text)
        self.assertIn("Join-Path $codexHome \"skills\"", text)
        self.assertIn("source validation script", text.lower())
        self.assertIn("reportedRoot", text)

    def test_resolve_skill_uses_exact_standalone_path_and_rejects_guesses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex-home"
            skill_path = codex_home / "skills/prepare-codex-goal/SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("---\nname: prepare-codex-goal\n---\n", encoding="utf-8")

            resolved = self.run_script(
                RESOLVE_SKILL_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-Name",
                "prepare-codex-goal",
            )
            self.assertEqual(Path(resolved.stdout.strip()), skill_path.resolve())

            missing = self.run_script(
                RESOLVE_SKILL_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-Name",
                "missing-skill",
                expected=1,
            )
            self.assertIn("do not prepend '.system'", missing.stdout)

    def test_onboarding_skill_resolves_bootstrap_runtime_without_searching(self) -> None:
        skill = (REPO_ROOT / "plugins/codex-personal-dev-kit/skills/onboard-codex-project/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("<CodexHome>\\codex-dev-kit\\scripts\\bootstrap-project.ps1", skill)
        self.assertIn("source.json", skill)
        self.assertIn("<WorkspaceRoot>\\codex-dev-kit\\plugins\\codex-personal-dev-kit\\scripts\\bootstrap-project.ps1", skill)
        self.assertIn("不得递归搜索整个磁盘", skill)
        self.assertIn("不要联网下载", skill)

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

    def test_rejects_nested_kit_directory_as_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, _ = self.make_clean_source(root)
            result = self.run_install(
                root / "codex-home",
                root / "workspace",
                "-Source",
                str(source_root / "plugins/codex-personal-dev-kit"),
                expected=1,
            )
            self.assertIn("repository root, not the nested kit directory", result.stdout)

    def test_manifest_detects_tampered_managed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, head = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", head, "-Apply")
            manifest = json.loads((codex_home / "codex-dev-kit/managed-files.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["files"])

            skill = codex_home / "skills/codex-development-assistant/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nTAMPERED\n", encoding="utf-8")
            diagnosis = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
                expected=1,
            )
            self.assertIn("Managed files match installed hashes", diagnosis.stdout)
            self.assertIn("codex-development-assistant/SKILL.md", diagnosis.stdout)

    def test_update_removes_unchanged_stale_managed_file_but_preserves_modified_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, _ = self.make_clean_source(root)
            source_scripts = source_root / "plugins/codex-personal-dev-kit/scripts"
            stale_source = source_scripts / "obsolete-test.ps1"
            stale_source.write_text("Write-Host 'obsolete'\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source_root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source_root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "add stale"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            first_head = subprocess.run(
                ["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE
            ).stdout.strip()
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", first_head, "-Apply")
            installed_stale = codex_home / "codex-dev-kit/scripts/obsolete-test.ps1"
            self.assertTrue(installed_stale.is_file())

            stale_source.unlink()
            subprocess.run(["git", "-C", str(source_root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source_root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "remove stale"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            second_head = subprocess.run(
                ["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE
            ).stdout.strip()
            removed = self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", second_head, "-Apply")
            self.assertIn("remove-stale", removed.stdout)
            self.assertFalse(installed_stale.exists())
            self.assertTrue(list((codex_home / "backups/codex-dev-kit").rglob("obsolete-test.ps1")))

            # Recreate an old-manifest scenario and prove a user-modified stale file is retained.
            stale_source.write_text("Write-Host 'obsolete-again'\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source_root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source_root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "restore stale"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            third_head = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", third_head, "-Apply")
            installed_stale.write_text("user customization\n", encoding="utf-8")
            stale_source.unlink()
            subprocess.run(["git", "-C", str(source_root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(source_root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "remove stale again"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            fourth_head = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
            preserved = self.run_install(codex_home, workspace, "-Source", str(source_root), "-Ref", fourth_head, "-Apply")
            self.assertIn("preserve-modified-stale", preserved.stdout)
            self.assertEqual(installed_stale.read_text(encoding="utf-8"), "user customization\n")

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

    def test_diagnose_ignores_subagent_settings_and_hides_sensitive_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root, _ = self.make_clean_source(root)
            codex_home = root / "codex-home"
            workspace = root / "workspace"
            self.run_install(codex_home, workspace, "-Source", str(source_root), "-Apply")
            (codex_home / "config.toml").write_text(
                '[agents]\n'
                'enabled = false\n'
                '\n'
                '[features]\n'
                'multi_agent = false\n'
                '\n'
                'experimental_bearer_token = "do-not-print-this-value"\n'
                'model = "gpt-5.5"\n',
                encoding="utf-8",
            )
            fake_codex = root / "codex.cmd"
            fake_codex.write_text(
                '@if "%1 %2"=="plugin list" echo no legacy plugins\r\n'
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
            self.assertNotIn("Native agents gate", diagnosis.stdout)
            self.assertNotIn("Native multi-agent feature gate", diagnosis.stdout)
            self.assertRegex(diagnosis.stdout, r"No plaintext sensitive Codex key\s+False")
            self.assertIn("Main model remains user-selectable", diagnosis.stdout)
            self.assertNotIn("do-not-print-this-value", diagnosis.stdout)

            project = workspace / "projects" / "budget"
            (project / ".codex").mkdir(parents=True)
            (project / ".codex/config.toml").write_text(
                '[agents]\n'
                'enabled = false\n'
                '\n'
                '[features]\n'
                'multi_agent = false\n',
                encoding="utf-8",
            )
            project_diagnosis = self.run_script(
                DIAGNOSE_SCRIPT,
                "-CodexHome",
                str(codex_home),
                "-WorkspaceRoot",
                str(workspace),
                "-ProjectRoot",
                str(project),
                expected=1,
                env={"CODEX_CLI": str(fake_codex)},
            )
            self.assertNotIn("Native agents gate", project_diagnosis.stdout)
            self.assertNotIn("Native multi-agent feature gate", project_diagnosis.stdout)

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
