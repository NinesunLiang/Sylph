#!/usr/bin/env bash
# test_race.sh — Race 蜂群协调层集成测试
#
# 测试范围:
#   - register:   注册子任务 → manifest.json + owner.json 结构验证
#   - status --all: 聚合子任务状态 (partial completion)
#   - report:     完整聚合报告
#   - 错误处理:   缺失参数/无效操作
#   - clean:      清理
#
# Usage:
#   bash test_race.sh            # 运行全部测试
#   bash test_race.sh --verbose  # 详细输出
#   bash test_race.sh <pattern>  # 运行匹配的测试

set -euo pipefail

VERBOSE=false
TEST_PATTERN="${1:-.*}"
[ "${1:-}" = "--verbose" ] && VERBOSE=true && TEST_PATTERN="${2:-.*}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RACE_MANAGER="$SCRIPT_DIR/race_manager.sh"
RACE_DIR="$PROJECT_ROOT/.omc/race"

PASS=0
FAIL=0
SKIP=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

setup() {
    # Ensure test starts clean
    rm -rf "$RACE_DIR/test-swarm-parent" "$RACE_DIR/test-standalone" "$RACE_DIR/test-err" 2>/dev/null || true
}

teardown() {
    rm -rf "$RACE_DIR/test-swarm-parent" "$RACE_DIR/test-standalone" "$RACE_DIR/test-err" 2>/dev/null || true
}

assert_eq() {
    local expected="$1"
    local actual="$2"
    local msg="${3:-}"

    if [ "$expected" = "$actual" ]; then
        return 0
    else
        [ -n "$msg" ] && echo "  ASSERT FAIL: $msg" >&2
        echo "  expected: '$expected'" >&2
        echo "  actual:   '$actual'" >&2
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local msg="${3:-}"

    if echo "$haystack" | grep -q "$needle"; then
        return 0
    else
        [ -n "$msg" ] && echo "  ASSERT FAIL: $msg" >&2
        echo "  expected to contain: '$needle'" >&2
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local msg="${2:-}"

    if [ -f "$file" ]; then
        return 0
    else
        [ -n "$msg" ] && echo "  ASSERT FAIL: $msg" >&2
        echo "  file not found: $file" >&2
        return 1
    fi
}

run_test() {
    local name="$1"
    shift

    # Pattern matching
    if ! echo "$name" | grep -E "$TEST_PATTERN" >/dev/null 2>&1; then
        SKIP=$((SKIP + 1))
        return 0
    fi

    echo -n "  [TEST] $name ... "

    # Reset workspace for each test
    teardown
    setup

    local output
    local exit_code=0

    # Run the test function
    if $VERBOSE; then
        echo ""
        if "$@"; then
            echo "    → PASS"
            PASS=$((PASS + 1))
        else
            echo "    → FAIL"
            FAIL=$((FAIL + 1))
        fi
    else
        if output=$("$@" 2>&1); then
            echo -e "${GREEN}PASS${NC}"
            PASS=$((PASS + 1))
        else
            echo -e "${RED}FAIL${NC}"
            echo "  output: $output"
            FAIL=$((FAIL + 1))
        fi
    fi
}

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

