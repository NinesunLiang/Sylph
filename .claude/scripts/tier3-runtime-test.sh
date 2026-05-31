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

H=".claude/hooks"; S=".claude/scripts"

echo "╔══════════════════════════════════════════╗"
echo "║  Tier 3: 链式多机制管道验证 (5链)        ║"
echo "╚══════════════════════════════════════════╝"

# ─── Chain 1: 编辑管道 ───
echo ""; echo "=== [28] 编辑管道: guard→scope→lsp→tracker→completion ==="
_test "edit-guard exists" "true" "$([ -f $H/edit-guard.sh ] && echo true)"
_test "pretool-edit-scope exists" "true" "$([ -f $H/pretool-edit-scope.sh ] && echo true)"
_test "pre-edit-lsp-check exists" "true" "$([ -f $H/pre-edit-lsp-check.sh ] && echo true)"
_test "intent-tracker exists" "true" "$([ -f $H/intent-tracker.sh ] && echo true)"
_test "completion-gate exists" "true" "$([ -f $H/completion-gate.sh ] && echo true)"

# Chain verification: simulate a full edit pipeline
R28_1=$(echo '{"tool_input":{"file_path":"test.py"}}' | bash $H/edit-guard.sh 2>&1 | grep -c 'continue' || echo 0)
_test "edit-guard responds" "[1-9]" "$R28_1"

R28_2=$(echo '{"tool_input":{"file_path":"test.py"}}' | bash $H/pre-edit-lsp-check.sh 2>&1 | grep -c 'continue' || echo 0)
_test "pre-edit-lsp chain responds" "[1-9]" "$R28_2"

# Verify pipeline state exists
_test "edit-log has entries" "true" "$([ -f .omc/state/session-edit-log.txt ] && echo true || echo false)"
_test "edit-churn-log has records" "true" "$([ -f .omc/state/edit-churn-log.jsonl ] && echo true || echo false)"

# ─── Chain 2: 错误管道 ───
echo ""; echo "=== [29] 错误管道: error-dna→retry-budget→retry-check ==="
_test "error-dna exists" "true" "$([ -f $H/error-dna.sh ] && echo true)"
_test "pretool-retry-check exists" "true" "$([ -f $H/pretool-retry-check.sh ] && echo true)"
_test "retry-budget.json exists" "true" "$([ -f .omc/state/retry-budget.json ] && echo true)"

# Check runtime pipeline data
R29_1=$(wc -l < .omc/state/error-signals.jsonl 2>/dev/null || echo 0)
_test "error-signals pipeline active (>0 records)" "[1-9]" "$R29_1"

R29_2=$(${PYTHON_BIN:-python3} -c "
import json
d=json.load(open('.omc/state/retry-budget.json'))
sigs=len(d.get('signatures',{}))
total=sum(v.get('retry_count',0) for v in d.get('signatures',{}).values())
print(f'sigs={sigs} retries={total}')
" 2>/dev/null || echo "error")
_test "retry-budget has tracked retries" "sigs=[1-9]" "$R29_2"

# ─── Chain 3: 打包管道 ───
echo ""; echo "=== [30] 打包管道: precheck→audit→package→postcheck ==="
_test "package-release.sh exists" "true" "$([ -f scripts/package-release.sh ] && echo true)"
_test "DG-100 precheck gate present" "true" "$(grep -c 'DG-100\|三源安全门禁' scripts/package-release.sh 2>/dev/null)"
_test "Step 5 post-check present" "true" "$(grep -c 'Step 5.*同步后' scripts/package-release.sh 2>/dev/null)"
_test "audit-hooks available" "true" "$([ -f $S/audit-hooks.sh ] && echo true)"

# Syntax check
R30=$(bash -n scripts/package-release.sh 2>&1 && echo true || echo false)
_test "package-release syntax OK" "true" "$R30"

# ─── Chain 4: 审查管道 ───
echo ""; echo "=== [31] 审查管道: AI→Oracle→Meta-Oracle ==="
_test "Oracle agent spawn capability" "true" "$([ -f $H/meta-oracle-trigger.sh ] && echo true)"
_test "Meta-Oracle G1-G4 trigger" "true" "$(grep -c 'G[1-4]' $H/meta-oracle-trigger.sh 2>/dev/null)"
_test "meta-oracle-review script" "true" "$([ -f $S/meta-oracle-review.sh ] && echo true)"
_test "oracle verdicts tracked" "true" "$([ -f .omc/state/oracle-verdicts.md ] && echo true)"
_test "meta-oracle verdicts tracked" "true" "$([ -f .omc/state/meta-oracle-verdicts.md ] && echo true)"

# Check verdict history
R31=$(wc -l < .omc/state/meta-oracle-verdicts.md 2>/dev/null || echo 0)
_test "meta-oracle verdicts have history (>0 lines)" "[1-9]" "$R31"

# ─── Chain 5: 会话管道 ───
echo ""; echo "=== [32] 会话管道: compressor→knowledge→probe ==="
_test "context-compressor exists" "true" "$([ -f $H/context-compressor.sh ] && echo true)"
_test "inject-project-knowledge exists" "true" "$([ -f $H/inject-project-knowledge.sh ] && echo true)"
_test "ecosystem-probe exists" "true" "$([ -f $H/ecosystem-probe.sh ] && echo true)"

# Session pipeline evidence
_test "context-cache.md generated" "true" "$([ -s .omc/state/context-cache.md ] && echo true)"
_test "session-handoff.md exists" "true" "$([ -f .omc/state/session-handoff.md ] && echo true)"

# Compact cache freshness
R32=$(head -1 .omc/state/context-cache.md 2>/dev/null)
_test "context-cache has timestamp" "CONTEXT-COMPRESSOR|2026" "$R32"

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
