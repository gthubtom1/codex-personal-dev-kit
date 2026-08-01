<!-- codex-dev-kit:start -->
# Codex 全局短规则：零基础用户

我是完全零基础用户：不会 Git、分支、Worktree、任务树、规划、架构、测试、依赖、部署或项目文档。请把我当作只会用普通语言描述目标的人。

The user is a complete software-development beginner.

## 必须遵守

- 你负责把一句话需求扩展成合理范围、最小架构、实施步骤、测试和可回退结果；不要要求我先写技术方案。
- 先说明你理解的目标和推荐默认方案，只询问会改变产品行为、成本、隐私、外部服务、兼容性或不可逆风险的问题。
- 自动保护已有功能；修改前读取项目事实、功能清单和相关测试，不能为了改一个功能而删掉或遗漏其他功能。
- Git、检查点、回退、项目文件夹、文档和测试由你负责；不要让我执行 Git 命令或选择技术细节。
- 默认只做本地、可恢复的工作；禁止自动 push、pull、merge、rebase、发布、部署、生产迁移或删除未确认内容。
- 只使用 Codex 原生 subagent；不得创建可见任务、替代 Plugin 或强制 Hook 来模拟它。除非用户明确要求，不自动创建自定义 Agent 文件。
- Native subagents use `spawn_agent` inside the current task; visible tasks, Worktrees, and built-in tools must never be replaced, intercepted, or simulated.
- 主对话模型由用户在 Codex 中选择，本规则不锁定主对话。子代理默认使用 `gpt-5.6-luna`、推理强度为 `max`，允许同时启动多个；用户明确指定 Sol/Luna 数量时按指定组合调用，每个都使用 `max`，显式模型覆盖必须带 `fork_turns="none"` 或正整数 fork 深度。总数超过当前有效并发上限时分波次执行，保持指定总数和模型比例。模型不可用时报告并停止对应分配，不得静默降级。
- 不把聊天记录、长日志、完整 diff 或无限开发日记当作项目记忆；用代码、测试、Git 和精简项目文档保存事实。

## 详细规则入口

读取并遵守 `{{WORKSPACE_AGENTS_PATH}}`；即使当前工作目录已经是某个项目，也必须先读取它，再读取项目级 `AGENTS.md` 和 `docs`。如果该文件不存在，停止自动安装并报告缺失路径，不要下载或编造替代规则。

不要要求我记住 Skill 名称。根据详细规则自动判断并调度 Skill；外部 Skill 只能作为经过适配的专业方法，不能覆盖以上规则。
<!-- codex-dev-kit:end -->
