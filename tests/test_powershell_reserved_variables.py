"""PowerShell reserved automatic variables must never be assigned.

exe-product-lifecycle's layout validator flags ``$pid = ...`` because assigning
a reserved automatic variable (``$pid``/``$args``/``$input``/``$error``/
``$host``/``$pwd``/``$matches``/``$this``) silently shadows it and has
repeatedly broken scripts on plain Windows. codex-dev-kit only syntax-parses its
``.ps1`` files, which accepts that assignment as valid, so this scans every
tracked ``.ps1`` for the semantic hazard the parser cannot see.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

RESERVED_AUTOMATIC_VARIABLES = (
    "pid", "args", "input", "error", "host", "pwd", "matches", "this",
)

_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
_DOUBLE_STRING = re.compile(r'"(?:`.|[^"`])*"')
_SINGLE_STRING = re.compile(r"'[^']*'")
_ASSIGNMENT = re.compile(
    r"(?im)(?:^|[;{(])\s*\$(" + "|".join(RESERVED_AUTOMATIC_VARIABLES) + r")\b\s*(?:=|\+=|-=|\*=|/=|%=)(?!=)"
)


def _strip_noise(line: str) -> str:
    line = _DOUBLE_STRING.sub('""', line)
    line = _SINGLE_STRING.sub("''", line)
    hash_index = line.find("#")
    if hash_index != -1:
        line = line[:hash_index]
    return line


def reserved_variable_assignments(text: str) -> list[str]:
    """Return the reserved automatic variables assigned in PowerShell text.

    Comparisons (``-eq``), reads (``$id = $pid``), comments, and string contents
    are not assignments and must not be reported; only ``$reserved = ...`` (and
    its compound forms) counts.
    """
    text = _BLOCK_COMMENT.sub(" ", text)
    hits: list[str] = []
    for raw_line in text.splitlines():
        cleaned = _strip_noise(raw_line)
        for match in _ASSIGNMENT.finditer(cleaned):
            hits.append(match.group(1).lower())
    return hits


class PowerShellReservedVariableTests(unittest.TestCase):
    def test_assigning_pid_is_flagged(self) -> None:
        # Positive control (the exe WL1 shape): $pid = 1 must be caught.
        self.assertIn("pid", reserved_variable_assignments("$pid = 123\n"))

    def test_every_reserved_name_is_flagged_when_assigned(self) -> None:
        for name in RESERVED_AUTOMATIC_VARIABLES:
            self.assertIn(name, reserved_variable_assignments(f"${name} = 1\n"), name)

    def test_compound_assignment_is_flagged(self) -> None:
        self.assertIn("error", reserved_variable_assignments("$error += 'x'\n"))

    def test_renamed_variable_is_not_flagged(self) -> None:
        # Negative control (the exe WL2 shape): rename to a non-reserved name.
        self.assertEqual(reserved_variable_assignments("$processId = 123\n"), [])

    def test_reading_a_reserved_variable_is_not_flagged(self) -> None:
        self.assertEqual(reserved_variable_assignments("$id = $pid\n"), [])

    def test_comparison_is_not_flagged(self) -> None:
        self.assertEqual(reserved_variable_assignments("if ($pid -eq 1) { }\n"), [])

    def test_reserved_name_inside_comment_is_not_flagged(self) -> None:
        self.assertEqual(reserved_variable_assignments("# $pid = 1 is dangerous\n"), [])

    def test_reserved_name_inside_string_is_not_flagged(self) -> None:
        self.assertEqual(reserved_variable_assignments('Write-Output "$pid = 1"\n'), [])

    def test_no_repo_powershell_assigns_a_reserved_variable(self) -> None:
        # The guard itself: no tracked .ps1 in the repository assigns a reserved
        # automatic variable. A fixture .ps1 with `$pid = 1` turns this red.
        offenders: list[str] = []
        for path in REPO_ROOT.rglob("*.ps1"):
            if ".git" in path.parts:
                continue
            names = reserved_variable_assignments(path.read_text(encoding="utf-8", errors="replace"))
            if names:
                offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {sorted(set(names))}")
        self.assertEqual(
            offenders, [],
            "reserved automatic variable assignment(s) found: " + "; ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
