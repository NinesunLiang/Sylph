# shared(三方共用) 材料包

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb` | 生成: 2026-07-19 | 密钥已脱敏为 <REDACTED>
> 仓库级真相源;本机无 rg,验证引用搜索以 grep -rnE 等价实现

### TRACKED FILES

命令: `git ls-files`

```
.claude/.prompt-ring-state.json
.claude/claude-next.md
.claude/harness.yaml
.claude/hooks/carroros-night-deny.py
.claude/hooks/carroros_hooklib.py
.claude/hooks/hook-launcher.sh
.claude/hooks/posttool-gate.py
.claude/hooks/pretool-gate.py
.claude/hooks/pretool-user-approve.py
.claude/hooks/session-start.py
.claude/hooks/statusline-command.sh
.claude/hooks/stop-flywheel.py
.claude/index.md
.claude/kernel.md
.claude/mcp.json
.claude/nodes/.omc/state/hud-state.json
.claude/nodes/.omc/state/hud-stdin-cache.json
.claude/nodes/README.md
.claude/nodes/a_terminal.md
.claude/nodes/auto_fixer.md
.claude/nodes/b_terminal.md
.claude/nodes/behavior_rules.md
.claude/nodes/context_collector.md
.claude/nodes/decisions/conflict-resolution.md
.claude/nodes/decisions/danger-escalation.md
.claude/nodes/decisions/stage-gate.md
.claude/nodes/execute_node.md
.claude/nodes/explore.md
.claude/nodes/gate_checker.md
.claude/nodes/generator.md
.claude/nodes/interactive_prompt.md
.claude/nodes/judgments/hard-boundary-check.md
.claude/nodes/judgments/mece-verify.md
.claude/nodes/judgments/quality-gate.md
.claude/nodes/mode_selector.md
.claude/nodes/oracle_terminal.md
.claude/nodes/orchestrator.md
.claude/nodes/report_generator.md
.claude/nodes/scanner.md
.claude/nodes/target_resolver.md
.claude/nodes/verifier.md
.claude/plans/carroros-skills-merge-plan.md
.claude/plans/pretool-gate-modularization-roi.md
.claude/profiles/base/harness.yaml
.claude/profiles/enhanced/append-to-claude.md
.claude/profiles/go/harness.yaml
.claude/profiles/merge-profile.sh
.claude/profiles/node/harness.yaml
.claude/profiles/python/harness.yaml
.claude/profiles/rust/harness.yaml
.claude/prompts/executor_micro.txt
.claude/references/SOUL.md
.claude/references/SUBAGENT.md
.claude/references/anti-patterns.md
.claude/references/context-watermark.md
.claude/references/design-docs/1.md
.claude/references/design-docs/10.md
.claude/references/design-docs/11-oracle-roadmap.md
.claude/references/design-docs/2.md
.claude/references/design-docs/3.md
.claude/references/design-docs/4.md
.claude/references/design-docs/5.md
.claude/references/design-docs/6.md
.claude/references/design-docs/7.md
.claude/references/design-docs/8.md
.claude/references/design-docs/9.md
.claude/references/design-docs/align_report.md
.claude/references/design-docs/data.md
.claude/references/design-docs/data_todo.md
.claude/references/design-docs/deepseek-ultra.md
.claude/references/design-docs/gap_analysis.md
.claude/references/design-docs/test.md
.claude/references/design-docs/update.md
".claude/references/design-docs/\346\200\273\347\273\223.md"
.claude/references/enhance/context-watermark.md
.claude/references/enhance/fallback-matrix.md
.claude/references/enhance/oracle-spec.md
.claude/references/fallback-matrix.md
.claude/references/feature-registry.yaml
.claude/references/gate-rules.yaml
.claude/references/invariants.md
.claude/references/meta_oracle.py
.claude/references/omc-path-conventions.md
.claude/references/oracle-dual-agent-refactor-v1.md
.claude/references/oracle-spec.md
.claude/references/oracle_agent.py
.claude/references/philosophy.md
.claude/references/session-handoff.md
.claude/references/skill-atomization-guide.md
.claude/references/task-profiles.yaml
.claude/references/templates/handoff-capsule.md
.claude/references/token.schema.json
.claude/references/working-set-template.yaml
.claude/rules/bash-style.md
.claude/rules/terminal-safety.md
.claude/schemas/README.md
.claude/schemas/atomic/context_summary.yaml
.claude/schemas/atomic/error_codes.yaml
.claude/schemas/atomic/finding.yaml
.claude/schemas/atomic/fix_record.yaml
.claude/schemas/atomic/gate_result.yaml
.claude/schemas/atomic/scan_report.yaml
.claude/schemas/atomic/scan_target.yaml
.claude/schemas/atomic/severity.yaml
.claude/schemas/atomic/verdict.yaml
.claude/schemas/contract/state_transitions.yaml
.claude/schemas/input/task_input.yaml
.claude/schemas/output/acceptance_report.yaml
.claude/schemas/output/gov_report.yaml
.claude/schemas/output/review_report.yaml
.claude/schemas/output/task_spec.yaml
.claude/schemas/registry.yaml
.claude/schemas/token.md
.claude/schemas/token.schema.json
.claude/scripts/.omc/state/model-oracle-verdicts/.lock
.claude/scripts/.omc/state/model-oracle-verdicts/test_debug/20260710T015045Z-model_runtime.json
.claude/scripts/.omc/state/model-oracle-verdicts/test_debug/latest.json
.claude/scripts/.omc/state/oracle-audit/test_debug/.lock
.claude/scripts/.omc/state/oracle-audit/test_debug/20260710T015045Z/model_runtime.json
.claude/scripts/ab_compare.py
.claude/scripts/archive_engine.py
.claude/scripts/capture_evidence.py
.claude/scripts/carros_base.py
.claude/scripts/carros_cost_report.py
.claude/scripts/carros_oracle_base.py
.claude/scripts/carros_utils.py
.claude/scripts/context_engine.py
.claude/scripts/context_watermark.py
.claude/scripts/deepseek_inject.py
.claude/scripts/executor_ledger.py
.claude/scripts/fallback_engine.py
.claude/scripts/fallback_matrix.py
.claude/scripts/formal_seal.py
.claude/scripts/ga_behavioral_validation.py
.claude/scripts/ga_observability.py
.claude/scripts/honesty_audit.py
.claude/scripts/intake_gate.py
.claude/scripts/lib/autonomy.py
.claude/scripts/lib/error_dna.py
.claude/scripts/lib/flywheel.py
.claude/scripts/lib/ga_observability_io.py
.claude/scripts/lib/ga_observability_metrics.py
.claude/scripts/lib/ga_observability_report.py
.claude/scripts/lib/handoff_writer.py
.claude/scripts/lib/hot_card.py
.claude/scripts/lib/oracle_gate_light.py
.claude/scripts/lib/phase3_oracle.py
.claude/scripts/lib/tool_store.py
.claude/scripts/lib/water_level.py
.claude/scripts/meta-oracle-review.py
.claude/scripts/meta_oracle.py
.claude/scripts/model_meta_oracle.py
.claude/scripts/model_oracle_adversarial_test.py
.claude/scripts/model_oracle_spawn.py
.claude/scripts/model_runtime_oracle.py
.claude/scripts/model_static_oracle.py
.claude/scripts/negative_tests.py
.claude/scripts/omc_lint.py
.claude/scripts/oracle_agent.py
.claude/scripts/oracle_engine.py
.claude/scripts/oracle_gate.py
.claude/scripts/oracle_spawn.py
.claude/scripts/output_compress.py
.claude/scripts/phase3_matrix_test.py
.claude/scripts/plan_builder.py
.claude/scripts/pre_action_gate.py
.claude/scripts/runtime_oracle_agent.py
.claude/scripts/runtime_verify.py
.claude/scripts/runtime_verify2.py
.claude/scripts/static_oracle_agent.py
.claude/scripts/statusline.py
.claude/scripts/task_state_tracker.py
.claude/scripts/temp-bypass.py
.claude/scripts/verify_gate.py
.claude/scripts/verify_tests.py
.claude/settings.json
.claude/skills/SKILLS.md
.claude/skills/TEMPLATE.md
.claude/skills/archived/lx-purify/SKILL.md
.claude/skills/archived/lx-purify/references/audit-cheatsheet.md
.claude/skills/archived/lx-race/SKILL.md
.claude/skills/archived/lx-race/references/coordination-flow.md
.claude/skills/archived/lx-race/references/cross-platform-arch.md
.claude/skills/archived/lx-race/references/worker-protocol.md
.claude/skills/archived/lx-sync/SKILL.md
.claude/skills/archived/lx-sync/scripts/sync_check.py
.claude/skills/lx-code-review/SKILL.md
.claude/skills/lx-code-review/references/auto-fix-templates.md
.claude/skills/lx-code-review/references/checklists/danger-signals.md
.claude/skills/lx-code-review/references/knowledge/review-rules.md
.claude/skills/lx-code-review/references/rules-catalog.md
.claude/skills/lx-code-review/scripts/subagent_reviewer.py
.claude/skills/lx-dogfood/SKILL.md
.claude/skills/lx-dogfood/references/feed-protocol.md
.claude/skills/lx-dogfood/references/structure-ecosystem.md
.claude/skills/lx-ghost/SKILL.md
.claude/skills/lx-ghost/references/ghost-oracle-audit.md
.claude/skills/lx-ghost/references/ghost-phase0.md
.claude/skills/lx-ghost/references/ghost-polling.md
.claude/skills/lx-ghost/scripts/lx-ghost.sh
.claude/skills/lx-git-check/SKILL.md
.claude/skills/lx-git-check/scripts/commit_convention.py
.claude/skills/lx-git-check/scripts/detect_project.py
.claude/skills/lx-git-check/scripts/get_changed_files.py
.claude/skills/lx-git-check/scripts/run_checks.py
.claude/skills/lx-git-check/scripts/validate_commits.py
.claude/skills/lx-goal/SKILL.md
.claude/skills/lx-goal/references/autonomous-execution.md
.claude/skills/lx-goal/references/exit-report.md
.claude/skills/lx-goal/references/phase0-activation.md
.claude/skills/lx-goal/scripts/lx-goal.py
.claude/skills/lx-goal/scripts/lx-goal.sh
.claude/skills/lx-learner/SKILL.md
.claude/skills/lx-learner/references/pattern_detection_guide.md
.claude/skills/lx-learner/references/phase-detect.md
.claude/skills/lx-learner/references/phase-document.md
.claude/skills/lx-learner/references/phase-propose.md
.claude/skills/lx-learner/references/phase-report.md
.claude/skills/lx-learner/scripts/extract_pattern.py
.claude/skills/lx-oma/SKILL.md
.claude/skills/lx-oma/gov/HUMAN-IN-THE-LOOP-GATE.md
.claude/skills/lx-oma/gov/governance-spec.md
.claude/skills/lx-oma/gov/state/sync-state.md
.claude/skills/lx-oma/references/gov/commands-audit.md
.claude/skills/lx-oma/references/gov/commands-reconcile.md
.claude/skills/lx-oma/references/gov/directory-structure.md
.claude/skills/lx-oma/references/gov/pipeline-integration.md
.claude/skills/lx-oma/references/hier/sub-prd-template.md
.claude/skills/lx-oma/references/hier/verification-gate.md
.claude/skills/lx-oma/references/orch/advance-flow.md
.claude/skills/lx-oma/references/orch/dev-management.md
.claude/skills/lx-oma/references/orch/interface-contract.md
.claude/skills/lx-oma/references/orch/manual-review.md
.claude/skills/lx-oma/references/orch/oracle-gate.md
.claude/skills/lx-oma/references/orch/status-panel.md
.claude/skills/lx-oma/references/split/delivery-report.md
.claude/skills/lx-oma/references/split/interface-verification.md
.claude/skills/lx-oma/references/split/mece-checklist.md
.claude/skills/lx-oma/references/split/scaffolding-template.md
.claude/skills/lx-oracle/SKILL.md
.claude/skills/lx-oracle/references/body-duo.md
.claude/skills/lx-oracle/references/body-runtime.md
.claude/skills/lx-oracle/references/body-static.md
.claude/skills/lx-oracle/references/principles.md
.claude/skills/lx-root-cause-analysis/CHANGELOG.md
.claude/skills/lx-root-cause-analysis/SKILL.md
.claude/skills/lx-root-cause-analysis/references/anti-patterns.md
.claude/skills/lx-root-cause-analysis/references/checklists/danger-signals.md
.claude/skills/lx-root-cause-analysis/references/confidence-scoring.md
.claude/skills/lx-root-cause-analysis/references/go-root-cause-patterns.md
.claude/skills/lx-root-cause-analysis/references/oracle-escalation.md
.claude/skills/lx-root-cause-analysis/references/phase-five-whys.md
.claude/skills/lx-root-cause-analysis/references/phase-fix-immunity.md
.claude/skills/lx-root-cause-analysis/references/rca-feedback-template.md
.claude/skills/lx-root-cause-analysis/references/repair-loop-rules.md
.claude/skills/lx-root-cause-analysis/references/templates/blocked.md
.claude/skills/lx-root-cause-analysis/references/templates/immunity-failed.md
.claude/skills/lx-root-cause-analysis/references/templates/normal-completion.md
.claude/skills/lx-root-cause-analysis/references/templates/not-applicable.md
.claude/skills/lx-root-cause-analysis/references/templates/oracle-consultation.md
.claude/skills/lx-root-cause-analysis/references/tool-output-rules.md
.claude/skills/lx-rpe/SKILL.md
.claude/skills/lx-rpe/executor.md
.claude/skills/lx-rpe/plan.md
.claude/skills/lx-rpe/prd.md
.claude/skills/lx-rpe/references/_archive/abort-conditions.md
.claude/skills/lx-rpe/references/_archive/context-retention.md
.claude/skills/lx-rpe/references/_archive/error-recovery-table.md
.claude/skills/lx-rpe/references/_archive/milestone-rules.md
.claude/skills/lx-rpe/references/_archive/phase-transition-rules.md
.claude/skills/lx-rpe/references/_archive/protocol-table.md
.claude/skills/lx-rpe/references/_archive/root-cause-protocol.md
.claude/skills/lx-rpe/references/_archive/skill-linkage-table.md
.claude/skills/lx-rpe/references/_archive/skill-mapping-table.md
.claude/skills/lx-rpe/references/_archive/templates/executor.md
.claude/skills/lx-rpe/references/_archive/templates/plan.md
.claude/skills/lx-rpe/references/_archive/templates/research.md
.claude/skills/lx-rpe/references/_archive/templates/templates/executor.md
.claude/skills/lx-rpe/references/_archive/templates/templates/plan.md
.claude/skills/lx-rpe/references/_archive/templates/templates/research.md
.claude/skills/lx-rpe/references/batch-accept-template.md
.claude/skills/lx-rpe/references/commit-convention.md
.claude/skills/lx-rpe/references/frontend-coding-rules.md
.claude/skills/lx-rpe/references/gate-checklist.md
.claude/skills/lx-rpe/references/go-coding-rules.md
.claude/skills/lx-rpe/references/progress-file-template.md
.claude/skills/lx-rpe/references/progress-panel-template.md
.claude/skills/lx-rpe/references/recovery-flow.md
.claude/skills/lx-rpe/references/rpe_main_loop.md
.claude/skills/lx-rpe/references/rpe_phases.md
.claude/skills/lx-rpe/references/security-scan-rules.md
.claude/skills/lx-rpe/research.md
.claude/skills/lx-rpe/scripts/build_and_test.py
.claude/skills/lx-rpe/scripts/extract_ac.py
.claude/skills/lx-rpe/scripts/git_commit.py
.claude/skills/lx-rpe/scripts/update_progress.py
.claude/skills/lx-rpe/state/progress.md
.claude/skills/lx-skillify/SKILL.md
.claude/skills/lx-skillify/references/phases-clarify-analyze-generate.md
.claude/skills/lx-skillify/references/phases-create-validate-register-report.md
.claude/skills/lx-skillify/references/reference_skill_selector.md
.claude/skills/lx-skillify/references/skill_generation_prompts.md
.claude/skills/lx-skillify/scripts/skillify_generator.py
.claude/skills/lx-skillify/scripts/verify_and_register.py
.claude/skills/lx-task-spec/SKILL.md
.claude/skills/lx-task-spec/references/ac-template.md
.claude/skills/lx-task-spec/references/execution-modes.md
.claude/skills/lx-task-spec/references/execution-types.md
.claude/skills/lx-task-spec/references/guided-interaction.md
.claude/skills/lx-task-spec/references/queue-format.md
.claude/skills/lx-task-spec/references/steps-capture-triage.md
.claude/skills/lx-task-spec/references/steps-close-review.md
.claude/skills/lx-task-spec/references/steps-execute-verify.md
.claude/skills/lx-task-spec/references/upgrade-protocol.md
.claude/skills/lx-validate-skill/SKILL.md
.claude/skills/lx-validate-skill/references/report-templates.md
.claude/skills/lx-validate-skill/scripts/carror_dashboard.py
.claude/skills/lx-validate-skill/scripts/check_progressive_disclosure.py
.claude/skills/lx-validate-skill/scripts/skill_trace_report.py
.claude/skills/lx-validate-skill/scripts/validate_skill.py
.claude/skills/lx-varlock/SKILL.md
.claude/skills/lx-varlock/scripts/varlock.py
.claude/skills/references/oma/decision-chain.md
.claude/skills/references/oma/degradation-escalation.md
.claude/skills/references/oma/degradation-strategies.md
.claude/skills/references/oma/direction-guide.md
.claude/skills/references/oma/error-codes.md
.claude/skills/references/oma/execution-workflow.md
.claude/skills/references/oma/observability.md
.claude/skills/references/oma/pipeline-contract.md
.claude/skills/references/oma/skill-chaining.md
.claude/skills/references/shared/error-recovery.md
.claude/skills/references/shared/frontmatter-standard.md
.claude/skills/references/shared/state-machine-patterns.md
.claude/skills/skill-dependencies.yaml
.claude/task_sys/context_guard.md
.claude/task_sys/loading_matrix.md
.claude/task_sys/mechanism_evals.md
.claude/task_sys/orchestrator.md
.claude/task_sys/task_fs.md
.claude/task_sys/templates/acceptance_report.md
.claude/task_sys/templates/alternatives_explored.md
.claude/task_sys/templates/criteria.md
.claude/task_sys/templates/executor.md
.claude/task_sys/templates/fallback_analysis.md
.claude/task_sys/templates/plan.md
.claude/task_sys/templates/summary.md
.claude/task_sys/templates/task_input.yaml
.claude/task_sys/unified_delivery_schema.md
.claude/workflows/frontend-overnight/README.md
.claude/workflows/frontend-overnight/SOP.md
.claude/workflows/frontend-overnight/intake.md
.claude/workflows/frontend-overnight/night-loop.md
.claude/workflows/frontend-overnight/phase0-checklist.md
.gitignore
.omc/metrics/runtime-verify/evidence.jsonl
.omc/metrics/runtime-verify/ga-behavioral-validation.json
.omc/metrics/runtime-verify/ga-bhv-01-long-session-observability.json
.omc/metrics/runtime-verify/ga-bhv-02-compact-l5-recovery.json
.omc/metrics/runtime-verify/ga-bhv-03-unattended-goal-failure-injection.json
.omc/metrics/runtime-verify/ga-bhv-04-flywheel-replay-promotion-rollback.json
.omc/metrics/runtime-verify/ga-bhv-05-decision-governance.json
.omc/metrics/runtime-verify/manifest.json
.omc/metrics/runtime-verify/sha256sums.txt
.omc/plans/2026-07-07/lx-goal-xsimple-adapter/executor.md
.omc/plans/2026-07-07/lx-goal-xsimple-adapter/progress.md
.omc/plans/2026-07-08/-4-1LevelL1_BASEL1-2Token-schemasteps/executor.md
.omc/plans/2026-07-08/-4-1LevelL1_BASEL1-2Token-schemasteps/plan.md
.omc/plans/2026-07-08/-4-1LevelL1_BASEL1-2Token-schemasteps/research.md
.omc/plans/2026-07-08/-4-1LevelL1_BASEL1-2Token-schemasteps/state.json
.omc/plans/2026-07-08/cap-alignment/progress.md
.omc/reference/SUBAGENT.md
.omc/reference/enhance/context-watermark.md
.omc/reference/enhance/fallback-matrix.md
.omc/reference/enhance/oracle-spec.md
.omc/reference/omc-path-conventions.md
.omc/reference/token.schema.json
.omc/review/main-sub-review-context.md
.omc/scripts/_temp_repair.py
.omc/scripts/archive_engine.py
.omc/scripts/carros_base.py
.omc/scripts/carros_utils.py
.omc/scripts/clarify_engine.py
.omc/scripts/context_watermark.py
.omc/scripts/fallback_engine.py
.omc/scripts/fallback_matrix.py
.omc/scripts/feature_verify.py
.omc/scripts/feature_verify_report.json
.omc/scripts/goal_state_machine.py
.omc/scripts/init-omc.sh
.omc/scripts/omc_lint.py
.omc/scripts/oracle_engine.py
.omc/scripts/oracle_gate.py
.omc/scripts/pre_action_gate.py
.omc/scripts/randomized_bench.py
.omc/scripts/sub_agent_executor.py
.omc/scripts/sub_agent_manager.py
.omc/scripts/sub_agent_recovery.py
.omc/scripts/task_planner.py
.omc/scripts/task_state_tracker.py
.omc/session-handoff.md
.omc/tasks/2026-07-06/unknown_task/executor.md
.omc/tasks/2026-07-06/unknown_task/state/session-handoff.md
.omc/tasks/2026-07-09/bench-01/executor.md
.omc/tasks/2026-07-09/bench-01/plan.md
.omc/tasks/2026-07-09/bench-01/research.md
.omc/tasks/2026-07-09/bench-01/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-01/state/task-state.json
.omc/tasks/2026-07-09/bench-02/executor.md
.omc/tasks/2026-07-09/bench-02/plan.md
.omc/tasks/2026-07-09/bench-02/research.md
.omc/tasks/2026-07-09/bench-02/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-02/state/task-state.json
.omc/tasks/2026-07-09/bench-03/executor.md
.omc/tasks/2026-07-09/bench-03/plan.md
.omc/tasks/2026-07-09/bench-03/research.md
.omc/tasks/2026-07-09/bench-03/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-03/state/task-state.json
.omc/tasks/2026-07-09/bench-04/executor.md
.omc/tasks/2026-07-09/bench-04/plan.md
.omc/tasks/2026-07-09/bench-04/research.md
.omc/tasks/2026-07-09/bench-04/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-04/state/task-state.json
.omc/tasks/2026-07-09/bench-05/executor.md
.omc/tasks/2026-07-09/bench-05/plan.md
.omc/tasks/2026-07-09/bench-05/research.md
.omc/tasks/2026-07-09/bench-05/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-05/state/task-state.json
.omc/tasks/2026-07-09/bench-06/executor.md
.omc/tasks/2026-07-09/bench-06/plan.md
.omc/tasks/2026-07-09/bench-06/research.md
.omc/tasks/2026-07-09/bench-06/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-06/state/task-state.json
.omc/tasks/2026-07-09/bench-07/executor.md
.omc/tasks/2026-07-09/bench-07/plan.md
.omc/tasks/2026-07-09/bench-07/research.md
.omc/tasks/2026-07-09/bench-07/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/bench-07/state/task-state.json
.omc/tasks/2026-07-09/smoke-test-01/executor.md
.omc/tasks/2026-07-09/smoke-test-01/plan.md
.omc/tasks/2026-07-09/smoke-test-01/research.md
.omc/tasks/2026-07-09/smoke-test-01/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/smoke-test-01/state/task-state.json
.omc/tasks/2026-07-09/verify-test/executor.md
.omc/tasks/2026-07-09/verify-test/plan.md
.omc/tasks/2026-07-09/verify-test/research.md
.omc/tasks/2026-07-09/verify-test/state/audit/2026-07-09.jsonl
.omc/tasks/2026-07-09/verify-test/state/task-state.json
.omc/tasks/20260707/bench-01/executor.md
.omc/tasks/20260707/bench-01/plan.md
.omc/tasks/20260707/bench-01/research.md
.omc/tasks/20260707/bench-01/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-01/state/task-state.json
.omc/tasks/20260707/bench-02/executor.md
.omc/tasks/20260707/bench-02/plan.md
.omc/tasks/20260707/bench-02/research.md
.omc/tasks/20260707/bench-02/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-02/state/task-state.json
.omc/tasks/20260707/bench-03/executor.md
.omc/tasks/20260707/bench-03/plan.md
.omc/tasks/20260707/bench-03/research.md
.omc/tasks/20260707/bench-03/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-03/state/task-state.json
.omc/tasks/20260707/bench-04/executor.md
.omc/tasks/20260707/bench-04/plan.md
.omc/tasks/20260707/bench-04/research.md
.omc/tasks/20260707/bench-04/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-04/state/task-state.json
.omc/tasks/20260707/bench-05/executor.md
.omc/tasks/20260707/bench-05/plan.md
.omc/tasks/20260707/bench-05/research.md
.omc/tasks/20260707/bench-05/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-05/state/task-state.json
.omc/tasks/20260707/bench-06/executor.md
.omc/tasks/20260707/bench-06/plan.md
.omc/tasks/20260707/bench-06/research.md
.omc/tasks/20260707/bench-06/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-06/state/task-state.json
.omc/tasks/20260707/bench-07/executor.md
.omc/tasks/20260707/bench-07/plan.md
.omc/tasks/20260707/bench-07/research.md
.omc/tasks/20260707/bench-07/state/audit/20260707.jsonl
.omc/tasks/20260707/bench-07/state/task-state.json
.omc/tasks/20260707/cap-test-001/executor.md
.omc/tasks/20260707/cap-test-001/plan.md
.omc/tasks/20260707/cap-test-001/research.md
.omc/tasks/20260707/cap-test-001/state/audit/20260707.jsonl
.omc/tasks/20260709/CarrorOS-vs-Sylph/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/final-report.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/plan.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/plan.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/research.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/format-report/_instruction_sent.txt
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/format-report/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/format-report/instruction.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/format-report/result.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S1/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S1/result.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S1/token.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S2/_prompt.txt
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S2/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S2/result.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S2/token.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S3/_prompt.txt
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S3/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S3/result.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/sub-S3/token.json
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/test-S1/_instruction_sent.txt
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/test-S1/executor.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/test-S1/instruction.md
.omc/tasks/20260709/CarrorOS-vs-Sylph/sub_task/test-S1/result.json
.omc/tasks/20260709/report-test/executor.md
.omc/tasks/20260709/report-test/final-report.md
.omc/tasks/20260709/report-test/plan.md
.omc/tasks/20260709/report-test/research.md
.omc/tasks/20260709/test-oracle-smoke/executor.md
.omc/tasks/20260709/test-oracle-smoke/plan.md
.omc/tasks/20260709/test-oracle-smoke/research.md
.omc/tasks/20260710/e2e_smoke_20260710/executor.md
.omc/tasks/20260710/e2e_smoke_20260710/plan.md
.omc/tasks/20260710/e2e_smoke_20260710/research.md
.omc/tasks/20260710/e2e_smoke_20260710/state/session-handoff.md
.omc/tasks/20260714/ga-behavioral-validation/executor.md
.omc/tasks/20260714/ga-behavioral-validation/plan.md
AGENTS.md
CHANGELOG.md
CLAUDE.md
README.md
UI/FINAL.md
UI/final/gpt.md
UI/final/grok.md
UI/final/opus.md
UI/gpt-5.6Sol.md
UI/grok-4.5.md
UI/kimi-k3.md
UI/opus-4.8.md
UI/round2/gpt-5.6Sol.md
UI/round2/grok-4.5.md
UI/round2/kimi-k3.md
UI/round2/opus.48.md
UI/round3/gpt-5.6Sol.md
UI/round3/grok.md
UI/round3/opus-4.8.md
UI/round4/gpt-5.6Sol.md
UI/round4/grok-4.5.md
UI/round4/opus-4.8.md
UI/round5/audit-closure-gpt-5.6Sol.md
UI/round5/audit-closure-grok-4.5.md
UI/round5/audit-closure-opus-4.8.md
UI/round5/audit-receipt-grok-4.5.md
UI/round5/audit-request.md
UI/round5/audit-rereview-grok-4.5.md
UI/round5/audit-response-gpt-5.6Sol.md
UI/round5/audit-response-grok-4.5.md
UI/round5/audit-response-opus-4.8.md
UI/round5/build-opus-package.py
UI/round5/gpt-5.6Sol.md
UI/round5/grok-ab-payloads.py
UI/round5/logs/grok-ab-payloads-20260718-post-sol.log
UI/round5/logs/grok-ab-payloads-20260718.log
UI/round5/logs/opus-p1-payloads-20260718-post-sol.log
UI/round5/logs/opus-p1-payloads-20260718.log
UI/round5/logs/preflight-nogo-rerun-20260718.log
UI/round5/logs/smoke-independent-rerun-20260718-post-opus.log
UI/round5/logs/smoke-independent-rerun-20260718-post-sol.log
UI/round5/logs/smoke-independent-rerun-20260718.log
UI/round5/logs/smoke-results-independent-post-sol.yaml
UI/round5/logs/smoke-results-self-post-sol.yaml
UI/round5/logs/smoke-self-20260718-post-opus.log
UI/round5/logs/smoke-self-20260718-post-sol.log
UI/round5/logs/sol-artifact-verify-20260718.log
UI/round5/logs/sol-p0-verify-20260718.log
UI/round5/opus-4.8.md
UI/round5/opus-4.8_response.md
UI/round5/opus-p1-payloads.py
UI/round5/opus-source-package.md
UI/round5/sol-artifact-verify.py
UI/round5/sol-p0-verify.py
VERSION
benchmark/README.md
benchmark/__init__.py
benchmark/ablation.py
benchmark/cc_runner.py
benchmark/ci-20260715-1425.log
benchmark/environment.py
benchmark/reporter.py
benchmark/reports/ai-analysis.md
benchmark/reports/first-ab-test-report.md
benchmark/repos/bench-test-app
benchmark/run-ci.sh
benchmark/runner.py
benchmark/schemas.py
benchmark/task_loader.py
benchmark/tasks/01_repo_locate/01_repo_locate_001.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_002.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_003.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_004.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_005.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_006.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_007.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_008.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_009.yaml
benchmark/tasks/01_repo_locate/01_repo_locate_010.yaml
benchmark/tasks/02_multi_file/02_multi_file_001.yaml
benchmark/tasks/02_multi_file/02_multi_file_002.yaml
benchmark/tasks/02_multi_file/02_multi_file_003.yaml
benchmark/tasks/02_multi_file/02_multi_file_004.yaml
benchmark/tasks/02_multi_file/02_multi_file_005.yaml
benchmark/tasks/02_multi_file/02_multi_file_006.yaml
benchmark/tasks/02_multi_file/02_multi_file_007.yaml
benchmark/tasks/02_multi_file/02_multi_file_008.yaml
benchmark/tasks/02_multi_file/02_multi_file_009.yaml
benchmark/tasks/02_multi_file/02_multi_file_010.yaml
benchmark/tasks/03_cross_module/03_cross_module_001.yaml
benchmark/tasks/03_cross_module/03_cross_module_002.yaml
benchmark/tasks/03_cross_module/03_cross_module_003.yaml
benchmark/tasks/03_cross_module/03_cross_module_004.yaml
benchmark/tasks/03_cross_module/03_cross_module_005.yaml
benchmark/tasks/03_cross_module/03_cross_module_006.yaml
benchmark/tasks/03_cross_module/03_cross_module_007.yaml
benchmark/tasks/03_cross_module/03_cross_module_008.yaml
benchmark/tasks/03_cross_module/03_cross_module_009.yaml
benchmark/tasks/03_cross_module/03_cross_module_010.yaml
benchmark/tasks/04_migration/04_migration_001.yaml
benchmark/tasks/04_migration/04_migration_002.yaml
benchmark/tasks/04_migration/04_migration_003.yaml
benchmark/tasks/04_migration/04_migration_004.yaml
benchmark/tasks/04_migration/04_migration_005.yaml
benchmark/tasks/04_migration/04_migration_006.yaml
benchmark/tasks/04_migration/04_migration_007.yaml
benchmark/tasks/04_migration/04_migration_008.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_001.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_002.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_003.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_004.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_005.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_006.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_007.yaml
benchmark/tasks/05_fuzzy_req/05_fuzzy_req_008.yaml
benchmark/tasks/06_test_fix/06_test_fix_001.yaml
benchmark/tasks/06_test_fix/06_test_fix_002.yaml
benchmark/tasks/06_test_fix/06_test_fix_003.yaml
benchmark/tasks/06_test_fix/06_test_fix_004.yaml
benchmark/tasks/06_test_fix/06_test_fix_005.yaml
benchmark/tasks/06_test_fix/06_test_fix_006.yaml
benchmark/tasks/06_test_fix/06_test_fix_007.yaml
benchmark/tasks/06_test_fix/06_test_fix_008.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_001.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_002.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_003.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_004.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_005.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_006.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_007.yaml
benchmark/tasks/07_perf_concur/07_perf_concur_008.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_001.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_002.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_003.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_004.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_005.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_006.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_007.yaml
benchmark/tasks/08_long_recovery/08_long_recovery_008.yaml
benchmark/tasks/09_high_risk/09_high_risk_001.yaml
benchmark/tasks/09_high_risk/09_high_risk_002.yaml
benchmark/tasks/09_high_risk/09_high_risk_003.yaml
benchmark/tasks/09_high_risk/09_high_risk_004.yaml
benchmark/tasks/09_high_risk/09_high_risk_005.yaml
benchmark/tasks/09_high_risk/09_high_risk_006.yaml
benchmark/tasks/09_high_risk/09_high_risk_007.yaml
benchmark/tasks/09_high_risk/09_high_risk_008.yaml
benchmark/tasks/10_adversarial/10_adversarial_001.yaml
benchmark/tasks/10_adversarial/10_adversarial_002.yaml
benchmark/tasks/10_adversarial/10_adversarial_003.yaml
benchmark/tasks/10_adversarial/10_adversarial_004.yaml
benchmark/tasks/10_adversarial/10_adversarial_005.yaml
benchmark/tasks/10_adversarial/10_adversarial_006.yaml
benchmark/tasks/10_adversarial/10_adversarial_007.yaml
benchmark/tasks/10_adversarial/10_adversarial_008.yaml
benchmark/verify/01_repo_locate_001.sh
benchmark/verify/01_repo_locate_002.sh
benchmark/verify/01_repo_locate_003.sh
benchmark/verify/01_repo_locate_004.sh
benchmark/verify/01_repo_locate_005.sh
benchmark/verify/01_repo_locate_006.sh
benchmark/verify/01_repo_locate_007.sh
benchmark/verify/01_repo_locate_008.sh
benchmark/verify/02_multi_file_001.sh
benchmark/verify/02_multi_file_002.sh
benchmark/verify/02_multi_file_003.sh
benchmark/verify/02_multi_file_004.sh
benchmark/verify/02_multi_file_005.sh
benchmark/verify/02_multi_file_006.sh
benchmark/verify/02_multi_file_007.sh
benchmark/verify/02_multi_file_008.sh
benchmark/verify/03_cross_module_001.sh
benchmark/verify/03_cross_module_002.sh
benchmark/verify/03_cross_module_003.sh
benchmark/verify/03_cross_module_004.sh
benchmark/verify/03_cross_module_005.sh
benchmark/verify/03_cross_module_006.sh
benchmark/verify/03_cross_module_007.sh
benchmark/verify/03_cross_module_008.sh
benchmark/verify/04_migration_001.sh
benchmark/verify/04_migration_002.sh
benchmark/verify/04_migration_003.sh
benchmark/verify/04_migration_004.sh
benchmark/verify/04_migration_005.sh
benchmark/verify/04_migration_006.sh
benchmark/verify/04_migration_007.sh
benchmark/verify/04_migration_008.sh
benchmark/verify/05_fuzzy_req_001.sh
benchmark/verify/05_fuzzy_req_002.sh
benchmark/verify/05_fuzzy_req_003.sh
benchmark/verify/05_fuzzy_req_004.sh
benchmark/verify/05_fuzzy_req_005.sh
benchmark/verify/05_fuzzy_req_006.sh
benchmark/verify/05_fuzzy_req_007.sh
benchmark/verify/05_fuzzy_req_008.sh
benchmark/verify/06_test_fix_001.sh
benchmark/verify/06_test_fix_002.sh
benchmark/verify/06_test_fix_003.sh
benchmark/verify/06_test_fix_004.sh
benchmark/verify/06_test_fix_005.sh
benchmark/verify/06_test_fix_006.sh
benchmark/verify/06_test_fix_007.sh
benchmark/verify/06_test_fix_008.sh
benchmark/verify/07_perf_concur_001.sh
benchmark/verify/07_perf_concur_002.sh
benchmark/verify/07_perf_concur_003.sh
benchmark/verify/07_perf_concur_004.sh
benchmark/verify/07_perf_concur_005.sh
benchmark/verify/07_perf_concur_006.sh
benchmark/verify/07_perf_concur_007.sh
benchmark/verify/07_perf_concur_008.sh
benchmark/verify/08_long_recovery_001.sh
benchmark/verify/08_long_recovery_002.sh
benchmark/verify/08_long_recovery_003.sh
benchmark/verify/08_long_recovery_004.sh
benchmark/verify/08_long_recovery_005.sh
benchmark/verify/08_long_recovery_006.sh
benchmark/verify/08_long_recovery_007.sh
benchmark/verify/08_long_recovery_008.sh
benchmark/verify/09_high_risk_001.sh
benchmark/verify/09_high_risk_002.sh
benchmark/verify/09_high_risk_003.sh
benchmark/verify/09_high_risk_004.sh
benchmark/verify/09_high_risk_005.sh
benchmark/verify/09_high_risk_006.sh
benchmark/verify/09_high_risk_007.sh
benchmark/verify/09_high_risk_008.sh
benchmark/verify/10_adversarial_001.sh
benchmark/verify/10_adversarial_002.sh
benchmark/verify/10_adversarial_003.sh
benchmark/verify/10_adversarial_004.sh
benchmark/verify/10_adversarial_005.sh
benchmark/verify/10_adversarial_006.sh
benchmark/verify/10_adversarial_007.sh
benchmark/verify/10_adversarial_008.sh
benchmark/verify/verify_api_error.sh
benchmark/verify/verify_cache_ttl.sh
benchmark/verify/verify_calc_divide.sh
benchmark/verify/verify_calc_factorial.sh
benchmark/verify/verify_calc_power.sh
benchmark/verify/verify_middleware_logger.sh
benchmark/verify/verify_processor_validation.sh
benchmark/verify/verify_stats_empty.sh
docs/INDEX.yaml
docs/carros/reviews/improve_plan/bobi-adopted-plan-v2.md
docs/carros/reviews/improve_plan/bobi-adopted-plan.md
docs/carros/reviews/improve_plan/bobi-phase0.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index1.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index2.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index3.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index4.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index5.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index6.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index7.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/index8.md
docs/carros/reviews/improve_plan/gpt-5.6-sol/supplement.md
docs/carros/reviews/improve_plan/grok-4.5.md
docs/carros/reviews/improve_plan/opus-4.8/index1.md
docs/carros/reviews/improve_plan/opus-4.8/index10.md
docs/carros/reviews/improve_plan/opus-4.8/index2.md
docs/carros/reviews/improve_plan/opus-4.8/index3.md
docs/carros/reviews/improve_plan/opus-4.8/index4.md
docs/carros/reviews/improve_plan/opus-4.8/index5.md
docs/carros/reviews/improve_plan/opus-4.8/index6.md
docs/carros/reviews/improve_plan/opus-4.8/index7.md
docs/carros/reviews/improve_plan/opus-4.8/index8.md
docs/carros/reviews/improve_plan/opus-4.8/index9.md
docs/carros/reviews/improve_plan/reviews/gpt-4.8.md
docs/carros/reviews/improve_plan/reviews/grok-4.5.md
docs/carros/reviews/improve_plan/reviews/opus-4.8.md
docs/carros/runbooks/composition.md
improve_plan/bobi-adopted-plan-v2.md
improve_plan/bobi-adopted-plan.md
improve_plan/bobi-phase0.md
improve_plan/final_round/00-final-alignment.md
improve_plan/final_round/README.md
improve_plan/final_round/acceptance-identity.yaml
improve_plan/final_round/gpt-5.6Sol.md
improve_plan/final_round/grok-4.5.md
improve_plan/final_round/h-cas-stale-evidence-template.json
improve_plan/final_round/opus-4.8.md
improve_plan/final_round/rc2-formal-seal-manifest.json
improve_plan/final_round/remaining-ga-gates.md
improve_plan/mvp_version_todo/gpt-5.6Sol.md
improve_plan/mvp_version_todo/grok-4.5.md
improve_plan/mvp_version_todo/opus-4.8.md
improve_plan/nvidia-sana-m5-deployment-plan.md
improve_plan/release_prev_todo/conflict-analysis.md
improve_plan/release_prev_todo/gpt-5.6Sol.md
improve_plan/release_prev_todo/grok-4.5.md
improve_plan/release_prev_todo/opus-4.8.md
improve_plan/release_prev_todo/round_3_final_report.md
improve_plan/reviews/gpt-4.8.md
improve_plan/reviews/grok-4.5.md
improve_plan/reviews/opus-4.8.md
improve_plan/round_0/gpt-5.6-sol/index1.md
improve_plan/round_0/gpt-5.6-sol/index2.md
improve_plan/round_0/gpt-5.6-sol/index3.md
improve_plan/round_0/gpt-5.6-sol/index4.md
improve_plan/round_0/gpt-5.6-sol/index5.md
improve_plan/round_0/gpt-5.6-sol/index6.md
improve_plan/round_0/gpt-5.6-sol/index7.md
improve_plan/round_0/gpt-5.6-sol/index8.md
improve_plan/round_0/gpt-5.6-sol/supplement.md
improve_plan/round_0/grok-4.5.md
improve_plan/round_0/opus-4.8/index1.md
improve_plan/round_0/opus-4.8/index10.md
improve_plan/round_0/opus-4.8/index2.md
improve_plan/round_0/opus-4.8/index3.md
improve_plan/round_0/opus-4.8/index4.md
improve_plan/round_0/opus-4.8/index5.md
improve_plan/round_0/opus-4.8/index6.md
improve_plan/round_0/opus-4.8/index7.md
improve_plan/round_0/opus-4.8/index8.md
improve_plan/round_0/opus-4.8/index9.md
improve_plan/round_2/gpt-5.6Sol.md
improve_plan/round_2/grok-4.5.md
improve_plan/round_2/opus-4.8.md
improve_plan/round_3/gpt-5.6Sol.md
improve_plan/round_3/grok-4.5.md
improve_plan/round_3/opus-4.8.md
install.sh
opencode/carroros.json
opencode/observer.py
packages/carroros-base-v1.0.0.tar.gz
packages/carroros-base/.claude/harness.yaml
packages/carroros-base/.claude/hooks/carroros_hooklib.py
packages/carroros-base/.claude/hooks/hook-launcher.sh
packages/carroros-base/.claude/hooks/pretool-gate.py
packages/carroros-base/.claude/hooks/pretool-user-approve.py
packages/carroros-base/.claude/hooks/statusline-command.sh
packages/carroros-base/.claude/index.md
packages/carroros-base/.claude/kernel.md
packages/carroros-base/.claude/scripts/archive_engine.py
packages/carroros-base/.claude/scripts/capture_evidence.py
packages/carroros-base/.claude/scripts/carros_base.py
packages/carroros-base/.claude/scripts/carros_cost_report.py
packages/carroros-base/.claude/scripts/carros_utils.py
packages/carroros-base/.claude/scripts/context_engine.py
packages/carroros-base/.claude/scripts/context_watermark.py
packages/carroros-base/.claude/scripts/executor_ledger.py
packages/carroros-base/.claude/scripts/fallback_engine.py
packages/carroros-base/.claude/scripts/formal_seal.py
packages/carroros-base/.claude/scripts/intake_gate.py
packages/carroros-base/.claude/scripts/lib/lib/autonomy.py
packages/carroros-base/.claude/scripts/lib/lib/error_dna.py
packages/carroros-base/.claude/scripts/lib/lib/flywheel.py
packages/carroros-base/.claude/scripts/lib/lib/ga_observability_io.py
packages/carroros-base/.claude/scripts/lib/lib/ga_observability_metrics.py
packages/carroros-base/.claude/scripts/lib/lib/ga_observability_report.py
packages/carroros-base/.claude/scripts/lib/lib/handoff_writer.py
packages/carroros-base/.claude/scripts/lib/lib/hot_card.py
packages/carroros-base/.claude/scripts/lib/lib/oracle_gate_light.py
packages/carroros-base/.claude/scripts/lib/lib/phase3_oracle.py
packages/carroros-base/.claude/scripts/lib/lib/tool_store.py
packages/carroros-base/.claude/scripts/lib/lib/water_level.py
packages/carroros-base/.claude/scripts/omc_lint.py
packages/carroros-base/.claude/scripts/oracle_engine.py
packages/carroros-base/.claude/scripts/output_compress.py
packages/carroros-base/.claude/scripts/plan_builder.py
packages/carroros-base/.claude/scripts/pre_action_gate.py
packages/carroros-base/.claude/scripts/runtime_verify.py
packages/carroros-base/.claude/scripts/statusline.py
packages/carroros-base/.claude/scripts/task_state_tracker.py
packages/carroros-base/.claude/scripts/verify_gate.py
packages/carroros-base/.claude/scripts/verify_tests.py
packages/carroros-base/.claude/settings.json
packages/carroros-base/AGENTS.md
packages/carroros-base/CLAUDE.md
packages/carroros-base/benchmark/__init__.py
packages/carroros-base/benchmark/ablation.py
packages/carroros-base/benchmark/cc_runner.py
packages/carroros-base/benchmark/environment.py
packages/carroros-base/benchmark/reporter.py
packages/carroros-base/benchmark/reports/ai-analysis.md
packages/carroros-base/benchmark/reports/first-ab-test-report.md
packages/carroros-base/benchmark/run-ci.sh
packages/carroros-base/benchmark/runner.py
packages/carroros-base/benchmark/schemas.py
packages/carroros-base/benchmark/task_loader.py
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_001.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_002.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_003.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_004.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_005.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_006.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_007.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_008.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_009.yaml
packages/carroros-base/benchmark/tasks/01_repo_locate/01_repo_locate_010.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_001.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_002.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_003.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_004.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_005.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_006.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_007.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_008.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_009.yaml
packages/carroros-base/benchmark/tasks/02_multi_file/02_multi_file_010.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_001.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_002.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_003.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_004.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_005.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_006.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_007.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_008.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_009.yaml
packages/carroros-base/benchmark/tasks/03_cross_module/03_cross_module_010.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_001.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_002.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_003.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_004.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_005.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_006.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_007.yaml
packages/carroros-base/benchmark/tasks/04_migration/04_migration_008.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_001.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_002.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_003.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_004.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_005.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_006.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_007.yaml
packages/carroros-base/benchmark/tasks/05_fuzzy_req/05_fuzzy_req_008.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_001.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_002.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_003.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_004.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_005.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_006.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_007.yaml
packages/carroros-base/benchmark/tasks/06_test_fix/06_test_fix_008.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_001.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_002.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_003.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_004.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_005.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_006.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_007.yaml
packages/carroros-base/benchmark/tasks/07_perf_concur/07_perf_concur_008.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_001.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_002.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_003.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_004.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_005.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_006.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_007.yaml
packages/carroros-base/benchmark/tasks/08_long_recovery/08_long_recovery_008.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_001.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_002.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_003.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_004.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_005.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_006.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_007.yaml
packages/carroros-base/benchmark/tasks/09_high_risk/09_high_risk_008.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_001.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_002.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_003.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_004.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_005.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_006.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_007.yaml
packages/carroros-base/benchmark/tasks/10_adversarial/10_adversarial_008.yaml
packages/carroros-base/benchmark/verify/01_repo_locate_001.sh
packages/carroros-base/benchmark/verify/01_repo_locate_002.sh
packages/carroros-base/benchmark/verify/01_repo_locate_003.sh
packages/carroros-base/benchmark/verify/01_repo_locate_004.sh
packages/carroros-base/benchmark/verify/01_repo_locate_005.sh
packages/carroros-base/benchmark/verify/01_repo_locate_006.sh
packages/carroros-base/benchmark/verify/01_repo_locate_007.sh
packages/carroros-base/benchmark/verify/01_repo_locate_008.sh
packages/carroros-base/benchmark/verify/02_multi_file_001.sh
packages/carroros-base/benchmark/verify/02_multi_file_002.sh
packages/carroros-base/benchmark/verify/02_multi_file_003.sh
packages/carroros-base/benchmark/verify/02_multi_file_004.sh
packages/carroros-base/benchmark/verify/02_multi_file_005.sh
packages/carroros-base/benchmark/verify/02_multi_file_006.sh
packages/carroros-base/benchmark/verify/02_multi_file_007.sh
packages/carroros-base/benchmark/verify/02_multi_file_008.sh
packages/carroros-base/benchmark/verify/03_cross_module_001.sh
packages/carroros-base/benchmark/verify/03_cross_module_002.sh
packages/carroros-base/benchmark/verify/03_cross_module_003.sh
packages/carroros-base/benchmark/verify/03_cross_module_004.sh
packages/carroros-base/benchmark/verify/03_cross_module_005.sh
packages/carroros-base/benchmark/verify/03_cross_module_006.sh
packages/carroros-base/benchmark/verify/03_cross_module_007.sh
packages/carroros-base/benchmark/verify/03_cross_module_008.sh
packages/carroros-base/benchmark/verify/04_migration_001.sh
packages/carroros-base/benchmark/verify/04_migration_002.sh
packages/carroros-base/benchmark/verify/04_migration_003.sh
packages/carroros-base/benchmark/verify/04_migration_004.sh
packages/carroros-base/benchmark/verify/04_migration_005.sh
packages/carroros-base/benchmark/verify/04_migration_006.sh
packages/carroros-base/benchmark/verify/04_migration_007.sh
packages/carroros-base/benchmark/verify/04_migration_008.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_001.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_002.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_003.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_004.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_005.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_006.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_007.sh
packages/carroros-base/benchmark/verify/05_fuzzy_req_008.sh
packages/carroros-base/benchmark/verify/06_test_fix_001.sh
packages/carroros-base/benchmark/verify/06_test_fix_002.sh
packages/carroros-base/benchmark/verify/06_test_fix_003.sh
packages/carroros-base/benchmark/verify/06_test_fix_004.sh
packages/carroros-base/benchmark/verify/06_test_fix_005.sh
packages/carroros-base/benchmark/verify/06_test_fix_006.sh
packages/carroros-base/benchmark/verify/06_test_fix_007.sh
packages/carroros-base/benchmark/verify/06_test_fix_008.sh
packages/carroros-base/benchmark/verify/07_perf_concur_001.sh
packages/carroros-base/benchmark/verify/07_perf_concur_002.sh
packages/carroros-base/benchmark/verify/07_perf_concur_003.sh
packages/carroros-base/benchmark/verify/07_perf_concur_004.sh
packages/carroros-base/benchmark/verify/07_perf_concur_005.sh
packages/carroros-base/benchmark/verify/07_perf_concur_006.sh
packages/carroros-base/benchmark/verify/07_perf_concur_007.sh
packages/carroros-base/benchmark/verify/07_perf_concur_008.sh
packages/carroros-base/benchmark/verify/08_long_recovery_001.sh
packages/carroros-base/benchmark/verify/08_long_recovery_002.sh
packages/carroros-base/benchmark/verify/08_long_recovery_003.sh
packages/carroros-base/benchmark/verify/08_long_recovery_004.sh
packages/carroros-base/benchmark/verify/08_long_recovery_005.sh
packages/carroros-base/benchmark/verify/08_long_recovery_006.sh
packages/carroros-base/benchmark/verify/08_long_recovery_007.sh
packages/carroros-base/benchmark/verify/08_long_recovery_008.sh
packages/carroros-base/benchmark/verify/09_high_risk_001.sh
packages/carroros-base/benchmark/verify/09_high_risk_002.sh
packages/carroros-base/benchmark/verify/09_high_risk_003.sh
packages/carroros-base/benchmark/verify/09_high_risk_004.sh
packages/carroros-base/benchmark/verify/09_high_risk_005.sh
packages/carroros-base/benchmark/verify/09_high_risk_006.sh
packages/carroros-base/benchmark/verify/09_high_risk_007.sh
packages/carroros-base/benchmark/verify/09_high_risk_008.sh
packages/carroros-base/benchmark/verify/10_adversarial_001.sh
packages/carroros-base/benchmark/verify/10_adversarial_002.sh
packages/carroros-base/benchmark/verify/10_adversarial_003.sh
packages/carroros-base/benchmark/verify/10_adversarial_004.sh
packages/carroros-base/benchmark/verify/10_adversarial_005.sh
packages/carroros-base/benchmark/verify/10_adversarial_006.sh
packages/carroros-base/benchmark/verify/10_adversarial_007.sh
packages/carroros-base/benchmark/verify/10_adversarial_008.sh
packages/carroros-base/benchmark/verify/verify_api_error.sh
packages/carroros-base/benchmark/verify/verify_cache_ttl.sh
packages/carroros-base/benchmark/verify/verify_calc_divide.sh
packages/carroros-base/benchmark/verify/verify_calc_factorial.sh
packages/carroros-base/benchmark/verify/verify_calc_power.sh
packages/carroros-base/benchmark/verify/verify_middleware_logger.sh
packages/carroros-base/benchmark/verify/verify_processor_validation.sh
packages/carroros-base/benchmark/verify/verify_stats_empty.sh
rpe/deepseek-injection/executor.md
rpe/deepseek-injection/plan/plan.md
rpe/deepseek-injection/research/research.md
rpe/human_check_feature/executor.md
rpe/human_check_feature/plan.md
rpe/human_check_feature/prd.md
rpe/human_check_feature/research.md
rpe/human_check_feature/state/progress.md
rpe/mechanism-verification-checklist/README.md
rpe/mechanism-verification-checklist/executor.md
rpe/mechanism-verification-checklist/plan.md
rpe/mechanism-verification-checklist/prd.md
rpe/mechanism-verification-checklist/research.md
rpe/mechanism-verification-checklist/scripts/verify_l1.sh
rpe/mechanism-verification-checklist/scripts/verify_l2.py
rpe/mechanism-verification-checklist/scripts/verify_l3.sh
scripts/carroros-gates/abstraction-check.sh
scripts/carroros-gates/assertion-catalog.yaml
scripts/carroros-gates/c7-check.sh
scripts/carroros-gates/evidence-check.sh
scripts/carroros-gates/finalize-page.sh
scripts/carroros-gates/gen-control-plane-lock.sh
scripts/carroros-gates/install-night-hook.sh
scripts/carroros-gates/lib/common.sh
scripts/carroros-gates/lib/gate_result.py
scripts/carroros-gates/lib/run-gate.sh
scripts/carroros-gates/morning-report.sh
scripts/carroros-gates/preflight.sh
scripts/carroros-gates/scope-check.sh
scripts/carroros-gates/smoke/run-all.sh
scripts/carroros-gates/templates/night-manifest.signoff.template.yaml
scripts/carroros-gates/templates/night-manifest.template.yaml
scripts/test-verify-gate.py
state/session-handoff.md
```

### STATUS

命令: `git status --short`

```
 M .claude/.prompt-ring-state.json
 M .claude/hooks/hook-launcher.sh
 M .claude/hooks/pretool-gate.py
 M .claude/references/anti-patterns.md
 M .claude/settings.json
 M .gitignore
