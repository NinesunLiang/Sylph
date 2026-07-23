# references/ — 公共资源文档

> 存放 CarrorOS 设计文档、架构决策、模板、规则等可复用资源。
> subdir 索引由各子目录的 `INDEX.md` 管理。

## 目录结构

| 目录 | 用途 | 入口 |
|------|------|------|
| `adr/` | 架构决策记录 | `INDEX.md` |
| `design-docs/` | 设计文档（分阶段编号） | `1.md` ~ `11.md` 按主题阅读 |
| `task-architecture/` | 任务架构参考 | `orchestrator.md`, `loading_matrix.md` 等 |
| `templates/` | 模板（handoff-capsule, stepwise-cards 等） | 直接引用 |
| `race/` | Race 编排模式文档 | `state-machine.md` |

## 独立文件

| 文件 | 用途 |
|------|------|
| `SOUL.md` | CarrorOS 哲学（铁律/优先级/设计原则） |
| `SUBAGENT.md` | SubAgent 契约 |
| `anti-patterns.md` | 已知反模式库（飞轮自动补充） |
| `context-watermark.md` | 三段式水位规格 |
| `evaluation-framework.md` | 评分框架（C1-C9/E1-E8/治理/UX） |
| `fallback-matrix.md` | 降级矩阵 |
| `feature-registry.yaml` | 功能注册表 |
| `gate-rules.yaml` | Gate 规则 |
| `invariants.md` | 12 条系统不变量 |
| `oracle-spec.md` | Oracle 门禁规格 |
| `philosophy.md` | 决策链哲学 |
| `skill-atomization-guide.md` | Skill 原子化指南 |

## ADR

新增架构决策时在 `adr/` 下创建文件并按模板格式填写。
