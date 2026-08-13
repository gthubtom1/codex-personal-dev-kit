"""The rules that decide when a claim is allowed to be stated as fact.

Every rule here exists because something reported success while the thing it
claimed was not true: a suite that stayed green after a guard was deleted, a
"fixed" defect backed only by a declaration no code read, and tools that
returned "done" without doing it.  These are prose rules, so these tests only
prove the rules are still present and worded as decided -- they cannot prove
anyone followed them.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-personal-dev-kit"
WORKSPACE_RULES = PLUGIN / "assets/workspace-template/AGENTS.md"
QUALITY_GATES = PLUGIN / "skills/codex-safe-development/references/quality-gates.md"


class RuleTextTestCase(unittest.TestCase):
    """Report the missing sentence, not the whole document it is missing from."""

    def assertStates(self, document: str, *phrases: str) -> None:
        text = self.documents[document]
        missing = [phrase for phrase in phrases if phrase not in text]
        if missing:
            self.fail(f"{document} no longer states: " + " | ".join(missing))


class EvidenceStandardTests(RuleTextTestCase):
    def setUp(self) -> None:
        self.documents = {
            "workspace-template/AGENTS.md": WORKSPACE_RULES.read_text(encoding="utf-8"),
            "quality-gates.md": QUALITY_GATES.read_text(encoding="utf-8"),
        }

    def test_completion_standard_grades_evidence_instead_of_accepting_all_green(self):
        self.assertStates(
            "workspace-template/AGENTS.md",
            "结论强度不得高于证据等级",
            "把它改坏后哪一条会红",
            "全绿只说明量对了自己出的那张卷子",
        )

    def test_a_declaration_is_not_an_implementation(self):
        """schema/config/CI/README describe intent; only running code enforces it."""
        self.assertStates(
            "workspace-template/AGENTS.md",
            "执行它的代码",
            "schema",
            "类型定义",
            "README",
            "引用得再逐字正确也不算证据",
        )

    def test_absence_claims_require_a_search_that_ignore_rules_cannot_hide_from(self):
        self.assertStates(
            "workspace-template/AGENTS.md",
            "rg --no-ignore",
            "中英文关键词",
            "唯一写入口反推调用点",
        )

    def test_single_environment_results_stay_scoped_to_that_environment(self):
        self.assertStates(
            "workspace-template/AGENTS.md",
            "一个环境",
            "收窄到那一格",
            "未验证",
        )

    def test_defect_fixes_require_both_the_red_and_the_green_run(self):
        self.assertStates("workspace-template/AGENTS.md", "先红后绿")
        self.assertStates(
            "quality-gates.md",
            "先红后绿",
            "只交绿的那一次不算",
            "红在该红的那几条上",
            "恒绿的假守卫",
        )

    def test_guard_writing_requires_fixture_self_check_and_both_controls(self):
        self.assertStates("quality-gates.md", "夹具自检", "正控", "负控", "一律拒绝")

    def test_a_tool_reporting_success_is_not_proof_it_happened(self):
        for document in self.documents:
            self.assertStates(document, "验状态", "回话是它说的，状态是它做的", "git add .")


if __name__ == "__main__":
    unittest.main()
