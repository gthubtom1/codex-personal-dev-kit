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
- Git 缺失时会自动初始化并建立安全基线；每次验证完成后 Stop 门禁要求真正保存本地回退点，不会只留下几千个未提交文件，也不会用 `codex/v1`、`codex/v2` 分支冒充版本历史。
- 用户可以直接说“回到上一个版本”。助手会先保护未保存工作，再用一个新的恢复提交回到上一回退点，不改写或删除历史。
- 子代理只使用 Codex 当前任务内的原生 collaboration 能力；不会用侧边栏新任务、聊天、跨任务消息或 Handoff 假装子代理。
- Dev Kit 只编排原生 subagent、任务、Worktree、Git 审查面板和 Appshots，不拦截 `Agent` 工具，也不注册另一套代理接口。
- 一个 Codex 任务只负责一个连贯成果；启动、恢复或压缩后先得到有上限的当前事实包，再从短状态、功能地图、相关架构、测试和 Git 恢复。
- 项目文档保存当前事实并覆盖更新；复杂任务最多保留一个临时计划，不保存聊天全文、原始日志或无限增长的开发流水账。

## 系统内容

- 简短的全局 `~/.codex/AGENTS.md`：只保存零基础用户约定、关键安全边界和详细规则入口。
- 详细的母文件夹 `D:\开发\AGENTS.md`：保存完整工作流、目录模型、需求拓展、架构、Git、文档、任务和原生 subagent 规则。
- 七个 Codex standalone Skills：一个普通语言入口和六个专业能力，不依赖 Plugin 才能使用。
- 中央运行时 `~/.codex/codex-dev-kit/`：Git 检查、诊断、模板和脚本；项目只引用已验证的中央运行时，不复制整套框架。
- 母文件夹和项目 `.codex/config.toml`：模板启用原生 multi-agent，默认请求子代理为 `gpt-5.6-luna`/`max`，并允许多个并行子代理；Codex 原生解析为“本次 spawn 明确值 > `[agents]` 默认 > 当前父任务值”，所以不会把主对话锁死。合并脚本只补充缺失的子代理默认键，保留已有 `enabled`、模型和推理强度以及主对话模型；若用户配置显式关闭原生 agent 闸门，诊断会报告并停止子代理路由，不会偷偷打开。
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

# 验证 Dev Kit
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\validate-kit.ps1
```

## GitHub 分发

主安装方式是先取得固定 Tag 或 commit 的源码，再运行 standalone 安装器。禁止从未固定的 `main` 自动下载或执行远程脚本。安装器只在显式 `-Apply` 时写入短全局 `AGENTS.md`、standalone Skills、中央运行时和模板；它不会安装 Plugin、项目生命周期 Hook、自定义 Agent 或自定义 Rules。

```text
git clone --branch v0.1.0 --depth 1 <repository> codex-dev-kit
powershell -ExecutionPolicy Bypass -File .\codex-dev-kit\plugins\codex-personal-dev-kit\scripts\bootstrap\install.ps1 -WorkspaceRoot D:\开发 -Source .\codex-dev-kit -Apply
```

安装或更新后必须开启新 Codex 任务，让全局 `AGENTS.md` 和 Skills 重新加载。项目使用显式安全开发脚本和本地 Git 检查点，不依赖项目 Hook。

完整设计见 `docs/DESIGN.md`。
