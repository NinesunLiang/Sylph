# Carror OS Four-Dimension Scoring Framework

> **Version**: v6.1.9 | **Updated**: 2026-05-13
> **Status**: Official scoring framework — all evaluation reports should use this as baseline

---

## Overview

Carror OS evaluates itself across four dimensions comprising 28 sub-dimensions. Total weighted score is 345 points, normalized to a 10-point or 8-point scale.

| Dimension | Name | Sub-dimensions | Total Weight | Description |
|-----------|------|---------------|-------------|-------------|
| **C** | Capability | 9 | 105 | Instruction clarity, context completeness, process structure, etc. |
| **E** | Error Prevention | 8 | 110 | Goal drift, hallucination, false completion, etc. |
| **G** | Governance | 6 | 65 | Anti-decay, automation, security gates, etc. |
| **U** | User Experience | 5 | 65 | Mental load, sense of control, interaction quality, etc. |

**Composite = weighted average of C + E + G + U**, total weight 345.

---

## C Dimension: Capability

Measures Carror OS's capability completeness as an AI governance framework.

| ID | Name | Weight | Check Method | Maturity |
|----|------|--------|-------------|----------|
| C1 | Instruction Clarity | 15 | Hook script `# Role:` comment coverage ratio | 0.85 |
| C2 | Context Completeness | 15 | index.md iron laws / references / knowledge coverage | 0.85 |
| C3 | Process Structure | 15 | completion-gate L3 gate + Oracle review + smoke regression | 1.00 |
| C4 | Output Standardization | 10 | posttool-format-gate registration and matcher scope | 0.85 |
| C5 | Tool Lifecycle | 10 | settings.json event type coverage (6 event types) | 0.90 |
| C6 | Knowledge Density | 10 | claude-next.md line count + R-lessons + memory files | 0.85 |
| C7 | Orchestration | 10 | OMA skill directory existence | 0.85 |
| C8 | Maintainability | 10 | audit-hooks / smoke-test / hook-production-verify presence | 0.90 |
| C9 | Error Recovery | 10 | error-dna / auto-fix / dna-jsonl infrastructure | 0.85 |

### Sub-dimension Details

**C1 Instruction Clarity**: Checks what proportion of `.claude/hooks/*.sh` scripts have a `# Role:` comment in their first 5 lines. Target: 100%.

**C2 Context Completeness**: Checks `index.md` for iron laws quick-reference, hooks reference pointers, anti-patterns/kernel references.

**C3 Process Structure**: Checks completion-gate.sh implements:
- L3 complexity keyword detection (architecture decisions, multi-file changes)
- Oracle review record block check
- harness-smoke-test E2E-6 test case

**C4 Output Standardization**: Checks posttool-format-gate.sh is registered in settings.json with matcher `.*` (full coverage).

**C5 Tool Lifecycle**: Checks registered event types: PreToolUse / PostToolUse / PostToolUseFailure / Stop / UserPromptSubmit / SessionStart.

**C6 Knowledge Density**: Composite — 50% line count + 30% R-lessons + 20% memory file existence.

**C7 Orchestration**: Checks OMA skill directories: lx-oma-hier / lx-oma-split / lx-oma-gov / lx-oma-orch.

**C8 Maintainability**: Checks key maintenance scripts: audit-hooks.sh / harness-smoke-test.sh / hook-production-verify.sh.

**C9 Error Recovery**: Checks error-dna infrastructure: hook script / auto-fix script / JSONL data file.

---

## E Dimension: Error Prevention

Measures Carror OS's defense against common AI error patterns.

| ID | Name | Weight | Check Method | Maturity |
|----|------|--------|-------------|----------|
| E1 | Goal Drift | 20 | pretool-edit-scope + claude-next lessons + turn-counter detection | 0.85 |
| E2 | Hallucination | 20 | posttool-claim-audit presence + settings registration + claude-next lessons | 0.90 |
| E3 | False Completion | 15 | completion-gate evidence check + anti-patterns A2 entry | 1.00 |
| E4 | Inertial Execution | 12 | fuzzy-block presence + turn-counter fuzzy words + ghost exemption | 1.00 |
| E5 | Symptom Confusion | 10 | error-dna NOISE_PATTERNS filter + JSONL data volume | 0.85 |
| E6 | Self-Contradiction | 13 | claude-next R42 + R43 + anti-pattern-detect hook | 0.85 |
| E7 | Overconfidence | 10 | completion-gate soft words + anti-patterns A2/F1 + quality score | 1.00 |
| E8 | Context Amnesia | 10 | compact-detect knowledge injection + inject-project-knowledge + context-guard | 0.90 |

