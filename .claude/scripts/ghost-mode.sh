#!/usr/bin/env bash
# ghost-mode.sh — [已废弃] 请改用 lx-ghost
# 本文件保留用于后向兼容，自动转发到 lx-ghost.sh
# 移除时间: 2026-06-01 后
#
# 哲学 #3 先守护: 旧格式文件标记仍被 is_mode_active() 兼容检测
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/lx-ghost.sh" ]; then
    echo "⚠️ [DEPRECATED] ghost-mode.sh 已废弃，请改用 lx-ghost" >&2
    exec bash "$SCRIPT_DIR/lx-ghost.sh" "$@"
fi
# 回退: 新脚本不存在时使用内嵌逻辑
# 注意: 以下为兼容路径，is_mode_active() 仍检测 ghost-mode.json 等旧格式
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null
MODE_FILE="$STATE_DIR/ghost-mode.json"
case "${1:-status}" in
    on)
        DIRECTION="${2:-自主探索}"
        INTERVAL="${3:-600}"
        EXPIRY_HOURS="${4:-3}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        cat > "$MODE_FILE" <<JSON
{"active":true,"mode":"ghost","direction":"$DIRECTION","cycle_interval_seconds":$INTERVAL,"expires_at":"$EXPIRES","activated_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","retry_count":0,"skipped_risks":[]}
JSON
        touch "$STATE_DIR/autonomous.active"
        echo "⚠️ [DEPRECATED] 幽灵模式已开启（旧格式），建议: lx-ghost on \"$DIRECTION\""
        ;;
    off)
        rm -f "$MODE_FILE" "$STATE_DIR/ghost-mode.active" "$STATE_DIR/autonomous.active"
        echo "幽灵模式已关闭"
        ;;
    status)
        [ -f "$MODE_FILE" ] && echo "幽灵模式: 🟢 开启中（旧格式）" || echo "幽灵模式: ⚪ 已关闭"
        ;;
    *)
        echo "用法: ghost-mode on|off|status — [废弃] 建议使用 lx-ghost"
        exit 1
        ;;
esac
