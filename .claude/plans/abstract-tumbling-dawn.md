# Plan: Fix 7 Issues + Optimize Scope & Terminal-Safety Rules

## Context

Meta-Oracle scoring revealed 7 issues (2 P0, 5 P1) in Carror OS v6.5.0. This plan addresses all 7 with precise fixes, plus optimizations to the scope-gate and terminal-safety rules that caused friction during the scoring session itself.

**Correction from scoring report**: flywheel.log DOES exist at `~/.claude/flywheel.log` (38,876 lines, actively writing). The scoring report's "flywheel.log 完全不存在" was checking `.omc/state/flywheel.log` instead of the actual path `$HOME/.claude/flywheel.log`. The real fix is: (a) update flywheel-report.py to check the correct path, (b) add a symlink or copy from `.omc/state/` for tooling convenience.

---

## Task List (7 issues + 2 optimizations = 9 tasks)

### Task 1: [P0] Fix flywheel.log path discovery
**Files**: `.claude/scripts/flywheel-report.py`, `.claude/hooks/harness_config.sh`
**Problem**: flywheel_event writes to `$HOME/.claude/flywheel.log` but scoring tools check `.omc/state/flywheel.log`. The file exists and works (38,876 lines), but the path is undiscoverable.
**Fix**: 
- Add a symlink: `ln -sf ~/.claude/flywheel.log .omc/state/flywheel.log`
- OR update flywheel-report.py to check both paths, preferring `$HOME/.claude/flywheel.log`
- Update kernel.md to document the actual path

### Task 2: [P0] Fix error-dna classifier — add missing categories
**Files**: `.claude/hooks/error-dna.sh` (lines 220-240)
**Problem**: Classifier works (147 entries: 86 runtime, 55 file_ops, 6 git) but lacks `build`, `test`, `dependency`, `lint`, `docker`, `network` categories. The `runtime` catch-all is too broad (58% of entries).
**Fix**: 
- Add `python3`, `node`, `deno` to build category
- Add `bash -n`, `shellcheck` to lint category
- Add `brew`, `gem`, `cargo install` to dependency category
- Add `ssh`, `api`, `fetch` to network category
- Add `docker` category (currently missing from classifier)
- Add `make`, `cmake`, `mvn`, `gradle` to build category

### Task 3: [P1] Fix scope-gate fnmatch pattern matching (scope optimization)
**Files**: `.claude/hooks/pretool-scope-gate.sh`
**Problem**: The fnmatch-based matching only supports flat patterns. `Benchmarking/` does NOT match `.claude/Benchmarking/file.md` because fnmatch doesn't do recursive directory matching. This caused 6+ blocks during the scoring session.
**Fix**: 
- Add recursive glob support: if pattern ends with `/`, auto-expand to `pattern*` and `**/pattern/*`
- Add `fnmatch.filter()` with `*` prefix for directory patterns
- Specifically: patterns ending in `/` should match any path containing that directory segment

### Task 4: [P1] Fix terminal-safety Rule 6 — increase max_command_length
**Files**: `.claude/hooks/pretool-terminal-safety.sh`, `.claude/harness.yaml`
**Problem**: Rule 6 hard-blocks python3 -c > 120 chars AND any command > 2000 chars. The 120-char limit for python3 -c is too aggressive — many legitimate commands exceed this. The 2000-char limit for general commands is reasonable.
**Fix**:
- Remove the 120-char python3 -c hard block (line 42-52) — python3 heredocs can be long
- Keep the 2000-char hard block (line 56-63) — this prevents genuine terminal truncation
- Change python3 -c > 120 chars to a **warning** instead of hard block
- Update `.claude/rules/terminal-safety.md` Rule 6 to reflect the new limits

### Task 5: [P1] Fix source mirror — create missing hooks directory and sync
**Files**: `scripts/package-release.sh`, `source/.claude/hooks/`
**Problem**: `source/.claude/hooks/` directory does not exist, meaning source mirror sync has never run successfully for hooks.
**Fix**:
- Create `source/.claude/hooks/` directory
- Sync all hooks: `rsync -a .claude/hooks/ source/.claude/hooks/`
- Check `scripts/package-release.sh` for the sync logic — fix if it's writing to wrong path
- Verify with `audit-hooks.sh --check-source-mirror`

