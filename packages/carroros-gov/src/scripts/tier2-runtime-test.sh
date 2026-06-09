#!/usr/bin/env bash
# tier2-runtime-test.sh — 配对机制协同验证
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 用法: bash .claude/scripts/tier2-runtime-test.sh
set -uo pipefail
PASS=0; FAIL=0; WARN=0; TOTAL=0

H=".claude/hooks"
S=".claude/scripts"

_test() {
    TOTAL=$((TOTAL+1))
    local name="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -qE "$expected"; then
        echo "  🟢 PASS: $name"
        PASS=$((PASS+1))
    else
        echo "  🔴 FAIL: $name"
        echo "     expected: $expected"
        echo "     actual:   $(echo "$actual" | head -c 150)"
        FAIL=$((FAIL+1))
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
# Helper: grep with echo true (fixes grep -c returning count instead of "true")
_grep_true() {
    local file="$1" pattern="$2"
    grep -q "$pattern" "$file" 2>/dev/null && echo true || echo ""
}

echo "╔══════════════════════════════════════════╗"
echo "║  Tier 2: 配对机制协同验证 (8对)          ║"
echo "╚══════════════════════════════════════════╝"

# [19] completion-gate + posttool-completion-audit — 双层证据门禁
echo ""; echo "=== [19] completion-gate + posttool-completion-audit ==="
_test "completion-gate exists" "true" "$(_hook_exists completion-gate)"
_test "posttool-completion-audit exists" "true" "$(_hook_exists posttool-completion-audit)"
_test "both registed in settings.json" "true" "$(
  c1=$(grep -c 'completion-gate' .claude/settings.json 2>/dev/null || echo 0)
  c2=$(grep -c 'posttool-completion-audit' .claude/settings.json 2>/dev/null || echo 0)
  [ "$c1" -gt 0 ] && [ "$c2" -gt 0 ] && echo true
)"

# [20] permission-gate + privacy-gate — 双层拦截
echo ""; echo "=== [20] permission-gate + privacy-gate ==="
_test "permission-gate exists" "true" "$(_hook_exists permission-gate)"
_test "privacy-gate exists" "true" "$(_hook_exists privacy-gate)"
_test "both enabled in harness" "true" "$(
  p1=$(grep -c 'permission_gate: true' .claude/harness.yaml 2>/dev/null || echo 0)
  p2=$(grep -c 'privacy_gate: true' .claude/harness.yaml 2>/dev/null || echo 0)
  [ "$p1" -gt 0 ] && [ "$p2" -gt 0 ] && echo true
)"

# [21] pretool-edit-scope + intent-tracker — scope 编辑 → tracker 记录
echo ""; echo "=== [21] pretool-edit-scope + intent-tracker ==="
_test "scope hook exists" "true" "$(_hook_exists pretool-edit-scope)"
_test "intent-tracker exists" "true" "$(_hook_exists intent-tracker)"
_check_data "scope log exists & non-empty" "$(
  if [ -f .omc/state/current-scope.txt ]; then
    [ $(wc -l < .omc/state/current-scope.txt 2>/dev/null || echo 0) -gt 0 ] && echo true || echo ""
  else echo ""; fi
)"
_check_data "edit-churn log exists" "$([ -f .omc/state/edit-churn-log.jsonl ] && echo true)"

# [22] error-dna + retry-budget — 错误检测 → 重试追踪
echo ""; echo "=== [22] error-dna + retry-budget ==="
_test "error-dna exists" "true" "$(_hook_exists error-dna)"
_test "pretool-retry-check exists" "true" "$(_hook_exists pretool-retry-check)"
R22_1=$(wc -l < .omc/state/error-signals.jsonl 2>/dev/null || echo 0)
if [ "$R22_1" -gt 0 ] 2>/dev/null; then
  _test "error-signals pipeline active (>0 records)" "[1-9]" "$R22_1"
else
  _warn "error-signals.jsonl — no data (CI/empty session)"
