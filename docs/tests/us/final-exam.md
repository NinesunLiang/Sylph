# Carror OS Ultimate Manual Acceptance Checklist (Final Exam)

> **Positioning**: Pre-dogfooding survival threshold.
> **Principle**: Zero trust. Nothing the AI says counts. Every single item in this document must be executed by you personally to count.
> **Execution environment**: Enter project root `cd @`
> **Version constraint**: Applicable to v6.1.8 and all prior mechanisms.

---

## Zone 1: Static Provisions and Entry Anchoring (Foundation Defense)

> **Test purpose**: Verify that the framework's "iron laws" exist in physical files. If the source is lost, the LLM will completely lose control.
> **Expected benefit**: Ensure that after any new environment deployment, the AI's very first token will load our supreme constitution.

### [S12] CLAUDE.md Dual Entry Point Architecture Verification (v1.0)
- **Why**: Claude Code natively only reads `CLAUDE.md`. Without an entry point, the global constitution `AGENTS.md` is worthless.
- **Benefit**: Ensures the constitution is forcibly injected into System Prompt at every session start.
- **Execute**: `head -1 CLAUDE.md` (expected output `@AGENTS.md`)
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S8~S11] Core Governance Provisions Existence Verification (v1.0 - v4.0)
- **Why**: Without explicit "prohibited terms" and "fuse conditions," the AI will retry infinitely and use vague language to evade.
- **Benefit**: Completely eliminate the AI's "I'm done" hallucination, standardize permission requests.
- **Execute**:
```bash
grep -A 20 "软完成语禁令" AGENTS.md | head -5 # S8 Soft completion ban
grep -A 10 "权限申请透明" AGENTS.md           # S9 Permission transparency clause
grep -A 15 "证据层级" AGENTS.md               # S10 Evidence hierarchy system
grep -A 8 "修复上限" AGENTS.md                # S11 Repair limit three-round fuse
```
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M14, M15, L5] harness.yaml Mechanism Configuration Verification (v5.x)
- **Why**: YAML configuration is the dynamic switch of the entire framework; missing means mechanism failure.
- **Benefit**: Ensures coupling analysis, knowledge sublimation, and large task decomposition specifications are usable.
- **Execute**:
```bash
grep -A 6 "^coupling:" .claude/harness.yaml           # M14 Coupling analysis mechanism
grep -A 5 "^sublimation:" .claude/harness.yaml         # M15 Knowledge sublimation threshold
grep -A 20 "task_decomposition:" .claude/harness.yaml  # L5 Large task decomposition
```
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

---

## Zone 2: Low-Level Independent Gate Interception (Core Safety Barrier)

> **Test purpose**: Verify that when the AI breaks through prompt constraints and attempts dangerous actions, the OS's underlying scripts can physically block them like pulling the power plug.
> **Expected benefit**: Ensure absolute security of local file system, environment variables, and production code when the AI is completely out of control.

