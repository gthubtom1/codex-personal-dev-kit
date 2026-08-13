# 本地正式版本

## 两层历史

- 普通检查点：每个验证切片自动保存，用于短期回退，不要求用户记忆，也不创建标签。
- 正式版本：用户接受的完整里程碑。使用 `v主版本.次版本.修订版本`、`docs/VERSIONS.md` 和指向最终检查点的本地不可移动标签。

不要为 v1.0、v1.1 创建分支。版本标签只在本机保存，不代表 GitHub Release、发布、部署或远程备份。

## 版本号

- 修复且不增加能力：`v1.2.0` → `v1.2.1`。
- 增加兼容的新能力：`v1.2.0` → `v1.3.0`。
- 明确的不兼容产品或数据变化：先说明影响并询问，再考虑 `v2.0.0`。
- 用户说 `v1.2` 时规范化为 `v1.2.0`。用户不需要自己决定；Codex根据已经接受的版本推荐下一编号并说明一句原因。

## 创建正式版本

1. 确认这是完整、可运行、已验证的用户里程碑，而不是普通修复中途状态。
2. 按 [release-readiness.md](release-readiness.md) 完成 21 维发布终审，把逐维结论覆盖写入 `docs/RELEASE-REVIEW.md` 并记录本次版本号；未验证的维度如实标注原因，不许伪造。
3. 在 `docs/VERSIONS.md` 增加一行，描述用户能识别的能力、保留行为和验证；第一个版本建立时删除“No formal version”占位句。不要写 commit hash 或开发流水账。
4. 同步项目已有版本字段，例如 `package.json` 或根目录 `VERSION`。没有版本字段时不新增无意义清单；存在的字段必须与正式标签一致。
5. 把代码、测试、功能地图、STATUS、VERSIONS、RELEASE-REVIEW 和版本字段放进同一个最终检查点，避免随后再建“只记录完成”的第二个提交。
6. 检查点形成且工作树干净后运行：

```text
python <dev-kit-root>/scripts/feature_guard.py version --root . --name v1.2.0
```

该命令只允许标记当前已验证的 Dev Kit 检查点；标签已存在、版本索引缺失、21 维终审缺失或不完整、项目版本字段不一致或工作树不干净时必须停止。禁止通过原始 Git 命令创建、移动、覆盖或删除旧版本标签；只读标签查询可以用于审计。

接管已有项目时，如果过去的完整里程碑已经是当前分支历史中的 Dev Kit 检查点，可以补建正式标签：

```text
python <dev-kit-root>/scripts/feature_guard.py version --root . --name v1.0.0 --target <历史检查点>
```

`--target` 只供 Codex 内部迁移使用，不要求用户提供提交编号。它拒绝非当前分支祖先、非 Dev Kit 检查点、版本字段不匹配和已存在的标签，不能成为任意移动标签的后门。历史检查点树中通常没有终审文件且不可改写；补建前先在当前检查点为该历史版本完成 21 维终审（`- Version:` 写历史版本号），门禁接受当前 HEAD 中记录该版本的终审。

## 找版本

用户不需要记住编号。先读取 `docs/VERSIONS.md`，再运行只读列表：

```text
python <dev-kit-root>/scripts/feature_guard.py versions --root .
```

根据能力描述回答差异，例如“有护盾但没有激光 Boss”。如果两个版本都可能匹配，列出差异并让用户确认，不让其选择 commit hash。

## 恢复正式版本

确认目标后，在工作树干净且没有未完成契约时运行：

```text
python <dev-kit-root>/scripts/feature_guard.py restore-version --root . --name v1.2.0
```

恢复会在当前分支创建一个新的检查点，其产品内容匹配所选标签；后续版本的提交和标签继续保留，完整 `docs/VERSIONS.md` 也会保留。不得使用 `reset --hard`、删除分支、移动标签或让用户手工 checkout。
