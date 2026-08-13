---
name: codex-safe-development
description: 在 Git、测试、审查和权限保护下实施功能、修复、重构或配置变更，并创建本地检查点。用户要求写代码、修 bug、重构、添加测试、修改依赖、数据库迁移、发布准备、远程同步、分支整合、撤销暂存、清理 Worktree、安装 Windows 开发工具，或希望 AI 自动开发但可回滚时使用。
---

# Codex Safe Development

完成用户要求的最小完整改动，并留下可验证、可回滚的本地历史。

## 开发循环

1. 读取当前范围内的 `AGENTS.md`、Goal、项目状态和相关源码。确认工作目录、Git 状态、分支或 Worktree，以及已有用户修改。任何时候不确定当前该做哪一步，运行 bundled `scripts/next_step.py --root .`，按它打印的 NOW/NEXT 顺序执行，不要凭记忆重排流程。
2. 对中大型任务先调用 `$prepare-codex-goal`。存在独立并行工作时再调用 `$orchestrate-codex-team`。
3. 读取 [git-policy.md](references/git-policy.md)。默认沿当前本地开发线工作，绝不把“保存版本”实现成不断创建分支；只有隔离实验、后台任务或并行写入确实能降低冲突时才创建分支或 Worktree。不得把用户未提交的无关修改混入检查点。
4. 读取 [feature-protection.md](references/feature-protection.md)。在已有 Dev Kit 项目第一次编辑前，用 bundled `scripts/feature_guard.py` 建立当前变更契约，声明本次改变的功能 ID、邻接验证、有意删除，以及确需接管的已有脏文件。没有契约不得直接修改源码。
5. 在编辑前确定最小影响面、回归风险和验证计划。遵循项目现有架构与工具，不顺手重构无关代码。
6. 分成可验证的小切片实现。新增抽象必须真实减少复杂度或匹配项目现有模式。
7. 聚合核对 `docs/FEATURES.md` 和 `docs/features/**/*.md` 中受影响的现有能力，再按 [quality-gates.md](references/quality-gates.md) 选择风险相称的测试、静态检查、构建和行为验证。
8. 审查最终 diff 后，用 feature guard `stage` 明确暂存任务文件，并用 `verify` 让门禁实际运行验证命令、记录退出码、功能 ID、Git tree 和内容指纹。最后运行 `complete`；自由文本不能代替成功命令。
9. 每个独立且验证通过的切片必须在结束前运行 bundled `feature_guard.py checkpoint` 创建本地回退点。该命令只提交已验证的精确快照，使用一次性本地 Dev Kit 身份，不修改用户的全局 Git 配置，也不创建版本分支。不要在托管项目中直接运行 `git commit`。
10. 用户把一个完整阶段称为 v1.2、正式版本、新版本或要求以后能按版本找回时，读取 [local-versions.md](references/local-versions.md)。先完成 [release-readiness.md](references/release-readiness.md) 的 21 维发布终审并覆盖更新 `docs/RELEASE-REVIEW.md`，再更新 `docs/VERSIONS.md` 和项目版本字段，把它们放进同一个最终验证检查点，然后用 guard-managed `version` 创建仅本地的不可移动标签；门禁会拒绝缺少完整终审的正式版本，普通检查点也不得冒充正式版本。
11. 用户要求同步远程、整合分支、撤销暂存、清理 Worktree 或安装 Windows 全局工具时，读取 [guarded-operations.md](references/guarded-operations.md)，只使用对应的精确受控命令。
12. 更新真正发生变化的架构、状态或运行说明，然后调用 `$manage-project-continuity` 完成交接。

## 高风险路由

遇到以下情况必须读取对应参考：

- 新增或升级依赖：[dependency-and-supply-chain.md](references/dependency-and-supply-chain.md)
- 身份、权限、密钥、上传或外部输入：[security.md](references/security.md)
- 数据库、结构或历史数据变化：[data-migrations.md](references/data-migrations.md)
- 准备上线、打包或交付：[release-readiness.md](references/release-readiness.md)

## 权限边界

可自动执行：项目内编辑、已有测试和构建、本地分支、本地 Worktree、本地检查点提交，以及满足专用不变量的精确撤销暂存和已整合 Worktree 清理。

先询问：生产依赖、付费服务、重大架构替换、数据库结构迁移、访问项目外数据、远程同步、安装全局工具或修改全局 Codex 配置。用户授权全局工具后，由 AI 使用精确版本的 guarded winget installer，不要求用户执行命令。

禁止原始或未授权执行：raw Git push/pull/merge/rebase/restore/Worktree removal、远程 release、deploy、包发布、生产迁移、基础设施 apply/destroy、强制 clean、`reset --hard` 和不可恢复数据操作。已授权的发布、快进同步、线性分支整合、精确撤销暂存和 Worktree 清理必须走 guarded commands；分叉历史不会自动 merge/rebase。

## 完成标准

只有在请求行为已实现、feature guard 已验证、相关验证已运行、diff 已审查、风险和未验证项已说明、项目状态已更新且本地回退点已经形成时才声明完成。没有形成匹配的回退点时，必须把任务报告为未完成并继续处理。
