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
- FEATURES 可按领域拆到 `docs/features/`，门禁会聚合读取并拒绝重复 ID；检查点只接收明确暂存的任务文件，并绑定门禁实际运行的测试命令和内容指纹。
- 默认只有一个源码写入者并沿当前开发线创建本地回退点，减少分支合并冲突。
- 子代理只使用 Codex 当前任务内的原生 collaboration 能力；不会用侧边栏新任务、聊天、跨任务消息或 Handoff 假装子代理。
- 一个 Codex 任务只负责一个连贯成果；启动、恢复或压缩后先得到有上限的当前事实包，再从短状态、功能地图、相关架构、测试和 Git 恢复。
- 项目文档保存当前事实并覆盖更新；复杂任务最多保留一个临时计划，不保存聊天全文、原始日志或无限增长的开发流水账。

## Plugin 内容

- 一个用户入口：`codex-development-assistant`
- 六个内部能力：项目接入、Goal 准备、团队编排、安全开发、项目连续性、系统审计
- Plugin Hook 和 Codex Rules：阻止破坏性命令，并在编辑、上下文压缩、提交和结束任务时执行功能保全门禁
- 工作区与项目模板、原生 subagent 的专业只读角色提示、安装/诊断/审计/验证脚本

## 本地开发

本仓库不会自动修改 `~/.codex`。脚本默认只预览，显式 `-Apply` 才写入目标位置，并在更新已有托管文件前创建备份。

```powershell
# 创建母文件夹结构
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\bootstrap-workspace.ps1 -WorkspaceRoot D:\开发

# 创建一个独立项目
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\create-project.ps1 -WorkspaceRoot D:\开发 -ProjectName my-app

# 验证 Dev Kit
powershell -ExecutionPolicy Bypass -File .\plugins\codex-personal-dev-kit\scripts\validate-kit.ps1
```

## GitHub 分发

发布后使用固定 Tag 或 commit 安装 Marketplace，禁止从未固定的 `main` 自动下载：

```text
codex plugin marketplace add OWNER/codex-dev-kit --ref v0.1.0
codex plugin add codex-personal-dev-kit@codex-dev-kit
```

安装或更新 Plugin 后必须开启新 Codex 任务。Plugin Hooks 还需要在 Codex 的 Hook 审查界面确认信任。

本地开发 Marketplace 使用目录路径且不带 `--ref`；全局 Profile 的 `source.json` 会另外记录该目录的真实 Git HEAD 和插件版本。`diagnose.ps1` 会检查本地源码是否变脏或漂移。GitHub Marketplace 才使用固定 Tag/commit 的 `--ref`。

完整设计见 `docs/DESIGN.md`。
