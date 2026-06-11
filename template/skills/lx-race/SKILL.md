---
name: lx-race
description: "蜂群协调层 — 快速并行处理简单同构任务。goal/ghost 自动路由至此。"
complexity: intermediate
version: v1.0.0
harness_version: ">=6.3.0"
status: stable
when_to_use: "任务有多个独立同构子任务可并行执行；goal/ghost 自动路由；/lx-race 手动调用"
role: "Swarm coordinator — sub-task registration, dispatch, collection, conflict resolution"
execution_mode: race
triggers:
  - "/lx-race"
body_ref: references/body.md
---
