# Oracle 门禁 & Meta-Oracle

> 本 skill 不自行判断 Oracle 裁决结果。只做两件事：
> 1. **检查 pipeline.yaml 中的 gate status** — `approved` 或 `pending`
> 2. **通过 gate 命令让用户/外部裁决者更新 gate status**

## gate — Oracle 门禁裁决

`/lx-oma-orch gate <og-id> approve|reject [--reason "..."]`

- `approve`：门禁通过，允许阶段推进。更新 `oracle_gates[].status = approved`
- `reject`：门禁拒绝。更新 `oracle_gates[].status = rejected`

裁决逻辑由外部 Oracle 节点（`oracle_terminal.md`）完成，orch 只负责编排和状态维护。

## Meta-Oracle 最后守门（G2 触发）

当整个管线到达最终阶段（所有 Oracle gate 已 approved，dev 阶段 completed），触发 G2：

1. **触发时机**：`stages.dev = completed` + 所有 `oracle_gates[].status = approved`
2. **执行方式**：`bash .claude/scripts/meta-oracle-review.sh G2`
3. **门禁类型**：软门禁 — ACCEPT/ADVISORY/REJECT
4. **留痕**：`.omc/state/meta-oracle-verdicts.md`

> Meta-Oracle 消耗巨大（opus + 独立上下文），仅在管线最终完成时触发一次。
