# AH-Guard: Anti-Hallucination Defense Layer

> **Purpose**: Document the three-layer anti-hallucination defense and its coverage boundaries
> **Version**: v1.0.0
> **Status**: Active
> **Last Updated**: 2026-05-09

---

## Design Philosophy

AH-Guard does not have a single dedicated "anti-hallucination guard" hook. Instead, three independent mechanisms at different enforcement points form a defense-in-depth layer. This is intentional: hallucination detection at the semantic level is technically infeasible for hook scripts (which operate at tool-call boundaries on structured JSON, not on chat completion output semantics). Physical interception cannot evaluate whether a natural language assertion is true.

The strategy is **layered risk reduction at enforcement boundaries** — not complete hallucination prevention.

---

## Layer 1: Completion Gate — Output Boundary

**Hook**: `.claude/hooks/completion-gate.sh`
**Trigger**: `PreToolUse:TaskUpdate` when status = `completed`
**Enforcement**: `exit 2` (hard block, AI cannot bypass)

### What it does
- Blocks `TaskUpdate("completed")` unless a structured evidence file exists with:
  - `VERIFIED` keyword ([`:74-78`](../hooks/completion-gate.sh#L74-L78))
  - Structured format markers: `[已验证: file:line]`, `[已测试: 命令+输出]`, `exit 0`, `PASS`, etc. ([`:98-101`](../hooks/completion-gate.sh#L98-L101))
  - Minimum 20 characters of evidence content
- Atomic consume: evidence file is consumed on first pass (multi-process race defense via mv + read-back)

### Coverage boundary
| Covers | Does NOT cover |
|--------|----------------|
| False "completed" claims without evidence | Completing tasks without VERIFIED keyword |
| Evidence-less task closure | Semantic truth of evidence content |
| Minimal evidence length enforcement | Prohibits hallucinated evidence that passes form checks |

### Key limitation
**Form verification ≠ truth verification**. As documented in [anti-patterns.md H1](../anti-patterns.md#h1语义编造--形式合规掩护语义作弊), "形式门禁通过 ≠ 断言真实." An assertion formatted as `[已验证: some_file:42]` passes the structural gate even if the claim is false. The gate checks format, not fidelity.

---

## Layer 2: Context Guard — Execution Boundary

**Hook**: `.claude/hooks/context-guard.sh`
**Trigger**: `PreToolUse:Edit|Write` (per R29 fix — Read/Grep/Bash are open for diagnostics)
**Enforcement**: `exit 2` at ≥80% context token threshold

### What it does
- Monitors context token percentage via OMC state + config
- At ≥80%: physical blocks all Edit/Write operations ([`:54-61`](../hooks/context-guard.sh#L54-L61))
- At ≥50%: emits sweet-spot handoff warning (stderr, non-blocking)
- Escape hatch: `context-force-override` marker file bypasses block (created via Bash, which remains unblocked)

### Coverage boundary
| Covers | Does NOT cover |
|--------|----------------|
| Prevents context-degraded writes (hallucination risk peaks at >80%) | Does not evaluate semantic correctness at any context level |
| Latent writes at high context | Does not block Read/Grep/Bash — these remain available for diagnostics |
| Self-inflicted DoS (locking all tools) | Requires manual escape hatch for override |

### Key limitation
The Edit|Write-only scope (R29) is a compromise: it prevents destructive operations at high context while preserving diagnostic channels. A determined hallucination during Bash execution at 70% context is not blocked by this layer.

---

## Layer 3: A-B-A Cross-Verification — Semantic Boundary

**Trigger**: `completion-gate.sh` keyword detection on report/plan content ([`:96-103`](../hooks/completion-gate.sh#L96-L103))
**Mechanism**: Generates `cross-verify-handoff.md` for transfer to B terminal
**Enforcement**: Procedure — different model recommended, not enforced

### What it does
- Completion gate detects high-risk content keywords (验收/方案/报告/评估/analysis etc.)
- Generates handoff document with:
  - A's task description and recent file changes
  - B's adversarial review prompt template
  - Comparison protocol: A receives B's report, compares predictions, self-verifies
- Oracle terminal provides final judgment on discrepancies

### Coverage boundary
| Covers | Does NOT cover |
|--------|----------------|
| Semantic truth checking via cross-model blind execution | Only triggers on report/plan/analysis content keywords |
| Breaking confirmation bias through independent context | Same-model cross-verification has blind spot overlap |
| Structured handoff format for B terminal | Requires user to manually open B terminal with different model |

### Key limitation
- **Not automatic for all tasks** — only triggers for tasks containing specific content keywords
- **Cross-model is recommended but not enforced** — user must manually switch models
- **Gate does not block completion if B validation is skipped** — it's a procedural prompt, not a hard gate

---

## Defense Coverage Summary

```
Layer 1 (Form):    completion-gate ───── Exit 2 ──── Form check ✓
                    blocks unverified completions     Truth check ✗

Layer 2 (Context): context-guard ────── Exit 2 ──── Writes blocked at >80%
                    prevents late-session decay       Semantics unevaluated

Layer 3 (Semantic): A-B-A cross-verify ── Prompt ── Truth check ✓
                    cross-model blind review          Requires manual execution
```

| Attack vector | Layer 1 | Layer 2 | Layer 3 | Effective? |
|---------------|---------|---------|---------|------------|
| False "completed" with no evidence | ✅ Blocks | — | — | ✅ Strong |
| Hallucinated code at low context | — | — | — | ❌ Not covered |
| Hallucinated report at low context | — | — | ✅ If keywords trigger | Partial |
| Evidence formatted as correct but false | ✅ Form passes | — | ✅ If cross-review triggered | Partial |
| Context-degraded destructive writes | — | ✅ Blocks | — | ✅ Strong |
| Hallucinated Bash commands | — | Partial (>80%) | — | ❌ Weak |

---

## Known Gaps & Accepted Risks

1. **No runtime semantic verification**: AH-Guard cannot detect hallucinations during execution (coding, Bash commands). Only catches at completion boundary (Layer 1) or report/plan content (Layer 3).

2. **Evidence form != evidence truth**: A comprehensively false claim formatted as proper evidence passes Layer 1. Mitigated only by Layer 3 cross-verification, which is manual and keyword-triggered.

3. **Context guard is write-only**: At 70-80% context, hallucinated code can be written via Bash sessions that pass the Edit|Write matcher. R29 compromise prioritizes diagnostic access over absolute protection.

4. **A-B-A is procedure, not guard**: Layer 3 cannot enforce cross-model review. It generates a handoff document and prompts — but does not `exit 2` if validation is skipped.

---

## Runtime Confidence Protocol (v2 — E2 Gap Mitigation)

> **Purpose**: Provide an inline guard that skills apply during execution (not just at completion boundary)
> **Reference**: Confidence field in `schemas/atomic/verdict.yaml` v2, output schemas in `schemas/output/`

### 1. Confidence Assertion Rule

Every technical assertion in a skill's output must carry one of three confidence levels:

| Level | Label | When to use | Example |
|-------|-------|------------|---------|
| 🟢 High | `[high]` | Directly verified via `file:line` read or command output | `Query is not vulnerable to SQL injection [high: verified query uses parameterized input at user_repo.go:42]` |
| 🟡 Medium | `[medium]` | Reasonable inference from indirect evidence | `This function is likely called on startup [medium: referenced in main.go:15 init() block but not traced at runtime]` |
| 🔴 Low | `[low]` | Speculative / unchecked / inferred from naming only | `This flag likely controls caching [low: deduced from flag name --enable-cache, actual usage not verified]` |

**Enforcement**: Skills must differentiate these in output. A `[low]` assertion is **not a violation** — it's honest. The violation is omitting the level and letting the user assume `[high]`.

### 2. Output Schema Integration

The `confidence` field has been added to:

| Schema | Location | Values |
|--------|----------|--------|
| `schemas/atomic/verdict.yaml` | `.confidence` | high, medium, low |
| `schemas/output/review_report.yaml` | `findings[].confidence` | confirmed, likely, needs_review |
| `schemas/output/gov_report.yaml` | `changes[].confidence` | confirmed, likely, needs_review |
| `schemas/output/task_spec.yaml` | `acceptance_criteria[].confidence` | confirmed, likely, needs_review |

### 3. Pre-Output Validation Step

Skills SHOULD include a pre-output validation step before finalizing results:

```
1. Scan all assertions for confidence markers
2. For each assertion:
   a. Is there a file:line? → high
   b. Is there indirect evidence? → medium
   c. Neither → low
3. If >50% assertions are [low]:
   Flag: "报告中有 N% 的断言为推测(低置信度), 建议交叉验证后输出"
4. Append confidence breakdown to report footer
```

This step can be referenced by any skill via `@../../references/hallucination-defense.md` §Runtime Confidence Protocol.

### 4. Triple-Gate Integration (L4 Tasks)

For L4 tasks (per AGENTS.md 三重门), the confidence protocol is enforced as part of the A→B→A pipeline:
- A's predictions MUST include confidence levels for each assertion
- Oracle checks: "Are A's confidence levels appropriate given B's results?"
- Systemic overconfidence (A marked [high] but B found errors) → Oracle flags as confidence calibration issue

---

## Future Considerations

If Claude Code (or the underlying platform) exposes semantic evaluation capabilities at the tool-call boundary, AH-Guard should be upgraded:
- Add a `truth-check` layer that evaluates evidence assertions against known source truth
- Add automatic confidence scoring for AI outputs below configurable thresholds
- Gate cross-model review as a hard requirement for L3 tasks (currently soft)

Until then, the defense strategy remains: **intercept at enforcement boundaries, accept that semantic hallucination detection requires human or cross-model review.**
