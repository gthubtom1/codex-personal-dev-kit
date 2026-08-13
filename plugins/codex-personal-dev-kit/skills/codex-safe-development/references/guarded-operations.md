# 受控高级操作

这些命令解决“原始命令太危险，但不能把工作甩给零基础用户”的场景。只在用户授权外部或系统状态变化后调用；本地精确撤销暂存和安全 Worktree 清理可按普通开发权限自动执行。

## 远程同步

使用 `feature_guard.py sync --root . --remote <name> --branch <current> --confirm-remote-url <url>`。

- 要求当前工作树干净、HEAD 是 Dev Kit 检查点、remote URL 和当前分支精确匹配。
- 只 fetch 指定分支；远程领先且本地是其祖先时只做 fast-forward。
- 本地领先时不覆盖；双方分叉时停止，不自动 merge/rebase。

## 本地分支整合

使用 `feature_guard.py integrate --root . --source-branch <exact-local-branch>`。

- 只接受精确本地分支和干净的 Dev Kit 检查点。
- 当前分支是来源分支祖先时只做 fast-forward；已经包含来源时幂等返回。
- 历史分叉时保留两边并另开冲突解决任务，不生成未经验证的 merge commit，也不 rebase。

## 撤销暂存

使用 `feature_guard.py unstage --root . --path <exact-file>`。

- 只能撤销当前变更契约通过 guard 暂存的精确文件。
- 只修改 Git index，工作区内容保持不变；清除旧验证证据，之后重新 stage/verify。
- 恢复已提交版本使用 `rollback` 或 `restore-version`；不得用 raw restore 丢弃未确认内容。

## Worktree 位置

新建并行工作副本前，用 `feature_guard.py worktree-path --root . --name <label>` 取路径，再交给 `git worktree add`。

- 路径在运行时按当前项目推导（项目旁边的 `.<项目名>-worktrees/<label>`），不写死任何机器或目录名。
- 副本一律建在打开的项目外面：被忽略规则盖住的路径 AI 自己读不了，而副本是它还要读写的。
- 只规划新副本；目标已被占用时报错换名，不移动、不覆盖任何已存在的副本。

## Worktree 清理

使用 `feature_guard.py remove-worktree --root . --path <exact-registered-path>`。

- 不能删除当前打开的 Worktree、锁定 Worktree、含修改/未跟踪/忽略文件的 Worktree。
- 目标 HEAD 必须已经包含在当前项目历史中；存在唯一提交就保留。
- 不使用 `--force`，也不删除对应分支。

## Windows 全局工具

从 `codex-safe-development` Skill 目录运行：

```text
python scripts/install_global_tool.py --package-id <exact-id> --version <exact-version> --scope <user|machine> --confirm-package-id <same-id> --confirm-version <same-version> --confirm-scope <same-scope>
```

- 当前仅支持 winget 官方 source 的首次精确安装，默认推荐 `user` scope。
- 先核对 package/version；检测到其他已安装版本时拒绝隐式升级或降级；完成后再次验证。
- winget 不可用时停止，不自动下载工具或改用其他包管理器。
