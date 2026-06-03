# reconcile / verifier / resolve / propagate

## reconcile — 变更检测 + 冲突裁决

将 `master-prd.md` 与各 feature `prd.md` 比对：

| 级别 | 适用场景 | 处理 |
|------|---------|------|
| L1 | 新术语、注释、元数据 | 自动归并 |
| L2 | 新研究线索、可选需求 | 自动归并 |
| L3 | 改核心需求、推翻决策、修改已有对象 | 挂起 pending-decisions |

**L2→L3 自动升级**：若修改已有 `REQ-*`/`DEC-*`/`TERM-*` 或与已有决策矛盾。

**产出**：`CHG-YYYYMMDD-NNN` + `CONFLICT-NNN`（L3）+ 更新 `CONSOLIDATION-LOG.md` + L3 挂起写入 `state/pending-decisions.md`。

## verifier — 变更质量门禁

> 引用节点 `../../nodes/verifier.md`

reconcile 产出后、propagate 前运行：

```
1. 读 CONSOLIDATION-LOG.md → 提取所有 CHG-ID
2. 逐项校验：
   a. CHG-ID 格式 CHG-YYYYMMDD-NNN
   b. L3 必须涉及 REQ-/DEC-/TERM- 修改
   c. L3 有对应 CONFLICT-NNN 且已写入 pending-decisions.md
3. verifier 节点裁决 → verified/warning
```

产出：`state/verify-report.md` + `verified: true|false`

## resolve — L3 人工裁决

`/lx-oma-gov resolve <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason]`

更新 CONSOLIDATION-LOG.md + 移除 pending-decisions.md。

## propagate — 增量传播

- `--dry-run`：预览
- `--execute`：实际写入（v2 计划）

**幂等**：每条 CHG-ID 写入 `sync-notes.md`，重复执行跳过已有 ID。
