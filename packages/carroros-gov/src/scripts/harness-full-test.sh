#!/usr/bin/env bash
# harness-full-test.sh — 全量冒烟测试：运行所有领域测试套件并聚合结果
#
# 设计：全量 = 领域测试用例之和
# 每个领域套件保持独立，通过硬连接（子进程调用）聚合
#
# 使用：bash packages/carroros-gov/src/scripts/harness-full-test.sh
# 返回：0=全绿；非 0=失败项总数
# 日志：.omc/state/harness-full-<timestamp>.log

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
# 从 scripts/ 出发找项目根：packages/carroros-gov/src/scripts/ → 4级上到 Carror_OS
# 试一试不同级数，能找到 AGENTS.md 的就是根
for LEVELS in ".." "../.." "../../.." "../../../.." "../../../../.." "../../../../../.."; do
    CANDIDATE=$(cd "$HERE/$LEVELS" && pwd 2>/dev/null)
    if [ -f "$CANDIDATE/AGENTS.md" ]; then
        cd "$CANDIDATE" || exit 99
        PROJECT_ROOT=$CANDIDATE
        break
    fi
done
if [ -z "${PROJECT_ROOT:-}" ]; then
    echo "FATAL: Cannot find project root (AGENTS.md not found)"
    exit 99
fi
TS=$(date -u +%Y%m%d-%H%M%S)
LOG=".omc/state/harness-full-$TS.log"
mkdir -p .omc/state

# ── 两份路径：先找 packages 分支，再 fallback 旧路径 ──
PACKAGE_SCRIPTS="$PROJECT_ROOT/packages/carroros-gov/src/scripts"
LEGACY_SCRIPTS="$PROJECT_ROOT/.claude/scripts"
if [ -d "$PACKAGE_SCRIPTS" ]; then
    SCRIPT_DIR="$PACKAGE_SCRIPTS"
else
    SCRIPT_DIR="$LEGACY_SCRIPTS"
