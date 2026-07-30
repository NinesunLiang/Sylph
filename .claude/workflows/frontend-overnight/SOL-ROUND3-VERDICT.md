# Frontend-Overnight Workflow — Sol Round3 终审判决

> **Updated**: 2026-07-30 (After Grok 4.5 | Opus 5 | GPT-5.6 Sol Round3 Review)  
> **Previous Claim**: 13/13 Critical Gaps Fixed  
> **Sol Verdict**: **NO-GO** (Production Overnight 6h)  
> **Current Status**: Design Stage — P0 Blockers Must Be Fixed Before Execution

---

## Executive Summary

提交 GAP-FIX-REPORT.md 给三个顶级模型（Grok 4.5 | Opus 5 | GPT-5.6 Sol）终审后，收到一致的 **NO-GO** 判决。

### Sol 三模型共识
```yaml
design_direction: ACCEPT (架构方向正确)
execution_readiness: NO-GO (存在 P0 级阻断问题)
overnight_6h_claim: REJECTED (无人值守声明被驳回)

confirmed_sound:
  - Phase 分层设计
  - EMA 收敛状态机
  - Bounded task + file scope 方向
  - state_store 原子写

confirmed_broken:
  - Token 权限规则自相矛盾 (allow vs deny)
  - checkpoint 不是 rollback (无 candidate workspace)
  - D6/D7 测量缺失 (UIF-99 数学不可达)
  - Gate 信任边界错误 (worker 可自报 gate_results)
  - 时间语义错误 (monotonic 不可跨进程)
  - StrategyState.locked_until 使用 monotonic
  - orchestrator.tick() NameError (MAX_TOTAL_ITERATIONS 未导入)
```

---

## Round3 终审核心发现

### Grok 4.5 核心观点
> "这是一个'高级编排器设计草案'，还不是一个'可无人值守的 UI 高还原执行系统'。"

**四条硬不变量缺失**:
1. **可证明的写权限边界** — Token freeze 自相矛盾
2. **可证明的失败回滚** — checkpoint 只恢复状态，不回滚代码
3. **可证明的评分来源** — D6/D7 占 42% 权重但完全缺失
4. **可证明的跨进程恢复** — monotonic 时间不可持久化

### Opus 5 核心观点
> "D6 + D7 占 UIF-99 权重 42%，measurement producer 完全缺席。"

**测量–收敛–评分三角断裂**:
- D6 (TokenAlign 18%) + D7 (Interaction 24%) = 42% 权重无测量
- 诚实默认 0.0 → 最高 0.64，目标 0.99 数学不可达
- 虚假默认 1.0 → 分数虚高，评分变成 facade
- Gate 失败 → score=0.0 → EMA 误判 DIVERGING

### GPT-5.6 Sol 核心观点
> "上传的代码已经包含可以确定复现的 P0 问题。"

**确定性运行时错误**:
- `orchestrator.py:171` — `NameError: MAX_TOTAL_ITERATIONS not defined`
- `wall_clock_start` 用 monotonic 持久化 → checkpoint 恢复后时间错误
- Worker 可注入 `gate_results` → 控制平面污染

---

## P0 Blockers (Must Fix Before Any Execution)

### P0-1: Token Permission Rules — Self-Contradictory
**Problem**: `phase_rules.py` 同时 allow 和 prohibit `src/styles/tokens/source/**`

**Fix Required**: Token phase only writes proposals to `artifacts/`, never to production token source

### P0-2: Checkpoint Is Not Rollback — No Candidate Workspace
**Problem**: Gate fails → state rolls back, but code remains polluted

**Fix Required**: Implement candidate workspace (git worktree) isolation

### P0-3: D6/D7 Measurement Missing — UIF-99 Mathematically Unreachable
**Problem**: D6 (18%) + D7 (24%) = 42% weight, but no measurement producers

**Fix Required**: Implement `token_align_producer.py` + `interaction_assertion_runner.py`