fi
R22_2=$(${PYTHON_BIN:-python3} -c "
import json
try:
  d=json.load(open('.omc/state/retry-budget.json'))
  sigs=len(d.get('signatures',{}))
  total=sum(v.get('retry_count',0) for v in d.get('signatures',{}).values())
  print(f'sigs={sigs} retries={total}')
except: print('no_data')
" 2>/dev/null || echo "no_data")
if echo "$R22_2" | grep -qE "sigs=[1-9]"; then
  _test "retry-budget has tracked retries" "sigs=[1-9]" "$R22_2"
else
  _warn "retry-budget.json — no retry data (CI/empty session)"
fi

# [23] --- test 23 based on the structure shown in earlier read_file ---
# [24] lsp-suggest + pre-edit-lsp — 提前检测 → 安全编辑
echo ""; echo "=== [24] lsp-suggest + pre-edit-lsp ==="
_test "lsp-suggest exists" "true" "$(_hook_exists lsp-suggest)"
_test "pre-edit-lsp exists" "true" "$(_hook_exists pre-edit-lsp-check)"
_test "pre-edit-lsp echo true passthrough" "true" "$(
  if [ -f "$H/pre-edit-lsp-check.py" ]; then
    echo '{}' | python3 "$H/pre-edit-lsp-check.py" 2>/dev/null | grep -q 'continue' && echo true
  else echo ""; fi
)"
_test "pre-edit-lsp tolerance" "true" "$(_hook_grep pre-edit-lsp-check 'soft_fail\|return True\|exit 0' | grep -q '[1-9]' && echo true)"

# [25] Oracle + Meta-Oracle — 静态审查 + 运行时裁决
echo ""; echo "=== [25] Oracle + Meta-Oracle ==="
_test "oracle-gate exists" "true" "$([ -f "$H/oracle-gate.py" ] && echo true)"
_check_data "oracle-verdicts.md exists" "$([ -f .omc/state/oracle-verdicts.md ] && echo true)"
_test "meta-oracle-trigger exists" "true" "$(_hook_exists meta-oracle-trigger)"
_test "meta-oracle-review exists" "true" "$(
  if [ -f "$S/meta-oracle-review.py" ]; then echo "true"
  elif [ -f "$S/meta-oracle-review.sh" ]; then echo "true"
  else echo ""; fi
)"
_check_data "oracle-verdicts.md exists (2)" "$([ -f .omc/state/oracle-verdicts.md ] && echo true)"
_check_data "meta-oracle-verdicts.md exists" "$([ -f .omc/state/meta-oracle-verdicts.md ] && echo true)"

# [26] blast-radius + permission-gate — 硬阻断 + 危险命令
echo ""; echo "=== [26] blast-radius + permission-gate ==="
_test "blast-radius blocks checkout ." "true" "$(
  if [ -f "$H/pretool-blast-radius.py" ]; then
    echo '{"tool_name":"Bash","tool_input":{"command":"git checkout ."}}' | \
      python3 "$H/pretool-blast-radius.py" 2>/dev/null
    [ $? -eq 2 ] && echo true || echo ""
  else echo ""; fi
)"
_test "permission-gate catches safe command" "true" "$(
  if [ -f "$H/permission-gate.py" ]; then
    echo '{"tool_name":"Bash","tool_input":{"command":"echo test"}}' | \
      python3 "$H/permission-gate.py" 2>/dev/null | \
      grep -q 'continue' && echo true
  else echo ""; fi
)"

# [27] package-release DG-100 — 三源预检门禁
echo ""; echo "=== [27] package-release DG-100 门禁 ==="
_test "DG-100 gate in package-release" "true" "$(grep -q 'DG-100' scripts/package-release.sh 2>/dev/null && echo true)"
_test "package-release bash syntax OK" "true" "$(bash -n scripts/package-release.sh 2>/dev/null && echo true)"
_test "source mirror clean" "true" "$(
  if [ -f "$S/audit-hooks.sh" ]; then
    # Run non-existent mirror check — we expect drift for new test scripts
    bash "$S/audit-hooks.sh" --check-source-mirror 2>&1 | grep -q '🔴' && echo "" || echo true
  elif [ -f "$S/audit-hooks.py" ]; then
    python3 "$S/audit-hooks.py" --check-source-mirror 2>&1 | grep -q '🔴' && echo "" || echo true
  else echo ""; fi
)"

echo ""
echo "══════════════════════════════════════════════"
echo "  Tier 2: $PASS/$TOTAL passed, $FAIL failed, $WARN warn"
echo "══════════════════════════════════════════════"
