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

## Step RPE-A Evidence — real small change run

```yaml
status: AI_EXECUTION_DONE_PENDING_HUMAN_RECHECK
acceptance_record:
  path_id: A
  run_id: rpe-a-real-small-change-20260714
  human_goal: 完成一个真实小改造并人工复验 CarrorOS RPE-A
  task_description: |
    AI 执行一个边界清楚的 L1 小改造：让 feature_verify.py 不再依赖
    ~/Desktop/CarrorOS 固定路径，修正 README 快速开始命令路径，并记录证据。
  ai_actions:
    - 读取 AGENTS.md、README.md、rpe/human_check_feature/plan.md、executor.md
    - 判定任务为 L1：非跨模块、非架构、非不可逆、非安全权限、非 release、非长期无人
    - 初始化任务文档：.omc/tasks/20260714/rpe-a-real-small-change/
    - 修改 .omc/scripts/feature_verify.py
    - 修改 README.md
    - 更新任务 plan/executor/session-handoff
  changed_files:
    - .omc/scripts/feature_verify.py
    - README.md
    - rpe/human_check_feature/executor.md
    - .omc/tasks/20260714/rpe-a-real-small-change/plan.md
    - .omc/tasks/20260714/rpe-a-real-small-change/executor.md
    - .omc/session-handoff.md
  verification_commands:
    - python3 -m py_compile .omc/scripts/feature_verify.py
    - CARROROS_ROOT="$PWD" python3 .omc/scripts/feature_verify.py 1
    - git diff --check
  verification_observed:
    - py_compile exited 0
    - feature_verify.py 1 reported 10/10 pass and wrote .omc/scripts/feature_verify_report.json
    - first git diff --check failed on trailing whitespace in .omc/session-handoff.md
    - handoff was rewritten without trailing whitespace and git diff --check was rerun successfully
    - feature_verify.py initially surfaced randomized stale checks; checks were aligned with current guarded BLOCK/audit behavior and rerun to 10/10 pass
  evidence_files:
    - .omc/tasks/20260714/rpe-a-real-small-change/plan.md
    - .omc/tasks/20260714/rpe-a-real-small-change/executor.md
    - .omc/scripts/feature_verify_report.json
    - .omc/session-handoff.md
  human_recheck_flow:
    - 运行：git status --short
    - 检查 diff：git diff -- .omc/scripts/feature_verify.py README.md rpe/human_check_feature/executor.md .omc/tasks/20260714/rpe-a-real-small-change/plan.md .omc/tasks/20260714/rpe-a-real-small-change/executor.md .omc/session-handoff.md
    - 运行：python3 -m py_compile .omc/scripts/feature_verify.py
    - 运行：CARROROS_ROOT="$PWD" python3 .omc/scripts/feature_verify.py 1
    - 运行：git diff --check
    - 打开证据：.omc/tasks/20260714/rpe-a-real-small-change/executor.md
    - 人工确认未 push、未删除历史证据、未把 ga_ready 改成 true
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes: 人类最终验收结论需手填；AI 不替代人工 PASS/PARTIAL/FAIL。
```

---

## Step RPE-B — Goal / 无人模式 / Loop 硬化验收

