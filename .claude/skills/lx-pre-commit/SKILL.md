---
name: lx-pre-commit

version: v2.0.0

description: "提交前质量门禁：项目类型检测 → 编译 → 测试 → 代码审查。操作层由 scripts/ 脚本执行，AI 负责结果解读和路由决策。"

when_to_use: "Use when user says 'pre-commit', 'commit check', '提交前检查', or before git commit."


argument-hint: "[--skip-review]"

harness_version: ">=6.3.0"
status: stable
role: "Pre-commit quality gate — compile, test, lint, coverage check"
execution_mode: stepwise

triggers:
  - "/lx-pre-commit"
body_ref: reference/body.md
---
