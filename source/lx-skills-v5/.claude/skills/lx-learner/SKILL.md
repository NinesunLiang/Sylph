---
name: lx-learner
version: v1.0.0
description: "从对话中提取可重复工作流并生成 lx-* skill。检测模式 → 提议提取 → 生成技能 → 附带来源文档。"
when_to_use: "Use when user says 'learner', 'extract skill', '从对话中学习', /learner, or AI detects repeated workflow patterns"
argument-hint: "[可选：指定要提取的重复任务描述。留空则自动检测对话模式]"
harness_version: ">=6.3.0"
status: draft
role: "技能学习者 — 从对话模式中检测、提议并提取可重用 lx-* skill，附带来源文档"
execution_mode: stepwise
triggers:
  - "/learner"
  - "learner"
  - "extract skill"
  - "从对话中学习"
body_ref: reference/body.md
---
