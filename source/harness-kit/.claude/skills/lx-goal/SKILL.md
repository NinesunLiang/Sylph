---
name: lx-goal
version: v1.4.1
description: "目标模式 — 一次前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。"
when_to_use: "Use when user says 'goal mode', 'lx-goal', '无人值守', '自主执行', /lx-goal"
argument-hint: "[目标描述] [过期小时=6]"
harness_version: ">=6.3.0"
status: stable
role: "Goal-driven autonomous execution — single briefing, zero interruptions, final report"
execution_mode: stepwise
triggers: ["/lx-goal"]
body_ref: references/body.md
---
