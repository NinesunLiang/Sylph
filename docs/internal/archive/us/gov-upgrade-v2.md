# Long-Term Governance Upgrade Plan v2 -- Four Items to 80+

> Version: v2 | Date: 2026-05-10
> Baseline: Long-term Governance 68/100 | Target: All four items 80+

---

## 1. Current Overview

```
Long-term Governance 68/100
|- Shield Anti-decay Defense 68  <- error-dna has capture and alert, missing auto-fix loop
|- Cycle Flywheel Self-healing 63  <- flywheel_analytics is deprecated, missing alert channel
|- Transfer Session Handoff ~82 <- session-dump + handoff + proactive complete ✓
|- Note Learning Notes 70  <- token_writer + posttool-edit-quality, missing auto knowledge extraction
|- Link Governance Consistency 65  <- source mirror fixed, 1 yellow drift remaining
```

- Session handoff already >=80 (US-001 delivered session-dump.json), no changes needed
- Four items to improve: anti-decay, flywheel, learning notes, governance consistency

---

## 2. Plan GS-001: Anti-Decay Defense Auto-Fix Loop

### Goal
Upgrade error-dna from "record + alert" to "record + alert + auto-fix proposal."

### Design

New file `.claude/hooks/error-dna-auto-fix.sh` -- Stop hook

```
Trigger: Stop (session end or before /compact)
Behavior:
  1. Read error-dna.json -> filter conditions:
     - count >= 2
     - status != fixed
     - repair_command exists
     - fix_count < 3 (under fix cap)
  2. Sort by count descending
  3. Output additionalContext format:
     [error-dna auto-fix] {N} errors eligible for auto-fix:
      . {signature[:16]} x{count} -- {message[:80]}
       > Fix command: `{repair_command}`  (last failure: {last_seen})
  4. Each output is suggestion-only (hook architecture limits to suggestion, not execution)
```

### Existing Dependencies
- `error-dna.json` already has `repair_command`, `fix_count`, `repair_success` fields ✓
- error-classifier.py already classifies error_type ✓
- `fix_count < 3` already tracked in error-dna.sh ✓

### New Files
- `.claude/hooks/error-dna-auto-fix.sh` (~40 lines shell)

### Registration
- settings.json new `Stop` event
- harness.yaml `error_dna_auto_fix` switch
- audit-hooks R35 regression

### Not Covered
- Hook architecture limit: cannot auto-execute repair_command, only suggest via additionalContext
- If Claude Code opens PostToolUse command execution in the future, can upgrade to auto-fix

---

## 3. Plan GS-002: Flywheel Self-Healing Deprecation Alert

### Goal
flywheel_analytics.py already computes deprecated skills (`days_since_last_use > 30`), but alerts do not reach AI sessions. Need to inject deprecated skill list into additionalContext at Stop.

### Design

Modify `.claude/hooks/skill-flywheel.sh` -- Stop hook append section

```
After existing flush buffer + analytics call, append:
  5. Read flywheel-report.json
  6. Extract deprecated_skills list
  7. If deprecated skills exist:
     [flywheel] Warning: {N} skills deprecated (>30 days unused):
      . {skill_name} -- last used: {days_since} days ago
      . {skill_name} -- last used: {days_since} days ago
     Tip: Consider running /lx-validate-skill or manual removal
```

### Existing Dependencies
- `flywheel_analytics.py` already computes `deprecated_skills` ✓
- `flywheel-report.json` already written ✓
- skill-flywheel.sh already calls analytics ✓

### Changed Files
- `.claude/hooks/skill-flywheel.sh` -- append ~15 lines

### Registration
- Stop event already registered, no new registration needed

---

## 4. Plan GS-003: Learning Notes Auto Knowledge Extraction

### Goal
High-frequency patterns (hits>=3) in claude-next.md are auto-identified and sublimation suggestions output.

### Design

New file `.claude/hooks/knowledge-condenser.sh` -- Stop hook

```
Trigger: Stop
Behavior:
  1. Read .claude/claude-next.md
  2. Regex extract all [seed:*] or *@YYYY-MM-DD hits:N* entries
  3. Filter patterns with hits >= 3
  4. Check if kernel.md already contains the rule (grep rule name or keyword)
  5. Output additionalContext:
     [knowledge-condenser] {N} high-frequency patterns eligible for sublimation to kernel.md:
      . {rule_name} (hits:{N}, age:{days} days) -> {current status}
       | Suggestion: {suggested action: sublimate to kernel.md / update kernel.md / discard}
       \_ Evidence: claude-next.md:line:{N}
```

### Sublimation Rules

