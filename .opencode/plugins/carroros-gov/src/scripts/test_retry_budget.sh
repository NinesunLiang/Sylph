#!/usr/bin/env bash
# test_retry_budget.sh — R39 预算单元测试
# 验证 retry-budget.sh 在边界条件下的行为：
#   - 0 次重试 (初始状态)
#   - 正数重试 (1, 2, 3 = MAX_RETRIES)
#   - 越界 (> MAX_RETRIES)
#   - 签名隔离
#   - 空/特殊签名 (防御性)
#   - clear 重置
#
# 用法: bash test_retry_budget.sh
# 不修改生产代码，使用真实项目路径（因为 retry-budget.sh 硬编码了 PROJECT_ROOT）

set -u
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RETRY_SCRIPT="$PROJECT_ROOT/.claude/scripts/retry-budget.sh"

# Save actual budget file and restore after test
ACTUAL_BUDGET="$PROJECT_ROOT/.omc/state/retry-budget.json"
BACKUP_BUDGET="/tmp/test_retry_budget_backup_$$.json"

if [ -f "$ACTUAL_BUDGET" ]; then
    cp "$ACTUAL_BUDGET" "$BACKUP_BUDGET"
fi

cleanup() {
    if [ -f "$BACKUP_BUDGET" ]; then
        mv "$BACKUP_BUDGET" "$ACTUAL_BUDGET" 2>/dev/null
    elif [ -f "$ACTUAL_BUDGET" ]; then
        rm -f "$ACTUAL_BUDGET"
    fi
    rm -f /tmp/test_retry_budget_*.json
}
trap cleanup EXIT

# Start fresh test budget
rm -f "$ACTUAL_BUDGET"
mkdir -p "$PROJECT_ROOT/.omc/state"

assert() {
    local desc="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo -e "  ${GREEN}✅ PASS${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} $desc"
        echo "     expected: $expected"
        echo "     actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local desc="$1"
    local expected_substring="$2"
    local actual="$3"
    if echo "$actual" | grep -qF "$expected_substring"; then
        echo -e "  ${GREEN}✅ PASS${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} $desc"
        echo "     expected substring: $expected_substring"
        echo "     actual: $actual"
        FAIL=$((FAIL + 1))
    fi
}

assert_exit_code() {
    local desc="$1"
    local expected_code="$2"
    local actual_code="$3"
    local output="$4"
    if [ "$actual_code" -eq "$expected_code" ]; then
        echo -e "  ${GREEN}✅ PASS${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} $desc (exit: $actual_code, expected: $expected_code)"
        echo "     output: $output"
        FAIL=$((FAIL + 1))
    fi
}

get_count() {
    local sig="$1"
    python3 -c "import json; d=json.load(open('$ACTUAL_BUDGET')); print(d['signatures'].get('$sig', {}).get('retry_count', 0))" 2>/dev/null || echo "0"
}

echo "=== R39 预算单元测试 ==="
echo "测试脚本: $RETRY_SCRIPT"
echo "预算文件: $ACTUAL_BUDGET"
echo ""

# ── Test 1: 初始状态 ──
echo "【1/9】初始状态 — 无重试记录"
rm -f "$ACTUAL_BUDGET"
output=$(bash "$RETRY_SCRIPT" status 2>&1)
assert_contains "status 输出含 'no retry data'" "(no retry data)" "$output"
bash "$RETRY_SCRIPT" check >/dev/null 2>&1; ec=$?
assert_exit_code "check 无文件返回 0" 0 $ec ""
echo ""

# ── Test 2: 第1次 record ──
echo "【2/9】正数重试 — 第1次"
output=$(bash "$RETRY_SCRIPT" record "test_sig_1" "test error 1" 2>&1)
assert_contains "record 输出含 retry 1/3" "retry 1/3" "$output"
[ -f "$ACTUAL_BUDGET" ] && echo -e "  ${GREEN}✅ PASS${NC} budget file created" && PASS=$((PASS+1)) || { echo -e "  ${RED}❌ FAIL${NC} budget file not created"; FAIL=$((FAIL+1)); }
assert "retry_count == 1" "1" "$(get_count "test_sig_1")"
echo ""

