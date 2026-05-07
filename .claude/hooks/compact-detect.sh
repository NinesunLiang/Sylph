#!/usr/bin/env bash
# compact-detect.sh — UserPromptSubmit Hook
#
# 检测用户输入是否为 /compact，保存 compact 前 usage 供 token_writer 处理
# 流程：
#   UserPromptSubmit (此脚本) → token_writer.sh --increment (下一次 PostToolUse)
#
# 依赖：token-tracking-index.json（由 token_writer.sh 维护）
# 输出：.omc/state/token-compact-state.json（写入预 compact 状态）
#
# 不阻塞：任何失败都 exit 0，不干扰用户流程

# 故意不设 set -e: 本 hook 永不阻塞，任何失败静默 exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Config gate: 从 harness.yaml 读取启停开关
source "$SCRIPT_DIR/harness_config.sh" 2>/dev/null || true
hc_enabled "compact_detect" || exit 0

STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
COMPACT_STATE="$STATE_DIR/token-compact-state.json"

# 读取 STDIN（UserPromptSubmit 会传入用户输入）
INPUT=$(cat 2>/dev/null || echo "")

# 清理输入（移除 ANSI 码、首尾空格）
CLEAN_INPUT=$(echo "$INPUT" | sed 's/\x1b\[[0-9;]*m//g' | tr -d '[:space:]')

# 匹配 /compact 命令（含各种变体：/compact、compact、/compact  等）
case "$CLEAN_INPUT" in
    /compact|compact|/compact*)
        ;;
    *)
        exit 0
        ;;
esac

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# 读取当前 usage
USAGE=0
if [ -f "$INDEX_FILE" ]; then
    USAGE=$(python3 -c "
import json
try:
    d = json.load(open('$INDEX_FILE'))
    print(d.get('usage', 0))
except:
    print('0')
" 2>/dev/null)
fi

# 写入 compact state
cat > "$COMPACT_STATE" <<EOF
{
  "pre_compact_usage": $USAGE,
  "detected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%s)"
}
EOF

exit 0
