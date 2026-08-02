---
name: onboard-codex-project
description: 将新建或已有软件项目接入 Codex Personal Dev Kit，建立安全的 Git 基线、专业目录、AGENTS.md、项目文档、Codex 配置和可复现命令。用户要求创建新项目、接管旧项目、整理项目文件夹、初始化 Git、拆分巨型文件、为长期 AI 开发做准备，或项目缺少清晰结构和运行说明时使用。
---

# Onboard Codex Project

把项目整理成未来任务可以快速理解、验证和回滚的状态。只处理用户指定的项目根目录，不扫描同级其他项目。

## 工作流

1. 确认项目根目录和用户允许的范围。用户明确说不要读取本地代码时，只提供方案，不访问文件。
2. 判断项目类型：空目录或仅有草稿为新项目；已有源码、清单、数据库或 Git 历史为现有项目。
3. 对现有项目先做只读评估。读取 [project-assessment.md](references/project-assessment.md)，优先检查目录、清单、入口、测试、Git 状态和大文件，不要一开始完整读取超大源码。
4. 新建或重组目录时读取 [repository-layout.md](references/repository-layout.md)。每个长期项目默认使用独立目录和独立 Git 仓库，不把无关项目塞进同一个仓库。
5. Git 不存在或还没有任何提交时，自动初始化本地仓库、默认分支和首个基线回退点。先检查 `.gitignore`、生成目录、密钥、本地数据库和用户数据；发现可疑路径就停下整理忽略规则，不把它们塞进 Git。
6. 按下面的固定顺序解析 `bootstrap-project.ps1`，不得把 Skill 目录误当成 runtime 根目录，也不得递归搜索整个磁盘：
   1. 先确定 Codex Home：优先使用非空的 `CODEX_HOME`，否则使用 `%USERPROFILE%\.codex`。
   2. 首选 `<CodexHome>\codex-dev-kit\scripts\bootstrap-project.ps1`。这是 standalone 安装后的规范位置。
   3. 如果该文件缺失，但 `<CodexHome>\codex-dev-kit\source.json` 可读且声明了已验证的本地 `source`，使用 `<source>\plugins\codex-personal-dev-kit\scripts\bootstrap-project.ps1`。
   4. 如果仍缺失，只检查当前项目明确引用的母目录下 `<WorkspaceRoot>\codex-dev-kit\plugins\codex-personal-dev-kit\scripts\bootstrap-project.ps1`。
   5. 三个候选都不存在时，报告检查过的准确路径并停止；不要联网下载、创建替代脚本、扫描兄弟项目或修改全局配置。
7. 使用解析到的脚本预览缺失模板，并显式传入当前项目对应的 `-WorkspaceRoot <母文件夹>`；确认目标正确后再追加 `-Apply -InitializeGit -CreateBaselineCheckpoint` 写入。脚本只创建缺失文件，不覆盖已有项目文件；已有 Git 历史不会被替换或重新初始化。只有脚本能从 `projects/<项目>` 结构或已安装的 standalone metadata 明确推导母文件夹时，才可省略 `-WorkspaceRoot`。
8. 用真实发现更新 `AGENTS.md`、`docs/PROJECT.md`、`docs/FEATURES.md`、`docs/ARCHITECTURE.md`、`docs/STATUS.md` 和 `docs/ROADMAP.md`。FEATURES 为当前用户能力分配稳定 ID，并记录完整入口/接线链路、预期结果、验证、重要性和状态；未知命令明确标为未确认，不要编造。
9. 识别职责混杂、耦合过高或难以验证的复杂度热点。文件行数只用于帮助定位，不作为强制拆分标准；是否拆分由职责、变更风险、测试难度和项目约定决定，也不要在接入阶段顺手进行无关的大规模重写。
10. 运行成本最低的基线检查。记录成功命令、失败原因和环境缺口。
11. 若已有 Git 历史且本次产生了独立、可验证的接入改动，使用 `$codex-safe-development` 在当前本地开发线上创建回退点。只有隔离实验或并行写入确有价值时才创建额外分支或 Worktree。不得 push、merge、rebase 或发布。

## 接入完成标准

- 项目边界和用户目标清楚。
- Git 可用于查看差异和回滚，且用户原有修改被保留。
- 启动、测试、检查命令有真实来源或被明确标记为待确认。
- 当前架构、状态和下一步可以由新任务在几分钟内定位。
- 已存在的用户能力可由稳定功能 ID、接线路径和验证入口定位。
- 复杂度热点或技术债被记录为后续候选，没有混入无关重构。

## 输出

用通俗语言报告：项目类型、创建或更新的文件、Git 状态、已验证命令、主要风险，以及最值得开始的下一个 Goal。
