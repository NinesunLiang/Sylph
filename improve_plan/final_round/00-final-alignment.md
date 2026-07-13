# CarrorOS Base 1.0 RC2 Final Alignment

> Scope: align `opus-4.8.md`, `gpt-5.6Sol.md`, and `grok-4.5.md` without rewriting the reviewers' original judgments.
> Date: 2026-07-13
> Target label: `CarrorOS Base 1.0 RC2 — Claude Code`

---

## 1. Unified Verdict

```yaml
final_aligned_verdict: APPROVE_RC2
engineering_release: APPROVED
formal_evidence_seal: SEALED
score_band: 8.1-8.4
aligned_score: 8.35/10
confidence: high

certified_scope:
  platform: Claude Code only
  writers: 1
  sessions_per_task: 1
  modes:
    - L1 short tasks
    - L1 medium tasks with human checkpoint
    - L2 supervised tasks with explicit human gate
  unattended: false

not_certified:
  - CarrorOS GA
  - OpenCode path
  - dual-stack base
  - multi-session concurrent writing
  - unattended production operation
  - Qwen3.6-27B production certification
```

Aligned conclusion:

- Opus and Grok approve RC2 immediately.
- GPT conditionally approved engineering RC2 and identified two formal evidence hold points.
- Those hold points are now closed by the generated formal-seal artifacts: `acceptance-identity.yaml`, `.omc/metrics/runtime-verify/manifest.json`, `.omc/metrics/runtime-verify/sha256sums.txt`, and `.omc/metrics/runtime-verify/h-cas-stale-evidence.json`.
- The reconciled position is: **RC2 engineering release is approved; the formal RC2 evidence seal is sealed; GA remains blocked by longitudinal observability and OpenCode certification.**

This means there is no need for Round 4 architecture work. The remaining work is longitudinal measurement and GA hardening.

---

## 2. Reviewers' Positions Reconciled

| Reviewer | Original verdict | Primary boundary protected | Alignment result |
|---|---|---|---|
| Opus-4.8 | `APPROVE_RC2` | physical stop, recovery, single-writer boundary | Engineering release approved |
| GPT-5.6 Sol | `CONDITIONAL_APPROVE_RC2` | evidence reproducibility, CAS wording, manifest identity | Formal hold points closed by formal-seal artifacts |
| Grok-4.5 | `APPROVE_RC2` | long-session health, L5 ratio, cost/cache observability, OpenCode split | Engineering release approved; GA observability gates retained |

The apparent disagreement is not a product disagreement. It is a signature-level disagreement:

```yaml
shared_consensus:
  rc2_engineering_release: true
  opencode_out_of_scope: true
  unattended_ga_not_ready: true
  multi_writer_not_certified: true
  l5_summary_not_soot: true
  evidence_packaging_closed_for_rc2: true
```

---

## 3. Hold Point Closure Status

### HP-1: `H-CAS-STALE` wording

Final aligned wording:

```yaml
H-CAS-STALE:
  intended_semantics: stale writer must be rejected
  stale_write_applied: false
  expected_result: CAS_CONFLICT
  final_revision: unchanged_after_rejected_stale_writer
  multiprocess_atomicity: NOT_CERTIFIED
```

Interpretation:

- RC2 only certifies single writer / single session.
- Logical stale-revision rejection is required for the report wording to be correct.
- Cross-process compare-and-write atomicity still requires `flock`, `fcntl`, SQLite serialization, or an equivalent lock before GA.

Current evidence status:

```yaml
wording_clarified_in_alignment: true
structured_raw_cas_evidence_present: true
structured_raw_cas_evidence_path: .omc/metrics/runtime-verify/h-cas-stale-evidence.json
rc2_blocking: false
ga_blocking: false_for_current_evidence_backed_cas_serialization
```

Sealed evidence shape:

```json
{
  "test_id": "H-CAS-STALE",
  "initial_revision": 1,
  "writer_a": {
    "expected_revision": 1,
    "result": "COMMITTED",
    "new_revision": 2
  },
  "writer_b": {
    "expected_revision": 1,
    "result": "CAS_CONFLICT"
  },
  "final_revision": 2,
  "stale_write_applied": false,
  "status": "PASS"
}
```

### HP-2: Evidence Root

Current repository snapshot sealed during formal-seal generation:

```yaml
acceptance_identity:
  git_commit_full: "6afbdff40826fb036f152aff1d86c19816f130d6"
  git_dirty_current_worktree: true
  generated_at: "2026-07-13T15:29:01+00:00"
  evidence_path: ".omc/metrics/runtime-verify/evidence.jsonl"
  evidence_records: 184
  evidence_sha256: "02dbd96520f3e39efbf7ff3fed232fc3d6dd70a75fc67348f78d028d89831049"
  manifest_path: ".omc/metrics/runtime-verify/manifest.json"
  manifest_sha256: "96aba31bd61cc13241afe82839eb64b37639e2e927a56e4c6210d61f375b6947"
```

