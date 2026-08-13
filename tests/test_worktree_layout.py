from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import worktree_layout  # noqa: E402


class WorktreeLayoutTests(unittest.TestCase):
    def test_new_work_copies_are_planned_beside_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = (Path(directory) / "example-project").resolve()
            project.mkdir()

            planned = worktree_layout.plan_worktree_path(project, "wt/c4 audit")

            self.assertFalse(planned.is_relative_to(project))
            self.assertEqual(planned.parent, worktree_layout.default_worktree_root(project))
            self.assertEqual(planned.parent.parent, project.parent)
            self.assertEqual(planned.parent.name, ".example-project-worktrees")
            self.assertEqual(planned.name, "wt-c4-audit")
            self.assertFalse(planned.exists())

    def test_unusable_names_and_occupied_targets_are_refused_without_touching_anything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = (Path(directory) / "example-project").resolve()
            project.mkdir()

            with self.assertRaisesRegex(worktree_layout.WorktreeLayoutError, "needs a name"):
                worktree_layout.plan_worktree_path(project, " -- ")

            occupied = worktree_layout.default_worktree_root(project) / "taken"
            occupied.mkdir(parents=True)
            (occupied / "in-use.txt").write_text("someone is working here\n", encoding="utf-8")

            with self.assertRaisesRegex(worktree_layout.WorktreeLayoutError, "already occupies"):
                worktree_layout.plan_worktree_path(project, "taken")
            self.assertEqual((occupied / "in-use.txt").read_text(encoding="utf-8"), "someone is working here\n")

            reusable = worktree_layout.default_worktree_root(project) / "empty"
            reusable.mkdir(parents=True)
            self.assertEqual(worktree_layout.plan_worktree_path(project, "empty"), reusable)


if __name__ == "__main__":
    unittest.main()
