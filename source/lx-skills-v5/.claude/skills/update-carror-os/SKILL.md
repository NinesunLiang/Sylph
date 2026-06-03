---
name: update-carror-os
version: v1.0.0
description: "Carror OS 安装/更新技能，自动保护 AGENTS.md 不被安装脚本污染。备份 → 安装 → 恢复 → 验证 4 步闭环。"
when_to_use: "When user says '更新 Carror OS', '安装 Carror OS', 'upgrade carror', '跑安装包', 'update-carror-os'. Also when user wants to install/refresh Carror OS harness."
argument-hint: "[enhanced]"
harness_version: ">=6.3.0"
role: "Carror OS install/upgrade with AGENTS.md protection — backup, install, restore, verify"
execution_mode: stepwise
triggers:
  - "/update-carror-os"
  - "更新 Carror OS"
  - "安装 Carror OS"
  - "upgrade carror"
  - "跑安装包"
  - "update-carror-os"
status: stable
body_ref: references/body.md
---