### Sub-dimension Details

**E1 Goal Drift**: Checks edit-scope.sh's scope freeze mechanism, drift lessons in claude-next.md, drift detection in turn-counter.sh.

**E2 Hallucination**: Checks posttool-claim-audit.sh existence and registration, relevant lessons in claude-next.md. Maturity 0.90 (claim-audit exit 2 hard-block).

**E3 False Completion**: Checks completion-gate.sh's evidence gating logic, anti-patterns.md A2 entry. Maturity 1.00 (hard-block).

**E4 Inertial Execution**: Checks fuzzy-block.sh existence, turn-counter.sh fuzzy verb detection, ghost mode fuzzy command exemption. Maturity 1.00.

**E5 Symptom Confusion**: Checks error-dna.sh's NOISE_PATTERNS filter rules, JSONL data volume > 10 entries.

**E6 Self-Contradiction**: Checks claude-next.md records R42 (hook rules misapplied to skills) and R43 (CAPTCHA scripted approval).

**E7 Overconfidence**: Checks completion-gate.sh soft completion word matching, anti-patterns.md A2/F1 definitions, quality score threshold. Maturity 1.00 (A2/F1/H1 all exit 2 hard-block).

**E8 Context Amnesia**: Checks compact-detect.sh's knowledge reinjection, inject-project-knowledge.sh existence, context-guard.sh existence.

---

## G Dimension: Governance

Measures Carror OS's long-term governance capabilities and infrastructure robustness.

| ID | Name | Weight | Check Method | Maturity |
|----|------|--------|-------------|----------|
| G1 | Anti-Decay Defense | 10 | audit-hooks + hook-production-verify + smoke test + auto-snapshot | 0.90 |
| G2 | AI Automation | 10 | compact-detect + auto-snapshot + error-dna registration + auto-fix | 0.85 |
| G3 | Learning Notes | 10 | claude-next.md > 100 lines + handoff + snapshot + R lessons > 10 | 0.85 |
| G4 | Feature Flags | 10 | harness.yaml hooks_enabled + audit-hooks + hc_enabled full coverage | 0.90 |
| G5 | Built-in Security | 15 | permission-gate + privacy-gate + sensitive-edit + context-guard registered | 1.00 |
| G6 | Evaluation Framework | 10 | score-self-check exists + baseline + report + weights documented | 0.85 |

### Sub-dimension Details

**G1 Anti-Decay Defense**: Checks four anti-decay mechanisms: audit-hooks.sh (three-way consistency audit), hook-production-verify.sh (production verification), harness-smoke-test.sh (regression testing), auto-snapshot.sh (session snapshots).

**G2 AI Automation**: Checks four automation mechanisms: compact-detect.sh (compression detection), auto-snapshot.sh (snapshot capture), error-dna registration in settings.json, error-dna-auto-fix.sh (auto repair).

**G3 Learning Notes**: Checks knowledge accumulation: claude-next.md > 100 lines, session-handoff.md exists, session-snapshot.json exists, R-lesson count > 10.

**G4 Feature Flags**: Checks feature toggle infrastructure: harness.yaml defines hooks_enabled, audit-hooks.sh exists, all hook scripts implement hc_enabled gating.

**G5 Built-in Security**: Checks four security mechanisms registered in settings.json: permission-gate (dangerous command interception), privacy-gate (privacy protection), pretool-sensitive-edit (governance file CAPTCHA), context-guard (context threshold blocking). Maturity 1.00 — all are hard-block mechanisms.

**G6 Evaluation Framework**: Checks scoring infrastructure: score-self-check.sh exists, score-baseline.json baseline saved, score-report.json report exists, weights defined in script.

---

## U Dimension: User Experience

Measures interaction quality and mental load when users interact with Carror OS.

