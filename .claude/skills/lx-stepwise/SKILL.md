---
name: lx-stepwise
version: v1.0.0
description: 逐步攻坚模式 — 高难度 bug 单步推进，每步需验证，不可跳过。与 lx-race 互补（race 并行快处理，stepwise 串行深攻坚）。
category: infrastructure
type: orchestrator
execution_mode: stepwise
enabled_by_default: true
harness_version: ">=6.3.0"
status: stable
role: "Stepwise debugger — serial deep-dive, each step verified"
evidence_level: L3
triggers:
  - "stepwise"
  - "single step"
  - "deep debug"
  - "step by step"
when_to_use: "Use for high-difficulty serial debugging: unknown root cause, cross-module (>3 files), failed prior fixes (2+), complex state machines or concurrency. Auto-routed by goal/ghost, not manually invoked."
body_ref: references/body.md
---
