#!/usr/bin/env bash
# lsp-suggest.sh — PreToolUse:Grep — 检测 Grep 搜索导出符号时建议改用 LSP 工具
# Role: 检测 Grep 搜索导出符号时建议改用 LSP 工具

source "$(dirname "$0")/harness_config.sh"
hc_enabled "lsp_suggest" || exit 0

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
SUGGESTED_FILE="$STATE_DIR/lsp-suggested"

# 提取 pattern 字段
if command -v jq &>/dev/null; then
    PATTERN=$(echo "$INPUT" | jq -r '.tool_input.pattern // empty' 2>/dev/null)
else
    PATTERN=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('pattern', ''))
except:
    pass" 2>/dev/null)
fi

# 无 pattern 则静默放行
if [ -z "$PATTERN" ]; then
    exit 0
fi

# 排除：包含正则元字符（非纯符号搜索）
if echo "$PATTERN" | grep -qE '[.*+?\[\](){}|^$\\]'; then
    exit 0
fi

# 排除：不匹配导出符号正则（默认大写字母开头）
SYMBOL_REGEX=$(hc_get "lsp_suggest.exported_symbol_regex" "^[A-Z]")
if ! echo "$PATTERN" | grep -qE "$SYMBOL_REGEX"; then
    exit 0
fi

# 排除：太短
MIN_LEN=$(hc_get "lsp_suggest.min_symbol_length" "3")
if [ ${#PATTERN} -lt "$MIN_LEN" ]; then
    exit 0
fi

# 排除：包含非字母数字字符（非纯符号名）
if ! echo "$PATTERN" | grep -qE '^[A-Za-z0-9_]+$'; then
    exit 0
fi

# 已提醒过本会话 → 放行
if [ -f "$SUGGESTED_FILE" ]; then
    exit 0
fi

# 首次检测到 Go 符号 Grep → 阻断 + 建议 + 写标记
mkdir -p "$STATE_DIR"
touch "$SUGGESTED_FILE"

EXAMPLE_FILE=$(hc_get "lsp_suggest.example_file" "model/tasks_mongo.go")

cat >&2 <<EOF
[LSP 建议] 检测到导出符号查找: "$PATTERN"
LSP 工具可精确定位（无噪音），推荐：
  - 全局搜索: lsp_workspace_symbols(query="$PATTERN", file="$EXAMPLE_FILE")
  - 找定义:   lsp_goto_definition(file=..., line=..., character=...)
  - 找引用:   lsp_find_references(file=..., line=..., character=...)
请改用 LSP 工具，或重新发起同一 Grep 继续（本会话不再阻断）。
EOF

exit 2
