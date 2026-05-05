# Loading Benchmark Report

**Generated:** 2026-05-04 09:07:31
**Method:** tiktoken cl100k_base
**Repository:** `/Users/lucas.liang/Desktop/Sylph/Carror_OS`

---

## 1. Method

- **Token estimation:** Uses `tiktoken` with `cl100k_base` encoding (the same tokenizer
  used by Claude models). This is an **estimate** -- actual LLM context usage depends on
  the model's internal tokenization and system prompt overhead.
- **Fallback:** If tiktoken is not installed, falls back to `chars // 4`, which is a
  coarse estimate (~4 characters per token for English text). Fallback results are
  labelled `[estimate: chars/4 fallback]`.
- **Sample:** Single pass measurement of all `.md` files in `.claude/` + `CLAUDE.md` +
  `AGENTS.md`. No repeated sampling (file contents are static).
- **Limitations:**
  1. Token counts are estimates, not exact LLM context measurements.
  2. Does not account for system prompt size, conversation history, or tool definitions.
  3. Single measurement -- no variance calculation (static content).
  4. Only counts text content; binary/frontmatter parsing not applied.
  5. Line counts are reported as total lines (including blanks) for comparison with
     loading_matrix.md claims (which uses total lines). Non-empty line counts also included.

---

## 2. Layer Definitions

| Layer | Contents | Load Strategy |
|-------|----------|--------------|
| **L1** | `CLAUDE.md`, `AGENTS.md`, `kernel.md`, `anti-patterns.md`, `claude-next.md` | Always loaded at session start |
| **L2** | All `SKILL.md` files, node system files (`.claude/nodes/`), on-demand `task_sys/` files (orchestrator, context_guard, mechanism_evals, loading_matrix, etc.) | Loaded on-demand when entering a specific phase or triggering a skill |
| **L3** | Skill reference docs (`.claude/skills/*/references/`), task template files (`.claude/task_sys/templates/`) | Precision-loaded when performing a specific operation |

---

## 3. Condition Comparison

### Condition A: Progressive Disclosure (L1 only)
- Files: 5
- Total lines (incl. blanks): 427
- Non-empty lines: 311
- Total tokens: 7,539

### Condition B: Full Load (L1 + L2 + L3)
- Files: 143
- Total lines (incl. blanks): 9200
- Non-empty lines: 6984
- Total tokens: 172,994

### Savings
| Metric | Progressive (A) | Full (B) | Reduction |
|--------|----------------|----------|-----------|
| Lines (incl. blanks) | 427 | 9200 | 95.4% |
| Non-empty lines | 311 | 6984 | 95.5% |
| Tokens | 7,539 | 172,994 | 95.6% |

---

## 4. Verification of loading_matrix.md Claims

The loading matrix (`task_sys/loading_matrix.md`, line 89) claims:

> "首次加载从 394 行 → ~120 行，减少 70%。"

### Measured Results (total lines, including blanks)
| Metric | Claimed | Measured |
|--------|---------|----------|
| Full load (before) | ~394 lines | **9200 lines** |
| Progressive (after) | ~120 lines | **427 lines** |
| Reduction | ~70% | **95.4%** |

**Verdict (total lines):** NOTE - measured values differ from claimed values

### Alternative: Non-empty lines
| Metric | Claimed | Measured |
|--------|---------|----------|
| Full load (before) | ~394 lines | **6984 lines** |
| Progressive (after) | ~120 lines | **311 lines** |
| Reduction | ~70% | **95.5%** |

**Verdict (non-empty):** NOTE - measured values differ from claimed values

---

## 5. Structure Report

### L1 Files (always loaded)
| path                     | lines | nonempty | tokens | method               |
| ------------------------ | ----- | -------- | ------ | -------------------- |
| CLAUDE.md                | 17    | 13       | 197    | tiktoken cl100k_base |
| AGENTS.md                | 232   | 168      | 3180   | tiktoken cl100k_base |
| .claude/kernel.md        | 30    | 20       | 410    | tiktoken cl100k_base |
| .claude/anti-patterns.md | 117   | 89       | 2878   | tiktoken cl100k_base |
| .claude/claude-next.md   | 31    | 21       | 874    | tiktoken cl100k_base |