# --- test_register_basic: register 3 subtasks ---
test_register_basic() {
    local out
    out=$(bash "$RACE_MANAGER" register test-swarm-parent \
        --subtasks "A,B,C" \
        --desc "test parent" 2>&1)

    # Verify output
    echo "$out" | grep -q "RACE_REGISTERED" || return 1

    # Verify directory structure
    assert_file_exists "$RACE_DIR/test-swarm-parent/manifest.json" "manifest.json" || return 1
    assert_file_exists "$RACE_DIR/test-swarm-parent/subtasks/A/owner.json" "A/owner.json" || return 1
    assert_file_exists "$RACE_DIR/test-swarm-parent/subtasks/B/owner.json" "B/owner.json" || return 1
    assert_file_exists "$RACE_DIR/test-swarm-parent/subtasks/C/owner.json" "C/owner.json" || return 1

    # Verify manifest content
    local total
    total=$(python3 -c "import json; f=open('$RACE_DIR/test-swarm-parent/manifest.json'); d=json.load(f); print(d['total_subtasks'])")
    [ "$total" = "3" ] || { echo "expected 3 subtasks, got $total"; return 1; }

    local parent_id
    parent_id=$(python3 -c "import json; f=open('$RACE_DIR/test-swarm-parent/manifest.json'); d=json.load(f); print(d['parent_id'])")
    [ "$parent_id" = "test-swarm-parent" ] || { echo "wrong parent_id: $parent_id"; return 1; }

    # Verify subtask owner.json
    local st
    st=$(python3 -c "import json; f=open('$RACE_DIR/test-swarm-parent/subtasks/A/owner.json'); d=json.load(f); print(d['status'])")
    [ "$st" = "registered" ] || { echo "expected registered, got $st"; return 1; }

    return 0
}

# --- test_register_missing_subtasks: error without --subtasks ---
test_register_missing_subtasks() {
    local out
    out=$(bash "$RACE_MANAGER" register test-swarm-parent 2>&1 || true)

    echo "$out" | grep -q "ERROR: --subtasks is required" || return 1

    # Should NOT create workspace
    [ ! -d "$RACE_DIR/test-swarm-parent" ] || return 1

    return 0
}

# --- test_register_duplicate: error on duplicate parent ---
test_register_duplicate() {
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "A,B" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" register test-swarm-parent --subtasks "C,D" 2>&1 || true)

    echo "$out" | grep -q "ERROR: race 'test-swarm-parent' already exists" || return 1

    return 0
}

# --- test_status_all_basic: status aggregation with mixed states ---
test_status_all_basic() {
    # Register
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "A,B,C" >/dev/null 2>&1

    # Complete A
    bash "$RACE_MANAGER" complete "test-swarm-parent/A" completed "Task A done" >/dev/null 2>&1

    # Fail B
    bash "$RACE_MANAGER" complete "test-swarm-parent/B" failed "Task B failed" >/dev/null 2>&1

    # status --all
    local out
    out=$(bash "$RACE_MANAGER" status test-swarm-parent --all 2>&1)

    echo "$out" | grep -q "1/3 completed" || { echo "no 1/3"; return 1; }
    echo "$out" | grep -q "1 failed" || { echo "no 1 failed"; return 1; }
    echo "$out" | grep -q "1 registered" || { echo "no 1 registered"; return 1; }

    return 0
}

# --- test_status_all_json: JSON output ---
test_status_all_json() {
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "X,Y" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/X" completed "X done" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" status test-swarm-parent --all --json 2>&1)

    # Validate JSON
    echo "$out" | python3 -c "
import json, sys
data = json.load(sys.stdin)
assert data['race_id'] == 'test-swarm-parent', f'wrong race_id: {data[\"race_id\"]}'
assert data['total'] == 2, f'wrong total: {data[\"total\"]}'
assert data['completed'] == 1, f'wrong completed: {data[\"completed\"]}'
assert data['running'] == 0, f'wrong running: {data[\"running\"]}'
assert len(data['subtasks']) == 2, f'wrong subtask count: {len(data[\"subtasks\"])}'
" || return 1

    return 0
}

# --- test_status_all_non_parent: error on non-parent race ---
test_status_all_non_parent() {
    bash "$RACE_MANAGER" init test-standalone "standalone task" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" status test-standalone --all 2>&1 || true)

    echo "$out" | grep -q "ERROR" || return 1

    return 0
}

# --- test_complete_updates_manifest: subtask completion updates parent count ---
test_complete_updates_manifest() {
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "A,B" >/dev/null 2>&1

    # Complete both subtasks
    bash "$RACE_MANAGER" complete "test-swarm-parent/A" completed "A done" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/B" completed "B done" >/dev/null 2>&1

    # Verify manifest counts
    local comp
    comp=$(python3 -c "import json; f=open('$RACE_DIR/test-swarm-parent/manifest.json'); d=json.load(f); print(d['completed_subtasks'])")
    [ "$comp" = "2" ] || { echo "expected 2 completed, got $comp"; return 1; }

    return 0
}

