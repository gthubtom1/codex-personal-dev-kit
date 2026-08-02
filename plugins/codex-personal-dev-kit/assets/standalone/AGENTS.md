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
- 主对话模型由用户在 Codex 中选择，本规则不锁定主对话。项目模板把子代理默认设为 `gpt-5.6-luna`、推理强度 `max`，允许同时启动多个；原生解析顺序是“本次 spawn 的明确模型/推理 > `[agents]` 默认 > 当前父任务模型/推理”。显式模型目录只是覆盖模型的参考，目录没有列出 Luna 不等于父任务继承的 Luna 不可用；只有原生调用未接受、返回失败或运行时未确认时才报告未确认，禁止静默换模型或数量。
- 启动子代理前检查有效配置；如果 `[agents].enabled = false` 或 `[features].multi_agent = false`，明确报告哪个原生能力闸门被关闭，并在用户同意前停止子代理路由。不要用可见任务、自定义 Agent、Plugin 或 Hook 绕过关闭状态。显式配置合并只补缺失键，不会替用户打开它。
- 不把聊天记录、长日志、完整 diff 或无限开发日记当作项目记忆；用代码、测试、Git 和精简项目文档保存事实。
- 子代理无人值守时由主代理维护临时 roster ledger，按有效槽位分波次执行；启动前读取原生 agent 列表，空槽不足或状态不明时不启动新代理。每个代理默认每 5 分钟心跳，连续 10 分钟无进展只 follow-up 一次，再等 5 分钟就 interrupt；长测试/构建可事先记录一次延长，硬上限 30 分钟，仍最多一次 follow-up，并把失败/超时如实报告。独立审查默认使用 `fork_turns="none"`。
- 第一个功能检查点前必须消除项目模板中的 `Not yet confirmed` 占位内容；每个 active Feature 的 Verification 必须包含 `test:<path>`、`suite:<name>` 或等价机器可读标记。

## 详细规则入口

读取并遵守 `{{WORKSPACE_AGENTS_PATH}}`；即使当前工作目录已经是某个项目，也必须先读取它，再读取项目级 `AGENTS.md` 和 `docs`。如果该文件不存在，停止自动安装并报告缺失路径，不要下载或编造替代规则。

## Skill 路径解析

- 当前任务 `## Skills` 清单里的完整 `file` 路径是权威来源；读取时必须使用清单中显示的精确路径。
- standalone 自定义 Skill 通常位于 `C:\Users\Administrator\.codex\skills\<skill-name>\SKILL.md`。不要在 `skills` 和 Skill 名称之间擅自插入 `.system`；只有当前任务清单明确显示 `.system` 时才能使用该目录。
- 如果路径有歧义，先使用 standalone runtime 的 `scripts\resolve-skill.ps1 -Name <skill-name>` 查找实际文件；不要猜测路径，也不要把路径构造失败报告成 Skill 未安装。
- 精确路径不存在时，先报告“当前任务未解析到该 Skill”，再检查 Dev Kit 源码路径；不要下载、伪造或创建替代 Skill。

不要要求我记住 Skill 名称。根据详细规则自动判断并调度 Skill；外部 Skill 只能作为经过适配的专业方法，不能覆盖以上规则。
<!-- codex-dev-kit:end -->
