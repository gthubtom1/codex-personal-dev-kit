# 发布准备与 21 维终审

本流程默认只准备可供用户审查的发布材料。用户明确授权精确 Git 远程备份时，可使用 guarded publisher 推送当前分支和正式标签；这不等于创建 Release、部署或生产发布。

## 21 维发布终审

创建正式版本前，把逐维结论覆盖写入 `docs/RELEASE-REVIEW.md`（一版一份，覆盖更新；历史终审随版本标签保留在 Git 中）。首次创建该文件时把它加入 `docs/INDEX.md` 导航。guarded `version` 会拒绝：文件缺失、记录的版本与标签不一致、21 个维度缺行、状态非法或证据/原因为空。

状态只允许四种：`verified`（有证据已验证）、`partial`（部分验证）、`not-verified`（明确未验证）、`not-applicable`（不适用）。宁可如实标 `not-verified` 并写明原因，也不许把未验证伪造成 `verified`；证据列优先指向可复现来源——测试命令、feature guard verify 记录、文档章节或明确的人工验证步骤。

模板（`#`、维度键、状态词是机器校验的固定契约，不能改写；中文提示和证据列自由填写）：

```markdown
# Release Review

- Version: v1.2.0
- Result: <一句发布结论>

| # | Dimension | Status | Evidence / reason |
| --- | --- | --- | --- |
| 01 | requirements 需求 | not-verified | - |
| 02 | product-logic 产品逻辑 | not-verified | - |
| 03 | business-flow 业务流程 | not-verified | - |
| 04 | data-model 数据模型 | not-verified | - |
| 05 | data-integrity 数据完整性 | not-verified | - |
| 06 | state-machine 状态机 | not-verified | - |
| 07 | api-contract API 契约 | not-verified | - |
| 08 | architecture 架构 | not-verified | - |
| 09 | code-quality 代码质量 | not-verified | - |
| 10 | security 安全 | not-verified | - |
| 11 | authorization 授权 | not-verified | - |
| 12 | error-handling 错误处理 | not-verified | - |
| 13 | performance 性能 | not-verified | - |
| 14 | deployment 部署准备 | not-verified | - |
| 15 | observability 可观测性 | not-verified | - |
| 16 | backup-recovery 备份与恢复 | not-verified | - |
| 17 | migration-rollback 迁移与回滚 | not-verified | - |
| 18 | ux 用户体验 | not-verified | - |
| 19 | ui 界面 | not-verified | - |
| 20 | user-acceptance 用户验收 | not-verified | - |
| 21 | ai-completion-audit AI 完成度审计 | not-verified | - |
```

模板原样提交会被门禁拒绝（证据列为空）；每一行都必须真正评审后填写。逐维检查时对应参考：安全与授权见 `security.md`，迁移/回滚/备份见 `data-migrations.md`，质量与错误路径见 `quality-gates.md`，需求/验收对照 Goal 合同与 `docs/FEATURES.md`。

## 其余发布材料

- 配置、环境变量、密钥来源和功能开关有清单。
- 依赖和锁文件变化已审查。
- 用户可见变化、兼容性和已知限制有说明。
- 版本号、变更记录和发布说明已准备但未发布。

## 交付

输出：候选提交、终审结论、风险、回滚步骤和发布后检查。项目内的正式里程碑先通过 guarded `version` 建立本地标签；若用户明确授权目标远程、分支和标签，由 AI 通过 guarded `publish` 完成并验证远程备份。Release、deploy、包发布和生产迁移仍需独立授权与专用受控流程，不能把原始命令甩给零基础用户。
