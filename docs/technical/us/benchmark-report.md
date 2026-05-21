[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# Loading Benchmark Report
     2|
     3|**Generated:** 2026-05-04 09:07:31
     4|**Method:** tiktoken cl100k_base
     5|**Repository:** `/Users/lucas.liang/Desktop/Sylph/Carror_OS`
     6|**Data version:** Carror OS ≤ v6.1.8 (archived — current v6.2.1). The 8 skills listed below (lx-browser-verify, lx-react-review, lx-golang-test, lx-web-perf, lx-prd, lx-debug-spec, lx-security-review, lx-tdd-spec) were removed from core in v6.2.0. This report is a **historical benchmark snapshot** preserved for reference.
     7|
     8|---
     9|
    10|## 1. Method
    11|
    12|- **Token estimation:** Uses `tiktoken` with `cl100k_base` encoding (the same tokenizer
    13|  used by Claude models). This is an **estimate** -- actual LLM context usage depends on
    14|  the model's internal tokenization and system prompt overhead.
    15|- **Fallback:** If tiktoken is not installed, falls back to `chars // 4`, which is a
    16|  coarse estimate (~4 characters per token for English text). Fallback results are
    17|  labelled `[estimate: chars/4 fallback]`.
    18|- **Sample:** Single pass measurement of all `.md` files in `.claude/` + `CLAUDE.md` +
    19|  `AGENTS.md`. No repeated sampling (file contents are static).
    20|- **Limitations:**
    21|  1. Token counts are estimates, not exact LLM context measurements.
    22|  2. Does not account for system prompt size, conversation history, or tool definitions.
    23|  3. Single measurement -- no variance calculation (static content).
    24|  4. Only counts text content; binary/frontmatter parsing not applied.
    25|  5. Line counts are reported as total lines (including blanks) for comparison with
    26|     loading_matrix.md claims (which uses total lines). Non-empty line counts also included.
    27|
    28|---
    29|
    30|## 2. Layer Definitions
    31|
    32|| Layer | Contents | Load Strategy |
    33||-------|----------|--------------|
    34|| **L1** | `CLAUDE.md`, `AGENTS.md`, `kernel.md`, `anti-patterns.md`, `claude-next.md` | Always loaded at session start |
    35|| **L2** | All `SKILL.md` files, node system files (`.claude/nodes/`), on-demand `task_sys/` files (orchestrator, context_guard, mechanism_evals, loading_matrix, etc.) | Loaded on-demand when entering a specific phase or triggering a skill |
    36|| **L3** | Skill reference docs (`.claude/skills/*/references/`), task template files (`.claude/task_sys/templates/`) | Precision-loaded when performing a specific operation |
    37|
    38|---
    39|
    40|## 3. Condition Comparison
    41|
    42|### Condition A: Progressive Disclosure (L1 only)
    43|- Files: 5
    44|- Total lines (incl. blanks): 427
    45|- Non-empty lines: 311
    46|- Total tokens: 7,539
    47|
    48|### Condition B: Full Load (L1 + L2 + L3)
    49|- Files: 143
    50|- Total lines (incl. blanks): 9200
    51|- Non-empty lines: 6984
    52|- Total tokens: 172,994
    53|
    54|### Savings
    55|| Metric | Progressive (A) | Full (B) | Reduction |
    56||--------|----------------|----------|-----------|
    57|| Lines (incl. blanks) | 427 | 9200 | 95.4% |
    58|| Non-empty lines | 311 | 6984 | 95.5% |
    59|| Tokens | 7,539 | 172,994 | 95.6% |
    60|
    61|---
    62|
    63|## 4. Verification of loading_matrix.md Claims
    64|
    65|The loading matrix (`task_sys/loading_matrix.md`, line 89) claims:
    66|
    67|> "首次加载从 394 行 → ~120 行，减少 70%。"
    68|
    69|### Measured Results (total lines, including blanks)
    70|| Metric | Claimed | Measured |
    71||--------|---------|----------|
    72|| Full load (before) | ~394 lines | **9200 lines** |
    73|| Progressive (after) | ~120 lines | **427 lines** |
    74|| Reduction | ~70% | **95.4%** |
    75|
    76|**Verdict (total lines):** NOTE - measured values differ from claimed values
    77|
    78|### Alternative: Non-empty lines
    79|| Metric | Claimed | Measured |
    80||--------|---------|----------|
    81|| Full load (before) | ~394 lines | **6984 lines** |
    82|| Progressive (after) | ~120 lines | **311 lines** |
    83|| Reduction | ~70% | **95.5%** |
    84|
    85|**Verdict (non-empty):** NOTE - measured values differ from claimed values
    86|
    87|---
    88|
    89|## 5. Structure Report
    90|
    91|### L1 Files (always loaded)
    92|| path                     | lines | nonempty | tokens | method               |
    93|| ------------------------ | ----- | -------- | ------ | -------------------- |
    94|| CLAUDE.md                | 17    | 13       | 197    | tiktoken cl100k_base |
    95|| AGENTS.md                | 232   | 168      | 3180   | tiktoken cl100k_base |
    96|| .claude/kernel.md        | 30    | 20       | 410    | tiktoken cl100k_base |
    97|| .claude/anti-patterns.md | 117   | 89       | 2878   | tiktoken cl100k_base |
    98|| .claude/claude-next.md   | 31    | 21       | 874    | tiktoken cl100k_base |
    99|
   100|### L2 Files (on-demand)
   101|| path                                           | lines | nonempty | tokens | method               |
   102|| ---------------------------------------------- | ----- | -------- | ------ | -------------------- |
   103|| .claude/skills/lx-browser-verify/SKILL.md      | 113   | 80       | 2322   | tiktoken cl100k_base |
   104|| .claude/skills/lx-code-review/SKILL.md         | 174   | 133      | 4149   | tiktoken cl100k_base |
   105|| .claude/skills/lx-debug-spec/SKILL.md          | 201   | 142      | 3652   | tiktoken cl100k_base |
   106|| .claude/skills/lx-frontend-test/SKILL.md       | 9     | 8        | 257    | tiktoken cl100k_base |
   107|| .claude/skills/lx-golang-test/SKILL.md         | 133   | 98       | 1753   | tiktoken cl100k_base |
   108|| .claude/skills/lx-oma/SKILL.md                 | 55    | 36       | 944    | tiktoken cl100k_base |
   109|| .claude/skills/lx-perf-analysis/SKILL.md       | 151   | 114      | 2684   | tiktoken cl100k_base |
   110|| .claude/skills/lx-prd/SKILL.md                 | 369   | 282      | 8333   | tiktoken cl100k_base |
   111|| .claude/skills/lx-pre-commit/SKILL.md          | 69    | 44       | 942    | tiktoken cl100k_base |
   112|| .claude/skills/lx-pre-push/SKILL.md            | 89    | 59       | 1214   | tiktoken cl100k_base |
   113|| .claude/skills/lx-react-review/SKILL.md        | 149   | 112      | 3172   | tiktoken cl100k_base |
   114|| .claude/skills/lx-root-cause-analysis/SKILL.md | 211   | 168      | 5864   | tiktoken cl100k_base |
   115|| .claude/skills/lx-rpe/SKILL.md                 | 1052  | 914      | 15695  | tiktoken cl100k_base |
   116|| .claude/skills/lx-security-review/SKILL.md     | 127   | 95       | 2431   | tiktoken cl100k_base |
   117|| .claude/skills/lx-status/SKILL.md              | 50    | 33       | 529    | tiktoken cl100k_base |
   118|| .claude/skills/lx-style-guide/SKILL.md         | 128   | 94       | 2669   | tiktoken cl100k_base |
   119|| .claude/skills/lx-task-spec/SKILL.md           | 194   | 151      | 3312   | tiktoken cl100k_base |
   120|| .claude/skills/lx-tdd-spec/SKILL.md            | 140   | 106      | 3540   | tiktoken cl100k_base |
   121|| .claude/skills/lx-todo/SKILL.md                | 293   | 229      | 6188   | tiktoken cl100k_base |
   122|| .claude/skills/lx-validate-skill/SKILL.md      | 159   | 112      | 1897   | tiktoken cl100k_base |
   123|| .claude/skills/lx-varlock/SKILL.md             | 68    | 47       | 1175   | tiktoken cl100k_base |
   124|| .claude/skills/lx-web-perf/SKILL.md            | 133   | 97       | 2745   | tiktoken cl100k_base |
   125|| .claude/nodes/a_terminal.md                    | 70    | 45       | 707    | tiktoken cl100k_base |
   126|| .claude/nodes/auto_fixer.md                    | 45    | 37       | 543    | tiktoken cl100k_base |
   127|| .claude/nodes/b_terminal.md                    | 77    | 47       | 734    | tiktoken cl100k_base |
   128|| .claude/nodes/behavior_rules.md                | 198   | 135      | 2968   | tiktoken cl100k_base |
   129|| .claude/nodes/context_collector.md             | 14    | 8        | 147    | tiktoken cl100k_base |
   130|| .claude/nodes/execute_node.md                  | 89    | 64       | 1095   | tiktoken cl100k_base |
   131|| .claude/nodes/gate_checker.md                  | 42    | 34       | 457    | tiktoken cl100k_base |
   132|| .claude/nodes/generator.md                     | 43    | 35       | 466    | tiktoken cl100k_base |
   133|| .claude/nodes/interactive_prompt.md            | 56    | 42       | 1293   | tiktoken cl100k_base |
   134|| .claude/nodes/orchestrator.md                  | 71    | 51       | 886    | tiktoken cl100k_base |
   135|| .claude/nodes/report_generator.md              | 54    | 42       | 493    | tiktoken cl100k_base |
   136|| .claude/nodes/scanner.md                       | 60    | 50       | 678    | tiktoken cl100k_base |
   137|| .claude/nodes/target_resolver.md               | 43    | 35       | 515    | tiktoken cl100k_base |
   138|| .claude/nodes/verifier.md                      | 46    | 38       | 505    | tiktoken cl100k_base |
   139|| .claude/task_sys/context_guard.md              | 93    | 72       | 1433   | tiktoken cl100k_base |
   140|| .claude/task_sys/mechanism_evals.md            | 88    | 63       | 1496   | tiktoken cl100k_base |
   141|| .claude/task_sys/loading_matrix.md             | 101   | 84       | 1739   | tiktoken cl100k_base |
   142|| .claude/task_sys/orchestrator.md               | 125   | 87       | 2204   | tiktoken cl100k_base |
   143|| .claude/task_sys/unified_delivery_schema.md    | 66    | 52       | 938    | tiktoken cl100k_base |
   144|| .claude/task_sys/task_fs.md                    | 37    | 31       | 447    | tiktoken cl100k_base |
   145|
   146|### L3 Files (precision-loaded)
   147|| path                                                                              | lines | nonempty | tokens | method               |
   148|| --------------------------------------------------------------------------------- | ----- | -------- | ------ | -------------------- |
   149|| .claude/skills/lx-browser-verify/references/checklists/danger-signals.md          | 13    | 7        | 527    | tiktoken cl100k_base |
   150|| .claude/skills/lx-code-review/references/checklists/danger-signals.md             | 11    | 6        | 506    | tiktoken cl100k_base |
   151|| .claude/skills/lx-code-review/references/knowledge/review-rules.md                | 20    | 16       | 404    | tiktoken cl100k_base |
   152|| .claude/skills/lx-debug-spec/references/checklists/danger-signals.md              | 35    | 33       | 491    | tiktoken cl100k_base |
   153|| .claude/skills/lx-debug-spec/references/condition-based-waiting.md                | 59    | 43       | 629    | tiktoken cl100k_base |
   154|| .claude/skills/lx-debug-spec/references/defense-in-depth.md                       | 31    | 20       | 411    | tiktoken cl100k_base |
   155|| .claude/skills/lx-debug-spec/references/root-cause-tracing.md                     | 33    | 23       | 457    | tiktoken cl100k_base |
   156|| .claude/skills/lx-debug-spec/references/templates/normal-completion.md            | 9     | 8        | 257    | tiktoken cl100k_base |
   157|| .claude/skills/lx-frontend-test/references/checklists/danger-signals.md           | 13    | 7        | 753    | tiktoken cl100k_base |
   158|| .claude/skills/lx-golang-test/references/checklists/danger-signals.md             | 15    | 14       | 201    | tiktoken cl100k_base |
   159|| .claude/skills/lx-golang-test/references/checklists/usability-v01-v12.md          | 18    | 17       | 258    | tiktoken cl100k_base |
   160|| .claude/skills/lx-golang-test/references/commands-quickref.md                     | 43    | 30       | 306    | tiktoken cl100k_base |
   161|| .claude/skills/lx-golang-test/references/go-version-matrix.md                     | 9     | 8        | 136    | tiktoken cl100k_base |
   162|| .claude/skills/lx-golang-test/references/knowledge/benchmarks.md                  | 21    | 15       | 220    | tiktoken cl100k_base |
   163|| .claude/skills/lx-golang-test/references/knowledge/cicd.md                        | 23    | 15       | 206    | tiktoken cl100k_base |
   164|| .claude/skills/lx-golang-test/references/knowledge/coverage.md                    | 15    | 9        | 134    | tiktoken cl100k_base |
   165|| .claude/skills/lx-golang-test/references/knowledge/fuzzing.md                     | 22    | 15       | 240    | tiktoken cl100k_base |
   166|| .claude/skills/lx-golang-test/references/knowledge/golden-files.md                | 14    | 10       | 205    | tiktoken cl100k_base |
   167|| .claude/skills/lx-golang-test/references/knowledge/helpers.md                     | 11    | 8        | 195    | tiktoken cl100k_base |
   168|| .claude/skills/lx-golang-test/references/knowledge/http-handler.md                | 13    | 10       | 309    | tiktoken cl100k_base |
   169|| .claude/skills/lx-golang-test/references/knowledge/mocking.md                     | 30    | 21       | 248    | tiktoken cl100k_base |
   170|| .claude/skills/lx-golang-test/references/knowledge/race-condition.md              | 31    | 21       | 276    | tiktoken cl100k_base |
   171|| .claude/skills/lx-golang-test/references/knowledge/subtests.md                    | 14    | 9        | 171    | tiktoken cl100k_base |
   172|| .claude/skills/lx-golang-test/references/knowledge/table-driven.md                | 17    | 13       | 360    | tiktoken cl100k_base |
   173|| .claude/skills/lx-golang-test/references/mock-strategy-quickref.md                | 11    | 10       | 147    | tiktoken cl100k_base |
   174|| .claude/skills/lx-perf-analysis/references/checklists/danger-signals.md           | 11    | 6        | 473    | tiktoken cl100k_base |
   175|| .claude/skills/lx-perf-analysis/references/knowledge/optimization-patterns.md     | 126   | 94       | 1693   | tiktoken cl100k_base |
   176|| .claude/skills/lx-perf-analysis/references/knowledge/profiling-guide.md           | 104   | 65       | 1212   | tiktoken cl100k_base |
   177|| .claude/skills/lx-prd/references/appendix-templates.md                            | 90    | 62       | 738    | tiktoken cl100k_base |
   178|| .claude/skills/lx-prd/references/full-flow-diagram.md                             | 9     | 7        | 420    | tiktoken cl100k_base |
   179|| .claude/skills/lx-prd/references/mermaid-templates.md                             | 60    | 43       | 1085   | tiktoken cl100k_base |
   180|| .claude/skills/lx-prd/references/polish-workflow.md                               | 21    | 16       | 730    | tiktoken cl100k_base |
   181|| .claude/skills/lx-prd/references/prd-toc-template.md                              | 19    | 11       | 547    | tiktoken cl100k_base |
   182|| .claude/skills/lx-prd/references/scoring.md                                       | 86    | 73       | 1758   | tiktoken cl100k_base |
   183|| .claude/skills/lx-prd/references/self-eval-checklist.md                           | 18    | 16       | 430    | tiktoken cl100k_base |
   184|| .claude/skills/lx-pre-push/references/commit-convention-guide.md                  | 36    | 25       | 345    | tiktoken cl100k_base |
   185|| .claude/skills/lx-react-review/references/checklists/danger-signals.md            | 13    | 7        | 975    | tiktoken cl100k_base |
   186|| .claude/skills/lx-root-cause-analysis/references/anti-patterns.md                 | 39    | 36       | 1060   | tiktoken cl100k_base |
   187|| .claude/skills/lx-root-cause-analysis/references/checklists/danger-signals.md     | 25    | 21       | 635    | tiktoken cl100k_base |
   188|| .claude/skills/lx-root-cause-analysis/references/confidence-scoring.md            | 31    | 26       | 736    | tiktoken cl100k_base |
   189|| .claude/skills/lx-root-cause-analysis/references/go-root-cause-patterns.md        | 43    | 37       | 939    | tiktoken cl100k_base |
   190|| .claude/skills/lx-root-cause-analysis/references/oracle-escalation.md             | 37    | 26       | 596    | tiktoken cl100k_base |
   191|| .claude/skills/lx-root-cause-analysis/references/rca-feedback-template.md         | 18    | 15       | 462    | tiktoken cl100k_base |
   192|| .claude/skills/lx-root-cause-analysis/references/repair-loop-rules.md             | 21    | 16       | 646    | tiktoken cl100k_base |
   193|| .claude/skills/lx-root-cause-analysis/references/templates/blocked.md             | 13    | 11       | 416    | tiktoken cl100k_base |
   194|| .claude/skills/lx-root-cause-analysis/references/templates/immunity-failed.md     | 11    | 9        | 254    | tiktoken cl100k_base |
   195|| .claude/skills/lx-root-cause-analysis/references/templates/normal-completion.md   | 12    | 10       | 946    | tiktoken cl100k_base |
   196|| .claude/skills/lx-root-cause-analysis/references/templates/not-applicable.md      | 13    | 12       | 210    | tiktoken cl100k_base |
   197|| .claude/skills/lx-root-cause-analysis/references/templates/oracle-consultation.md | 12    | 10       | 318    | tiktoken cl100k_base |
   198|| .claude/skills/lx-root-cause-analysis/references/tool-output-rules.md             | 28    | 19       | 634    | tiktoken cl100k_base |
   199|| .claude/skills/lx-rpe/references/abort-conditions.md                              | 11    | 10       | 236    | tiktoken cl100k_base |
   200|| .claude/skills/lx-rpe/references/batch-accept-template.md                         | 618   | 490      | 19021  | tiktoken cl100k_base |
   201|| .claude/skills/lx-rpe/references/commit-convention.md                             | 28    | 22       | 346    | tiktoken cl100k_base |
   202|| .claude/skills/lx-rpe/references/context-retention.md                             | 10    | 9        | 269    | tiktoken cl100k_base |
   203|| .claude/skills/lx-rpe/references/error-recovery-table.md                          | 13    | 12       | 432    | tiktoken cl100k_base |
   204|| .claude/skills/lx-rpe/references/frontend-coding-rules.md                         | 16    | 11       | 343    | tiktoken cl100k_base |
   205|| .claude/skills/lx-rpe/references/gate-checklist.md                                | 41    | 37       | 755    | tiktoken cl100k_base |
   206|| .claude/skills/lx-rpe/references/go-coding-rules.md                               | 19    | 13       | 409    | tiktoken cl100k_base |
   207|| .claude/skills/lx-rpe/references/milestone-rules.md                               | 22    | 17       | 418    | tiktoken cl100k_base |
   208|| .claude/skills/lx-rpe/references/phase-transition-rules.md                        | 14    | 13       | 338    | tiktoken cl100k_base |
   209|| .claude/skills/lx-rpe/references/progress-file-template.md                        | 34    | 22       | 848    | tiktoken cl100k_base |
   210|| .claude/skills/lx-rpe/references/progress-panel-template.md                       | 31    | 22       | 1004   | tiktoken cl100k_base |
   211|| .claude/skills/lx-rpe/references/protocol-table.md                                | 11    | 10       | 218    | tiktoken cl100k_base |
   212|| .claude/skills/lx-rpe/references/root-cause-protocol.md                           | 6     | 5        | 371    | tiktoken cl100k_base |
   213|| .claude/skills/lx-rpe/references/security-scan-rules.md                           | 30    | 18       | 348    | tiktoken cl100k_base |
   214|| .claude/skills/lx-rpe/references/skill-linkage-table.md                           | 14    | 13       | 474    | tiktoken cl100k_base |
   215|| .claude/skills/lx-rpe/references/skill-mapping-table.md                           | 16    | 15       | 396    | tiktoken cl100k_base |
   216|| .claude/skills/lx-rpe/references/templates/executor.md                            | 66    | 42       | 1040   | tiktoken cl100k_base |
   217|| .claude/skills/lx-rpe/references/templates/plan.md                                | 87    | 59       | 1108   | tiktoken cl100k_base |
   218|| .claude/skills/lx-rpe/references/templates/research.md                            | 57    | 38       | 834    | tiktoken cl100k_base |
   219|| .claude/skills/lx-rpe/references/templates/templates/executor.md                  | 30    | 16       | 1027   | tiktoken cl100k_base |
   220|| .claude/skills/lx-rpe/references/templates/templates/plan.md                      | 35    | 18       | 1085   | tiktoken cl100k_base |
   221|| .claude/skills/lx-rpe/references/templates/templates/research.md                  | 23    | 12       | 819    | tiktoken cl100k_base |
   222|| .claude/skills/lx-security-review/references/checklists/danger-signals.md         | 15    | 14       | 233    | tiktoken cl100k_base |
   223|| .claude/skills/lx-security-review/references/exclusion-patterns.md                | 10    | 9        | 85     | tiktoken cl100k_base |
   224|| .claude/skills/lx-security-review/references/false-positive-rules.md              | 13    | 12       | 260    | tiktoken cl100k_base |
   225|| .claude/skills/lx-security-review/references/fix-templates.md                     | 88    | 66       | 916    | tiktoken cl100k_base |
   226|| .claude/skills/lx-security-review/references/scan-rules.md                        | 34    | 29       | 731    | tiktoken cl100k_base |
   227|| .claude/skills/lx-security-review/references/severity-levels.md                   | 8     | 7        | 149    | tiktoken cl100k_base |
   228|| .claude/skills/lx-style-guide/references/checklists/danger-signals.md             | 13    | 7        | 608    | tiktoken cl100k_base |
   229|| .claude/skills/lx-task-spec/references/ac-template.md                             | 18    | 14       | 309    | tiktoken cl100k_base |
   230|| .claude/skills/lx-task-spec/references/execution-modes.md                         | 10    | 7        | 183    | tiktoken cl100k_base |
   231|| .claude/skills/lx-tdd-spec/references/behavior-matrix.md                          | 17    | 15       | 249    | tiktoken cl100k_base |
   232|| .claude/skills/lx-tdd-spec/references/gwt-template.md                             | 17    | 13       | 241    | tiktoken cl100k_base |
   233|| .claude/skills/lx-todo/references/execution-types.md                              | 48    | 37       | 1653   | tiktoken cl100k_base |
   234|| .claude/skills/lx-todo/references/queue-format.md                                 | 27    | 25       | 640    | tiktoken cl100k_base |
   235|| .claude/skills/lx-todo/references/upgrade-protocol.md                             | 20    | 16       | 504    | tiktoken cl100k_base |
   236|| .claude/skills/lx-web-perf/references/checklists/danger-signals.md                | 13    | 7        | 893    | tiktoken cl100k_base |
   237|| .claude/task_sys/templates/acceptance_report.md                                   | 23    | 15       | 127    | tiktoken cl100k_base |
   238|| .claude/task_sys/templates/alternatives_explored.md                               | 23    | 17       | 307    | tiktoken cl100k_base |
   239|| .claude/task_sys/templates/criteria.md                                            | 7     | 6        | 78     | tiktoken cl100k_base |
   240|| .claude/task_sys/templates/executor.md                                            | 12    | 11       | 131    | tiktoken cl100k_base |
   241|| .claude/task_sys/templates/fallback_analysis.md                                   | 21    | 14       | 358    | tiktoken cl100k_base |
   242|| .claude/task_sys/templates/plan.md                                                | 30    | 22       | 286    | tiktoken cl100k_base |
   243|| .claude/task_sys/templates/summary.md                                             | 9     | 8        | 107    | tiktoken cl100k_base |
   244|
   245|### Layer Summary
   246|| Layer | Files | Lines | Non-empty | Tokens |
   247||-------|-------|-------|-----------|--------|
   248|| L1 | 5 | 427 | 311 | 7,539 |
   249|| L2 | 43 | 5638 | 4317 | 97,963 |
   250|| L3 | 95 | 3135 | 2356 | 67,492 |
   251|| **Total (A: progressive)** | **5** | **427** | **311** | **7,539** |
   252|| **Total (B: full)** | **143** | **9200** | **6984** | **172,994** |
   253|
   254|---
   255|
   256|## 6. Token 节省估算公式
   257|
   258|### L3 Reference 按需加载
   259|```
   260|池均值   = L3总分担 / skill数             = 67,492 ÷ 17 ≈ 3,970 tok/skill
   261|单文件均 = L3总分担 / ref文件数            = 67,492 ÷ 95 ≈ 710 tok/文件
   262|每次触发 = 池均值 - 单文件均               ≈ 3,260 tok/次 skill 触发
   263|会话总计 = skill 触发次数 × 每次触发节省
   264|```
   265|
   266|**口径**：假设无渐进式时 skill 触发加载该 skill 全部 reference；有渐进式时只加载命中的（~1 文件）。实际节省量随 skill 的 reference 数波动（如 lx-rpe 池 ~19K tok，lx-golang-test 池 ~3K tok）。
   267|
   268|### CLAUDE.md 轻量化 (含 AGENTS.md)
   269|```
   270|每次会话节省 = 内联估算 - CLAUDE.md实际 - AGENTS.md
   271|             ≈ 9,400 - 160 - 3,180 = 6,060 tok/session
   272|```
   273|无 Carror OS 时 AGENTS.md 的内容也在 CLAUDE.md 内，净节省需扣除 AGENTS 加载成本。
   274|
   275|### Compact 节流
   276|```
   277|首次节省 ≈ 200K × 50% - 基线上下文  ≈ 100K - 39K ≈ 61K tok
   278|实际节省更多（transcript 实测一次 compact 即 112K tok）
   279|```
   280|Compact 发生在上下文接近 200K 限时，压缩后约剩 50%。实际节省量取决于压缩前的实际上下文大小，通常多于保守估算。
   281|
   282|---
   283|
   284|## 7. 20 轮会话节省结论（真实 transcript 推算）
   285|
   286|| 指标 | 无 Carror OS | 有 Carror OS | 节省量 | 比例 |
   287||------|-------------|-------------|--------|------|
   288|| Session start | 45,524 tok (CLAUDE.md 9,400) | 39,464 tok (L1 7,539) | +6,060 | |
   289|| 20 轮对话增长 | ~58,843 tok (19×~3,097) | ~58,843 tok | — | |
   290|| Skill 触发 (3 次) | ~11,910 tok (3×3,970 全加载) | ~2,130 tok (3×710 命中) | +9,780 | |
   291|| **Context 预估** | **~116,277 tok** | **~100,437 tok** | **~15,840** | **~14%** |
   292|| **含 1 次 Compact** | **~107,000 tok** | **~50,000 tok** | **~57,000** | **~53%** |
   293|
   294|**关键发现：**
   295|- 仅结构节省（轻量化 + 按需加载）在短会话中占比约 14%
   296|- Compact 是最大节省来源，一次压缩即可超出所有结构节省之和
   297|- 会话越长（>80 轮），Compact 触发概率越高，节省比例可达 50%+
   298|- 以上为 transcript 实测数据 + 启发式估算值，标注 `[估算]` 处为口径说明
   299|
   300|## 8. Limitations
   301|
   302|1. **Token estimation method:** tiktoken cl100k_base
   303|2. **Single sample:** File contents are static, so repeated measurements would yield identical results.
   304|3. **LLM context overhead:** This benchmark counts only file content tokens, not the system prompt,
   305|   conversation history, or tool/function definitions that also consume context window.
   306|4. **Line counts:** Both total lines (including blanks) and non-empty lines are reported.
   307|   The loading_matrix.md claim likely uses total lines.
   308|5. **File coverage:** Only scans `.claude/` governance/skill files.
   309|   External dependencies are not included.
   310|
   311|---
   312|
   313|## 8. Raw Data
   314|
   315|```json
   316|{
   317|  "timestamp": "2026-05-04T09:07:31.190050",
   318|  "method_hint": "tiktoken cl100k_base",
   319|  "condition_a": {
   320|    "label": "Progressive (L1 only)",
   321|    "files": 5,
   322|    "lines": 427,
   323|    "nonempty": 311,
   324|    "tokens": 7539
   325|  },
   326|  "condition_b": {
   327|    "label": "Full load (L1+L2+L3)",
   328|    "files": 143,
   329|    "lines": 9200,
   330|    "nonempty": 6984,
   331|    "tokens": 172994
   332|  },
   333|  "layer_summary": {
   334|    "L1": {
   335|      "file_count": 5,
   336|      "total_lines": 427,
   337|      "total_nonempty": 311,
   338|      "total_tokens": 7539
   339|    },
   340|    "L2": {
   341|      "file_count": 43,
   342|      "total_lines": 5638,
   343|      "total_nonempty": 4317,
   344|      "total_tokens": 97963
   345|    },
   346|    "L3": {
   347|      "file_count": 95,
   348|      "total_lines": 3135,
   349|      "total_nonempty": 2356,
   350|      "total_tokens": 67492
   351|    }
   352|  },
   353|  "claim_verification": {
   354|    "claim": "首次加载从 394 行 → ~120 行，减少 70%",
   355|    "measured_full_lines": 9200,
   356|    "measured_progressive_lines": 427,
   357|    "measured_full_nonempty": 6984,
   358|    "measured_progressive_nonempty": 311,
   359|    "measured_reduction_pct_total_lines": 95.4,
   360|    "measured_reduction_pct_nonempty": 95.5,
   361|    "verdict_total_lines": "differs",
   362|    "verdict_nonempty": "differs"
   363|  },
   364|  "file_details": [
   365|    {
   366|      "path": "CLAUDE.md",
   367|      "lines": 17,
   368|      "nonempty": 13,
   369|      "tokens": 197,
   370|      "method": "tiktoken cl100k_base"
   371|    },
   372|    {
   373|      "path": "AGENTS.md",
   374|      "lines": 232,
   375|      "nonempty": 168,
   376|      "tokens": 3180,
   377|      "method": "tiktoken cl100k_base"
   378|    },
   379|    {
   380|      "path": ".claude/kernel.md",
   381|      "lines": 30,
   382|      "nonempty": 20,
   383|      "tokens": 410,
   384|      "method": "tiktoken cl100k_base"
   385|    },
   386|    {
   387|      "path": ".claude/anti-patterns.md",
   388|      "lines": 117,
   389|      "nonempty": 89,
   390|      "tokens": 2878,
   391|      "method": "tiktoken cl100k_base"
   392|    },
   393|    {
   394|      "path": ".claude/claude-next.md",
   395|      "lines": 31,
   396|      "nonempty": 21,
   397|      "tokens": 874,
   398|      "method": "tiktoken cl100k_base"
   399|    },
   400|    {
   401|      "path": ".claude/skills/lx-browser-verify/SKILL.md",
   402|      "lines": 113,
   403|      "nonempty": 80,
   404|      "tokens": 2322,
   405|      "method": "tiktoken cl100k_base"
   406|    },
   407|    {
   408|      "path": ".claude/skills/lx-code-review/SKILL.md",
   409|      "lines": 174,
   410|      "nonempty": 133,
   411|      "tokens": 4149,
   412|      "method": "tiktoken cl100k_base"
   413|    },
   414|    {
   415|      "path": ".claude/skills/lx-debug-spec/SKILL.md",
   416|      "lines": 201,
   417|      "nonempty": 142,
   418|      "tokens": 3652,
   419|      "method": "tiktoken cl100k_base"
   420|    },
   421|    {
   422|      "path": ".claude/skills/lx-frontend-test/SKILL.md",
   423|      "lines": 9,
   424|      "nonempty": 8,
   425|      "tokens": 257,
   426|      "method": "tiktoken cl100k_base"
   427|    },
   428|    {
   429|      "path": ".claude/skills/lx-golang-test/SKILL.md",
   430|      "lines": 133,
   431|      "nonempty": 98,
   432|      "tokens": 1753,
   433|      "method": "tiktoken cl100k_base"
   434|    },
   435|    {
   436|      "path": ".claude/skills/lx-oma/SKILL.md",
   437|      "lines": 55,
   438|      "nonempty": 36,
   439|      "tokens": 944,
   440|      "method": "tiktoken cl100k_base"
   441|    },
   442|    {
   443|      "path": ".claude/skills/lx-perf-analysis/SKILL.md",
   444|      "lines": 151,
   445|      "nonempty": 114,
   446|      "tokens": 2684,
   447|      "method": "tiktoken cl100k_base"
   448|    },
   449|    {
   450|      "path": ".claude/skills/lx-prd/SKILL.md",
   451|      "lines": 369,
   452|      "nonempty": 282,
   453|      "tokens": 8333,
   454|      "method": "tiktoken cl100k_base"
   455|    },
   456|    {
   457|      "path": ".claude/skills/lx-pre-commit/SKILL.md",
   458|      "lines": 69,
   459|      "nonempty": 44,
   460|      "tokens": 942,
   461|      "method": "tiktoken cl100k_base"
   462|    },
   463|    {
   464|      "path": ".claude/skills/lx-pre-push/SKILL.md",
   465|      "lines": 89,
   466|      "nonempty": 59,
   467|      "tokens": 1214,
   468|      "method": "tiktoken cl100k_base"
   469|    },
   470|    {
   471|      "path": ".claude/skills/lx-react-review/SKILL.md",
   472|      "lines": 149,
   473|      "nonempty": 112,
   474|      "tokens": 3172,
   475|      "method": "tiktoken cl100k_base"
   476|    },
   477|    {
   478|      "path": ".claude/skills/lx-root-cause-analysis/SKILL.md",
   479|      "lines": 211,
   480|      "nonempty": 168,
   481|      "tokens": 5864,
   482|      "method": "tiktoken cl100k_base"
   483|    },
   484|    {
   485|      "path": ".claude/skills/lx-rpe/SKILL.md",
   486|      "lines": 1052,
   487|      "nonempty": 914,
   488|      "tokens": 15695,
   489|      "method": "tiktoken cl100k_base"
   490|    },
   491|    {
   492|      "path": ".claude/skills/lx-security-review/SKILL.md",
   493|      "lines": 127,
   494|      "nonempty": 95,
   495|      "tokens": 2431,
   496|      "method": "tiktoken cl100k_base"
   497|    },
   498|    {
   499|      "path": ".claude/skills/lx-status/SKILL.md",
   500|      "lines": 50,
   501|