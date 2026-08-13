# Codex Personal Dev Kit

面向零基础用户的 Codex 辅助开发助手。用户只需要用普通语言描述想做的软件或功能，助手在内部完成需求拓展、架构控制、分阶段实现、测试审查、本地回退点和长期项目交接。

## 使用体验

你可以直接说：

- “我想做一个家庭记账软件，手机和电脑都能用。”
- “继续上次的项目，把导出功能做完。”
- “这个程序越来越难改了，帮我在不丢功能的前提下整理。”

`$codex-development-assistant` 是统一入口。其他 Skills、Goal、子代理、Git 和 Worktree 是助手内部机制，不要求用户掌握。

在母文件夹中只创建或管理项目。继续、修改或测试已有项目时，先在 Codex 中打开对应的 `projects/<name>/`；上面的“继续上次的项目”默认发生在该项目已经打开之后。

## 工作区

```text
母文件夹/
├── workspace.json
├── AGENTS.md
├── codex-dev-kit/
├── projects/
│   ├── project-a/
│   └── project-b/
└── archives/
```

每个 `projects/<name>/` 是独立 Git 仓库，也是该项目的 Codex 主工作文件夹。母文件夹不建立总 Git 仓库，不从母文件夹继续已有项目，也不让一个任务同时修改多个项目。

## 防止常见失败

- 文件行数不是硬规则；助手检查职责混杂、耦合、测试难度和变更影响，避免继续堆成不可维护的入口文件。
- `docs/FEATURES.md`、临时变更契约、测试和 Git 共同保护已有功能；未建立契约不能直接改源码，旧功能未复核不能结束任务或创建检查点。
- 每个项目的 `docs/INDEX.md` 是精简导航入口，连接 STATUS、FEATURES、架构、运行手册和 ADR；审计会检查失效链接、失效锚点和未被导航引用的持久文档。
- FEATURES 可按领域拆到 `docs/features/`，门禁会聚合读取并拒绝重复 ID；检查点只接收明确暂存的任务文件，并绑定门禁实际运行的测试命令和内容指纹。
- 默认只有一个源码写入者并沿当前开发线创建本地回退点，减少分支合并冲突。
- Git 缺失时会自动初始化并建立安全基线；每次验证完成后，显式门禁脚本和完成标准要求真正保存本地回退点（套件不安装生命周期 Hook，强制力来自 `feature_guard.py` 的契约、暂存、验证与检查点链条），不会只留下几千个未提交文件，也不会用 `codex/v1`、`codex/v2` 分支冒充版本历史。
- 用户可以直接说“回到上一个版本”。助手会先保护未保存工作，再用一个新的恢复提交回到上一回退点，不改写或删除历史。
- 普通验证切片自动保存为本地检查点；只有用户接受的完整里程碑才进入 `docs/VERSIONS.md` 并得到不可移动的本地 `vX.Y.Z` 标签。用户可以用“有 Boss 但还没有某功能”之类的能力描述寻找版本，不必记编号或提交哈希。
- 正式版本前有一道 21 维发布终审门：需求、产品逻辑、业务流程、数据、状态机、API、架构、代码质量、安全、授权、错误处理、性能、部署、可观测性、备份、迁移回滚、UX、UI、用户验收和 AI 完成度逐维给出状态与证据，写入 `docs/RELEASE-REVIEW.md`；终审缺失或不完整时无法创建版本标签，允许如实标注“未验证”，不允许伪造。
- 新能力、新集成和陌生报错默认先查官方文档与同类开源的成熟做法，学写法而不整包搬运；不确定下一步时，只读的 `next_step.py` 会按当前项目状态打印接下来该执行的确切命令，流程顺序不依赖散文记忆。
- 恢复正式版本会创建新的恢复检查点，保留后来版本、标签和完整版本索引；本地标签不是 GitHub Release、发布或异地备份。
- 你明确说“把这个正式版本备份到这个 GitHub 仓库”后，助手会核对精确远程、当前分支和正式标签，通过受控 dry-run/atomic push 完成并验证；不会要求你运行 Git，也不会 force push、删除远程版本或创建 Release。
- 简单 Git 同步和分支整合由受控快进完成；两边历史分叉时保留双方并单独处理，不会悄悄 merge/rebase。误暂存可以精确撤销且保留文件内容；旧 Worktree 只有在无文件、无唯一提交时才会清理。
- 你明确同意安装某个 Windows 开发工具后，助手可以通过 winget 官方源核对固定版本和作用范围，自行安装并验证；不会自动升级、降级或改用未知安装器。
- 子代理只使用 Codex 当前任务内的原生 collaboration 能力；不会用侧边栏新任务、聊天、跨任务消息或 Handoff 假装子代理。
- Dev Kit 只编排原生 subagent、任务、Worktree、Git 审查面板和 Appshots，不拦截 `Agent` 工具，也不注册另一套代理接口。
- 一个 Codex 任务只负责一个连贯成果；启动、恢复或压缩后先得到有上限的当前事实包，再从短状态、功能地图、相关架构、测试和 Git 恢复。
- 项目文档保存当前事实并覆盖更新；复杂任务最多保留一个临时计划，不保存聊天全文、原始日志或无限增长的开发流水账。