### L2 Files (on-demand)
| path                                           | lines | nonempty | tokens | method               |
| ---------------------------------------------- | ----- | -------- | ------ | -------------------- |
| .claude/skills/lx-browser-verify/SKILL.md      | 113   | 80       | 2322   | tiktoken cl100k_base |
| .claude/skills/lx-code-review/SKILL.md         | 174   | 133      | 4149   | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/SKILL.md          | 201   | 142      | 3652   | tiktoken cl100k_base |
| .claude/skills/lx-frontend-test/SKILL.md       | 9     | 8        | 257    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/SKILL.md         | 133   | 98       | 1753   | tiktoken cl100k_base |
| .claude/skills/lx-oma/SKILL.md                 | 55    | 36       | 944    | tiktoken cl100k_base |
| .claude/skills/lx-perf-analysis/SKILL.md       | 151   | 114      | 2684   | tiktoken cl100k_base |
| .claude/skills/lx-prd/SKILL.md                 | 369   | 282      | 8333   | tiktoken cl100k_base |
| .claude/skills/lx-pre-commit/SKILL.md          | 69    | 44       | 942    | tiktoken cl100k_base |
| .claude/skills/lx-pre-push/SKILL.md            | 89    | 59       | 1214   | tiktoken cl100k_base |
| .claude/skills/lx-react-review/SKILL.md        | 149   | 112      | 3172   | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/SKILL.md | 211   | 168      | 5864   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/SKILL.md                 | 1052  | 914      | 15695  | tiktoken cl100k_base |
| .claude/skills/lx-security-review/SKILL.md     | 127   | 95       | 2431   | tiktoken cl100k_base |
| .claude/skills/lx-status/SKILL.md              | 50    | 33       | 529    | tiktoken cl100k_base |
| .claude/skills/lx-style-guide/SKILL.md         | 128   | 94       | 2669   | tiktoken cl100k_base |
| .claude/skills/lx-task-spec/SKILL.md           | 194   | 151      | 3312   | tiktoken cl100k_base |
| .claude/skills/lx-tdd-spec/SKILL.md            | 140   | 106      | 3540   | tiktoken cl100k_base |
| .claude/skills/lx-todo/SKILL.md                | 293   | 229      | 6188   | tiktoken cl100k_base |
| .claude/skills/lx-validate-skill/SKILL.md      | 159   | 112      | 1897   | tiktoken cl100k_base |
| .claude/skills/lx-varlock/SKILL.md             | 68    | 47       | 1175   | tiktoken cl100k_base |
| .claude/skills/lx-web-perf/SKILL.md            | 133   | 97       | 2745   | tiktoken cl100k_base |
| .claude/nodes/a_terminal.md                    | 70    | 45       | 707    | tiktoken cl100k_base |
| .claude/nodes/auto_fixer.md                    | 45    | 37       | 543    | tiktoken cl100k_base |
| .claude/nodes/b_terminal.md                    | 77    | 47       | 734    | tiktoken cl100k_base |
| .claude/nodes/behavior_rules.md                | 198   | 135      | 2968   | tiktoken cl100k_base |
| .claude/nodes/context_collector.md             | 14    | 8        | 147    | tiktoken cl100k_base |
| .claude/nodes/execute_node.md                  | 89    | 64       | 1095   | tiktoken cl100k_base |
| .claude/nodes/gate_checker.md                  | 42    | 34       | 457    | tiktoken cl100k_base |
| .claude/nodes/generator.md                     | 43    | 35       | 466    | tiktoken cl100k_base |
| .claude/nodes/interactive_prompt.md            | 56    | 42       | 1293   | tiktoken cl100k_base |
| .claude/nodes/orchestrator.md                  | 71    | 51       | 886    | tiktoken cl100k_base |
| .claude/nodes/report_generator.md              | 54    | 42       | 493    | tiktoken cl100k_base |
| .claude/nodes/scanner.md                       | 60    | 50       | 678    | tiktoken cl100k_base |
| .claude/nodes/target_resolver.md               | 43    | 35       | 515    | tiktoken cl100k_base |
| .claude/nodes/verifier.md                      | 46    | 38       | 505    | tiktoken cl100k_base |
| .claude/task_sys/context_guard.md              | 93    | 72       | 1433   | tiktoken cl100k_base |
| .claude/task_sys/mechanism_evals.md            | 88    | 63       | 1496   | tiktoken cl100k_base |
| .claude/task_sys/loading_matrix.md             | 101   | 84       | 1739   | tiktoken cl100k_base |
| .claude/task_sys/orchestrator.md               | 125   | 87       | 2204   | tiktoken cl100k_base |
| .claude/task_sys/unified_delivery_schema.md    | 66    | 52       | 938    | tiktoken cl100k_base |
| .claude/task_sys/task_fs.md                    | 37    | 31       | 447    | tiktoken cl100k_base |

