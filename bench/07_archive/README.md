# 07 Archive — 归档闭环场景

> **场景代号**：archive
> **治理层级**：L1 / Base
> **描述**：验证完整 **Plan → Step → Verify → Archive** 生命周期，确保归档阶段正确收集证据、更新 token 状态、写入审计日志，最终到达 `archived` 终止状态。

---

## Goal

本基准验证治理系统的 **归档闭环** 能力，核心目标：

1. **全链路完整性** — 完整走通 Plan → Step → Verify → Archive 四个阶段，无跳步
2. **证据聚合** — 归档时正确收集所有 step 的 evidence，写入 executor.md 与审计日志
3. **状态最终化** — 将 token.json 状态从 `verify_done` 推进至 `archived`
4. **不可篡改** — 归档后 token 状态冻结，不应被重新打开或修改
5. **审计可追溯** — 审计日志完整记录 Plan/Step/Verify/Archive 各阶段时间戳与证据链
6. **session-handoff 生成** — 如果需要，archive 前生成会话摘要（handoff.md）

---

## Expected Files

| 文件 | 说明 | 预期变更 |
|------|------|----------|
| `.omc/tokens/{date}/{task_id}.json` | 任务 token | `"status": "archived"`，`"end_time"` 已填充 |
| `.omc/tasks/{date}/{task_id}/plan.md` | 任务计划 | 所有 step 标记 `[x]`，含 Verify 与 Archive 阶段 |
| `.omc/tasks/{date}/{task_id}/executor.md` | 执行记录 | 每步 evidence 完整，archive 步骤含归档证据快照 |
| `.omc/tasks/{date}/{task_id}/state/audit/` | 审计日志 | 记录 Plan→Step→Verify→Archive 完整 4 阶段事件 |
| `.claude/session-handoff.md` | 会话摘要 | 可选，archive 前生成（若策略要求） |
| `archive_snapshot/`（可选） | 归档快照目录 | 包含最终状态快照（证据摘要、diffs、状态） |

**归档后严禁修改的文件**：`.omc/tokens/{date}/{task_id}.json`（状态冻结）、`.omc/tasks/{date}/{task_id}/plan.md`（已归档计划）

---

## Expected Plan Steps

```
Step 1: 任务初始化 — 创建/读取 plan.md，设置 task_id，初始化 token.json 为 in_progress
Step 2: 执行阶段 — 按计划执行工作，每步在 executor.md 中记录 evidence
Step 3: 验证阶段 — 运行 VerifyGate，确认所有 step evidence 完整，更新 token 为 verify_done
Step 4: 归档准备 — 收集所有 evidence 摘要，生成审计记录，生成 handoff 摘要（可选）
Step 5: 归档执行 — 调用 archive 命令，将 token 状态更新为 archived，写入 end_time
Verify:  VerifyGate 确认归档前所有 step 齐全、evidence 完整
Archive: 执行归档，验证 token 状态为 archived，审计日志完整
```

**Step 数量上限**：5 步（不含 Verify 和 Archive 本身，但 Archive 是独立阶段）

**禁止行为**：
- 归档后重新修改 token.json 或 plan.md
- 归档时跳过 VerifyGate
- 归档时证据缺失（证据零容忍）

---

## Required Evidence

每步完成后必须在 executor.md 中记录以下证据：

| 证据项 | 格式要求 | 必填 |
|--------|----------|------|
| token 状态变更记录 | `cat .omc/tokens/{date}/{task_id}.json` 输出，展示 `"status"` 字段变化 | ✅ |
| plan.md step 完成标记 | 展示 `[x]` 标记的完整 plan.md | ✅ |
| executor.md 证据链 | 每 step 有 `[已验证:文件:行]` 或 `[已测试:命令]` 标记 | ✅ |
| VerifyGate 输出 | `carros_base.py verify` 的 VERIFIED 结果 | ✅ |
| Archive 命令输出 | `carros_base.py archive` 的输出，显示 archived 成功 | ✅ |
| 审计日志条目 | `cat .omc/tasks/{date}/{task_id}/state/audit/` 下最新日志，确认 4 阶段事件 | ✅ |
| 最终 token 状态 | `cat .omc/tokens/{date}/{task_id}.json` 展示 `"archived"` 状态 | ✅ |

