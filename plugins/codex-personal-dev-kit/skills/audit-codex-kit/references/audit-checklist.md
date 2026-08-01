# 审计检查表

## 快速项目审计

- 根目录和 Git 仓库边界是否清楚。
- 工作树是否长期脏、是否有未跟踪重要文件或未保存成果。
- 当前分支、远程跟踪和 Worktree 是否可解释。
- `AGENTS.md`、PROJECT、FEATURES、STATUS、ROADMAP、ARCHITECTURE 是否存在且当前。
- FEATURES 是否使用稳定 ID，并记录 active 功能的完整接线链路、验证入口、重要性和状态。
- `.codex/current-change.json` 和 `.codex/active-plan.md` 是否被 Git 忽略；残留 open 契约或过期临时计划是否需要恢复或清理。
- 启动、测试、lint、类型和构建命令是否可复现。
- 是否有职责混杂、难以局部验证的复杂度热点、循环依赖或跨层访问；不要只按行数判定。
- 清单与锁文件是否一致，是否出现多个包管理器。
- `.env`、密钥、数据库副本和用户数据是否被跟踪。
- 高风险模块是否缺少测试、迁移或回滚说明。
- STATUS 是否有一个具体下一步；FEATURES/ARCHITECTURE 是否需要按领域拆分并保留主索引。
- 是否存在超大的开发/聊天日志、累计计划版本，或缺少索引和替代状态的 ADR 集合。

## Dev Kit 审计

- Marketplace、manifest 和七个 Skill（一个入口、六个内部能力）通过官方 validator。
- Skill 描述覆盖真实触发语句，正文无占位符且 references 都可达。
- `agents/openai.yaml` 的默认提示包含正确 `$skill-name`。
- Hook 对危险命令阻止、对常见安全命令放行，并覆盖无契约编辑、未验证提交、压缩恢复和未完成 Stop。
- Rules 有 match/not_match 样例并通过 execpolicy 检查。
- Bootstrap 预览不写入，重复 Apply 幂等且覆盖前有备份。
- 项目模板没有无限追加式文档。
- 新项目、旧项目、复杂度热点、长任务和危险命令场景有测试。
- Git 仓库只有本地检查点，没有自动 push 或发布。

## 严重度

- P0：正在发生或极易造成数据丢失、安全事故、生产破坏。
- P1：高概率错误、权限绕过、不可回滚变更或严重测试缺口。
- P2：架构、维护、文档、依赖或流程风险。
- P3：低风险改进、清理或效率建议。
