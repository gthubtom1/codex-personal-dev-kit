# Release Review

- Version: v0.2.7
- Result: 通过。21 维全部评审完毕，无 P0、无 P1；10 维已验证、9 维部分验证、1 维不适用、1 维（用户验收）如实标记未验证，待用户本人走查。

评审基线：`89ea0dd`（工作区干净）。证据由三名独立只读采集者在该提交上实跑取得，未修改本仓任何文件。
全量套件 123 用例通过（零跳过、零失败），`validate_kit.py` 结构校验退出码 0，9 个 Skill 全部校验通过。

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | verified | `docs/FEATURES.md` 18 行 DK-001~DK-018 均带接线链路与验证入口；引用的 9 个测试文件与 `tests/` 实际文件双向零差（无悬空引用、无孤儿测试）；123 用例在 `89ea0dd` 实跑 OK |
| 02 | product-logic 产品逻辑 | partial | 可执行部分全落实：`next_step.py` 对真实仓库状态给出正确 NOW/NEXT，9 个 Skill 目录与 AGENTS 调度表逐项对应，路由由 `tests/test_orchestration_routing.py` 覆盖。未验证：从自然语言到 Skill 自动选中的真实链路无法在只读采集中触发，仅有测试断言 |
| 03 | business-flow 业务流程 | partial | 主流程 onboard→契约→暂存→验证→封契约→检查点→正式版本→恢复 在临时受管仓实跑闭合（含版本链三层闸逐级拒绝并各自点名下一步）；里程碑闭环可证：`docs/VERSIONS.md` 7 行与 7 个本地标签逐一对应，根 `VERSION` 与最新标签一致 |
| 04 | data-model 数据模型 | partial | 契约 JSON 字段全集已实测；`docs/VERSIONS.md` 行结构与本文件 21 个固定维度键均为机器校验契约；安装侧 `managed-files.json` 记录每个受管文件 SHA-256。扣分项 A-01：`verifiedWorktreeFingerprint` 是只写不读的死字段且名实不符（存的是内容指纹） |
| 05 | data-integrity 数据完整性 | verified | 验证与快照真绑定：`verify` 在命令前后各算一次暂存快照，期间索引或内容变化即判不通过；`complete` 要求内容指纹一致；`checkpoint` 在新提交与已验证快照不符时拒绝；契约失效时统一清空 verified* 键。`version` 另交叉校验 `package.json`、根 `VERSION` 与本文件版本行 |
| 06 | state-machine 状态机 | verified | 状态与迁移单一可读：无 Git→缺文档→无契约→open（未暂存/已暂存未验证/已记录验证）→verified→已检查点，另有 reopen/cancel/close/allow-delete/declare-change 支路；`next_step.py` 为唯一驱动点，真实仓只读实跑状态正确；`stage` 在非 open 态拒绝 |
| 07 | api-contract API 契约 | partial | `feature_guard.py --help` 自描述 20 个子命令且每条一句话契约，`next_step.py`/`validate_kit.py`/`audit_project.py` 各有明确入参。扣分项 A-02：`hook` 子命令 help 被设为 `==SUPPRESS==`，主入口存在一条不在 `--help` 里的隐藏命令面 |
| 08 | architecture 架构 | verified | `DESIGN.md` §4 八项内部能力 + 一个入口 == `skills/` 下 9 个目录，名称逐个对应；全仓无 `hooks.json`，与「不安装生命周期 Hook」边界一致；模板/脚本/Skills 分层与文档一致 |
| 09 | code-quality 代码质量 | verified | `python -m unittest discover -s tests -p 'test_*.py'` = Ran 123 tests OK（零跳过零失败）；`validate-kit.ps1` 退出码 0，9× "Skill is valid!" + 结构检查 + PowerShell 解析检查全过。守卫质量抽查：多处用真 bare remote/peer 仓做端到端验证而非 mock |
| 10 | security 安全 | verified | `shell=True` / `Invoke-Expression` / `eval(`|`exec(` 三轮全仓扫描零命中，外部调用一律 list 形式 argv；行为实测：路径逃逸（`../`、`C:/`、通配符、整仓路径）全部点名拒绝；植入假私钥块与云 token 后 `stage` 返回 "Refusing to stage likely credentials"，且索引树前后一致、用户文件保留 |
| 11 | authorization 授权 | verified | `publish`/`sync` 的 `--confirm-remote-url` 为 argparse required，服务侧再与实际 remote 逐字对照；publish 另要求干净已验证检查点、指向 HEAD 的标签、VERSIONS 行，并拒绝移动已存在的远程标签，dry-run + atomic 后回读校验；`install_global_tool.py` 要求 ID/版本/scope 三元精确复述并拒通配。单测覆盖确认串不符、分叉拒绝、远程标签冲突三种形态 |
| 12 | error-handling 错误处理 | partial | GuardError 全部落成 `ERROR: <一句话>` + 退出码 1，13 次行为探针零 Python 回溯；失败回滚实证：暂存命中密钥后还原索引且不删用户文件。partial 原因：`main()` 只捕获 GuardError，非 GuardError 异常仍会以 Python 回溯直达零基础用户；`install.ps1` 用裸 throw，错误面带 PowerShell 帧信息 |
| 13 | performance 性能 | partial | 本机实测：单测 123 用例 295.4s，完整 `validate-kit` 383.4s；验证器内部超时上限默认 900s，占用约 33%，余量充足。partial 原因：无历史基准可比、单机单次、未做慢机/冷缓存对照，不足以判定趋势 |
| 14 | deployment 部署准备 | partial | 本套件按零基础安全边界**有意不做**真实部署，仓内零部署资产。`install.ps1` 结构齐备：默认 preview 不写入，覆盖/删除前备份到 `$CODEX_HOME\backups\codex-dev-kit\<timestamp>`，重复安装幂等早退，旧状态未加 `-MigrateLegacy` 直接报错。partial 原因：沙箱 preview 被 Codex CLI 前置条件挡住（退出码 1 且沙箱内零写入），备份与幂等分支仍是读码结论 |
| 15 | observability 可观测性 | verified | 状态自证三件套实跑：`next_step.py` 按四种状态打印可直接粘贴的下一条命令；`feature_guard status` 与 `--json` 均可用；`audit_project.py` 在探针仓真报出 P1 与 4 条 P2。已知不一致见 F-15-01（同一阻塞态三条命令给三种理由） |
| 16 | backup-recovery 备份与恢复 | partial | 安全属性行为实证：`rollback` 拒绝回退非 Dev Kit 检查点流程创建的提交；有未保存工作时拒绝并点名文件，实测该文件原封不动存活；安装器备份路径结构齐备。partial 原因：一次「成功的 rollback」未能在探针中触达（需先有真守卫检查点，而 `verify` 拒绝空操作命令），该属性目前只有单测证据 |
| 17 | migration-rollback 迁移与回滚 | partial | 正式版本门行为实证：`version` 对未验证检查点、非法版本名、未结契约三种情况分别拒绝并点名下一步；`restore-version` 对不存在版本给可操作提示；代码侧失败走 `read-tree --reset -u` 与 `revert --abort` 回滚。partial 原因：`-MigrateLegacy` 旧系统迁移与一次成功的 `restore-version` 均未实际执行，仅读码与单测 |
| 18 | ux 用户体验 | verified | 面向零基础的关键属性成立：每次拒绝都是一句完整人话 + 点名具体对象 + 给出下一步动作，且从不销毁用户内容（实测用户草稿文件存活）；`next_step.py` 把下一步直接打印成可粘贴命令行，不依赖散文记忆；13+ 次探针零 Python 回溯 |
| 19 | ui 界面 | not-applicable | 本产品无图形界面，交付面是 CLI 文本 + Markdown 文档 + Skills，不存在可评的 UI 层；文本呈现质量已并入维度 18 评估 |
| 20 | user-acceptance 用户验收 | not-verified | 按定义必须由用户本人按真实流程走一遍并口头验收，代理不能代替，也不得由其他维度的绿色推导为通过。当前无任何用户验收记录。建议验收动作：在一个真实项目上跑 `next_step.py` 看是否说得清下一步，并完整走一次「改代码→验证→检查点」 |
| 21 | ai-completion-audit AI 完成度审计 | verified | 四类残留全扫干净：TODO/FIXME/XXX/HACK/stub/NotImplementedError 零真命中；恒真假守卫（`assertTrue(True)` 等）零命中；文档写到的 15 个子命令全部存在、零漂移；`.gitignore` 未吞任何应交付物。正向证据：`verify` 主动拒绝空操作验证命令（"Feature-bound verification cannot be an inline/no-op command"），是防「假验证」的主动防线 |

