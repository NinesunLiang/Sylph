# Next Steps — Engineering Roadmap

> Ongoing packaging and documentation improvements for Carror OS.

---

## Current Status

The three-tier architecture (Base / Enhanced / mechanism toggles) is correct. It properly separates **system complexity** from **user-facing complexity**.

The remaining engineering work falls into three areas:

### 1. Default Value Calibration

Which mechanisms should be enabled by default in Base Edition? The current defaults are conservative (max safety), but some users may benefit from relaxed defaults in specific scenarios. 

**Pending**: Review each hook's `hc_enabled` default in `harness.yaml` against real-world dogfooding data.

### 2. Information Architecture for Advanced Docs

The transition path from "zero knowledge" to "advanced user" needs to be clearer:

- Onboarding guide covers installation + first encounters (done)
- Concepts docs cover each mechanism (done)
- Missing: a structured "learning path" that connects concepts to practice

**Pending**: Cross-reference audit between docs/ directories to ensure no orphaned topics and complete navigation paths.

### 3. False Positive Rate Tuning

When a gate fires and the user doesn't understand why, the experience breaks trust. Current challenges:

- `completion-gate` edge cases (false trigger on legitimate completion claims)
- `context-guard` warn vs danger threshold calibration
- `permission-gate` whitelist ergonomics

**Pending**: Collect dogfooding false positive reports and add a feedback mechanism in gate output messages.

---

## Priority

Calibration (1) and IA (2) are prerequisites for FP tuning (3). Expected order:

1. Default calibration — low effort, high impact (1-2 days)
2. Docs IA — medium effort, medium impact (3-5 days)
3. FP tuning — ongoing, requires dogfooding data (continuous)
