# Release Review

- Version: v0.2.8
- Result: 通过。21 维复审完毕，无 P0、无 P1；证据以本次基线 a473463 上的两次独立全量实跑（葛雪绯、濮儒慎）+ 独立变异复审 + 总指挥门禁实跑为准。v0.2.7 登记的 5 条发现已关闭 4 条，剩 1 条 P3（两个空目录，无害）；用户验收维如实标未验证（用户已明确授权自动定版并推 GitHub，但未本人走查）。

评审基线：`a473463`（工作区干净，20 commits ahead of origin/main）。相较 v0.2.7（`89ea0dd`）新增四道机器门 DK-019~DK-022（快照救命网 / 大文件审计 / 并行副本放置 / 写入锁）、一条「读本仓自身功能表」的守卫，以及从 exe-product-lifecycle 复审吸收的四条防御性守卫（技能清单防漂移、validate_kit 覆盖率记账、PowerShell 保留变量 lint、拒绝不泄漏 traceback）。
全量套件在 a473463 上两次独立实跑均 `Ran 211 tests OK`（葛雪绯 429s、濮儒慎 386s 并发环境）；`audit_project.py` 无发现、22 个特性全 active、文档零断链；`validate_kit.py` 结构校验退出码 0。

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | verified | `docs/FEATURES.md` 22 行 DK-001~DK-022 均带接线链路与验证入口；引用测试文件与 `tests/` 实际文件对应；211 用例在 a473463 两次独立实跑 OK（葛雪绯、濮儒慎）。较 v0.2.7 新增 DK-019~DK-022 四项能力 |
| 02 | product-logic 产品逻辑 | partial | 可执行部分全落实：`next_step.py` 对真实仓库状态给 NOW/NEXT，Skill 目录与 AGENTS 调度表对应，路由由测试覆盖。未验证：自然语言到 Skill 自动选中的真实链路无法在只读采集中触发，仅测试断言 |
| 03 | business-flow 业务流程 | verified | 主流程 onboard→契约→暂存→验证→封契约→检查点→正式版本→恢复 闭合；新增写入锁（DK-022）在契约全程强制单写入者，含取锁/续锁/死持有者回收/force-unlock，`tests/test_write_lock.py` 变异验证（濮儒慎独立复现取锁拿掉→14 红）；版本链三层闸逐级拒绝 |
| 04 | data-model 数据模型 | verified | 契约 JSON 字段全集已测；`managed-files.json` 记录每个受管文件 SHA-256。v0.2.7 扣分项 A-01（`verifiedWorktreeFingerprint` 死字段）已关闭——a473463 上该标识符 0 处 |
| 05 | data-integrity 数据完整性 | verified | `verify` 命令前后各算暂存快照，索引或内容变化即判不通过；`complete` 要求内容指纹一致；`checkpoint` 拒绝与已验证快照不符的新提交。新增 index-safe 工作树快照救命网（DK-019）在不惊动索引的前提下保全在途改动（本轮实战救过一次）；写入锁防并发写入损坏契约 |
| 06 | state-machine 状态机 | verified | 状态与迁移单一可读；写入锁新增 acquire/renew/reclaim(死持有者)/force-unlock 支路；`next_step.py` 为唯一驱动点，真实仓只读实跑状态正确；`stage` 在非 open 态拒绝 |
| 07 | api-contract API 契约 | verified | `feature_guard.py --help` 自描述子命令且每条一句话契约；v0.2.7 扣分项 A-02（`hook` 子命令 help 被 `==SUPPRESS==` 隐藏）已关闭——a473463 上 SUPPRESS 0 处；写入锁/快照/worktree-path 等新命令均在 `--help` 中 |
| 08 | architecture 架构 | verified | `DESIGN.md` 内部能力与 `skills/` 目录逐一对应；全仓无 `hooks.json`；新能力落成独立模块（`workspace_snapshot.py`、`worktree_layout.py`），共享守卫只增子命令接线 |
| 09 | code-quality 代码质量 | verified | `python -m unittest discover -s tests -p test_*.py` = Ran 211 tests OK，在 a473463 上由葛雪绯与濮儒慎两次独立实跑；`validate-kit` 结构+PowerShell 解析+9 Skill 校验通过。四条 exe 复审守卫与写锁套件均「改坏→红→还原→绿」变异验证，且由濮儒慎独立复现全部四条；validate_kit 现记账 COVERAGE/aborted-in（验证器自身崩溃不再被当成通过），套件现读本仓真实 FEATURES.md（重号无法蒙混过绿） |
| 10 | security 安全 | verified | `shell=True`/`Invoke-Expression`/`eval(`/`exec(` 全仓扫描零命中，外部调用一律 list argv；路径逃逸全部点名拒绝；植入假密钥后 `stage` 拒绝且索引前后一致。新增 PowerShell 保留自动变量赋值 lint，防 `$pid=` 类静默 shadow（濮儒慎独立复现 fixture→红、改名→绿） |
| 11 | authorization 授权 | verified | `publish`/`sync` 的 `--confirm-remote-url` 为 required 且服务侧与实际 remote 逐字对照；publish 要求干净已验证检查点、指向 HEAD 的标签、VERSIONS 行，拒绝移动已存在远程标签，dry-run+atomic 后回读校验。单测覆盖确认串不符、分叉、远程标签冲突三形态。本次正式版本的远程备份将走 guarded publish |
| 12 | error-handling 错误处理 | partial | GuardError 全部落成 `ERROR: <一句话>`+退出码 1；新增 `tests/test_guard_refusals_are_clean.py` 对 9 个确定性拒绝断言零 Traceback（濮儒慎独立复现：把 main() 的 except 改 raise→9 条全红并泄漏 Traceback，还原→绿）。partial 原因：`main()` 仍只稳妥处理 GuardError，非 GuardError 异常与 `install.ps1` 裸 throw 仍可能带栈信息，本轮 A4 实跑未复现真实泄漏、作回归守卫保留 |
| 13 | performance 性能 | partial | 211 用例实测多次：429s（葛雪绯）、386s（濮儒慎，并发环境）、以及本机早前 537s/637s；跨度主要来自单机多会话并发抢占。partial 原因：无历史基准、单机多次、未做慢机/冷缓存对照，不足以判定趋势（早前「变慢」判断已被同批同机 100s 波动推翻） |
| 14 | deployment 部署准备 | partial | 本套件按零基础安全边界有意不做真实部署，仓内零部署资产；`install.ps1` 默认 preview 不写入、覆盖前备份、重复安装幂等。partial 原因：装机侧当前落后源码（诊断显示装机运行时钉在 8cc7518、源码在 a473463），正式版本落地后需重装运行时使其生效——属装机态、非源码产物缺陷 |
| 15 | observability 可观测性 | verified | `next_step.py`/`feature_guard status`/`audit_project.py` 状态自证；a473463 上 `audit_project` 报「No audit findings」、22 特性、零断链。v0.2.7 F-15-01（next_step 对 STATUS 盲区）已关闭——`completion_blockers` 已进 `next_step.py`；新增 validate_kit COVERAGE 记账 |
| 16 | backup-recovery 备份与恢复 | partial | `rollback` 拒绝回退非 Dev Kit 检查点流程创建的提交、有未保存工作时点名拒绝且文件存活；新增 index-safe 快照救命网（DK-019）经本轮实战验证可无损保全散落在途改动。partial 原因：一次「成功的 restore-version」仍只有单测/单次证据 |
| 17 | migration-rollback 迁移与回滚 | partial | 正式版本门对未验证检查点、非法版本名、未结契约分别点名拒绝；`restore-version` 对不存在版本给可操作提示。partial 原因：`-MigrateLegacy` 与一次成功 `restore-version` 未实际执行，仅读码与单测 |
| 18 | ux 用户体验 | verified | 每次拒绝一句人话+点名对象+给下一步，从不销毁用户内容；`next_step.py` 打印可粘贴的下一条命令；新增 A4 守卫钉死拒绝态不甩 Python 回溯给零基础用户 |
| 19 | ui 界面 | not-applicable | 无图形界面，交付面是 CLI 文本+Markdown+Skills；文本呈现质量并入维度 18 |
| 20 | user-acceptance 用户验收 | not-verified | 用户已明确授权本轮自动定版并推 GitHub（原话「不需要问我」），全程指挥了 exe 复审并审阅了四条守卫 diff；但按定义仍需用户本人按真实流程走查一遍，代理不能代签，故如实标未验证。建议验收动作：在真实项目上跑一次 `next_step.py` 并完整走一遍「改代码→验证→检查点」 |
| 21 | ai-completion-audit AI 完成度审计 | verified | TODO/FIXME/stub/NotImplementedError 零真命中；恒真假守卫零命中（濮儒慎独立确认四条新守卫的负控在干净树上皆绿、非恒红）；文档所述子命令零漂移。v0.2.7 F-21-01（cancel/close 文档零提及）已关闭——现 13 处提及。正向证据：套件新增「读本仓真实功能表」的守卫，主动拦截重号蒙混过绿 |

