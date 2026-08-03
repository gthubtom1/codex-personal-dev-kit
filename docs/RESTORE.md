# 新电脑恢复指南

这份指南用于把 GitHub 中的固定 Dev Kit 版本恢复到一台新的 Windows 电脑。用户不需要手工编辑 Git、`AGENTS.md`、Skills、Hooks、Plugins 或子代理配置；可以在 Codex 中直接要求 AI 按本文件执行。

## GitHub 中保存什么

- `plugins/codex-personal-dev-kit/assets/standalone/AGENTS.md`：全局短版规则模板。
- `plugins/codex-personal-dev-kit/assets/workspace-template/AGENTS.md`：母目录详细规则模板。
- 九个 standalone Skills、中央安全运行时、项目模板、安装/更新/诊断脚本。
- 当前设计、功能地图、正式版本、测试和本地验证入口。

不保存旧电脑的 API Key、全局 `config.toml`、聊天记录、安装备份、Python 缓存、压力测试输出或各个项目源码。

## 推荐恢复流程

1. 安装 Codex Desktop、Git 和 Python 3。
2. 选择母目录；默认示例是 `D:\开发`，没有 D 盘时可以使用其他绝对路径。
3. 从私有 GitHub 克隆固定正式版本：

```powershell
git clone --branch v0.2.4 --depth 1 <repository-url> D:\开发\codex-dev-kit
```

4. 先预览安装：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\开发\codex-dev-kit\plugins\codex-personal-dev-kit\scripts\bootstrap\install.ps1 -WorkspaceRoot D:\开发 -Source D:\开发\codex-dev-kit
```

5. 确认预览目标正确后追加 `-Apply`。安装器根据实际环境生成：

```text
<CodexHome>\AGENTS.md
<CodexHome>\skills\<nine-skill-folders>
<CodexHome>\codex-dev-kit\
<WorkspaceRoot>\AGENTS.md
<WorkspaceRoot>\workspace.json
```

6. 完整退出 Codex Desktop，再重新打开并创建新任务。仅新建任务而不退出整个应用，可能继续使用旧 Skill 目录缓存。
7. 运行安装诊断：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <CodexHome>\codex-dev-kit\scripts\bootstrap\diagnose.ps1 -WorkspaceRoot D:\开发
```

## 恢复项目

Dev Kit 仓库只备份辅助系统，不自动包含 `projects/<name>`。每个长期项目都是独立 Git 仓库，应分别保存到私有远程仓库。恢复项目后，把它放回 `<WorkspaceRoot>\projects\<project-name>`，在 Codex 中直接打开该项目文件夹，再让 `$onboard-codex-project` 做只读检查和必要接入。

## 安全边界

- 安装器默认只预览，只有显式 `-Apply` 才写入。
- 不自动修改全局 `config.toml`、子代理模型、Plugin、Hook 或自定义 Agent。
- 不从未固定的 `main` 自动下载并执行脚本。
- 不把 API Key、密码、私人源码或用户数据提交到本仓库。
- GitHub ZIP 缺少正常 Git 历史和固定来源元数据，不作为长期更新源；使用固定 tag 的 Git checkout。
- 远程仓库创建、push、公开发布和许可证选择必须由用户明确授权。
