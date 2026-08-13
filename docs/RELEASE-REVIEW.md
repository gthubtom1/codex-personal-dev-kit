# Release Review

- Version: v0.2.9
- Result: 通过。相对 v0.2.8 是**纯文档增量**（跨宿主采用去打折：把 AGENTS/README/Skill 里的 Codex 宿主专属内容标注为「宿主相关」，并在 README 增加逐节映射表），未改任何门禁/测试/运行时代码。21 维在 v0.2.8 的评审基础上顺延（代码逐字未变），本次仅复核受影响的文档维度；无 P0、无 P1；用户验收维如实标未验证（用户已明确授权自动定版并推 GitHub，但未本人走查）。

评审基线：代码检查点 `a7f2087`（跨宿主标注 + README 逐节映射表；工作区干净），发布检查点在其上追加本终审 + VERSIONS 行 + VERSION=0.2.9。相对 v0.2.8（`4ddf8ce`）的唯一差异是 7 个文档文件的新增标注 + README 映射表 + STATUS 记账，`git diff` 不含任何 .py/.ps1 逻辑改动。
全量套件在本轮由 濮儒慎 经 guard verify 实跑 `Ran 211 tests OK`（exit 0，绑定 DK-007/DK-009）；`validate_kit.py` 结构校验 COVERAGE 8/8、0 error（确认四个必需标题、四个可移植 token 仍在、workspace-template 无硬编码路径）；总指挥另行核实标注未破坏固定标题/token、硬编码路径 0 处。

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | verified | 特性集与 v0.2.8 一致：`docs/FEATURES.md` 22 行 DK-001~DK-022，本版纯文档、未增删特性；211 用例实跑 OK（濮儒慎，绑定 DK-007/DK-009）。 |
| 02 | product-logic 产品逻辑 | partial | 可执行部分同 v0.2.8。本版新增跨宿主可采用性：非 Codex 宿主（Cursor/Claude）拿到 README 逐节映射表即可把 Codex 专属项翻译成本宿主做法。未验证：NL→Skill 自动选中仍无法只读触发；Claude 宿主端到端未实测。 |
| 03 | business-flow 业务流程 | verified | 契约生命周期同 v0.2.8（含写入锁强制单写入者）；本版发布检查点自身即经 start→stage→verify→complete→checkpoint 闭合验证。 |
| 04 | data-model 数据模型 | verified | 同 v0.2.8：契约 JSON 字段全测、managed-files SHA-256；A-01 死字段仍为 0。本版未动数据模型。 |
| 05 | data-integrity 数据完整性 | verified | 同 v0.2.8：verify 前后暂存快照绑定、complete/checkpoint 拒绝不符树；写入锁防并发；本版未动。 |
| 06 | state-machine 状态机 | verified | 同 v0.2.8：状态与迁移单一可读、写入锁支路齐全、next_step 唯一驱动；本版未动。 |
| 07 | api-contract API 契约 | verified | 同 v0.2.8：feature_guard --help 自描述、A-02 隐藏子命令仍为 0；本版未增删子命令。 |
| 08 | architecture 架构 | verified | DESIGN↔skills 对应不变；本版新增「跨宿主适配」文档层：AGENTS/README/1 个 SKILL 的 Codex 专属处标为宿主相关，核心方法论(§1/2/3/5/6/7/10/11)与 Codex 专属(§4/§9/§12)清楚分层，README 逐节映射表覆盖 $skill/spawn_agent/openai.yaml/.system+resolve-skill/CODEX_HOME/§12/桌面措辞/winget+门禁 8 条。 |
| 09 | code-quality 代码质量 | verified | `python -m unittest discover -s tests -p test_*.py` = Ran 211 tests OK（濮儒慎，与 v0.2.8 同数，纯文档未加测试）；`validate_kit` COVERAGE 8/8、0 error（用的正是 v0.2.8 落地的覆盖率记账）；标注为纯新增，未删固定标题/token、硬编码路径 0（总指挥复核）。 |
| 10 | security 安全 | verified | 同 v0.2.8：注入类扫描零命中、路径逃逸拒绝、凭证暂存拒绝、PowerShell 保留变量 lint；本版未动代码。 |
| 11 | authorization 授权 | verified | 同 v0.2.8：publish/sync 远程确认串逐字对照、dry-run+atomic+回读；本次 v0.2.9 远程备份仍走 guarded publish。 |
| 12 | error-handling 错误处理 | partial | 同 v0.2.8：GuardError→ERROR:+exit 1、A4 拒绝无 Traceback 守卫在；partial 原因同前（非 GuardError 路径与 install.ps1 裸 throw 未全覆盖）。本版未动代码。 |
| 13 | performance 性能 | partial | 同 v0.2.8：211 用例多次实测 379~429s，跨度为单机并发噪声，无受控基准；本版纯文档、性能面无变化。 |
| 14 | deployment 部署准备 | partial | 同 v0.2.8：有意不做真实部署、install.ps1 preview/备份/幂等；装机侧仍需在正式版本后重装运行时生效（本机态，非源码缺陷）。 |
| 15 | observability 可观测性 | verified | 同 v0.2.8：next_step/status/audit_project 自证；a7f2087 上 audit_project「No audit findings」、validate_kit COVERAGE 8/8；F-15-01 已关闭。 |
| 16 | backup-recovery 备份与恢复 | partial | 同 v0.2.8：rollback 安全属性 + 快照救命网；partial 原因同前（一次成功 restore-version 仍单测证据）。 |
| 17 | migration-rollback 迁移与回滚 | partial | 同 v0.2.8：正式版本门三态拒绝、restore-version 提示；partial 原因同前。 |
| 18 | ux 用户体验 | verified | 同 v0.2.8 的零基础拒绝体验；本版进一步提升跨宿主可读性：非 Codex 宿主一眼看清哪些是 Codex 专属、去 README 映射表翻译，不再被死内容误导。 |
| 19 | ui 界面 | not-applicable | 无图形界面，交付面为 CLI 文本 + Markdown + Skills；文本质量并入维度 18。 |
| 20 | user-acceptance 用户验收 | not-verified | 用户明确授权本轮自动定版并推 GitHub，且亲自提出并确认了「跨宿主去打折」需求；但按定义仍需用户本人走查，代理不能代签，故如实标未验证。 |
| 21 | ai-completion-audit AI 完成度审计 | verified | 同 v0.2.8：TODO/stub/恒真假守卫零命中、文档子命令零漂移；本版标注为纯新增文本、未引入占位符或死代码；F-21-01 仍关闭（cancel/close 有文档）。 |

## 本次未修、已登记的发现

无 P0、无 P1。均自 v0.2.8 顺延，本纯文档版未新增缺陷：

- **F-21-02（P3，维度 21）**：`artifacts/` 与 `.agents/plugins/` 空目录，无害。
- **A-03（P3，维度 09）**：`validate_kit._check_unit_tests` 嵌套 discover 脚枪，当前不触发。
- **文案瑕疵（非文件内容）**：a7f2087 检查点提交信息里的 `$skill` 被 PowerShell 变量展开吞成空；README 表格与 §4 标注的文件内容均正确，属无害提交信息瑕疵，未改写历史。

## 静态门的固有上限

同 v0.2.8：本终审门只校验结构完整、版本匹配、状态合法与证据非空，不能证明证据本身真实。本版为纯文档增量，代码与测试逐字未变，证据以 v0.2.8 的两次独立全量 + C 的独立变异复审为基线，叠加本轮 濮儒慎 的 211 OK 全量、validate_kit 8/8，与总指挥对标注未破坏固定标题/token 的复核。
