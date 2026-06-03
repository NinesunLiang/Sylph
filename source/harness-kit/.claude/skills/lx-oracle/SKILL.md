---
name: lx-oracle
version: v2.0.0
description: "Oracle 独立第三方审核 — 环境自适应路由: 有 Agent 时物理隔离 spawn, 无 Agent 时本地 prompt。裁决留痕 oracle-verdicts.md。"
role: "Independent third-party auditor for autonomous decision chains"
when_to_use: "Use when autonomous execution hits a decision gate requiring independent review: dangerous operations, architecture decisions, direction drift, hard-boundary pre-checks, or true-blockage judgments. Trigger: '/lx-oracle', 'oracle:review'."
harness_version: ">=6.3.0"
status: stable
execution_mode: stepwise
triggers:
  - "/lx-oracle"
  - "oracle:review"
  - "oracle:approve"
  - "oracle:reject"
# model-agnostic: 路由到 Agent 时由平台自动选择，本地 prompt 时模型无关
body_ref: references/body.md
---