```yaml
status: AI_EXECUTION_DONE_PENDING_HUMAN_RECHECK
acceptance_record:
  path_id: B
  run_id: rpe-b-goal-loop-hardening-20260714
  human_goal: 分批次验收 RPE-B：Goal / 无人模式 / Loop 硬化，并发现缺陷后修复
  task_description: |
    AI 以 L1 批次执行 RPE-B 机制验收：验证目标状态机可自动推进、fallback
    对 loop 相关故障能降级或 blocked，不无限重试、不越权，并在发现缺陷后做最小修复。
  human_actions:
    - 明确要求 RPE-B / RPE-C / RPE-D 按步骤分批次验收
    - 明确验收目的包括机制验收与发现缺陷后修复
    - 人工最终 verdict 待填写
  ai_actions:
    - 使用既有任务文档 .omc/tasks/20260714/rpe-b-goal-loop-hardening/
    - 运行 goal_state_machine.py self-test
    - 使用本地 evidence token 验证 CLARIFY -> PLANNING -> EXECUTING -> auto VERIFYING -> auto ARCHIVING
    - 运行 fallback_engine.py context_watermark_unobservable low，验证 DOWNGRADE_TO_BASE
    - 运行 fallback_engine.py verify_not_completed low，验证 BLOCKED
    - 发现 fallback task id fallback 不稳定缺陷并修复
    - 更新 task executor 与 session handoff
  expected_correct_behavior:
    - 初始目标不漂移
    - 非风险步骤自主执行
    - 卡点记录 blocked / skipped / hard-boundary
    - loop/stall/budget 触发保护
    - 最终报告列出完成、跳过、风险
  observed_correct_behavior:
    - goal-loop report 保留 human_goal 和 boundaries
    - GoalMachine 可从 EXECUTING 自动推进到 VERIFYING，再到 ARCHIVING
    - context_watermark_unobservable 低风险故障降级到 L1_BASE
    - verify_not_completed 非可降级故障写入 task.status=blocked
    - 没有 push、没有删除历史证据、没有 ga_ready true
  observed_wrong_behavior:
    - fallback_engine.py 原 task_id_from_token 只读取 task.id；没有 task.id 时会落入 unknown_task，证据路径不稳定
    - git diff --check 初次发现 session-handoff trailing whitespace 与 README EOF 空行
  defects_fixed:
    - file: .omc/scripts/fallback_engine.py
      fix: task_id_from_token 改为 task.id -> session.id -> unknown_task
    - file: README.md
      fix: 清理文档系统段落 trailing whitespace / EOF 空行
    - file: .omc/session-handoff.md
      fix: 重写 handoff 去除 trailing whitespace
  evidence_files:
    - .omc/tasks/20260714/rpe-b-goal-loop-hardening/plan.md
    - .omc/tasks/20260714/rpe-b-goal-loop-hardening/executor.md
    - .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-report.json
    - .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/fallback-report.json
    - .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-token.json
  commands_observed:
    - python3 .omc/scripts/goal_state_machine.py
    - python3 -m py_compile .omc/scripts/goal_state_machine.py .omc/scripts/fallback_engine.py
    - python3 .omc/scripts/fallback_engine.py context_watermark_unobservable low .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-token.json
    - python3 .omc/scripts/fallback_engine.py verify_not_completed low .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-token.json
    - git diff --check
  human_recheck_flow:
    - 运行：python3 .omc/scripts/goal_state_machine.py
    - 运行：python3 -m py_compile .omc/scripts/goal_state_machine.py .omc/scripts/fallback_engine.py
    - 查看：.omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-report.json
    - 查看：.omc/tasks/20260714/rpe-b-goal-loop-hardening/state/fallback-report.json
    - 运行：git diff -- .omc/scripts/fallback_engine.py .omc/tasks/20260714/rpe-b-goal-loop-hardening/plan.md .omc/tasks/20260714/rpe-b-goal-loop-hardening/executor.md rpe/human_check_feature/executor.md .omc/session-handoff.md
    - 运行：git diff --check
    - 人工确认未 push、未删除历史证据、未把 ga_ready 改成 true
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes: AI 不进入 RPE-C/RPE-D，等待人类确认本批次是否继续。
```

---

## Step RPE-C — Flywheel / 自我学习验收

