#!/usr/bin/env bash
# tier3-runtime-test.sh — 链式机制管道验证 (5链)
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 用法: bash .claude/scripts/tier3-runtime-test.sh
set -uo pipefail
PASS=0; FAIL=0; WARN=0; TOTAL=0

_test() {
    TOTAL=$((TOTAL+1))
    local name="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -qE "$expected"; then
        echo "  🟢 PASS: $name"; PASS=$((PASS+1))
    else
        echo "  🔴 FAIL: $name — expected '$expected'"; FAIL=$((FAIL+1))
        echo "     actual: $(echo "$actual" | head -c 120)"
    fi
}
_warn() { TOTAL=$((TOTAL+1)); WARN=$((WARN+1)); echo "  ⚠️  WARN: $1"; }
# _check_data: if condition is truthy → PASS, else → WARN (CI/empty session tolerant)
_check_data() {
    local name="$1" cond="$2"
    if [ "$cond" = "true" ]; then
        echo "  🟢 PASS: $name"; PASS=$((PASS+1)); TOTAL=$((TOTAL+1))
    else
        _warn "$name — data not available (CI/empty session)"
    fi
}

H=".claude/hooks"; S=".claude/scripts"

# Helper: check file exists (.py only)
_hook_exists() {
    local base="$1"
    if [ -f "$H/${base}.py" ]; then echo "true"
    else echo ""; fi
}
# Helper: run a hook (.py only)
_hook_run() {
    local base="$1"
    if [ -f "$H/${base}.py" ]; then python3 "$H/${base}.py"
    else echo "ERROR: $H/${base}.py not found"; exit 1; fi
}
# Helper: check pattern in hook file (.py only)
_hook_grep() {
    local base="$1" pattern="$2"
    if [ -f "$H/${base}.py" ]; then grep -c "$pattern" "$H/${base}.py" 2>/dev/null || echo 0
    else echo 0; fi
}

echo "╔══════════════════════════════════════════╗"
echo "║  Tier 3: 链式多机制管道验证 (5链)        ║"
echo "╚══════════════════════════════════════════╝"

# ─── Chain 1: 编辑管道 ───
echo ""; echo "=== [28] 编辑管道: guard→scope→lsp→tracker→completion ==="
_test "edit-guard exists" "true" "$(_hook_exists edit-guard)"
_test "pretool-edit-scope exists" "true" "$(_hook_exists pretool-edit-scope)"
_test "pre-edit-lsp-check exists" "true" "$(_hook_exists pre-edit-lsp-check)"
_test "intent-tracker exists" "true" "$(_hook_exists intent-tracker)"
_test "completion-gate exists" "true" "$(_hook_exists completion-gate)"

# Chain verification: simulate a full edit pipeline
R28_1=$(_hook_run edit-guard 2>&1 <<< '{"tool_input":{"file_path":"test.py"}}' | grep -c 'continue' || echo 0)
_test "edit-guard responds" "[1-9]" "$R28_1"

R28_2=$(_hook_run pre-edit-lsp-check 2>&1 <<< '{"tool_input":{"file_path":"test.py"}}' | grep -c 'continue' || echo 0)
_test "pre-edit-lsp chain responds" "[1-9]" "$R28_2"

# Verify pipeline state exists
_check_data "edit-log has entries" "$([ -f .omc/state/session-edit-log.txt ] && echo true)"
_check_data "edit-churn-log has records" "$([ -f .omc/state/edit-churn-log.jsonl ] && echo true)"

# ─── Chain 2: 错误管道 ───
echo ""; echo "=== [29] 错误管道: error-dna→retry-budget→retry-check ==="
_test "error-dna exists" "true" "$(_hook_exists error-dna)"
_test "pretool-retry-check exists" "true" "$(_hook_exists pretool-retry-check)"
_check_data "retry-budget.json exists" "$([ -f .omc/state/retry-budget.json ] && echo true)"

# Check runtime pipeline data
R29_1=$(wc -l < .omc/state/error-signals.jsonl 2>/dev/null || echo 0)
if [ "$R29_1" -gt 0 ] 2>/dev/null; then
  _test "error-signals pipeline active (>0 records)" "[1-9]" "$R29_1"
else
  _warn "error-signals.jsonl — no data (CI/empty session)"
fi

