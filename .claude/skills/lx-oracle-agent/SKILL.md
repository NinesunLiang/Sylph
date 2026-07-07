---
name: lx-oracle-agent
description: Oracle agent 静态分析审核 — 基于 Oracle-D 协议，偏紧的静态检查：scope 越界、危险路径/命令、file:line 证据、文件存在性和注册完整性
harness_version: ">=6.3.0"
role: "critic — Oracle agent 静态分析，偏紧审查"
execution_mode: stepwise
triggers:
  - "/lx-oracle-agent"
when_to_use:
  - verify/archive 前做静态预检
  - 架构决策终审（跨模块变更）
  - 危险操作前置审核
  - 需要独立第三方检验 scope 合规性时
body_ref: references/body.md
---
