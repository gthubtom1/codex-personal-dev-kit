from pathlib import Path
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

    def test_skill_paths_use_exact_locator_without_system_prefix(self):
        standalone_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(
            encoding="utf-8"
        )
        repo_agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for text in (standalone_agents, repo_agents):
            self.assertTrue(
                "never prepend `.system`" in text
                or "never invent a `.system` prefix" in text
                or ("`.system`" in text and "Skill" in text)
            )
            self.assertTrue("exact" in text.lower() or "精确" in text)
            self.assertIn("resolve-skill.ps1", text)

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

    def test_native_agent_tools_have_no_replacement_interceptor(self):
        self.assertFalse((PLUGIN / "assets/project-template/.codex/hooks.json").exists())
        self.assertFalse((PLUGIN / ".codex-plugin/plugin.json").exists())
        self.assertFalse((ROOT / ".agents/plugins/marketplace.json").exists())
        self.assertFalse((PLUGIN / ".mcp.json").exists())
        self.assertFalse((PLUGIN / ".app.json").exists())
        self.assertFalse((PLUGIN / "hooks/hooks.json").exists())

    def test_native_capabilities_are_preserved_as_dependencies(self):
        design = (ROOT / "docs/DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("Native Capability Non-Interference", design)
        self.assertIn("does not intercept `Agent`", design)
        self.assertIn("does not create a replacement agent protocol", design)

    def test_disabled_native_agent_gates_stop_subagent_routing(self):
        orchestration_skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        workspace_agents = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        standalone_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")

        for text in (orchestration_skill, routing, workspace_agents, standalone_agents):
            self.assertIn("[agents].enabled = false", text)
            self.assertIn("[features].multi_agent = false", text)
            self.assertTrue("visible" in text.lower() or "可见" in text)
            self.assertIn("hook", text.lower())

    def test_feature_guard_imports_sibling_script_without_removed_hook_path(self):
        source = (PLUGIN / "scripts/feature_guard.py").read_text(encoding="utf-8")
        self.assertIn("scripts_root = Path(__file__).resolve().parent", source)
        self.assertNotIn('parents[1] / "hooks"', source)

    def test_task_local_max_effort_subagent_policy_is_declared_without_custom_agent_dependency(self):
        orchestration_skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        workspace_agents = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        workspace_config = (PLUGIN / "assets/workspace-template/.codex/config.toml").read_text(encoding="utf-8")
        project_config = (PLUGIN / "assets/project-template/.codex/config.toml").read_text(encoding="utf-8")
        repo_config = (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        short_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")

        for text in (orchestration_skill, routing, workspace_agents, short_agents):
            self.assertIn("spawn_agent", text)
            self.assertIn("max", text)
        self.assertIn("default_subagent_reasoning_effort = \"max\"", workspace_config)
        self.assertIn("default_subagent_reasoning_effort = \"max\"", project_config)
        self.assertIn("The main conversation model is user-selected", workspace_agents)
        self.assertIn("do not set `default_subagent_model`", workspace_agents)
        self.assertIn("Every system-requested subagent reasoning effort: `max`", workspace_agents)
        self.assertIn("受管模板不固定 `default_subagent_model`", orchestration_skill)
        self.assertIn("继承当前父任务模型", orchestration_skill)
        self.assertIn("gpt-5.6-sol", orchestration_skill)
        self.assertIn('fork_turns="none"', orchestration_skill)
        self.assertIn("正整数 fork 深度", routing)
        self.assertIn("用户明确指定模型数量", routing)
        self.assertIn("run it in waves", workspace_agents)
        self.assertIn("temporary in-memory ledger", workspace_agents)
        self.assertIn("every 5 minutes", workspace_agents)
        self.assertIn("10 minutes", workspace_agents)
        self.assertIn("`list_agents`", workspace_agents)
        self.assertIn("Explicit user/project configuration", workspace_agents)
        self.assertTrue("user's roster" in workspace_agents or "user's explicit roster" in workspace_agents)
        self.assertIn("30-minute cap", workspace_agents)
        self.assertIn("分波次执行", (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8"))
        for config in (workspace_config, project_config, repo_config):
            self.assertNotRegex(config, r"(?m)^model\s*=")
            self.assertNotRegex(config, r"(?m)^default_subagent_model\s*=")
            self.assertIn('default_subagent_reasoning_effort = "max"', config)
            self.assertRegex(config, r"(?m)^max_concurrent_threads_per_session\s*=\s*[2-9]\d*\s*$")
        self.assertNotIn("`codex_kit_reviewer`", orchestration_skill)

    def test_explicit_models_follow_current_task_capability_surface(self):
        orchestration_skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        workspace_agents = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")

        for text in (orchestration_skill, routing, workspace_agents):
            self.assertIn("inherited-current-model", text)
            self.assertIn("runtime-unconfirmed", text)
            self.assertIn("task-tool-unsupported", text)
            self.assertTrue("effective model" in text.lower() or "有效模型" in text)
        self.assertIn("权威能力面", orchestration_skill)
        self.assertIn("authoritative", workspace_agents)
        self.assertIn("must not be called explicitly", workspace_agents)
        self.assertIn("不静默换成其他模型", orchestration_skill)
        self.assertIn("成功启动后记为 `config-default`", orchestration_skill)
        self.assertIn("否则成功后记为 `inherited-current-model`", orchestration_skill)
        self.assertIn("record `config-default`", workspace_agents)
        self.assertIn("timeout=", (PLUGIN / "scripts/validate_kit.py").read_text(encoding="utf-8"))
        self.assertIn("timed out", (PLUGIN / "scripts/validate_kit.py").read_text(encoding="utf-8"))

    def test_missing_agent_list_uses_conservative_degraded_waves(self):
        orchestration_skill = (PLUGIN / "skills/orchestrate-codex-team/SKILL.md").read_text(encoding="utf-8")
        routing = (PLUGIN / "skills/orchestrate-codex-team/references/agent-routing.md").read_text(encoding="utf-8")
        workspace_agents = (PLUGIN / "assets/workspace-template/AGENTS.md").read_text(encoding="utf-8")
        standalone_agents = (PLUGIN / "assets/standalone/AGENTS.md").read_text(encoding="utf-8")

        for text in (orchestration_skill, routing, workspace_agents, standalone_agents):
            self.assertIn("list_agents", text)
            self.assertTrue("最多 2 个" in text or "at most 2" in text)
            self.assertTrue("可选" in text or "optional" in text)
        self.assertIn("仍可使用 `spawn_agent`", orchestration_skill)
        self.assertIn("缺少 `list_agents` 不能被解释为子代理整体不可用", routing)


if __name__ == "__main__":
    unittest.main()
