# Schema 系统

> 状态: **文档蓝图** — 定义标准化的 I/O 契约，供 skill 引用和未来 runtime 验证使用。

## 目录

| 目录 | 用途 | 消费者 |
|------|------|--------|
| `atomic/` | 基础数据类型 (错误码、裁决、修复记录) | lx-* skills (SKILL.md 引用) |
| `contract/` | 状态转换合约 | task_sys orchestrator |
| `input/` | 结构化任务输入 | lx-task-spec |
| `output/` | 验收报告、规范输出、评审报告 | lx-todo, lx-rpe |

## 当前状态

这些 schema 定义了**期望的输出格式**——skill 文档引用它们作为"应该产出什么"的规范。目前没有 hook 在 runtime 做 schema 验证。这是有意为之——schema 作为文档蓝图，指导 skill 输出格式的统一，而非作为物理门禁。

## 未来方向

当某个 skill 的输出格式需要被其他 skill 消费时，schema 可升级为 runtime 验证（在 PostToolUse 做结构化检查）。在此之前，它们作为文档规范存在。