## 本次未修、已登记的发现

无 P0、无 P1。

- **F-21-02（P3，维度 21）**：`artifacts/` 与 `.agents/plugins/` 仍是无内容空目录（a473463 上二者仍存在）。无害，留待后续切片。
- **新增 A-03（P3，维度 09，独立复审 濮儒慎 提出，非阻塞）**：`validate_kit._check_unit_tests` 在验证器被调用时会跑一次嵌套 discover；当前无任何测试调用真实验证器，故不会递归，属既有设计的潜在脚枪，与本次四条守卫无关，不阻塞发布。

## v0.2.7 → v0.2.8 已关闭的发现（本次在 a473463 上复核）

- F-15-01（next_step 对 STATUS 盲区）→ 关闭：`next_step.py` 已含 `completion_blockers`。
- A-01（`verifiedWorktreeFingerprint` 死字段）→ 关闭：源码 0 处。
- A-02（`hook` 子命令 `==SUPPRESS==` 隐藏）→ 关闭：源码 SUPPRESS 0 处。
- F-21-01（`cancel`/`close` 文档零提及）→ 关闭：文档/Skills 13 处提及。

## 静态门的固有上限

本终审门只校验结构完整、版本匹配、状态合法与证据非空，**不能证明证据本身真实**。本次证据由两名成员（葛雪绯实现方全量、濮儒慎独立复审含亲手变异四条守卫）在 a473463 上分别实跑，加总指挥独立跑 `audit_project`/`diagnose`/四条守卫单测（25 绿）取得，可按「结论强度不得高于证据」抽查复现。