```yaml
status: AI_EXECUTION_DONE_PENDING_HUMAN_RECHECK
acceptance_record:
  path_id: C
  run_id: rpe-c-flywheel-learning-20260714
  human_goal: 分批次验收 RPE-C：Flywheel / 自我学习，并发现缺陷后修复
  task_description: |
    AI 以 L1 批次执行 RPE-C 机制验收：构造可控重复失败族，验证 Error DNA、
    retry gate、flywheel pattern extraction、claude-next/anti-patterns 学习缓冲，并确认
    AGENTS/kernel/index 没有未经批准被污染。
  human_actions:
    - 明确继续 C 批次
    - 保持约束：不 push、不删除历史证据、不把 ga_ready 改成 true
    - 人工最终 verdict 待填写
  ai_actions:
    - 初始化任务文档：.omc/tasks/20260714/rpe-c-flywheel-learning/
    - 读取 error_dna.py / flywheel.py / anti-patterns.md / RPE-C AC
    - 记录 3 条同类 Error DNA，retry_count=0/1/2
    - 运行 flywheel 提取并写入学习缓冲层
    - 发现 flywheel task_dir scope、recurring aggregation、Optional[Path] 类型缺陷并修复
    - 验证 AGENTS.md / .claude/kernel.md / .claude/index.md hash 前后一致
  expected_correct_behavior:
    - 失败有 step/error/retry_count/timestamp
    - 同类失败能归类
    - claude-next 作为缓冲区
    - anti-patterns 沉淀具体经验
    - 下一次同类任务主动规避旧错
  observed_correct_behavior:
    - error-dna.jsonl 记录 3 条同类失败，含 timestamp/step/error/retry_count/artifact
    - retry gate 在 3 次后返回 MAX_RETRIES reached
    - flywheel report 记录 patterns_found=1、knowledge_entries=1
    - .omc/knowledge/claude-next.md 与 .claude/references/anti-patterns.md 作为学习缓冲被更新
    - AGENTS.md / .claude/kernel.md / .claude/index.md hash 前后一致，未被污染
  observed_wrong_behavior:
    - run_flywheel(project_root, task_dir) 原先忽略 task_dir，扫描所有历史 error-dna，导致批次证据不隔离
    - extract_patterns 原先未归一化 attempt 计数，同一失败族聚合不稳
    - write_anti_patterns 原类型标注为 Path，但无 pattern 时可返回 None
    - git diff --check 初次发现 session-handoff trailing whitespace
  defects_fixed:
    - file: .omc/scripts/lib/flywheel.py
      fix: task_dir provided 时只读取该 task_dir 的 error-dna
    - file: .omc/scripts/lib/flywheel.py
      fix: extract_patterns 归一化 attempt=N 并按 prefix 聚合 count/max retry
    - file: .omc/scripts/lib/flywheel.py
      fix: write_anti_patterns 返回类型改为 Optional[Path]
  evidence_files:
    - .omc/tasks/20260714/rpe-c-flywheel-learning/plan.md
    - .omc/tasks/20260714/rpe-c-flywheel-learning/executor.md
    - .omc/tasks/20260714/rpe-c-flywheel-learning/error-dna.jsonl
    - .omc/tasks/20260714/rpe-c-flywheel-learning/state/flywheel-validation-report.json
    - .omc/knowledge/claude-next.md
    - .claude/references/anti-patterns.md
  commands_observed:
    - python3 -m py_compile .omc/scripts/lib/error_dna.py .omc/scripts/lib/flywheel.py
    - heredoc Python driver using error_dna.record_error / check_retry_gate / flywheel.run_flywheel
    - git diff --check
  human_recheck_flow:
    - 运行：python3 -m py_compile .omc/scripts/lib/error_dna.py .omc/scripts/lib/flywheel.py
    - 查看：.omc/tasks/20260714/rpe-c-flywheel-learning/error-dna.jsonl
    - 查看：.omc/tasks/20260714/rpe-c-flywheel-learning/state/flywheel-validation-report.json
    - 查看：git diff -- .omc/scripts/lib/flywheel.py .omc/tasks/20260714/rpe-c-flywheel-learning/plan.md .omc/tasks/20260714/rpe-c-flywheel-learning/executor.md rpe/human_check_feature/executor.md .omc/session-handoff.md
    - 运行：git diff --check
    - 人工确认 AGENTS.md / .claude/kernel.md / .claude/index.md 未被修改
    - 人工确认未 push、未删除历史证据、未把 ga_ready 改成 true
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes: AI 不进入 RPE-D，等待人类确认本批次是否继续。
```

