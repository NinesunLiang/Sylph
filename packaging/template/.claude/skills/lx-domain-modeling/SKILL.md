---
name: lx-domain-modeling
version: v1.0.0
description: "领域语言一致性检查 — 当发现领域术语不一致时警告。纯指令调用，不接入治理管线。"
when_to_use: "Use when reviewing code/docs that reference domain entities, or when the user uses vague/inconsistent domain terminology."
status: stable
---

# lx-domain-modeling — 领域语言检查（Base 版）

> 精简版。仅保留触发算子规则。Enhance 版有主动打磨能力。

## 触发算子

仅以下情况激活语言检查：

1. **一词多义**：同一个名词在不同 context 下解释不同 → "你刚说的 X 在 kernel.md 里定义是 Y，有歧义"

2. **多词一义**：不同模块/组件指代同一实体 → "模块 A 叫 Customer，模块 B 叫 User，是一个东西吗"

3. **与 kernel.md 冲突**：当前用语与 kernel.md 术语不同 → "kernel.md 定义的是 X，但这里叫 Y"

## 不做的事

- 不修改 kernel.md（冻结规则）
- 不主动"打磨"语言（Base 版只触发警告）
- 不是 spec 文档
- 不记录琐碎选择