## 系统内容

- 简短的全局 `~/.codex/AGENTS.md`：只保存零基础用户约定、关键安全边界和详细规则入口。
- 详细的母文件夹 `<WorkspaceRoot>\AGENTS.md`：保存完整工作流、目录模型、需求拓展、架构、Git、文档、任务和原生 subagent 规则。
- 九个 Codex standalone Skills：一个普通语言入口和八个专业能力，包括受控外部研究/源码复用与多项目能力融合，不依赖 Plugin 才能使用。
- 中央运行时 `~/.codex/codex-dev-kit/`：Git 检查、诊断、模板和脚本；项目只引用已验证的中央运行时，不复制整套框架。
- 母文件夹和项目 `.codex/config.toml`：模板只设置通用审批、sandbox 和 Goal，不写入任何子代理模型、推理强度、并发数、启用开关或中断设置。原生 `spawn_agent` 使用当前 Codex 任务和用户已有配置的官方默认行为。
- 不使用 Dev Kit Plugin、项目生命周期 Hook 或自定义 Agent；Codex 原生能力和 standalone Skills 是唯一运行入口。

## 本地开发

本仓库不会自动修改 `~/.codex`。脚本默认只预览，显式 `-Apply` 才写入目标位置，并在更新已有托管文件前创建备份。

```powershell
# 预览母文件夹结构
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\bootstrap-workspace.ps1 -WorkspaceRoot D:\开发

# 确认后真正创建母文件夹结构
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\bootstrap-workspace.ps1 -WorkspaceRoot D:\开发 -Apply

# 预览 standalone Skills、中央运行时和模板安装；确认后追加 -Apply
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\bootstrap\install.ps1 -WorkspaceRoot D:\开发 -Source (Resolve-Path .)

# 预览创建一个独立项目
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\create-project.ps1 -WorkspaceRoot D:\开发 -ProjectName my-app

# 确认后真正创建项目、Git 和首个本地回退点
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\create-project.ps1 -WorkspaceRoot D:\开发 -ProjectName my-app -Apply

# 完整验证（结构、Skill、脚本解析与单元测试）
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\validate-kit.ps1

# 也可单独运行完整回归测试
python -m unittest discover -s tests -p test_*.py -v
```

## 换电脑恢复

仓库完整保存了系统源码、九个 Skills、运行时脚本、全局短版 `AGENTS.md` 模板、完整中文母目录规则模板、项目模板和验证测试。仓库模板是详细规则的唯一可移植标准；安装器会替换新电脑的 Codex Home、母目录、工作区名称和 Skill 源路径。诊断会比较实际母目录规则与固定版本模板，防止只改本机却忘记同步 GitHub。即使母目录还是空的，也不需要预先手工创建 `AGENTS.md`。

推荐使用固定正式版本克隆，不使用缺少 Git 历史的 ZIP 作为长期安装源。新电脑上的零基础流程是：

