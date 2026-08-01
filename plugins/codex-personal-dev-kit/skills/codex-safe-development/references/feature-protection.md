# 功能保全门禁

Git 负责恢复历史，不能判断某个旧功能是否被意外删掉。每次修改已有项目都要同时使用功能地图、当前变更契约、测试和最终 diff。

## 修改前

1. 从 `docs/FEATURES.md` 找到本次明确改变的功能 ID。
2. 沿入口、状态、API、持久化、后台任务和错误路径追踪完整链路，找出可能被连带影响的邻接功能。
3. 对未列入“明确改变”的 active 功能保持当前能力、入口链路、结果和状态。
4. 在第一次编辑前运行 bundled `scripts/feature_guard.py start`：

```text
python <plugin>/scripts/feature_guard.py start --root . --objective "<结果>" --change F-012 --verify F-014
```

- `--change` 可重复，表示本次允许改变并必须更新验证的功能。
- `--verify` 可重复，表示虽然不改变但处于相邻链路、必须回归的功能。
- 所有 active 且未声明改变的功能会自动成为受保护项。
- 删除已跟踪文件必须在开始时用 `--allow-delete` 声明，或在契约打开时用 `allow-delete` 补充；未声明删除会使完成检查失败。

## 修改后

1. 验证新验收条件、改变的功能、显式邻接功能，以及所有 critical 主流程。
2. 比较最终 diff，特别检查控件、路由、字段、配置、事件绑定、保存接口、worker 和测试是否被删除或断开。
3. 更新 `FEATURES.md` 的当前事实，不把任务日志写进去。
4. 运行：

```text
python <plugin>/scripts/feature_guard.py complete --root . --verified F-012 --verified F-014 --evidence "targeted tests: pass" --evidence "main UI flow: pass"
```

门禁会拒绝：受保护功能条目消失或被改写、变更功能没有成为 active、未声明的已跟踪文件删除、critical/指定功能未记录验证、没有任何验证证据。

`complete` 后若还需编辑，先运行 `reopen` 并在完成后重新验证。契约是 `.codex/current-change.json` 中的单个临时文件，Git 忽略它；新契约覆盖旧契约，不形成历史文档。
