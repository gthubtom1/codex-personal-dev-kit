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

- 母文件夹只负责创建、总览和归档，不建立总 Git 仓库，也不作为已有项目的开发入口。
- 每个项目独立 Git、独立 Codex Local Project、独立任务和文档。
- 用户继续或修改已有项目时，先在 Codex 中打开该项目文件夹；母文件夹不替用户选择或进入项目。
- 新项目创建完成后在该项目文件夹开启新任务，使项目 `AGENTS.md` 和 `.codex/config.toml` 在新运行中正确加载。
- 不使用容易漂移的 `projects.json`；项目列表由 `projects/` 目录实时发现。
- Dev Kit 以 standalone Skills 和中央运行时安装一次并全局复用；源码目录只是分发源码，不是运行时 Plugin。

## 3. Codex-Native Layers

| Layer | Responsibility |
| --- | --- |
| Global `AGENTS.md` | 简短的零基础交互、权限、安全边界和母文件夹详细规则入口 |
| Mother-folder `AGENTS.md` | 完整工作流、目录、Skills、Git、文档、任务和原生 subagent 规则 |
| Standalone Skills | 一个普通语言入口和八个按需加载的专业能力，包括外部研究复用与多项目融合 |
| Central runtime | `~/.codex/codex-dev-kit/` 下的脚本、模板、索引、版本和来源信息 |
| Explicit safety scripts | 通过当前任务显式运行功能保全、危险命令和 Git 检查，不定义或替代智能体 |
| Mother-folder files | 新建项目、项目隔离和归档；不管理原生 subagent 配置 |
| Project `AGENTS.md` | 当前项目命令、验证、边界和文档路由 |
| Project `.codex/config.toml` | workspace-write 和 Goal；不写入任何子代理设置 |
| Code/tests/Git/docs | 长期项目事实和恢复来源 |
| Current Codex task | 一个连贯成果的临时上下文和持久 Goal |

`AGENTS.md` 是软指令；sandbox、approvals、显式安全脚本和 Git 检查点提供可审计的恢复边界。全局 AGENTS、Skills 或配置变化在新任务开始时加载。

### Verified Codex Runtime Facts

