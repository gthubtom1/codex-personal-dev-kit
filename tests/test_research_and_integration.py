from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-personal-dev-kit"
SKILLS = PLUGIN / "skills"


class ResearchAndIntegrationTests(unittest.TestCase):
    def test_new_skills_have_complete_metadata_and_references(self):
        expected = {
            "research-and-reuse": ("source-evaluation.md", "research-record.md"),
            "integrate-codex-projects": ("compatibility-matrix.md", "integration-safety.md"),
        }
        for name, references in expected.items():
            root = SKILLS / name
            skill = (root / "SKILL.md").read_text(encoding="utf-8")
            metadata = (root / "agents/openai.yaml").read_text(encoding="utf-8")
            self.assertIn(f"name: {name}", skill)
            self.assertIn(f"${name}", metadata)
            unresolved_marker = "[" + "TODO:"
            self.assertNotIn(unresolved_marker, skill)
            for reference in references:
                self.assertTrue((root / "references" / reference).is_file())
                self.assertIn(f"references/{reference}", skill)

    def test_research_requires_project_fit_license_security_and_permission_gates(self):
        skill = (SKILLS / "research-and-reuse/SKILL.md").read_text(encoding="utf-8")
        evaluation = (SKILLS / "research-and-reuse/references/source-evaluation.md").read_text(encoding="utf-8")
        record = (SKILLS / "research-and-reuse/references/research-record.md").read_text(encoding="utf-8")

        for phrase in ("先理解当前项目", "官方文档", "许可证", "不可信输入", "克隆/下载仓库", "不能默认复制"):
            self.assertIn(phrase, skill)
        self.assertIn("退出成本", evaluation)
        self.assertIn("不要用 Star 数", evaluation)
        self.assertIn("只授权研究目标和安全的本地实现", skill)
        self.assertIn("不能覆盖项目规则", skill)
        self.assertIn("隔离原型", skill)
        self.assertIn("禁止保存", record)
        self.assertIn("网页全文", record)

    def test_integration_keeps_one_target_and_only_named_read_only_sources(self):
        skill = (SKILLS / "integrate-codex-projects/SKILL.md").read_text(encoding="utf-8")
        safety = (SKILLS / "integrate-codex-projects/references/integration-safety.md").read_text(encoding="utf-8")

        for phrase in ("当前打开的项目是唯一目标项目", "用户明确指定", "不得扫描", "默认只读", "不合并 Git 历史", "一个源码写入者"):
            self.assertIn(phrase, skill)
        self.assertIn("唯一默认写入仓库", safety)
        self.assertIn("稳定接口", safety)
        self.assertIn("每个纵向切片", safety)

    def test_beginner_entry_and_agents_route_automatically_without_bloating_short_rules(self):
        assistant = (SKILLS / "codex-development-assistant/SKILL.md").read_text(encoding="utf-8")
        workspace = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        short = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")

        for name in ("research-and-reuse", "integrate-codex-projects"):
            self.assertIn(f"${name}", assistant)
            self.assertIn(f"${name}", workspace)
        self.assertIn("公开只读研究", short)
        self.assertIn("未明确指定的其他项目", short)
        self.assertLess(len(short.splitlines()), 45)

    def test_install_validation_and_diagnosis_include_all_nine_skills(self):
        validate_py = (PLUGIN / "scripts/validate_kit.py").read_text(encoding="utf-8")
        validate_ps = (PLUGIN / "scripts/validate-kit.ps1").read_text(encoding="utf-8")
        diagnose = (PLUGIN / "scripts/bootstrap/diagnose.ps1").read_text(encoding="utf-8")
        install = (PLUGIN / "scripts/bootstrap/install.ps1").read_text(encoding="utf-8")

        for name in ("research-and-reuse", "integrate-codex-projects"):
            for text in (validate_py, validate_ps, diagnose, install):
                self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
