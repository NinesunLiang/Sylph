---
name: lx-rpe
version: v4.0.0
description: "RPE 系统性特性开发 — 9 步闭环：TDD → code-review → security → acceptance → graded rollback"
complexity: advanced
when_to_use: "Use when user says 'rpe', 'feature dev', '/lx-rpe', or begins systematic feature development"
argument-hint: "new [name] [需求描述] | [feature name] | [path] | status | batch-accept"
harness_version: ">=6.3.0"
status: mature
role: "RPE-driven feature development — 9-step closed loop with quality gates"
execution_mode: stepwise
triggers:
  - "/lx-rpe"
body_ref: reference/body.md
---
