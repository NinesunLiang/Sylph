#!/usr/bin/env bash
# pretool-sensitive-file-guard.sh — PreToolUse:Edit|Write — 保护门禁文件不被 AI 直接写入
# Role: 拦截 AI 通过 Edit/Write 工具直接写 permission-approved / permission-required
# 哲学 #6 (0信任): AI 不能自己批准自己的操作

source "$(dirname "$0")/harness_config.sh"
hc_enabled "sensitive_file_guard" || exit 0

INPUT=$(cat)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# 从输入中提取文件路径
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    fp = data.get('file_path', data.get('tool_input', {}).get('file_path', ''))
    print(fp)
except:
    pass
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 检测是否在写敏感文件
BASENAME=$(basename "$FILE_PATH")
case "$BASENAME" in
    permission-approved|permission-required|permission-marker|current-scope.txt|sensitive-approved|sensitive-required|oracle-gate-approved|oracle-gate-required)
        cat >&2 <<EOF

🚫 [Sensitive File Guard] AI 不得直接写入门禁文件！

文件: ${FILE_PATH}
原因: 这是权限门禁的标记文件，只能由 hook 或用户操作写入。
AI 自行写入此文件构成门禁绕过企图。

EOF
        flywheel_event "sensitive_file_guard" "blocked_${BASENAME}" "P0" || true
        printf '[Sensitive File Guard] AI 试图直接写入门禁文件 %s，已阻断。门禁文件只能由 hook 或用户操作修改。' "$BASENAME" | hc_emit_hook_json "PreToolUse" "false"
        exit 2
        ;;
esac

echo '{"continue": true}'
exit 0