| ID | Name | Weight | Check Method | Maturity |
|----|------|--------|-------------|----------|
| U1 | Mental Load Reduction | 15 | CAPTCHA clear prompts + ghost exemption + format direction + score direction | 0.90 |
| U2 | User Control | 15 | permission-gate + sensitive-edit CAPTCHA + git gate + Oracle verdict | 0.90 |
| U3 | Behavioral Predictability | 10 | index.md iron laws + scope freeze + fix cap + confidence format | 0.85 |
| U4 | Interaction Quality | 10 | format-gate direction + matcher full coverage + anti-pattern detection | 0.85 |
| U5 | Permission Boundary Clarity | 15 | permission-gate scope + sensitive-edit file list + git gate + privacy targets | 0.90 |

### Sub-dimension Details

**U1 Mental Load Reduction**: Checks mechanisms that reduce cognitive burden:
- CAPTCHA prompts in pretool-sensitive-edit.sh include directional guidance ("paste in input box and press Enter")
- turn-counter.sh ghost mode fuzzy command exemption
- posttool-format-gate.sh provides format direction hints
- completion-gate.sh outputs quality breakdown and improvement direction when evidence fails (R38)

**U2 User Control**: Checks user control over system behavior:
- permission-gate registered in settings.json
- pretool-sensitive-edit.sh uses verification code approval
- index.md includes Git gate rules
- lx-oma-orch SKILL.md includes Oracle gate verdict mechanism

**U3 Behavioral Predictability**: Checks system behavior predictability:
- index.md includes iron laws quick-reference table
- Contains scope freeze rules
- Contains fix cap rules
- Contains confidence annotation format

**U4 Interaction Quality**: Checks output quality and interaction experience:
- posttool-format-gate.sh provides direction/summary
- matcher configured as `.*` (full coverage)
- posttool-anti-pattern-detect.sh exists (A2/F1/H1 real-time blocking)

**U5 Permission Boundary Clarity**: Checks human-AI permission boundary clarity:
- permission-gate.sh includes SCOPE_WRITE_RE / gh_write_regex and other precise scopes
- pretool-sensitive-edit.sh includes sensitive file match list
- index.md includes Git operation gate descriptions
- privacy-gate.sh includes `.env`/private key detection

---

## Scoring Formula

### Base Score

Each sub-dimension's base score is determined by its check item pass rate:

```
base_score = features_present / features_total
```

Example C1 (3 checks): all pass → base = 1.0; 2 pass → base = 0.67.

### Maturity Coefficient

Mechanism quality matters more than existence. Maturity reflects actual enforcement strength:

| Maturity | Value | Meaning | Example |
|----------|-------|---------|---------|
| Hard-block | 1.00 | exit 2, aborts execution | permission-gate blocks rm -rf |
| Active | 0.90 | Produces actionable warnings/context, doesn't block | claim-audit outputs additionalContext |
| Advisory | 0.85 | Reference or passive check | index.md iron laws |

### Lesson Penalty

R-prefix lessons are parsed from claude-next.md and mapped to dimensions:

```
penalty = base_penalty × hits
if fixed: penalty ×= 0.3
penalty = min(penalty, 0.3)  # cap at 30%
```

### Final Score

```
final = max(0, base × maturity - penalty)
```

### Weighted Aggregation

```
weighted_sum = Σ(final × weight) / total_weight
composite_10 = weighted_sum × 10
composite_8 = weighted_sum × 8
```

---

## Score Interpretation

| Composite | Meaning |
|-----------|---------|
| 9.0+ | Excellent — all dimensions well covered, key mechanisms at hard-block level |
| 8.0-8.9 | Good — core dimensions complete, some limited by maturity or lesson penalty |
| 7.0-7.9 | Adequate — major dimensions covered, but clear weak spots exist |
| < 7.0 | Needs improvement — multiple dimensions have gaps, mechanisms need supplementing |

### Current Baseline

The current Carror OS baseline score is saved at `.omc/state/score-baseline.json`. Run the following to see the latest score:

```bash
bash .claude/scripts/score-self-check.sh           # Latest report
bash .claude/scripts/score-self-check.sh --init    # Update baseline
bash .claude/scripts/score-self-check.sh --diff <baseline>  # Diff comparison
```

---

## Relationship to Other Scoring Systems

| System | Dimensions | Relationship |
|--------|-----------|-------------|
| Three-dimension internal (Defense/Amplification/Governance) | 3 | C+E maps to Defense, G is independent, U is new |
| Dual-domain 12-dimension | 12 | Capability domain ≈ C, Governance domain ≈ G+E |
| Product comparison scorecard | 10 | Different granularity for external benchmarking |

This scoring framework is the project's **official dimension system**. All evaluation reports should use it as the baseline.
