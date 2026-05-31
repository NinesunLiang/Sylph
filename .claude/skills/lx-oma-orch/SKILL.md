---
name: lx-oma-orch
description: Pipeline Orchestrator — 4-skill 管线编排（状态查看/阶段推进/Oracle 门禁/并行开发管理）
version: v1.2.2
harness_version: ">=6.3.0"
status: stable
argument-hint: "status | advance [--force] | gate <og-id> approve|reject [--reason \"...\"] | run <target> | dev list | dev mark <feature-id> <status>"
when_to_use: |
  查看 PRD 全生命周期管线进度、推进到下一阶段、裁决 Oracle 门禁、直接路由到子 skill、管理并行开发进度
triggers: ["/lx-oma-orch", "pipeline", "管线状态", "orchestrate"]
role: "Pipeline orchestrator — 4-skill lifecycle orchestration with Oracle gates"
execution_mode: stepwise
body_ref: reference/body.md
---
