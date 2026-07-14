# Executor — human_check_feature

> RPE executor evidence ledger.  
> AI 只记录执行与证据，不做最终人工验收 verdict。

---

## Setup Evidence

```yaml
action: Initialize RPE package for CarrorOS original 10 goals human acceptance
files:
  - rpe/human_check_feature/prd.md
  - rpe/human_check_feature/research.md
  - rpe/human_check_feature/plan.md
  - rpe/human_check_feature/executor.md
  - rpe/human_check_feature/state/progress.md
status: PASS
notes:
  - PRD loaded
  - Research completed
  - Plan completed
  - Waiting for user confirmation before Phase 3 human acceptance execution
```

---

## Step RPE-A — Context / Compact / 文档恢复 / U 型注意力 / 工作流验收

```yaml
status: PENDING_USER_EXECUTION
acceptance_record:
  path_id: A
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
    - 大输出落盘或只保留 preview
    - handoff.md 包含 goal / next_action / evidence_refs
    - plan.md / executor.md / evidence 可恢复真实状态
    - 头部规则稳定，尾部状态实时
    - Verify 失败不能被 claim done 覆盖
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes:
```

---

## Step RPE-B — Goal / 无人模式 / Loop 硬化验收

```yaml
status: PENDING_USER_EXECUTION
acceptance_record:
  path_id: B
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
    - 初始目标不漂移
    - 非风险步骤自主执行
    - 卡点记录 blocked / skipped / hard-boundary
    - loop/stall/budget 触发保护
    - 最终报告列出完成、跳过、风险
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes:
```

---

## Step RPE-C — Flywheel / 自我学习验收

```yaml
status: PENDING_USER_EXECUTION
acceptance_record:
  path_id: C
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
    - 失败有 step/error/retry_count/timestamp
    - 同类失败能归类
    - claude-next 作为缓冲区
    - anti-patterns 沉淀具体经验
    - 下一次同类任务主动规避旧错
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes:
```

---

## Step RPE-D — L1/L2 分级与智能决策验收

```yaml
status: PENDING_USER_EXECUTION
acceptance_record:
  path_id: D
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
    - L1 快速轻量
    - L2 严谨有证据
    - 读文件/查状态/非破坏测试可自决
    - 删除/push/认证改口需要人工或硬边界
    - Oracle 调用有理由
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes:
```

---

## Step RPE-E — 双审判官与 Verify 优先级验收

```yaml
status: PENDING_USER_EXECUTION
acceptance_record:
  path_id: E
  run_id:
  start_time:
  end_time:
  human_goal:
  task_description:
  human_actions:
  ai_actions:
  expected_correct_behavior:
    - Oracle 和 Mate 有独立上下文
    - 分歧显式保留
    - Meta 不静默覆盖一方意见
    - Verify FAIL > Oracle ACCEPT
    - 分歧原因可复盘
  observed_correct_behavior:
  observed_wrong_behavior:
  evidence_files:
  commands_observed:
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes:
```

---

## Step RPE-F — 汇总人工判定报告

```yaml
status: PENDING_USER_EXECUTION
final_verdict_template:
  context_boom:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  compact_handoff:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  docs_recovery:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  flywheel_learning:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  l1_l2:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  u_shape_attention:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  unattended_goal_loop:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  workflow:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  intelligent_decision:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  dual_judge:
    status: HUMAN_TO_FILL
    evidence_level: HUMAN_TO_FILL
    confidence: HUMAN_TO_FILL
    notes:
  overall:
    rc2_base_ready: HUMAN_TO_FILL
    ga_behavioral_validation: HUMAN_TO_FILL
    ga_ready: HUMAN_TO_FILL
    reason:
    remaining_blockers:
```
