[ARCHIVED v6.2.1 — Historical test record. Referenced hooks/scripts may no longer exist.]

     1|# Carror OS Ultimate Manual Acceptance Checklist (Final Exam)
     2|
     3|> **Positioning**: Pre-dogfooding survival threshold.
     4|> **Principle**: Zero trust. Nothing the AI says counts. Every single item in this document must be executed by you personally to count.
     5|> **Execution environment**: Enter project root `cd @`
     6|> **Version constraint**: Applicable to v6.1.8 and all prior mechanisms.
     7|
     8|---
     9|
    10|## Zone 1: Static Provisions and Entry Anchoring (Foundation Defense)
    11|
    12|> **Test purpose**: Verify that the framework's "iron laws" exist in physical files. If the source is lost, the LLM will completely lose control.
    13|> **Expected benefit**: Ensure that after any new environment deployment, the AI's very first token will load our supreme constitution.
    14|
    15|### [S12] CLAUDE.md Dual Entry Point Architecture Verification (v1.0)
    16|- **Why**: Claude Code natively only reads `CLAUDE.md`. Without an entry point, the global constitution `AGENTS.md` is worthless.
    17|- **Benefit**: Ensures the constitution is forcibly injected into System Prompt at every session start.
    18|- **Execute**: `head -1 CLAUDE.md` (expected output `@AGENTS.md`)
    19|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    20|
    21|### [S8~S11] Core Governance Provisions Existence Verification (v1.0 - v4.0)
    22|- **Why**: Without explicit "prohibited terms" and "fuse conditions," the AI will retry infinitely and use vague language to evade.
    23|- **Benefit**: Completely eliminate the AI's "I'm done" hallucination, standardize permission requests.
    24|- **Execute**:
    25|```bash
    26|grep -A 20 "软完成语禁令" AGENTS.md | head -5 # S8 Soft completion ban
    27|grep -A 10 "权限申请透明" AGENTS.md           # S9 Permission transparency clause
    28|grep -A 15 "证据层级" AGENTS.md               # S10 Evidence hierarchy system
    29|grep -A 8 "修复上限" AGENTS.md                # S11 Repair limit three-round fuse
    30|```
    31|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    32|
    33|### [M14, M15, L5] harness.yaml Mechanism Configuration Verification (v5.x)
    34|- **Why**: YAML configuration is the dynamic switch of the entire framework; missing means mechanism failure.
    35|- **Benefit**: Ensures coupling analysis, knowledge sublimation, and large task decomposition specifications are usable.
    36|- **Execute**:
    37|```bash
    38|grep -A 6 "^coupling:" .claude/harness.yaml           # M14 Coupling analysis mechanism
    39|grep -A 5 "^sublimation:" .claude/harness.yaml         # M15 Knowledge sublimation threshold
    40|grep -A 20 "task_decomposition:" .claude/harness.yaml  # L5 Large task decomposition
    41|```
    42|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    43|
    44|---
    45|
    46|## Zone 2: Low-Level Independent Gate Interception (Core Safety Barrier)
    47|
    48|> **Test purpose**: Verify that when the AI breaks through prompt constraints and attempts dangerous actions, the OS's underlying scripts can physically block them like pulling the power plug.
    49|> **Expected benefit**: Ensure absolute security of local file system, environment variables, and production code when the AI is completely out of control.
    50|
    51|### [S4] Permission Gate Database Deletion Intercept (v1.0)
    52|- **Why**: LLMs sometimes decide to execute `rm -rf` to "clean the environment" on their own.
    53|- **Benefit**: Intercepts all destructive system commands, converts to human approval workflow.
    54|- **Execute**: `echo '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' | bash .claude/hooks/permission-gate.sh`
    55|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    56|
    57|### [S6] Subagent Guard Sub-Agent Runaway Intercept (v2.0)
    58|- **Why**: If the LLM indefinitely spawns other LLMs, it causes bill avalanche.
    59|- **Benefit**: Forces high-consumption Agents to set `max_turns`.
    60|- **Execute**: `echo '{"tool_input":{"subagent_type":"executor"}}' | bash .claude/hooks/subagent-guard.sh task`
    61|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    62|
    63|### [S1] Privacy Gate Defense Intercept (v6.0.5)
    64|- **Why**: LLMs easily read `.env` and send real company keys to cloud APIs.
    65|- **Benefit**: Physically cuts off sniffing of password files, intercepts plaintext token execution.
    66|- **Execute**: `echo '{"tool":"read","tool_input":{"file_path":"config/.env"}}' | bash .claude/hooks/privacy-gate.sh`
    67|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    68|
    69|### [S2] Context Guard 80% OOM Physical Fuse (v6.0.6)
    70|- **Why**: When context exceeds 80% (e.g., 160K), the model becomes "brain-dead," wildly deleting and modifying working code.
    71|- **Benefit**: Physically locks all write operations, forcing the user to compress the session.
    72|- **Execute**: `echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool":"edit","tool_input":{"file_path":"main.go"}}' | bash .claude/hooks/context-guard.sh`
    73|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    74|
    75|### [S3] Completion Gate Strong Evidence Gate (v4.0)
    76|- **Why**: Prevents the AI from lying that "it's done."
    77|- **Benefit**: Must provide test logs containing `VERIFIED` to close the task.
    78|- **Execute**: `rm -f /tmp/.completion-evidence-$(date +%Y%m%d) && echo '{"tool":"task","tool_input":{"status":"completed"}}' | bash .claude/hooks/completion-gate.sh`
    79|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    80|
    81|### [M18, M19] CI Commit Gate Verification (v5.x)
    82|- **Why**: Non-compliant code or commit messages pollute the codebase.
    83|- **Benefit**: Auto-run tests before commit (lx-pre-commit), validate format before push (lx-pre-push).
    84|- **Execute**: `ls .claude/skills/lx-pre-commit/scripts/ && ls .claude/skills/lx-pre-push/scripts/`
    85|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    86|
    87|### [M10] Plan Gate Document Gate (v6.0.0)
    88|- **Why**: LLM skips research and directly writes code.
    89|- **Benefit**: Before editing plan.md, reminds to confirm Research Gate has passed.
    90|- **Execute**: `mkdir -p rpe/test-feature && echo '{"tool_input":{"file_path":"rpe/test-feature/plan.md","new_content":"# Plan"}}' | bash .claude/hooks/plan-gate.sh edit`
    91|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
    92|
    93|---
    94|
    95|## Zone 3: Lifecycle Integration Test (Advanced State Transition)
    96|
    97|> **Test purpose**: Verify that multiple distributed scripts can tightly mesh in a complete lifecycle, driving state machine transitions.
    98|> **Expected benefit**: Ensure a fully automated closed loop from "block" to "self-heal" to "experience solidification."
    99|
   100|### [L1, S5] Read-before-Edit Timing and Scope Freeze (v3.0)
   101|- **Why**: LLMs often edit without reading the original file, or modify files outside the task scope.
   102|- **Benefit**: Physically forces the AI to "read before writing" and locks it within the defined file sandbox.
   103|- **Execute**: Clear `.omc/state/read-files.log`, execute `edit-guard.sh` (intercept); execute `read-tracker.sh` (allow); execute `pretool-edit-scope.sh` (scope validation).
   104|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   105|
   106|### [L3] Build Failure Self-Healing Chain (build-validator ↔ error-dna) (v4.0)
   107|- **Why**: LLM repeatedly makes the same compilation error.
   108|- **Benefit**: Automatically writes errors into the DNA library, avoiding similar errors next time.
   109|- **Execute**: Simulate `bash` failure input to `build-validator.sh`, then pass to `error-dna.sh`, check `error-dna.jsonl`.
   110|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   111|
   112|### [L2] Lesson Solidification and Sublimation Chain (user-correction ↔ write-cite) (v5.0)
   113|- **Why**: If a human verbally corrects the AI but doesn't start a new session, the AI never learns.
   114|- **Benefit**: Structurally deposits personal lessons into `claude-next.md`.
   115|- **Execute**: Simulate user input "wrong" to trigger `pretool-user-correction.sh`, then simulate write to trigger `posttool-write-cite.sh` format validation.
   116|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   117|
   118|### [L7, M4, M6] Session State Save and Knowledge Infusion (v5.1)
   119|- **Why**: Shutdown and restart lose all progress and rules.
   120|- **Benefit**: Auto-snapshot on shutdown (auto-snapshot), auto-read snapshot and inject iron laws on startup (inject-project-knowledge).
   121|- **Execute**: Trigger `auto-snapshot.sh`, check `session-handoff.md`; execute `inject-project-knowledge.sh`, view output.
   122|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   123|
   124|### [S7, M7, M8, M9] Small Mechanism Integration (v4.0-v5.0)
   125|- **Why**: LLMs lack expert-level awareness when using tools.
   126|- **Benefit**: LSP smart reminder (S7), core file source reminder (M7), edit quality reuse detection (M8), Bash dangerous command post-audit (M9).
   127|- **Execute**: Check the logical existence of these 4 post-hooks individually.
   128|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   129|
   130|### [M1, M2, L6] Drift Prevention Electroshock Therapy (turn-counter ↔ rule-anchor) (v5.2.4)
   131|- **Why**: Long conversations cause AI to forget rules or accept "vague instructions."
   132|- **Benefit**: Every 10 rounds inject iron laws; after round 15, inject iron laws before writing; detect drift words like "continue," "while you're at it."
   133|- **Execute**: Modify `session-turns.json` to 16 rounds, input drift words, execute `pretool-rule-anchor.sh` and `turn-counter.sh`.
   134|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   135|
   136|---
   137|
   138|## Zone 4: Monitoring, Diagnostics, and Governance Flywheel (Observability)
   139|
   140|> **Test purpose**: Verify that data silently collected by the system in the background is accurate and can guide optimization.
   141|> **Expected benefit**: Make the black-box AI coding process completely transparent and quantifiable.
   142|
   143|### [M3] 50% Sweet Spot Proactive Handoff (v6.0.7)
   144|- **Why**: Model intelligence starts declining after 50% usage.
   145|- **Benefit**: When the model state is cleanest, gently remind the user to shift and restart, maintaining peak reasoning speed.
   146|- **Execute**: Modify Token tracking ratio to 55%, run `context_monitor.py`.
   147|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   148|
   149|### [M12, M13] Token Savings Quantified Bill (v6.0.3 & v6.1.0)
   150|- **Why**: Must prove to the team that "progressive disclosure" is not a pseudo-concept.
   151|- **Benefit**: Demonstrate business value with specific tokens saved and USD equivalent.
   152|- **Execute**: Verify `inject-project-knowledge.sh` uses summary mode; run `skill_trace_report.py --tokens-only`.
   153|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   154|
   155|### [M5, M11] Governance Flywheel Data Closed Loop (v6.1.1)
   156|- **Why**: The team doesn't know what high-frequency blocks the AI is encountering.
   157|- **Benefit**: `skill-flywheel.sh` flushes data; `flywheel-report.sh` generates the last 30 days of high-frequency alerts.
   158|- **Execute**: Write fake flywheel data, run `flywheel-report.sh`, view Markdown alert table.
   159|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   160|
   161|### [M17] lx-status Health Dashboard (v6.0.4)
   162|- **Why**: Data scattered everywhere, needs one-click visibility.
   163|- **Benefit**: Terminal three-screen display showing Token bill, self-heal rate, execution efficiency.
   164|- **Execute**: `ls .claude/skills/lx-status/` verify skill exists.
   165|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   166|
   167|---
   168|
   169|## Zone 5: One-Man Army Concurrent Architecture
   170|
   171|> **Test purpose**: Verify this is a distributed system capable of surviving extreme concurrent loads (multi-terminal writing to same disk).
   172|> **Expected benefit**: Give a single developer the throughput of a platoon, with zero code conflicts.
   173|
   174|### [L4] Microkernel Physical Lock and Deadlock Self-Heal (oma_lock_manager) (v6.1.5)
   175|- **Why**: Multi-agent concurrent writing leads to fatal mutual overwrites.
   176|- **Benefit**: Queue via OS mutex primitives; auto-crush deadlocks after 60s timeout.
   177|- **Execute**: Terminal A `acquire` holds; Terminal B tries `acquire`; verify `WAITING:` and timeout reclamation.
   178|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   179|
   180|### [M21] Polymorphic Orthogonal Decomposition Brain (lx-oma) (v6.1.5)
   181|- **Why**: Manually creating concurrent isolation zones is too slow; need to force AI to decompose requirements by MECE.
   182|- **Benefit**: Auto-generate highly isolated physical directory sandboxes `rpe/feat-X`.
   183|- **Execute**: Check `lx-oma/SKILL.md`, confirm polymorphic path and `mkdir -p` scaffolding logic.
   184|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   185|
   186|### [M16] Bidirectional Desensitization Proxy (lx-varlock) (v6.0.5)
   187|- **Why**: Plaintext keys in concurrent environments are extremely dangerous.
   188|- **Benefit**: LLM uses `{API_KEY}` placeholders; underlying Python substitutes real keys and bidirectionally obfuscates results.
   189|- **Execute**: `python3 .claude/skills/lx-varlock/scripts/varlock.py list`
   190|- **Feedback**: [ ] Pass / [ ] Fail | Notes:
   191|
   192|---
   193|
   194|**Human Signoff: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_**
   195|
   196|*Note: This document has undergone exhaustive audit and deep restructuring. All test points have been categorized and archived by architectural purpose.*
   197|