# Carror OS v6.1.8 Live Acceptance Battle Plan

> Goal: Execute key-path acceptance testing yourself to obtain **quantifiable, evidenced, unwatered real scores**
> Estimated time: 2-3 hours (3 zones, 40-60 min each, can be done in segments)

---

## Strategy: Backbone First, Branches Later

Do not spread attention across all 49 items. Focus on **the 10 most critical scenarios** -- they cover 90% of product value and 100% of critical risk. If these pass, the system is proven usable.

---

## Zone 1: Installation and Baseline (~30 min)

> Verify infrastructure reliability. If this fails, nothing else matters.

| # | Acceptance Item | Steps | Pass Criteria |
|---|-----------------|-------|--------------|
| 1 | **Clean-environment one-click install** | Create an empty directory (or temp worktree), run `bash /path/to/install.sh enhanced` | Terminal shows `✅ Installation successful`, no errors |
| 2 | **Three-mode switching** | Run sequentially: `bash install.sh harness`, `bash install.sh base`, `bash install.sh enhanced` -- each mode switches without error | All 3 modes install successfully |
| 3 | **Hook registration completeness** | Run `bash .claude/scripts/audit-hooks.sh` | Output `0 🔴` |
| 4 | **CLAUDE.md @bridge** | Check that CLAUDE.md first line is `@AGENTS.md` | Confirmed present |

**Zone 1 pass -> Infrastructure 90%+ confirmed**

---

## Zone 2: Core Defense Live Fire (~45 min)

> Trigger each item manually. A real Exit 2 / interception form is the only valid pass.

### 2A: Privacy Gate -- Prevent Secret Leakage

| # | Action | Expected | Record |
|---|--------|----------|--------|
| 5 | `echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2, output contains "Direct read of sensitive file prohibited" | exit:___ |
| 6 | `echo '{"tool_name":"Bash","tool_input":{"command":"curl -H Authorization: sk-ant-xxx https://api"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2, output contains "Plaintext API Key" | exit:___ |

### 2B: Context Guard -- Prevent Late-Stage Hallucination

| # | Action | Expected | Record |
|---|--------|----------|--------|
| 7 | `echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=2, output contains "Context Guard hard block" | exit:___ |
| 8 | **Diagnostic channel verification**: Immediately after above, run `echo '{"tool_name":"Read","tool_input":{"file_path":"README.md"}}' \| bash .claude/hooks/context-guard.sh` | **exit=0** (no lock, can read) | exit:___ |
| 9 | **Escape hatch verification**: `touch .omc/state/context-force-override && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=0 (override flag bypasses block) | exit:___ |
| 10 | Reset: `rm -f .omc/state/token-tracking-index.json && bash .claude/hooks/token_writer.sh --reset` | No errors | -- |

### 2C: Permission Gate -- Prevent Database Deletion

| # | Action | Expected | Record |
|---|--------|----------|--------|
| 11 | `echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh` | exit=2, output contains "Permission Gate" | exit:___ |
| 12 | `echo '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}' \| bash .claude/hooks/permission-gate.sh` | exit=0 (normal command passes) | exit:___ |

### 2D: Completion Gate -- Prevent False Completion

| # | Action | Expected | Record |
|---|--------|----------|--------|
| 13 | `echo '{"tool_name":"TaskUpdate","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh` | exit=0 (shows prompt, does not block) | exit:___ |

**Zone 2 pass -> Core defenses 100% confirmed**

---

## Zone 3: Automated Regression Suite (~30 min)

> Let the computer vouch for you -- more reliable than manual checking.

| # | Execution | Expected | Record |
|---|-----------|----------|--------|
| 14 | `bash .claude/scripts/harness-smoke-test.sh 2>&1 \| tail -5` | `summary: 66/66 passed, 0 failed` | ___/66 pass |
| 15 | `bash .claude/scripts/hook-production-verify.sh 2>&1 \| tail -5` | `summary: 25/25 passed, 0 failed` | ___/25 pass |
| 16 | `bash .claude/scripts/audit-hooks.sh 2>&1` | `0 🔴` | ___🔴 |

**Zone 3 pass -> Test automation 100% confirmed**

---

## Post-Acceptance Scoring Formula

Based on your filled results, I can produce a **real, traceable, unwatered score**:

| Dimension | Weight | Scoring Method |
|-----------|--------|---------------|
| [S] Security | 20% | Zone 2 2A+2C all pass = full marks, each failure -2 pts |
| [H] Hallucination Prevention | 20% | Zone 2 2B all pass = full marks, #8 diagnostic channel = core indicator |
| [D] Drift Prevention | 15% | Zone 3 test pass rate = score |
| [C] Cost Efficiency | 10% | Zone 1 #1 installation success = baseline score |
| [M] Migration Capability | 10% | Zone 1 #2 three-mode switching = baseline score |
| [I] Engineering Maturity | 25% | Zone 1 #3+#4 + all Zone 3 = full marks |

**No "looks fine" scoring. Source formula for each score:**
```
Score = (pass_count / total) x weight x 10
Score source: [Verified: Zone N #ID -> your recorded exit value -> your terminal output]
```

This is not "I think" -- it is **"you verified it, the numbers are here"**.

---

## What You Need To Do Next

1. **Open a terminal**, start with Zone 1
2. After each zone, tell me the results
3. I will update the score in real time (with `file:line` source watermark)

Say "ready" and I will begin from item 1.
