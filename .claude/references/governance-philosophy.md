# CarrorOS 治理哲学：疏导 + 兜底

> **原则**：不防错（防不过来），而是**疏导**（工作流步骤前置引导）+ **兜底**（防止 AI 不遵循引导）。

## 核心思想

| 模式 | 描述 | 工作量 | 算力消耗 |
|---|---|---|---|
| **防错**（禁用）| 试图预测 AI 所有错误并拦截 | 不可穷尽 | — |
| **疏导**（首选）| 在 step 前置给 AI 明确引导 | 低 | 低 |
| **兜底**（辅助）| AI 不遵守引导时拦截 | 中 | 中 |

**双层设计**：每个治理机制**先疏导**（前置 tooltip / 模板 / 字段引导）→ **后兜底**（REDIRECT / BLOCK）。

## 实测分类（2026-08-30 评估时点快照）

> ⚠️ 本表是 2026-08-30 评估时点的 22 门快照，**不是现状**：其后 index47/48/49 按 ROI 删除多门，2026-10-16 人类裁决收敛为 L1=L2=14 道，门数现状单一真源 = `pretool-gate.py::_GATE_CORE`。本表保留用于"疏导 vs 兜底"比例的方法论参考。

按 2026-08-30 评估：

| 类别 | 数量 | 比例 | 例子 |
|---|---|---|---|
| **疏导为主** | 8 | 36% | doc_reference_before_delete / verify_gate / oracle_gate / document_quality / g2_large_file / g5_wide_glob / g6_budget / numeric_claim |
| **疏导 + 兜底双层** | 11 | 50% | sensitive_edit (goal-mode 降级 + 兜底) / secret_scan (前置 scan + 兜底 REDIRECT) / commit_soft_completion (模板提示 + REDIRECT) / action_gate (替代方案提示 + REDIRECT) / doc_reference_before_delete (REDIRECT 包含如何处理) / 等等 |
| **纯兜底** | 3 | 14% | governance_bypass (恶意绕过) / injection (攻击) / omc_skeleton_readonly (写 .omc 文档) |

**目标比例**：疏导 ≥ 50%、纯兜底 ≤ 10%。当前大致满足。

## 实操准则

加新门时**按此顺序考虑**：

1. **能否疏导？** → 加 tooltip / 模板 / 字段前置引导
2. **是否必须兜底？**（如安全、攻击面）→ 加 REDIRECT / BLOCK
3. **两者都要？** → 疏导优先，兜底次之

## 当时已含疏导+兜底双层的门（11 个，2026-08-30 时点）

- sensitive_edit (goal-mode 降级放行 + REDIRECT 提示)
- sensitive_write_bash (替代方案提示 + REDIRECT)
- sensitive_read (skip 时 log + 通知)
- secret_scan (git push 前置 scan + WARN)
- action_gate (替代方案建议 + REDIRECT)
- commit_soft_completion (VERIFIED 模板建议 + REDIRECT)
- doc_reference_before_delete (REDIRECT 含处理建议)
- verify_gate (plan verify 字段前置 + REDIRECT)
- test_verification (verify 字段前置 + REDIRECT)
- action_loop (建议 + 升级 ASK_USER)
- stall (建议恢复 + REDIRECT)

## 不应加的"纯防错"模式

- 试图预测所有软完成语
- 试图预测所有 scope creep 模式
- 试图预测所有 secret 模式
- 试图用规则覆盖所有 LLM 输出错误

**这些防错工作量指数增长、收益递减**——优先用疏导。

## 用户哲学原话（2026-08-30）

> "我们不防错（因为防不过来），而是疏导（工作流步骤前置的引导）+ 兜底（防止 AI 不遵循引导），这样工作量和不确定就下去了。"

## 相关 commit

- `2907e42` hook JSON 合并：兜底（让 Claude Code 不报 hook error）
- `6d3de8e` event name 修复：兜底（让 launcher 返回正确 event）
- `6307724` plan consumes/produces：疏导（路径锁定）
- `4394791` handoff/executor 契约：疏导（步骤边界契约握手）
- `e97fb07` 用户视角命名：疏导（让用户不需要懂内部模块）

**总结**：每加一个机制，先问"能否疏导"，再问"是否要兜底"，最后问"两者能否合并"。
