# Carror OS Full Feature Full Manual Acceptance Dashboard (Manual Acceptance v3.0)

> **You are the last line of defense.**
> This document does NOT contain any "one-click idiot-proof scripts." What's laid out here are 49 physical probes reaching directly into the underlying OS.
> As the acceptance officer, you can pick any command at any time, drop it into the terminal, and watch the LLM get physically suppressed with your own eyes.

---

## How to Work with This Document?

Enter the project root in terminal: `cd @`

Copy the `[Trigger Command]` from the table and execute in terminal.
- **Items marked with [Agentic UI]** will physically hijack the LLM and force-display a **native multi-choice form**.
- **Items marked with [Data Board]** will present the terminal or LLM output as an **aligned Markdown data dashboard**.
- Other items are silent defense cornerstones — observe terminal output directly.

> Please tick and sign off in the companion `manual-acceptance-test-log.md`.

---

## Chapter 1: Foundation Verification — See the Foundation at a Glance (A1-A9)

> Verify that the system governance constitution and interceptor switches are successfully mounted.

| ID | Verification Target | Trigger Command (copy and execute) | Required Evidence |
| :-: | :--- | :--- | :--- |
| **A1** | Constitution dual entry point | `head -1 CLAUDE.md` | Output `@AGENTS.md` |
| **A2** | harness.yaml integrity | `grep -c "hooks_enabled:" .claude/harness.yaml && grep "completion_gate\|permission_gate" .claude/harness.yaml` | Output switch states with Chinese annotation comments |
| **A3** | Soft completion ban | `grep -A 10 "软完成语禁令" AGENTS.md \| head -10` | Lists 6 prohibited phrases including "应该没问题了" |
| **A4** | L1~L4 evidence hierarchy | `grep -A 12 "证据层级" AGENTS.md` | Contains L1~L4 system, with L4 marked ❌ |
| **A5** | Three-round fuse clause | `grep -A 8 "修复上限" AGENTS.md` | Specifies "maximum 3 repair rounds" for the same issue |
| **A6** | Permission transparency | `grep -A 8 "权限申请透明" AGENTS.md` | Mandatory application format: permission needed / current task / reason |
| **A7** | Large task three-state fuse | `grep -A 15 "task_decomposition:" .claude/harness.yaml` | Contains three-state fuse (Closed→Open→Half-Open) configuration |
| **A8** | Knowledge sublimation threshold | `grep -A 5 "^sublimation:" .claude/harness.yaml` | Three thresholds for lesson deposition (20 entries / 10 days / 5 hits) |
| **A9** | Coupling analysis configuration | `grep -A 6 "^coupling:" .claude/harness.yaml` | Same-file modification pre-warning (min_co_change: 3) |

---

> **Anti-OOM checkpoint**: After each chapter, type `/compact` in the dialog to compress context and keep AI at peak performance.

---

## Chapter 2: Physical Gate Battle Royale (S1-S16)

> Core climax chapter. Verify that when the LLM attempts to violate rules, the underlying interceptor can instantly pull its power.

