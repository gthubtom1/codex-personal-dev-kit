#!/usr/bin/env python3
"""Where a new parallel work copy belongs, derived from the opened project at run time."""

from __future__ import annotations

import re
from pathlib import Path


DIRECTORY_SUFFIX = "-worktrees"
LABEL_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class WorktreeLayoutError(Exception):
    """A new parallel work copy cannot be placed safely."""


def default_worktree_root(root: Path) -> Path:
    """Derive the work-copy directory beside the project so a new copy never lands inside the opened workspace."""
    project = Path(root).expanduser().resolve()
    parent = project.parent
    if parent == project:
        raise WorktreeLayoutError("A project directly at a filesystem root cannot host parallel work copies beside itself.")
    return parent / f".{project.name}{DIRECTORY_SUFFIX}"


def plan_worktree_path(root: Path, name: str) -> Path:
    """Return where one new parallel work copy belongs, without creating, moving, or touching any existing copy."""
    project = Path(root).expanduser().resolve()
    label = LABEL_PATTERN.sub("-", name.strip()).strip("-.")
    if not label:
        raise WorktreeLayoutError("A parallel work copy needs a name containing letters, digits, '.', '_', or '-'.")
    target = default_worktree_root(project) / label
    if target == project or target.is_relative_to(project):
        raise WorktreeLayoutError(f"A new parallel work copy must stay outside the opened project: {target}")
    if target.exists() and not (target.is_dir() and not any(target.iterdir())):
        raise WorktreeLayoutError(f"Another parallel work copy already occupies this path; choose a different name: {target}")
    return target
