#!/usr/bin/env python3
"""Install one explicitly authorized exact Windows tool through winget."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence


SAFE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")


class InstallGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallResult:
    package_id: str
    version: str
    scope: str
    state: str


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        errors="replace",
    )


def _contains_exact_install(output: str, package_id: str, version: str) -> bool:
    normalized = " ".join(output.lower().split())
    return package_id.lower() in normalized and version.lower() in normalized


def install_authorized_winget_tool(
    package_id: str,
    version: str,
    scope: str,
    confirmed_package_id: str,
    confirmed_version: str,
    confirmed_scope: str,
) -> InstallResult:
    package_id = package_id.strip()
    version = version.strip()
    scope = scope.strip().lower()
    if not SAFE_VALUE.fullmatch(package_id):
        raise InstallGuardError("Use one exact winget package ID without spaces or wildcard characters.")
    if not SAFE_VALUE.fullmatch(version):
        raise InstallGuardError("Use one exact published package version.")
    if scope not in {"user", "machine"}:
        raise InstallGuardError("Scope must be exactly user or machine.")
    if confirmed_package_id.strip() != package_id or confirmed_version.strip() != version or confirmed_scope.strip().lower() != scope:
        raise InstallGuardError("The confirmed package ID, version, and scope must exactly match the requested installation.")
    if os.name != "nt":
        raise InstallGuardError("The guarded global-tool installer currently supports Windows only.")
    winget = shutil.which("winget")
    if not winget:
        raise InstallGuardError("winget is not available. Do not download or substitute another installer automatically.")

    list_command = [
        winget,
        "list",
        "--id",
        package_id,
        "--exact",
        "--scope",
        scope,
        "--source",
        "winget",
        "--accept-source-agreements",
        "--disable-interactivity",
    ]
    before = _run(list_command)
    if before.returncode == 0 and _contains_exact_install(before.stdout or "", package_id, version):
        return InstallResult(package_id, version, scope, "already-installed")
    if before.returncode == 0 and package_id.lower() in (before.stdout or "").lower():
        raise InstallGuardError(
            "A different version of this tool is already installed. Guarded installation will not upgrade or downgrade it implicitly."
        )

    shown = _run(
        [
            winget,
            "show",
            "--id",
            package_id,
            "--exact",
            "--version",
            version,
            "--source",
            "winget",
            "--accept-source-agreements",
            "--disable-interactivity",
        ]
    )
    if shown.returncode != 0 or not _contains_exact_install(shown.stdout or "", package_id, version):
        raise InstallGuardError("The exact package and version could not be verified in the winget source.")

    installed = _run(
        [
            winget,
            "install",
            "--id",
            package_id,
            "--exact",
            "--version",
            version,
            "--scope",
            scope,
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ]
    )
    if installed.returncode != 0:
        raise InstallGuardError((installed.stdout or "").strip() or "The guarded winget installation failed.")
    after = _run(list_command)
    if after.returncode != 0 or not _contains_exact_install(after.stdout or "", package_id, version):
        raise InstallGuardError("The installer finished but the exact package version could not be verified.")
    return InstallResult(package_id, version, scope, "installed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--scope", choices=("user", "machine"), required=True)
    parser.add_argument("--confirm-package-id", required=True)
    parser.add_argument("--confirm-version", required=True)
    parser.add_argument("--confirm-scope", choices=("user", "machine"), required=True)
    args = parser.parse_args()
    try:
        result = install_authorized_winget_tool(
            args.package_id,
            args.version,
            args.scope,
            args.confirm_package_id,
            args.confirm_version,
            args.confirm_scope,
        )
    except InstallGuardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Guarded winget tool {result.state}: {result.package_id} {result.version} ({result.scope})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
