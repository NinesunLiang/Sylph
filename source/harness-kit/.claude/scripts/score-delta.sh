#!/usr/bin/env bash
# score-delta.sh — 语义改进可感知性: before/after runtime 数据对比
# P2-7: 记录每项语义修复的 before/after runtime 数据
# 用法: bash .claude/scripts/score-delta.sh [--since <timestamp>]

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
STATE_DIR="$PROJECT_ROOT/.omc/state"
TS=$(date -u +%Y%m%d-%H%M%S)

pct() { echo "scale=1; $1 * 100 / $2" | bc 2>/dev/null || echo "0"; }

SINCE_TS="${2:-0}"
OUTPUT_FILE="$STATE_DIR/score-delta-$TS.json"

echo "=== Score Delta v1 (语义改进可感知性) @ $TS ==="

# R1: Flywheel 覆盖率变化
FW_LOG="${HOME}/.claude/flywheel.log"
FW_COVERED=0
if [ -f "$FW_LOG" ] && [ -s "$FW_LOG" ]; then
  FW_COVERED=$(cut -d',' -f2 "$FW_LOG" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
FW_ENABLED=$(sed -n '/^hooks_enabled:/,/^[a-z]/p' .claude/harness.yaml 2>/dev/null | grep -cE '^\s\s\w+:\s*true\s*$' || echo "0")
FW_PCT=$(pct "$FW_COVERED" "$FW_ENABLED")

# R2: Error DNA 噪声率
ED_TOTAL=0; ED_NOISE=0
if [ -f "$STATE_DIR/error-dna.jsonl" ]; then
  ED_TOTAL=$(wc -l < "$STATE_DIR/error-dna.jsonl" 2>/dev/null | tr -d ' \n\r'); ED_TOTAL="${ED_TOTAL:-0}"
  ED_NOISE=$(grep -c '"status": "noise"' "$STATE_DIR/error-dna.jsonl" 2>/dev/null | tr -d '\n\r '); ED_NOISE="${ED_NOISE:-0}"
fi
ED_NOISE_PCT=$(pct "$ED_NOISE" "$ED_TOTAL")

# R3: 矛盾检测统计
CONT_TOTAL=0; CONT_TRUE=0; CONT_BASH=0
if [ -f "$STATE_DIR/edit-churn-log.jsonl" ]; then
  CONT_TOTAL=$(wc -l < "$STATE_DIR/edit-churn-log.jsonl" 2>/dev/null | tr -d ' ')
  CONT_TRUE=$(grep -c '"contradiction": true' "$STATE_DIR/edit-churn-log.jsonl" 2>/dev/null || echo "0")
  CONT_BASH=$(grep -c '"type": "bash_edit"' "$STATE_DIR/edit-churn-log.jsonl" 2>/dev/null || echo "0")
fi

# R4: Hook 证据覆盖率
HOOK_TOTAL=$(ls .claude/hooks/*.sh 2>/dev/null | grep -v 'harness_config.sh\|agentic-ui.sh' | wc -l | tr -d ' ')
HOOK_EVID=0
if [ -f "$STATE_DIR/hook-evidence.jsonl" ]; then
  HOOK_EVID=$(cut -d'"' -f4 "$STATE_DIR/hook-evidence.jsonl" 2>/dev/null | sort -u | wc -l | tr -d ' ')
fi
HOOK_EVID_PCT=$(pct "$HOOK_EVID" "$HOOK_TOTAL")

# R5: 构建健康度
BUILD_STREAK=0
if [ -f "$STATE_DIR/build-fail-gate.json" ]; then
  BUILD_STREAK=$(python3 -c "import json; print(json.load(open('$STATE_DIR/build-fail-gate.json')).get('streak',0))" 2>/dev/null || echo "0")
fi

# 语义改进可感知清单
DELTA_ITEMS=""

# E6: 假阳性率变化 (如果有 edit-churn-log 数据)
if [ "$CONT_TRUE" -gt 0 ] 2>/dev/null && [ "$CONT_TOTAL" -gt 0 ] 2>/dev/null; then
  REVERT_COUNT=$(grep -c '"type": "revert"' "$STATE_DIR/edit-churn-log.jsonl" 2>/dev/null); REVERT_COUNT="${REVERT_COUNT:-0}"
  REVERT_COUNT=$(echo "$REVERT_COUNT" | tr -d '\n\r ')
  CONT_TOTAL_C=$(echo "$CONT_TOTAL" | tr -d '\n\r ')
  CONT_TRUE_C=$(echo "$CONT_TRUE" | tr -d '\n\r ')
  CONT_FP=$((${CONT_TRUE_C:-0} - ${REVERT_COUNT:-0}))
  [ "$CONT_FP" -lt 0 ] 2>/dev/null && CONT_FP=0
  CONT_FP_RATE=$(pct "$CONT_FP" "${CONT_TRUE_C:-1}")
  DELTA_ITEMS="${DELTA_ITEMS}E6: contradiction=true 计数=${CONT_TRUE_C}, 回退确认=${REVERT_COUNT}; "
fi

# C8: 源镜像漂移状态
if [ -x ".claude/scripts/audit-hooks.sh" ]; then
  MIRROR_RED=$(bash .claude/scripts/audit-hooks.sh --check-source-mirror 2>/dev/null | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
  MIRROR_RED="${MIRROR_RED:-N/A}"
  DELTA_ITEMS="${DELTA_ITEMS}C8: source mirror CRITICAL 漂移=${MIRROR_RED}; "
fi

# Bash 编辑检测覆盖率 (DG-107)
if [ "$CONT_BASH" -gt 0 ] 2>/dev/null; then
  DELTA_ITEMS="${DELTA_ITEMS}P0-2: Bash 编辑检测已激活, 记录=${CONT_BASH}条; "
else
  DELTA_ITEMS="${DELTA_ITEMS}P0-2: Bash 编辑检测待验证（无 Bash 编辑记录）; "
fi

# Retry-Budget 清理状态 (P1-4)
if [ -f "$STATE_DIR/retry-budget.json" ]; then
  RB_COUNT=$(python3 -c "import json; d=json.load(open('$STATE_DIR/retry-budget.json')); print(len(d.get('signatures',{})))" 2>/dev/null || echo "N/A")
  DELTA_ITEMS="${DELTA_ITEMS}P1-4: retry-budget 签名数=${RB_COUNT}; "
else
  DELTA_ITEMS="${DELTA_ITEMS}P1-4: retry-budget 已清理（build 成功自动清除）; "
fi

echo "--- 运行时快照 ---"
echo "R1 飞轮覆盖率:       ${FW_COVERED}/${FW_ENABLED} = ${FW_PCT}%"
echo "R2 错误信噪比:       ${ED_NOISE}/${ED_TOTAL} = ${ED_NOISE_PCT}%"
echo "R3 矛盾检测:         总计=${CONT_TOTAL} 矛盾标记=${CONT_TRUE} Bash编辑=${CONT_BASH}"
echo "R4 Hook证据:          ${HOOK_EVID}/${HOOK_TOTAL} = ${HOOK_EVID_PCT}%"
echo "R5 构建健康:         streak=${BUILD_STREAK}"
echo "---"
echo "语义改进可感知: ${DELTA_ITEMS}"

# JSON 输出
cat > "$OUTPUT_FILE" <<JSONEOF
{
  "generated_at": "$TS",
  "runtime_snapshot": {
    "flywheel_coverage_pct": $FW_PCT,
    "error_dna_noise_pct": $ED_NOISE_PCT,
    "contradiction_total": $CONT_TOTAL,
    "contradiction_true": $CONT_TRUE,
    "bash_edits_detected": $CONT_BASH,
    "hook_evidence_pct": $HOOK_EVID_PCT,
    "build_streak": $BUILD_STREAK
  },
  "semantic_improvements": "$DELTA_ITEMS"
}
JSONEOF

echo "---"
echo "Delta written: $OUTPUT_FILE"
exit 0
