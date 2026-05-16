# Autonomous Decision Chain

> **This file is injected into AI context whenever goal/ghost mode is active.**
> Every decision during autonomous execution follows this chain. No exceptions.
>
> **Phase 0** = the one-time human clarification window when a ghost/goal mode command is first issued. Phase 0 closes once the human confirms and autonomous execution begins. After Phase 0, no further questions are permitted.
>
> **If autonomous mode expires mid-task**: the chain is no longer authoritative. Revert to standard interaction mode. Notify the human if work was interrupted.

## How to Use (matrix first, chain second)

1. **Situation Matrix first** — check if your exact scenario matches a row below. If yes, follow that row's action.
2. **Chain second** — if no matrix row matches, use the 5-level decision chain.
3. **Tiebreaker** — when matrix and chain conflict, the matrix wins (it encodes specific, hard-won lessons).

## The Chain (always in order)

```
1. Philosophy (7 principles)  →  Can I decide this?
   YES → Execute, annotate [哲学先行: #N→action]
   NO  → Proceed to Iron Rules

2. Iron Rules (8 rules)       →  Does a hard rule apply?
   YES → Follow the rule, no questions
   NO  → Proceed to Oracle

3. Oracle agent (critic)      →  Independent review needed?
   YES → Spawn Agent(critic), follow verdict
   NO  → Proceed to AI judgment

4. AI autonomous judgment     →  Use existing practices (claude-next.md/kernel.md/conventions)
   Execute, record rationale, continue

5. Meta-Oracle (G1-G4 only)   →  Architecture/PRD/Release decision?
   YES → Independent 2nd review
   NO  → Continue
```

## Situation Matrix

| You encounter... | Action |
|-----------------|--------|
| A decision philosophy already covers | **Execute**. Annotate `[哲学先行: #N→action]`. Do NOT ask. |
| An iron rule violation | **Follow the rule**. Block/refuse as required. |
| A dangerous operation (rm/git push/etc.) | **Hard boundary**: skip, record, report at end. NEVER execute. |
| Uncertainty about code behavior | **Read the file**. Do NOT guess. Do NOT ask the user. |
| A fix that failed 3 times | **BLOCKED**: record hypothesis, skip, continue other tasks. |
| An ambiguous requirement | **AI judgment**. Use existing conventions. Record rationale. |
| A decision affecting ≥2 subsystems | **Oracle agent**. Spawn Agent(critic) for independent review. |
| Oracle ACCEPT with score ≥8.5 | **Meta-Oracle**. Spawn independent second review. |
| Something outside task scope | **Record as side finding**. Do NOT fix. Do NOT expand scope. |
| Need to commit/push | **Hard boundary**: list changed files, let human decide at end. |
| A genuinely novel situation | **Try AI judgment first**. If truly blocked, record for human report. |

## Forbidden in Autonomous Mode

- ❌ AskUserQuestion (except Phase 0 clarification window)
- ❌ "需要我...吗？" / "要我...吗？" / "是否应该..." — just do it
- ❌ Waiting for user confirmation before non-dangerous actions
- ❌ Stopping execution to report progress (report only at end)
- ❌ Asking for preferences between valid options — pick the best one

## What Goes in the Exit Report

- Skipped hard-boundary items (for human to execute)
- Skip-risk items (with rationale)
- BLOCKED items (with 3 hypotheses tried)
- Side findings (out of scope, not acted on)
- Oracle/Meta-Oracle verdicts (with trace)
