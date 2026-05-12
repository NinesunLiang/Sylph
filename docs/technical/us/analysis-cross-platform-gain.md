# Carror OS Cross-Platform Gain Analysis

> Compiled from: Platform Gain Report
> Label: [Internal self-assessment, non-industry-standard]

---

## 1. Analysis Framework

**Method**: Establish a "baseline score without governance" (native model capabilities + native platform infrastructure, excluding any Carror OS prompt injection), then compare against the "score with governance" to derive the delta (Δ).

**Gain Source Breakdown**:
Score with governance = Native platform capability + Carror OS prompt-layer gain + Carror OS-platform infrastructure synergy gain
Baseline without governance = Native platform capability (model natural behavior + hook/sandbox/LSP and other native mechanisms)
Delta (Δ) = Carror OS prompt-layer gain + Carror OS-platform infrastructure synergy gain

### Native Capabilities by Platform

| CLI | Native Features (w/out Carror OS) | Missing Natively |
|-----|----------------------------------|-----------------|
| Claude Code | Hook system, OMC agent system, TodoWrite, basic git safety, model routing | 7 iron laws constraints, evidence hierarchy, fix ceiling, A→B→A verification, soft-language prohibition |
| OpenCode | TodoWrite, native AGENTS.md reading | All governance specifications |
| Codex CLI | Sandbox execution, git diff, code syntax checking | All governance prompt constraints |
| Cursor | .cursorrules empty template, LSP, IDE context | All governance prompt constraints |

---

## 2. Four-Dimension Scoring System

### Dimension C: Capability (C1-C9, max 35)

Includes: Instruction parsing, context structuring, workflow orchestration, delivery standards, knowledge depth, associative reasoning, version iteration awareness, graceful degradation, evidence citation

### Dimension E: Error Prevention (E1-E8, max 35)

Includes: Goal anchoring, hallucination suppression, logical consistency, uncertainty calibration, false-completion detection, root-cause discrimination, error-correction restructuring, constraint forgetting

### Dimension G: Long-term Governance (G1-G6, max 20)

Includes: Knowledge freshness, cross-session handoff, decision traceability, pattern sedimentation, bias self-adaptation, long-term consistency

### Dimension U: User Friendliness (U1-U7, max 10)

Includes: Feedback clarity, clarification interaction, output consumability, user sense of control, error recovery, interaction burden, style adaptation

---

## 3. Summary Comparison

| Dimension | CC NoGov | CC Gov | CC Δ | OC NoGov | OC Gov | OC Δ | Codex NoGov | Codex Gov | Codex Δ | Cursor NoGov | Cursor Gov | Cursor Δ |
|-----------|---------|-------|------|---------|-------|------|-----------|---------|--------|------------|---------|--------|
| Capability C | 26.6 | 30.3 | +3.7 | 20.6 | 27.8 | +7.2 | 17.7 | 21.9 | +4.2 | 19.9 | 24.2 | +4.3 |
| Prevention E | 17.8 | 30.26 | +12.46 | 15.0 | 27.76 | +12.76 | 15.0 | 22.7 | +7.7 | 14.6 | 21.66 | +7.06 |
| Governance G | 17.5 | 17.2 | -0.30 | 6.7 | 13.76 | +7.06 | 5.2 | 11.14 | +5.94 | 6.4 | 12.36 | +5.96 |
| Friendly U | 7.44 | 8.22 | +0.78 | 6.58 | 7.88 | +1.30 | 5.66 | 6.36 | +0.70 | 6.66 | 7.40 | +0.74 |
| **Total** | **69.34** | **85.98** | **+16.64** | **48.88** | **77.20** | **+28.32** | **43.56** | **62.10** | **+18.54** | **47.56** | **65.62** | **+18.06** |

---

## 4. Total Gain Ranking

```
OpenCode   ████████████████████████████  +28.32   Highest ROI
Codex CLI  ███████████████████           +18.54
Cursor     ██████████████████            +18.06
Claude CC  ████████████████              +16.64   High baseline, bounded gain
```

### Gain Heatmap by Dimension

```
           E (Prevention)  C (Capability)  G (Governance)  U (Friendliness)
CC         ████████        ███              ─              █
OC         ████████        ████             ████           █
Codex      █████           ███              ████           █
Cursor     █████           ███              ████           █
```

