---
name: lx-oma-gov
description: OMA PRD 治理 — reconcile/propagate 增量同步、冲突裁决、漂移检测
version: v1.2.1
harness_version: ">=6.3.0"
status: mature
argument-hint: "init [path] | reconcile [path] | resolve <CONFLICT-ID> <verdict> [--reason] | propagate --dry-run|--execute [path] | status | audit [path]"
when_to_use: 主 PRD 变更需向下游 feature 增量同步、检测漂移、PRD 冲突需人工裁决、查看治理状态
triggers: ["/lx-oma-gov", "oma治理", "reconcile", "propagate", "漂移检测"]
role: "PRD governance — drift detection, reconciliation, propagation"
execution_mode: stepwise
body_ref: references/body.md
---
