---
name: lx-domain-modeling
version: v1.0.0
description: "主动领域语言管理 — 语言挑战 + ADR 记录。Enhance 专有。在 Phase0 澄清和代码设计过程中主动打磨领域术语一致性。"
when_to_use: "Use when designing/building/refactoring in a domain with established vocabulary, or when the user uses vague/inconsistent terminology."
harness_version: ">=6.3.0"
status: stable
---

# lx-domain-modeling — 领域语言管理

> Enhance 专有。不写 kernel.md（冻结规则）。ADR 放 `.claude/references/adr/`。

## 三规则

### 规则 1: 语言挑战

触发算子 — 仅以下情况激活：
- **一词多义**：同一个名词在不同 context 下解释不同 → "你刚说的 X 在 kernel.md 里定义是 Y，有歧义"
- **多词一义**：不同模块/组件指代同一实体 → "模块 A 叫 Customer，模块 B 叫 User，是一个东西吗"
- **与 kernel.md 冲突**：当前用语与 kernel.md 术语不同 → "kernel.md 定义的是 X，但代码里叫 Y"

不触发的情况：闲聊、非领域命名（变量名/临时变量）、外部术语（第三方库概念）。

### 规则 2: ADR 记录

仅当三个条件都满足时写 ADR：
1. **难撤销** — 后悔成本高
2. **非直觉** — 未来读者会问"为什么"
3. **真权衡** — 有明确替代方案并做了选择

ADR 写到 `.claude/references/adr/NNNN-title.md`，参考 ADR-FORMAT.md 模板。写完后刷新 INDEX.md。

### 规则 3: 不做的事

- 不修改 kernel.md
- 不创建 CONTEXT.md（用 kernel.md + index.md 替代）
- 不是 spec 文档，只记录领域语言决策
- 不记录琐碎选择（变量名风格 / 代码格式）

## 调用场景

- lx-goal Phase0 自动调用（ADR 判断步骤）
- lx-codebase-design 设计过程中
- 用户显式提及 "/lx-domain-modeling" 时