T  .omc/scripts/oracle_gate.py
 M .omc/session-handoff.md
 D UI/FINAL.md
 D UI/final/gpt.md
 D UI/final/grok.md
 D UI/final/opus.md
 D UI/gpt-5.6Sol.md
 D UI/grok-4.5.md
 D UI/kimi-k3.md
 D UI/opus-4.8.md
 D UI/round2/gpt-5.6Sol.md
 D UI/round2/grok-4.5.md
 D UI/round2/kimi-k3.md
 D UI/round2/opus.48.md
 D UI/round3/gpt-5.6Sol.md
 D UI/round3/grok.md
 D UI/round3/opus-4.8.md
 D UI/round4/gpt-5.6Sol.md
 D UI/round4/grok-4.5.md
 D UI/round4/opus-4.8.md
 D UI/round5/audit-closure-gpt-5.6Sol.md
 D UI/round5/audit-closure-grok-4.5.md
 D UI/round5/audit-closure-opus-4.8.md
 D UI/round5/audit-receipt-grok-4.5.md
 D UI/round5/audit-request.md
 D UI/round5/audit-rereview-grok-4.5.md
 D UI/round5/audit-response-gpt-5.6Sol.md
 D UI/round5/audit-response-grok-4.5.md
 D UI/round5/audit-response-opus-4.8.md
 D UI/round5/build-opus-package.py
 D UI/round5/gpt-5.6Sol.md
 D UI/round5/grok-ab-payloads.py
 D UI/round5/logs/grok-ab-payloads-20260718-post-sol.log
 D UI/round5/logs/grok-ab-payloads-20260718.log
 D UI/round5/logs/opus-p1-payloads-20260718-post-sol.log
 D UI/round5/logs/opus-p1-payloads-20260718.log
 D UI/round5/logs/preflight-nogo-rerun-20260718.log
 D UI/round5/logs/smoke-independent-rerun-20260718-post-opus.log
 D UI/round5/logs/smoke-independent-rerun-20260718-post-sol.log
 D UI/round5/logs/smoke-independent-rerun-20260718.log
 D UI/round5/logs/smoke-results-independent-post-sol.yaml
 D UI/round5/logs/smoke-results-self-post-sol.yaml
 D UI/round5/logs/smoke-self-20260718-post-opus.log
 D UI/round5/logs/smoke-self-20260718-post-sol.log
 D UI/round5/logs/sol-artifact-verify-20260718.log
 D UI/round5/logs/sol-p0-verify-20260718.log
 D UI/round5/opus-4.8.md
 D UI/round5/opus-4.8_response.md
 D UI/round5/opus-p1-payloads.py
 D UI/round5/opus-source-package.md
 D UI/round5/sol-artifact-verify.py
 D UI/round5/sol-p0-verify.py
 M benchmark/reporter.py
 M benchmark/reports/ai-analysis.md
 ? benchmark/repos/bench-test-app
 M benchmark/task_loader.py
 M benchmark/tasks/01_repo_locate/01_repo_locate_001.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_002.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_003.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_004.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_005.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_006.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_007.yaml
 M benchmark/tasks/01_repo_locate/01_repo_locate_008.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_001.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_002.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_003.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_004.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_005.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_006.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_007.yaml
 M benchmark/tasks/02_multi_file/02_multi_file_008.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_001.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_002.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_003.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_004.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_005.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_006.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_007.yaml
 M benchmark/tasks/03_cross_module/03_cross_module_008.yaml
 M benchmark/tasks/04_migration/04_migration_001.yaml
 M benchmark/tasks/04_migration/04_migration_002.yaml
 M benchmark/tasks/04_migration/04_migration_003.yaml
 M benchmark/tasks/04_migration/04_migration_004.yaml
 M benchmark/tasks/04_migration/04_migration_005.yaml
 M benchmark/tasks/04_migration/04_migration_006.yaml
 M benchmark/tasks/04_migration/04_migration_007.yaml
 M benchmark/tasks/04_migration/04_migration_008.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_001.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_002.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_003.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_004.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_005.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_006.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_007.yaml
 M benchmark/tasks/05_fuzzy_req/05_fuzzy_req_008.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_001.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_002.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_003.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_004.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_005.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_006.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_007.yaml
 M benchmark/tasks/06_test_fix/06_test_fix_008.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_001.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_002.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_003.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_004.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_005.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_006.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_007.yaml
 M benchmark/tasks/07_perf_concur/07_perf_concur_008.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_001.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_002.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_003.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_004.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_005.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_006.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_007.yaml
 M benchmark/tasks/08_long_recovery/08_long_recovery_008.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_001.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_002.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_003.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_004.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_005.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_006.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_007.yaml
 M benchmark/tasks/09_high_risk/09_high_risk_008.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_001.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_002.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_003.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_004.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_005.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_006.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_007.yaml
 M benchmark/tasks/10_adversarial/10_adversarial_008.yaml
 M state/session-handoff.md
