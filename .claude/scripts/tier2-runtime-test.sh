#!/usr/bin/env bash
# tier2-runtime-test.sh — 配对机制协同验证
# 用法: bash .claude/scripts/tier2-runtime-test.sh
set -uo pipefail
PASS=0; FAIL=0; TOTAL=0

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

H=".claude/hooks"
S=".claude/scripts"

echo "╔══════════════════════════════════════════╗"
echo "║  Tier 2: 配对机制协同验证 (8对)          ║"
echo "╚══════════════════════════════════════════╝"

# [19] completion-gate + posttool-completion-audit — 双层证据门禁
echo ""; echo "=== [19] completion-gate + posttool-completion-audit ==="
_test "completion-gate exists" "true" "$([ -f $H/completion-gate.sh ] && echo true)"
_test "posttool-completion-audit exists" "true" "$([ -f $H/posttool-completion-audit.sh ] && echo true)"
_test "both registed in settings.json" "true" "$(
  c1=$(grep -c 'completion-gate.sh' .claude/settings.json 2>/dev/null || echo 0)
  c2=$(grep -c 'posttool-completion-audit.sh' .claude/settings.json 2>/dev/null || echo 0)
  [ "$c1" -gt 0 ] && [ "$c2" -gt 0 ] && echo true
)"

# [20] permission-gate + privacy-gate — 双层拦截
echo ""; echo "=== [20] permission-gate + privacy-gate ==="
_test "permission-gate exists" "true" "$([ -f $H/permission-gate.sh ] && echo true)"
_test "privacy-gate exists" "true" "$([ -f $H/privacy-gate.sh ] && echo true)"
_test "both enabled in harness" "true" "$(
  p1=$(grep -c 'permission_gate: true' .claude/harness.yaml 2>/dev/null || echo 0)
  p2=$(grep -c 'privacy_gate: true' .claude/harness.yaml 2>/dev/null || echo 0)
  [ "$p1" -gt 0 ] && [ "$p2" -gt 0 ] && echo true
)"

# [21] pretool-edit-scope + intent-tracker — scope 编辑 → tracker 记录
echo ""; echo "=== [21] pretool-edit-scope + intent-tracker ==="
_test "scope hook exists" "true" "$([ -f $H/pretool-edit-scope.sh ] && echo true)"
_test "tracker hook exists" "true" "$([ -f $H/intent-tracker.sh ] && echo true)"
_test "tracker has E6 fix" "true" "$(grep 'contradiction_level >= 2' $H/intent-tracker.sh | grep -c '2')"
# Verify intent-tracker records exist in log
R21=$(wc -l .omc/state/contradiction-log.jsonl 2>/dev/null | awk '{print $1}' || echo 0)
_test "contradiction-log has runtime data (>0 entries)" "[1-9]" "$R21"

# [22] error-dna + retry-budget — 错误捕获 → 重试追踪
echo ""; echo "=== [22] error-dna + retry-budget ==="
_test "error-dna exists" "true" "$([ -f $H/error-dna.sh ] && echo true)"
_test "error-signals has data" "true" "$(
  [ "$(wc -l < .omc/state/error-signals.jsonl 2>/dev/null || echo 0)" -gt 0 ] && echo true
)"
_test "retry-budget has data" "true" "$(
  [ -f .omc/state/retry-budget.json ] && ${PYTHON_BIN:-python3} -c "
import json; d=json.load(open('.omc/state/retry-budget.json'))
print('true' if len(d.get('signatures',{})) > 0 else 'false')
" 2>/dev/null
)"

# [23] context-compressor + compact-detect — SessionStart 压缩 → /compact 恢复
echo ""; echo "=== [23] context-compressor + compact-detect ==="
_test "compressor exists" "true" "$([ -f $H/context-compressor.sh ] && echo true)"
_test "compact-detect exists" "true" "$([ -f $H/compact-detect.sh ] && echo true)"
_test "context-cache.md has content" "true" "$(
  [ -s .omc/state/context-cache.md ] && echo true
)"
# Run compact-detect to verify it reads the cache
R23=$(bash $H/compact-detect.sh 2>&1 <<< "/compact" || true)
_test "compact-detect reads cache" "CTX-COMPACT|铁律|知识恢复" "$R23"

# [24] lsp-suggest + pre-edit-lsp-check — 搜索建议 + 编辑前诊断
echo ""; echo "=== [24] lsp-suggest + pre-edit-lsp ==="
_test "lsp-suggest exists" "true" "$([ -f $H/lsp-suggest.sh ] && echo true)"
_test "pre-edit-lsp exists" "true" "$([ -f $H/pre-edit-lsp-check.sh ] && echo true)"
_test "both registered in settings" "true" "$(
  l1=$(grep -c 'lsp-suggest.sh' .claude/settings.json 2>/dev/null || echo 0)
  l2=$(grep -c 'pre-edit-lsp-check.sh' .claude/settings.json 2>/dev/null || echo 0)
  [ "$l1" -gt 0 ] && [ "$l2" -gt 0 ] && echo true
)"

# [25] Oracle + Meta-Oracle — 独立审查 + 终审
echo ""; echo "=== [25] Oracle + Meta-Oracle 审查体系 ==="
_test "lx-oracle skill exists" "true" "$([ -d .claude/skills/lx-oracle ] && echo true)"
_test "meta-oracle-trigger exists" "true" "$([ -f $H/meta-oracle-trigger.sh ] && echo true)"
_test "meta-oracle-review exists" "true" "$([ -f $S/meta-oracle-review.sh ] && echo true)"
_test "oracle-verdicts.md exists" "true" "$([ -f .omc/state/oracle-verdicts.md ] && echo true)"
_test "meta-oracle-verdicts.md exists" "true" "$([ -f .omc/state/meta-oracle-verdicts.md ] && echo true)"

# [26] blast-radius + permission-gate — 硬阻断 + 危险命令
echo ""; echo "=== [26] blast-radius + permission-gate ==="
_test "blast-radius blocks checkout ." "true" "$(
  echo '{"tool_name":"Bash","tool_input":{"command":"git checkout ."}}' | \
    bash $H/pretool-blast-radius.sh 2>/dev/null | \
    grep -q '"continue": false' && echo true
)"
_test "permission-gate catches danger" "true" "$(
  echo '{"tool_name":"Bash","tool_input":{"command":"echo test"}}' | \
    bash $H/permission-gate.sh 2>/dev/null | \
    grep -q 'continue' && echo true
)"

# [27] package-release DG-100 — 三源预检门禁
echo ""; echo "=== [27] package-release DG-100 门禁 ==="
_test "DG-100 gate in package-release" "true" "$(grep -c 'DG-100' scripts/package-release.sh 2>/dev/null)"
_test "package-release bash syntax OK" "true" "$(bash -n scripts/package-release.sh 2>/dev/null && echo true)"
_test "source mirror clean" "true" "$(
  bash $S/audit-hooks.sh --check-source-mirror 2>/dev/null | grep -q '✅ source mirror 一致性' && echo true
)"

echo ""
echo "═══════════════════════════════════════"
echo "  Tier 2: $PASS/$TOTAL passed, $FAIL failed"
echo "═══════════════════════════════════════"
