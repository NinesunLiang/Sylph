---
name: lx-pre-push

version: v2.0.0

description: "推送前深度门禁：commit message 规范校验（骨架驱动，通用）→ 测试覆盖 → 安全扫描 → 判定。"

when_to_use: "Use when user says 'pre-push', 'push check', '推送前检查', or before git push."


argument-hint: "<prod-commit-hash>"

harness_version: ">=6.3.0"
status: stable
role: "Pre-push quality gate — commit message validation, diff sanity check"
execution_mode: stepwise

triggers:
  - "/lx-pre-push"
body_ref: references/body.md
---
