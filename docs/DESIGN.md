# Codex Personal Dev Kit Design

## 1. Product Goal

这是一个面向零基础用户的 Codex 开发助手，不是要求用户学习专业软件流程的教程。用户只说想得到什么，助手负责把一句话扩展成合理产品、可维护架构和可验证软件，并在多个长期项目中保持连续性。

用户不应负责：Git 命令、分支策略、Worktree、子代理选择、文件拆分、测试框架和工程文档维护。用户只在产品方向、成本、隐私、外部服务和不可逆风险上做决定。

## 2. Workspace Model

```text
Mother Folder
├── AGENTS.md
├── workspace.json
├── codex-dev-kit/
├── projects/
│   ├── project-a/  # own Git repo and Codex primary folder
│   └── project-b/  # own Git repo and Codex primary folder
└── archives/
```

- 母文件夹只负责创建、总览和归档，不建立总 Git 仓库。
- 每个项目独立 Git、独立 Codex Local Project、独立任务和文档。
- 新项目创建完成后在该项目文件夹开启新任务，使项目 `AGENTS.md` 和 `.codex/config.toml` 在新运行中正确加载。
- 不使用容易漂移的 `projects.json`；项目列表由 `projects/` 目录实时发现。
- Dev Kit 通过 Plugin 安装一次并全局复用。

## 3. Codex-Native Layers

| Layer | Responsibility |
| --- | --- |
| Global `AGENTS.md` | 简短的零基础交互、权限和 Plugin Bootstrap 约定 |
| Plugin | 单入口助手、六个内部 Skills、Hooks、模板和脚本 |
| Global agents/rules | 专业只读角色和命令政策 |
| Mother-folder files | 新建项目、项目隔离和归档约定 |
| Project `AGENTS.md` | 当前项目命令、验证、边界和文档路由 |
| Project `.codex/config.toml` | workspace-write、Goal、Hooks 和子代理默认设置 |
| Code/tests/Git/docs | 长期项目事实和恢复来源 |
| Current Codex task | 一个连贯成果的临时上下文和持久 Goal |

`AGENTS.md` 是软指令；Hooks、Rules、sandbox 和 approvals 提供独立防护。Plugin 或全局配置变化在新任务开始时加载。

## 4. Assistant Architecture

### User Front Door

`codex-development-assistant` 捕获普通软件请求。它负责判断当前位于母文件夹还是项目文件夹，并在内部调用专业 Skills。

### Internal Capabilities

1. `onboard-codex-project`: 建立项目事实、模板和 Git 基线。
2. `prepare-codex-goal`: 从一句话拓展需求并形成可验证 Goal。
3. `orchestrate-codex-team`: 自适应选择主代理、子代理、多任务和 Worktree。
4. `codex-safe-development`: 实现、测试、审查和本地检查点。
5. `manage-project-continuity`: 新任务恢复、短状态和交接。
6. `audit-codex-kit`: 只读巡检项目和助手本身。

### Adaptive Team

- 小任务：主代理直接完成。
- 中任务：主代理写入，1 个只读探索者或验证者辅助。
- 大任务：产品/架构/探索/审查可并行只读，主代理保持单一写入。
- 独立长期成果：多个 Codex 任务。
- 真正需要并行写入或后台计划任务：独立 Worktree；普通开发不为了流程创建额外分支。

子代理返回精炼证据，不通过永久报告文件交流，也不得把原始日志倾倒到主任务。

## 5. End-To-End Behavior

```text
一句话需求
  -> 推荐理解和少量关键问题
  -> 20 维需求检查与范围分级
  -> 更新功能地图和可验证 Goal
  -> 最小足够架构与纵向切片
  -> 单一写入者实现
  -> 测试 + 旧功能回归 + 独立审查
  -> 本地回退点
  -> 覆盖更新短状态
  -> 可试用结果或下一任务
```

普通工程阶段不中断用户。只有会明显改变产品、成本、权限、隐私或可逆性的事项才暂停。

## 6. Failure Prevention

### Unmaintainable Files

文件行数只是定位线索，不设置通用硬阈值。架构守护检查模块责任、依赖方向、变更频率、测试难度和小改动影响面。确需拆分时先建立行为基线，再逐个稳定责任迁移，禁止借小需求实施全面重写。

### Missing Existing Features

`docs/FEATURES.md` 用稳定 ID 保存当前用户能力、完整接线链路和验证入口；测试是可执行行为记忆；Git 保存恢复历史。修改前创建一个 Git 忽略的 `.codex/current-change.json`，声明允许改变、必须保护、邻接验证和有意删除。PreToolUse Hook 阻止无契约编辑或未验证提交，SessionStart 在新任务和压缩后恢复契约，Stop Hook 在验证缺失或验证后再次改动时要求 Codex 继续。契约只保留当前任务，不进入长期文档。

