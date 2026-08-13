# Dev Kit 正式版本

这里只记录经过完整验证、适合固定 Git tag 和跨电脑恢复的正式分发版本。普通开发检查点保留在本地 Git 历史中，不形成文档流水账。

| 版本 | 用户可识别的能力 | 验证与恢复状态 |
| --- | --- | --- |
| v0.2.10 | 让并行 / 多 agent 开发不再拖垮编辑器：worktree 一律建到工作区外（代码本就如此），Cursor / VSCode 再由随项目模板附带的 `.cursor/hooks.json`（beforeShellExecution 守卫 `worktree_guard.py`）硬拦「解析到工作区内的 git worktree add」（含把父文件夹当工作区打开的情形），并附 `.vscode/settings.json` 把 `__pycache__` / `*.sqlite3*` / `*.db` 排除出监视与搜索；顺带修掉命令分类器被换行 / `$()` 绕过的 force-push 通道，把「worktree 外置」写进短全局规则与 README（含「安装 AI 必读自检清单」），澄清 `validate-kit.ps1` 为 Codex 专属（非 Codex 宿主用 `validate_kit.py` 加单测） | Cursor 守卫实测 8/8（拦 `.local/` / 相对内 / 换行藏 / 父文件夹；放行外置 / status / list；处理 Windows 反斜杠）；新增 `tests/test_worktree_guard_hooks.py` 10 条「改坏必红」守卫全绿；全量套件实跑 `Ran 221 tests OK`（211 + 10，exit 0）、`validate_kit` 结构校验通过后创建本地不可移动标签 v0.2.10；远程发布经用户授权走 guarded publish |
| v0.2.9 | 让这套系统被其他 agent（Cursor / Claude 等）从 GitHub 采用后不打折：把 AGENTS.md / README / Skill 里 Codex 宿主专属的内容（$skill 调用语法、spawn_agent 原生子代理、openai.yaml、.system+resolve-skill、CODEX_HOME/~/.codex、第 12 节 Codex 桌面设置）清楚标注为「宿主相关」，核心方法论与 Codex 专属分层可见，并在 README 增加一张逐节映射表告诉非 Codex 宿主每一条对应的本宿主做法或「跳过」 | 纯文档增量，代码/测试逐字未变；全仓扫出 Codex 专属清单，标注为纯新增未破坏 validate_kit 必需标题与 token（结构校验 COVERAGE 8/8、0 error），211 用例实跑 OK 后创建本地不可移动标签 v0.2.9；远程备份经用户授权走 guarded publish |
| v0.2.8 | 一个 checkout 只允许一个源码写入者（写入锁，第二个写入者当场被拒并告知持锁人与时长）；自动 index-safe 工作树快照救命网可无损保全散落的在途改动；体检列工作区大文件；并行副本强制放工作区外；套件读本仓自身功能表使重号无法蒙混过绿；另加四条从 exe-product-lifecycle 复审吸收的防御守卫（技能清单三处防漂移、验证器覆盖率/中断记账、PowerShell 保留自动变量赋值 lint、拒绝不泄漏 Python 回溯） | 21 维终审在 a473463 复审无 P0/P1，211 用例两次独立实跑全绿、结构与 Skill 校验通过后创建本地不可移动标签 v0.2.8；四条新守卫与写入锁套件均「改坏必红」变异验证并经独立复审复现；远程备份经用户授权走 guarded publish |
| v0.2.7 | 正式版本前必须通过 21 维发布终审硬门（缺维度、伪造状态或空证据一律拒绝打标签，如实标 `not-verified` 可放行）；新增只读 `next_step.py` 入口脚本，按仓库真实状态直接打印下一条该跑的命令；「先查现成做法再动手」成为新能力的默认行为；暂存前复扫密钥、锁文件漂移与大文件警告三道保护；中文 Windows(cp936) 下安装与诊断脚本不再乱码 | 三名独立只读采集者在 `89ea0dd` 上分头实跑 21 维终审并各留可复跑命令，结论记入 `docs/RELEASE-REVIEW.md`（10 维已验证、9 维部分验证、1 维不适用、用户验收如实标未验证，无 P0/P1）；123 用例全绿、9 个 Skill 校验与结构检查通过后创建本地不可移动标签；远程同步需用户另行授权 |
| v0.2.6 | GitHub 保存当前完整中文母目录规则的可移植标准模板；新电脑按真实 Codex Home、工作区名称/路径和 Skill 源生成同一套规则，诊断能发现本机与固定模板的漂移且不泄露自定义内容 | 模板逐字渲染、空白安装、已有规则保护、漂移诊断、完整回归和 standalone 校验通过后创建本地不可移动标签；可按用户授权同步既有 GitHub 仓库 |
| v0.2.5 | 全新 Windows 电脑只需固定 Git checkout 和一次 standalone 安装：安装器会从空白母目录创建详细 `AGENTS.md`、工作区骨架和配置，再生成指向真实路径的全局短版 `AGENTS.md`；预览不写入，重复安装幂等，已有母目录规则不覆盖 | 空白环境、重复安装、已有规则保护、完整回归和 standalone 诊断通过后创建本地不可移动标签；可按用户授权通过 guarded publisher 同步既有 GitHub 仓库 |
| v0.2.4 | v0.2.3 四条受控通道的干净安装修正版：安装器永久排除 `__pycache__`、`.pyc` 和 `.pyo`，并清理先前由 Dev Kit 管理的缓存残留 | 完整回归、安装幂等和真实 standalone 诊断通过后创建本地不可移动标签；已同步既有 GitHub 仓库 |
| v0.2.3 | 在 v0.2.2 远程备份基础上增加四条零基础受控通道：快进同步/线性整合、精确撤销暂存、安全 Worktree 清理、固定版本 winget 工具安装 | 完整回归和结构验证通过后创建本地不可移动标签；外部 GitHub 更新需要本次另行授权 |
| v0.2.2 | 增加零基础受控远程备份：用户只需明确授权仓库、分支和正式标签，AI 自行 dry-run、精确推送并核验；原始/强制 push 和远程删除仍被阻止 | 完整回归和结构验证通过后创建不可移动标签，并通过 guarded publisher 同步 `main`、v0.2.0、v0.2.1 和 v0.2.2 |
| v0.2.1 | 在 v0.2.0 完整跨电脑恢复能力上增加 MIT 许可证、第三方方法来源说明，以及 `VERSION`/正式标签一致性保护 | 完整回归和结构验证通过后创建不可移动本地标签；公开 GitHub 推荐固定使用此版本 |
| v0.2.0 | 两层 `AGENTS.md`、九个 standalone Skills、零基础开发入口、旧功能保护、Git 检查点、正式项目版本、上下文记忆、受控公开研究、多项目能力融合、新电脑恢复和完整诊断 | 完整回归和结构验证通过后创建不可移动本地标签；支持从固定 GitHub tag 恢复 |

## 规则

- 每个正式版本必须对应干净、已验证的 Dev Kit 检查点和根目录 `VERSION`。
- 不记录聊天历史、完整 diff、压力测试日志、安装缓存或普通检查点。
- 本地标签不等于已经 push、发布或创建 GitHub Release。