---

## 5. Five Key Insights

### Insight 1: OpenCode delivers the highest ROI

OpenCode baseline 48.88 → with governance 77.20 → **gain +28.32 points (+57.9% improvement)**

Reason: OpenCode has nearly zero native infrastructure (no hooks, no agent system, no persistence). Carror OS prompt-layer injection is essentially "building governance from scratch," yielding maximum marginal returns.

**Conclusion**: Embedding Carror OS specifications into AGENTS.md and running on OpenCode is the lowest-cost, highest-gain combination.

### Insight 2: Claude Code shows a "governance side effect" in Dimension G (-0.30)

Claude Code without governance G-dimension score: 17.5 (natural OMC infrastructure support), with governance: 17.2, Δ = -0.30.

This is not a bug but a feature conflict:
- **G4 Pattern Sedimentation (-0.60)**: OMC's learner skill has its own pattern sedimentation path; Carror OS's claude-next.md format constraints compete with OMC's format
- **G5 Bias Self-adaptation (-0.42)**: The filtering criteria for "what is worth recording" differ slightly, causing redundant or conflicting writes
- **G6 Long-term Consistency (-0.72)**: OMC's ralph/autopilot has its own continuity mechanism; Carror OS's "context guard > 40% triggers summary and reset" conflicts directionally with OMC

**Conclusion**: Claude Code already has mature governance infrastructure. Some Carror OS rules create "dual-track competition" with OMC specifications, requiring specification fusion rather than simple layering.

### Insight 3: E2 Hallucination Suppression is the most stable cross-platform gain source

| Platform | Without Gov | With Gov | Gain |
|----------|-----------|---------|------|
| Claude Code | 2.4 | 6.88 | +4.48 |
| OpenCode | 2.0 | 6.72 | +4.72 |
| Codex CLI | 2.0 | 5.28 | +3.28 |
| Cursor | 2.0 | 4.80 | +2.80 |

Without governance, all platforms score 2.0-2.4 on hallucination suppression (out of 8) — this is determined by the model's natural hallucination rate, not a problem native platform capabilities can solve. Carror OS's Iron Laws #1/#7 + soft-language ban are currently the most effective prompt-layer hallucination suppression methods known.

### Insight 4: C5 Knowledge Depth is nearly unaffected by Carror OS

All platforms show a knowledge depth gain of approximately +0.3-0.5, the smallest gain item. Reason: Knowledge depth is determined by the underlying model. A prompt-layer governance framework cannot make the model "know more" — it can only make the model "present known information more honestly" (which is exactly the value of C9 evidence citation).

### Insight 5: Codex ≈ Cursor have essentially the same total gain, but different structure

Codex gain +18.54: Dimension E contributes 7.70, Dimension G contributes 5.94
Cursor gain +18.06: Dimension E contributes 7.06, Dimension G contributes 5.96

Both have nearly identical G-dimension gains (+5.94 vs +5.96), but Codex leads by about 0.7 in Dimension E — Codex's sandbox execution contributes extra to E5 (false-completion detection).

---

## 6. Deployment Recommendations (by Gain/Cost Ratio)

| Priority | Deployment Plan | Cost | Gain | ROI |
|----------|----------------|------|------|-----|
| P1 | OpenCode + Full AGENTS.md | Low (file maintenance only) | +28.32 | Highest |
| P2 | Claude Code + Carror OS (spec fusion to resolve G conflicts) | Medium (spec alignment) | +16.64 → est. +18~19 | High |
| P3 | Cursor + .cursorrules with core iron laws | Low | +18.06 | High |
| P4 | Codex CLI + system prompt injection | Medium (external prompt maintenance) | +18.54 | High |

---

## 7. One-Sentence Summary per Platform

**Claude Code**: Strongest native foundation (86 points), Carror OS gain (+16.64) is relatively smallest, but spec fusion conflicts need resolution — not "useless to add," but "adds friction."

**OpenCode**: Weakest native foundation (49 points), largest Carror OS gain (+28.32, +58%), practically a "0→1" transformation — Carror OS's core value is most fully demonstrated here.

**Codex CLI / Cursor**: Similar native foundations (44-48 points), similar gains (+18 points), primarily from Dimension E — the biggest benefit is "preventing AI from falsely believing it has completed a task during code modification."
