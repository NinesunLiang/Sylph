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
| Oracle ACCEPT with score ≥8.5, OR any CRITICAL finding, OR architecture/PRD/release gate (G1-G4) | **Meta-Oracle mandatory**. Use runtime trace method (execution path tracing, condition branch verification), not static review alone. DG-56: static-only Meta-Oracle missed critical logic bugs. |
| Something outside task scope | **Record as side finding**. Do NOT fix. Do NOT expand scope. |
| Need to commit/push | **Hard boundary**: list changed files, let human decide at end. |
| Non-dangerous actionable items within scope | **Execute immediately**. DO NOT ask "要不要"/"需要我"/"是否应该". Annotate rationale and go. Philosophy #5 (reduce mental burden): human only sees results in exit report. DG-57. |
| Non-trivial task completed / bug fix applied | **Spawn Oracle critic for independent re-review**. AI cannot self-certify its own work. Philosophy #4 (not verified = not done) + Philosophy #6 (0 trust). DG-18, DG-23, DG-33. |
| Sub-agent / child agent returned data to use | **Verify against source files before writing to output**. Sub-agent data defaults to [推断,待确认]. Never treat as verified fact without reading origin files. DG-44 (primary: cross-agent info-chain untrustworthy). |
| Oracle findings received (CRITICAL/MAJOR/REVISE) | **Evaluate against design intent first**. Not all Oracle findings are actionable bugs — some are correct design decisions the Oracle misjudged. Separate real bugs from design disagreements before acting. DG-21. |
| Security mechanism or safety-critical change | **Oracle + Meta-Oracle DUAL sign-off required**. No single-reviewer shortcuts. Philosophy #6 (0 trust): two independent reviews are the minimum for safety. DG-32. |
| Ghost vs Goal mode selection ambiguous | **AI self-evaluates direction type** (do NOT ask human): deterministic task list with action verbs (修复/优化/实现) → goal mode. Open exploration (分析/调研/阅读) → ghost mode. Never use ghost mode for fixed fix lists. DG-55, GL-01. |
| Writing persuasive / marketing / non-technical content | **Apply stricter verification**. All numeric claims must be traceable to source files. This output mode historically produces unverified assertions. Use `[内部自检]` markers when no external source exists. DG-43 (primary: marketing/semantic-gate blind spot). |
| Autonomous mode nearing completion / phase end | **Generate exit report section immediately**. Mandatory fields: (1) hard-boundary items (2) skip-risk items w/ rationale (3) BLOCKED items (4) side findings (5) Oracle/Meta-Oracle verdicts. Do NOT defer report writing. DG-58. |
| A genuinely novel situation | **Try AI judgment first**. If truly blocked, record for human report. |

## Forbidden in Autonomous Mode

> **Enforcement note**: These rules rely on AI compliance with injected context. They are verified by
> post-session audit (exit report review), not runtime physical enforcement. `posttool-claim-audit` + `meta-oracle-trigger` enforce philosophy-first rules at runtime (replaced deprecated `pretool-ask-guard`, removed 2026-05-17)
> violations to stderr without blocking during autonomous mode — this is a safety tradeoff to preserve
> the human escape hatch if the AI enters a broken state.

- ❌ AskUserQuestion (except Phase 0 clarification window)
- ❌ "需要我...吗？" / "要我...吗？" / "是否应该..." — just do it
- ❌ Waiting for user confirmation before non-dangerous actions
- ❌ Stopping execution to report progress (report only at end)
- ❌ Asking for preferences between valid options — pick the best one
- ❌ Manually creating `autonomous.active` or mode signal files — always use `lx-goal.sh on` or `lx-ghost.sh on`. Manual touch bypasses half the activation chain. DG-46.

## What Goes in the Exit Report

## ⚠️ Needs Human Decision — Aggregated Summary (REQUIRED in every exit report)

> **Every exit report MUST include this aggregated section** as the first "needs attention" block.
> It consolidates ALL items requiring human review across categories so the human doesn't hunt through sections.

Format:
```
## ⚠️ 需人为决策汇总

| # | 类型 | 描述 | AI 推荐 | 依据 |
|---|------|------|---------|------|
| 1 | 硬边界 | ... | 建议人类执行: ... | 触碰哪条硬边界 |
| 2 | 阻断 | ... | 已尝试方案: A/B/C | 为何无法继续 |
| 3 | 推迟决策 | ... | 推荐方案 + 理由 | 决策链依据 |
```

### Categories to aggregate:
- **Hard boundary items** — operations AI cannot execute (rm, git push, commit, credentials)
- **BLOCKED items** — core path blocked, 3 hypotheses tried and failed
- **Postponed decisions** — decisions deferred to exit report (with AI recommendation + rationale)
- **Uncertain judgments** — decisions AI made with low confidence, flagged for human review

### Per-item format:
- **What was blocked/postponed** — specific operation or decision
- **Why** — which hard boundary, rule, or uncertainty triggered the postponement
- **AI recommendation** — what the AI would do if authorized
- **Decision basis** — philosophy/iron-rule/Oracle verdict that informed the AI's recommendation

---

## Standard Exit Report Sections

- Skipped hard-boundary items (for human to execute)
- Skip-risk items (with rationale)
- BLOCKED items (with 3 hypotheses tried)
- Side findings (out of scope, not acted on)
- Oracle/Meta-Oracle verdicts (with trace)
