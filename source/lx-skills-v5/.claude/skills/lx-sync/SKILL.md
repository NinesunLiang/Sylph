---
name: lx-sync
version: v1.0.0
description: "变更后一致性检查：frontmatter↔registry 漂移、source mirror 同步、harness_version 对齐、重复 key、引用完整性。修完任何治理文件后调用。"
when_to_use: "Use after modifying SKILL.md, feature-registry.yaml, VERSION, or any governance file. Trigger: 'lx-sync', 'sync check', '一致性检查', 'check drift'."
argument-hint: "[--skill lx-name]"
harness_version: "6.2.31"
role: "Post-change consistency checker — 6 checks covering drift, mirror, version, duplicates, references"
execution_mode: stepwise
triggers:
  - "/lx-sync"
  - "sync check"
  - "check drift"
status: stable
---

# lx-sync — 变更后一致性检查

> **改完文件 → 跑一次 `/lx-sync` → 确认无漂移。替代记忆 "grep 命令"。**

## 6 项检查

| # | 检查 | 做什么 |
|---|------|--------|
| 1 | registry-drift | SKILL.md frontmatter 描述 vs feature-registry.yaml 描述是否一致 |
| 2 | source-mirror | root `.claude/skills/` 与 `source/lx-skills-v5/.claude/skills/` 是否同步 |
| 3 | version | `harness_version` 是否与 VERSION 文件对齐 |
| 4 | duplicate-key | frontmatter 是否有重复 key（如 triggers 定义两次） |
| 5 | references | SKILL.md 引用的 nodes/schemas/task_sys 文件是否存在 |
| 6 | deps-version | skill-dependencies.yaml 版本号是否与 SKILL.md version 一致 |

## 执行

```bash
python3 .claude/skills/lx-sync/scripts/sync_check.py
```

单 skill：`python3 .claude/skills/lx-sync/scripts/sync_check.py --skill lx-code-review`

JSON 输出：`python3 .claude/skills/lx-sync/scripts/sync_check.py --json`

## 输出示例

```
============================================================
  lx-sync — Consistency Check
  2026-05-15 12:00:00
============================================================

  ❌ registry-drift (3 skills)
     [FAIL] lx-code-review: Registry says "语言无关" but frontmatter says "Go code"

  ✅ source-mirror (26 skills)

  ❌ version (4 skills)
     [FAIL] lx-oma-hier: harness_version=6.1.9 but VERSION=6.2.0

  ✅ duplicate-key (26 skills)
  ✅ references (26 skills)
  ✅ deps-version (6 skills)

============================================================
  Result: 5 FAIL, 0 WARN, 151 PASS
============================================================
```

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #4 | 没验证=没做 | 修完即验证，不依赖记忆 |
| #5 | 以人为本 | `/lx-sync` 替代记忆冗长 grep 命令 |

---

## 降级策略

| 场景 | 处理 |
|------|------|
| sync_check.py 不可用 | 手动执行各检查项的 grep 命令 |
| yaml 模块缺失 | `pip3 install pyyaml` |
