---
name: lx-sync
version: v1.0.0
description: "变更后一致性检查：frontmatter↔registry 漂移、source mirror 同步、harness_version 对齐、重复 key、引用完整性。修完任何治理文件后调用。"
when_to_use: "Use after modifying SKILL.md, feature-registry.yaml, VERSION, or any governance file. Trigger: 'lx-sync', 'sync check', '一致性检查', 'check drift'."
argument-hint: "[--skill lx-name]"
harness_version: ">=6.3.0"
role: "Post-change consistency checker — 6 checks covering drift, mirror, version, duplicates, references"
execution_mode: stepwise
triggers:
  - "/lx-sync"
  - "sync check"
  - "check drift"
status: stable
body_ref: reference/body.md
---
