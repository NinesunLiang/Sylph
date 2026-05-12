# Triple Gate Cross-Verification System

> **Version**: v1.0 | **Date**: 2026-05-08
> **Positioning**: Semantic layer defense in the AI behavior governance system — the last line of defense against executable/measurable falsehoods

---

## 1. Background: The Blind Spot of Formal Gates

Carror OS already has three layers of formal gates:

| Gate | Check Content | Blind Spot |
|------|--------------|------------|
| completion-gate | Evidence file exists + VERIFIED keyword | Does not check assertion truth |
| edit-guard | File changes within declared scope | Does not check change correctness |
| context-guard | Context percentage within limit | Does not check content quality |

**The R27 incident** exposed a critical problem: all formal layers of completion-gate passed (evidence file exists, has VERIFIED, path is traceable), but the C/E metrics in the report were self-created numbers without industry-standard sources. Formal gates do not check **assertion truth.**

Triple Gate fills this gap: through **cross-model blind execution + falsifiable predictions + dual Oracle notarization**, it exposes semantic-layer falsehoods in cross-verification.

---

## 2. Core Protocol

### 2.1 Three Phases

```
Phase 1: A generates test plan + explicit falsifiable predictions (includes success/failure scenarios)
         → Oracle notarizes the plan (pre-hoc defense: raises the threshold)
Phase 2: B executes blindly (does not know A's predictions, eliminating confirmation bias)
         → B produces a pure factual report (only states: what was executed, what was observed)
Phase 3: A receives B's report, compares against own predictions, self-justifies line by line
         → Oracle final adjudication (Defense 4: independent ruling)
```

### 2.2 Three Roles

| Role | Responsibility | Model Requirement |
|------|---------------|-------------------|
| **A Terminal** | Generates test plan + falsifiable predictions → self-justifies after receiving B's report | Plan author |
| **B Terminal** | Blind execution (does not know expected results) → pure factual report | Must differ from A's model family |
| **Oracle** | Phase 1: notarizes test plan + Phase 2: final adjudication of A's self-justification | Must differ from A's model family |

### 2.3 Key Constraints

| Constraint | Requirement |
|------------|-------------|
| A ≠ B model family | Must differ (prevents blind spot overlap) |
| Oracle ≠ A | Oracle must differ from A's model family |
| Ideal state | A / B / Oracle all from different model families |
| A's predictions not given to B | B receives only cleaned test plan, no expected results |
| A must predict first | Predictions must be completed before receiving B's report, forming falsifiable hypotheses |

---

## 3. Minimum Evidence Checklist (minimal_by_category)

This is the core complement to the Triple Gate system — ensuring each piece of B's evidence is machine-verifiable, not a soft description like "looks normal."

### 3.1 Minimum Machine Fields by Category

| category | Required Fields | Falsification Example |
|----------|----------------|----------------------|
| **build** | path + size + sha256 + exit_code | Artifact does not exist / size=0 / checksum mismatch |
| **test** | exit_code + framework output line (case count/pass/fail/skip) | Case count=0 but claims all green |
| **behavior** | path + type + mode + owner + mtime + side-effect list | Target path does not exist / changes outside declared scope |
| **perf** | real/user/sys time + maxrss (if applicable) | Time deviates from predicted range / insufficient sample count |
| **security** | path + mode + permission before/after diff | Write permission extended to undeclared path / plaintext secret |
| **doc** | path + size + checksum + key field grep result | size=0 / key field missing |

### 3.2 Oracle Rejection Baseline

During Oracle Phase 1 notarization, check line by line:

1. Does each evidence item have ≥3 machine fields? (at least 3 of: path / size / sha256 / exit_code)
2. Fewer than 3 → **rejected**, returned to A for supplementation, not entering B execution
3. Are all machine fields reproducible? (References specific paths/commands/raw output)

---

## 4. Differences from the Old Scheme (A→B→A)

| Dimension | Old A→B→A Scheme | Triple Gate |
|-----------|------------------|-------------|
| Final Adjudication | None — A self-comparison, then ends | Oracle independent final adjudication |
| Expected Results | B knows expectations, confirmation bias exists | B executes blindly, **does not know** expected results |
| Evidence Granularity | Binary "pass/fail" conclusion | Machine fields (exit_code+path+size+sha256) |
| Model Isolation | Suggested different models | A≠B must differ, Oracle≠A must differ |
| Threshold | B executes directly | Oracle Phase 1 notarization raises threshold |

---

## 5. Defense Coverage Boundaries

```
Defense Coverage:
  - Falsified build/compile results (fake exit 0)
  - Empty test runs (fake all green, actual case count=0)
  - Artifacts claimed generated but do not exist (size=0)
  - Security scan claimed run but not actually executed
  - Self-created metrics mixed into industry-standard tables (R27 type)
  - Fabricated URLs/sources

Not Covered:
  - Code logic bugs (compiles but logic is wrong)
  - Architectural design flaws (assertions with no executable commands)
  - Requirement misunderstanding (did the right thing but solved the wrong problem)
  - Performance/security review requiring expert judgment
```

---

## 6. Workflow

```
User initiates evaluation task
    │
    ▼
A Terminal: generates test plan + predictions (with category + falsification_threshold)
    │
    ▼
Oracle Phase 1: notarizes test plan
    ├─ min_evidence_check: each evidence ≥3 machine fields?
    ├─ Pass → strip predictions, hand to B
    └─ Reject → return to A for supplementation
    │
    ▼
B Terminal: blind execution (does not know expected results)
    ├─ machine_evidence: exit_code + path + size + sha256 + raw_preview
    └─ observed: objective description
    │
    ▼
A Terminal: self-justification (compares predictions vs B's observations)
    │
    ▼
Oracle Phase 2: final adjudication
    ├─ PASS → deliver
    ├─ FAIL → return to A for fix
    └─ INCONCLUSIVE → supplemental evidence required
```

---

## 7. Handoff Format (AGENTS.md Section 6)

See `AGENTS.md` Section 6 for details. Key interface fields:

```
evidence_requirements:
  minimal_by_category:  # Minimum evidence requirements by category
    build: [...]
    test: [...]
    behavior: [...]
    ...

B Report:
  machine_evidence:     # Structured evidence that B prioritizes
    exit_code: 0|1|null
    path: "target path|null"
    size: "bytes|null"
    sha256: "checksum|null"
    raw_preview: "key lines from raw output"

Oracle Phase 1:
  min_evidence_check:
    passed: true|false
    detail: "list of evidence items with fewer than 3 machine fields"
```

---

## 8. Trigger Scenarios

Triple Gate is a manual trigger protocol (not an automatic hook). Trigger conditions:

- Key task types listed in AGENTS.md Section 6 (proposals/verification/scoring/benchmark/critical decisions)
- When completion-gate detects `evidence` contains "report/proposal/verification/pass-rate/evaluation/standard" and criticality is high, it prints a Triple Gate invocation reminder
- User actively requests "run Triple Gate"

> **Cross-verification with the same model is limited (blind spot overlap). Different models are required to truly discover assertion fabrication.**
> It is recommended to switch to a different model family each time a new terminal (B / Oracle) is opened.

---

## 9. Related Files

| File | Content |
|------|---------|
| `AGENTS.md` | Full protocol definition + handoff template + degradation fallback |
| `.claude/nodes/a_terminal.md` | A Terminal mode (prediction generation + self-justification) |
| `.claude/nodes/b_terminal.md` | B Terminal mode (blind execution + machine_evidence) |
| `.claude/nodes/oracle_terminal.md` | Oracle mode (two-phase notarization + min_evidence_check) |
