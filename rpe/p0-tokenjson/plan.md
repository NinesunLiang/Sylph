# Plan

## Gate
- level: L2
- phase: B
- oracle_required: true
- meta_oracle_required: true

## Goal
goal: P0稳定性修复: token.json状态死锁 + 共享写锁

## Four Factors
- Philosophy: 验证优先 + 零信任 + 守护优先
- Iron Rules: 范围冻结；证据门禁；危险操作审批
- ROI: low (score=-5; effort=17[scope=1+steps=5*2+L2], risk=high→8)
- Current State: must be supported by research.md evidence

## Classification
- task_id: P0-tokenjson
- risk: high
- task_type: unknown
- doc_root: rpe/p0-tokenjson

## Scope
- token.json

## Scope Freeze
- status: frozen
- change_policy: requires_user_confirmation_or_l2_review

## User Decisions
- <none>

## Steps

### A Cognition
- [ ] A.1: 确认目标、边界、约束与验收标准
  - scope: token.json
  - verify: file:research.md contains goal, boundaries, constraints, acceptance criteria
  - risk: scope_drift

### B Plan
- [ ] B.1: 冻结方案、scope 与 step 状态机
  - scope: token.json
  - verify: file:plan.md contains Gate, Four Factors, Scope, Steps
  - risk: plan_drift

### C Review
- [ ] C.1: 完成方案审核
  - scope: token.json
  - verify: file:oracle-verdicts.md contains ACCEPT or ADVISORY
  - risk: review_required
  - oracle: plan_review

### D Execute
- [ ] D.1: 实施核心变更
  - scope: token.json
  - verify: assertion:实施核心变更
  - risk: high

### E Acceptance
- [ ] E.1: 完成验收与残余风险记录
  - scope: token.json
  - verify: file:acceptance.md contains verification evidence and residual risks
  - risk: high
  - oracle: final_acceptance
