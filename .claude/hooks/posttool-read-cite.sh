#!/bin/bash

# harness-kit:managed v1.0.3
# PostToolUse:Read 来源标注提醒 - 读取文件后提示引用规范 [已注册，默认禁用]
# 已在 settings.json PostToolUse:Read 注册。默认关闭（harness.yaml posttool_read_cite: false）。
# 启用：harness.yaml → posttool_read_cite: true

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_read_cite" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

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

if [ -z "$FILE_PATH" ]; then
    echo '{"continue": true}'
    exit 0
fi

BASENAME=$(basename "$FILE_PATH")
MSG=""

# 从配置读取需要引用提醒的扩展名列表
# R24-S3 修复：set -f 禁用 pathname expansion，避免 cwd 有 *.go 时 $CITE_EXTS 被展开为具体文件名
CITE_EXTS=$(hc_get "project.cite_extensions" "*.go *.api")
_CITE_MATCH=false
set -f
for ext in $CITE_EXTS; do
    # shellcheck disable=SC2254  # glob ${ext} is intentional (matches "*.go" as pattern)
    case "$BASENAME" in
        ${ext})
            _CITE_MATCH=true
            MSG="已读取${BASENAME}。引用代码事实时必须标注[已验证: file:line]，禁止凭记忆引用。"
            break
            ;;
    esac
done
set +f

# 特殊文件额外提醒（不依赖扩展名）
case "$BASENAME" in
    PROJECT_MASTER.md)
        _CITE_MATCH=true
        MSG="已读取PROJECT_MASTER.md（唯一权威数据源）。状态机/数据表引用必须标注行号。"
        ;;
    kernel.md|style-guide.md|go-style-guide.md)
        _CITE_MATCH=true
        MSG="已加载代码规范。写代码时遵循此规范。"
        ;;
esac

if [ "$_CITE_MATCH" = false ]; then
    echo '{"continue": true}'
    exit 0
fi

printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$MSG"
exit 0
