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

1. 验证新验收条件、改变的功能、显式邻接功能，以及源码/配置/数据结构变化影响到的所有 active 功能；不要因为功能标记为 standard 就静默跳过。
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

门禁会拒绝：受保护功能条目消失或被改写、变更功能没有成为 active、未声明的已跟踪文件删除、用户原有脏文件混入暂存、任务改动未暂存、active/指定功能没有成功命令、验证后内容或 index 改变。大型功能目录可以用共享 `suite:all-tests` 标记或多个真实命令分批覆盖，但不能只验证 critical 功能。

`complete` 后若还需编辑，先运行 `reopen`，重新 `stage` 和 `verify`。完成后运行：

```text
python <dev-kit-root>/scripts/feature_guard.py checkpoint --root . --message "checkpoint: <outcome>"
```

该命令只保存 tree 与父提交都匹配验证快照的内容，并自动关闭契约。安全开发 Skill 在没有匹配回退点时不得声明任务完成；新契约也不能覆盖这种未保存状态。任务结束或开启新任务时，只清理已经形成匹配检查点的契约。

如果该检查点是用户接受的正式里程碑，必须先在同一验证快照中完成 21 维发布终审（覆盖写入 `docs/RELEASE-REVIEW.md`，见 release-readiness 参考）并更新 `docs/VERSIONS.md` 和已有版本字段；检查点完成后再运行 `feature_guard.py version --root . --name vX.Y.Z`。普通检查点不创建版本标签。

## 放弃或收尾契约

`checkpoint` 成功后会自动删除契约，正常流程不需要手工清理。只有下面两种情况需要显式命令，任何时候都不要手工删除 `.codex/current-change.json`。

契约开错了、目标变了，或本次不再修改任何文件时用 `cancel`：

```text
python <dev-kit-root>/scripts/feature_guard.py cancel --root .
```

仓库内容与契约基线仍有差异时它会拒绝，因此不会丢弃已完成的工作。最常见的场景是先改了文件才发现没开契约：`start` 时漏掉 `--own-path`，`stage` 就会拒绝这些路径，而契约已存在又不能重开——此时先 `cancel`，再带上每个 `--own-path <file>` 重新 `start`。

契约已经 `complete`、验证快照也已经有检查点，但契约文件还留着时用 `close`：

```text
python <dev-kit-root>/scripts/feature_guard.py close --root .
```

契约还没验证、验证后内容又变了、或验证快照还没有检查点时它都会拒绝。两个命令都只删除契约文件，不修改工作区内容，也不删除任何提交。

契约是 `.codex/current-change.json` 中的单个临时文件，Git 忽略它；新契约覆盖旧契约，不形成历史文档。

## 一份 checkout 只有一个写入者（强制，不是约定）

`start` 会为当前 checkout 取一把排他写锁 `.codex/write-lock.json`，此后所有会修改契约或仓库的命令（`stage`、`verify`、`declare-change`、`allow-delete`、`unstage`、`reopen`、`complete`、`checkpoint`、`rollback`、`cancel`、`close`）都要求持锁。**取不到锁是硬失败（退出码 1），没有"警告一声然后放行"这种模式。** 只读命令（`status`、`versions`、`lock-status`）永远不需要锁。

被拒绝时错误信息会说明持锁者是谁、持了多久、在做什么：

```text
python <dev-kit-root>/scripts/feature_guard.py lock-status --root .
```

锁按 **checkout** 划分，不是按仓库。因此独立 Worktree 并行开发不受影响——那本来就是合法的并行方式，各自有各自的锁。

持锁者是**写入会话**，不是执行命令的那个短命进程（每条 guard 命令都是新进程，若按进程标识锁，下一条命令就会把自己的锁回收掉，等于没锁）。会话身份优先取环境变量 `CODEX_WRITE_LOCK_SESSION`，没有则退回到父进程（会话的 shell）。**如果你的工具链为每条命令新开一个 shell，请为每个会话设置一个稳定的 `CODEX_WRITE_LOCK_SESSION`**，否则同一个会话会被当成不同写入者。

会话崩溃不会把仓库永久锁死：持锁进程已经消失时，下一个写入者会自动接管；长时间无人续期的锁也会过期。确认对方确实已经消失、但自动回收没生效（例如持锁者在另一台机器上）时，才用显式的破锁命令，它必须点名当前持锁者，且对方进程仍在运行时会拒绝：

```text
python <dev-kit-root>/scripts/feature_guard.py force-unlock --root . --confirm-holder <pid>
```
