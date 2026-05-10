#!/usr/bin/env bash
# token_writer.sh — PostToolUse:.* / SessionStart — 写入 token 用量追踪索引供 context-guard 计算
# Role: 写入 token 用量追踪索引供 context-guard 计算
# NOTE: 增量优先使用实际响应内容字节（tool_response 的 content/stdout 字节数），
# 无响应内容时回退到工具类型固定值（Read 500 / Grep 1000 / Bash 2000 / Edit&Write 5000 / 默认 3000）。
# 增量上限 50000 防止异常值。
# 阈值选择依据: Edit-heavy 场景 ~15 轮 50% / ~20 轮 60%，Read-heavy 场景 ~150 轮 50% / ~240 轮 60%

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
hc_enabled "token_writer" || exit 0
STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
SAVINGS_FILE="$STATE_DIR/token-savings.json"
COMPACT_STATE="$STATE_DIR/token-compact-state.json"

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# Read stdin for tool context (PostToolUse hook — extract tool_name for differentiated increment)
INPUT_STDIN=$(cat 2>/dev/null || echo "")
TOOL_NAME=""
if [ -n "$INPUT_STDIN" ]; then
    if command -v jq &>/dev/null; then
        TOOL_NAME=$(echo "$INPUT_STDIN" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
    else
        TOOL_NAME=$(echo "$INPUT_STDIN" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
        [ -z "$TOOL_NAME" ] && TOOL_NAME=$(echo "$INPUT_STDIN" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    fi
fi

# Map tool type to per-turn token increment
# Read: light, Grep: medium, Bash: moderate, Edit/Write: heavy, default: baseline
get_increment() {
    case "${TOOL_NAME:-}" in
        Read|read)       echo 500  ;;
        Grep|grep)       echo 1000 ;;
        Bash|bash)       echo 2000 ;;
        Write|write|Edit|edit) echo 5000 ;;
        *)               echo 3000 ;;
    esac
}

# Get effective increment: actual response content bytes, or fallback to tool-type fixed value
# Read/Grep → content blocks (array of {type, text}), Bash → stdout, Edit/Write → fallback
get_effective_incr() {
    local raw
    raw=$(echo "$INPUT_STDIN" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tr = d.get('tool_response', {}) or {}

    # Sum all text from content blocks (Read, Grep, Edit results)
    total = 0
    content = tr.get('content')
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                total += len(str(block.get('text', '') or ''))

    # Fall back to stdout (Bash results)
    if total == 0:
        stdout = tr.get('stdout', '') or ''
        total = len(stdout)

    # Fall back to stderr
    if total == 0:
        stderr = tr.get('stderr', '') or ''
        total = len(stderr)

    print(total if total > 0 else '0')
except:
    print('0')
" 2>/dev/null)

    if [ -n "$raw" ] && [ "$raw" -gt 0 ] 2>/dev/null; then
        [ "$raw" -gt 50000 ] && raw=50000
        echo "$raw"
    else
        get_increment
    fi
}

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
            NEW_USAGE=$((POST_COMPACT + 3000))
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
            # 无待处理 compact：正常递增（优先按实际响应字节）
            INCR=$(get_effective_incr)
            USAGE=$((USAGE + INCR))
            [ "$USAGE" -gt "$LIMIT" ] && USAGE=$LIMIT
        fi
    else
        # 无 compact state 文件：正常递增（优先按实际响应字节）
        INCR=$(get_effective_incr)
        USAGE=$((USAGE + INCR))
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