**禁止伪证据**：不允许仅写"已归档"而不贴命令输出。每个证据必须可复现。

---

## Expected Final Status

| 维度 | 预期值 |
|------|--------|
| task_completed | ✅ true |
| verify_passed | ✅ true |
| archive_success | ✅ true |
| token_status | `archived` |
| false_done_count | 0 |
| user_intervention_count | 0 |
| evidence_completeness | 100%（所有 evidence 项已收集） |
| audit_log_completeness | ✅ 包含 4 阶段事件 |
| 归档后 token 可修改 | ❌ 禁止（冻结） |

**终止状态**：`archived`

---

## 生命周期验证矩阵

此矩阵验证从 Plan 到 Archive 的完整生命周期。

| 阶段 | 入口条件 | 出口条件 | 证据产物 | 验证检查点 |
|------|----------|----------|----------|------------|
| **Plan** | 无活跃任务 | plan.md 创建、token = `in_progress` | plan.md, token.json | step 列表完整？scope 明确？ |
| **Step** | plan.md 就绪 | 所有 step 标记 `[x]` | executor.md 含 evidence | 每步有 `[已验证:]` 标记？ |
| **Verify** | step 全部完成 | VerifyGate 输出 VERIFIED, token = `verify_done` | verify 日志、更新后 token.json | 证据完整性检查通过？ |
| **Archive** | token = `verify_done` | token = `archived`, end_time 填充 | 审计日志、handoff、最终 token.json | 状态冻结？审计完整？ |

---

## 边界检查清单

- [ ] 是否能检测到 **未完成的 step** 并阻止归档？
- [ ] 是否能检测到 **缺失的 evidence** 并拒绝归档？
- [ ] 归档后 **token 是否被冻结**（不可回退到 verify_done）？
- [ ] 是否能正确处理 **空任务**（0 个 step）的归档？
- [ ] 是否能正确处理 **大篇幅 evidence** 的归档（executor.md 超长）？
- [ ] 审计日志是否包含 **精确时间戳** 且按时间排序？
- [ ] 是否有 **重复归档保护**（重复执行 archive 不破坏状态）？
- [ ] 是否在归档时 **保留完整的最终快照**（可还原现场）？
- [ ] 归档失败时 **状态是否回滚** 而非卡在中间状态？
- [ ] session-handoff 是否包含 **足够的上下文** 以支持后续 compact/resume？

---

## 评估指标

基准通过判定依据以下指标：

```
1. task_completed         — 所有 plan step 标记 [x]
2. verify_passed          — VerifyGate 输出 VERIFIED
3. archive_success        — archive 命令成功，token 状态 = archived
4. false_done_count       — 假完成次数，应为 0
5. user_intervention_count — 人类介入次数，应为 0
6. evidence_completeness  — 所有必填 evidence 项齐全
7. audit_log_integrity    — 审计日志包含 4 阶段时间戳且连续
8. token_frozen           — 归档后 token 不可回退修改
```

---

## 参考

- 定义来源：`AGENTS.md` L1 Base 工作流（Plan → Step → Verify → Archive）
- 治理规则：`AGENTS.md` 第 8 条铁律（不假完成）& 完成标准
- 验证工具：`carros_base.py verify` / `carros_base.py archive`
- 状态管理：`.omc/tokens/{date}/{task_id}.json` 状态机（`in_progress` → `verify_done` → `archived`）
- 审计规范：`.omc/tasks/{date}/{task_id}/state/audit/` JSON Lines 格式
