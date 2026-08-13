# Release Review

- Version: v0.2.10
- Result: 通过。相对 v0.2.9 是**代码 + 文档**版：为有检查点快照 / 文件监视的宿主（Cursor / VSCode）把「worktree 建到工作区外」从「代码能算出安全路径」升级为「Cursor 上硬拦截」——随项目模板附带 `.cursor/hooks.json` 的 `beforeShellExecution` 守卫（`.cursor/hooks/worktree_guard.py`），拒绝解析到任一被监视工作区根内部的 `git worktree add`（含把父文件夹当工作区打开的情形），并附 `.vscode/settings.json` 把 `__pycache__` / `*.sqlite3*` / `*.db` 排除出监视与搜索；顺带修掉命令分类器被换行 / `$()` 绕过的 force-push 通道；文档层把「worktree 外置」写进短全局块与 README（新增「安装 AI 必读自检清单」），并澄清 `validate-kit.ps1` 为 Codex 专属。无 P0、无 P1；用户验收维如实标未验证（用户已明确授权自动定版，但未本人走查）。

评审基线：代码检查点 `43ee759`（= v0.2.9）之上追加本版改动。相对 v0.2.9 的差异含 `.py` 逻辑改动（`pre_tool_guard.py` 的换行 / 子命令替换 force-push 修复）、新模板文件（`.cursor/hooks.json`、`.cursor/hooks/worktree_guard.py`、`.vscode/settings.json`）、新测试文件（`tests/test_worktree_guard_hooks.py`）与多处规则 / 文档对齐（git-policy、短全局块、README、STATUS、ROADMAP、RESTORE、workspace-template）。
全量套件本轮实跑 `Ran 221 tests OK`（exit 0；211 顺延 + 10 条新守卫）；Cursor `worktree_guard.py` 以 8 组 stdin 载荷实测（拦 `.local/` / 相对内 / 换行藏 / 父文件夹；放行外置 / status / list；处理 Windows 反斜杠）；`validate_kit.py` 结构校验通过。

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | verified | 本版强化既有 DK-020 / DK-021（worktree 外置）：在 Cursor 上从「代码算出安全路径」升级为「hook 硬拦截」，并加产物监视排除；未新增 / 删除特性编号，`docs/FEATURES.md` DK-001~DK-022 不变。新增行为由 `tests/test_worktree_guard_hooks.py`（10 条）固定，221 用例实跑 OK。 |
| 02 | product-logic 产品逻辑 | verified | 目标（并行 / 多 agent 开发不冻结编辑器）被可执行地满足：hook 在 Cursor 拦下工作区内 worktree、watcherExclude 挡住产物 churn，实测 8/8 + 10 守卫全绿。 |
| 03 | business-flow 业务流程 | verified | 契约生命周期同 v0.2.9（含写入锁强制单写入者）；本发布检查点自身经 start→stage→verify→complete→checkpoint 闭合。 |
| 04 | data-model 数据模型 | verified | 未动数据模型；契约 JSON 字段与 managed-files SHA-256 结构同 v0.2.9。 |
| 05 | data-integrity 数据完整性 | verified | 未动 verify 前后暂存快照绑定与写入锁；本版无数据面改动。 |
| 06 | state-machine 状态机 | verified | 未动状态机；`next_step.py` 仍唯一驱动阶段推进。 |
| 07 | api-contract API 契约 | verified | 未增删 `feature_guard.py` 子命令；`worktree_guard.py` 是独立的宿主 hook，非 guard 子命令。 |
| 08 | architecture 架构 | verified | 新增宿主适配层：Cursor `.cursor/hooks.json` `beforeShellExecution` 守卫（自包含、仅 stdlib、只拦「工作区内 worktree add」）加项目模板 `.vscode/settings.json`；与既有 `worktree_layout.py` / `pre_tool_guard.py` 分层不冲突（`.cursor/hooks.json` ≠ 被禁用的 `.codex/hooks.json`，短块已注明区别）。 |
| 09 | code-quality 代码质量 | verified | `Ran 221 tests OK`（211 + 10）；`worktree_guard.py` 8 组载荷实测；`pre_tool_guard.py` force-push 修复有换行 / `$()` 正反用例；`validate_kit.py` 结构校验通过。 |
| 10 | security 安全 | verified | 修掉一条**旧** force-push 绕过：分类器 `shlex(whitespace_split)` 折叠换行 + `$()`/反引号未解析，而 `feature_guard verify` 会执行被过滤命令 → 现按行拆分 + 递归解析子命令，`git push --force` 藏在换行 / `$()` 均被拦（新测试固定）。其余注入 / 路径逃逸 / 凭证暂存守卫不变。 |
| 11 | authorization 授权 | verified | 未动 publish / sync 授权链；远程发布仍走 guarded publish + 用户逐字确认串 + dry-run + 回读。 |
| 12 | error-handling 错误处理 | partial | 同 v0.2.9：GuardError→`ERROR:`+exit 1、拒绝无 Traceback；`worktree_guard.py` 解析异常一律放行（fail-open，避免误伤终端），是有意取舍。 |
| 13 | performance 性能 | partial | 无受控基准；221 用例 414s 属单机并发噪声区间。hook 每条 shell 命令跑一次纯 stdlib、无 I/O 的轻量分类，未做延迟基准。 |
| 14 | deployment 部署准备 | partial | 同 v0.2.9：install / create-project preview / 幂等；新模板文件随 `bootstrap-project.ps1` 的 `-Recurse -Force` 复制（含点目录），装机侧仍需正式版本后重装运行时生效（本机态，非源码缺陷）。 |
| 15 | observability 可观测性 | verified | `next_step` / `status` / `audit_project` 自证；本版新增行为均有测试可见。 |
| 16 | backup-recovery 备份与恢复 | partial | 同 v0.2.9：rollback 安全属性 + 快照救命网；一次成功 restore-version 仍为单测证据。 |
| 17 | migration-rollback 迁移与回滚 | partial | 同 v0.2.9：正式版本门三态拒绝、restore-version 提示；本版未改回滚代码。 |
| 18 | ux 用户体验 | verified | 零基础不再手配：新项目自动带 watcherExclude 与 hook；README 增「安装 AI 必读自检清单」让装机 AI 自查不误解。 |
| 19 | ui 界面 | not-applicable | 无图形界面；交付面为 CLI 文本 + Markdown + Skills + JSON 配置，文本质量并入维度 18。 |
| 20 | user-acceptance 用户验收 | not-verified | 用户提出并确认了「让并行开发不再卡」的需求、明确授权自动定版；按定义仍需用户本人走查，代理不代签，故如实标未验证。 |
| 21 | ai-completion-audit AI 完成度审计 | verified | 无 TODO / stub / 占位；新代码均有「改坏必红」守卫（force-push 正反用例、hook 8/8、规则文本存在性、模板文件存在性）；`.cursor/hooks.json` 不是被禁用的 `.codex/hooks.json`，与「不装 Codex 生命周期 Hook」不冲突。 |

## 本次未修、已登记的发现

无 P0、无 P1。以下为已知、低危或有意取舍：

- **worktree_guard fail-open（维度 12 / 13）**：hook 解析异常或超时按 fail-open 放行，是为避免误伤终端的有意取舍；硬拦截只针对能确认「解析到工作区内」的 worktree add，其余（含 `bash -c "..."` 包裹）由 pre_tool_guard（Codex 侧）与散文规则兜底。
- **父文件夹打开时的仓库根推导（维度 08）**：`worktree_layout.py` 仍按 git 仓库根推导 `../.<project>-worktrees/`；当用户把父文件夹当工作区打开时该路径可能仍落在被监视树内——已由 Cursor hook 按 `workspace_roots`（被监视根，而非只按 git 根）兜住，并在 README 说明「打开仓库本身，别打开祖先目录」。
- 顺延自 v0.2.9 的 partial 维度（性能基准、端到端 restore-version、部署）证据等级不变。

## 静态门的固有上限

同前：本终审门只校验结构完整、版本匹配、状态合法与证据非空，不能证明证据本身真实。本版证据以本轮 221 用例全量 OK、`worktree_guard.py` 8/8 实测、10 条新守卫、force-push 正反用例与 `validate_kit.py` 结构校验为基线。
