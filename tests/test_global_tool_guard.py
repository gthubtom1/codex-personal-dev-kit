from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "plugins/codex-personal-dev-kit/skills/codex-safe-development/scripts/install_global_tool.py"
SPEC = importlib.util.spec_from_file_location("install_global_tool", SCRIPT_PATH)
assert SPEC and SPEC.loader
install_global_tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install_global_tool
SPEC.loader.exec_module(install_global_tool)


class GlobalToolGuardTests(unittest.TestCase):
    def test_requires_exact_package_version_and_scope_confirmation(self) -> None:
        with self.assertRaisesRegex(install_global_tool.InstallGuardError, "exactly match"):
            install_global_tool.install_authorized_winget_tool(
                "Git.Git", "2.50.0", "user", "Git.Git", "2.49.0", "user"
            )

    def test_installs_and_verifies_one_exact_winget_tool(self) -> None:
        responses = [
            subprocess.CompletedProcess(["winget", "list"], 1, "No installed package found"),
            subprocess.CompletedProcess(["winget", "show"], 0, "Git Git.Git 2.50.0"),
            subprocess.CompletedProcess(["winget", "install"], 0, "Successfully installed"),
            subprocess.CompletedProcess(["winget", "list"], 0, "Git Git.Git 2.50.0 winget"),
        ]
        with mock.patch.object(install_global_tool.os, "name", "nt"), mock.patch.object(
            install_global_tool.shutil, "which", return_value="winget.exe"
        ), mock.patch.object(install_global_tool, "_run", side_effect=responses) as run:
            result = install_global_tool.install_authorized_winget_tool(
                "Git.Git", "2.50.0", "user", "Git.Git", "2.50.0", "user"
            )
        self.assertEqual(result.state, "installed")
        install_command = run.call_args_list[2].args[0]
        self.assertIn("--exact", install_command)
        self.assertIn("--version", install_command)
        self.assertIn("2.50.0", install_command)
        self.assertIn("--scope", install_command)
        self.assertIn("user", install_command)

    def test_refuses_implicit_upgrade_or_downgrade(self) -> None:
        installed_other = subprocess.CompletedProcess(["winget", "list"], 0, "Git Git.Git 2.49.0 winget")
        with mock.patch.object(install_global_tool.os, "name", "nt"), mock.patch.object(
            install_global_tool.shutil, "which", return_value="winget.exe"
        ), mock.patch.object(install_global_tool, "_run", return_value=installed_other):
            with self.assertRaisesRegex(install_global_tool.InstallGuardError, "different version"):
                install_global_tool.install_authorized_winget_tool(
                    "Git.Git", "2.50.0", "machine", "Git.Git", "2.50.0", "machine"
                )


if __name__ == "__main__":
    unittest.main()
