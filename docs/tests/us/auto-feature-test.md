# Carror OS Automated Feature Acceptance (auto-feature-test)

> **Version**: v6.1.8 | **Audience**: First deployment acceptance / regression testing / new member onboarding
>
> **Hello! Welcome to the Carror OS automated acceptance workflow.**
>
> This is NOT a traditional test document that requires you to manually type commands.
> All you need to do is **give natural language instructions to the AI** — the underlying system automatically triggers physical probes, displays interactive forms, and presents all results as visual charts.
>
> **Three steps to complete acceptance:**
> 1. Ensure you have installed Carror OS v6.1.8 (`bash install.sh`)
> 2. Open an AI conversation and speak each zone's trigger phrase (see sections below)
> 3. Record actual results in the companion `auto-feature-test-log.md`, then sign off
>
> **Companion file**: `auto-feature-test-log.md` (acceptance battle report template, fill as you test)

---

> **Presentation Constitution**
> 1. **Agentic UI First, Terminal Fallback**: During runtime, all physical gates involving decisions or blocks must hijack the AI to display an interactive `question` form for human selection, replacing manual `echo` state file writes.
> 2. **Data Visualization Mounted**: All system logs, error interception records, and token savings must be presented as **aligned Markdown tables, ASCII charts, or high-density indicator cards**. Reject plain-text log dumps.

---

## How to Execute This Dashboard Acceptance

You no longer need to copy and paste obscure Bash commands one by one. All test items in this dashboard are adapted for **AI auto-run mode**. Simply tell the LLM:
> **"Please execute the tests in [Zone 1] and display the interception results to me using Agentic UI (choice menu)."**

**(The accompanying `[Terminal fallback trigger]` is only used when the AI environment crashes or you want to directly verify underlying script connectivity through the terminal.)**

---

## Zone 1: Agentic UI Physical Gate Experience (The Interactive Hard Gates)

> **Test purpose**: Verify that when the LLM attempts to overstep, the underlying OS can physically suspend it in milliseconds and, **via System Prompt hijack, display a native multi-choice form** to obtain human authorization.

| ID | Defense Threat Vector | Terminal Fallback Trigger (for pure Bash verification) | Expected Native Interaction Form (Agentic UI) | Acceptance |
| :-: | :--- | :--- | :--- | :---: |
| **S4** | Destructive command block (prevent AI from deleting production) | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' \| bash .claude/hooks/permission-gate.sh 2>&1` | High-risk operation authorization form, Options: Clean temp environment / Delete deprecated module / Backup production data / Custom reason | ⬜ |
| **S7** | Evidence-free speculation block (prevent AI from fabricating test results) | `rm -f /tmp/.completion-evidence-$(date +%Y%m%d)`<br>`printf '{"tool":"task","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh 2>&1` | Strong evidence gate intercept form, Options: Send back to write tests / Force exemption | ⬜ |
| **S8** | OOM physical fuse (prevent late-session amnesia hallucinations) | `echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json`<br>`printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1` | OOM physical block (90%) form, Options: Compress memory now (/compact) / Abandon changes and start new branch | ⬜ |
| **S9** | Incidental contamination intercept (prevent out-of-scope code edits) | `echo "auth.go" > .omc/state/current-scope.txt`<br>`printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1` | Scope violation intercept form, Options: Add to allowed scope / Abandon modification and continue / New step | ⬜ |

---

## Zone 2: Visual Observability and Governance Flywheel (Visual Observability)

> **Test purpose**: Reject dry stdout string logs. Verify the system can render collected AI work habits, token burn rates, and error stacks into clear Markdown charts.

| ID | Core Observation Mechanism | Terminal Fallback Trigger | Expected High-Density Chart Format (Markdown/ASCII) | Acceptance |
| :-: | :--- | :--- | :--- | :---: |
| **O1** | Progressive disclosure (Summary) | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| grep -A 30 "anti-patterns"` | Token compression indicator: 216 lines of anti-pattern text physically compressed to 20 title lines | ⬜ |
| **O2** | Token savings quantified bill | `python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only 2>&1` | Pivot table: Tokens saved and equivalent USD from on-demand loading | ⬜ |
| **O4** | High-frequency intercept flywheel alert | `(Repeat 6x) echo "date,permission_gate_triggered,P0,test" >> ~/.claude/flywheel.log`<br>`bash .claude/hooks/flywheel-report.sh` | Markdown alert dashboard: Aligned table with event/frequency/level + Agentic disposition button | ⬜ |
| **T1** | Round freshness and iron law anchoring | `echo '{"count":9}' > .omc/state/session-turns.json && echo "Round 10" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1` | Rule replay matrix: Recite 6 iron laws + Todo queue status | ⬜ |

---

## Zone 3: Zero-Trust Security and Foundation

> **Test purpose**: Test the silent cornerstones that require no UI interaction but firmly guard enterprise code assets at the foundation level.

| ID | Defense Name | Fallback Execution Command | Required Blockage Evidence (Exit 2) | Acceptance |
| :-: | :--- | :--- | :--- | :---: |
| **S5/S6** | Enterprise DLP leak prevention | `echo '{"tool":"read","tool_input":{"file_path":"config/.env"}}' \| bash .claude/hooks/privacy-gate.sh` | Physical cutoff: Contains `Direct read of sensitive files containing configuration, credentials, or keys prohibited` | ⬜ |
| **S10** | No blind code editing | `printf '{"tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1` | Timing deadlock: Contains `[Read-before-Edit] You are editing a source file but have not Read it first` | ⬜ |
| **S13** | Garbage search intercept | `printf '{"tool_input":{"pattern":"GetUserById","path":"src/"}}' \| bash .claude/hooks/lsp-suggest.sh grep 2>&1` | Engine hijack: grep intercepted, LSP precision targeting recommended | ⬜ |
| **A1-A9** | Configuration files and gate switches | `grep "hooks_enabled:" .claude/harness.yaml` | Matrix all green: 15 gates YAML fully mounted + `CLAUDE.md` has `@AGENTS.md` entry point | ⬜ |

---

## Zone 4: Next-Gen Multi-Agent Dual-Core Engine

> **Test purpose**: Verify that OMA multi-terminal concurrent orchestration and automatic decomposition capabilities are in place.

| ID | Engine Emblem | Core Strategic Value | Physical Acceptance Criteria | Acceptance |
| :-: | :--- | :--- | :--- | :---: |
| **N5** | `lx-oma` (One-Man Army concurrent engine) | Multi-terminal concurrent throughput limit: MECE orthogonal decomposition + OMA mutex lock, single developer launching 5 parallel models | Directory `.claude/skills/lx-oma` exists, contains MECE orthogonal decomposition principles | ⬜ |

---

> **Final Ruling:**
> As the quality gatekeeper, if you personally use any of the above `Terminal Fallback` commands to trigger a defense line and it does NOT display the expected Agentic form or high-density Markdown chart, but instead a messy raw character stream, immediately rule this version as **FAILED** for violating the Presentation Constitution.
>
> **(Detailed execution records for this verification are stored in the historical `features-executor-log.md` pool.)**
