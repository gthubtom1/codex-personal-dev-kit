# Release Review

- Version: v0.2.11
- Result: 通过。v0.2.11 是 v0.2.10 的**审查跟进修复版**（源自本仓 10 智能体只读审计）。核心：堵上一个 **HIGH 分类器漏洞**（`_catastrophic_delete` 现在在换行归一化之后跑、`$()` 提取改成配对括号扫描，`echo x\nrm -rf /` / `format c:` / 嵌套 `$(...)` 不再溜过 `classify_command`）；化解「不装 Hook」文档与已发 `.cursor/hooks.json` 的**危险矛盾**（限定为「不装会改 Codex 原生行为的 lifecycle hook；发的是 fail-open 的 Cursor shell 守卫」）；把 watcher-exclude 补进两层 AGENTS + 项目模板；修过期文档（DESIGN Handoff→guarded `integrate`、README 映射表 `validate-kit.ps1` Codex 专属 + `.cursor`/`.vscode` host-adaptation 行 + `$skill` standalone-§4 指针、self-check 限定 Cursor）；把 `tests/test_worktree_guard_hooks.py` 接进 FEATURES DK-021；加强守卫测试。无 P0、无 P1；用户验收维如实标未验证。已知延后 v0.3：已有项目迁移。

评审基线：代码检查点 `541e7d4`（= v0.2.10）之上追加本版改动。差异含 `pre_tool_guard.py` 的 `_catastrophic_delete`/`_extract_substitutions`/`classify_command` 修复、`tests/test_worktree_guard_hooks.py` +2 守卫、以及一批规则/文档对齐（README、两层+项目模板 AGENTS.md、DESIGN、FEATURES、STATUS、ROADMAP、VERSIONS、.vscode/settings.json）。
全量套件本轮实跑 `Ran 223 tests OK`（exit 0；221 + 2 新守卫）；`classify_command` 以 11 组正反用例实测（换行藏的 `rm -rf /`/`format c:`/`Remove-Item`、嵌套 `$()`、backtick 全拦；正常命令放行）；`validate_kit.py` 结构校验通过。

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | verified | 本版为 v0.2.10 缺陷跟进，不新增用户特性；把 v0.2.10 已交付的 worktree 硬门禁的验证入口 `tests/test_worktree_guard_hooks.py` 正式接进 `docs/FEATURES.md` DK-021（此前孤儿）。223 用例实跑 OK。 |
| 02 | product-logic 产品逻辑 | verified | 目标（并行开发不冻结编辑器 + 命令门禁不被绕过）更完整：分类器补齐换行/嵌套 `$()` 删除类，hook/watcherExclude 不变。 |
| 03 | business-flow 业务流程 | verified | 契约生命周期同 v0.2.10；本发布检查点自身经 start→stage→verify→complete→checkpoint 闭合。 |
| 04 | data-model 数据模型 | verified | 未动数据模型。 |
| 05 | data-integrity 数据完整性 | verified | 未动 verify 前后快照绑定与写入锁。 |
| 06 | state-machine 状态机 | verified | 未动状态机。 |
| 07 | api-contract API 契约 | verified | 未增删子命令；`classify_command` 签名不变（`_depth` 默认参数向后兼容）。 |
| 08 | architecture 架构 | verified | 文档层把「不装 Hook」与「已发的 Cursor shell 守卫」的边界画清（`.cursor/hooks.json` = fail-open beforeShellExecution 守卫 ≠ 会改 Codex 原生行为的 lifecycle hook），并把 watcher-exclude 补齐进两层 AGENTS + 模板，消除审查发现的分层不一致。 |
| 09 | code-quality 代码质量 | verified | `Ran 223 tests OK`（221 + 2）；`_catastrophic_delete`/嵌套 `$()` 修复有 11 组正反用例；WorktreeRuleTextTests 改为断言 mandate 专属 token（`worktree-path`）而非泛在的 `worktree`；`validate_kit` 结构校验通过。 |
| 10 | security 安全 | verified | 关掉一个**旧 HIGH 绕过**：分类器先跑 `_catastrophic_delete` 再归一化换行，导致 `echo x\nrm -rf /`/`\nformat c:`/`\nRemove-Item -Recurse -Force` 与嵌套 `$()` 藏的破坏命令逃过（且 `feature_guard verify` 会执行被过滤命令）。现归一化提前 + 配对括号扫描，全部拦下（新测试固定）。其余守卫不变。 |
| 11 | authorization 授权 | verified | 未动 publish/sync 授权链。 |
| 12 | error-handling 错误处理 | partial | 同 v0.2.10：GuardError→`ERROR:`+exit 1、拒绝无 Traceback；`worktree_guard.py` 仍 fail-open（有意）。分类器覆盖面本版扩大但仍非完备 shell 解析（`bash -c` 包裹等由多层兜底）。 |
| 13 | performance 性能 | partial | 无受控基准；223 用例数分钟属单机噪声。`classify_command` 增加换行归一化 + 有界（depth≤4）子命令递归，量级不变。 |
| 14 | deployment 部署准备 | partial | 同 v0.2.10；**已知缺口（审查确认）**：v0.2.10/v0.2.11 只覆盖新建项目 + Cursor，已有项目无自动迁移路径——如实记入 ROADMAP/STATUS，延后到 v0.3 安装器。 |
| 15 | observability 可观测性 | verified | next_step/status/audit_project 自证；新行为均有测试可见。 |
| 16 | backup-recovery 备份与恢复 | partial | 同 v0.2.10。 |
| 17 | migration-rollback 迁移与回滚 | partial | 同 v0.2.10；已有项目迁移作为 v0.3 明确项。 |
| 18 | ux 用户体验 | verified | 修掉会误导维护 agent 删掉防线的文档矛盾，降低「防线被当违规删」的风险；文档过期项清理。 |
| 19 | ui 界面 | not-applicable | 无图形界面。 |
| 20 | user-acceptance 用户验收 | not-verified | 用户提出并确认「审查后修到最终版本」，明确授权自动定版；按定义仍需用户本人走查，代理不代签。 |
| 21 | ai-completion-audit AI 完成度审计 | verified | 无 TODO/stub/占位；新代码均有「改坏必红」守卫（换行删除、嵌套 `$()`、规则文本 mandate token）；DK-021 验证入口已补 `tests/test_worktree_guard_hooks.py`，孤儿测试问题关闭。 |

## 本次未修、已登记的发现

无 P0、无 P1。以下有意延后或作为已知限制：

- **已有项目迁移（维度 14/17，MED）**：hook/watcher-exclude/守卫只随新项目模板发；已有项目（含维护者自己的主项目）不会自动获得，且其已存在的工作区内 worktree 不会被清。这是审查点名的「真实世界仍会卡」主因，延后到 v0.3 安装器（update.ps1 -MigrateProjects + 批量 worktree 重定位）。
- **worktree_guard fail-open + `python`/`python3` PATH（维度 12/13，LOW）**：hook 解析异常或 `python` 不在 PATH 时放行，有意取舍；`bash -c "..."` 包裹类由 pre_tool_guard（Codex 侧）与散文规则兜底。
- **worktree_layout git-root vs opened-workspace-root（维度 08，LOW）**：Cursor hook 已按 `workspace_roots` 兜住父文件夹打开的情形，README 说明「打开仓库本身」。

## 静态门的固有上限

同前：本终审门只校验结构完整、版本匹配、状态合法与证据非空，不能证明证据本身真实。本版证据以本轮 223 用例全量 OK、`classify_command` 11 组正反实测、`validate_kit` 结构校验为基线。
