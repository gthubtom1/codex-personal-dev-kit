from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-personal-dev-kit"


class OrchestrationRoutingTests(unittest.TestCase):
    def test_subagents_use_native_collaboration_not_visible_tasks(self):
        skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (
            PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md"
        ).read_text(encoding="utf-8")

        self.assertIn("`spawn_agent`", skill)
        self.assertIn("Codex 当前任务内部", skill)
        for visible_task_tool in (
            "create_thread",
            "fork_thread",
            "send_message_to_thread",
            "handoff_thread",
        ):
            self.assertIn(f"`{visible_task_tool}`", skill)
            self.assertIn(f"`{visible_task_tool}`", routing)
        self.assertIn("不能互相替代", routing)

    def test_installed_instructions_preserve_the_same_boundary(self):
        global_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(
            encoding="utf-8"
        )
        project_agents = (PLUGIN / "assets/project-template/AGENTS.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("subagents use `spawn_agent` inside the current task", global_agents)
        self.assertIn("must never be replaced, intercepted, or simulated", global_agents)
        self.assertIn("Use one source writer per checkout", project_agents)

    def test_forward_testing_uses_native_subagents(self):
        audit_skill = (PLUGIN / "skills/audit-codex-kit/SKILL.md").read_text(
            encoding="utf-8"
        )
        forward_testing = (
            PLUGIN / "skills/audit-codex-kit/references/forward-testing.md"
        ).read_text(encoding="utf-8")

        self.assertIn("collaboration `spawn_agent`", audit_skill)
        self.assertIn("collaboration `spawn_agent`", forward_testing)
        self.assertIn("不得创建、分叉或转发用户可见任务", forward_testing)

    def test_project_config_keeps_native_multi_agent_enabled(self):
        config = (PLUGIN / "assets/project-template/.codex/config.toml").read_text(
            encoding="utf-8"
        )
        workspace_config = (PLUGIN / "assets/workspace-template/.codex/config.toml").read_text(
            encoding="utf-8"
        )

        for text in (config, workspace_config):
            self.assertIn("[agents]", text)
            self.assertIn("enabled = true", text)
            self.assertIn("multi_agent = true", text)

    def test_plugin_does_not_intercept_or_reimplement_native_agent_tools(self):
        hooks = json.loads((PLUGIN / "assets/project-template/.codex/hooks.json").read_text(encoding="utf-8"))["hooks"]
        for entry in hooks.get("PreToolUse", []):
            matcher = entry.get("matcher", "")
            if not matcher:
                continue
            compiled = re.compile(matcher)
            self.assertIsNone(compiled.search("Agent"), matcher)
            self.assertIsNone(compiled.search("spawn_agent"), matcher)

        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("apps", manifest)
        self.assertFalse((PLUGIN / ".mcp.json").exists())
        self.assertFalse((PLUGIN / ".app.json").exists())
        self.assertFalse((PLUGIN / "hooks/hooks.json").exists())

    def test_native_capabilities_are_preserved_as_dependencies(self):
        design = (ROOT / "docs/DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("Native Capability Non-Interference", design)
        self.assertIn("does not intercept `Agent`", design)
        self.assertIn("does not create a replacement agent protocol", design)

    def test_required_subagent_model_is_declared_without_custom_agent_dependency(self):
        orchestration_skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        workspace_agents = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        workspace_config = (PLUGIN / "assets/workspace-template/.codex/config.toml").read_text(encoding="utf-8")
        project_config = (PLUGIN / "assets/project-template/.codex/config.toml").read_text(encoding="utf-8")
        short_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")

        for text in (
            orchestration_skill,
            routing,
            workspace_agents,
            workspace_config,
            project_config,
            short_agents,
        ):
            self.assertIn("gpt-5.6-luna", text)
            self.assertIn("max", text)
        self.assertIn("default_subagent_reasoning_effort = \"max\"", workspace_config)
        self.assertIn("default_subagent_reasoning_effort = \"max\"", project_config)
        self.assertIn("If unavailable", workspace_agents)
        self.assertIn("不得选择会把模型或推理强度固定成其他值的自定义角色", orchestration_skill)
        self.assertNotIn("`codex_kit_reviewer`", orchestration_skill)


if __name__ == "__main__":
    unittest.main()