## 本次未修、已登记的发现

无 P0、无 P1。以下按严重度记账，留待后续切片处理：

- **F-15-01（P2，维度 15/18）**：同一被阻塞状态下三条命令给出三种不同理由，而被指定为「不确定下一步就问它」的 `next_step.py` 给的那条不完整——它只看验证记录是否为空，从不提 `docs/STATUS.md` 未更新这道要求，照它走的人会反复重跑 `verify`。
- **A-01（P3，维度 04）**：`verifiedWorktreeFingerprint` 是只写不读的死字段，且名字承诺工作树指纹、实际存内容指纹。
- **A-02（P3，维度 07）**：`hook` 子命令在 `--help` 中被 `==SUPPRESS==` 隐藏，公开契约不完全自描述。
- **F-21-01（P3，维度 21）**：`cancel`、`close` 两个已实现子命令在全部文档与 Skills 中零提及，按 Skills 驱动的 AI 永远不会调用它们。
- **F-21-02（P3，维度 21）**：`artifacts/` 与 `.agents/plugins/` 是无内容无说明的空目录。

## 静态门的固有上限

本终审门只校验结构完整、版本匹配、状态合法与证据非空，**不能证明证据本身真实**。本次三段证据由三名独立采集者分别实跑并各自留下可复跑命令，`audit-codex-kit` 可按「结论强度不得高于证据」抽查复现。