1. 安装 Codex Desktop、Git 和 Python。
2. 把固定版本克隆为母目录下的 `codex-dev-kit`。
3. 在 Codex 中打开该仓库，直接说：“按照 `docs/RESTORE.md` 把这套系统安装到这台电脑，母目录使用 `D:\开发`。”
4. Codex 先预览，再运行 standalone 安装器；安装完成后完整退出并重新打开 Codex Desktop。
5. 新任务运行诊断，确认两层 `AGENTS.md`、九个 Skills、中央运行时和模板都已恢复。

完整步骤见 [新电脑恢复指南](docs/RESTORE.md)。项目源码和项目数据不包含在本系统仓库中；每个长期项目仍需拥有自己的私有远程备份。

## GitHub 分发

主安装方式是先取得固定 Tag 或 commit 的源码，再运行 standalone 安装器。禁止从未固定的 `main` 自动下载或执行远程脚本。安装器只在显式 `-Apply` 时写入短全局 `AGENTS.md`、standalone Skills、中央运行时和模板；它不会安装 Plugin、项目生命周期 Hook、自定义 Agent 或自定义 Rules。

```text
git clone --branch v0.2.10 --depth 1 <repository> codex-dev-kit
powershell -ExecutionPolicy Bypass -File .\codex-dev-kit\plugins\codex-personal-dev-kit\scripts\bootstrap\install.ps1 -WorkspaceRoot D:\开发 -Source .\codex-dev-kit -Apply
```

安装或更新后必须开启新 Codex 任务，让全局 `AGENTS.md` 和 Skills 重新加载。项目使用显式安全开发脚本和本地 Git 检查点，不依赖项目 Hook。

## 其他 Agent 自适配安装（Cursor / Claude 等）

本套件的强制核心——门禁脚本、测试、项目模板和两层 `AGENTS.md` 规则——是纯 Python + Git + Markdown，与具体 agent 无关；Codex 专属的只有 Skill 安装位置、`$skill` 调度语法、原生子代理调用和 `~/.codex` Home 假设。在正式的多宿主安装器（见 `docs/ROADMAP.md` 的 v0.3 主题）完成之前，其他 agent 的安装方式是：把本仓库链接交给你的 AI，直接说“按 README 的自适配指引把这套系统装到当前环境”。

AI 自适配约定（按当前宿主执行）：

1. 识别当前宿主的 Skills 目录：Codex 用 `~/.codex/skills`，Cursor 用 `~/.cursor/skills`，Claude 用 `~/.claude/skills`；把 `plugins/codex-personal-dev-kit/skills/` 下九个 Skill 目录连同 `references/` 原样复制过去。
2. 中央运行时脚本（`plugins/codex-personal-dev-kit/scripts/`）复制到本机一个固定位置，Skill 正文里的 `<dev-kit-root>` 一律指向该位置；门禁脚本、测试和安全边界不得改写。
3. 母目录与项目 `AGENTS.md` 模板照常安装并替换路径占位符；`AGENTS.md` 是跨 agent 事实标准，Cursor 和 Claude 的**项目内**都会读取。但「跨所有项目始终生效」的全局规则各宿主机制不同：Cursor **没有全局 `.mdc`**，要全局常开就把短全局 `AGENTS.md` 的关键约定放进 **User Rules**（设置 → Customize → Rules，纯文字）；`.mdc` + `alwaysApply` 只对单个项目生效。Claude 用其全局 memory / `CLAUDE.md` 等价机制。规则内容是标准，**放置位置随宿主变**，不要照抄 Codex 的放法。
4. 正文中的 `$skill-name` 调度理解为“读取对应 SKILL.md 并遵循”；宿主没有 `$` 语法时用自然语言路由，不需要 `agents/openai.yaml`。
5. “原生子代理”章节替换为当前宿主的原生子代理能力（如 Cursor 的后台子任务、Claude 的 subagent）；宿主没有子代理时由主代理顺序完成并如实说明。
6. 安装后验证：**非 Codex 宿主**用 `python plugins/codex-personal-dev-kit/scripts/validate_kit.py` 加 `python -m unittest discover -s tests -p "test_*.py"`（都是纯 Python，无 Codex 依赖）判定是否装好。`validate-kit.ps1` 是 **Codex 专属**——它调用 Codex Desktop 内置的 `.system/skill-creator` 校验器并假设 `~/.codex`，在 Cursor / Claude 上会直接报错，**不要**拿它当跨宿主通过标准。

