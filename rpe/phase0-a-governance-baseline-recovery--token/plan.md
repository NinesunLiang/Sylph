# Plan

## Gate
- level: L2
- phase: B
- oracle_required: true
- meta_oracle_required: true

## Goal
goal: Phase0-A: Governance Baseline Recovery — 恢复token状态、校准K1/K2/I1/J1分类、登记disabled hooks、处理worktree、补齐回归测试

## Four Factors
- Philosophy: 验证优先 + 零信任 + 守护优先
- Iron Rules: 范围冻结；证据门禁；危险操作审批
- ROI: low (score=-4; effort=16[scope=0+steps=5*2+L2], risk=high→8)
- Current State: must be supported by research.md evidence

## Classification
- task_id: Phase0-A-Governance-Baseline-Recovery--token
- risk: high
- task_type: code
- doc_root: rpe/phase0-a-governance-baseline-recovery--token

## Scope
- <pending-user-confirmation>

## Scope Freeze
- status: frozen
- change_policy: requires_user_confirmation_or_l2_review

## User Decisions
- <none>

## Steps

### A Cognition
- [ ] A.1: 确认目标、边界、约束与验收标准
  - scope: <discovery-required>
  - verify: file:research.md contains goal, boundaries, constraints, acceptance criteria
  - risk: scope_drift

### B Plan
- [ ] B.1: 冻结方案、scope 与 step 状态机
  - scope: <discovery-required>
  - verify: file:plan.md contains Gate, Four Factors, Scope, Steps
  - risk: plan_drift

### C Review
- [ ] C.1: 完成方案审核
  - scope: <discovery-required>
  - verify: file:oracle-verdicts.md contains ACCEPT or ADVISORY
  - risk: review_required
  - oracle: plan_review

### D Execute
- [ ] D.1: 实施核心变更
  - scope: <discovery-required>
  - verify: command:<project test command>
  - verify: assertion:实施核心变更
  - risk: high

### E Acceptance
- [ ] E.1: 完成验收与残余风险记录
  - scope: <discovery-required>
  - verify: file:acceptance.md contains verification evidence and residual risks
  - risk: high
  - oracle: final_acceptance
