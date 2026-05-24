#!/usr/bin/env bash
# session-health-check.sh — 抗衰减: 会话健康检查
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# Compares last-audit date with current date; flags if >7 days stale.
# Also checks for stale lock files, large error-dna, and flywheel P0 backlog.
#
# Commands:
#   status   — Print health check report
#   mark     — Mark current time as last audit timestamp
#   inject   — Inject health warnings (for SessionStart hook)

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
HEALTH_FILE="$STATE_DIR/session-health.json"
MAX_AGE_DAYS=7
mkdir -p "$STATE_DIR"

init_health() {
  if [ ! -f "$HEALTH_FILE" ]; then
    echo '{"last_audit": null, "created": '$(date +%s)'}' > "$HEALTH_FILE"
  fi
}

days_since_audit() {
  init_health
  ${PYTHON_BIN:-python3} -c "
import json, time
try:
    d = json.load(open('$HEALTH_FILE'))
    last = d.get('last_audit')
    if last is None:
        print('999')
    else:
        age = (time.time() - last) / 86400
        print(f'{age:.1f}')
except:
    print('999')
" 2>/dev/null
}

check_stale_locks() {
  local stale=0
  local msg=""
  for lock in "$STATE_DIR"/*.lock "$STATE_DIR"/locks.json; do
    if [ -f "$lock" ]; then
      local age=$(( $(date +%s) - $(stat -f %m "$lock" 2>/dev/null || stat -c %Y "$lock" 2>/dev/null || echo 0) ))
      if [ "$age" -gt 3600 ] 2>/dev/null; then
        stale=$((stale + 1))
        msg="$msg  · $(basename "$lock"): ${age}s stale"
      fi
    fi
  done
  echo "$stale|$msg"
}

check_error_dna_size() {
  if [ -f "$STATE_DIR/error-dna.json" ]; then
    local size=$(wc -c < "$STATE_DIR/error-dna.json" | tr -d ' ')
    if [ "$size" -gt 102400 ] 2>/dev/null; then
      echo "1|error-dna.json: ${size} bytes (>100KB, may indicate unfixed errors)"
    else
      echo "0|"
    fi
  else
    echo "0|"
  fi
}

check_flywheel_p0() {
  local flywheel="$HOME/.claude/flywheel-buffer.jsonl"
  if [ -f "$flywheel" ]; then
    local count=$(wc -l < "$flywheel" | tr -d ' ')
    if [ "$count" -gt 0 ] 2>/dev/null; then
      echo "1|flywheel P0: ${count} pending events"
    else
      echo "0|"
    fi
  else
    echo "0|"
  fi
}

case "${1:-status}" in
  status)
    init_health
    days=$(days_since_audit)
    echo "═══════════════════════════════════════"
    echo "  Session Health Check"
    echo "═══════════════════════════════════════"
    if [ "$(echo "$days > $MAX_AGE_DAYS" | bc -l 2>/dev/null)" = 1 ] || [ "$days" = "999" ]; then
      echo "  🔴 审计年龄: ${days}天 (阈值: ${MAX_AGE_DAYS}天)"
      echo "  建议: 运行审计脚本进行全面检查"
    else
      echo "  🟢 审计年龄: ${days}天 (阈值: ${MAX_AGE_DAYS}天)"
    fi

    IFS='|' read -r stale_count stale_msg <<< "$(check_stale_locks)"
    if [ "$stale_count" -gt 0 ]; then
      echo "  🟡 过期锁: ${stale_count}个"
      echo "$stale_msg"
    else
      echo "  🟢 锁状态: 正常"
    fi

    IFS='|' read -r dna_warn dna_msg <<< "$(check_error_dna_size)"
    if [ "$dna_warn" = "1" ]; then
      echo "  🟡 $dna_msg"
    fi

    IFS='|' read -r fly_warn fly_msg <<< "$(check_flywheel_p0)"
    if [ "$fly_warn" = "1" ]; then
      echo "  🟡 $fly_msg"
    fi
    echo "═══════════════════════════════════════"
    ;;

  mark)
    echo '{"last_audit": '$(date +%s)', "created": '$(date +%s)'}' > "$HEALTH_FILE"
    echo "[Health] 审计时间已标记: $(date)"
    ;;

  inject)
    init_health
    days=$(days_since_audit)
    if [ "$(echo "$days > $MAX_AGE_DAYS" | bc -l 2>/dev/null)" = 1 ] || [ "$days" = "999" ]; then
      echo "[Health Warning] 上次审计已是 ${days} 天前 (阈值: ${MAX_AGE_DAYS}天)"
      echo "  运行 .claude/scripts/session-health-check.sh status 查看详情"
    fi

    IFS='|' read -r stale_count stale_msg <<< "$(check_stale_locks)"
    if [ "$stale_count" -gt 0 ]; then
      echo "[Health Warning] ${stale_count} 个过期锁文件"
    fi
    ;;

  *)
    echo "Usage: session-health-check.sh {status|mark|inject}"
    exit 1
    ;;
esac
