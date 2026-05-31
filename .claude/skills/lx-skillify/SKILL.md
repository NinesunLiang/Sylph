---
name: lx-skillify
version: v1.0.0
description: "将自然语言描述转化为生产级 lx-* skill。6 阶段管道。"
when_to_use: "Use when user says 'skillify', '创建 skill', '生成 skill', /skillify"
argument-hint: "[描述，例如：'创建一个审查 Dockerfile 的 skill']"
harness_version: ">=6.3.0"
status: draft
role: "Skill 自动生成器 — 6 阶段管道：澄清→分析→生成→创建→验证→注册"
execution_mode: stepwise
triggers:
  - "/skillify"
  - "skillify"
  - "创建 skill"
body_ref: reference/body.md
---
