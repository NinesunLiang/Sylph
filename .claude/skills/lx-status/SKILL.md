---
name: lx-status

version: v2.0.0

description: "Carror OS 健康面板 v3.0：Token 节省、任务通过率、拦截的错误、升华的知识点 + ROI 量化面板。底部追加 audit dashboard 摘要（5 源聚合）。"

complexity: beginner
when_to_use: "Use when user says 'status', 'show dashboard', 'health check', 'lx-status', '面板', '状态'"


argument-hint: "[--json | --watch]"

harness_version: ">=6.3.0"
status: draft
role: "Carror OS health dashboard — system status panel"
execution_mode: race

triggers:
  - "/lx-status"
  - "status"
  - "dashboard"
body_ref: reference/body.md
---
