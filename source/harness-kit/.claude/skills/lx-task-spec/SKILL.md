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
body_ref: references/body.md
---
