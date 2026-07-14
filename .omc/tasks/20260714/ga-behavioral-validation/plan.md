# Plan
## Goal
Close the final review gap by adding a deterministic GA behavioral validation suite for the five scenarios called out by the MVP review notes, while preserving honest non-GA certification semantics.

## Scope
Allowed code/doc changes for this task:

- `.claude/scripts/ga_behavioral_validation.py`
- `.claude/scripts/formal_seal.py`
- `improve_plan/final_round/remaining-ga-gates.md`
- `.omc/tasks/20260714/ga-behavioral-validation/plan.md`
- `.omc/tasks/20260714/ga-behavioral-validation/executor.md`
- `.omc/session-handoff.md`

Generated evidence allowed after verification:

- `.omc/metrics/runtime-verify/ga-behavioral-validation.json`
- `.omc/metrics/runtime-verify/ga-bhv-*.json`
- `.omc/metrics/runtime-verify/evidence.jsonl`
- `.omc/metrics/runtime-verify/manifest.json`
- `.omc/metrics/runtime-verify/sha256sums.txt`
- `improve_plan/final_round/acceptance-identity.yaml`
- `improve_plan/final_round/rc2-formal-seal-manifest.json`

Out of scope:

- No OpenCode certification.
- No production unattended certification.
- No false `ga_ready: true` claim.

## Steps
- [x] S1: Add deterministic GA behavioral validation harness with five final-review scenarios.
- [x] S2: Wire formal seal to surface behavioral validation evidence while keeping `ga_ready: false`.
- [x] S3: Update final GA gate documentation and task evidence ledger.
- [x] S4: Run syntax, negative, observability, behavioral, formal seal, and diff hygiene checks.

## Verify
- S1: `python3 -m py_compile .claude/scripts/ga_behavioral_validation.py .claude/scripts/formal_seal.py` exits 0.
- S2: `python3 .claude/scripts/ga_behavioral_validation.py` exits 0 and writes aggregate evidence with five passing scenarios and `ga_ready: false`.
- S3: `python3 .claude/scripts/formal_seal.py` exits 0, remains SEALED, and keeps `ga_ready: false`.
- S4: `git diff --check` exits 0.

---
> 冻结规则：不改 scope、不改 step 顺序、不改 verify 条件。
