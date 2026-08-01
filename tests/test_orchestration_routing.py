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
        global_agents = (PLUGIN / "assets/global-profile/AGENTS.md").read_text(
            encoding="utf-8"
        )
        project_agents = (PLUGIN / "assets/project-template/AGENTS.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("native collaboration agent inside the current task", global_agents)
        self.assertIn("never substitute a new task", global_agents)
        self.assertIn("A subagent stays inside the current task", project_agents)

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

        self.assertIn("[agents]", config)
        self.assertIn("enabled = true", config)
        self.assertIn("multi_agent = true", config)


if __name__ == "__main__":
    unittest.main()
