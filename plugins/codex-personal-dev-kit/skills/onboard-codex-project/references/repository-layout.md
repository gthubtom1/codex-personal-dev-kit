# 项目和目录分级

## 多项目工作区

无关长期项目使用并列目录和独立 Git 仓库：

```text
开发工作区/
├── codex-dev-kit/
├── project-a/
├── project-b/
├── shared-assets/
└── archives/
```

- 不把 `project-a` 和 `project-b` 放进同一个仓库，除非它们本来就是需要统一发布的 monorepo。
- `shared-assets` 只放真正跨项目复用且有明确版本策略的内容。
- 归档项目保留 Git 历史和恢复说明，不与活跃项目混放。
- Codex Desktop 中一个长期项目对应一个 Local Project；不相关目录使用不同 Project。

## 单项目建议结构

根据技术栈调整名称，但保持职责可定位：

```text
project/
├── AGENTS.md
├── README.md
├── .codex/
│   └── config.toml
├── docs/
│   ├── PROJECT.md
│   ├── FEATURES.md
│   ├── ROADMAP.md
│   ├── ARCHITECTURE.md
│   ├── STATUS.md
│   ├── RUNBOOK.md
│   └── adr/
├── src/
├── tests/
├── scripts/
└── package-or-build-files
```

## 分级原则

- 目录按业务或技术责任划分，不按“misc”“utils2”长期堆放。
- 一个模块有明确入口、依赖方向和测试位置。
- 生成物、依赖和缓存不进入源码目录。
- 只有当前范围需要特殊指令时才添加嵌套 `AGENTS.md`。
- 项目文档保存当前事实，历史保存到 Git；重大架构决定保存到 ADR。
