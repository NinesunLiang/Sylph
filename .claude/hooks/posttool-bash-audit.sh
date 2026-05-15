#!/usr/bin/env bash
# posttool-bash-audit.sh — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计权限上下文，只提醒不阻断
# Role: Bash 执行后审计权限上下文，只提醒不阻断

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_bash_audit" || { echo '{"continue": true}'; exit 0; }
_ed_val="$(hc_get 'escape_detection' 'true')"; _ed_val="${_ed_val%\\}"
[ "$_ed_val" = "true" ] || { echo '{"continue": true}'; exit 0; }

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

# === Escape Pattern E4: Evidence fabrication detection ===
# Pattern: completion-gate blocks recorded → AI echo "VERIFIED" to evidence file → TaskUpdate(completed)
# Signal: gate blocks in recent jsonl + current command writes evidence + no build/test commands in between
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
EV_DNA_JSONL="$STATE_DIR/error-dna.jsonl"
EV_SIGNALS_JSONL="$STATE_DIR/error-signals.jsonl"
ESCAPE_E4_MSG=""
if [ -f "$EV_DNA_JSONL" ]; then
    ESCAPE_E4_MSG=$(python3 - "$EV_DNA_JSONL" "$COMMAND" <<'E4EOF'
import json, sys, re

jsonl_path = sys.argv[1]
current_cmd = sys.argv[2]

try:
    recent_entries = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                if rec:
                    recent_entries.append(rec)
            except:
                pass

    recent = recent_entries[-20:]

    # Detect: completion-gate block recorded
    gate_blocks = [r for r in recent
                   if r.get('error_type') == 'gate_operation'
                   and ('completion' in r.get('message', '').lower()
                        or 'evidence' in r.get('message', '').lower())]

    # Detect: current command is creating/writing evidence file
    is_evidence_write = bool(re.search(
        r'VERIFIED|completion-evidence|\.completion-evidence|echo.*VERIFIED|echo.*PASS',
        current_cmd))

    # Detect: build/test commands in recent entries
    build_cmds = [r for r in recent
                  if r.get('error_type') in ('build', 'test')
                  or any(x in r.get('cmd', '') for x in ['go build', 'go test', 'npm test', 'cargo build'])]

    if len(gate_blocks) >= 1 and is_evidence_write and len(build_cmds) == 0:
        print(f"[E4] 可能证据编造: completion-gate 最近阻断({len(gate_blocks)}次)，当前命令写入证据文件，但最近{len(recent)}条记录中无编译/测试命令。")
        print(f"  建议: 验证 AI 实际执行了测试，而非仅 echo VERIFIED 伪造完成证据。")
    else:
        print("")
except Exception:
    print("")
E4EOF
)
fi

# === Escape Pattern E3: Context evasion via subagent ===
# Pattern: context-guard blocks (high context) → immediate Task subagent creation
ESCAPE_E3_MSG=""
# 优先扫描 error-signals.jsonl（context-guard 阻断记录主源），备选 error-dna.jsonl
_E3_FILE=""
[ -f "$EV_SIGNALS_JSONL" ] && _E3_FILE="$EV_SIGNALS_JSONL" || { [ -f "$EV_DNA_JSONL" ] && _E3_FILE="$EV_DNA_JSONL"; }
if [ -n "$_E3_FILE" ]; then
    ESCAPE_E3_MSG=$(python3 - "$_E3_FILE" "$COMMAND" <<'E3EOF'
import json, sys, re

jsonl_path = sys.argv[1]
current_cmd = sys.argv[2]

try:
    recent_entries = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                if rec:
                    recent_entries.append(rec)
            except:
                pass

    recent = recent_entries[-10:]

    # Check for context-guard blocks in recent history
    ctx_blocks = [r for r in recent
                  if ('context' in r.get('message', '').lower()
                      or 'context' in r.get('error_type', '').lower())
                  and ('guard' in r.get('message', '').lower()
                       or 'guard' in r.get('cmd', '').lower())]

    # Detect if current command is creating a subagent (Task tool via Bash)
    is_subagent = bool(re.search(
        r'task.*(create|execute|run|spawn)|subagent|sub_agent|start_agent|delegate',
        current_cmd, re.IGNORECASE))

    if len(ctx_blocks) >= 1 and is_subagent:
        print(f"[E3] 可能的上下文规避: context-guard 最近阻断({len(ctx_blocks)}次)后立即创建子 agent。")
        print(f"  建议: 检查 AI 是否通过子 agent 绕过上下文限制。")
    else:
        print("")
except Exception:
    print("")
E3EOF
)
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

# Merge all messages and output
COMBINED_MSG=""
[ -n "$AUDIT_MSG" ] && COMBINED_MSG="$AUDIT_MSG"
[ -n "$ANTI_PATTERN_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ANTI_PATTERN_MSG}"
[ -n "$ESCAPE_E4_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ESCAPE_E4_MSG}"
[ -n "$ESCAPE_E3_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ESCAPE_E3_MSG}"

if [ -z "$COMBINED_MSG" ]; then
    echo '{"continue": true}'
    exit 0
fi

printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$COMBINED_MSG"
exit 0
