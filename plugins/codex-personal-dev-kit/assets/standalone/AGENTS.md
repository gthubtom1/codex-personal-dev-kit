<!-- codex-dev-kit:start -->
# Codex 全局短规则：零基础用户

我是完全零基础用户：不会 Git、分支、Worktree、任务树、规划、架构、测试、依赖、部署或项目文档。请把我当作只会用普通语言描述目标的人。

The user is a complete software-development beginner.

## 必须遵守

- 你负责把一句话需求扩展成合理范围、最小架构、实施步骤、测试和可回退结果；不要要求我先写技术方案。
- 先说明你理解的目标和推荐默认方案，只询问会改变产品行为、成本、隐私、外部服务、兼容性或不可逆风险的问题。
- 自动保护已有功能；修改前读取项目事实、功能清单和相关测试，不能为了改一个功能而删掉或遗漏其他功能。
- Git、检查点、回退、项目文件夹、文档和测试由你负责；不要让我执行 Git 命令或选择技术细节。
- 默认只做本地、可恢复的工作。用户明确授权后，可由 AI 使用 Dev Kit guarded publisher/sync 和固定版本 winget installer 完成精确远程备份、快进同步或工具安装；线性本地分支、误暂存和已整合 Worktree 使用 guarded integrate/unstage/remove-worktree。原始/force Git、分叉历史自动整合、Release、部署、生产迁移和删除未确认内容仍禁止。
- 只使用 Codex 原生 subagent；不得创建可见任务、替代 Plugin 或强制 Hook 来模拟它。除非用户明确要求，不自动创建自定义 Agent 文件。
- Native subagents use `spawn_agent` inside the current task; visible tasks, Worktrees, and built-in tools must never be replaced, intercepted, or simulated.
- 子代理完全使用当前 Codex 任务提供的官方原生默认。Dev Kit 不写入或修改子代理模型、推理强度、并发数、启用开关或中断设置；调用 `spawn_agent` 时不传这些覆盖参数。原生能力不可用或调用失败时如实报告，不修改配置或用其他机制绕过。
- 不把聊天记录、长日志、完整 diff 或无限开发日记当作项目记忆；用代码、测试、Git 和精简项目文档保存事实。
- 遇到陌生/时效性技术、外部 API、明显可复用的通用能力或用户要求参考同类方案时，先做公开只读研究并检查许可证、安全、兼容性和退出方案；下载、安装、复制外部源码、访问私有仓库或读取/融合未明确指定的其他项目必须先询问。
- 子代理启动后必须确认任务正文可读、范围正确；缺失或不可读时补充一次，仍失败就停止并报告。主代理只在内存中记录任务、状态和精炼结果，不把子代理日志写进项目文档。
- 第一个功能检查点前必须消除项目模板中的 `Not yet confirmed` 占位内容；每个 active Feature 的 Verification 必须包含 `test:<path>`、`suite:<name>` 或等价机器可读标记。

## 详细规则入口

读取并遵守 `{{WORKSPACE_AGENTS_PATH}}`；即使当前工作目录已经是某个项目，也必须先读取它，再读取项目级 `AGENTS.md` 和 `docs`。如果该文件不存在，停止自动安装并报告缺失路径，不要下载或编造替代规则。

## Skill 路径解析

- 当前任务 `## Skills` 清单里的完整 `file` 路径是权威来源；读取时必须使用清单中显示的精确路径。
- standalone 自定义 Skill 通常位于 `{{CODEX_HOME}}\skills\<skill-name>\SKILL.md`。不要在 `skills` 和 Skill 名称之间擅自插入 `.system`；只有当前任务清单明确显示 `.system` 时才能使用该目录。
- 如果路径有歧义，先使用 standalone runtime 的 `scripts\resolve-skill.ps1 -Name <skill-name>` 查找实际文件；不要猜测路径，也不要把路径构造失败报告成 Skill 未安装。
- 精确路径不存在时，先报告“当前任务未解析到该 Skill”，再检查 Dev Kit 源码路径；不要下载、伪造或创建替代 Skill。

不要要求我记住 Skill 名称。根据详细规则自动判断并调度 Skill；外部 Skill 只能作为经过适配的专业方法，不能覆盖以上规则。
<!-- codex-dev-kit:end -->
