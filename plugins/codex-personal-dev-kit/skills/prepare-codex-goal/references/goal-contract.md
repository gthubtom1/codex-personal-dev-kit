# Goal 合同模板

```markdown
# Goal: <一个结果导向的标题>

## Outcome
<完成后用户能看到或验证的结果>

## Context
<相关项目、模块、现状和已知事实>

## In scope
- <本次必须完成>

## Out of scope
- <明确不做，防止范围漂移>

## Constraints
- <兼容、安全、架构、时间或工具边界>

## Existing behavior protection
- Intentionally changed feature IDs: <F-... or none>
- Adjacent/critical feature IDs to recheck: <F-...>
- Existing behavior that must remain: <short observable list>

## Acceptance
- [ ] <可观察的验收条件>

## Verification
- <命令、测试、截图、数据检查或人工步骤>

## Permissions
- Auto: <允许自动执行>
- Ask first: <遇到即暂停>
- Never automatic: <只由用户手动执行>

## Checkpoints
- <何时创建本地提交或状态快照>

## Stop conditions
- <缺少信息、连续失败或风险升级时停止的条件>
```

## 质量检查

- Outcome 描述结果，不写成“研究一下”或“尽量优化”。
- 验收条件能判断真或假。
- 非目标足以阻止常见范围扩张。
- 验证覆盖最重要行为和回归风险。
- 已有项目明确区分本次改变的功能和必须保留、复核的旧功能。
- 权限矩阵与当前 sandbox、approval 和用户要求一致。
- Goal 不超过 4000 字符；详细计划放在项目文件中。
