---
name: lx-oma-hier
description: 分层 PRD 拆解 — 将超大型 PRD 按功能域 MECE 拆分为多个 Sub PRD（黑盒/接口契约/Mock 数据/内部闭环），再委托 lx-oma-split 拆解为特性级 RPE。
version: v1.3.2
harness_version: ">=6.3.0"
status: stable
argument-hint: "<path> [output_dir]"
when_to_use: |
  当需要将超大型 PRD 按功能域 MECE 拆分为多个独立的 Sub PRD，
  每个 Sub PRD 定义接口契约、Mock 数据、黑盒边界、依赖关系和验收条件，
  并可进一步委托 lx-oma-split 拆解为特性级 RPE。
triggers: ["/lx-oma-hier", "分层拆解", "prd 拆分"]
role: "PRD hierarchical decomposer — master PRD to Sub PRDs (Level 1)"
execution_mode: stepwise
body_ref: reference/body.md
---