### [S4] Permission Gate Database Deletion Intercept (v1.0)
- **Why**: LLMs sometimes decide to execute `rm -rf` to "clean the environment" on their own.
- **Benefit**: Intercepts all destructive system commands, converts to human approval workflow.
- **Execute**: `echo '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' | bash .claude/hooks/permission-gate.sh`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S6] Subagent Guard Sub-Agent Runaway Intercept (v2.0)
- **Why**: If the LLM indefinitely spawns other LLMs, it causes bill avalanche.
- **Benefit**: Forces high-consumption Agents to set `max_turns`.
- **Execute**: `echo '{"tool_input":{"subagent_type":"executor"}}' | bash .claude/hooks/subagent-guard.sh task`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S1] Privacy Gate Defense Intercept (v6.0.5)
- **Why**: LLMs easily read `.env` and send real company keys to cloud APIs.
- **Benefit**: Physically cuts off sniffing of password files, intercepts plaintext token execution.
- **Execute**: `echo '{"tool":"read","tool_input":{"file_path":"config/.env"}}' | bash .claude/hooks/privacy-gate.sh`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S2] Context Guard 80% OOM Physical Fuse (v6.0.6)
- **Why**: When context exceeds 80% (e.g., 160K), the model becomes "brain-dead," wildly deleting and modifying working code.
- **Benefit**: Physically locks all write operations, forcing the user to compress the session.
- **Execute**: `echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool":"edit","tool_input":{"file_path":"main.go"}}' | bash .claude/hooks/context-guard.sh`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S3] Completion Gate Strong Evidence Gate (v4.0)
- **Why**: Prevents the AI from lying that "it's done."
- **Benefit**: Must provide test logs containing `VERIFIED` to close the task.
- **Execute**: `rm -f /tmp/.completion-evidence-$(date +%Y%m%d) && echo '{"tool":"task","tool_input":{"status":"completed"}}' | bash .claude/hooks/completion-gate.sh`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M18, M19] CI Commit Gate Verification (v5.x)
- **Why**: Non-compliant code or commit messages pollute the codebase.
- **Benefit**: Auto-run tests before commit (lx-pre-commit), validate format before push (lx-pre-push).
- **Execute**: `ls .claude/skills/lx-pre-commit/scripts/ && ls .claude/skills/lx-pre-push/scripts/`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M10] Plan Gate Document Gate (v6.0.0)
- **Why**: LLM skips research and directly writes code.
- **Benefit**: Before editing plan.md, reminds to confirm Research Gate has passed.
- **Execute**: `mkdir -p rpe/test-feature && echo '{"tool_input":{"file_path":"rpe/test-feature/plan.md","new_content":"# Plan"}}' | bash .claude/hooks/plan-gate.sh edit`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

---

## Zone 3: Lifecycle Integration Test (Advanced State Transition)

> **Test purpose**: Verify that multiple distributed scripts can tightly mesh in a complete lifecycle, driving state machine transitions.
> **Expected benefit**: Ensure a fully automated closed loop from "block" to "self-heal" to "experience solidification."

### [L1, S5] Read-before-Edit Timing and Scope Freeze (v3.0)
- **Why**: LLMs often edit without reading the original file, or modify files outside the task scope.
- **Benefit**: Physically forces the AI to "read before writing" and locks it within the defined file sandbox.
- **Execute**: Clear `.omc/state/read-files.log`, execute `edit-guard.sh` (intercept); execute `read-tracker.sh` (allow); execute `pretool-edit-scope.sh` (scope validation).
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [L3] Build Failure Self-Healing Chain (build-validator ↔ error-dna) (v4.0)
- **Why**: LLM repeatedly makes the same compilation error.
- **Benefit**: Automatically writes errors into the DNA library, avoiding similar errors next time.
- **Execute**: Simulate `bash` failure input to `build-validator.sh`, then pass to `error-dna.sh`, check `error-dna.jsonl`.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [L2] Lesson Solidification and Sublimation Chain (user-correction ↔ write-cite) (v5.0)
- **Why**: If a human verbally corrects the AI but doesn't start a new session, the AI never learns.
- **Benefit**: Structurally deposits personal lessons into `claude-next.md`.
- **Execute**: Simulate user input "wrong" to trigger `pretool-user-correction.sh`, then simulate write to trigger `posttool-write-cite.sh` format validation.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [L7, M4, M6] Session State Save and Knowledge Infusion (v5.1)
- **Why**: Shutdown and restart lose all progress and rules.
- **Benefit**: Auto-snapshot on shutdown (auto-snapshot), auto-read snapshot and inject iron laws on startup (inject-project-knowledge).
- **Execute**: Trigger `auto-snapshot.sh`, check `session-handoff.md`; execute `inject-project-knowledge.sh`, view output.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [S7, M7, M8, M9] Small Mechanism Integration (v4.0-v5.0)
- **Why**: LLMs lack expert-level awareness when using tools.
- **Benefit**: LSP smart reminder (S7), core file source reminder (M7), edit quality reuse detection (M8), Bash dangerous command post-audit (M9).
- **Execute**: Check the logical existence of these 4 post-hooks individually.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M1, M2, L6] Drift Prevention Electroshock Therapy (turn-counter ↔ rule-anchor) (v5.2.4)
- **Why**: Long conversations cause AI to forget rules or accept "vague instructions."
- **Benefit**: Every 10 rounds inject iron laws; after round 15, inject iron laws before writing; detect drift words like "continue," "while you're at it."
- **Execute**: Modify `session-turns.json` to 16 rounds, input drift words, execute `pretool-rule-anchor.sh` and `turn-counter.sh`.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

