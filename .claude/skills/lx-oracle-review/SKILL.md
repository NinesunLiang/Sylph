---
name: lx-oracle-review
description: 完整双 Agent Oracle 审核 — 同时执行静态分析 + 运行时分析，再经 Meta-Oracle G1-G4 聚合评分
harness_version: ">=6.3.0"
role: "orchestrator — 编排 Static + Runtime 双 Oracle 做完整审核链路"
execution_mode: stepwise
triggers:
  - "/lx-oracle-review"
when_to_use:
  - verify/archive 前做完整双检
  - 架构评审终审
  - Release 门禁
  - 任何需要双重 Oracle 验证的高风险场景
dependencies:
  - lx-oracle-agent
  - lx-oracle-meta
body_ref: references/body.md
---