Formal RC2 seal status:

```yaml
formal_evidence_seal: SEALED
suite_total_executions: 184
suite_latest_execution_counted: 42
suite_total_unique_tests: 42
passed: 42
failed: 0
skipped: 0
sha256sums_path: ".omc/metrics/runtime-verify/sha256sums.txt"
```

---

## 4. Final Release Matrix

```yaml
approved_now:
  product: "CarrorOS Base 1.0 RC2 — Claude Code"
  operational_mode:
    human_supervision: required
    unattended: false
  task_classes:
    - L1 short production tasks
    - L1 medium production tasks with checkpoint
    - L2 supervised tasks with explicit plan and human gate
  concurrency:
    writers: 1
    sessions_per_task: 1

must_keep:
  - token.json is the only deterministic source of truth
  - handoff.md is navigation only, not source of truth
  - artifacts are full evidence; previews may be lossy but recoverable
  - VerifyGate failure cannot be overridden by Oracle, Mate, or Meta
  - archived tasks cannot automatically resume
  - L5 / AutoCompact summaries are lossy and must never become memory source
  - CRITICAL water must checkpoint before any further governance action
  - governance files must not be silently rewritten by ordinary task agents

forbidden_claims:
  - "CarrorOS Base 1.0 GA"
  - "CarrorOS dual-stack is complete"
  - "OpenCode certified"
  - "safe multi-session concurrent writing"
  - "unattended production operation"
  - "Phase 3 is heterogeneous-model fault isolation"
  - "Qwen3.6-27B is production-certified for Claude Code"
```

---

## 5. RC2 to GA Gates

```yaml
ga_gates:
  deterministic_gates_closed:
    - H-CONCURRENT-WRITER-CONFLICT
    - H-L5-RECOVERY
    - H-ARTIFACT-MISSING
    - H-WATER-CRITICAL-HARD-PAUSE
    - H-WATER-PRETOOL-WHITELIST

  longitudinal_observability:
    - 30+ turn session distribution
    - controllable_tokens p50 and p95
    - critical trip frequency
    - compact request/resume success rate
    - L5 ratio, target near 0
    - token cost per session
    - token cost per successful task
    - cache hit rate or stable-prefix proxy metric

  opencode:
    - independent certification package
    - non-destructive prune audit
    - SQLite raw-session recovery proof
    - task lease / serialized writer proof
    - provider routing and privacy boundary
```

---

## 6. Context Waterline Clarification

The final-round documents use the 70% waterline as a CarrorOS governance threshold, not as proof that Claude Code will automatically compact at 70% UI context usage.

Aligned clarification:

```yaml
waterline_70_percent:
  meaning: CarrorOS-controlled context budget enters CRITICAL
  source: controllable injected tokens / CarrorOS configured budget
  current_behavior: checkpoint + soft pause / compact request
  not_equal_to: Claude Code UI total context percentage
  not_guaranteed_to_trigger: native auto compact
```

Why the UI can show high context without the CarrorOS gate firing:

- CarrorOS water currently estimates only controlled project injection: `AGENTS.md`, `.claude/kernel.md`, `.claude/index.md`, `.claude/settings.json`.
- Claude Code UI context includes much more: system instructions, loaded skills, tool schemas, large tool outputs, long markdown reads, and conversation transcript.
- `autoCompactEnabled` and `autoCompactWindow` are not set in the project settings observed during this alignment.
- Therefore a UI value such as 88% does not prove CarrorOS water math is fake; it proves the two percentages are measuring different denominators.

Required fix if the project wants 70% to be a real operational compact trigger:

```yaml
needed:
  - capture actual model input token usage when available
  - distinguish controllable_tokens from total_context_tokens
  - write both values into token.json/session telemetry
  - add PreCompact/PostCompact evidence hooks
  - decide whether to configure Claude Code native autoCompactEnabled / autoCompactWindow
```

Until then, claims should say:

```text
CarrorOS provides a 70% controlled-context governance threshold.
It does not yet prove native Claude Code auto-compact at 70% total UI context.
```

---

## 7. Final Archive Statement

```yaml
archive_statement:
  final_decision: "APPROVE RC2 engineering release"
  formal_evidence_status: "SEALED"
  next_required_artifact: "longitudinal GA observability samples and OpenCode certification package"
  round_4_architecture_required: false
  ga_ready: false
```

Final aligned wording:

> CarrorOS Base 1.0 RC2 is approved for Claude Code, single writer, single session, human-supervised L1/L2 operation. The system has closed the core RC2 architecture loop: disk-backed state, water governance, tool-result storage, VerifyGate priority, Phase 3 disagreement handling, and explicit OpenCode exclusion. The formal RC2 evidence seal is sealed. The remaining GA work is real long-session observability, cost/cache distribution evidence, and OpenCode independent certification.