---

## Zone 4: Monitoring, Diagnostics, and Governance Flywheel (Observability)

> **Test purpose**: Verify that data silently collected by the system in the background is accurate and can guide optimization.
> **Expected benefit**: Make the black-box AI coding process completely transparent and quantifiable.

### [M3] 50% Sweet Spot Proactive Handoff (v6.0.7)
- **Why**: Model intelligence starts declining after 50% usage.
- **Benefit**: When the model state is cleanest, gently remind the user to shift and restart, maintaining peak reasoning speed.
- **Execute**: Modify Token tracking ratio to 55%, run `context_monitor.py`.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M12, M13] Token Savings Quantified Bill (v6.0.3 & v6.1.0)
- **Why**: Must prove to the team that "progressive disclosure" is not a pseudo-concept.
- **Benefit**: Demonstrate business value with specific tokens saved and USD equivalent.
- **Execute**: Verify `inject-project-knowledge.sh` uses summary mode; run `skill_trace_report.py --tokens-only`.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M5, M11] Governance Flywheel Data Closed Loop (v6.1.1)
- **Why**: The team doesn't know what high-frequency blocks the AI is encountering.
- **Benefit**: `skill-flywheel.sh` flushes data; `flywheel-report.sh` generates the last 30 days of high-frequency alerts.
- **Execute**: Write fake flywheel data, run `flywheel-report.sh`, view Markdown alert table.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M17] lx-status Health Dashboard (v6.0.4)
- **Why**: Data scattered everywhere, needs one-click visibility.
- **Benefit**: Terminal three-screen display showing Token bill, self-heal rate, execution efficiency.
- **Execute**: `ls .claude/skills/lx-status/` verify skill exists.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

---

## Zone 5: One-Man Army Concurrent Architecture

> **Test purpose**: Verify this is a distributed system capable of surviving extreme concurrent loads (multi-terminal writing to same disk).
> **Expected benefit**: Give a single developer the throughput of a platoon, with zero code conflicts.

### [L4] Microkernel Physical Lock and Deadlock Self-Heal (oma_lock_manager) (v6.1.5)
- **Why**: Multi-agent concurrent writing leads to fatal mutual overwrites.
- **Benefit**: Queue via OS mutex primitives; auto-crush deadlocks after 60s timeout.
- **Execute**: Terminal A `acquire` holds; Terminal B tries `acquire`; verify `WAITING:` and timeout reclamation.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M21] Polymorphic Orthogonal Decomposition Brain (lx-oma) (v6.1.5)
- **Why**: Manually creating concurrent isolation zones is too slow; need to force AI to decompose requirements by MECE.
- **Benefit**: Auto-generate highly isolated physical directory sandboxes `rpe/feat-X`.
- **Execute**: Check `lx-oma/SKILL.md`, confirm polymorphic path and `mkdir -p` scaffolding logic.
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

### [M16] Bidirectional Desensitization Proxy (lx-varlock) (v6.0.5)
- **Why**: Plaintext keys in concurrent environments are extremely dangerous.
- **Benefit**: LLM uses `{API_KEY}` placeholders; underlying Python substitutes real keys and bidirectionally obfuscates results.
- **Execute**: `python3 .claude/skills/lx-varlock/scripts/varlock.py list`
- **Feedback**: [ ] Pass / [ ] Fail | Notes:

---

**Human Signoff: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_**

*Note: This document has undergone exhaustive audit and deep restructuring. All test points have been categorized and archived by architectural purpose.*
