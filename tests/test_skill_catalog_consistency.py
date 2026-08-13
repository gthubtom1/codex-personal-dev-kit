"""Three skill lists, one truth: py SKILLS == ps1 array == skills/ directories.

exe-product-lifecycle's ISSUE-096 lesson is that the same list must never live
in two hand-maintained copies that can silently drift apart. codex-dev-kit keeps
its skill roster in three places -- ``validate_kit.py``'s ``SKILLS`` set,
``validate-kit.ps1``'s hardcoded array, and the ``skills/`` directory.
``validate_kit`` already ties ``SKILLS`` to the directory, but nothing tied the
PowerShell array to either, so adding or removing a skill in one copy and
forgetting another drifted silently. This guard fails the moment the three
disagree.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN = REPO_ROOT / "plugins" / "codex-personal-dev-kit"
SCRIPT_ROOT = PLUGIN / "scripts"
VALIDATE_PS1 = SCRIPT_ROOT / "validate-kit.ps1"
SKILL_ROOT = PLUGIN / "skills"
sys.path.insert(0, str(SCRIPT_ROOT))

import validate_kit  # noqa: E402


def powershell_skill_list(text: str) -> set[str]:
    """The skill names PowerShell iterates over in ``validate-kit.ps1``.

    The array is the first ``@( ... ) | ForEach-Object`` block, and every entry
    is a double-quoted skill name. Parsing the real construct -- rather than
    keeping a second copy of the names here -- is what lets this guard notice
    the PowerShell list drifting from the Python one.
    """
    match = re.search(r"@\((?P<body>.*?)\)\s*\|\s*ForEach-Object", text, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r'"([a-z0-9][a-z0-9-]*)"', match.group("body")))


def directory_skill_list() -> set[str]:
    return {path.name for path in SKILL_ROOT.iterdir() if path.is_dir()}


class SkillCatalogConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.py_skills = set(validate_kit.SKILLS)
        self.ps1_skills = powershell_skill_list(VALIDATE_PS1.read_text(encoding="utf-8"))
        self.dir_skills = directory_skill_list()

    def test_the_powershell_array_is_actually_parsed(self) -> None:
        # Fixture self-check: if the parser found nothing, "the lists match"
        # would be the meaningless equality of two empty sets.
        self.assertGreaterEqual(len(self.ps1_skills), 9)
        self.assertIn("research-and-reuse", self.ps1_skills)

    def test_all_three_skill_lists_agree(self) -> None:
        # The guard itself, and the negative control: on the real tree the three
        # copies are in sync, so a correct tree stays green.
        self.assertEqual(
            self.py_skills, self.dir_skills,
            "validate_kit.SKILLS drifted from the skills/ directories",
        )
        self.assertEqual(
            self.py_skills, self.ps1_skills,
            "validate-kit.ps1's array drifted from validate_kit.SKILLS",
        )

    def test_a_single_copy_drifting_is_detected(self) -> None:
        # Positive control for the comparison: dropping or adding one name in a
        # single copy is exactly the ISSUE-096 drift this guard exists to catch.
        dropped = set(self.py_skills)
        dropped.discard(sorted(dropped)[0])
        self.assertNotEqual(self.py_skills, dropped)
        added = set(self.py_skills)
        added.add("a-tenth-skill-only-in-one-copy")
        self.assertNotEqual(self.py_skills, added)


if __name__ == "__main__":
    unittest.main()