R29_2=$(${PYTHON_BIN:-python3} -c "
import json
try:
  d=json.load(open('.omc/state/retry-budget.json'))
  sigs=len(d.get('signatures',{}))
  total=sum(v.get('retry_count',0) for v in d.get('signatures',{}).values())
  print(f'sigs={sigs} retries={total}')
except: print('no_data')
" 2>/dev/null || echo "no_data")
if echo "$R29_2" | grep -qE "sigs=[1-9]"; then
  _test "retry-budget has tracked retries" "sigs=[1-9]" "$R29_2"
else
  _warn "retry-budget.json — no retry data (CI/empty session)"
fi

# ─── Chain 3: 打包管道 ───
echo ""; echo "=== [30] 打包管道: precheck→audit→package→postcheck ==="
_test "package-release.sh exists" "true" "$([ -f scripts/package-release.sh ] && echo true)"
_test "DG-100 precheck gate present" "true" "$(grep -q 'DG-100' scripts/package-release.sh 2>/dev/null && echo true)"
_test "Step 5 post-check present" "true" "$(grep -q 'Step 5.*同步后' scripts/package-release.sh 2>/dev/null && echo true)"
_test "audit-hooks available" "true" "$(if [ -f "$S/audit-hooks.sh" ]; then echo true; elif [ -f "$S/audit-hooks.py" ]; then echo true; else echo ""; fi)"

# Syntax check
R30=$(bash -n scripts/package-release.sh 2>&1 && echo true || echo false)
_test "package-release syntax OK" "true" "$R30"

# ─── Chain 4: 审查管道 ───
echo ""; echo "=== [31] 审查管道: AI→Oracle→Meta-Oracle ==="
_test "Oracle agent spawn capability" "true" "$(_hook_exists meta-oracle-trigger)"
_test "Meta-Oracle G1-G4 trigger" "[1-9]" "$(_hook_grep meta-oracle-trigger 'G[1-4]')"
_test "meta-oracle-review script" "true" "$(if [ -f "$S/meta-oracle-review.sh" ]; then echo true; elif [ -f "$S/meta-oracle-review.py" ]; then echo true; else echo ""; fi)"
_test "oracle verdicts tracked" "true" "$([ -f .omc/state/oracle-verdict.md ] && echo true)"
_test "meta-oracle verdicts tracked" "true" "$([ -f .omc/state/meta-oracle-verdicts.md ] && echo true)"

# Check verdict history
R31=$(wc -l < .omc/state/meta-oracle-verdicts.md 2>/dev/null || echo 0)
_test "meta-oracle verdicts have history (>0 lines)" "[1-9]" "$R31"

# ─── Chain 5: 会话管道 ───
echo ""; echo "=== [32] 会话管道: compressor→knowledge→probe ==="
_test "context-compressor exists" "true" "$(_hook_exists context-compressor)"
_test "inject-project-knowledge exists" "true" "$(_hook_exists inject-project-knowledge)"
_test "ecosystem-probe exists" "true" "$(_hook_exists ecosystem-probe)"

# Session pipeline evidence
_check_data "context-cache.md generated" "$([ -s .omc/state/context-cache.md ] && echo true)"
_check_data "session-handoff.md exists" "$([ -f .omc/state/session-handoff.md ] && echo true)"

# Compact cache freshness
R32=$(head -1 .omc/state/context-cache.md 2>/dev/null)
if [ -n "$R32" ]; then
  _test "context-cache has timestamp" "Context Cache|Empty" "$R32"
else
  _warn "context-cache.md — no content (CI/empty session)"
fi

# ─── Issues Found ───
echo ""
echo "=== 发现的问题 ==="

# Issue 1: E6 contradiction 185 entries 0 true
R_ISSUE1=$(${PYTHON_BIN:-python3} -c "
import json; total=0; contra=0
try:
  with open('.omc/state/edit-churn-log.jsonl') as f:
    for l in f:
      if not l.strip(): continue
      total+=1
      if json.loads(l).get('contradiction'): contra+=1
  print(f'{total} entries, {contra} contradictions')
except: print('no data')
" 2>/dev/null)
echo "  📋 E6: $R_ISSUE1 — 编辑追踪活跃但矛盾检测零命中"
_warn "E6 contradiction detection may need threshold tuning"

# Issue 2: error-dna.jsonl permanently empty (E2 pipeline)
R_ISSUE2=$(wc -c < .omc/state/error-dna.jsonl 2>/dev/null || echo 0)
echo "  📋 error-dna.jsonl: $R_ISSUE2 bytes — E2 CAPTCHA管道永远为空"
_warn "error-dna.jsonl design: only E2 events, normal=empty"

# Issue 3: retry-budget sparse
R_ISSUE3=$(${PYTHON_BIN:-python3} -c "
import json; d=json.load(open('.omc/state/retry-budget.json'))
print(f'{len(d.get(\"signatures\",{}))} sigs')
" 2>/dev/null)
echo "  📋 retry-budget: $R_ISSUE3 — 重试追踪数据稀疏"
_warn "retry-budget reset frequently, losing historical patterns"

echo ""
echo "═══════════════════════════════════════"
echo "  Tier 3: $PASS/$TOTAL passed, $FAIL failed, $WARN warn"
echo "═══════════════════════════════════════"
