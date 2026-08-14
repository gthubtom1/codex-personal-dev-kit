from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-personal-dev-kit"


class NativeOrchestrationTests(unittest.TestCase):
    def test_managed_configs_do_not_set_native_subagent_options(self):
        paths = (
            ROOT / ".codex/config.toml",
        )
        forbidden = re.compile(
            r"(?m)^\s*(\[agents\]|default_subagent_model\s*=|"
            r"default_subagent_reasoning_effort\s*=|max_concurrent_threads_per_session\s*=|"
            r"interrupt_message\s*=|multi_agent\s*=)"
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, forbidden, path)
            self.assertIn("goals = true", text)

    def test_standalone_mode_ships_no_config_or_hook_templates(self):
        plugin = PLUGIN
        for relative in (
            "assets/global-profile",
            "assets/workspace-template/.codex",
            "assets/project-template/.codex",
            "assets/project-template/.cursor",
            "assets/project-template/.vscode",
            "scripts/merge-codex-config.ps1",
        ):
            self.assertFalse((plugin / relative).exists(), relative)

    def test_orchestration_uses_only_native_official_defaults(self):
        skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        short = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")
        workspace = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")

        for text in (skill, routing, short, workspace):
            self.assertIn("spawn_agent", text)
            self.assertTrue("官方默认" in text or "官方原生默认" in text or "official" in text.lower())
            self.assertNotIn("gpt-5.6-luna", text.lower())
            self.assertNotIn("default_subagent_model", text)
            self.assertNotIn("task-tool-unsupported", text)
        self.assertIn("不传模型、推理强度或并发覆盖", skill)
        self.assertIn("确认", skill)
        self.assertIn("任务正文可读", workspace)

    def test_native_agents_are_not_replaced_by_visible_tasks_or_extensions(self):
        skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        for required in ("可见 Codex 任务", "Plugin", "Hook", "MCP", "自定义 Agent"):
            self.assertIn(required, skill)
        self.assertIn("不得使用", skill)

    def test_one_writer_and_task_receipt_confirmation_are_explicit(self):
        skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        workspace = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("同一 checkout 默认只有主代理写入", skill)
        self.assertIn("任务正文缺失、不可读或范围错误", skill)
        self.assertIn("一个 checkout 只有一个写入者", workspace)
        self.assertIn("任务正文可读", workspace)

    def test_project_template_explicitly_reads_only_the_parent_rules_file(self):
        project = (PLUGIN / "assets/project-template/AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Always read the explicitly referenced mother-folder `AGENTS.md`", project)
        self.assertIn("Apart from that rules file", project)

    def test_no_replacement_agent_artifacts_ship(self):
        self.assertFalse((PLUGIN / ".codex-plugin").exists())
        self.assertFalse((PLUGIN / "agents").exists())
        self.assertFalse((PLUGIN / "hooks").exists())


if __name__ == "__main__":
    unittest.main()