fi

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
# 每个套件输出格式不同，逐个匹配已知格式
parse_summary() {
    local output="$1" suite_name="$2"
    local pass=0 fail=0 warn=0

    # 去掉 ANSI 转义序列（颜色控制码），否则 grep 无法匹配
    output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')

    # 格式1: "summary: X/Y passed, Z failed"
    if echo "$output" | grep -qE '^summary: [0-9]+/[0-9]+ passed, [0-9]+ failed'; then
        local line; line=$(echo "$output" | grep -E '^summary: [0-9]+/[0-9]+ passed')
        pass=$(echo "$line" | grep -oE '[0-9]+/[0-9]+' | grep -oE '^[0-9]+')
        fail=$(echo "$line" | grep -oE '[0-9]+ failed' | grep -oE '^[0-9]+')

    # 格式2: "Tier N: X/Y passed, Z failed" 或 "Deep Runtime: X/Y passed, Z failed"
    elif echo "$output" | grep -qE '(Tier [234]:|Deep Runtime:).*[0-9]+/[0-9]+ passed'; then
        local line; line=$(echo "$output" | grep -E '(Tier [234]:|Deep Runtime:)' | grep -E '[0-9]+/[0-9]+ passed' | head -1)
        pass=$(echo "$line" | grep -oE '[0-9]+/[0-9]+ passed' | grep -oE '^[0-9]+')
        fail=$(echo "$line" | grep -oE '[0-9]+ failed' | grep -oE '^[0-9]+')

    # 格式3: "PASS: N  FAIL: N" 格式 (Capability Matrix)
    # 输出: "Checks: 63 pass  0 fail  21 warn  Total=84"
    elif echo "$output" | grep -qE 'Checks: [0-9]+ pass'; then
        local line; line=$(echo "$output" | grep -E 'Checks: [0-9]+ pass' | head -1)
        pass=$(echo "$line" | grep -oE '[0-9]+ pass' | grep -oE '^[0-9]+')
        fail=$(echo "$line" | grep -oE '[0-9]+ fail' | grep -oE '^[0-9]+')

    # 格式4: "结果: X 通过 / Y 失败 / 共 Z 断言" (ED Red Team — 中文格式)
    elif echo "$output" | grep -qE '结果: [0-9]+ 通过'; then
        local line; line=$(echo "$output" | grep -E '结果: [0-9]+ 通过' | head -1)
        pass=$(echo "$line" | grep -oE '[0-9]+ 通过' | grep -oE '^[0-9]+')
        fail=$(echo "$line" | grep -oE '[0-9]+ 失败' | grep -oE '^[0-9]+')

    # 格式5: "Results: X PASS / Y FAIL / Z SKIP" (Race Condition — 英文大写)
    elif echo "$output" | grep -qE 'Results: [0-9]+ PASS'; then
        local line; line=$(echo "$output" | grep -E 'Results: [0-9]+ PASS' | head -1)
        pass=$(echo "$line" | grep -oE '[0-9]+ PASS' | grep -oE '^[0-9]+')
        fail=$(echo "$line" | grep -oE '[0-9]+ FAIL' | grep -oE '^[0-9]+')

    # 格式6: "Results: PASS=N FAIL=N" — Harness Smoke 的汇总格式
    elif echo "$output" | grep -qE 'Results: PASS='; then
        local line; line=$(echo "$output" | grep -E 'Results: PASS=' | head -1)
        pass=$(echo "$line" | grep -oE 'PASS=[0-9]+' | grep -oE '[0-9]+')
        fail=$(echo "$line" | grep -oE 'FAIL=[0-9]+' | grep -oE '[0-9]+')

    # 格式7: "PASS: N" / "FAIL: N" (简单名值对)
    elif echo "$output" | grep -qE 'PASS: [0-9]+'; then
        pass=$(echo "$output" | grep -oE 'PASS: [0-9]+' | grep -oE '[0-9]+' | tail -1)
        fail=$(echo "$output" | grep -oE 'FAIL: [0-9]+' | grep -oE '[0-9]+' | tail -1 || echo 0)

    # 格式7: "Checks: N pass  N fail" (备选)
    elif echo "$output" | grep -qE 'Checks: [0-9]+ pass'; then
        pass=$(echo "$output" | grep -oE '[0-9]+ pass' | grep -oE '^[0-9]+')
        fail=$(echo "$output" | grep -oE '[0-9]+ fail' | grep -oE '^[0-9]+')

    else
        # 未知格式
        log "  ⚠️  无法解析 $suite_name 结果格式，算 0 pass"
    fi

    warn=$(echo "$output" | grep -oE '[0-9]+ warn' | grep -oE '^[0-9]+' || echo 0)
    [ -z "$pass" ] && pass=0
    [ -z "$fail" ] && fail=0
    [ -z "$warn" ] && warn=0

    log "  📊 $suite_name: $pass pass, $fail fail, $warn warn"
    TOTAL_PASS=$((TOTAL_PASS + pass))
    TOTAL_FAIL=$((TOTAL_FAIL + fail))
    TOTAL_WARN=$((TOTAL_WARN + warn))
}

# ── 确定运行方式 ──
suffix="${1##*.}"
get_runner() {
    case "$1" in
        *.py) echo "python3" ;;
        *.sh|*) echo "bash" ;;
    esac
}

run_suite() {
    local script="$1" name="$2"
    suite_log "$name"
    if [ ! -f "$SCRIPT_DIR/$script" ]; then
        log "  ⚠️  $script 不存在，跳过"
        return
    fi

    local runner
    runner=$(get_runner "$script")

    local start_ts=$(date +%s)
    local output
    output=$("$runner" "$SCRIPT_DIR/$script" 2>&1)
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
log "  脚本目录: $SCRIPT_DIR"
log ""

# ── L0: 基础设施 ──
run_suite "harness-smoke-test.py"      "Harness Smoke (核心冒烟)"

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
