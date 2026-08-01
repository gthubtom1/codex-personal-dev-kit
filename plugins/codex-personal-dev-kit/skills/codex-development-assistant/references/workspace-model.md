# 母文件夹与项目模型

## 推荐结构

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

- 母文件夹不是所有源码的单一 Git 仓库。
- 每个 `projects/<name>/` 是独立 Git 仓库，也是该项目在 Codex Desktop 中的主工作文件夹。
- `codex-dev-kit/` 是框架源码；安装成 Plugin 后所有项目复用，不复制到项目中。
- `archives/` 存放不活跃项目；移动或删除前必须确认恢复方式。
- `workspace.json` 只记录目录约定和版本，不维护容易漂移的 `projects.json`。项目列表由扫描 `projects/` 得到。

## 创建新项目

1. 在母文件夹任务中把项目名规范化，拒绝路径穿越、盘符和嵌套绝对路径。
2. 创建 `projects/<slug>/`，写入缺失模板，初始化独立 Git 和首个本地回退点。
3. 不读取或修改其他项目。
4. 创建完成后提示用户在 Codex 中把新项目文件夹作为主工作文件夹并开启新任务。Codex 在新任务开始时才会完整加载该项目的 `AGENTS.md` 和 `.codex/config.toml`。

## 开发已有项目

用户先在 Codex 中直接打开具体项目文件夹，再在该项目任务中说“继续”“修改”或提出新需求。不要在母文件夹中替用户选择、进入或继续某个已有项目。母文件夹级任务只做新建、总览、归档和只读组合审计，不跨项目同时写代码。
