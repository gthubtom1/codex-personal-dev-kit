# Git 安全与检查点

## 默认开发线

- 为零基础用户减少需要整合的分支。正常顺序开发默认继续当前本地分支，并用小型检查点提交提供回滚。
- 分支用于隔离并行工作或高风险实验，不是版本编号。不得为普通的“v1、v2、v3”存档不断创建 `codex/v*` 分支。
- 只有隔离高风险实验、计划任务、真正独立的并行写入或用户明确要求时才创建额外分支或 Codex Worktree。
- 并行写入默认避免；优先让子代理只读，主代理单独实现。
- 使用 Codex Worktree 时优先通过桌面端 Handoff 把成果带回主工作区，不要求用户手工解决常规合并。
- 不切换、删除或重写用户正在使用的分支。

## 脏工作树

1. 先读 `git status --short` 和相关 diff。
2. 把已有修改视为用户工作，除非能证明属于当前任务。
3. 只编辑必要文件。已有 Dev Kit 项目不得直接运行 `git add`；通过 `feature_guard.py stage --path <file>` 逐个明确暂存，让门禁排除契约开始前的用户修改。
4. 如果任务必须修改契约开始前已经脏的文件，在 `start` 时用 `--own-path <file>` 明确接管；否则该路径不得进入检查点。
4. 无法分离时不提交，报告哪些文件阻止了安全检查点。

## 检查点

- 在一个行为切片完成且验证通过后提交。
- 提交消息使用项目约定；没有约定时使用 `checkpoint: <outcome>`。
- 提交前查看 staged diff 和 staged 文件列表。
- 验证完成后运行 `python <dev-kit-root>/scripts/feature_guard.py checkpoint --root . --message "checkpoint: <outcome>"`。托管项目中的原始 `git commit` 会被拒绝，避免身份缺失、错误暂存或忘记关闭契约。
- 不为了“干净”提交缓存、构建产物、密钥或无关格式化。
- 自动检查点使用一次性的 `Codex Dev Kit <codex-dev-kit@local.invalid>` 身份，不修改全局 Git 身份，也不伪装成用户。

## 正式版本

- 普通检查点和正式产品版本必须分开。只有用户接受的完整、已验证里程碑才更新 `docs/VERSIONS.md` 并通过 `feature_guard.py version --name vX.Y.Z` 创建本地语义标签。
- 本地正式标签指向包含代码、测试和当前文档的最终检查点。旧标签不可移动、覆盖或删除，也不为版本创建分支。
- 用户不记得版本号时，先按 `docs/VERSIONS.md` 的能力描述匹配，再用 `feature_guard.py versions` 核对真实标签；不要让用户选择 commit hash。
- 指定版本恢复通过 `feature_guard.py restore-version --name vX.Y.Z` 创建新的恢复检查点，保留较新提交、标签和完整版本索引。

## 禁止自动操作

- push、pull、merge、rebase、远程 tag/release，以及原始 `git tag`。本地正式版本只能走 guard-managed `version`。
- `commit --amend`、强制分支删除、filter-branch/filter-repo。
- `reset --hard`、clean、restore 或 checkout 丢弃未确认修改。
- 删除 Worktree、stash 或 reflog 中可能仍需恢复的内容。

## 零基础回退

- 用户说“回到上一个版本”“撤销刚才那次开发”或“恢复上一个回退点”时，先确认当前没有未保存修改，再运行 `feature_guard.py rollback --root .`。
- 回退会把上一个已提交版本恢复成一个新的本地检查点；当前版本仍保留在 Git 历史中，因此可以再次恢复。
- 当前有未保存修改、开放契约或冲突时必须先保存或说明，绝不自动丢弃。
- 更早或指定版本先用 Git 历史识别目标，再采用同样的“新增恢复提交”原则。不得使用 `reset --hard`、强制 checkout、原始 `git revert` 或删除历史来冒充简单回退。
