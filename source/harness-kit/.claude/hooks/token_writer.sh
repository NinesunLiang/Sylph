#!/usr/bin/env bash

# token_writer.sh — 写入 token-tracking-index.json + token-savings.json
#
# 由 PostToolUse 钩子调用或 context-guard.sh 调用，
# 作为 context_monitor.py 的写入端，更新 token 使用量。
#
# 功能：
#   1. 维护 token-tracking-index.json（合成使用计数器）
#   2. 维护 token-savings.json（分项节省累积）
#   3. 处理 compact 后续（检测待处理的 compact → 计算节省 → 重置计数器）
#
# 用法: token_writer.sh [--increment]
#   --increment    每调用一次将 usage 增加约 500 (模拟轨迹)
#   无参数         仅确保文件存在（默认值写入）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
hc_enabled "token_writer" || exit 0
STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
SAVINGS_FILE="$STATE_DIR/token-savings.json"
COMPACT_STATE="$STATE_DIR/token-compact-state.json"

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# --reset 模式：新会话重置计数器
if [ "${1:-}" = "--reset" ]; then
    cat > "$INDEX_FILE" <<'RESETEOF'
{
  "usage": 0,
  "limit": 200000,
  "last_updated": "SESSION_START",
  "source": "token_writer.sh --reset"
}
RESETEOF
    echo "[token_writer] reset" >> "$STATE_DIR/.token-writer-session.log" 2>/dev/null
    exit 0
fi

# 从 harness config 读取可配置的 token limit
LIMIT=$(hc_get "token_tracking.limit" "200000")

# 读取当前值
USAGE=0
if [ -f "$INDEX_FILE" ]; then
    DATA=$(cat "$INDEX_FILE" 2>/dev/null)
    USAGE=$(echo "$DATA" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('usage', 0))
except:
    print('0')
" 2>/dev/null)
fi

# 读取 savings 当前值
COMPACT_SAVED=0
COMPACT_EVENTS=0
if [ -f "$SAVINGS_FILE" ]; then
    SAVINGS_DATA=$(cat "$SAVINGS_FILE" 2>/dev/null)
    read -r COMPACT_SAVED COMPACT_EVENTS <<< "$(echo "$SAVINGS_DATA" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('compact', 0), d.get('compact_events', 0))
except:
    print('0 0')
" 2>/dev/null)"
fi

# --increment 模式
if [ "${1:-}" = "--increment" ]; then
    # 检查是否有待处理的 compact
    if [ -f "$COMPACT_STATE" ]; then
        PENDING=$(echo "$(cat "$COMPACT_STATE" 2>/dev/null)" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # pending=true 且 pre_compact_usage > 0
    print('true' if d.get('pre_compact_usage', 0) > 0 else 'false')
except:
    print('false')
" 2>/dev/null)

        if [ "$PENDING" = "true" ]; then
            PRE_COMPACT=$(echo "$(cat "$COMPACT_STATE" 2>/dev/null)" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('pre_compact_usage', 0))
except:
    print('0')
" 2>/dev/null)

            # 用户公式：savings = pre_compact_usage - post_compact_usage
            # post_compact_usage 估算为 pre_compact_usage × 0.3（压缩后约剩 30%）
            POST_COMPACT=$((PRE_COMPACT * 3 / 10))
            COMPACT_DELTA=$((PRE_COMPACT - POST_COMPACT))

            # 累计 compact 节省
            COMPACT_SAVED=$((COMPACT_SAVED + COMPACT_DELTA))
            COMPACT_EVENTS=$((COMPACT_EVENTS + 1))

            # 更新 usage：从旧值降至 post_compact + 当前增量（保持单调性）
            # 这样合成计数器不会暴跌（避免 context-guard 误判），但反映了 compact 效果
            NEW_USAGE=$((POST_COMPACT + 500))
            [ "$NEW_USAGE" -gt "$LIMIT" ] && NEW_USAGE=$LIMIT
            USAGE=$NEW_USAGE

            # 清除 compact state
            cat > "$COMPACT_STATE" <<'COMPACTEOF'
{
  "pre_compact_usage": 0,
  "pending": false
}
COMPACTEOF
        else
            # 无待处理 compact：正常递增
            USAGE=$((USAGE + 500))
            [ "$USAGE" -gt "$LIMIT" ] && USAGE=$LIMIT
        fi
    else
        # 无 compact state 文件：正常递增
        USAGE=$((USAGE + 500))
        [ "$USAGE" -gt "$LIMIT" ] && USAGE=$LIMIT
    fi
fi

# 写入 token-tracking-index.json
cat > "$INDEX_FILE" <<EOF
{
  "usage": $USAGE,
  "limit": $LIMIT,
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')",
  "source": "token_writer.sh"
}
EOF

# 计算 total
TOTAL=$COMPACT_SAVED

# 写入 token-savings.json
cat > "$SAVINGS_FILE" <<EOF
{
  "compact": $COMPACT_SAVED,
  "total": $TOTAL,
  "compact_events": $COMPACT_EVENTS,
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')"
}
EOF

exit 0
