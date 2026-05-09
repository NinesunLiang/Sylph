#!/bin/bash
# posttool-bash-audit.sh — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计权限上下文，只提醒不阻断
# Role: Bash 执行后审计权限上下文，只提醒不阻断

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_bash_audit" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // empty' 2>/dev/null)
    STDERR_OR_STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stderr // .tool_response.stdout // empty' 2>/dev/null | head -c 500)
    # PostToolUseFailure fallback: top-level `error`, no tool_response
    EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)
    TOP_ERROR=$(echo "$INPUT" | jq -r '.error // empty' 2>/dev/null | head -c 500)
    if [ "$EVENT" = "PostToolUseFailure" ]; then
        [ -z "$EXIT_CODE" ] && EXIT_CODE="1"
        [ -z "$STDERR_OR_STDOUT" ] && STDERR_OR_STDOUT="$TOP_ERROR"
    fi
else
    COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    pass" 2>/dev/null)
    EXIT_CODE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('exit_code', ''))
except:
    pass" 2>/dev/null)
    STDERR_OR_STDOUT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    r = data.get('tool_response', {})
    print(r.get('stderr') or r.get('stdout') or '')
except:
    pass" 2>/dev/null | head -c 500)
fi

if [ -z "$COMMAND" ]; then
    echo '{"continue": true}'
    exit 0
fi

AUDIT_MSG=""
if echo "$COMMAND" | grep -q "git commit"; then
    AUDIT_MSG="Git提交已执行。确认: 编译验证通过 + 用户已批准(§1.4)"
elif echo "$COMMAND" | grep -q "git push"; then
    AUDIT_MSG="Git推送已执行。确认: 用户已明确批准推送操作"
elif echo "$COMMAND" | grep -q "git reset --hard"; then
    AUDIT_MSG="⚠️ 硬重置已执行。请确认操作符合用户指令"
elif echo "$COMMAND" | grep -qE "rm -rf|rm -r"; then
    AUDIT_MSG="⚠️ 递归删除已执行。请确认操作范围正确"
elif echo "$COMMAND" | grep -qE "^pkill|^kill| pkill | kill "; then
    AUDIT_MSG="进程信号已发送。确认目标进程正确"
fi

# === C1 反模式检测: 编译错误盲修 ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
BUILD_FAIL_FILE="$STATE_DIR/build-fail-streak.json"
ANTI_PATTERN_MSG=""

# Check if this is a build command
if echo "$COMMAND" | grep -qE "go build|go test|npm run build|npm test|cargo build"; then
    if [ "$EXIT_CODE" != "0" ]; then
        # Record failure
        mkdir -p "$STATE_DIR" 2>/dev/null
        export STDERR_OR_STDOUT
        export BUILD_FAIL_FILE
        STREAK=$(python3 -c "import json, os
path = os.environ.get('BUILD_FAIL_FILE', '')
stderr_out = os.environ.get('STDERR_OR_STDOUT', '')
data = {'count': 0, 'signatures': []}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except:
        pass
data['count'] += 1
# Extract first error line as signature
sig = stderr_out[:200].split('\n')[0]
if sig and sig not in data['signatures']:
    data['signatures'].append(sig)
with open(path, 'w') as f:
    json.dump(data, f)
print(data['count'])" 2>/dev/null)

        FAIL_STREAK_THRESHOLD=$(hc_get "posttool_bash_audit.fail_streak_threshold" "3")
        if [ "$STREAK" -ge "$FAIL_STREAK_THRESHOLD" ] 2>/dev/null; then
            # Get number of distinct signatures
            DISTINCT=$(python3 -c "import json, os
data = json.load(open(os.environ.get('BUILD_FAIL_FILE', '')))
print(len(data.get('signatures', [])))" 2>/dev/null)
            ANTI_PATTERN_MSG="[反模式 C1: 编译错误盲修] 连续 ${STREAK} 次构建失败"
            if [ "$DISTINCT" -gt 1 ] 2>/dev/null; then
                ANTI_PATTERN_MSG="${ANTI_PATTERN_MSG}，且错误签名在变化(${DISTINCT}种不同错误)。建议: 停下来做根因分析(5-Why)，错误可能不在你正在改的地方。"
            else
                ANTI_PATTERN_MSG="${ANTI_PATTERN_MSG}，错误签名相同。建议: 当前修复方向可能正确但实现有误，仔细检查最近的改动。"
            fi
        fi
    else
        # Build succeeded, reset streak
        rm -f "$BUILD_FAIL_FILE" 2>/dev/null
    fi
fi

# Merge messages and output
COMBINED_MSG=""
[ -n "$AUDIT_MSG" ] && COMBINED_MSG="$AUDIT_MSG"
if [ -n "$ANTI_PATTERN_MSG" ]; then
    [ -n "$COMBINED_MSG" ] && COMBINED_MSG="${COMBINED_MSG} | ${ANTI_PATTERN_MSG}" || COMBINED_MSG="$ANTI_PATTERN_MSG"
fi

if [ -z "$COMBINED_MSG" ]; then
    echo '{"continue": true}'
    exit 0
fi

printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$COMBINED_MSG"
exit 0
