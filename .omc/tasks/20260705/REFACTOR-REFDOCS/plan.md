# Plan: REFACTOR-REFDOCS

## Goal
统一 .claude/references/ 目录文档的治理层格式（YAML frontmatter + 证据门禁标记 + 版本头）

## Scope
- .claude/references/SOUL.md
- .claude/references/anti-patterns.md
- .claude/references/philosophy.md

## Steps
- [ ] S1: 给 SOUL.md 添加 YAML frontmatter + 证据标记
- [ ] S2: 给 anti-patterns.md 添加 YAML frontmatter + 证据标记
- [ ] S3: 给 philosophy.md 添加 YAML frontmatter + 证据标记

## Verify
- S1: SOUL.md 第1行是 "---"，有 name/version/level 字段，每个断言含 `[已验证：file:line]`
- S2: anti-patterns.md 第1行是 "---"，同上
- S3: philosophy.md 第1行是 "---"，同上

---
> 冻结规则：不改 scope、不改 step 顺序、不改 verify 条件。
