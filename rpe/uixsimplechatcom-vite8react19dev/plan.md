# Plan

## Gate
- level: L2
- phase: B
- oracle_required: true
- meta_oracle_required: true

## Goal
goal: UI无人值守还原xsimplechat.com 初始化Vite8+React19项目骨架→启动dev server→token_bootstrap→orchestrator autopilot 5阶段(Tokens/Shell/Regions/Interactions/Polish)迭代到UIF-99≥0.99

## Four Factors
- Philosophy: 验证优先 + 零信任 + 守护优先
- Iron Rules: 范围冻结；证据门禁；危险操作审批
- ROI: low (score=-5; effort=17[scope=1+steps=5*2+L2], risk=high→8)
- Current State: must be supported by research.md evidence

## Classification
- task_id: UIxsimplechatcom-Vite8React19dev
- risk: high
- task_type: unknown
- doc_root: rpe/uixsimplechatcom-vite8react19dev

## Scope
- UI无人值守还原xsimplechat.com

## Scope Freeze
- status: frozen
- change_policy: requires_user_confirmation_or_l2_review

## User Decisions
- <none>

## Steps

### A Cognition
- [ ] A.1: 确认目标、边界、约束与验收标准
  - scope: UI无人值守还原xsimplechat.com
  - verify: file:research.md contains goal, boundaries, constraints, acceptance criteria
  - risk: scope_drift

### B Plan
- [ ] B.1: 冻结方案、scope 与 step 状态机
  - scope: UI无人值守还原xsimplechat.com
  - verify: file:plan.md contains Gate, Four Factors, Scope, Steps
  - risk: plan_drift

### C Review
- [ ] C.1: 完成方案审核
  - scope: UI无人值守还原xsimplechat.com
  - verify: file:oracle-verdicts.md contains ACCEPT or ADVISORY
  - risk: review_required
  - oracle: plan_review

### D Execute
- [ ] D.1: 实施核心变更
  - scope: UI无人值守还原xsimplechat.com
  - verify: assertion:实施核心变更
  - risk: high

### E Acceptance
- [ ] E.1: 完成验收与残余风险记录
  - scope: UI无人值守还原xsimplechat.com
  - verify: file:acceptance.md contains verification evidence and residual risks
  - risk: high
  - oracle: final_acceptance
