# 工作区快照救命网

`plugins/codex-personal-dev-kit/scripts/workspace_snapshot.py` 把当前工作区存成一个可恢复的 Git 提交对象，挂在 `refs/codex-wip/` 下面。它解决的是一种具体事故：**刚才还在改的东西没了**——被覆盖、被误删、被别人的 `git add .` 卷走。

## 它不是什么

先说这个，因为把它当成别的东西用会真的丢数据。

- **它不是备份。** 它只存在于这一个本地仓库里，硬盘坏了它一起没。远程备份走 `feature_guard.py publish`。
- **它不是正式检查点。** 检查点是「这一版验证过、可以回到」；快照是「刚才那一下还没来得及验证」。正式恢复点仍然走 `feature_guard.py checkpoint`。
- **它不会自动跑。** 本工具只提供可调用的命令，不装后台守护进程、不挂 Hook。要定时拍，由调用方自己决定何时调。

## 三条命令

```powershell
# 拍一张（工作区没有改动时什么也不做）
python plugins\codex-personal-dev-kit\scripts\workspace_snapshot.py snapshot --label <来源>

# 看有哪些，最新的在最上面
python plugins\codex-personal-dev-kit\scripts\workspace_snapshot.py list

# 取回来：写进一个空目录，绝不写回工作区
python plugins\codex-personal-dev-kit\scripts\workspace_snapshot.py restore --name <引用名> --into <空目录>
```

恢复是**只写到你指定的空目录**，然后由你自己挑要哪几个文件复制回去。它不会替你覆盖工作区，也不会动暂存区——正因为出事时你往往分不清「现在这份」和「快照那份」哪个更新，替你决定就是第二次事故。

引用名形如 `refs/codex-wip/20260813T183000Z-<来源>`，带 UTC 时间与来源标签。`--name` 可以只给尾巴（例如来源标签），但一旦匹配到多张就会拒绝并要求写全名，不猜。

## 绝不碰你的暂存区

这是本工具的头号铁律，因为把「把当前所有改动都加进来」自动化，等于把一次事故变成每隔几分钟重演一次。

- 收集未跟踪文件时，`git add` 一律指向 `GIT_INDEX_FILE` 临时索引，真索引从不打开。
- 恢复时用临时索引 + `git checkout-index`，同理。
- 每次运行前后都会比对暂存区指纹（`git ls-files --stage`）。一旦不一致，**当场中止并把刚存的快照删掉**——宁可没有快照，也不能让快照背上「它改了我的暂存区」的嫌疑。

## 实测边界（这些是跑出来的，不是推的）

| 说法 | 实测结果 |
| --- | --- |
| `git stash create` 会不会改 `.git/index`？ | **会重写该文件**，但只动 stat 缓存。暂存内容不变：`git ls-files --stage` 与索引树前后逐字相同。所以「index 文件 sha256 相同」是个会给出错误答案的代理指标，本工具改用暂存区指纹判断。 |
| 快照会不会被 `git gc` 清掉？ | **不会。** 有 ref 钉着的对象是可达的，`git gc --prune=now` 之后仍然存在。它们不会自己过期。 |
| 那什么时候清？ | 由本工具自己清：每次 `snapshot` 顺带删掉超过保留期的旧快照，默认 14 天（`--retain-days`，`--no-prune` 可关）。**只删 `refs/codex-wip/` 下面的**，同样过期的分支和标签一律不碰。 |
| 日常命令看得见吗？ | `git status`、`git log`、`git branch`、`git stash list` 都看不见。但 `git log --all`、`git for-each-ref`、`git fsck` 看得见——这是事实，不是缺陷，写在这里免得下一个人以为仓库被污染了。 |
| 未跟踪文件存不存？ | 存。`git stash create` 本身**只管已跟踪文件**，未跟踪的由本工具用临时索引单独收，挂成快照提交的第三个父提交（与 `git stash -u` 同形）。 |
| 被 `.gitignore` 忽略的呢？ | 从不收集。否则 `node_modules` 会被反复塞进对象库。 |

## 什么时候它会拒绝拍

- **Git 正处在 rebase / merge / cherry-pick / revert / bisect 中途**：跳过。半途状态存下来是个用户从未真正拥有过的状态。
- **工作区干净**：跳过，不制造空快照。
- **仓库还没有第一个提交**：跳过。
- **大文件**：默认照存但打印警告（阈值 `--large-mb`，默认 5 MB）。加 `--skip-large` 则把超限的**未跟踪**文件排除在外并列出被排除的是哪些。已跟踪文件的改动不会被排除——把它悄悄漏掉会让快照对不上真实内容，那比大一点更危险。

## 验证

`tests/test_workspace_snapshot.py`（18 条）。每条保护都配了「改坏就必红」的用例：拿掉临时索引、拿掉中途跳过、拿掉忽略过滤、拿掉空树跳过、拿掉覆盖保护、拿掉保留期判断，各自变红。保留期的「只删自己命名空间」由两道彼此独立的机制把守（`for-each-ref` 限定前缀 + 循环内前缀复核），任意一道单独去掉行为不变，两道同时去掉才会红——这是有意的纵深防御，不是死代码。
