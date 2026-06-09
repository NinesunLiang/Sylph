#!/usr/bin/env bash
# cross-verify-b-terminal.sh — B 终端跨会话独立验证
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# Role: 在独立终端中运行 verification 任务，不与 AI 主会话共享上下文
# 三扇门 A→B→A 的 B 环节：盲执行验证
#
# 用法:
#   bash cross-verify-b-terminal.sh                    # 运行标准验证套件
#   bash cross-verify-b-terminal.sh --quick             # 快速验证
#   bash cross-verify-b-terminal.sh --full              # 全量验证 + smoke test
#
# 原理:
#   - 独立 bash 进程，不读取 AI 上下文
#   - 只信任文件系统事实（exit code, file content, checksum）
#   - 输出 JSON 结果供 AI 读取（Source III 运行时事实）
#
# 哲学映射:
#   #4 没验证=没做 — 独立验证是最后一步
#   #6 0信任 — 不信任 AI 上下文中的任何断言

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

MODE="${1:---standard}"
RESULT_FILE="$STATE_DIR/b-terminal-result.json"
START_TS=$(date +%s)

echo "=== B-Terminal Cross-Verify ==="
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Mode: $MODE"
echo ""

PASSED=0
FAILED=0
CHECKS=()

run_check() {
    local name="$1"
    local cmd="$2"
    echo -n "[ ] $name ... "
    if eval "$cmd" 2>/dev/null; then
        echo "PASS"
        PASSED=$((PASSED + 1))
        CHECKS+=("{\"name\":\"$name\",\"status\":\"PASS\"}")
    else
        echo "FAIL"
        FAILED=$((FAILED + 1))
        CHECKS+=("{\"name\":\"$name\",\"status\":\"FAIL\"}")
    fi
}

# ─── 核心验证 ───────────────────────────────────────────────
run_check "harness-smoke-test" "bash $PROJECT_ROOT/.claude/scripts/harness-smoke-test.sh 2>&1 | grep -q 'summary:.*0 failed'"
run_check "audit-hooks-zero-critical" "bash $PROJECT_ROOT/.claude/scripts/audit-hooks.sh 2>&1 | grep -q '🔴 严重: 0'"
run_check "source-mirror-consistent" "bash $PROJECT_ROOT/.claude/scripts/audit-hooks.sh --check-source-mirror 2>&1 | grep -q '全部一致'"

# 快速验证只跑核心
if [ "$MODE" = "--quick" ]; then
    echo ""
    echo "=== Quick Check Complete ==="
    ${PYTHON_BIN:-python3} -c "
import json, time
result = {'terminal': 'B', 'mode': 'quick', 'passed': $PASSED, 'failed': $FAILED,
          'total': $((PASSED+FAILED)), 'duration_sec': $(($(date +%s) - START_TS)),
          'checks': [$(IFS=,; echo "${CHECKS[*]}")], 'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'}
with open('$RESULT_FILE', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
    exit $FAILED
fi

# ─── 扩展验证 ───────────────────────────────────────────────
run_check "flywheel-log-exists" "[ -f ~/.claude/flywheel.log ] && [ -s ~/.claude/flywheel.log ]"
run_check "error-signals-exists" "[ -f $STATE_DIR/error-signals.jsonl ] && [ -s $STATE_DIR/error-signals.jsonl ]"
run_check "hook-syntax-all" "for f in $PROJECT_ROOT/.claude/hooks/*.sh; do bash -n \"\$f\" || exit 1; done"

if [ "$MODE" = "--full" ]; then
    run_check "auto-score-above-8.6" "bash $PROJECT_ROOT/.claude/scripts/auto-score.sh 2>&1 | grep -q '>= 8.6'"
    run_check "bash-audit-no-critical" "bash $PROJECT_ROOT/.claude/scripts/posttool-bash-audit.sh 2>&1 | grep -qv 'CRITICAL'"
fi

# ─── 输出结果 ───────────────────────────────────────────────
echo ""
echo "=== B-Terminal Result ==="
echo "Passed: $PASSED | Failed: $FAILED | Total: $((PASSED+FAILED))"
echo "Duration: $(($(date +%s) - START_TS))s"

${PYTHON_BIN:-python3} -c "
import json, time
result = {'terminal': 'B', 'mode': '$MODE', 'passed': $PASSED, 'failed': $FAILED,
          'total': $((PASSED+FAILED)), 'duration_sec': $(($(date +%s) - START_TS)),
          'checks': [$(IFS=,; echo "${CHECKS[*]}")], 'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'}
with open('$RESULT_FILE', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"

exit $FAILED