已实测：Cursor 宿主可完整走契约→暂存→验证→检查点门禁（本套件自身的多个开发切片就是在 Cursor 会话中按此流程完成的）。Claude 路径遵循同样约定，尚未实测。

### Codex 专属内容 → 宿主等价（逐节映射表）

本套件的规则文件（两层 `AGENTS.md`、项目模板、九个 `SKILL.md`）主要为 Codex 宿主蒸馏，装到别的宿主后有一批 **Codex 专属内容**会变成死内容或误导。下表逐条给出在 Cursor / Claude 等宿主上的等价做法；核心方法论（用户合同、需求拓展、旧功能保护、文档记忆、权限边界、完成标准与证据分级）与 agent 无关，不需要翻译。安装后按此表把每一处翻译成当前宿主的做法，或按标注跳过。

| Codex 专属内容 | 主要出现位置 | 其他宿主（Cursor / Claude 等）的等价做法 |
|---|---|---|
| `$skill-name` 调度语法（`$codex-development-assistant` 等 `$` 前缀） | workspace-template / standalone `AGENTS.md` 第 4 节、各 `SKILL.md` | **翻译**：把 `$skill-name` 读作“定位当前宿主 skills 目录下同名 `SKILL.md` 并遵循”，按用户意图用自然语言路由；无需 `$` 前缀。 |
| 原生子代理工具名 `spawn_agent` / `list_agents`（及 wait / message / follow-up / interrupt） | `AGENTS.md` 第 9 节、`orchestrate-codex-team` 等 `SKILL.md` | **翻译**：换成当前宿主的原生子代理（Cursor 后台子任务 / Claude subagent）；宿主没有子代理时由主代理顺序执行并如实说明。单写入者、审查子代理只读等原则不变。 |
| `agents/openai.yaml`（Skill 元数据 / 隐式触发策略） | 各 Skill 目录、`audit-codex-kit` 检查单 | **跳过**：Cursor / Claude 不需要该文件；用 `SKILL.md` 的 `description` 触发即可。 |
| `.system` 前缀 与 `resolve-skill.ps1`（Skill 路径解析） | `AGENTS.md` 路径解析节、根 `AGENTS.md` | **翻译/跳过**：直接用当前宿主 skills 目录定位 `SKILL.md`；没有 `.system` 概念，无需该解析脚本。 |
| `{{CODEX_HOME}}` / `~/.codex`（Codex 主目录假设） | standalone / workspace `AGENTS.md`、README | **翻译**：换成当前宿主主目录——Cursor `~/.cursor`、Claude `~/.claude`（Skills、运行时脚本路径同步替换）。 |
| 第 12 节「Codex 桌面高级设置」（本地环境 / 环境列表 / 工作树 / Git 高级设置 / 分支前缀 `codex/` / 代码评审交付 / 提交指令） | workspace-template `AGENTS.md` 第 12 节 | **整节跳过**：这是 Codex Desktop 客户端专属 UI，其他宿主没有等价物，跳过不影响前 11 节方法论。 |
| “Codex Desktop / Local Project”措辞 | 少量 `SKILL.md` references | **翻译**：读作“当前宿主里一个长期项目对应一个工作区/项目”。 |
| `winget` 固定版本安装器；`feature_guard.py` / `validate-kit.ps1` / `next_step.py` 等门禁脚本 | `AGENTS.md`、多个 `SKILL.md`、`scripts/` | **保持不变（非 Codex 专属）**：winget 是 Windows 包管理器，门禁是纯 Python / PowerShell，任何宿主照用——它们是本套件的强制核心，不要改写。 |

### 宿主性能适配（有快照 / 文件监视的宿主，如 Cursor / VSCode）

纯 Codex CLI 不监视工作区、也没有检查点快照；Cursor / VSCode 会对**整个工作区**做文件监视 + 索引，Cursor 还对每次改动做检查点快照（影子仓库把整个工作区重打包一次）。装到这类宿主时必须补一层性能适配，否则并行开发会把编辑器拖到卡死：

