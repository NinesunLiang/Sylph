#!/bin/bash
# posttool-write-cite.sh — PostToolUse:Write|Edit — 检测写入 claude-next.md 时验证教训格式
# Role: 检测写入 claude-next.md 时验证教训格式

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_write_cite" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

# 提取 file_path
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    pass" 2>/dev/null)
fi

[ -z "$FILE_PATH" ] && echo '{"continue": true}' && exit 0

# 只关心 claude-next.md
BASENAME=$(basename "$FILE_PATH")
[ "$BASENAME" != "claude-next.md" ] && echo '{"continue": true}' && exit 0

# 读取写入内容
if command -v jq &>/dev/null; then
    NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_content // empty' 2>/dev/null)
else
    NEW_CONTENT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('new_content', ''))
except:
    pass" 2>/dev/null)
fi

[ -z "$NEW_CONTENT" ] && echo '{"continue": true}' && exit 0

# ─── 格式验证 ─────────────────────────────────────────────────────
ISSUES=""
TODAY=$(date +%Y-%m-%d)

# 检查最近添加的教训（找最后一个 ## [...] 条目）
LAST_ENTRY=$(echo "$NEW_CONTENT" | grep -E "^## \\[" | tail -1)
if [ -z "$LAST_ENTRY" ]; then
    ISSUES="$ISSUES\n ⚠️ 未找到标准教训标题格式（## [YYYY-MM-DD] {教训标题}）"
else
    # 检查日期格式
    if ! echo "$LAST_ENTRY" | grep -qE "^## \\[[0-9]{4}-[0-9]{2}-[0-9]{2}\]"; then
        ISSUES="$ISSUES\n ⚠️ 标题日期格式错误（应为 [YYYY-MM-DD]）"
    fi
    # 检查标题非空
    TITLE=$(echo "$LAST_ENTRY" | sed 's/^## \[[^]]*\] *//')
    if [ -z "$TITLE" ] || [ "$TITLE" = "{教训标题}" ]; then
        ISSUES="$ISSUES\n ⚠️ 教训标题为空或是占位符"
    fi
fi

# 检查三个必填字段
for FIELD in "**问题**" "**根因**" "**纠正**"; do
    echo "$NEW_CONTENT" | grep -qF "$FIELD" ||
        ISSUES="$ISSUES\n ⚠️ 缺少字段 $FIELD"
done

# 检查内容非占位符
if echo "$NEW_CONTENT" | grep -qE "\{描述[^}]*\}|\{为什么[^}]*\}|\{正确做法[^}]*\}"; then
    ISSUES="$ISSUES\n ⚠️ 内容含未填充占位符（{...}）"
fi

# ─── 输出结果 ─────────────────────────────────────────────────────
if [ -z "$ISSUES" ]; then
    MSG="✅ claude-next.md 教训格式合规。升华检查：已记录，未来达到 20 条时可升华到 kernel.md。"
    printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$MSG"
else
    ISSUE_LIST=$(printf "%b" "$ISSUES")
    MSG="⚠️ claude-next.md 格式问题，建议修正：${ISSUE_LIST}\n\n标准格式：\n## [${TODAY}] {教训标题}\n<!-- @${TODAY} hits:1 -->\n**问题**：{描述}\n**根因**：{为什么}\n**纠正**：{正确做法}"
    # 转义 JSON
    MSG_ESC=$(echo "$MSG" | python3 -c "
import sys
s = sys.stdin.read()
print(s.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"').replace('\n', '\\\\\\n'))" 2>/dev/null || echo "$MSG")
    printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$MSG_ESC"
fi

exit 0