# --- test_report_basic: full aggregated report ---
test_report_basic() {
    bash "$RACE_MANAGER" register test-swarm-parent \
        --subtasks "A,B,C" \
        --desc "Integration test" >/dev/null 2>&1

    bash "$RACE_MANAGER" complete "test-swarm-parent/A" completed "A output" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/B" completed "B output" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/C" failed "C error" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" report test-swarm-parent 2>&1)

    echo "$out" | grep -q "Race Report: test-swarm-parent" || return 1
    echo "$out" | grep -q "2/3 completed" || { echo "no 2/3"; return 1; }
    echo "$out" | grep -q "1 failed" || { echo "no 1 failed"; return 1; }
    echo "$out" | grep -q "A output" || return 1
    echo "$out" | grep -q "C error" || return 1

    return 0
}

# --- test_report_no_manifest: error on non-parent race ---
test_report_no_manifest() {
    bash "$RACE_MANAGER" init test-standalone "standalone" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" report test-standalone 2>&1 || true)

    echo "$out" | grep -q "ERROR" || return 1

    return 0
}

# --- test_list_shows_swarm: list shows X/Y for parent races ---
test_list_shows_swarm() {
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "A,B" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/A" completed "" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" list 2>&1)

    echo "$out" | grep -q "swarm 1/2" || return 1

    return 0
}

# --- test_clean_subtask_parent: clean removes entire swarm ---
test_clean_subtask_parent() {
    bash "$RACE_MANAGER" register test-swarm-parent --subtasks "A,B" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/A" completed "" >/dev/null 2>&1
    bash "$RACE_MANAGER" complete "test-swarm-parent/B" completed "" >/dev/null 2>&1

    # clean specific
    bash "$RACE_MANAGER" clean test-swarm-parent >/dev/null 2>&1

    [ ! -d "$RACE_DIR/test-swarm-parent" ] || return 1

    return 0
}

# --- test_bad_complete_status: error on invalid status ---
test_bad_complete_status() {
    bash "$RACE_MANAGER" init test-err "error test" >/dev/null 2>&1

    local out
    out=$(bash "$RACE_MANAGER" complete test-err "in_progress" 2>&1 || true)

    echo "$out" | grep -q "ERROR: status must be 'completed' or 'failed'" || return 1

    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

echo ""
echo "=========================================="
echo "  Race Manager Integration Tests"
echo "=========================================="
echo ""

# Register tests (bash 3.2 compatible — parallel arrays)
TEST_NAMES=()
TEST_FUNCS=()
register_test() {
    TEST_NAMES+=("$1")
    TEST_FUNCS+=("$2")
}

register_test "register: 3 subtasks + structure" "test_register_basic"
register_test "register: error without --subtasks" "test_register_missing_subtasks"
register_test "register: error on duplicate parent" "test_register_duplicate"
register_test "status --all: aggregation" "test_status_all_basic"
register_test "status --all: JSON output" "test_status_all_json"
register_test "status --all: error on non-parent" "test_status_all_non_parent"
register_test "complete: updates parent manifest" "test_complete_updates_manifest"
register_test "report: full aggregation" "test_report_basic"
register_test "report: error on non-parent" "test_report_no_manifest"
register_test "list: shows swarm X/Y" "test_list_shows_swarm"
register_test "clean: removes parent race" "test_clean_subtask_parent"
register_test "complete: invalid status error" "test_bad_complete_status"

for ((i=0; i<${#TEST_NAMES[@]}; i++)); do
    run_test "${TEST_NAMES[$i]}" "${TEST_FUNCS[$i]}"
done

# Final teardown
teardown

echo ""
echo "=========================================="
echo -e "  Results: ${GREEN}$PASS PASS${NC} / ${RED}$FAIL FAIL${NC} / ${YELLOW}$SKIP SKIP${NC}"
echo "=========================================="
echo ""

[ "$FAIL" -eq 0 ] || exit 1
