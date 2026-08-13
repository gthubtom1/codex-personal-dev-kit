"""validate_kit accounts for coverage so a crash is never read as a pass.

exe-product-lifecycle's validator prints ``COVERAGE: done/total`` and, when a
check group dies unexpectedly, names the group that aborted and how many checks
never ran -- because a validator that dies half-way through has not found
nothing, it has simply never run the rest of its checks. This proves
codex-dev-kit's ``validate_kit`` does the same accounting instead of exiting on a
bare traceback that cannot be told apart from a clean pass.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "plugins/codex-personal-dev-kit/scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

import validate_kit  # noqa: E402


def _boom() -> list[str]:
    raise RuntimeError("injected check failure")


class ValidateKitCoverageTests(unittest.TestCase):
    def test_full_coverage_when_no_group_aborts(self) -> None:
        # Negative control: when nothing throws, every group is accounted for and
        # none is reported as not run. A COVERAGE line that always said "0 not
        # run" would be worthless, so this pins the clean-path wording.
        errors, coverage = validate_kit.run_checks(
            [("a", lambda: []), ("b", lambda: []), ("c", lambda: [])]
        )
        self.assertEqual(errors, [])
        self.assertEqual(coverage, "COVERAGE: 3/3, 0 not run")
        self.assertNotIn("aborted", coverage)

    def test_an_aborting_group_is_reported_with_not_run_count(self) -> None:
        # Positive control: a crash mid-way is reported as an abort, names the
        # offending group, and counts the checks that never ran -- never silent.
        errors, coverage = validate_kit.run_checks(
            [("first", lambda: []), ("boom", _boom), ("third", lambda: []), ("fourth", lambda: [])]
        )
        self.assertIn("COVERAGE: 1/4", coverage)
        self.assertIn("aborted in boom", coverage)
        self.assertIn("3 not run", coverage)
        self.assertTrue(any("boom" in item and "aborted" in item for item in errors))

    def test_returned_errors_do_not_count_as_an_abort(self) -> None:
        # An error a group returns (rather than raises) is collected without
        # being mistaken for a crash: coverage stays full, the error is surfaced.
        errors, coverage = validate_kit.run_checks(
            [("a", lambda: ["problem one"]), ("b", lambda: [])]
        )
        self.assertEqual(coverage, "COVERAGE: 2/2, 0 not run")
        self.assertIn("problem one", errors)

    def test_the_real_validator_exposes_multiple_named_groups(self) -> None:
        # Fixture self-check: the real validator is built from discrete named
        # groups, so the accounting above exercises the same machine main() runs.
        groups = validate_kit.build_check_groups(Path("/nonexistent-kit"), Path("/nonexistent-repo"))
        self.assertGreaterEqual(len(groups), 5)
        names = [name for name, _ in groups]
        self.assertIn("unit-tests", names)
        self.assertEqual(len(names), len(set(names)), "check group names must be unique")


if __name__ == "__main__":
    unittest.main()