# ── Test 3: 第2次 → 未超限 ──
echo "【3/9】正数重试 — 第2次 (未超限)"
output=$(bash "$RETRY_SCRIPT" record "test_sig_1" "test error 1" 2>&1)
assert_contains "record 输出含 retry 2/3" "retry 2/3" "$output"
bash "$RETRY_SCRIPT" check >/dev/null 2>&1; ec=$?
assert_exit_code "check 未超限返回 0" 0 $ec ""
echo ""

# ── Test 4: 第3次 → 达到上限 ──
echo "【4/9】正数重试 — 第3次 (达到上限)"
output=$(bash "$RETRY_SCRIPT" record "test_sig_1" "test error 1" 2>&1)
assert_contains "record 输出含 BLOCKED" "BLOCKED" "$output"
output=$(bash "$RETRY_SCRIPT" check 2>&1); ec=$?
assert_exit_code "check 超限返回 2" 2 $ec "$output"
assert_contains "check 输出含 BLOCKED" "BLOCKED" "$output"
echo ""

# ── Test 5: 第4次 → 越界 ──
echo "【5/9】越界重试 — 第4次 (> MAX_RETRIES=3)"
output=$(bash "$RETRY_SCRIPT" record "test_sig_1" "test error 1" 2>&1)
assert_contains "record 第4次仍输出 BLOCKED" "BLOCKED" "$output"
assert "retry_count == 4 (仍在累加)" "4" "$(get_count "test_sig_1")"
echo ""

# ── Test 6: 签名隔离 ──
echo "【6/9】签名隔离 — 不同签名互不影响"
bash "$RETRY_SCRIPT" record "test_sig_2" "another error" >/dev/null 2>&1
bash "$RETRY_SCRIPT" record "test_sig_2" "another error" >/dev/null 2>&1
output=$(bash "$RETRY_SCRIPT" status 2>&1)
assert_contains "status 显示 sig_1 为 BLOCKED" "BLOCKED" "$output"
assert_contains "status 显示 sig_2 为 ok" "ok" "$output"
assert "sig_2 retry_count == 2" "2" "$(get_count "test_sig_2")"
echo ""

# ── Test 7: 空签名 ──
echo "【7/9】边界输入 — 空签名"
output=$(bash "$RETRY_SCRIPT" record "" "empty sig" 2>&1; ec=$?; echo "EXIT:$ec")
# Should not crash — check it completed
echo "$output" | grep -q "retry 1/3" && echo -e "  ${GREEN}✅ PASS${NC} 空签名可 record (无报错)" && PASS=$((PASS+1)) || { echo -e "  ${YELLOW}⚠️  INFO${NC} 空签名可能失败: $(echo "$output" | tail -1)"; }
echo ""

# ── Test 8: 特殊/长签名 ──
echo "【8/9】边界输入 — 特殊字符 + 长签名"
output=$(bash "$RETRY_SCRIPT" record "sig_special_!@#\$%" "special" 2>&1)
assert_contains "特殊字符签名可 record" "retry" "$output"
long_sig=$(python3 -c "print('a' * 500)")
output=$(bash "$RETRY_SCRIPT" record "$long_sig" "very long sig" 2>&1)
assert_contains "长签名(500字符)可 record" "retry" "$output"
echo ""

# ── Test 9: clear 重置 ──
echo "【9/9】clear 重置 — 清除后恢复正常"
bash "$RETRY_SCRIPT" clear "test_sig_1" >/dev/null 2>&1
bash "$RETRY_SCRIPT" check >/dev/null 2>&1; ec=$?
assert_exit_code "clear 后 check 返回 0" 0 $ec ""
output=$(bash "$RETRY_SCRIPT" record "test_sig_1" "fresh start" 2>&1)
assert_contains "clear 后 record 从 1 开始" "retry 1/3" "$output"
echo ""

# ── Summary ──
TOTAL=$((PASS + FAIL))
echo "=============================="
echo "  R39 预算单元测试: "
echo "  通过: $PASS / $TOTAL"
echo "  失败: $FAIL / $TOTAL"
echo "=============================="

# Auto-cleanup restores actual budget
[ "$FAIL" -eq 0 ]
