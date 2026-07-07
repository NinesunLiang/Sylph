---
name: lx-oracle-meta
description: Meta-Oracle 运行时验证审核 — 基于 Oracle-V 协议，偏松的运行时验证：token 进度、executor 执行证据、audit 事件、G1-G4 门禁评分
harness_version: ">=6.3.0"
role: "critic — Meta-Oracle 运行时验证，偏松审查"
execution_mode: stepwise
triggers:
  - "/lx-oracle-meta"
when_to_use:
  - verify/archive 前做运行时验证
  - 执行后终审（预测 vs 事实 vs 自证）
  - 方案/PRD 事前审核
  - 需要独立第三方验证执行完整性时
body_ref: references/body.md
---
