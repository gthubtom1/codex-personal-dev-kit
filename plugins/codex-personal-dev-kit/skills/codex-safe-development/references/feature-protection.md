# 功能保全门禁

Git 负责恢复历史，不能判断某个旧功能是否被意外删掉。每次修改已有项目都要同时使用功能地图、当前变更契约、测试和最终 diff。

## 修改前

1. 聚合读取 `docs/FEATURES.md` 和 `docs/features/**/*.md`，找到本次明确改变的功能 ID；任何文件间重复 ID 都必须先修复。
2. 沿入口、状态、API、持久化、后台任务和错误路径追踪完整链路，找出可能被连带影响的邻接功能。
3. 对未列入“明确改变”的 active 功能保持当前能力、入口链路、结果和状态。
4. 在第一次编辑前运行 bundled `scripts/feature_guard.py start`：

```text
python <dev-kit-root>/scripts/feature_guard.py start --root . --objective "<结果>" --change F-012 --verify F-014
```

- `--change` 可重复，表示本次允许改变并必须更新验证的功能。
- `--verify` 可重复，表示虽然不改变但处于相邻链路、必须回归的功能。
- 所有 active 且未声明改变的功能会自动成为受保护项。
- 删除已跟踪文件必须在开始时用 `--allow-delete` 声明，或在契约打开时用 `allow-delete` 补充；未声明删除会使完成检查失败。
- 契约开始前已经修改或暂存的文件默认属于用户。只有任务确实负责该文件时才在 `start` 增加 `--own-path <file>`。
- 如果调查后确认原本只需回归的功能也必须改变，使用 `declare-change --change <ID>` 把它升级为本次明确改动；不要手工编辑 `.codex/current-change.json` 或绕过受保护记录。

## 修改后

1. 验证新验收条件、改变的功能、显式邻接功能，以及所有 critical 主流程。
2. 比较最终 diff，特别检查控件、路由、字段、配置、事件绑定、保存接口、worker 和测试是否被删除或断开。
3. 更新 FEATURES 主索引或对应领域表的当前事实，不把任务日志写进去。
4. 逐个暂存本任务文件；不要运行原始 `git add`：

```text
python <dev-kit-root>/scripts/feature_guard.py stage --root . --path src/export.ts --path tests/export.test.ts
```

5. 通过门禁实际运行每条验证命令，并把该命令覆盖的功能 ID 绑定到同一内容快照：

```text
python <dev-kit-root>/scripts/feature_guard.py verify --root . --feature F-012 --feature F-014 -- npm test -- --runInBand
```

命令必须以退出码 0 完成，且运行前后 Git index、未暂存和未跟踪内容指纹一致。安装依赖、发布、部署或 Git 变更不能伪装成验证命令。

6. 最后运行：

```text
python <dev-kit-root>/scripts/feature_guard.py complete --root .
```

门禁会拒绝：受保护功能条目消失或被改写、变更功能没有成为 active、未声明的已跟踪文件删除、用户原有脏文件混入暂存、任务改动未暂存、critical/指定功能没有成功命令、验证后内容或 index 改变。

`complete` 后若还需编辑，先运行 `reopen`，重新 `stage` 和 `verify`。完成后运行：

```text
python <dev-kit-root>/scripts/feature_guard.py checkpoint --root . --message "checkpoint: <outcome>"
```

该命令只保存 tree 与父提交都匹配验证快照的内容，并自动关闭契约。Stop Hook 会阻止已验证但尚未形成回退点的任务结束；新契约也不能覆盖这种未保存状态。SessionEnd 只清理已经形成匹配检查点的契约。

契约是 `.codex/current-change.json` 中的单个临时文件，Git 忽略它；新契约覆盖旧契约，不形成历史文档。
