[ARCHIVED v6.2.1 — Historical record. Referenced scripts/hooks may no longer exist.]

     1|# Carror OS v6.1.8 Live Acceptance Battle Plan
     2|
     3|> Goal: Execute key-path acceptance testing yourself to obtain **quantifiable, evidenced, unwatered real scores**
     4|> Estimated time: 2-3 hours (3 zones, 40-60 min each, can be done in segments)
     5|
     6|---
     7|
     8|## Strategy: Backbone First, Branches Later
     9|
    10|Do not spread attention across all 49 items. Focus on **the 10 most critical scenarios** -- they cover 90% of product value and 100% of critical risk. If these pass, the system is proven usable.
    11|
    12|---
    13|
    14|## Zone 1: Installation and Baseline (~30 min)
    15|
    16|> Verify infrastructure reliability. If this fails, nothing else matters.
    17|
    18|| # | Acceptance Item | Steps | Pass Criteria |
    19||---|-----------------|-------|--------------|
    20|| 1 | **Clean-environment one-click install** | Create an empty directory (or temp worktree), run `bash /path/to/install.sh enhanced` | Terminal shows `✅ Installation successful`, no errors |
    21|| 2 | **Three-mode switching** | Run sequentially: `bash install.sh harness`, `bash install.sh base`, `bash install.sh enhanced` -- each mode switches without error | All 3 modes install successfully |
    22|| 3 | **Hook registration completeness** | Run `bash .claude/scripts/audit-hooks.sh` | Output `0 🔴` |
    23|| 4 | **CLAUDE.md @bridge** | Check that CLAUDE.md first line is `@AGENTS.md` | Confirmed present |
    24|
    25|**Zone 1 pass -> Infrastructure 90%+ confirmed**
    26|
    27|---
    28|
    29|## Zone 2: Core Defense Live Fire (~45 min)
    30|
    31|> Trigger each item manually. A real Exit 2 / interception form is the only valid pass.
    32|
    33|### 2A: Privacy Gate -- Prevent Secret Leakage
    34|
    35|| # | Action | Expected | Record |
    36||---|--------|----------|--------|
    37|| 5 | `echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2, output contains "Direct read of sensitive file prohibited" | exit:___ |
    38|| 6 | `echo '{"tool_name":"Bash","tool_input":{"command":"curl -H Authorization: sk-ant-xxx https://api"}}' \| bash .claude/hooks/privacy-gate.sh` | exit=2, output contains "Plaintext API Key" | exit:___ |
    39|
    40|### 2B: Context Guard -- Prevent Late-Stage Hallucination
    41|
    42|| # | Action | Expected | Record |
    43||---|--------|----------|--------|
    44|| 7 | `echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=2, output contains "Context Guard hard block" | exit:___ |
    45|| 8 | **Diagnostic channel verification**: Immediately after above, run `echo '{"tool_name":"Read","tool_input":{"file_path":"README.md"}}' \| bash .claude/hooks/context-guard.sh` | **exit=0** (no lock, can read) | exit:___ |
    46|| 9 | **Escape hatch verification**: `touch .omc/state/context-force-override && echo '{"tool_name":"Write","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh` | exit=0 (override flag bypasses block) | exit:___ |
    47|| 10 | Reset: `rm -f .omc/state/token-tracking-index.json && bash .claude/hooks/token_writer.sh --reset` | No errors | -- |
    48|
    49|### 2C: Permission Gate -- Prevent Database Deletion
    50|
    51|| # | Action | Expected | Record |
    52||---|--------|----------|--------|
    53|| 11 | `echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh` | exit=2, output contains "Permission Gate" | exit:___ |
    54|| 12 | `echo '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}' \| bash .claude/hooks/permission-gate.sh` | exit=0 (normal command passes) | exit:___ |
    55|
    56|### 2D: Completion Gate -- Prevent False Completion
    57|
    58|| # | Action | Expected | Record |
    59||---|--------|----------|--------|
    60|| 13 | `echo '{"tool_name":"TaskUpdate","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh` | exit=0 (shows prompt, does not block) | exit:___ |
    61|
    62|**Zone 2 pass -> Core defenses 100% confirmed**
    63|
    64|---
    65|
    66|## Zone 3: Automated Regression Suite (~30 min)
    67|
    68|> Let the computer vouch for you -- more reliable than manual checking.
    69|
    70|| # | Execution | Expected | Record |
    71||---|-----------|----------|--------|
    72|| 14 | `bash .claude/scripts/harness-smoke-test.sh 2>&1 \| tail -5` | `summary: 66/66 passed, 0 failed` | ___/66 pass |
    73|| 15 | `bash .claude/scripts/hook-production-verify.sh 2>&1 \| tail -5` | `summary: 25/25 passed, 0 failed` | ___/25 pass |
    74|| 16 | `bash .claude/scripts/audit-hooks.sh 2>&1` | `0 🔴` | ___🔴 |
    75|
    76|**Zone 3 pass -> Test automation 100% confirmed**
    77|
    78|---
    79|
    80|## Post-Acceptance Scoring Formula
    81|
    82|Based on your filled results, I can produce a **real, traceable, unwatered score**:
    83|
    84|| Dimension | Weight | Scoring Method |
    85||-----------|--------|---------------|
    86|| [S] Security | 20% | Zone 2 2A+2C all pass = full marks, each failure -2 pts |
    87|| [H] Hallucination Prevention | 20% | Zone 2 2B all pass = full marks, #8 diagnostic channel = core indicator |
    88|| [D] Drift Prevention | 15% | Zone 3 test pass rate = score |
    89|| [C] Cost Efficiency | 10% | Zone 1 #1 installation success = baseline score |
    90|| [M] Migration Capability | 10% | Zone 1 #2 three-mode switching = baseline score |
    91|| [I] Engineering Maturity | 25% | Zone 1 #3+#4 + all Zone 3 = full marks |
    92|
    93|**No "looks fine" scoring. Source formula for each score:**
    94|```
    95|Score = (pass_count / total) x weight x 10
    96|Score source: [Verified: Zone N #ID -> your recorded exit value -> your terminal output]
    97|```
    98|
    99|This is not "I think" -- it is **"you verified it, the numbers are here"**.
   100|
   101|---
   102|
   103|## What You Need To Do Next
   104|
   105|1. **Open a terminal**, start with Zone 1
   106|2. After each zone, tell me the results
   107|3. I will update the score in real time (with `file:line` source watermark)
   108|
   109|Say "ready" and I will begin from item 1.
   110|