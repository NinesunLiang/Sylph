# Carror OS Documentation Audit — 2026-05-09

## Reference State
- `.claude/skills/` — **25 files**, all have content ✓
- `.claude/hooks/` — **32 files**, all have content ✓
- `source/lx-skills-v5/` — OLD/STUB (should NOT be treated as current)
- `source/harness-kit/` — OLD/STUB (should NOT be treated as current)
- Rev2 audit: `docs/internal/audit-v6.1.8-rev2.md` = 72/100
- Old audit: `docs/internal/audit-v6.1.8.md` = 40/100 (flawed)

---

## FILES TO CHANGE (with specific changes needed)

### 1. docs/internal/audit-v6.1.8.md (OLD — 40/100)
**Status:** Superseded by rev2. Should be archived or heavily rewritten.
- ❌ References `source/lx-skills-v5/` as if it's the current skill directory — **factual error**. Actual skills are in `.claude/skills/` (25 files, all have content).
- ❌ References `source/harness-kit/` as if it's the current hooks directory — **factual error**. Actual hooks are in `.claude/hooks/` (32 files, all have content).
- ❌ Scores 40/100 based on wrong directory assessment. The rev2 audit correctly scores this at 72/100 after fixing the directory confusion.
- ❌ Claims "Skills are empty" (the core reason for the low score). Skills are NOT empty — `.claude/skills/` has 25 files with real content.
- **Change:** Add prominent header: `[SUPERSEDED] Use docs/internal/audit-v6.1.8-rev2.md instead.` Or archive as `audit-v6.1.8-superseded.md`.

### 2. docs/internal/scoring-defense-amplify-governance.md
**Status:** Framework doc has issues.
- ❌ Claims "Governance: 9.0/10" and "Capability: 7.5/10" in the summary — these don't match the rev2 audit's C1-C9 and E1-E8 scoring methodology.
- ❌ The framework uses a different rubric (C1-C9, E1-E8) than what the rev2 audit actually applied.
- ❌ The "Total Score" of 75/100 is inconsistent with the rev2 audit score of 72/100.
- **Change:** Update to align with rev2 audit's scoring methodology and numbers, or restructure as a standalone framework document not tied to specific scores.

### 3. docs/technical/architecture-review.md
**Status:** Needs update for current structure.
- ❌ References `source/lx-skills-v5/` in places — should reference `.claude/skills/`.
- ❌ References `source/harness-kit/` in places — should reference `.claude/hooks/`.
- ❌ Contains stale architecture descriptions that don't match the current three-stage rocket model (Harness Only / Base Edition / Enhanced Edition).
- **Change:** Replace all `source/lx-skills-v5/` with `.claude/skills/`. Replace all `source/harness-kit/` with `.claude/hooks/`. Update architecture description to match current editions model.

### 4. docs/internal/better-info.md & docs/internal/better-info2.md
**Status:** These appear to be draft/analysis files from the AI review process.
- ❌ `better-info.md` references `source/lx-skills-v5/` and suggests this as the current location.
- ❌ `better-info2.md` references `source/lx-skills-v5/` and suggests renaming `.claude/skills/`.
- **Change:** Both documents are based on the flawed assessment. Either rewrite them with correct facts or consolidate into a single updated analysis in `docs/internal/`.

### 5. docs/marketing/industry-benchmark.md
**Status:** References non-existent files.
- ❌ Line 33: `[自动化特性验收测试](../tests/auto-feature-test.md)` — file exists ✓ (at `docs/tests/auto-feature-test.md`)
- ❌ Line 34: `[全人工逐项验收测试](../tests/manual-acceptance-test.md)` — file exists ✓ (at `docs/tests/manual-acceptance-test.md`)
- ✅ These paths are actually correct since they use `../tests/` relative to the marketing folder.
- **Verdict:** Minor — keep as-is, paths resolve correctly.

