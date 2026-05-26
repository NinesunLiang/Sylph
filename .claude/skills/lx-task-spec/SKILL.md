---
name: lx-task-spec
version: v5.1.0
harness_version: ">=6.3.0"
status: stable
description: "任务驱动机制：lx-todo 升级目标，处理需精确 AC 但不需要完整 PRD 的中等复杂任务。3 问引导 → 规划 → 执行 → 验收。"
complexity: intermediate
when_to_use: "Use when task needs precise AC but not full PRD; lx-todo upgrades (>3 files/2 failures); /lx-task-spec"
role: "Task specification engine — structured task decomposition and execution"
execution_mode: stepwise
triggers:
  - "/lx-task-spec"
---

# lx-task-spec — 任务驱动机制

> **内在机制，按需触发。** 不触发时不加载任何 task_spec 相关文件。

## 原子化声明

| 节点 | 路径 |
|------|------|
| interactive_prompt | `../../nodes/interactive_prompt.md` |
| target_resolver / context_collector / generator / execute_node / verifier / report_generator / behavior_rules | `../../nodes/` |

| Schema | 路径 |
|--------|------|
| task_input / scan_target / finding / fix_record / verdict | `../../schemas/` |

| task_sys | 路径 |
|----------|------|
| orchestrator / loading_matrix / unified_delivery_schema / context_guard | `../../task_sys/` |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/ac-template.md` | ac template 阶段 |
| `references/execution-modes.md` | execution modes 阶段 |
| `references/guided-interaction.md` | guided interaction 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机 → `../../task_sys/orchestrator.md`

```
引导收集 → need_clarification → ready → planning → executing → done
              ↑ ↑ ↑ ↑
              └─ blocked ────┘ └─ fallback ┘
```

## 触发路由

| 输入 | 行为 |
|------|------|
| `/lx-task-spec`（无参数） | 恢复活跃任务 |
| 从 lx-todo 升级 | 携带 todo 上下文 → 直接规划 |
| `/lx-task-spec <描述>` | 3 问引导 |
| 结构化 task_input YAML | 跳过引导 → 直接规划 |

## 三模式边界

| 模式 | 场景 | 升级 |
|------|------|------|
| lx-todo | ≤3 文件快速闭环 | → lx-task-spec |
| lx-task-spec | 需精确 AC，>3 文件或需设计 | → lx-rpe |
| lx-rpe | 大特性，完整 PRD | — |

## 引导交互 → `@references/guided-interaction.md`

3 问逐个引导（名称/目标/AC），用户说"帮我生成"→ AI 自动生成 AC 草稿。完成后生成 task_input YAML，确认后开始。

## 执行模式 → `@references/execution-modes.md`

- **stepwise**（默认）：逐步执行，每步验证
- **race**：规划后并行派发独立子任务（后端 lx-race）

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| orchestrator 加载失败 | 状态机 | 跳过状态机，直接 3 问 |
| 无活跃任务 | 恢复 | 提示创建新任务 |
| AC 无法自动生成 | AI 草稿 | 提供 AC 模板让用户填写 |
