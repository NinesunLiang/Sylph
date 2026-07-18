#!/usr/bin/env bash
# test-hook-launcher.sh — H3 验收：关键 hook 缺失 fail-closed，非关键 fail-open，存在则透传
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHER="$PROJECT_ROOT/.claude/hooks/hook-launcher.sh"
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1"; }

[ -f "$LAUNCHER" ] || fail "launcher not found: $LAUNCHER"

# --- Case 1: 非关键 hook 缺失 → exit 0（fail-open 维持）---
set +e
out="$(bash "$LAUNCHER" "definitely-not-exist-hook.py" 2>/dev/null)"
code=$?
set -e
[ "$code" -eq 0 ] || fail "case1 非关键缺失应 exit 0，实际 $code"
echo "$out" | grep -q "hook not found" || fail "case1 输出应含 hook not found"
pass "case1 非关键 hook 缺失 → exit 0 fail-open"

# --- Case 2: 关键 hook 缺失 → exit 2（fail-closed）---
# 用假名冒充关键 hook 不可行（名单精确匹配），故临时移走真实关键 hook 再还原。
CRITICAL="pretool-gate.py"
BAK="$HOOKS_DIR/.$CRITICAL.test-bak"
[ -f "$HOOKS_DIR/$CRITICAL" ] || fail "前置条件：$CRITICAL 应存在"
mv "$HOOKS_DIR/$CRITICAL" "$BAK"
restore() { mv "$BAK" "$HOOKS_DIR/$CRITICAL"; }
trap restore EXIT

set +e
out="$(bash "$LAUNCHER" "$CRITICAL" 2>/dev/null)"
code=$?
set -e
[ "$code" -eq 2 ] || fail "case2 关键缺失应 exit 2，实际 $code"
echo "$out" | grep -q "CRITICAL hook missing" || fail "case2 输出应含 CRITICAL hook missing"
pass "case2 关键 hook 缺失（${CRITICAL}）→ exit 2 fail-closed"

restore
trap - EXIT

# --- Case 3: 关键 hook 存在 → 透传执行（非缺失分支）---
# carroros-night-deny.py 无 stdin payload 时会自行退出；此处只验证 launcher
# 不走 missing 分支（输出不含 hook not found / CRITICAL missing）。
set +e
out="$(echo '{}' | bash "$LAUNCHER" "$CRITICAL" 2>&1)"
code=$?
set -e
echo "$out" | grep -q "CRITICAL hook missing" && fail "case3 关键 hook 存在却走缺失分支"
echo "$out" | grep -q "hook not found" && fail "case3 关键 hook 存在却报 not found"
pass "case3 关键 hook 存在 → 透传（exit=${code}，由 hook 自身决定）"

echo "ALL PASS"
exit 0
