#!/usr/bin/env bash
# posttool-claim-audit.sh — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验
# 检测 AI 对文件内容的断言（file:line 引用）是否基于真实读取
# Role: 铁律 #1 enforce — AI 不能编造没读过的代码事实

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_claim_audit" || exit 0

INPUT=$(cat)
TOOL_NAME="$1"

# 仅审计 Edit/Write — AI 输出代码断言的主要出口
case "$TOOL_NAME" in
    Edit|Write) ;;
    *) exit 0 ;;
esac

# 提取 file_path（工具输入）
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

# 无路径 → 放行（避免误杀）
[ -z "$FILE_PATH" ] && exit 0

# 提取文件绝对路径用于 read-tracker 比对
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-tracker.txt"

# 提取所有 file:line 引用（如 kernel.go:42, .claude/hooks/plan-gate.sh:15）
CLAIMED_FILES=$(echo "$INPUT" | grep -oE '\./?[\w./-]+\.[a-z]+:[0-9]+' | sed 's|^\./||' || true)
if [ -z "$CLAIMED_FILES" ]; then
    exit 0
fi

# 读取 read-tracker（可能跨轮次累积）
read_files=""
if [ -f "$READ_LOG" ]; then
    read_files=$(cat "$READ_LOG")
fi

# 检测 claim 文件是否在 read-tracker 中
CLAIMED_BASENAMES=$(echo "$CLAIMED_FILES" | sed 's|:.*||' | xargs -I{} basename {} 2>/dev/null | sort -u || true)
CLAIMED_DIRS=$(echo "$CLAIMED_FILES" | sed 's|:.*||' | xargs -I{} dirname {} 2>/dev/null | sort -u || true)

VIOLATIONS=""
while IFS= read -r claimed; do
    [ -z "$claimed" ] && continue

    # 检查1: read-tracker 中有完整路径匹配
    if echo "$read_files" | grep -qxF "$(realpath "./$claimed" 2>/dev/null || echo "$claimed")"; then
        continue
    fi

    # 检查2: basename 匹配（同一文件被多次 Read）
    if echo "$read_files" | grep -qF "/$(basename "$claimed")"; then
        continue
    fi

    # 检查3: dirname 下有同名文件被 Read（包级引用）
    for dir in $CLAIMED_DIRS; do
        if echo "$read_files" | grep -qF "$dir/$(basename "$claimed")"; then
            continue 2
        fi
    done

    VIOLATIONS="${VIOLATIONS}⚠️ IRRELEVANT_CLAIM: ${claimed}\n"
done <<< "$CLAIMED_FILES"

if [ -n "$VIOLATIONS" ]; then
    printf '{"continue": true, "hookSpecificOutput": {"additionalContext": "⛔ [铁律#1] 以下代码引用无读取证据（AI 不得编造未读内容）:\n'"$VIOLATIONS"'宪法: "禁止编造" — 必须引用 file:line，找不到则 BLOCKED\n请确认以上文件已被 Read。如未读请先执行 Read 再编辑。"}}\n'
    exit 2
fi

exit 0
