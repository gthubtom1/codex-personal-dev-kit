---
name: manage-project-continuity
description: 在 Codex 长期项目的任务开始、上下文变长、对话切换、Goal 暂停或工作结束时恢复最小上下文、更新精炼状态、创建交接并控制文档膨胀。用户担心长对话降质、新对话不了解历史、文档无限增长，或要求继续上次工作和整理下一步时使用。
---

# Manage Project Continuity

让新任务依靠代码、测试、Git 和小型当前状态快速恢复，而不是读取旧聊天全文。

## 开始任务

1. 始终读取适用的 `AGENTS.md`、`docs/PROJECT.md`、`docs/FEATURES.md` 和 `docs/STATUS.md`；只在本任务相关时读取架构、ADR、路线图或运行手册。若 `.codex/current-change.json` 存在，先恢复其中的目标、允许改变的功能和待验证项，不另起冲突任务。
2. 查看 `git status -sb`、当前分支、最近少量提交和必要的 Worktree 信息。
3. 从这些事实重建当前 Goal、已验证状态、风险和下一步。记忆和旧聊天只能帮助召回，不能替代项目事实。
4. 读取 [context-and-task-boundaries.md](references/context-and-task-boundaries.md)，判断应继续当前任务、压缩当前对话，还是为新成果开启新任务。
5. 复杂任务可以使用一个 Git 忽略的 `.codex/active-plan.md` 保存尚未完成的执行步骤；它只属于当前任务，完成后删除，不保留版本历史。

## 结束任务

1. 运行最终验证并审查 diff；已有项目必须先完成当前 change guard，验证后又有改动时重新打开并复核。
2. 在允许且有独立成果、change guard 已通过时创建本地检查点提交。
3. 按 [document-lifecycle.md](references/document-lifecycle.md) 覆盖更新当前状态：
   - `STATUS.md` 只保留当前里程碑、验证、问题和下一步。
   - `ROADMAP.md` 只保留当前及接下来 2 到 3 个里程碑。
   - `ARCHITECTURE.md` 只在真实边界或数据流改变时更新。
   - 重大且难逆转的决定写入单独 ADR。
   - `FEATURES.md` 或 `ARCHITECTURE.md` 变大时保留主索引，并按稳定业务领域拆分。
4. 不复制聊天全文、完整 diff、原始日志或每日流水账。历史由 Git 保存。
5. 删除已完成任务的 `.codex/active-plan.md`，不创建 `plan-v2`、会话报告或永久 checkpoint 文档。
6. 使用 [handoff-template.md](references/handoff-template.md) 输出下一任务可直接使用的交接提示。

## 任务边界

- 同一问题仍在推进时保留当前任务；日志或历史过多时可压缩。
- 目标、分支、交付物或主要模块改变时开启新任务。
- 独立结果并行时使用多个任务；当前结果内部的短期调查使用子代理。
- 一个任务结束后归档，不把整个长期项目永久放在一个任务里。

## 文档限流

任何文档接近预算时，先删除过期快照和重复内容，再按领域拆分。不要通过不断追加来保存“记忆”。

## 输出

给出当前事实、分支和提交、验证、剩余风险、更新过的文档，以及一段短小、可直接用于新任务的下一步提示。