### L3 Files (precision-loaded)
| path                                                                              | lines | nonempty | tokens | method               |
| --------------------------------------------------------------------------------- | ----- | -------- | ------ | -------------------- |
| .claude/skills/lx-browser-verify/references/checklists/danger-signals.md          | 13    | 7        | 527    | tiktoken cl100k_base |
| .claude/skills/lx-code-review/references/checklists/danger-signals.md             | 11    | 6        | 506    | tiktoken cl100k_base |
| .claude/skills/lx-code-review/references/knowledge/review-rules.md                | 20    | 16       | 404    | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/references/checklists/danger-signals.md              | 35    | 33       | 491    | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/references/condition-based-waiting.md                | 59    | 43       | 629    | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/references/defense-in-depth.md                       | 31    | 20       | 411    | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/references/root-cause-tracing.md                     | 33    | 23       | 457    | tiktoken cl100k_base |
| .claude/skills/lx-debug-spec/references/templates/normal-completion.md            | 9     | 8        | 257    | tiktoken cl100k_base |
| .claude/skills/lx-frontend-test/references/checklists/danger-signals.md           | 13    | 7        | 753    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/checklists/danger-signals.md             | 15    | 14       | 201    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/checklists/usability-v01-v12.md          | 18    | 17       | 258    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/commands-quickref.md                     | 43    | 30       | 306    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/go-version-matrix.md                     | 9     | 8        | 136    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/benchmarks.md                  | 21    | 15       | 220    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/cicd.md                        | 23    | 15       | 206    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/coverage.md                    | 15    | 9        | 134    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/fuzzing.md                     | 22    | 15       | 240    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/golden-files.md                | 14    | 10       | 205    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/helpers.md                     | 11    | 8        | 195    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/http-handler.md                | 13    | 10       | 309    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/mocking.md                     | 30    | 21       | 248    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/race-condition.md              | 31    | 21       | 276    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/subtests.md                    | 14    | 9        | 171    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/knowledge/table-driven.md                | 17    | 13       | 360    | tiktoken cl100k_base |
| .claude/skills/lx-golang-test/references/mock-strategy-quickref.md                | 11    | 10       | 147    | tiktoken cl100k_base |
| .claude/skills/lx-perf-analysis/references/checklists/danger-signals.md           | 11    | 6        | 473    | tiktoken cl100k_base |
| .claude/skills/lx-perf-analysis/references/knowledge/optimization-patterns.md     | 126   | 94       | 1693   | tiktoken cl100k_base |
| .claude/skills/lx-perf-analysis/references/knowledge/profiling-guide.md           | 104   | 65       | 1212   | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/appendix-templates.md                            | 90    | 62       | 738    | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/full-flow-diagram.md                             | 9     | 7        | 420    | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/mermaid-templates.md                             | 60    | 43       | 1085   | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/polish-workflow.md                               | 21    | 16       | 730    | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/prd-toc-template.md                              | 19    | 11       | 547    | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/scoring.md                                       | 86    | 73       | 1758   | tiktoken cl100k_base |
| .claude/skills/lx-prd/references/self-eval-checklist.md                           | 18    | 16       | 430    | tiktoken cl100k_base |
| .claude/skills/lx-pre-push/references/commit-convention-guide.md                  | 36    | 25       | 345    | tiktoken cl100k_base |
| .claude/skills/lx-react-review/references/checklists/danger-signals.md            | 13    | 7        | 975    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/anti-patterns.md                 | 39    | 36       | 1060   | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/checklists/danger-signals.md     | 25    | 21       | 635    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/confidence-scoring.md            | 31    | 26       | 736    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/go-root-cause-patterns.md        | 43    | 37       | 939    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/oracle-escalation.md             | 37    | 26       | 596    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/rca-feedback-template.md         | 18    | 15       | 462    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/repair-loop-rules.md             | 21    | 16       | 646    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/templates/blocked.md             | 13    | 11       | 416    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/templates/immunity-failed.md     | 11    | 9        | 254    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/templates/normal-completion.md   | 12    | 10       | 946    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/templates/not-applicable.md      | 13    | 12       | 210    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/templates/oracle-consultation.md | 12    | 10       | 318    | tiktoken cl100k_base |
| .claude/skills/lx-root-cause-analysis/references/tool-output-rules.md             | 28    | 19       | 634    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/abort-conditions.md                              | 11    | 10       | 236    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/batch-accept-template.md                         | 618   | 490      | 19021  | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/commit-convention.md                             | 28    | 22       | 346    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/context-retention.md                             | 10    | 9        | 269    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/error-recovery-table.md                          | 13    | 12       | 432    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/frontend-coding-rules.md                         | 16    | 11       | 343    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/gate-checklist.md                                | 41    | 37       | 755    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/go-coding-rules.md                               | 19    | 13       | 409    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/milestone-rules.md                               | 22    | 17       | 418    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/phase-transition-rules.md                        | 14    | 13       | 338    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/progress-file-template.md                        | 34    | 22       | 848    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/progress-panel-template.md                       | 31    | 22       | 1004   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/protocol-table.md                                | 11    | 10       | 218    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/root-cause-protocol.md                           | 6     | 5        | 371    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/security-scan-rules.md                           | 30    | 18       | 348    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/skill-linkage-table.md                           | 14    | 13       | 474    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/skill-mapping-table.md                           | 16    | 15       | 396    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/executor.md                            | 66    | 42       | 1040   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/plan.md                                | 87    | 59       | 1108   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/research.md                            | 57    | 38       | 834    | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/templates/executor.md                  | 30    | 16       | 1027   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/templates/plan.md                      | 35    | 18       | 1085   | tiktoken cl100k_base |
| .claude/skills/lx-rpe/references/templates/templates/research.md                  | 23    | 12       | 819    | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/checklists/danger-signals.md         | 15    | 14       | 233    | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/exclusion-patterns.md                | 10    | 9        | 85     | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/false-positive-rules.md              | 13    | 12       | 260    | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/fix-templates.md                     | 88    | 66       | 916    | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/scan-rules.md                        | 34    | 29       | 731    | tiktoken cl100k_base |
| .claude/skills/lx-security-review/references/severity-levels.md                   | 8     | 7        | 149    | tiktoken cl100k_base |
| .claude/skills/lx-style-guide/references/checklists/danger-signals.md             | 13    | 7        | 608    | tiktoken cl100k_base |
| .claude/skills/lx-task-spec/references/ac-template.md                             | 18    | 14       | 309    | tiktoken cl100k_base |
| .claude/skills/lx-task-spec/references/execution-modes.md                         | 10    | 7        | 183    | tiktoken cl100k_base |
| .claude/skills/lx-tdd-spec/references/behavior-matrix.md                          | 17    | 15       | 249    | tiktoken cl100k_base |
| .claude/skills/lx-tdd-spec/references/gwt-template.md                             | 17    | 13       | 241    | tiktoken cl100k_base |
| .claude/skills/lx-todo/references/execution-types.md                              | 48    | 37       | 1653   | tiktoken cl100k_base |
| .claude/skills/lx-todo/references/queue-format.md                                 | 27    | 25       | 640    | tiktoken cl100k_base |
| .claude/skills/lx-todo/references/upgrade-protocol.md                             | 20    | 16       | 504    | tiktoken cl100k_base |
| .claude/skills/lx-web-perf/references/checklists/danger-signals.md                | 13    | 7        | 893    | tiktoken cl100k_base |
| .claude/task_sys/templates/acceptance_report.md                                   | 23    | 15       | 127    | tiktoken cl100k_base |
| .claude/task_sys/templates/alternatives_explored.md                               | 23    | 17       | 307    | tiktoken cl100k_base |
| .claude/task_sys/templates/criteria.md                                            | 7     | 6        | 78     | tiktoken cl100k_base |
| .claude/task_sys/templates/executor.md                                            | 12    | 11       | 131    | tiktoken cl100k_base |
| .claude/task_sys/templates/fallback_analysis.md                                   | 21    | 14       | 358    | tiktoken cl100k_base |
| .claude/task_sys/templates/plan.md                                                | 30    | 22       | 286    | tiktoken cl100k_base |
| .claude/task_sys/templates/summary.md                                             | 9     | 8        | 107    | tiktoken cl100k_base |