### P0-4: Gate Trust Boundary — Worker Can Self-Report gate_results
**Problem**: `tick(action_result)` accepts `gate_results` from untrusted worker

**Fix Required**: Worker envelope validation, orchestrator-only gate execution

### P0-5: Time Semantics — monotonic Not Persistable Across Processes
**Problem**: `wall_clock_start` uses `time.monotonic()`, invalid after restart

**Fix Required**: Use UTC deadline, only use monotonic for in-process watchdog

### P0-6: orchestrator.tick() NameError — MAX_TOTAL_ITERATIONS Not Imported
**Problem**: Line 171 uses `MAX_TOTAL_ITERATIONS` but not imported

**Fix Required**: Add to imports from `.config`

### P0-7: Gate Failure → EMA DIVERGING — False Emergency Rollback
**Problem**: Gate fail → score=0.0 → EMA negative spike → false DIVERGING

**Fix Required**: Add `gates_passed` param, only feed EMA with valid samples

---

## What Was Actually Fixed (vs What Remains)

### ✅ Actually Fixed (9 items)
1. GAP 1: `_manifest_regions()` extracts from manifest.routes
2. GAP 2: `_run_gates()` implements C1-C8a chain
3. GAP 4: `time.monotonic()` consistency in status
4. GAP 5: `import yaml` moved to module top
5. GAP 6: Line count fix in `patch_validator.py`
6. GAP 8: Phase patterns deduplicated to `phase_rules.py`
7. GAP 9: Periodic checkpoint every 60s
8. GAP 12: DISCOVERY/TOKENS phase entry conditions
9. GAP 7 (partial): ConvergenceTracker serialization

### ❌ Not Fixed — P0 Blockers (7 items)
1. Token permission contradiction
2. No candidate workspace isolation
3. D6/D7 measurement producers missing
4. Gate trust boundary violation
5. monotonic time persistence error
6. MAX_TOTAL_ITERATIONS NameError
7. Gate failure → EMA diverging

---

## Required Work Before Production

### Phase 1: P0 Blocker Fixes (2-3 days)
- [ ] Token freeze — artifacts-only write in TOKENS phase
- [ ] Candidate workspace — worktree isolation pattern
- [ ] D6 producer — token_align_producer.py (static analysis)
- [ ] D7 producer — interaction_assertion_runner.py (Playwright)
- [ ] Worker envelope — forbidden fields validation
- [ ] UTC budget — wall_clock_deadline_utc
- [ ] Import fix — MAX_TOTAL_ITERATIONS + CHECKPOINT_EVERY_SECONDS
- [ ] EMA fix — gates_passed parameter

### Phase 2: Contract Tests (1 day)
- [ ] test_token_source_denied_in_all_phases()
- [ ] test_gate_fail_does_not_mutate_main_tree()
- [ ] test_incomplete_d6_d7_sets_h2_false()
- [ ] test_budget_restores_from_utc_deadline()
- [ ] test_gate_failure_not_fed_to_ema()

---

## Sol Review Consensus

**Grok 4.5**: "终审 = NO-GO"  
**Opus 5**: "D6/D7 缺失导致 UIF-99 数学不可达"  
**GPT-5.6 Sol**: "连基础 dry-run 都不应放行"

---

## Revised Claims

### Before Sol (REJECTED)
✅ 13/13 Critical Gaps Fixed  
✅ Ready for Production

### After Sol (ACCURATE)
🟡 9/13 Implementation Gaps Fixed  
❌ 7 P0 Blockers Identified  
⏸️  Design Stage — NOT Ready for Execution

---

**Status**: Design Stage — P0 Blockers Must Be Fixed  
**Recommendation**: Fix P0 blockers before claiming "ready for execution"

详细终审报告见: `rpe/no-person-ui-archieve/plans/round3/{grok,opus,gpt}_final.md`

