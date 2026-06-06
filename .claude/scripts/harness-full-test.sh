#!/usr/bin/env bash
# harness-full-test.sh — 全量冒烟测试：运行所有领域测试套件并聚合结果
#
# 设计：全量 = 领域测试用例之和
# 每个领域套件保持独立，通过硬连接（子进程调用）聚合
#
# 使用：bash .claude/scripts/harness-full-test.sh
# 返回：0=全绿；非 0=失败项总数
# 日志：.omc/state/harness-full-<timestamp>.log

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
SCRIPT_DIR="$PROJECT_ROOT/.claude/scripts"
TS=$(date -u +%Y%m%d-%H%M%S)
LOG=".omc/state/harness-full-$TS.log"
mkdir -p .omc/state

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_WARN=0

log()  { echo "$@" | tee -a "$LOG"; }
suite_log() {
    echo "" | tee -a "$LOG"
    echo "╔══════════════════════════════════════════════════════" | tee -a "$LOG"
    echo "║ $1" | tee -a "$LOG"
    echo "╚══════════════════════════════════════════════════════" | tee -a "$LOG"
}

# ── 解析领域套件的 summary 行 ──
# 格式: "summary: X/Y passed, Z failed" 或 "Core: X/Y passed, Z failed"
parse_summary() {
    local output="$1" suite_name="$2"
    local pass=0 fail=0 warn=0

    # 尝试匹配各种 summary 格式
    # 格式1: summary: X/Y passed, Z failed
    if echo "$output" | grep -qE "summary: [0-9]+/[0-9]+ passed, [0-9]+ failed"; then
        pass=$(echo "$output" | grep -oE "summary: [0-9]+/[0-9]+" | grep -oE "[0-9]+" | head -1)
        fail=$(echo "$output" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+")
    # 格式2: Core/Tier N/Domain: X/Y passed, Z failed
    elif echo "$output" | grep -qE "(Core|Tier|Capability|Domain|Deep|Red).*: [0-9]+/[0-9]+ passed"; then
        pass=$(echo "$output" | grep -oE "[0-9]+/[0-9]+ passed" | grep -oE "^[0-9]+")
        fail=$(echo "$output" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+")
    # 格式3: Capability Matrix 使用 PASS 计数
    elif echo "$output" | grep -qE "PASS: [0-9]+"; then
        pass=$(echo "$output" | grep -oE "PASS: [0-9]+" | grep -oE "[0-9]+" | tail -1)
        fail=$(echo "$output" | grep -oE "FAIL: [0-9]+" | grep -oE "[0-9]+" | tail -1 || echo 0)
    fi

    warn=$(echo "$output" | grep -oE "[0-9]+ warn" | grep -oE "[0-9]+" || echo 0)
    [ -z "$pass" ] && pass=0
    [ -z "$fail" ] && fail=0
    [ -z "$warn" ] && warn=0

    log "  📊 $suite_name: $pass pass, $fail fail, $warn warn"
    TOTAL_PASS=$((TOTAL_PASS + pass))
    TOTAL_FAIL=$((TOTAL_FAIL + fail))
    TOTAL_WARN=$((TOTAL_WARN + warn))
}

run_suite() {
    local script="$1" name="$2"
    suite_log "$name"
    if [ ! -f "$SCRIPT_DIR/$script" ]; then
        log "  ⚠️  $script 不存在，跳过"
        return
    fi

    local start_ts=$(date +%s)
    local output
    output=$(bash "$SCRIPT_DIR/$script" 2>&1)
    local rc=$?
    local end_ts=$(date +%s)
    local duration=$((end_ts - start_ts))

    echo "$output" | tee -a "$LOG"
    log "  ⏱️  ${duration}s (exit=$rc)"
    parse_summary "$output" "$name"
}

# ══════════════════════════════════════════════════════════════════
# 领域测试套件（按层次排列）
# ══════════════════════════════════════════════════════════════════

log "🚀 harness-full-test — 全量冒烟测试"
log "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
log "  PID: $$  日志: $LOG"
log ""

# ── L0: 基础设施 ──
run_suite "harness-smoke-test.sh"     "Harness Smoke (核心冒烟)"

# ── L1-L4: 层级运行时 ──
run_suite "tier2-runtime-test.sh"      "Tier 2 Runtime"
run_suite "tier3-runtime-test.sh"      "Tier 3 Runtime"
run_suite "tier4-e2e-test.sh"          "Tier 4 E2E"

# ── 能力矩阵 ──
run_suite "capability-matrix-test.sh"  "Capability Matrix"

# ── 深度与对抗 ──
run_suite "deep-runtime-test.sh"       "Deep Runtime"
run_suite "ed-red-team-test.sh"        "ED Red Team"

# ── 并发 ──
run_suite "test_race.sh"              "Race Condition"

# ── 审计 ──
run_suite "audit-hooks.sh"            "Audit Hooks (三方一致性)"

# ── 如果存在 .local 扩展 ──
if [ -f "$SCRIPT_DIR/harness-smoke-test.local.sh" ]; then
    suite_log "Local Extensions (客户端扩展)"
    output=$(bash "$SCRIPT_DIR/harness-smoke-test.local.sh" 2>&1)
    echo "$output" | tee -a "$LOG"
    parse_summary "$output" "Local Extensions"
fi

# ══════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════

TOTAL_ALL=$((TOTAL_PASS + TOTAL_FAIL))
log ""
log "══════════════════════════════════════════════════════"
log "  全量汇总"
log "══════════════════════════════════════════════════════"
log "  ✅ Pass:  $TOTAL_PASS"
log "  ❌ Fail:  $TOTAL_FAIL"
log "  ⚠️  Warn:  $TOTAL_WARN"
log "  📊 Total: $TOTAL_ALL ($TOTAL_PASS/$TOTAL_ALL passed)"
log "  📁 日志: $LOG"
log "══════════════════════════════════════════════════════"

if [ "$TOTAL_FAIL" -eq 0 ]; then
    log "  🧹 全量全绿通过"
else
    log "  🔴 $TOTAL_FAIL 项失败"
fi

exit $TOTAL_FAIL