### Layer Summary
| Layer | Files | Lines | Non-empty | Tokens |
|-------|-------|-------|-----------|--------|
| L1 | 5 | 427 | 311 | 7,539 |
| L2 | 43 | 5638 | 4317 | 97,963 |
| L3 | 95 | 3135 | 2356 | 67,492 |
| **Total (A: progressive)** | **5** | **427** | **311** | **7,539** |
| **Total (B: full)** | **143** | **9200** | **6984** | **172,994** |

---

## 6. Limitations

1. **Token estimation method:** tiktoken cl100k_base
2. **Single sample:** File contents are static, so repeated measurements would yield identical results.
3. **LLM context overhead:** This benchmark counts only file content tokens, not the system prompt,
   conversation history, or tool/function definitions that also consume context window.
4. **Line counts:** Both total lines (including blanks) and non-empty lines are reported.
   The loading_matrix.md claim likely uses total lines.
5. **File coverage:** Only scans `.claude/` governance/skill files.
   External dependencies are not included.

---

## 7. Raw Data

```json
{
  "timestamp": "2026-05-04T09:07:31.190050",
  "method_hint": "tiktoken cl100k_base",
  "condition_a": {
    "label": "Progressive (L1 only)",
    "files": 5,
    "lines": 427,
    "nonempty": 311,
    "tokens": 7539
  },
  "condition_b": {
    "label": "Full load (L1+L2+L3)",
    "files": 143,
    "lines": 9200,
    "nonempty": 6984,
    "tokens": 172994
  },
  "layer_summary": {
    "L1": {
      "file_count": 5,
      "total_lines": 427,
      "total_nonempty": 311,
      "total_tokens": 7539
    },
    "L2": {
      "file_count": 43,
      "total_lines": 5638,
      "total_nonempty": 4317,
      "total_tokens": 97963
    },
    "L3": {
      "file_count": 95,
      "total_lines": 3135,
      "total_nonempty": 2356,
      "total_tokens": 67492
    }
  },
  "claim_verification": {
    "claim": "首次加载从 394 行 → ~120 行，减少 70%",
    "measured_full_lines": 9200,
    "measured_progressive_lines": 427,
    "measured_full_nonempty": 6984,
    "measured_progressive_nonempty": 311,
    "measured_reduction_pct_total_lines": 95.4,
    "measured_reduction_pct_nonempty": 95.5,
    "verdict_total_lines": "differs",
    "verdict_nonempty": "differs"
  },
  "file_details": [
    {
      "path": "CLAUDE.md",
      "lines": 17,
      "nonempty": 13,
      "tokens": 197,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": "AGENTS.md",
      "lines": 232,
      "nonempty": 168,
      "tokens": 3180,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/kernel.md",
      "lines": 30,
      "nonempty": 20,
      "tokens": 410,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/anti-patterns.md",
      "lines": 117,
      "nonempty": 89,
      "tokens": 2878,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/claude-next.md",
      "lines": 31,
      "nonempty": 21,
      "tokens": 874,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-browser-verify/SKILL.md",
      "lines": 113,
      "nonempty": 80,
      "tokens": 2322,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-code-review/SKILL.md",
      "lines": 174,
      "nonempty": 133,
      "tokens": 4149,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/SKILL.md",
      "lines": 201,
      "nonempty": 142,
      "tokens": 3652,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-frontend-test/SKILL.md",
      "lines": 9,
      "nonempty": 8,
      "tokens": 257,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/SKILL.md",
      "lines": 133,
      "nonempty": 98,
      "tokens": 1753,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-oma/SKILL.md",
      "lines": 55,
      "nonempty": 36,
      "tokens": 944,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-perf-analysis/SKILL.md",
      "lines": 151,
      "nonempty": 114,
      "tokens": 2684,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/SKILL.md",
      "lines": 369,
      "nonempty": 282,
      "tokens": 8333,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-pre-commit/SKILL.md",
      "lines": 69,
      "nonempty": 44,
      "tokens": 942,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-pre-push/SKILL.md",
      "lines": 89,
      "nonempty": 59,
      "tokens": 1214,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-react-review/SKILL.md",
      "lines": 149,
      "nonempty": 112,
      "tokens": 3172,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/SKILL.md",
      "lines": 211,
      "nonempty": 168,
      "tokens": 5864,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/SKILL.md",
      "lines": 1052,
      "nonempty": 914,
      "tokens": 15695,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/SKILL.md",
      "lines": 127,
      "nonempty": 95,
      "tokens": 2431,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-status/SKILL.md",
      "lines": 50,
      "nonempty": 33,
      "tokens": 529,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-style-guide/SKILL.md",
      "lines": 128,
      "nonempty": 94,
      "tokens": 2669,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-task-spec/SKILL.md",
      "lines": 194,
      "nonempty": 151,
      "tokens": 3312,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-tdd-spec/SKILL.md",
      "lines": 140,
      "nonempty": 106,
      "tokens": 3540,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-todo/SKILL.md",
      "lines": 293,
      "nonempty": 229,
      "tokens": 6188,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-validate-skill/SKILL.md",
      "lines": 159,
      "nonempty": 112,
      "tokens": 1897,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-varlock/SKILL.md",
      "lines": 68,
      "nonempty": 47,
      "tokens": 1175,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-web-perf/SKILL.md",
      "lines": 133,
      "nonempty": 97,
      "tokens": 2745,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/a_terminal.md",
      "lines": 70,
      "nonempty": 45,
      "tokens": 707,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/auto_fixer.md",
      "lines": 45,
      "nonempty": 37,
      "tokens": 543,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/b_terminal.md",
      "lines": 77,
      "nonempty": 47,
      "tokens": 734,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/behavior_rules.md",
      "lines": 198,
      "nonempty": 135,
      "tokens": 2968,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/context_collector.md",
      "lines": 14,
      "nonempty": 8,
      "tokens": 147,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/execute_node.md",
      "lines": 89,
      "nonempty": 64,
      "tokens": 1095,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/gate_checker.md",
      "lines": 42,
      "nonempty": 34,
      "tokens": 457,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/generator.md",
      "lines": 43,
      "nonempty": 35,
      "tokens": 466,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/interactive_prompt.md",
      "lines": 56,
      "nonempty": 42,
      "tokens": 1293,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/orchestrator.md",
      "lines": 71,
      "nonempty": 51,
      "tokens": 886,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/report_generator.md",
      "lines": 54,
      "nonempty": 42,
      "tokens": 493,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/scanner.md",
      "lines": 60,
      "nonempty": 50,
      "tokens": 678,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/target_resolver.md",
      "lines": 43,
      "nonempty": 35,
      "tokens": 515,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/nodes/verifier.md",
      "lines": 46,
      "nonempty": 38,
      "tokens": 505,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/context_guard.md",
      "lines": 93,
      "nonempty": 72,
      "tokens": 1433,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/mechanism_evals.md",
      "lines": 88,
      "nonempty": 63,
      "tokens": 1496,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/loading_matrix.md",
      "lines": 101,
      "nonempty": 84,
      "tokens": 1739,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/orchestrator.md",
      "lines": 125,
      "nonempty": 87,
      "tokens": 2204,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/unified_delivery_schema.md",
      "lines": 66,
      "nonempty": 52,
      "tokens": 938,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/task_fs.md",
      "lines": 37,
      "nonempty": 31,
      "tokens": 447,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-browser-verify/references/checklists/danger-signals.md",
      "lines": 13,
      "nonempty": 7,
      "tokens": 527,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-code-review/references/checklists/danger-signals.md",
      "lines": 11,
      "nonempty": 6,
      "tokens": 506,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-code-review/references/knowledge/review-rules.md",
      "lines": 20,
      "nonempty": 16,
      "tokens": 404,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/references/checklists/danger-signals.md",
      "lines": 35,
      "nonempty": 33,
      "tokens": 491,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/references/condition-based-waiting.md",
      "lines": 59,
      "nonempty": 43,
      "tokens": 629,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/references/defense-in-depth.md",
      "lines": 31,
      "nonempty": 20,
      "tokens": 411,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/references/root-cause-tracing.md",
      "lines": 33,
      "nonempty": 23,
      "tokens": 457,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-debug-spec/references/templates/normal-completion.md",
      "lines": 9,
      "nonempty": 8,
      "tokens": 257,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-frontend-test/references/checklists/danger-signals.md",
      "lines": 13,
      "nonempty": 7,
      "tokens": 753,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/checklists/danger-signals.md",
      "lines": 15,
      "nonempty": 14,
      "tokens": 201,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/checklists/usability-v01-v12.md",
      "lines": 18,
      "nonempty": 17,
      "tokens": 258,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/commands-quickref.md",
      "lines": 43,
      "nonempty": 30,
      "tokens": 306,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/go-version-matrix.md",
      "lines": 9,
      "nonempty": 8,
      "tokens": 136,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/benchmarks.md",
      "lines": 21,
      "nonempty": 15,
      "tokens": 220,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/cicd.md",
      "lines": 23,
      "nonempty": 15,
      "tokens": 206,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/coverage.md",
      "lines": 15,
      "nonempty": 9,
      "tokens": 134,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/fuzzing.md",
      "lines": 22,
      "nonempty": 15,
      "tokens": 240,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/golden-files.md",
      "lines": 14,
      "nonempty": 10,
      "tokens": 205,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/helpers.md",
      "lines": 11,
      "nonempty": 8,
      "tokens": 195,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/http-handler.md",
      "lines": 13,
      "nonempty": 10,
      "tokens": 309,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/mocking.md",
      "lines": 30,
      "nonempty": 21,
      "tokens": 248,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/race-condition.md",
      "lines": 31,
      "nonempty": 21,
      "tokens": 276,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/subtests.md",
      "lines": 14,
      "nonempty": 9,
      "tokens": 171,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/knowledge/table-driven.md",
      "lines": 17,
      "nonempty": 13,
      "tokens": 360,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-golang-test/references/mock-strategy-quickref.md",
      "lines": 11,
      "nonempty": 10,
      "tokens": 147,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-perf-analysis/references/checklists/danger-signals.md",
      "lines": 11,
      "nonempty": 6,
      "tokens": 473,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-perf-analysis/references/knowledge/optimization-patterns.md",
      "lines": 126,
      "nonempty": 94,
      "tokens": 1693,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-perf-analysis/references/knowledge/profiling-guide.md",
      "lines": 104,
      "nonempty": 65,
      "tokens": 1212,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/appendix-templates.md",
      "lines": 90,
      "nonempty": 62,
      "tokens": 738,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/full-flow-diagram.md",
      "lines": 9,
      "nonempty": 7,
      "tokens": 420,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/mermaid-templates.md",
      "lines": 60,
      "nonempty": 43,
      "tokens": 1085,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/polish-workflow.md",
      "lines": 21,
      "nonempty": 16,
      "tokens": 730,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/prd-toc-template.md",
      "lines": 19,
      "nonempty": 11,
      "tokens": 547,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/scoring.md",
      "lines": 86,
      "nonempty": 73,
      "tokens": 1758,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-prd/references/self-eval-checklist.md",
      "lines": 18,
      "nonempty": 16,
      "tokens": 430,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-pre-push/references/commit-convention-guide.md",
      "lines": 36,
      "nonempty": 25,
      "tokens": 345,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-react-review/references/checklists/danger-signals.md",
      "lines": 13,
      "nonempty": 7,
      "tokens": 975,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/anti-patterns.md",
      "lines": 39,
      "nonempty": 36,
      "tokens": 1060,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/checklists/danger-signals.md",
      "lines": 25,
      "nonempty": 21,
      "tokens": 635,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/confidence-scoring.md",
      "lines": 31,
      "nonempty": 26,
      "tokens": 736,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/go-root-cause-patterns.md",
      "lines": 43,
      "nonempty": 37,
      "tokens": 939,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/oracle-escalation.md",
      "lines": 37,
      "nonempty": 26,
      "tokens": 596,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/rca-feedback-template.md",
      "lines": 18,
      "nonempty": 15,
      "tokens": 462,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/repair-loop-rules.md",
      "lines": 21,
      "nonempty": 16,
      "tokens": 646,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/templates/blocked.md",
      "lines": 13,
      "nonempty": 11,
      "tokens": 416,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/templates/immunity-failed.md",
      "lines": 11,
      "nonempty": 9,
      "tokens": 254,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/templates/normal-completion.md",
      "lines": 12,
      "nonempty": 10,
      "tokens": 946,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/templates/not-applicable.md",
      "lines": 13,
      "nonempty": 12,
      "tokens": 210,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/templates/oracle-consultation.md",
      "lines": 12,
      "nonempty": 10,
      "tokens": 318,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-root-cause-analysis/references/tool-output-rules.md",
      "lines": 28,
      "nonempty": 19,
      "tokens": 634,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/abort-conditions.md",
      "lines": 11,
      "nonempty": 10,
      "tokens": 236,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/batch-accept-template.md",
      "lines": 618,
      "nonempty": 490,
      "tokens": 19021,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/commit-convention.md",
      "lines": 28,
      "nonempty": 22,
      "tokens": 346,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/context-retention.md",
      "lines": 10,
      "nonempty": 9,
      "tokens": 269,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/error-recovery-table.md",
      "lines": 13,
      "nonempty": 12,
      "tokens": 432,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/frontend-coding-rules.md",
      "lines": 16,
      "nonempty": 11,
      "tokens": 343,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/gate-checklist.md",
      "lines": 41,
      "nonempty": 37,
      "tokens": 755,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/go-coding-rules.md",
      "lines": 19,
      "nonempty": 13,
      "tokens": 409,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/milestone-rules.md",
      "lines": 22,
      "nonempty": 17,
      "tokens": 418,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/phase-transition-rules.md",
      "lines": 14,
      "nonempty": 13,
      "tokens": 338,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/progress-file-template.md",
      "lines": 34,
      "nonempty": 22,
      "tokens": 848,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/progress-panel-template.md",
      "lines": 31,
      "nonempty": 22,
      "tokens": 1004,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/protocol-table.md",
      "lines": 11,
      "nonempty": 10,
      "tokens": 218,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/root-cause-protocol.md",
      "lines": 6,
      "nonempty": 5,
      "tokens": 371,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/security-scan-rules.md",
      "lines": 30,
      "nonempty": 18,
      "tokens": 348,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/skill-linkage-table.md",
      "lines": 14,
      "nonempty": 13,
      "tokens": 474,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/skill-mapping-table.md",
      "lines": 16,
      "nonempty": 15,
      "tokens": 396,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/executor.md",
      "lines": 66,
      "nonempty": 42,
      "tokens": 1040,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/plan.md",
      "lines": 87,
      "nonempty": 59,
      "tokens": 1108,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/research.md",
      "lines": 57,
      "nonempty": 38,
      "tokens": 834,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/templates/executor.md",
      "lines": 30,
      "nonempty": 16,
      "tokens": 1027,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/templates/plan.md",
      "lines": 35,
      "nonempty": 18,
      "tokens": 1085,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-rpe/references/templates/templates/research.md",
      "lines": 23,
      "nonempty": 12,
      "tokens": 819,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/checklists/danger-signals.md",
      "lines": 15,
      "nonempty": 14,
      "tokens": 233,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/exclusion-patterns.md",
      "lines": 10,
      "nonempty": 9,
      "tokens": 85,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/false-positive-rules.md",
      "lines": 13,
      "nonempty": 12,
      "tokens": 260,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/fix-templates.md",
      "lines": 88,
      "nonempty": 66,
      "tokens": 916,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/scan-rules.md",
      "lines": 34,
      "nonempty": 29,
      "tokens": 731,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-security-review/references/severity-levels.md",
      "lines": 8,
      "nonempty": 7,
      "tokens": 149,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-style-guide/references/checklists/danger-signals.md",
      "lines": 13,
      "nonempty": 7,
      "tokens": 608,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-task-spec/references/ac-template.md",
      "lines": 18,
      "nonempty": 14,
      "tokens": 309,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-task-spec/references/execution-modes.md",
      "lines": 10,
      "nonempty": 7,
      "tokens": 183,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-tdd-spec/references/behavior-matrix.md",
      "lines": 17,
      "nonempty": 15,
      "tokens": 249,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-tdd-spec/references/gwt-template.md",
      "lines": 17,
      "nonempty": 13,
      "tokens": 241,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-todo/references/execution-types.md",
      "lines": 48,
      "nonempty": 37,
      "tokens": 1653,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-todo/references/queue-format.md",
      "lines": 27,
      "nonempty": 25,
      "tokens": 640,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-todo/references/upgrade-protocol.md",
      "lines": 20,
      "nonempty": 16,
      "tokens": 504,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/skills/lx-web-perf/references/checklists/danger-signals.md",
      "lines": 13,
      "nonempty": 7,
      "tokens": 893,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/acceptance_report.md",
      "lines": 23,
      "nonempty": 15,
      "tokens": 127,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/alternatives_explored.md",
      "lines": 23,
      "nonempty": 17,
      "tokens": 307,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/criteria.md",
      "lines": 7,
      "nonempty": 6,
      "tokens": 78,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/executor.md",
      "lines": 12,
      "nonempty": 11,
      "tokens": 131,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/fallback_analysis.md",
      "lines": 21,
      "nonempty": 14,
      "tokens": 358,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/plan.md",
      "lines": 30,
      "nonempty": 22,
      "tokens": 286,
      "method": "tiktoken cl100k_base"
    },
    {
      "path": ".claude/task_sys/templates/summary.md",
      "lines": 9,
      "nonempty": 8,
      "tokens": 107,
      "method": "tiktoken cl100k_base"
    }
  ]
}
```

---
*Report auto-generated by `.claude/scripts/loading_benchmark.py`. Re-run to refresh.*