### 6. docs/governance/features.md
**Status:** References non-existent files in internal/ folder.
- ❌ Line 84: `auto-feature-test.md` — does NOT exist at this path (it's in `docs/tests/`, not referenced correctly).
- ❌ Line 85: `auto-feature-test-log.md` — does NOT exist at this path (it's in `docs/tests/`).
- ❌ Line 95: `manual-acceptance-test.md` — does NOT exist at this path (it's in `docs/tests/`).
- ❌ Line 96: `manual-acceptance-test-log.md` — does NOT exist at this path (it's in `docs/tests/`).
- **Change:** Update all references to use correct relative paths: `../tests/auto-feature-test.md`, etc.

### 7. docs/governance/editions.md
**Status:** Number discrepancies.
- ❌ Claims "32 个底层 Hook 脚本" — actually **32 hooks** ✓ (correct)
- ❌ Claims "10 款自动化审查门禁 Skills" in Base Edition — verify against actual `.claude/skills/`
- ❌ Claims "14 款主动式工作流 Skills" in Enhanced Edition — verify count
- ❌ Total "24 款流水线 Skill" stated multiple times, but actual `.claude/skills/` has **25 files**
- ❌ References `bash install.sh harness/base/enhanced` — verify these commands work with current setup
- **Change:** Verify skill counts against actual directory contents and update numbers.

### 8. docs/marketing/FAQ.md
**Status:** Contains path reference issue.
- ❌ Line 49: `[已验证: /Users/lucas.liang/Desktop/Sylph/Carror_OS/.claude/hooks/context-guard.sh:50-70]` — This absolute path reference in public-facing FAQ is awkward.
- **Change:** Remove or generalize the `[已验证: ...]` annotation, as it leaks internal paths to public documentation.

### 9. docs/internal/behavior-matrix.md
**Status:** References non-existent directory.
- ❌ Mentions `harness-kit` as a component — this old stub path doesn't reflect reality.
- **Change:** Update to reference `.claude/hooks/`.

### 10. docs/internal/execution-types.md & execution-types-structure.md
**Status:** Reference old directory structure.
- ❌ Both reference `source/lx-skills-v5/` as the skills location.
- **Change:** Replace with `.claude/skills/`.

### 11. docs/internal/carror-os-assessment-20260505.md
**Status:** Score discrepancy with benchmark file.
- ❌ Claims "Benchmark 得分: 69.5/80" but `docs/internal/benchmark/pass-rate-summary-20260505.md` shows Carror OS at **72/80**.
- ❌ References "v4" version which predates v6.1.8.
- **Change:** Update score to match benchmark file (72/80), or note the discrepancy.

### 12. docs/internal/benchmark/*.md (all 6 files)
**Status:** Mixed accuracy.
- `pass-rate-summary-20260505.md` — Claims 72/80 for Carror OS. Verify against actual `.claude/skills/` state (25 skills, 32 hooks).
- `shellcheck-20260505.md` — Claims 0 real defects. Verify against current hook quality.
- `bandit-20260505.md` — Python security scan results. Should be current.
- **Change:** Update any benchmark scores that reference `source/lx-skills-v5/` or incorrect skill counts.

### 13. docs/marketing/PRESS-KIT.md
**Status:** Number discrepancies with actual state.
- ❌ Claims "30 个应用层 Hook" — actually **32 hooks** in `.claude/hooks/`.
- ❌ Claims "24 个工作流 Skill" — actually **25 skills** in `.claude/skills/`.
- ❌ References `lx-skills` naming (not the actual `.claude/skills/` path).
- **Change:** Update hook count to 32, skill count to 25. Replace `lx-skills` references with `.claude/skills/`.

### 14. docs/marketing/harness-landscape-2026.md
**Status:** Mostly accurate but has stale references.
- ❌ References "30 个注册 Hook" — should be **32**.
- ❌ Line 96: "30 个注册 Hook" — should be **32**.
- **Change:** Update hook count to 32.

### 15. docs/marketing/FAQ.md (continued)
**Status:** Number discrepancies.
- ❌ Line 60: "32 个 Hook" — correct ✓
- ✅ Overall numbers in FAQ are mostly accurate.

### 16. docs/governance/MIGRATION.md
**Status:** Mostly accurate.
- ✅ Correctly references `.claude/hooks/` and `.claude/skills/`.
- **Verdict:** Good quality, minor review only.

### 17. docs/governance/TESTING.md
**Status:** Needs minor verification.
- ✅ References `.claude/hooks/` correctly.
- **Verdict:** Good, minor review only.

---

## FILES TO KEEP AS-IS (good quality)

### Internal Docs
- **docs/internal/audit-v6.1.8-rev2.md** — 72/100, correct methodology and scoring ✓
- **docs/internal/EVIDENCE-BANK.md** — Well-maintained evidence collection ✓
- **docs/internal/DOGFOODING-LOG.md** — Current dogfooding record ✓
- **docs/internal/ac-template.md** — Acceptance criteria template, useful reference ✓

### Governance
- **docs/governance/MIGRATION.md** — Clear, accurate migration guide ✓
- **docs/governance/TESTING.md** — Accurate test documentation ✓

### Marketing
- **docs/marketing/v6.1.8-dual-domain-scoring.md** — Updated scoring (May 7, 2026) with new capabilities ✓
- **docs/marketing/FAQ.md** — Mostly accurate, minor path cleanup needed (see #8 above)

### Technical
- **docs/technical/benchmark-report.md** — Verify if current, otherwise flag for update
- **docs/technical/product-guide.md** — Review if it references correct paths

### Tests (correctly located)
- **docs/tests/auto-feature-test.md** — Exists and referenced correctly from `industry-benchmark.md` ✓
- **docs/tests/manual-acceptance-test.md** — Exists and referenced correctly from `industry-benchmark.md` ✓
- **docs/tests/final-exam.md** — "Final Exam" test suite, well structured ✓
- **docs/tests/auto-feature-test-log.md** — Test log template ✓
- **docs/tests/manual-acceptance-test-log.md** — Test log template ✓

### Other
- **docs/README.md** — Main documentation entry point
- **docs/concepts/** (audit-trail, context-control, gates, workflow) — Concept docs
- **docs/guides/** (quickstart, first-10-minutes, for-beginners, for-experts) — Guide docs
- **docs/overview/what-is-carror-os.md** — Product overview

### Marketing Archive (keep but mark as historical)
- All files in `docs/marketing/archive/` — These are draft/historical versions. They should be clearly marked as archived/superseded but can remain for reference.

---

## CROSS-CUTTING ISSUES SUMMARY

1. **Wrong directory references (critical):** Multiple files reference `source/lx-skills-v5/` and `source/harness-kit/` instead of `.claude/skills/` and `.claude/hooks/`. This is the #1 issue — it's a factual error that undermines credibility.

2. **Number discrepancies:** Hook count should be 32 (not 30), skill count should be 25 (not 24). Affects PRESS-KIT, editions.md, harness-landscape-2026.md, and possibly others.

3. **Missing files:** `docs/internal/auto-feature-test.md`, `manual-acceptance-test.md`, `launch-plan.md`, `manifesto.md` don't exist but are referenced. The actual files live in `docs/tests/`.

4. **Superseded audit:** The old 40/100 audit (audit-v6.1.8.md) should be clearly marked as superseded to prevent confusion with the current 72/100 rev2 audit.

5. **Score inconsistencies:** Multiple documents show different benchmark scores (69.5/80 vs 72/80). Should be unified to the latest benchmark number.

6. **Scoring framework mismatch:** The scoring-defense-amplify-governance.md framework doesn't align with the actual rev2 audit methodology.
