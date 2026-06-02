#!/usr/bin/env bash
# pretool-terminal-safety.sh — PreToolUse:Bash — 终端命令格式校验
# 永不阻断 (exit 0) 但超长命令(>2000字符)除外 — 告警+flywheel, >2000字符硬阻断
# Meta-Oracle ACCEPT: terminal-safety.md规则有但无强制, 低成本补缺口

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "pretool_terminal_safety" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat 2>/dev/null || echo "")
CMD=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
fi
[ -z "$CMD" ] && { echo '{"continue": true}'; exit 0; }

WARNINGS=""

# Rule 1: python3 -c with complex code (建议heredoc)
if echo "$CMD" | grep -q "${PYTHON_BIN:-python3} -c" && [ ${#CMD} -gt 100 ]; then
    WARNINGS="${WARNINGS}
[terminal-safety] ${PYTHON_BIN:-python3} -c过长(${#CMD}字符) → 建议用 ${PYTHON_BIN:-python3} << 'PY' heredoc"
fi

# Rule 2: git chain (git .*&&.*git)
if echo "$CMD" | grep -qE 'git\s+.*&&.*git'; then
    WARNINGS="${WARNINGS}
[terminal-safety] git链式操作 → 建议拆分: git add / git commit / git push 各一行"
fi

# Rule 4: git commit with #
if echo "$CMD" | grep -qE 'git\s+commit.*#\s*[0-9]'; then
    WARNINGS="${WARNINGS}
[terminal-safety] git commit含# → 可能被截断, 改用中文冒号或括号"
fi

# Rule 6: long python3 -c (>120 chars = terminal truncation risk) → WARNING only
# 哲学 #6(0信任): 终端宽度截断导致语法错误是已知事故 (DG-13, DG-22)
# 降级为警告而非硬阻断 — python3 heredocs 可长但不应阻断合法操作
if echo "$CMD" | grep -qE '${PYTHON_BIN:-python3} -c|python -c' && [ ${#CMD} -gt 120 ]; then
    WARNINGS="${WARNINGS}
[terminal-safety] ${PYTHON_BIN:-python3} -c过长(${#CMD}字符) → 建议用 ${PYTHON_BIN:-python3} << 'PY' heredoc 或 Write 脚本文件"
fi

# Rule 6b: any command > max_command_length chars → HARD BLOCK
MAX_CMD_LEN=$(hc_get "terminal_safety.max_command_length" "2000")
if [ ${#CMD} -gt "$MAX_CMD_LEN" ]; then
    SCRIPT_NAME="scripts/task-$(date +%Y%m%d-%H%M%S).sh"
    echo "🛑 [terminal-safety·Rule6] 命令超过${MAX_CMD_LEN}字符 (${#CMD}字符) — 不可复制执行" >&2
    echo "   AI 必须用 Write 创建: ${SCRIPT_NAME}" >&2
    flywheel_event "pretool_terminal_safety" "blocked_long_command" "P1" "len=${#CMD}" || true
    echo '{"continue": true, "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "[terminal-safety·Rule6] 命令过长('${#CMD}'字符)，请用 Write 创建脚本文件。"}}'
    exit 2
fi

# Rule 3: path pile-up
PATH_COUNT=$(echo "$CMD" | grep -oE '[^ ]+\.(go|py|ts|js|sh|yaml|json|md|rs|rb|java|css|html|toml)' 2>/dev/null | wc -l | tr -d ' ')
if [ "${PATH_COUNT:-0}" -gt 8 ]; then
    WARNINGS="${WARNINGS}
[terminal-safety] 路径堆砌(${PATH_COUNT}个文件) → 建议每行一个文件"
fi

if [ -n "$WARNINGS" ]; then
    echo "$WARNINGS" >&2
    flywheel_event "pretool_terminal_safety" "warned" "P2" "patterns=$(echo "$WARNINGS" | wc -l | tr -d ' ')" || true
fi

echo '{"continue": true}'
exit 0