| ID | Defense Vector | Trigger Command (simulate LLM's dangerous call) | Intercept Effect and Visual Presentation |
| :-: | :--- | :--- | :--- |
| **S1** | Constitution infusion | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| head -25` | Terminal prints "Iron Law Quick Reference" forcibly injected into context |
| **S2** | Power-off snapshot continuity | `echo '{"count":5}' > .omc/state/session-turns.json && bash .claude/hooks/auto-snapshot.sh` | Generates `session-handoff.md` snapshot file |
| **S3** | Read source reminder | `printf '{"tool_input":{"file_path":"kernel.md"}}' \| bash .claude/hooks/posttool-read-cite.sh read` | Injects "must cite file:line" warning |
| **S4** | **Database isolation** | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' \| bash .claude/hooks/permission-gate.sh 2>&1` | ** [Agentic UI]** Intercepts `rm -rf`, displays [High-Risk Operation Authorization] multi-choice form |
| **S5** | **DLP leak prevention** | `printf '{"tool":"read","tool_input":{"file_path":"config/.env"}}' \| bash .claude/hooks/privacy-gate.sh 2>&1` | Physically cuts access to sensitive credentials, Exit 2 error |
| **S6** | **Token bareback** | `printf '{"tool":"bash","tool_input":{"command":"curl -H \"Authorization: Bearer sk-ant-abc\""}}' \| bash .claude/hooks/privacy-gate.sh 2>&1` | Intercepts plaintext key execution, forces `lx-varlock` placeholder usage |
| **S7** | **Evidence-free speculation** | `rm -f /tmp/.completion-evidence-$(date +%Y%m%d) && printf '{"tool":"task","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh 2>&1` | ** [Agentic UI]** Intercepts delivery without tests, displays [Send Back / Force Exemption] form |
| **S8** | **OOM lock** | `mkdir -p .omc/state && echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json && printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1` | ** [Agentic UI]** Fakes 90% context (requires context_monitor.py +x permission), blocks all writes, displays compulsory `/compact` form |
| **S9** | **Out-of-scope contamination** | `echo "auth.go" > .omc/state/current-scope.txt && printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1` | ** [Agentic UI]** Intercepts non-task file edits, displays [Add to Scope / Abandon] disposition form |
| **S10** | Blind-write gate | `mkdir -p .omc/state && > .omc/state/read-files.log && printf '{"tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1` | Timing deadlock — must Read before Edit |
| **S11** | Sub-agent runaway | `printf '{"tool_input":{"subagent_type":"executor"}}' \| bash .claude/hooks/subagent-guard.sh task 2>&1` | Intercepts indefinite Agent without `max_turns` set |
| **S12** | Plan gate status | `grep "plan_gate" .claude/harness.yaml` | Confirms `false` (handled by `lx-rpe` internally) |
| **S13** | **Garbage search intercept** | `rm -f .omc/state/lsp-suggested && printf '{"tool_input":{"pattern":"GetUserById","path":"src/"}}' \| bash .claude/hooks/lsp-suggest.sh grep 2>&1` | Blocks `grep` full-repo blind search, recommends LSP precision targeting |
| **S14** | Command post-audit | `printf '{"tool_input":{"command":"git push origin main"},"tool_response":{"exit_code":0}}' \| bash .claude/hooks/posttool-bash-audit.sh bash 2>&1` | Allows dangerous command but leaves audit trail |
| **S15** | Code reuse detection | `printf "src/main.go\nsrc/handler.go\nsrc/service.go\n" > .omc/state/previous-edit-batch.log && rm -f .omc/state/edit-history.log && for f in src/main.go src/handler.go src/service.go; do printf '{"tool_input":{"file_path":"%s"}}' "$f" \| bash .claude/hooks/posttool-edit-quality.sh edit 2>&1; done` | Continuous editing of 3 files triggers 100% overlap warning, forces AI through 4 refactoring self-checks |
| **S16** | Hijack link verification | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh 2>&1 \| grep "question"` | Outputs `[System Instruction]` and `question` fields, proving Agentic UI drive link is intact |

---

> **Anti-OOM checkpoint**: Type `/compact` in the dialog, wait for AI to confirm before continuing.

---

## Chapter 3: State Machine and Long Conversation Drift Prevention (T1-T6)

> Verify the system's ability to counter the LLM's "context decay" and pull the runaway AI back to the main track.

| ID | Observation Mechanism | Trigger Command (simulate conversation round progression) | Expected Behavior |
| :-: | :--- | :--- | :--- |
| **T1** | Iron law replay | `echo '{"count":9}' > .omc/state/session-turns.json && echo "Round 10" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1 \| head -n 12` | ** [Data Board]** At round 10, slams 6 iron law matrix onto the LLM interface on time |
| **T2** | Drift word anchoring | `echo '{"count":15}' > .omc/state/session-turns.json && echo "顺手改了" > .omc/state/.last-user-prompt && printf '{"tool":"edit"}' \| bash .claude/hooks/pretool-rule-anchor.sh 2>&1` | Acutely captures the word "顺手" (while you're at it), immediately escalates scope freeze warning |
| **T3** | Vague command rejection | `echo '{"count":5}' > .omc/state/session-turns.json && echo "继续" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1` | Intercepts targetless "继续" (continue), forces user to provide context |
| **T4** | Sweet spot handoff | `echo '{"usage":110000,"limit":200000}' > .omc/state/token-tracking-index.json && python3 .claude/scripts/context_monitor.py 2>&1` | Gently reminds `/compact` at 55% healthy water level |
| **T5** | Offline hand recovery | `echo '{"count":8}' > .omc/state/session-turns.json && echo "- [ ] Fix pointer" > .omc/state/todo-queue.md && bash .claude/hooks/auto-snapshot.sh >/dev/null && head -6 .omc/state/session-handoff.md` | ** [Data Board]** The printed `handoff.md` snapshot accurately includes the unfinished Todo |
| **T6** | **OOM self-heal** | `echo '{"count":79}' > .omc/state/session-turns.json && echo "Round 80" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1 \| grep "OOM" && printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1 \| grep -q "OOM 物理阻断" && echo "✅ Agentic UI successfully hijacked"` | ** [Agentic UI]** Simulates round 80, underlying system auto-writes 80% usage, successfully displays OOM form on next Edit |

---

> **Anti-OOM checkpoint**: Type `/compact` in the dialog, wait for AI to confirm before continuing.

---

## Chapter 4: Visual Observability Dashboard (O1-O8)

> Verify that all dry logs are rendered into business-valuable data radars.

| ID | Observation Metric | Trigger Command (fetch telemetry data) | Expected Visual Behavior |
| :-: | :--- | :--- | :--- |
| **O1** | Extreme dehydration | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| grep -A 30 "anti-patterns"` | ** [Data Board]** 216 lines of anti-pattern text compressed to 20-line skeleton title injection |
| **O2** | Savings bill | `mkdir -p .omc/state && echo ".claude/skills/lx-oma/SKILL.md" > .omc/state/read-tracker.txt && python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only 2>&1` | ** [Data Board]** Output JSON data card, accurately calculates saved idle references = $$ |
| **O3** | Flywheel persistence | `mkdir -p ~/.claude && echo '{"skill":"lx-oma","action":"phase_start","ts":"'$(date -u +%FT%TZ)'"}' > ~/.claude/flywheel-buffer.jsonl && bash .claude/hooks/skill-flywheel.sh && tail -2 ~/.claude/flywheel.log` | Action event successfully pushed to persistent queue |
| **O4** | **High-frequency alert** | `mkdir -p ~/.claude && for i in {1..6}; do echo "$(date +%Y-%m-%d),permission_gate_triggered,P0,test" >> ~/.claude/flywheel.log; done && bash .claude/hooks/flywheel-report.sh` | ** [Agentic UI]** Renders Markdown frequency statistics table, directly displays disposition strategy choices |
| **O5** | Three-screen dashboard | `ls .claude/skills/lx-status/ && grep "触发" .claude/skills/lx-status/SKILL.md \| head -3` | ** [Data Board]** Proves `/lx-status` dashboard route actually exists |
| **O7** | Authorization menu tier | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh 2>&1 \| grep -E "^\s+[12]\."` | ** [Data Board]** Proves numbered interactive menu provided after block (write marker to continue / cancel) |
| **O8** | Out-of-scope menu tier | `echo "auth.go" > .omc/state/current-scope.txt && printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1 \| grep -E "^\s+[123]\." && rm .omc/state/current-scope.txt` | ** [Data Board]** Proves out-of-scope intercept provides elegant three structured options (force edit / cancel / switch branch) |

---

> **Anti-OOM checkpoint**: Type `/compact` in the dialog, wait for AI to confirm before continuing.

---

## Chapter 5: Multi-Mechanism Integrated Lifecycle (C1-C4)

> Verify that discrete probes mesh like gears to complete complex business closed loops.

| ID | Closed Loop Scenario | Trigger Command (simulate upstream-downstream interaction) | Required Meshing Evidence |
| :-: | :--- | :--- | :--- |
| **C1** | Evolution flywheel | `echo "You're wrong, use Repository" \| bash .claude/hooks/pretool-user-correction.sh UserPromptSubmit 2>&1 && TODAY=$(date +%Y-%m-%d) && printf '{"tool_input":{"file_path":".claude/claude-next.md","content":"### [seed:arch] Repository\n\n@%s hits:1\nTrigger: Aggregation\nCorrect: Repo\nEvidence: Decoupling"}}' "$TODAY" \| bash .claude/hooks/posttool-write-cite.sh write 2>&1 \| grep -E "合规\|升华"` | Capture user correction signal -> LLM writes lesson -> system successfully validates format and triggers sublimation mechanism |
| **C2** | Survey before digging | `rm -f .omc/state/read-files.log && printf '{"tool_input":{"file_path":"src/main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1 \| head -1 && printf '{"tool_input":{"file_path":"src/main.go"},"tool_response":{"stdout":""}}' \| bash .claude/hooks/read-tracker.sh read 2>&1 && printf '{"tool_input":{"file_path":"src/main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1; echo "Second attempt exit code: $?"` | Edit without Read fails and locked -> Record Read operation -> Edit succeeds (exit code 0) |
| **C3** | Error DNA self-heal | `rm -f .omc/state/error-dna.jsonl && echo '{"tool_input":{"command":"go build"},"tool_response":{"stderr":"undefined: SomeFunc","exit_code":1}}' \| bash .claude/hooks/build-validator.sh bash 2>&1 \| grep "修复建议" && echo '{"exitCode": 1}' \| bash .claude/hooks/error-dna.sh bash 2>&1 && cat .omc/state/error-dna.jsonl` | Validator extracts error log injects context -> Error DNA permanently remembers error signature across sessions |
| **C4** | OMA mutex deadlock | `printf '{"tool_input":{"file_path":"src/handler.go"}}' \| bash .claude/hooks/pretool-write-lock.sh write 2>&1; echo "Acquire lock Exit: $?" && printf '{"tool_input":{"file_path":"src/handler.go"}}' \| bash .claude/hooks/posttool-write-lock.sh write 2>&1; echo "Release lock Exit: $?" && ls .omc/locks/ 2>&1` | First terminal acquires lock successfully -> Second terminal suspended -> Lock directory emptied after release, system self-healed |

---

> **Anti-OOM checkpoint**: Type `/compact` in the dialog, wait for AI to confirm before continuing.

---

## Chapter 6: Next-Gen Dual-Core Engine Mounting (N1-N6)

> Check whether the two heavy-weight strategic add-ons representing Carror OS's future throughput limits are in place.

| ID | Strategic Weapon | Physical Mounting Acceptance Criteria |
| :-: | :--- | :--- |
| **N1** | `lx-varlock` Enterprise desensitization proxy | `python3 .claude/skills/lx-varlock/scripts/varlock.py list 2>&1 \| head -3` |
| **N2** | `lx-pre-commit` Pre-commit gate | `ls .claude/skills/lx-pre-commit/scripts/` |
| **N3** | `lx-pre-push` Compliance push checkpoint | `ls .claude/skills/lx-pre-push/scripts/` |
| **N5** | **`lx-oma` One-Man Army concurrent engine** | `ls .claude/skills/lx-oma/ && grep -i "mece\|正交" .claude/skills/lx-oma/SKILL.md \| head -3` |

---

**Acceptance Officer Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_**

**Any item producing output that does not match expectations must have a root cause record in `manual-acceptance-test-log.md`, be fixed, and then retested.**
