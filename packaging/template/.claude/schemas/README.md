# Schema 系统

> 状态: **文档蓝图** — 定义标准化的 I/O 契约，供 skill 引用和未来 runtime 验证使用。

## 目录

| 目录 | 用途 | 消费者 |
|------|------|--------|
| `atomic/` | 基础数据类型 (错误码、裁决、修复记录) | lx-* skills (SKILL.md 引用) |
| `contract/` | 状态转换合约 | phase_contracts.py / step_contracts.py |
| `input/` | 结构化任务输入 | lx-task-spec |
| `output/` | 验收报告、规范输出、评审报告 | lx-todo, lx-rpe |

## 当前状态

这些 schema 定义了**期望的输出格式**——skill 文档引用它们作为"应该产出什么"的规范。阶段交接使用 `.claude/schemas/contract/phase_handoff.yaml`，由 `.claude/scripts/phase_contracts.py` 在任务目录 `state/` 生成阶段/步骤 handoff 骨架，并由下一阶段门禁消费。

运行时原则：schema 先生成骨架，再由下一门禁检查对应内容是否 ready；VerifyGate 等末端校验保留为兜底，不替代前置交接。
