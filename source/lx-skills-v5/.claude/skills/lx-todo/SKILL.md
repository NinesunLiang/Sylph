---
name: lx-todo
version: v4.0.0
description: "轻量开发模式：捕获 → 分拣 → 执行 → 验证 → 关闭。5 步单终端闭环，≤3 文件变更。"
complexity: beginner
when_to_use: "Use when user says 'todo', 'quick fix', 'small bug', /lx-todo"
argument-hint: "add 🐛 P1 <desc> | do [#id] | next | list | review"
harness_version: ">=6.3.0"
status: mature
role: "Lightweight single-terminal fix-verify-close workflow"
execution_mode: stepwise
triggers:
  - "/lx-todo"
body_ref: reference/body.md
---