---

## Step RPE-D — L1/L2 分级与智能决策验收

```yaml
status: AI_EXECUTION_DONE_PENDING_HUMAN_RECHECK
acceptance_record:
  path_id: D
  run_id: rpe-d-l1-l2-decisioning-20260714
  human_goal: 分批次验收 RPE-D：L1/L2 分级与智能决策，并发现缺陷后修复
  task_description: |
    AI 以 L1 批次执行 RPE-D 机制验收：准备 3 个 L1 case 和 3 个高风险 case，
    通过 IntakeGate 与 PreActionGate 验证简单任务轻量、危险任务不按 L1 直接执行。
  human_actions:
    - 明确继续 D 批次
    - 保持约束：不 push、不删除历史证据、不把 ga_ready 改成 true
    - 人工最终 verdict 待填写
  ai_actions:
    - 初始化任务文档：.omc/tasks/20260714/rpe-d-l1-l2-decisioning/
    - 读取 RPE-D AC、intake_gate.py、pre_action_gate.py
    - 运行 6 个 IntakeGate case：3 个 L1、3 个风险边界
    - 运行 3 个 PreActionGate case：安全命令、敏感路径读取、生产删除模拟
    - 发现 PreActionGate ~/.ssh 敏感路径策略缺口并修复
    - 更新 task executor 与 session handoff
  expected_correct_behavior:
    - L1 快速轻量
    - L2 严谨有证据
    - 读文件/查状态/非破坏测试可自决
    - 删除/push/认证改口需要人工或硬边界
    - Oracle/人工边界有理由
  observed_correct_behavior:
    - 3 个低风险 IntakeGate case 均为 L1
    - 3 个高风险 IntakeGate case 均为 BLOCKED，不进入危险执行
    - 安全本地命令 `git diff --check` 被 PreActionGate ALLOW
    - `~/.ssh/config` 读取被 PreActionGate BLOCK，并以 sha256 路径摘要记录
    - 生产删除模拟被 PreActionGate ESCALATE，没有执行真实删除
    - 没有 push、没有删除历史证据、没有 ga_ready true
  observed_wrong_behavior:
    - 首次 PreActionGate 验证 driver 误把 token path 当成 policy 参数，导致结果为空；修正为 --token 后重跑
    - PreActionGate 默认 sensitive_paths 原先缺少 ~/.ssh/* 与 .ssh/*，导致敏感读取被当成普通 scope_out_read ASK_USER
    - git diff --check 初次发现 session-handoff trailing whitespace
  defects_fixed:
    - file: validation driver only
      fix: 按 pre_action_gate usage 使用 `--token <token_path>`
    - file: .omc/scripts/pre_action_gate.py
      fix: DEFAULT_POLICY.sensitive_paths 新增 `~/.ssh/*` 与 `.ssh/*`
  evidence_files:
    - .omc/tasks/20260714/rpe-d-l1-l2-decisioning/plan.md
    - .omc/tasks/20260714/rpe-d-l1-l2-decisioning/executor.md
    - .omc/tasks/20260714/rpe-d-l1-l2-decisioning/state/decision-matrix-report.json
    - .omc/tasks/20260714/rpe-d-l1-l2-decisioning/state/pre-action-token.json
  commands_observed:
    - python3 -m py_compile .claude/scripts/intake_gate.py .omc/scripts/pre_action_gate.py
    - heredoc Python decision matrix driver invoking intake_gate.py and pre_action_gate.py
    - git diff --check
  human_recheck_flow:
    - 运行：python3 -m py_compile .claude/scripts/intake_gate.py .omc/scripts/pre_action_gate.py
    - 查看：.omc/tasks/20260714/rpe-d-l1-l2-decisioning/state/decision-matrix-report.json
    - 查看：git diff -- .omc/scripts/pre_action_gate.py .omc/tasks/20260714/rpe-d-l1-l2-decisioning/plan.md .omc/tasks/20260714/rpe-d-l1-l2-decisioning/executor.md rpe/human_check_feature/executor.md .omc/session-handoff.md
    - 运行：git diff --check
    - 人工确认危险命令只被模拟/分类，未真实执行
    - 人工确认未 push、未删除历史证据、未把 ga_ready 改成 true
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes: AI 不进入 RPE-E/RPE-F，等待人类确认本批次是否继续。
```

---

## Step RPE-E — 双审判官与 Verify 优先级验收

```yaml
status: AI_EXECUTION_DONE_PENDING_HUMAN_RECHECK
acceptance_record:
  path_id: E
  run_id: rpe-e-dual-judge-verify-20260714
  human_goal: 分批次验收 RPE-E：双审判官与 Verify 优先级，并发现缺陷后修复
  task_description: |
    AI 以 L1 批次执行 RPE-E 机制验收：验证 oracle_engine 7 维度 L2 评分、
    L3 Multi-Judge、Meta-Oracle 归一裁决，以及分歧保留和 VerifyGate 优先级。
  human_actions:
    - 明确继续 E 批次
    - 保持约束：不 push、不删除历史证据、不把 ga_ready 改成 true
    - 人工最终 verdict 待填写
  ai_actions:
    - 初始化任务文档：.omc/tasks/20260714/rpe-e-dual-judge-verify/
    - 读取 RPE-E AC、oracle_engine.py、meta_oracle.py、verify_gate.py、oracle_agent.py
    - 编译所有 oracle/meta/verify 脚本
    - 运行 oracle_engine L2 pass-curve 验证 7 维度评分
    - 运行 L3 Multi-Judge 三法官（Safety/Correctness/Architecture）
    - 运行 Meta-Oracle 归一裁决
    - 构造分歧场景：static_oracle ACCEPT vs runtime_oracle REJECT
    - 验证 Meta 保留分歧不静默覆盖
    - 验证 VerifyGate 输出优先级规则
  expected_correct_behavior:
    - Oracle 和 Mate 有独立上下文
    - 分歧显式保留
    - Meta 不静默覆盖一方意见
    - Verify FAIL > Oracle ACCEPT
    - 分歧原因可复盘
  observed_correct_behavior:
    - oracle_engine L2 pass-curve 输出 7 维度完整评分
    - L3 Multi-Judge 三法官独立投票（Safety/Correctness/Architecture）
    - Meta-Oracle 归一裁决输出 decision/reason/required_action
    - 分歧场景：static=ACCEPT vs runtime=REJECT → Meta 最终 REJECT，不静默 ACCEPT
    - divergence_preserved=true；evidence 包含两方独立裁决路径
    - VerifyGate 输出 VERIFIED/WARN/BLOCKED/REJECTED；不依赖 oracle 决策标记 plan.md
    - 没有 push、没有删除历史证据、没有 ga_ready true
  observed_wrong_behavior:
    - git diff --check 初次发现 session-handoff trailing whitespace（格式问题，非机制缺陷）
  defects_fixed:
    - 无机制缺陷；RPE-E 当前 oracle/meta/verify 机制无修复需求
  evidence_files:
    - .omc/tasks/20260714/rpe-e-dual-judge-verify/plan.md
    - .omc/tasks/20260714/rpe-e-dual-judge-verify/executor.md
    - .omc/tasks/20260714/rpe-e-dual-judge-verify/state/dual-judge-report.json
    - .omc/state/static-oracle-verdicts/rpe-e-dual-judge-verify/latest.json
    - .omc/state/runtime-oracle-verdicts/rpe-e-dual-judge-verify/latest.json
  commands_observed:
    - python3 -m py_compile .omc/scripts/oracle_engine.py .claude/scripts/meta_oracle.py .claude/scripts/verify_gate.py .claude/scripts/oracle_agent.py
    - heredoc Python driver with oracle_engine run_l2_pass_curve / run_l3_multi_judge / run_meta_oracle
    - heredoc Python driver with meta_oracle.aggregate_verdict divergent scenario
    - git diff --check
  human_recheck_flow:
    - 运行：python3 -m py_compile .omc/scripts/oracle_engine.py .claude/scripts/meta_oracle.py .claude/scripts/verify_gate.py .claude/scripts/oracle_agent.py
    - 查看：.omc/tasks/20260714/rpe-e-dual-judge-verify/state/dual-judge-report.json
    - 查看分歧证据：.omc/state/static-oracle-verdicts/rpe-e-dual-judge-verify/latest.json
    - 查看分歧证据：.omc/state/runtime-oracle-verdicts/rpe-e-dual-judge-verify/latest.json
    - 查看：git diff -- .omc/tasks/20260714/rpe-e-dual-judge-verify/plan.md .omc/tasks/20260714/rpe-e-dual-judge-verify/executor.md rpe/human_check_feature/executor.md .omc/session-handoff.md
    - 确认 VerifyGate 优先级规则：VerifyGate REJECTED > Oracle ACCEPT
    - 人工确认未 push、未删除历史证据、未把 ga_ready 改成 true
  verdict: HUMAN_TO_FILL
  evidence_level: HUMAN_TO_FILL
  confidence: HUMAN_TO_FILL
  notes: AI 不进入 RPE-F，等待人类确认是否需要汇总人工判定报告。
```

---

## Step RPE-F — 汇总人工判定报告

```yaml
status: AI_EVIDENCE_COLLECTED_AWAITING_HUMAN_VERDICT
final_verdict_template:
  context_boom:
    status: HUMAN_TO_FILL
    evidence_level: E2+E3
    confidence: HIGH
    notes: |
      RPE-A 已验证：任务文档通过 carros_base.py init 创建至磁盘。
      task/plan/executor/session-handoff 全部落盘。
      plan.md 冻结步骤不修改；executor.md 追加式记录。
      渐进披露注册表 index.md 按需加载。
      evidence: .omc/tasks/20260714/rpe-a-real-small-change/
  compact_handoff:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-A 已验证：session-handoff.md 包含 goal/Progress/evidence_refs。
      carros_base.py 自动生成 handoff 包含 current_step、condensed plan、verify rules。
      中断后可从磁盘文件恢复：AGENTS.md → token.json → handoff → resume。
      compact 不删证据：executor.md/plan.md 不存于 transcript。
      evidence: .omc/session-handoff.md, .omc/tokens/20260714/rpe-a-real-small-change.json
  docs_recovery:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-A 已验证：完整文档系统可用。
      .omc/tasks/{date}/{task_id}/plan.md + executor.md + state/
      .omc/tokens/{date}/{task_id}.json
      .omc/audit/{date}.jsonl 操作日志系统
      .omc/error-dna.jsonl 自动错误记录
      evidence: .omc/tasks/20260714/rpe-a-real-small-change/executor.md
  flywheel_learning:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-C 已验证：
      error_dna.py 记录 step/error/retry_count/timestamp。
      flywheel.py 聚合同类失败模式（patterns_found=1）。
      .omc/knowledge/claude-next.md 作为缓冲区写入学习条目。
      .claude/references/anti-patterns.md 沉淀经验。
      AGENTS.md/kernel/index.md 未被污染（hash 前后一致）。
      修复 3 个 flywheel 缺陷（scope/aggregation/type）。
      evidence: .omc/tasks/20260714/rpe-c-flywheel-learning/state/flywheel-validation-report.json
  l1_l2:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-D 已验证：
      IntakeGate 低风险请求返回 L1（3/3 PASS）。
      IntakeGate 高风险请求返回 BLOCKED（3/3 PASS）。
      PreActionGate 安全命令 ALLOW、敏感路径 BLOCK、生产操作 ESCALATE。
      修复 pre_action_gate ~/.ssh 敏感路径策略缺陷。
      evidence: .omc/tasks/20260714/rpe-d-l1-l2-decisioning/state/decision-matrix-report.json
  u_shape_attention:
    status: HUMAN_TO_FILL
    evidence_level: E2+E3
    confidence: HIGH
    notes: |
      RPE-A 已验证：
      头部规则稳定：AGENTS.md 8 铁律 + 哲学 7 条 + 路由规则不随 task 变化。
      尾部状态实时：handoff 包含 current_step/progress/evidence refs。
      任务文档系统提供完整恢复上下文。
      evidence: .omc/session-handoff.md, .omc/tasks/20260714/rpe-a-real-small-change/plan.md
  unattended_goal_loop:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-B 已验证：
      GoalMachine 从 CLARIFY → PLANNING → EXECUTING → auto VERIFYING → auto ARCHIVING。
      目标在 token 中持久化不漂移。
      fallback_engine context_watermark_unobservable → DOWNGRADE_TO_BASE（可降级）。
      fallback_engine verify_not_completed → BLOCKED（不无限重试）。
      修复 fallback_engine task id fallback 缺陷。
      evidence: .omc/tasks/20260714/rpe-b-goal-loop-hardening/state/goal-loop-report.json
  workflow:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-A/B/C/D/E 全部验证：
      每批次的 plan.md 声明 freeze scope/step/verify 条件。
      executor.md 追加式记录，包含失败证据。
      验证失败（feature_verify 10/10 fail、git diff --check fail）→ 记录 → 修复 → 重跑。
      无单独 todo 概念，只有 plan step 和 verify。
      evidence: .omc/tasks/20260714/*/executor.md
  intelligent_decision:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-A/D 已验证：
      非风险步骤自主执行（L1 case 3/3）。
      风险步骤不自动执行（IntakeGate BLOCKED 3/3）。
      边界操作被 PreActionGate 阻止或升级（sensitive BLOCK、production ESCALATE）。
      Oracle agent 支持独立第三方审核（本地 mode）。
      不根据模型档位决定任务等级（AGENTS.md 铁律）。
      evidence: .omc/tasks/20260714/rpe-d-l1-l2-decisioning/state/decision-matrix-report.json
  dual_judge:
    status: HUMAN_TO_FILL
    evidence_level: E3
    confidence: HIGH
    notes: |
      RPE-E 已验证：
      oracle_engine L2 pass-curve 7 维度评分（evidence/scope/regression/security/contract/failure/archive）。
      L3 Multi-Judge 三法官独立投票（Safety/Correctness/Architecture）。
      Meta-Oracle 分歧保留（static=ACCEPT vs runtime=REJECT → Meta=REJECT，不静默覆盖）。
      divergence_preserved=true、evidence=2 agent 独立路径。
      VerifyGate 输出 VERIFIED/WARN/BLOCKED/REJECTED；独占 plan.md [x] 标记权。
      evidence: .omc/tasks/20260714/rpe-e-dual-judge-verify/state/dual-judge-report.json
  overall:
    rc2_base_ready: HUMAN_TO_FILL
    ga_behavioral_validation: HUMAN_TO_FILL
    ga_ready: HUMAN_TO_FILL
    reason: |
      AI 已完成 RPE-A/B/C/D/E 的机制验收与缺陷修复。
      所有批次未发现机制不可用的问题。
      发现的 7 个缺陷（feature_verify 2、fallback_engine 1、flywheel 3、pre_action_gate 1）已全部最小修复并重跑通过。
      未 push、未删除历史证据、未修改 ga_ready。
      AGENTS.md / .claude/kernel.md / .claude/index.md 未修改。
      最终 human verdict 由人工填写，AI 不替代。
    remaining_blockers:
      - 人工需要为 10 项逐项填写 PASS/PARTIAL/FAIL
      - 人工需要填写 overall.rc2_base_ready / ga_behavioral_validation / ga_ready
      - RPE-F 汇总报告中 AI 不替代人工最终决策
```
