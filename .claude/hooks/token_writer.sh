#!/usr/bin/env bash

# token_writer.sh — 写入 token-tracking-index.json
#
# 由 PostToolUse 钩子调用或 context-guard.sh 调用，
# 作为 context_monitor.py 的写入端，更新 token 使用量。
#
# 用法: token_writer.sh [--increment]
#   --increment    每调用一次将 usage 增加约 500 (模拟轨迹)
#   无参数         仅确保文件存在（默认值写入）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

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

# --increment 模式：每次增加约 500
if [ "${1:-}" = "--increment" ]; then
    USAGE=$((USAGE + 500))
    # 不超过 limit
    [ "$USAGE" -gt "$LIMIT" ] && USAGE=$LIMIT
fi

cat > "$INDEX_FILE" <<EOF
{
  "usage": $USAGE,
  "limit": $LIMIT,
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')",
  "source": "token_writer.sh"
}
EOF

exit 0
