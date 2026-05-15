# Verifier Reference Tiering Policy

> **Purpose**: Define mandatory/recommended/skip tiers for Verifier node引用 across all skills
> **Version**: v1.0.0
> **Status**: Active
> **Last Updated**: 2026-05-09 (revised: verifier nodes added to lx-oma-gov, lx-prd, lx-root-cause-analysis)

---

## Tier Definition

| Tier | Output Type | Rule | Examples |
|------|-------------|------|----------|
| **T1** | Code / binary / executable output | **MUST** reference verifier | code-review, security-review, test-generation |
| **T2** | Document / report / schema | **SHOULD** reference verifier for high-stakes outputs; SKIP for routine docs | governance reports, PRDs, audit docs |
| **T3** | Read-only dashboard / tracking / utility | **MAY** skip verifier | status panels, todo lists, utility skills |

### Enforcement
- T1 violation → smoke test failure (exit 1)
- T2 high-stakes violation → smoke test warning (exit 0 + stderr alert)
- T3 skip → no action required

---

## Skill Audit (2026-05-09)

### T1 — Code Output (MUST reference verifier)

| Skill | Has Verifier? | Gap |
|-------|--------------|------|
| lx-code-review | ✅ | — |
| lx-security-review | ✅ | — |
| lx-browser-verify | ✅ | — |
| lx-golang-test | ✅ | — |
| lx-react-review | ✅ | — |
| lx-web-perf | ✅ | — |
| lx-rpe | ✅ | — |
| lx-task-spec | ✅ | — |
| lx-debug-spec | ✅ | — |
| lx-pre-commit | ❌ | Debatable: gate skill, IS a quality gate. Output is block/pass decision. Recommend adding verifier for gate effectiveness audit |
| lx-pre-push | ❌ | Debatable: gate skill. Same reasoning as pre-commit. Recommend adding verifier |
| lx-race | ❌ | Debatable: race detection output. Low severity — race reports are diagnostic. Recommend SHALL (T2) not MUST (T1) |
| lx-tdd-spec | ❌ | Debatable: generates test specs. Not executable code. Classify as T2 |

### T2 — Document/Report (SHOULD reference verifier for high-stakes)

| Skill | Has Verifier? | Gap Assessment |
|-------|--------------|----------------|
| lx-oma-gov | ✅ | Governance reports → high-stakes. Verifier added: node + §2.3 workflow + state machine |
| lx-oma-hier | ❌ | Hierarchical decomposition → medium-stakes. Acceptable to skip (docs are human-reviewed) |
| lx-oma-split | ❌ | Feature split docs → medium-stakes. Acceptable to skip (docs are human-reviewed) |
| lx-oma-orch | ❌ | Orchestration → coordination, not output. Acceptable to skip |
| lx-prd | ✅ | PRD generation → high-stakes. Verifier added: node reference in atomic declarations |
| lx-root-cause-analysis | ✅ | RCA reports → high-stakes. Verifier added: node reference in atomic declarations |
| lx-validate-skill | ❌ | Skill validation → meta-skill (IS a verifier for other skills). Acceptable to skip self-verification |
| lx-tdd-spec | ❌ | Test spec generation → medium-stakes. Classified from T1. Acceptable to skip |

### T3 — Read-only / Tracking (MAY skip verifier)

| Skill | Has Verifier? | Assessment |
|-------|--------------|------------|
| lx-status | ❌ | ✅ Appropriate — read-only dashboard |
| lx-todo | ❌ | ✅ Appropriate — light task tracking |
| lx-varlock | ❌ | ✅ Appropriate — utility tool |

---

## Summary

| Category | Count |
|----------|-------|
| Total skills | 23 |
| T1 — MUST have verifier | 13 (9 ✅, 4 debatable) |
| T2 — SHOULD for high-stakes | 8 (3 ✅, 5 acceptable to skip) |
| T3 — MAY skip | 3 (3 ✅ skip) |
| Verified current gap | 0 remaining — 3 recommended skills all resolved |

### Priority Actions — Status

| # | Skill | Action | Status |
|---|-------|--------|--------|
| 1 | 🟡 **lx-oma-gov** | Add verifier: governance report quality validation | ✅ **DONE** — verifier node added, §2.3 workflow, state machine updated |
| 2 | 🟡 **lx-prd** | Add verifier: PRD acceptance criteria validation | ✅ **DONE** — verifier node added to atomic declarations |
| 3 | 🟡 **lx-root-cause-analysis** | Add verifier: RCA finding quality check | ✅ **DONE** — verifier node added to atomic declarations |
| 4 | 🟢 **lx-pre-commit/lx-pre-push** | Defer; gate skills benefit but not critical | ⬜ Deferred |

---

## Audit Method

- All 23 skills in `.claude/skills/` were scanned for `verifier` keyword in their `SKILL.md`
- Skills with explicit `verifier` mention in any section (atomic declarations, nodes, or body) are counted as "Has Verifier"
- Classification by output type: code, document/report, or read-only/tracking