| hits | age | Current Status | Suggestion |
|------|-----|---------------|------------|
| >=5 | >=10 days | Already in kernel.md | Update kernel.md, can remove from claude-next.md |
| >=5 | >=10 days | Not in kernel.md | Sublimate to kernel.md |
| >=3 | >=5 days | Already in kernel.md | Update kernel.md (fix wording/add evidence) |
| >=3 | >=5 days | Not in kernel.md | Suggest sublimation, mark pending confirmation |
| >=3 | <5 days | Any | Mark "wait for stability before sublimation" |
| <3 | Any | Any | Ignore (insufficient frequency, continue accumulating) |

### New Files
- `.claude/hooks/knowledge-condenser.sh` (~60 lines)

### Registration
- settings.json new `Stop` event
- harness.yaml `knowledge_condenser` switch
- audit-hooks R36 regression

### State Transition

```
claude-next.md entry lifecycle:
  Creation (hits:1) -> Accumulation (hits:2) -> High-frequency (hits>=3) -> Sublimation candidate (hits>=5, age>=10d)
                                                                              |
                                                                         Update kernel.md
                                                                              |
                                                                         Remove from claude-next.md
```

---

## 5. Plan GS-004: Governance Consistency Fix

### 5.1 Drift Fix
Current 1 yellow drift: posttool-read-cite.sh registered in settings.json for `PostToolUse` but `posttool_read_cite=false` in harness.yaml.

**Fix**: Set `posttool_read_cite` to `true` in harness.yaml (consistent with settings.json registration).

### 5.2 Auto Alert
Enhance `audit-hooks.sh` to output additionalContext, auto-reporting governance consistency status at SessionStart.

### Changed Files
- `.claude/harness.yaml` -- change 1 line

---

## 6. File Change Summary

| File | Type | Plan# |
|------|------|-------|
| `.claude/hooks/error-dna-auto-fix.sh` | New | GS-001 |
| `.claude/hooks/skill-flywheel.sh` | Modified | GS-002 |
| `.claude/hooks/knowledge-condenser.sh` | New | GS-003 |
| `.claude/harness.yaml` | Modified | GS-004 |
| `.claude/settings.json` | Modified | GS-001, GS-003 register Stop |
| `.claude/scripts/audit-hooks.sh` | Modified | GS-004 R35/R36 regression |
| `.claude/scripts/harness-smoke-test.sh` | Modified | GS-004 new regression case |
| `source/harness-kit/` | Sync | All |

---

## 7. Verification Plan

| # | Check | Command/Method |
|---|-------|---------------|
| V1 | error-dna.json entries with repair_command | `python3 -c "import json; d=json.load(open('.omc/state/error-dna.json')); print([k for k,v in d['error_signatures'].items() if v.get('repair_command')])"` |
| V2 | Auto-fix Stop hook syntax passes | `bash -n .claude/hooks/error-dna-auto-fix.sh` |
| V3 | flywheel-report.json deprecated field | `python3 -c "import json; print(json.load(open('.omc/state/flywheel-report.json')).get('deprecated_skills'))"` |
| V4 | knowledge-condenser hits>=3 detection | `python3 -c "import re; c=open('.claude/claude-next.md').read(); print(len(re.findall(r'hits:([3-9]|\d{2})',c)))"` |
| V5 | harness.yaml posttool_read_cite=true | `grep 'posttool_read_cite' .claude/harness.yaml` |
| V6 | Source mirror consistency | `bash .claude/scripts/audit-hooks.sh --check-source-mirror` |
| V7 | Harness smoke regression | `bash .claude/scripts/harness-smoke-test.sh` |
| V8 | All .sh syntax | `bash -n .claude/hooks/*.sh .claude/scripts/*.sh` |

---

## 8. Risks and Rollback

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|------------|
| Hook script syntax error blocks Stop | Low | Low | `exit 0` fallback |
| knowledge-condenser false positive sublimation | Medium | Low | Suggestion only, user confirms |
| New Stop hook increases session end latency | Low | Low | Each <100ms |
| Rollback: git revert + source mirror sync | -- | -- | Verify source mirror consistency before commit |

---

## 9. Estimated Improvement

| Dimension | Baseline | Target | Lever |
|-----------|---------|--------|-------|
| Anti-decay defense | 68 | **82** | +14: auto-fix alert loop |
| Flywheel self-healing | 63 | **80** | +17: deprecation alert injection |
| Learning note accumulation | 70 | **82** | +12: auto knowledge extraction |
| Governance consistency | 65 | **85** | +20: drift fix + auto alert |
| **Weighted Comprehensive** | **68** | **~82** | **+14** |