### Git Integration Errors

正常顺序开发沿当前本地开发线创建小型检查点，不让零基础用户管理大量分支。子代理默认只读，同一 checkout 一个写入者。Worktree 只用于真实隔离，优先由 Codex Handoff 处理，不依赖用户手工合并。

### Context Loss

一个任务只负责一个连贯成果。新任务恢复顺序为：AGENTS、PROJECT、FEATURES、STATUS、相关 ARCHITECTURE、Git 和必要测试。旧聊天和 Memories 是辅助召回，不是事实来源。

### Document Bloat

不创建 `.ai/history/`、每日会话日志、永久 checkpoint 报告或每个小功能一份规格。当前文档覆盖更新，历史交给 Git。

## 7. Durable Project Documents

| File | Current truth | Budget |
| --- | --- | --- |
| `AGENTS.md` | AI 工作规则、真实命令、验证和路由 | 目标小于 8 KiB |
| `README.md` | 用途、安装、启动和测试 | 保持当前 |
| `docs/PROJECT.md` | 用户、结果、范围和非目标 | 小于 200 行 |
| `docs/FEATURES.md` | 用户能力、关键规则和验证入口 | 主索引小于 250 行，按领域拆分 |
| `.codex/current-change.json` | 当前任务的功能保全范围和验证证据 | 单个临时忽略文件，任务间覆盖或清理 |
| `docs/ROADMAP.md` | 当前和接下来 2 到 3 个里程碑 | 小于 150 行 |
| `docs/ARCHITECTURE.md` | 当前模块、接口、依赖和数据流 | 主索引小于 300 行 |
| `docs/STATUS.md` | 当前里程碑、验证、问题和下一步 | 100 到 150 行 |
| `docs/adr/` | 重大且难逆转的决定 | 一项一个文件 |
| `docs/RUNBOOK.md` | 部署、备份、恢复和故障处理 | 仅按项目实际需要 |

禁止把聊天全文、模型推理、完整 diff、原始日志和每日流水账复制进长期文档。

## 8. Git And Recovery

- 新项目自动初始化独立 Git，并创建本地基线检查点。
- 每个通过验证的纵向切片可创建本地检查点。
- 默认不创建需要用户整合的额外分支。
- 不混入任务外的用户修改，不修改全局 Git 身份。
- 本地 Git 提供回滚但不是异地备份。远程备份需要用户明确配置和执行。
- 禁止自动 push、pull、merge、rebase、tag、release、历史重写、强制 clean 和丢弃未确认工作。

## 9. Permissions And Unattended Work

自动：项目内读写、已有测试和构建、只读子代理、本地 Git 初始化和检查点、精炼文档更新。

询问：生产依赖、付费服务、外部或隐私数据、重大架构替换、数据库结构迁移、全局 Codex 或系统工具变化。

禁止自动：发布、部署、生产迁移、包发布、基础设施变更、远程 Git 集成和不可恢复数据操作。

Goal 和计划任务不扩大权限。稳定的 Skill 定义方法，计划任务只定义时间；无人值守任务优先做只读审计、摘要和补丁准备，并使用 workspace-write 与隔离 Worktree。

## 10. What The Drafts Contributed

保留自 `AI-Engineering-Framework-v0.3.2`：文件化事实、短全局规则、独立项目 Git、增量开发、风险控制、测试、ADR 和角色分工。

改造或移除：庞大 Workspace Registry、framework locator、固定角色流水线、每阶段等待、`.ai/session-state/active-task/checkpoints/history/approvals`、所有功能永久规格、所有项目强制 release/monitoring/migration 文档，以及代理通过大量文件报告通信。

`Codex-Implementation-Workflow.md` 的“先核对运行时再实现”被保留；“每阶段必须停止”改成风险决策门，因为它不适合用户期待的持续自主开发。

## 11. Completion Criteria

- 用户只用普通语言即可创建、继续和改进项目。
- 新项目位于母文件夹的 `projects/` 下，并成为独立 Codex 工作文件夹和 Git 仓库。
- 修改已有功能前后都有稳定功能 ID、临时变更契约、测试证据和 Stop 门禁。
- 文档保持可快速定位，没有无限追加历史。
- Plugin、Skills、Hooks、Rules 和脚本验证通过。
- 新上下文子代理能在不看到设计答案时正确执行典型场景。
- 创建本地 Dev Kit Git 检查点，但不自动安装到全局、不 push、不发布。
