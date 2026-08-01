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

    def test_bootstrap_existing_project_preserves_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "existing"
            project.mkdir()
            readme = project / "README.md"
            readme.write_text("# Existing user project\n", encoding="utf-8")

            self.run_script("bootstrap-project.ps1", "-ProjectRoot", str(project), "-Apply", "-InitializeGit")
            self.assertEqual(readme.read_text(encoding="utf-8"), "# Existing user project\n")
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / "docs/FEATURES.md").is_file())
            self.assertEqual(self.git(project, "rev-parse", "--show-toplevel").returncode, 0)


if __name__ == "__main__":
    unittest.main()