- **并行 worktree 一律建到工作区外**：本套件 `worktree_layout.py` / `feature_guard.py worktree-path` 本就把副本放到项目旁的 `../.<项目名>-worktrees/`；**别手写 `git worktree add .local/...` 绕过它**——工作区内的 worktree 会被监视 / 快照 / 索引反复扫描，堆积后卡死（实测某工作区 100+ 个内建 worktree、检查点快照两天打了 9.65 GB，而项目自身 `.git` 只有几 MB）。
- **自动重生的产物排除出监视 / 搜索**：把 `**/__pycache__/**`、`**/*.sqlite3*`、`**/*.db` 等加进宿主的 `files.watcherExclude` / `search.exclude`（Cursor / VSCode 的 `settings.json`）。这些是产物不是源码，排除不影响 AI 读写。
- **把这条「减卡顿」规则放到宿主保证会读到的地方**：Cursor 用 **User Rules**（全局常开）或项目 `.cursor/rules/*.mdc`；长 / 项目 `AGENTS.md` 也可，只要该宿主确实每轮都读得到——放进宿主根本不常读的文件等于没放。

一句话：本套件的规则内容是标准，**放置位置和性能适配随宿主变**；安装时按宿主的规则机制和快照 / 监视特性适配，不要照抄 Codex 的放法。

### 安装 AI 必读自检清单（装完逐条自查，全部通过才算适配到位）

把本套件装到一个新宿主后，安装的 AI **必须**逐条自查——任何一条不通过都意味着「装了但会误解 / 会卡」：

- [ ] **宿主识别**：确认当前宿主是 Codex / Cursor / VSCode / Claude 中的哪个，并据此选规则放置位置与性能适配（见上文）。
- [ ] **短规则进系统规则**：短全局规则已放进本宿主「必读 / 常加载」的位置（Codex `~/.codex/AGENTS.md`；Cursor **User Rules**，因为它没有全局 `.mdc`；Claude 全局 memory）。
- [ ] **能读到完整规则**：短规则里「先读完整 `AGENTS.md`」的指针在本宿主真的会被执行；若本宿主不保证读到工作区外 / 祖先的完整 `AGENTS.md`，把关键约定（单写入者、worktree 外置、权限边界、完成标准）一并放进系统规则。
- [ ] **worktree 外置**：并行 worktree 建到工作区外（`../.<项目名>-worktrees/`，用 guarded `worktree-path`），**没有**任何 `.local/wt-*` 之类的工作区内副本。
- [ ] **worktree 硬门禁（有快照 / 监视的宿主）**：Cursor / VSCode 项目里有 `.cursor/hooks.json` + `.cursor/hooks/worktree_guard.py`，实测 `git worktree add <工作区内路径>` 被拦、外置路径放行。
- [ ] **产物排除**：`.vscode/settings.json` 的 `files.watcherExclude` / `search.exclude` 覆盖了 `__pycache__`、`*.sqlite3*`、`*.db`；大体积数据没堆在工作区里被快照。
- [ ] **9 个 Skills 可定位**：本宿主 skills 目录下能找到全部 9 个 `SKILL.md`；`$skill` 调度已理解为「读取对应 SKILL.md 并遵循」。
- [ ] **门禁可用**：`python .../feature_guard.py --help` 正常；**非 Codex 宿主**用 `python .../validate_kit.py` 加 `python -m unittest discover -s tests -p "test_*.py"` 全绿（不要用 Codex 专属的 `validate-kit.ps1`）。
- [ ] **Codex 专属内容已翻译 / 跳过**：按映射表处理了 `spawn_agent`、`.system`、`resolve-skill.ps1`、`{{CODEX_HOME}}`、`openai.yaml`、第 12 节桌面设置。

一句话：**规则内容照搬，放置位置和性能适配按宿主翻译**；上面任一条没做到，就是「装了但会误解或会卡」。

外部方法来源和归属说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。公开仓库不包含旧电脑的 Key、全局配置、项目源码、缓存或安装备份。

完整设计见 `docs/DESIGN.md`。
