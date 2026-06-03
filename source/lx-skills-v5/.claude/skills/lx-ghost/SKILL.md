---
name: lx-ghost
version: v1.4.1
description: "幽灵模式 — 方向驱动的自主探索。Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告。"
when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3] [最小迭代数=0]"
harness_version: ">=6.3.0"
status: stable
role: "Direction-driven autonomous exploration — Oracle-gated single briefing, zero interruptions"
execution_mode: stepwise
triggers: ["/lx-ghost"]
body_ref: references/body.md
---