- Codex automatically loads one global instruction file from `~/.codex`, then discovers project instructions from the selected project root down to the working directory. When an individual project under `D:\开发\projects\` is the Git/project root, the parent `D:\开发\AGENTS.md` is not automatically discovered; the short global file must explicitly require reading it.
- Native subagent behavior belongs to Codex and the user's own configuration. Managed templates and scripts do not write, merge, migrate, diagnose, or override model, reasoning, concurrency, enablement, or interruption settings. The orchestration Skill calls the native tool without those overrides and reports the actual result.
- A started subagent confirms its task payload is readable before doing work. Missing native tools, rejected calls and unreadable payloads are reported without changing configuration or substituting visible tasks, custom Agents, Plugins or Hooks. The diagnostic still flags known plaintext sensitive keys without printing their values.
- 本 Dev Kit 不安装生命周期 Hook，避免任何工具匹配器改变 Codex 原生 subagent、任务、浏览器或文件编辑语义；需要保护时由 Skill 调用显式脚本。
- `AGENTS.md` should stay small and route to focused Skills or references. Project state is split across concise current documents instead of expanding one permanent transcript.

## 4. Assistant Architecture

### User Front Door

`codex-development-assistant` 捕获普通软件请求。位于母文件夹时只创建或管理项目；位于已打开的项目文件夹时才恢复上下文并开发该项目，然后在内部调用专业 Skills。

### Internal Capabilities

1. `onboard-codex-project`: 建立项目事实、模板和 Git 基线。
2. `prepare-codex-goal`: 从一句话拓展需求并形成可验证 Goal。
3. `orchestrate-codex-team`: 自适应选择主代理、Codex 原生 collaboration subagent 和必要 Worktree；不使用可见任务模拟子代理。
4. `codex-safe-development`: 实现、测试、审查和本地检查点。
5. `manage-project-continuity`: 新任务恢复、短状态和交接。
6. `audit-codex-kit`: 只读巡检项目和助手本身。

### Adaptive Team

- 小任务：主代理直接完成。
- 中任务：主代理写入，1 个只读探索者或验证者辅助。
- 大任务：产品/架构/探索/审查可并行只读，主代理保持单一写入。
- 独立长期成果：完成当前检查点后，建议用户开启新的 Codex 任务并使用精炼交接；只有用户明确要求时才创建或操作可见任务。
- 真正需要并行写入或后台计划任务：独立 Worktree；普通开发不为了流程创建额外分支。

子代理只通过 Codex 原生 collaboration 接口在当前任务内运行并返回精炼证据，不通过可见任务、聊天、跨任务消息、Handoff 或永久报告文件模拟，也不得把原始日志倾倒到主任务。

### Native Capability Non-Interference

The Dev Kit orchestrates Codex capabilities; it does not replace them. It does not intercept `Agent` or `spawn_agent`; it does not create a replacement agent protocol through MCP or Apps; and it does not disable native multi-agent configuration or reinterpret user-visible tasks as subagents. Worktrees remain isolated Git checkouts, the review pane remains Codex's native staged/unstaged/commit UI, and Appshots remain visual app-state inputs rather than source-control snapshots.

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

`docs/FEATURES.md` 与 `docs/features/**/*.md` 聚合后用全局唯一稳定 ID 保存当前用户能力、完整接线链路和验证入口；测试是可执行行为记忆；Git 保存恢复历史。修改前创建一个 Git 忽略的 `.codex/current-change.json`，声明允许改变、必须保护、邻接验证、有意删除和需要接管的已有脏文件。门禁只按明确文件路径暂存，亲自执行验证命令并绑定退出码、Git tree 和内容指纹；验证后只允许单独 commit，且提交 tree 与父提交必须匹配验证快照。SessionEnd 不清理尚未形成检查点的契约。

### Unsafe Initial Baselines

新建或接管项目建立第一个 Git 回退点前，模板先扩充常见依赖、生成物、本地数据库、包管理器令牌、SSH 密钥、服务账号和证书忽略规则。门禁再检查未忽略路径和文本内容中的私钥、云密钥、GitHub/OpenAI/Slack 令牌、服务账号以及高风险 secret/token/password 赋值。命中时停止，不执行 `git add -A`。这不能替代专用 secret scanner，但防止最常见的零基础自动提交泄密。

### Legacy Installation Migration

Standalone 安装器不会把新系统叠加在旧 Plugin 上。它独立查询 Codex Plugin 列表并匹配所有 `codex-personal-dev-kit@*`，因此旧 `source.json` 缺失或使用自定义 Marketplace 时仍能识别旧 Plugin；发现旧 metadata、`codex-kit-*.toml` 或 Dev Kit 全局 Hook 时默认停止并列出目标。显式 `-MigrateLegacy` 后先完整写入并核验新的 standalone 运行时，再备份和清理精确识别的旧文件，最后用 Codex CLI 移除旧 Plugin；迁移前的写入或全局 AGENTS 标记校验失败不会先拆掉旧系统。混合 `hooks.json` 只删除同时匹配已知 Dev Kit 根路径与 `feature_guard.py hook`/`pre_tool_guard.py` 调用的处理器；只有模糊文本引用时停止人工检查，绝不猜测删除。

分发 checkout 同时保存全局短版和完整中文母目录 `AGENTS.md` 模板；仓库模板是母目录系统规则的唯一可移植标准。空白电脑安装时，安装器在完成固定 Git 来源、模板、旧状态和全局标记预检后，创建缺失的母目录结构与详细 `AGENTS.md`，再把 `{{WORKSPACE_AGENTS_PATH}}`、`{{CODEX_HOME}}`、`{{WORKSPACE_NAME}}`、`{{WORKSPACE_ROOT}}` 和 Skill 源路径替换为新电脑的真实位置。预览不写入，重复安装幂等；已有但不同的母目录规则被明确标为自定义/漂移并保留。诊断把实际母目录规则与已安装固定模板的渲染结果做完整比较，既不静默分叉，也不泄露自定义内容。固定 Git tag、根目录 `VERSION`、`docs/VERSIONS.md` 和 `source.json` 共同标识可恢复的 standalone 来源。

### Central Runtime Pinning

项目模板可以从源码 checkout 生成；项目不安装生命周期 Hook。需要安全检查时，Skill 显式调用 `~/.codex/codex-dev-kit/` 的中央脚本，这样源码目录移动、继续开发或出现未提交修改时，不会悄悄改变既有项目的检查脚本。

### Git Integration Errors

正常顺序开发沿当前本地开发线创建小型检查点，不让零基础用户管理大量分支。验证完成后，安全开发 Skill 必须调用 guard-managed `checkpoint` 形成 Git 提交；没有检查点就不能声明完成。原生子代理默认只读，同一 checkout 一个写入者。Worktree 只用于真实隔离；Handoff 仅用于用户明确授权的 Worktree 交接，绝不用于模拟子代理。

### Context Loss

一个任务只负责一个连贯成果。启动、恢复、压缩或开启新任务时，Skill 读取有上限的当前事实包：当前变更契约、精简 STATUS、分支/脏状态和最近检查点；`Next Action` 有独立预算，不会被前面的大段验证记录截断。随后始终读取 AGENTS、PROJECT、FEATURES 主索引、相关领域表和 STATUS，只按任务读取相关 ARCHITECTURE/ADR 和必要测试。

### Document Bloat

不创建 `.ai/history/`、每日会话日志、永久 checkpoint 报告或每个小功能一份规格。复杂任务最多使用一个 Git 忽略的 `.codex/active-plan.md`，完成即删除。审计不仅识别命名明显的开发/聊天日志，也对 `docs/` 下所有超大文本文件执行通用字节检查。当前文档覆盖更新，历史交给 Git。

## 7. Durable Project Documents

| File | Current truth | Budget |
| --- | --- | --- |
| `AGENTS.md` | AI 工作规则、真实命令、验证和路由 | 全局短版和项目规则目标小于 8 KiB；母目录完整标准保持在 32 KiB 内，继续增长时应把低频细节路由到 Skills/references |
| `README.md` | 用途、安装、启动和测试 | 保持当前 |
| `docs/PROJECT.md` | 用户、结果、范围和非目标 | 小于 200 行 |
| `docs/FEATURES.md` | 用户能力、关键规则和验证入口 | 主索引小于 250 行，按领域拆分 |
| `.codex/current-change.json` | 当前任务的功能保全范围和验证证据 | 单个临时忽略文件，任务间覆盖或清理 |
| `.codex/active-plan.md` | 当前复杂任务尚未完成的步骤 | 单个临时忽略文件，完成即删除 |
| `docs/ROADMAP.md` | 当前和接下来 2 到 3 个里程碑 | 小于 150 行 |
| `docs/ARCHITECTURE.md` | 当前模块、接口、依赖和数据流 | 主索引小于 300 行 |
| `docs/STATUS.md` | 当前里程碑、验证、问题和下一步 | 100 到 150 行 |
| `docs/VERSIONS.md` | 正式里程碑、用户可识别能力差异和本地版本标签；不记录普通检查点或 commit hash | 小于 250 行 |
| `docs/adr/INDEX.md` | 当前 ADR 的状态、领域和替代关系 | 小型索引 |
| `docs/adr/` | 重大且难逆转的决定 | 一项一个文件 |
| `docs/RUNBOOK.md` | 部署、备份、恢复和故障处理 | 仅按项目实际需要 |

禁止把聊天全文、模型推理、完整 diff、原始日志和每日流水账复制进长期文档。

`docs/features/**/*.md` 领域文件超过 1000 行或 128 KiB、单个 ADR 超过 800 行或 64 KiB 时，项目审计会提示拆分或压缩；这些是可定位性提示，不是对业务代码的硬性文件行数规则。

## 8. Git And Recovery

- 新项目自动初始化独立 Git，并创建本地基线检查点。
- 旧项目缺少 Git 或首个提交时，经生成物、密钥和本地数据检查后自动建立基线。
- 每个通过验证的纵向切片必须在任务结束前创建本地检查点；安全开发 Skill 会把缺少检查点报告为未完成。
- 默认不创建需要用户整合的额外分支。
- 用户只需说“回到上一个版本”；助手在确认没有未保存工作后创建一个恢复到上一版本的新提交，原版本和当前版本都保留。
- 普通检查点不等于产品版本。用户接受的完整里程碑更新 `docs/VERSIONS.md`，在同一个最终检查点中保存代码、测试和文档，再由 guarded `version` 创建本地 `vX.Y.Z` 标签。
- 用户不记得编号时按版本索引中的能力描述定位候选；确认后用 guarded `restore-version` 创建新的恢复检查点，保留较新历史、标签和完整版本索引。
- 不混入任务外的用户修改，不修改全局 Git 身份。
- 本地 Git 提供回滚但不是异地备份。远程备份需要用户明确授权目标 remote、当前 branch 和正式 tags；授权后由 AI 通过 guarded publisher 完成，不要求用户运行 Git。
- Guarded publisher 要求干净且已验证的 Dev Kit 检查点、至少一个指向 HEAD 的正式标签、精确 remote URL、dry-run、atomic 精确 refspec 和远程回读验证。原始/force Git、远程 ref 删除或移动、分叉历史自动整合、远程 Release、历史重写、强制 clean 和丢弃未确认工作仍禁止。
- Guarded synchronization separates safe linear movement from conflict resolution. `sync` fetches one exact authorized remote/current branch and permits only fast-forward; `integrate` accepts one exact local source branch and permits only fast-forward. Local-ahead and already-integrated states are idempotent; divergence never creates an unverified merge commit or rebase.
- Guarded index repair unstages only exact paths recorded by the open change contract and preserves working content. Guarded Worktree cleanup requires a registered non-current path, no modified/untracked/ignored files, and a target commit already contained in current history; it never uses force or deletes the branch.
- Guarded Windows tool installation lives inside the safe-development Skill. It requires explicit package ID/version/scope confirmation, uses only winget's named official source, refuses implicit upgrade/downgrade, and verifies the exact installed result.

## 9. Permissions And Unattended Work

自动：项目内读写、已有测试和构建、当前任务内的原生只读子代理、本地 Git 初始化和检查点、精炼文档更新。

询问：生产依赖、付费服务、外部或隐私数据、重大架构替换、数据库结构迁移、全局 Codex 或系统工具变化，以及任何远程状态变化。明确授权后的精确 branch/tag 备份、快进同步和固定版本 winget 首次安装由 AI 自行执行。

禁止原始、破坏性或未授权操作：raw/force Git、分叉历史自动 merge/rebase、Release、部署、生产迁移、包发布、基础设施变更、历史重写、远程 ref 删除和不可恢复数据操作。已有 guarded path 不受此句阻止。

普通软件请求由全局 AGENTS 自动路由到入口 Skill。用户明确要求完成多步骤结果、做到可用、继续直到完成或无人值守时，入口 Skill 在范围明确后建立持久 Goal；用户不需要知道 Goal 这个词。Goal 和计划任务不扩大权限。

## 10. What The Drafts Contributed

保留自 `AI-Engineering-Framework-v0.3.2`：文件化事实、短全局规则、独立项目 Git、增量开发、风险控制、测试、ADR 和角色分工。

改造或移除：庞大 Workspace Registry、framework locator、固定角色流水线、每阶段等待、`.ai/session-state/active-task/checkpoints/history/approvals`、所有功能永久规格、所有项目强制 release/monitoring/migration 文档，以及代理通过大量文件报告通信。

`Codex-Implementation-Workflow.md` 的“先核对运行时再实现”被保留；“每阶段必须停止”改成风险决策门，因为它不适合用户期待的持续自主开发。

## 11. Completion Criteria

- 用户只用普通语言即可创建项目，并在打开对应项目文件夹后继续和改进该项目。
- 新项目位于母文件夹的 `projects/` 下，并成为独立 Codex 工作文件夹和 Git 仓库。
- 修改已有功能前后都有稳定功能 ID、临时变更契约、测试证据和显式完成检查。
- 文档保持可快速定位，没有无限追加历史。
- Standalone Skills、安装/诊断脚本、显式安全脚本和原生 subagent 边界验证通过；仓库不安装 Plugin、项目生命周期 Hook 或自定义 Rules。
- 新上下文的原生子代理能在不看到设计答案时正确执行典型场景，且不会被替换成用户可见任务。
- 创建本地 Dev Kit Git 检查点；不自动安装到全局。只有用户明确授权时才通过 guarded publisher 做精确远程备份，不创建 Release 或部署。
