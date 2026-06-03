---
name: lx-validate-skill

version: v4.0.0

description: "验收新 skill 是否遵循原子化架构规则。检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等 11 项规则。"

complexity: beginner
when_to_use: "Use after creating a new skill. Trigger: 'validate skill', 'check skill', 'new skill review', 'skill audit'."


argument-hint: "[skill-name, default: all lx-* skills]"

paths:

 - ".claude/skills/lx-*/SKILL.md"

harness_version: ">=6.3.0"
status: draft
role: "Skill atomization compliance validator — 11-rule architecture check"
execution_mode: stepwise

triggers:
  - "/lx-validate-skill"
body_ref: references/body.md
---
