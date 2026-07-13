# Remaining Gates After RC2 Alignment

This file separates unfinished work into two groups:

- formal RC2 archive seal status
- remaining GA blockers

The engineering RC2 release is approved within the certified scope. These items must not be described as completed until backed by evidence.

---

## 1. Formal RC2 Archive Seal Status

Formal RC2 evidence seal is now sealed for the Claude Code RC2 scope. This does not certify GA.

```yaml
formal_evidence_seal: SEALED
manifest: .omc/metrics/runtime-verify/manifest.json
sha256sums: .omc/metrics/runtime-verify/sha256sums.txt
h_cas_stale_evidence: .omc/metrics/runtime-verify/h-cas-stale-evidence.json
ga_ready: false
```

| ID | Item | Current status | Evidence |
|---|---|---|---|
| SEAL-01 | Full acceptance manifest | Closed | `.omc/metrics/runtime-verify/manifest.json` |
| SEAL-02 | Manifest hash | Closed | `.omc/metrics/runtime-verify/sha256sums.txt` |
| SEAL-03 | Unique test accounting | Closed | `suite.total_executions`, `suite.latest_execution_counted`, `suite.total_unique_tests` in manifest |
| SEAL-04 | Environment fingerprint | Closed | `environment` block in manifest |
| SEAL-05 | `H-CAS-STALE` structured evidence | Closed | `.omc/metrics/runtime-verify/h-cas-stale-evidence.json` |
| SEAL-06 | Clean/dirty state at seal generation | Captured | `git.dirty_current_worktree` in manifest; dirty state is recorded, not hidden |

Sealed artifact set:

```yaml
sealed_files:
  - improve_plan/final_round/acceptance-identity.yaml
  - .omc/metrics/runtime-verify/manifest.json
  - .omc/metrics/runtime-verify/evidence.jsonl
  - .omc/metrics/runtime-verify/h-cas-stale-evidence.json
  - .omc/metrics/runtime-verify/sha256sums.txt
```

---

## 2. GA Gate Status

Several deterministic GA gates have now advanced to evidence-backed PASS. GA as a whole is still not complete because longitudinal observability and OpenCode certification remain pending.

| ID | Gate | Status | Evidence / remaining requirement |
|---|---|---|---|
| GA-CAS-01 | Cross-process writer lock | PASS | `.omc/metrics/runtime-verify/h-concurrent-writer-conflict.json`; `_save_token()` uses `fcntl.flock` + atomic replace |
| GA-CAS-02 | Concurrent writer test | PASS | `H-CONCURRENT-WRITER-CONFLICT`: exactly one commit, one `CAS_CONFLICT`, final JSON valid |
| GA-L5-01 | L5 recovery test | PASS | `.omc/metrics/runtime-verify/h-l5-recovery.json`; L5 summary is not accepted as SOOT |
| GA-L5-02 | Missing artifact detection | PASS | `.omc/metrics/runtime-verify/h-artifact-missing.json`; missing artifact returns `MISSING_ARTIFACT` |
| GA-WATER-01 | CRITICAL hard pause | PASS | `.omc/metrics/runtime-verify/h-water-critical-hard-pause.json`; persists `PAUSED_CONTEXT_CRITICAL` |
| GA-WATER-02 | PreToolUse whitelist | PASS | `.omc/metrics/runtime-verify/h-water-pretool-whitelist.json`; non-whitelisted actions blocked while paused |
| GA-OBS-01 | 30+ turn distribution | PENDING | requires p50/p95 controllable-token data over real long sessions |
| GA-OBS-02 | L5 ratio | PENDING | requires longitudinal L5 count / compact count / session count |
| GA-OBS-03 | Cost metrics | PENDING | requires real token cost per session and per successful task |
| GA-OBS-04 | Cache stability | PENDING | requires provider cache metrics or stable-prefix proxy sample |
| GA-OC-01 | OpenCode independent package | PENDING | requires separate SQLite/prune/lease/provider-route proof package |

---

## 3. Forbidden Until Closed

Do not claim:

```yaml
forbidden_claims:
  - "CarrorOS Base 1.0 GA"
  - "OpenCode certified"
  - "dual-stack complete"
  - "unattended production ready"
```

---

## 4. Allowed Now

Allowed release statement:

```text
CarrorOS Base 1.0 RC2 is approved for Claude Code, single writer, single session, human-supervised L1/L2 operation. Formal evidence seal is sealed. Deterministic GA gates for CAS serialization, L5/missing-artifact recovery, and CRITICAL water hard pause have evidence-backed PASS. Full GA remains blocked on longitudinal observability and OpenCode independent certification.
```
