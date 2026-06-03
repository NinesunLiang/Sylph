---
name: lx-oma-split
description: 一人成军司令部 — 将需求拆解为正交 feature 分支（prd/{sub_prd}/{feature}）
version: v1.2.1
harness_version: ">=6.3.0"
status: stable
argument-hint: "<path> [--pipeline <sub_prd_id>]"
when_to_use: Sub PRD 已完成 hier 拆解，需拆解为可独立开发的 feature 级 RPE
triggers: ["/lx-oma-split", "拆解需求", "一人成军拆解"]
role: "OMA commander — Sub PRD to feature decomposition (Level 2)"
execution_mode: race
body_ref: references/body.md
---