### Task 6: [P1] Fix auto-score UX=100% — add runtime quality metrics
**Files**: `.claude/scripts/score-ux.sh`
**Problem**: UX scoring is purely existence-based (checks if files exist, not whether UX is good). All 5 sub-dimensions score 2/2 because config files exist.
**Fix**: Add runtime quality checks:
- UX1: Check actual session turns from session-turns.json (already partially done)
- UX2: Check actual interruption count from session data
- UX3: Check completion-gate rejection rate from error-signals.jsonl
- UX4: Check error-dna classification diversity (not just existence)
- UX5: Check autonomous mode session duration from flywheel.log
- Add a calibration factor: `max(config_score, runtime_score * 0.5)` to prevent pure-config scoring

### Task 7: [P1] Fix retry-budget — ensure counter increments correctly
**Files**: `.claude/hooks/error-dna.sh` (lines 314-336), `.omc/state/retry-budget.json`
**Problem**: 145 signatures, all retry_count=1. The counter increments once per unique signature but never sees the same command twice because the MD5 signature includes variable parts (timestamps, session IDs, temp paths).
**Fix**:
- Add signature normalization: strip timestamps, session IDs, temp paths before hashing
- Specifically: replace patterns like `\d{8}-\d{6}` (timestamps), session IDs, temp file paths with a placeholder before MD5
- This ensures the same logical command retries produce the same signature

### Task 8: [P1] Fix oracle-gate config drift — align settings and harness
**Files**: `.claude/harness.yaml` (line 130), `.claude/settings.json`
**Problem**: oracle_gate is `false` in harness.yaml but registered in settings.json hooks. This wastes a SessionStart hook call.
**Fix**: Either:
- Option A: Set `oracle_gate: true` in harness.yaml (re-enable) — but this needs Oracle review
- Option B: Remove oracle-gate.sh registration from settings.json hooks — cleaner, no review needed
- **Recommendation**: Option B — oracle_gate was deliberately disabled (per auto-score appendix), so remove the dead registration

### Task 9: [P2] Optimize scope definition mechanism
**Files**: `.claude/hooks/pretool-scope-gate.sh`, `.claude/scripts/auto-scope.sh`
**Problem**: The scope gate is too rigid — it blocks legitimate operations that are within the spirit but not the letter of the scope.
**Fix**:
- Add `auto-extend` mode: when a Write/Edit to an out-of-scope file is detected, auto-add the file's directory to scope patterns and log it
- Add scope pattern inheritance: if `rpe/<name>/` is in scope, auto-include `rpe/<name>/**/*`
- Add comment-based scope hints: files can contain `# scope: <pattern>` comments that auto-register

---

## Verification Plan

After each fix, verify with:
1. **Task 1**: `ls -la .omc/state/flywheel.log` → should exist (symlink)
2. **Task 2**: `python3 -c "import json; [print(json.loads(l).get('error_type')) for l in open('.omc/state/error-dna.jsonl')]" | sort | uniq -c | sort -rn` → should show 8+ categories
3. **Task 3**: `python3 -c "import fnmatch; print(fnmatch.fnmatch('.claude/Benchmarking/x.md', '.claude/Benchmarking/*'))"` → should be True
4. **Task 4**: `python3 -c "import json; print(json.load(open('.claude/harness.yaml'))...)"` → max_command_length should be reasonable
5. **Task 5**: `ls source/.claude/hooks/ | wc -l` → should match `ls .claude/hooks/*.sh | wc -l`
6. **Task 6**: `bash .claude/scripts/score-ux.sh --json` → UX score should be < 10/10
7. **Task 7**: Simulate retry: run same command twice → retry_count should be 2
8. **Task 8**: `grep -c 'oracle_gate' .claude/settings.json` → should be 0 if removed
9. **Task 9**: Write to `.claude/Benchmarking/test.md` → should auto-extend scope

## Oracle + Meta-Oracle Dual Review

After all 9 tasks are implemented:
1. Run `bash .claude/scripts/harness-smoke-test.sh` — all 208/208 must pass
2. Run `bash .claude/scripts/audit-hooks.sh` — no 🔴 issues
3. Submit to Oracle for ACCEPT
4. Submit to Meta-Oracle for final ACCEPT
5. Only then mark as done