?? improve_plan/CarrorOS_second_time/
?? scripts/analyze-session-positions.py
?? scripts/assemble-pkg-materials.sh
?? scripts/find-empty-assistant.py
?? scripts/test-hook-launcher.sh
```

### HEAD

命令: `git rev-parse HEAD`

```
91954a0b01f9c53edf94965238308fcb080818eb
```

### ROOT LISTING

命令: `ls -la`

```
total 88
drwxr-xr-x@ 21 lucas.liang  staff   672 Jul 19 03:46 .
drwx------@ 24 lucas.liang  staff   768 Jul 17 14:07 ..
-rw-r--r--@  1 lucas.liang  staff  6148 Jul 16 14:09 .DS_Store
drwxr-xr-x@ 27 lucas.liang  staff   864 Jul 19 03:52 .claude
drwxr-xr-x@ 16 lucas.liang  staff   512 Jul 19 03:58 .git
-rw-r--r--@  1 lucas.liang  staff   175 Jul 19 03:08 .gitignore
drwxr-xr-x@ 16 lucas.liang  staff   512 Jul 18 13:59 .omc
-rw-r--r--@  1 lucas.liang  staff  2817 Jul 18 21:27 AGENTS.md
-rw-------@  1 lucas.liang  staff   730 Jul 12 14:17 CHANGELOG.md
-rw-r--r--@  1 lucas.liang  staff    12 Jul  5 14:24 CLAUDE.md
-rw-r--r--@  1 lucas.liang  staff  4532 Jul 14 23:48 README.md
-rw-------@  1 lucas.liang  staff     7 Jul 12 14:17 VERSION
drwxr-xr-x@ 22 lucas.liang  staff   704 Jul 19 03:08 benchmark
drwxr-xr-x@  4 lucas.liang  staff   128 Jul 13 03:01 docs
drwxr-xr-x@ 14 lucas.liang  staff   448 Jul 19 03:44 improve_plan
-rwx--x--x@  1 lucas.liang  staff  4925 Jul 15 15:55 install.sh
drwxr-xr-x@  4 lucas.liang  staff   128 Jul  6 20:34 opencode
drwxr-xr-x@  4 lucas.liang  staff   128 Jul 15 15:56 packages
drwxr-xr-x@  5 lucas.liang  staff   160 Jul 14 18:11 rpe
drwxr-xr-x@  8 lucas.liang  staff   256 Jul 19 03:58 scripts
drwxr-xr-x@  3 lucas.liang  staff    96 Jul 19 03:46 state
```

### `.gitignore`

```
     1	# .gitignore
     2	.omc/
     3	__pycache__/
     4	*.pyc
     5	node_modules/
     6	.DS_Store
     7	*.bak
     8	.claude/.prompt-ring.json
     9	.claude/settings.json
    10	.claude/settings_ds.json
    11	.claude/settings_k3.json
    12	benchmark```

### VALIDATION REFERENCES(rg 全量)

共 3770 行,全量在 `shared-rg-validation.txt`。前 200 行:

```
./benchmark/runner.py:142:        print("✅ 所有任务验证通过")
./benchmark/runner.py:182:        succ = sum(1 for r in grp if r.get("result", {}).get("verified_success", False))
./benchmark/runner.py:197:                             f"success={result.get('verified_success')} "
./benchmark/runner.py:206:        + "1. Which group performs best on verified_success_rate?\n"
./benchmark/runner.py:319:    run.verified_success = False
./benchmark/runner.py:416:verify_script: ".benchmark/verify/{task_id}/verify.sh"   # TODO: create verification
./benchmark/tasks/07_perf_concur/07_perf_concur_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/07_perf_concur/07_perf_concur_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/06_test_fix/06_test_fix_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_010.yaml:23:verify_script: ".benchmark/verify/02_multi_file_010/verify.sh"   # TODO: create verification
./benchmark/tasks/02_multi_file/02_multi_file_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_009.yaml:23:verify_script: ".benchmark/verify/02_multi_file_009/verify.sh"   # TODO: create verification
./benchmark/tasks/02_multi_file/02_multi_file_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/02_multi_file/02_multi_file_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/04_migration/04_migration_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_009.yaml:23:verify_script: ".benchmark/verify/03_cross_module_009/verify.sh"   # TODO: create verification
./benchmark/tasks/03_cross_module/03_cross_module_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/03_cross_module/03_cross_module_010.yaml:23:verify_script: ".benchmark/verify/03_cross_module_010/verify.sh"   # TODO: create verification
./benchmark/tasks/03_cross_module/03_cross_module_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/10_adversarial/10_adversarial_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/05_fuzzy_req/05_fuzzy_req_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/09_high_risk/09_high_risk_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_006.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/08_long_recovery/08_long_recovery_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_005.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_009.yaml:23:verify_script: ".benchmark/verify/01_repo_locate_009/verify.sh"   # TODO: create verification
./benchmark/tasks/01_repo_locate/01_repo_locate_008.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_004.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_003.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_002.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_001.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_007.yaml:13:  DO NOT skip verification steps.
./benchmark/tasks/01_repo_locate/01_repo_locate_010.yaml:23:verify_script: ".benchmark/verify/01_repo_locate_010/verify.sh"   # TODO: create verification
./benchmark/tasks/01_repo_locate/01_repo_locate_006.yaml:13:  DO NOT skip verification steps.
./benchmark/ci-20260719-0308.log:21:✅ 所有任务验证通过
./benchmark/ci-20260719-0308.log:600:| S100 | — | 0 |
./benchmark/ci-20260719-0308.log:675:| S100 | — | 0 |
./benchmark/verify/10_adversarial_004.sh:13:print(f'PASS: 10_adversarial_004 — strict compliance verified')
./benchmark/verify/10_adversarial_005.sh:13:print(f'PASS: 10_adversarial_005 — strict compliance verified')
./benchmark/verify/10_adversarial_001.sh:13:print(f'PASS: 10_adversarial_001 — strict compliance verified')
./benchmark/verify/10_adversarial_002.sh:13:print(f'PASS: 10_adversarial_002 — strict compliance verified')
./benchmark/verify/10_adversarial_003.sh:13:print(f'PASS: 10_adversarial_003 — strict compliance verified')
./benchmark/reporter.py:79:        verification = d.get("verification", {})
./benchmark/reporter.py:130:            verification=Verification(
./benchmark/reporter.py:131:                agent_claimed_complete=verification.get("agent_claimed_complete", False),
./benchmark/reporter.py:132:                visible_tests_pass=verification.get("visible_tests_pass", False),
./benchmark/reporter.py:133:                hidden_tests_pass=verification.get("hidden_tests_pass", False),
./benchmark/reporter.py:134:                regression_pass=verification.get("regression_pass", False),
./benchmark/reporter.py:135:                evidence_complete=verification.get("evidence_complete", False),
./benchmark/reporter.py:136:                verify_override_attempted=verification.get("verify_override_attempted", False),
./benchmark/reporter.py:137:                verify_override_escaped=verification.get("verify_override_escaped", False),
./benchmark/reporter.py:138:                governance_violation=verification.get("governance_violation", False),
./benchmark/reporter.py:139:                constraints_pass=verification.get("constraints_pass", False),
./benchmark/reporter.py:141:            verified_success=result.get("verified_success", False),
./benchmark/reporter.py:166:        successes = [r for r in self.runs if r.verified_success]
./benchmark/reporter.py:169:        regressions = [r for r in self.runs if not r.verification.regression_pass]
./benchmark/reporter.py:172:        metrics.verified_success_rate = len(successes) / len(self.runs) if self.runs else 0.0
./benchmark/reporter.py:174:            len([r for r in hard_tasks if r.verified_success]) / len(hard_tasks)
./benchmark/reporter.py:183:        metrics.dollar_per_verified_success = (
./benchmark/reporter.py:189:            g_successes = [r for r in group_runs if r.verified_success]
./benchmark/reporter.py:193:                "verified_success": len(g_successes),
./benchmark/reporter.py:194:                "verified_success_rate": len(g_successes) / len(group_runs) if group_runs else 0.0,
./benchmark/reporter.py:219:            f"| Verified Success Rate | {metrics.verified_success_rate:.1%} |",
./benchmark/reporter.py:224:            f"| Cost / Verified Success | ${metrics.dollar_per_verified_success:.2f} |",
./benchmark/reporter.py:235:                f"{data['verified_success_rate']:.1%} | "
./benchmark/reporter.py:243:            bare_rate = metrics.groups["A_bare"]["verified_success_rate"]
./benchmark/reporter.py:244:            full_rate = metrics.groups["E_full"]["verified_success_rate"]
./benchmark/reporter.py:314:        by_turns = {"S30": 0, "S60": 0, "S100": 0, "S_resume": 0}
./benchmark/reporter.py:318:                by_turns["S100"] += 1
./benchmark/reporter.py:324:        for tier in ["S30", "S60", "S100"]:
./benchmark/README.md:53:collector.py: 运行验证脚本 →
./benchmark/schemas.py:68:    verify_script: str             # Path to hidden verification script
./benchmark/schemas.py:166:    verification: Verification = field(default_factory=Verification)
./benchmark/schemas.py:169:    verified_success: bool = False
./benchmark/schemas.py:228:            "verification": {
./benchmark/schemas.py:229:                "agent_claimed_complete": self.verification.agent_claimed_complete,
./benchmark/schemas.py:230:                "visible_tests_pass": self.verification.visible_tests_pass,
./benchmark/schemas.py:231:                "hidden_tests_pass": self.verification.hidden_tests_pass,
./benchmark/schemas.py:232:                "regression_pass": self.verification.regression_pass,
./benchmark/schemas.py:233:                "evidence_complete": self.verification.evidence_complete,
./benchmark/schemas.py:234:                "verify_override_attempted": self.verification.verify_override_attempted,
./benchmark/schemas.py:235:                "verify_override_escaped": self.verification.verify_override_escaped,
./benchmark/schemas.py:236:                "governance_violation": self.verification.governance_violation,
./benchmark/schemas.py:237:                "constraints_pass": self.verification.constraints_pass,
./benchmark/schemas.py:240:                "verified_success": self.verified_success,
./benchmark/schemas.py:315:    verified_success_rate: float = 0.0
./benchmark/schemas.py:320:    dollar_per_verified_success: float = 0.0
./benchmark/cc_runner.py:148:- DO NOT skip verification"""
./benchmark/cc_runner.py:156:        print("  ✅ Step 3: Run verification...")
./benchmark/task_loader.py:271:        issues.append("Missing verify_script (hidden verification)")
./benchmark/task_loader.py:305:        print("✅ 所有任务验证通过")
./benchmark/ci-20260719-0301.log:683:| S100 | — | 0 |
./benchmark/ci-20260719-0301.log:756:| S100 | — | 0 |
./benchmark/reports/long-running-stability.md:14:| S100 | — | 0 |
./benchmark/reports/first-ab-test-report.md:107:| 能证明 | 证据 |
./benchmark/reports/first-ab-test-report.md:120:1. **修复 hint：** 让 pretool-gate 在阻断时同时通过 `additionalContext` 输出具体的下一步指引（已做，待验证）
./.claude/plans/carroros-skills-merge-plan.md:32:| lx-oracle-meta | 无版本号 | Oracle 运行时 | 运行时验证 (Oracle-V) | 2 |
./.claude/plans/carroros-skills-merge-plan.md:155:| **用途** | 基于 Oracle-D 协议的偏紧静态检查：scope 越界、危险路径/命令、file:line 证据 |
./.claude/plans/carroros-skills-merge-plan.md:161:#### lx-oracle-meta — Meta-Oracle 运行时验证审核
./.claude/plans/carroros-skills-merge-plan.md:164:| **用途** | 基于 Oracle-V 协议的偏松运行时验证：token 进度、executor 证据、audit 事件、G1-G4 门禁评分 |
./.claude/plans/carroros-skills-merge-plan.md:165:| **角色** | critic — 运行时验证，偏松审查 |
./.claude/plans/carroros-skills-merge-plan.md:178:| **检查维度** | scope/危险路径/命令/证据完整性 | G1(进度)/G2(失败)/G3(通过)/G4(哲学) | 聚合静态+运行时 |
./.claude/plans/carroros-skills-merge-plan.md:214:| **触发时机** | ghost 激活前（计划验证） | 执行后（结果验证） |
./.claude/plans/carroros-skills-merge-plan.md:220:| **D5 退出条件** | 成功/失败信号是否可验证 | 不涉及 |
./.claude/plans/carroros-skills-merge-plan.md:223:| **G3 通过证据** | 不涉及 | 检查 PASS/exit code 0 |
./.claude/plans/carroros-skills-merge-plan.md:233:- lx-oracle-meta: **事后执行验证引擎**（代码变更是否通过测试、证据完整）
./.claude/plans/carroros-skills-merge-plan.md:266:  hier <path> [output_dir] | split <path> [--pipeline <id>] |
./.claude/plans/carroros-skills-merge-plan.md:292:| **Hier refs** | error-codes.md, observability.md, pipeline.md, sub-prd-template.md, verification-gate.md | `references/hier/` |
./.claude/plans/carroros-skills-merge-plan.md:295:| **Split refs** | mece-checklist.md, scaffolding-template.md, interface-verification.md, delivery-report.md | `references/split/` |
./.claude/plans/carroros-skills-merge-plan.md:324:description: Oracle quality gate system — static analysis, runtime verification, dual-agent review
./.claude/plans/carroros-skills-merge-plan.md:334:  runtime: 执行后运行时验证、方案事前审核
./.claude/plans/carroros-skills-merge-plan.md:335:  duo: 高风险场景双重验证、Release 门禁
./.claude/plans/carroros-skills-merge-plan.md:346:/lx-oracle runtime <task-id>  → 运行时验证（原 lx-oracle-meta）
./.claude/plans/carroros-skills-merge-plan.md:373:- 证据门禁规则
./.claude/plans/carroros-skills-merge-plan.md:391:**理由：** lx-ghost 的功能域（方向驱动自主探索）与 lx-oracle-meta（通用运行时验证）不重叠。lx-ghost 提供了独特的"方向驱动、增量 poll 迭代、事前 Oracle 门禁"模式，与 lx-goal 的"目标驱动、逐项 task-done"形成互补。
./.claude/plans/carroros-skills-merge-plan.md:444:7. **回归验证** — 验证所有管线命令在新入口下正常工作
./.claude/plans/carroros-skills-merge-plan.md:471:    └── verification-gate.md
./.claude/plans/carroros-skills-merge-plan.md:491:    ├── interface-verification.md
./.claude/plans/carroros-skills-merge-plan.md:512:│   │   └── verification-gate.md
./.claude/plans/carroros-skills-merge-plan.md:524:│       ├── interface-verification.md
./.claude/plans/pretool-gate-modularization-roi.md:52:│   ├── verify_gate.py       (gate 6)
./.claude/plans/pretool-gate-modularization-roi.md:53:│   ├── oracle_gate.py       (gate 7)
./.claude/plans/pretool-gate-modularization-roi.md:69:| **开发时间** | ~30-45 分钟（拆 8 个文件 + 测试 + 验证） |
./.claude/plans/pretool-gate-modularization-roi.md:116:   - 每步独立验证：每个 gate 不依赖其他 gate 的状态
./.claude/nodes/interactive_prompt.md:12:所有交互统一使用以下模式（已验证通过）：
./.claude/nodes/interactive_prompt.md:43:| 选项1 推荐 ✓ | 加入 scope 并写入 | 全量+验证 | 确认执行 |
./.claude/nodes/interactive_prompt.md:82:    - "全量+验证 — 推荐 ✓": "检测 + 自动修复 P0/P1 + re-scan"
./.claude/nodes/interactive_prompt.md:100:1. 全量+验证 — 推荐 ✓
./.claude/nodes/interactive_prompt.md:114:| lx-code-review | 审查什么？ | 全量+验证 / 深度分析 / 快速扫描 | 并发安全 |
./.claude/nodes/auto_fixer.md:35:verification: pass | fail | pending
./.claude/nodes/auto_fixer.md:44:5. 标记 `fix_record.verification=pending`
./.claude/nodes/report_generator.md:5:# - scan_report: scan_report.yaml (required) — 扫描/审查/验证报告
./.claude/nodes/report_generator.md:20:| scan_report | scan_report.yaml | 是 | — | 扫描/审查/验证报告 |
./.claude/nodes/report_generator.md:41:- 每项：位置 + 描述 + 证据 + 建议
./.claude/nodes/mode_selector.md:54:| 跨模块功能开发（3+ 文件） | Stepwise | 有序依赖，需阶段验证 |
./.claude/nodes/mode_selector.md:74:      - "完成标准验证"
./.claude/nodes/mode_selector.md:83:      - "输入产物验证"
./.claude/nodes/mode_selector.md:86:      - "exit 标准逐条验证"
./.claude/nodes/mode_selector.md:87:      - "证据写入"
./.claude/nodes/mode_selector.md:91:      - "证据汇总"
./.claude/nodes/mode_selector.md:154:4. Stepwise 模式 → 使用 `completion-gate.sh` + `plan-gate.sh` 验证阶段
./.claude/nodes/verifier.md:9:# - verification_report: { total, passed, failed, residual_findings } — 验证报告
```
