from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL, "PowerShell is required")
class WorkspaceScriptTests(unittest.TestCase):
    def run_script(self, script: str, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT_ROOT / script), *arguments],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def git(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_workspace_preview_apply_idempotence_and_independent_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            legacy_workspace = Path(directory) / "legacy-mother"
            (legacy_workspace / ".codex").mkdir(parents=True)
            (legacy_workspace / ".codex/config.toml").write_text(
                'model = "gpt-5.5"\n\n[features]\ngoals = true\n',
                encoding="utf-8",
            )
            self.run_script("bootstrap-workspace.ps1", "-WorkspaceRoot", str(legacy_workspace), "-Apply")
            legacy_config = (legacy_workspace / ".codex/config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.5"', legacy_config)
            self.assertIn('default_subagent_model = "gpt-5.6-luna"', legacy_config)
            self.assertIn('default_subagent_reasoning_effort = "max"', legacy_config)
            self.assertIn("max_concurrent_threads_per_session = 6", legacy_config)

            workspace = Path(directory) / "mother"
            self.run_script("bootstrap-workspace.ps1", "-WorkspaceRoot", str(workspace))
            self.assertFalse(workspace.exists())

            self.run_script("bootstrap-workspace.ps1", "-WorkspaceRoot", str(workspace), "-Apply")
            self.assertTrue((workspace / "projects").is_dir())
            self.assertTrue((workspace / "archives").is_dir())
            self.assertFalse((workspace / ".git").exists())
            config = json.loads((workspace / "workspace.json").read_text(encoding="utf-8"))
            self.assertEqual(config["projectsDirectory"], "projects")

            agents = workspace / "AGENTS.md"
            agents_text = agents.read_text(encoding="utf-8")
            self.assertIn("Existing-project development starts only after the user opens that exact project folder", agents_text)
            self.assertIn(str(workspace), agents_text)
            self.assertIn(str(SCRIPT_ROOT.parent / "skills"), agents_text)
            self.assertNotIn("{{WORKSPACE_ROOT}}", agents_text)
            self.assertNotIn("{{DEV_KIT_SKILLS_ROOT}}", agents_text)
            workspace_config = workspace / ".codex/config.toml"
            self.assertTrue(workspace_config.is_file())
            config_text = workspace_config.read_text(encoding="utf-8")
            self.assertIn('default_subagent_model = "gpt-5.6-luna"', config_text)
            self.assertIn('default_subagent_reasoning_effort = "max"', config_text)
            agents.write_text(agents.read_text(encoding="utf-8") + "\nCUSTOM-WORKSPACE-RULE\n", encoding="utf-8")
            self.run_script("bootstrap-workspace.ps1", "-WorkspaceRoot", str(workspace), "-Apply")
            self.assertIn("CUSTOM-WORKSPACE-RULE", agents.read_text(encoding="utf-8"))

            self.run_script("create-project.ps1", "-WorkspaceRoot", str(workspace), "-ProjectName", "alpha")
            self.assertFalse((workspace / "projects/alpha").exists())

            self.run_script("create-project.ps1", "-WorkspaceRoot", str(workspace), "-ProjectName", "alpha", "-Apply")
            self.run_script("create-project.ps1", "-WorkspaceRoot", str(workspace), "-ProjectName", "beta", "-Apply")
            alpha = (workspace / "projects/alpha").resolve()
            beta = (workspace / "projects/beta").resolve()

            for project in (alpha, beta):
                top = self.git(project, "rev-parse", "--show-toplevel")
                self.assertEqual(top.returncode, 0, top.stderr)
                self.assertEqual(Path(top.stdout.strip()).resolve(), project)
                log = self.git(project, "log", "-1", "--pretty=%s")
                self.assertEqual(log.stdout.strip(), "checkpoint: initialize project")
                ignored = self.git(project, "check-ignore", ".codex/current-change.json")
                self.assertEqual(ignored.returncode, 0)
                ignored_plan = self.git(project, "check-ignore", ".codex/active-plan.md")
                self.assertEqual(ignored_plan.returncode, 0)
                self.assertTrue((project / "docs/adr/INDEX.md").is_file())
                self.assertFalse((project / ".codex/hooks.json").exists())
                project_agents = (project / "AGENTS.md").read_text(encoding="utf-8")
                self.assertIn(str(workspace / "AGENTS.md"), project_agents)
                self.assertNotIn("D:\\开发\\AGENTS.md", project_agents)

            self.assertNotEqual(alpha, beta)
            self.assertNotEqual((alpha / ".git").resolve(), (beta / ".git").resolve())
            mother_git = self.git(workspace, "rev-parse", "--show-toplevel")
            self.assertNotEqual(mother_git.returncode, 0)

            duplicate = self.run_script(
                "create-project.ps1",
                "-WorkspaceRoot",
                str(workspace),
                "-ProjectName",
                "alpha",
                "-Apply",
                expected=1,
            )
            self.assertIn("already exists", duplicate.stdout)

    def test_create_project_auto_initializes_a_new_mother_folder_for_beginner_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "new-mother"
            self.run_script(
                "create-project.ps1",
                "-WorkspaceRoot",
                str(workspace),
                "-ProjectName",
                "first-app",
                "-Apply",
            )
            self.assertTrue((workspace / "workspace.json").is_file())
            project = workspace / "projects/first-app"
            self.assertTrue(project.is_dir())
            self.assertEqual(Path(self.git(project, "rev-parse", "--show-toplevel").stdout.strip()).resolve(), project.resolve())
            self.assertEqual(self.git(project, "log", "-1", "--pretty=%s").stdout.strip(), "checkpoint: initialize project")

    def test_existing_agent_defaults_are_preserved_when_merging_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "custom"
            (workspace / ".codex").mkdir(parents=True)
            (workspace / ".codex/config.toml").write_text(
                '[agents]\n'
                'enabled = false\n'
                'default_subagent_model = "gpt-5.6-sol"\n'
                'default_subagent_reasoning_effort = "high"\n',
                encoding="utf-8",
            )
            self.run_script("bootstrap-workspace.ps1", "-WorkspaceRoot", str(workspace), "-Apply")
            config = (workspace / ".codex/config.toml").read_text(encoding="utf-8")
            self.assertIn("enabled = false", config)
            self.assertIn('default_subagent_model = "gpt-5.6-sol"', config)
            self.assertIn('default_subagent_reasoning_effort = "high"', config)
            self.assertIn("max_concurrent_threads_per_session = 6", config)

    def test_bootstrap_existing_project_preserves_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "existing"
            project.mkdir()
            readme = project / "README.md"
            readme.write_text("# Existing user project\n", encoding="utf-8")
            (project / ".codex").mkdir()
            (project / ".codex/config.toml").write_text(
                'model = "gpt-5.5"\n\n[features]\ngoals = true\n',
                encoding="utf-8",
            )

            self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(project),
                "-WorkspaceRoot",
                str(Path(directory)),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
            )
            self.assertEqual(readme.read_text(encoding="utf-8"), "# Existing user project\n")
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / "docs/FEATURES.md").is_file())
            self.assertFalse((project / ".codex/hooks.json").exists())
            project_config = (project / ".codex/config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.5"', project_config)
            self.assertIn('default_subagent_model = "gpt-5.6-luna"', project_config)
            self.assertIn('default_subagent_reasoning_effort = "max"', project_config)
            self.assertIn("max_concurrent_threads_per_session = 6", project_config)
            self.assertEqual(self.git(project, "rev-parse", "--show-toplevel").returncode, 0)
            self.assertEqual(self.git(project, "log", "-1", "--pretty=%s").stdout.strip(), "checkpoint: initialize project")
            self.assertEqual(self.git(project, "status", "--porcelain").stdout.strip(), "")
            tracked = self.git(project, "ls-files", "README.md")
            self.assertEqual(tracked.stdout.strip(), "README.md")

    def test_bootstrap_project_does_not_install_lifecycle_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "existing"
            project.mkdir()
            codex_home = root / "codex-home"
            runtime = codex_home / "codex-dev-kit"
            (runtime / "scripts").mkdir(parents=True)
            (runtime / "scripts/feature_guard.py").write_text("# installed guard\n", encoding="utf-8")
            (runtime / "scripts/pre_tool_guard.py").write_text("# installed guard\n", encoding="utf-8")
            (runtime / "source.json").write_text(json.dumps({"schemaVersion": 2, "mode": "standalone"}), encoding="utf-8")

            self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(project),
                "-WorkspaceRoot",
                str(root),
                "-CodexHome",
                str(codex_home),
                "-Apply",
            )

            self.assertFalse((project / ".codex/hooks.json").exists())

    def test_existing_project_baseline_stops_before_generated_or_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "unsafe-existing"
            (project / "node_modules/pkg").mkdir(parents=True)
            (project / "node_modules/pkg/index.js").write_text("generated\n", encoding="utf-8")
            (project / ".gitignore").write_text("# Existing project intentionally missing dependency ignores\n", encoding="utf-8")

            result = self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(project),
                "-WorkspaceRoot",
                str(Path(directory)),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
                expected=1,
            )
            self.assertIn("Baseline checkpoint stopped", result.stdout)
            self.assertIn("node_modules/pkg/index.js", result.stdout)
            self.assertNotEqual(self.git(project, "rev-parse", "--verify", "HEAD").returncode, 0)

    def test_existing_project_baseline_excludes_secret_names_and_stops_on_secret_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            named_secret = root / "named-secret"
            named_secret.mkdir()
            (named_secret / ".npmrc").write_text("//registry.npmjs.org/:_authToken=real-looking-token-value-123456\n", encoding="utf-8")
            (named_secret / ".env.sample").write_text("API_KEY=replace-me\n", encoding="utf-8")
            self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(named_secret),
                "-WorkspaceRoot",
                str(root),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
            )
            self.assertEqual(self.git(named_secret, "rev-parse", "--verify", "HEAD").returncode, 0)
            self.assertEqual(self.git(named_secret, "check-ignore", ".npmrc").returncode, 0)
            self.assertEqual(self.git(named_secret, "ls-files", ".npmrc").stdout.strip(), "")
            self.assertNotEqual(self.git(named_secret, "check-ignore", ".env.sample").returncode, 0)
            self.assertEqual(self.git(named_secret, "ls-files", ".env.sample").stdout.strip(), ".env.sample")

            content_secret = root / "content-secret"
            content_secret.mkdir()
            (content_secret / "settings.txt").write_text(
                "client_secret = this-is-a-real-looking-secret-value-123456\n",
                encoding="utf-8",
            )
            content_result = self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(content_secret),
                "-WorkspaceRoot",
                str(root),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
                expected=1,
            )
            self.assertIn("appear to contain credentials", content_result.stdout)
            self.assertIn("settings.txt", content_result.stdout)
            self.assertNotEqual(self.git(content_secret, "rev-parse", "--verify", "HEAD").returncode, 0)

            json_secret = root / "json-secret"
            json_secret.mkdir()
            (json_secret / "config.json").write_text(
                '{"clientSecret":"this-is-a-real-looking-json-secret-123456"}\n',
                encoding="utf-8",
            )
            json_result = self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(json_secret),
                "-WorkspaceRoot",
                str(root),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
                expected=1,
            )
            self.assertIn("config.json", json_result.stdout)
            self.assertNotEqual(self.git(json_secret, "rev-parse", "--verify", "HEAD").returncode, 0)

            utf16_secret = root / "utf16-secret"
            utf16_secret.mkdir()
            (utf16_secret / "settings.json").write_text(
                '{"clientSecret":"this-is-a-real-looking-utf16-secret-123456"}\n',
                encoding="utf-16",
            )
            utf16_result = self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(utf16_secret),
                "-WorkspaceRoot",
                str(root),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
                expected=1,
            )
            self.assertIn("settings.json", utf16_result.stdout)
            self.assertNotEqual(self.git(utf16_secret, "rev-parse", "--verify", "HEAD").returncode, 0)

            large_secret = root / "large-secret"
            large_secret.mkdir()
            (large_secret / "large.json").write_text(
                (" " * (3 * 1024 * 1024)) + '\n{"password":"this-is-a-real-looking-large-secret-123456"}\n',
                encoding="utf-8",
            )
            large_result = self.run_script(
                "bootstrap-project.ps1",
                "-ProjectRoot",
                str(large_secret),
                "-WorkspaceRoot",
                str(root),
                "-Apply",
                "-InitializeGit",
                "-CreateBaselineCheckpoint",
                expected=1,
            )
            self.assertIn("large.json", large_result.stdout)
            self.assertNotEqual(self.git(large_secret, "rev-parse", "--verify", "HEAD").returncode, 0)


if __name__ == "__main__":
    unittest.main()
