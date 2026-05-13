#!/usr/bin/env bash
# lx-unattended-toggle.sh — [已废弃] 请改用 lx-goal
# 本文件保留用于后向兼容，自动转发到 lx-goal.sh
# 移除时间: 2026-06-01 后
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/lx-goal.sh" ]; then
    echo "⚠️ [DEPRECATED] lx-unattended 已废弃，请改用 lx-goal" >&2
    exec bash "$SCRIPT_DIR/lx-goal.sh" "$@"
fi
# 回退: 新脚本不存在时使用内嵌逻辑
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null
MODE_FILE="$STATE_DIR/unattended-mode.json"
case "${1:-status}" in
    on)
        GOAL="${2:-目标任务}"
        EXPIRY_HOURS="${3:-6}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        cat > "$MODE_FILE" <<JSON
{"active":true,"mode":"unattended","goal":"$GOAL","expires_at":"$EXPIRES","activated_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","retry_count":0,"skipped_risks":[],"completed_tasks":[]}
JSON
        touch "$STATE_DIR/autonomous.active"
        echo "⚠️ [DEPRECATED] 目标模式已开启（旧格式），建议: lx-goal on \"$GOAL\""
        ;;
    off) rm -f "$MODE_FILE" "$STATE_DIR/.unattended-mode" "$STATE_DIR/autonomous.active" ;;
    status) [ -f "$MODE_FILE" ] && echo "目标模式: 🟢 开启中（旧格式）" || echo "目标模式: ⚪ 已关闭" ;;
    *) echo "用法: lx-unattended on|off|status — [废弃] 建议使用 lx-goal"; exit 1 ;;
esac
