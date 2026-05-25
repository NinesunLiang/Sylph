#!/usr/bin/env bash
# posttool-bash-audit.sh — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计权限上下文，只提醒不阻断
# Role: Bash 执行后审计权限上下文，只提醒不阻断

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "posttool_bash_audit" || { echo '{"continue": true}'; exit 0; }
_ed_val="$(hc_get 'escape_detection' 'true')"; _ed_val="${_ed_val%\\}"
[ "$_ed_val" = "true" ] || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
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
    COMMAND=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('command', data.get('tool_input', {}).get('command', '')))
except:
    pass" 2>/dev/null)
    EXIT_CODE=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('exit_code', ''))
except:
    pass" 2>/dev/null)
    STDERR_OR_STDOUT=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
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
    AUDIT_MSG="Git提交已执行。如未经显式CAPTCHA授权则为门禁绕过事件，请审查。"
elif echo "$COMMAND" | grep -q "git push"; then
    AUDIT_MSG="Git推送已执行。如未经显式CAPTCHA授权则为门禁绕过事件，请审查。"
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
# v3: gate 操作记录在 error-signals.jsonl, 逃逸记录在 error-dna.jsonl — 双源扫描
E4_SCAN_FILES=""
[ -f "$EV_SIGNALS_JSONL" ] && E4_SCAN_FILES="$E4_SCAN_FILES $EV_SIGNALS_JSONL"
[ -f "$EV_DNA_JSONL" ] && E4_SCAN_FILES="$E4_SCAN_FILES $EV_DNA_JSONL"
if [ -n "$E4_SCAN_FILES" ]; then
    ESCAPE_E4_MSG=$(${PYTHON_BIN:-python3} - "$E4_SCAN_FILES" "$COMMAND" <<'E4EOF'
import json, sys, re

scan_list = sys.argv[1].strip().split()
current_cmd = sys.argv[2]

try:
    all_entries = []
    for jsonl_path in scan_list:
        try:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        if rec:
                            all_entries.append(rec)
                    except:
                        pass
        except:
            pass

    recent = sorted(all_entries, key=lambda r: r.get('ts', r.get('timestamp', 0)), reverse=True)[:20]

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
    ESCAPE_E3_MSG=$(${PYTHON_BIN:-python3} - "$_E3_FILE" "$COMMAND" <<'E3EOF'
import json, sys, re

jsonl_path = sys.argv[1]
current_cmd = sys.argv[2]

try:
    recent_entries = []
    with open(jsonl_path, encoding="utf-8") as f:
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
        STREAK=$(${PYTHON_BIN:-python3} -c "import json, os
path = os.environ.get('BUILD_FAIL_FILE', '')
stderr_out = os.environ.get('STDERR_OR_STDOUT', '')
data = {'count': 0, 'signatures': []}
if os.path.exists(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except:
        pass
data['count'] += 1
# Extract first error line as signature
sig = stderr_out[:200].split('\n')[0]
if sig and sig not in data['signatures']:
    data['signatures'].append(sig)
with open(path, 'w', encoding="utf-8") as f:
    json.dump(data, f)
print(data['count'])" 2>/dev/null)

        FAIL_STREAK_THRESHOLD=$(hc_get "posttool_bash_audit.fail_streak_threshold" "2")
        if [ "$STREAK" -ge "$FAIL_STREAK_THRESHOLD" ] 2>/dev/null; then
            # Get number of distinct signatures
            DISTINCT=$(${PYTHON_BIN:-python3} -c "import json, os
data = json.load(open(os.environ.get('BUILD_FAIL_FILE', ''), encoding='utf-8'))
print(len(data.get('signatures', [])))" 2>/dev/null)
            ANTI_PATTERN_MSG="[反模式 C1: 编译错误盲修] 连续 ${STREAK} 次构建失败"
            if [ "$DISTINCT" -gt 1 ] 2>/dev/null; then
                ANTI_PATTERN_MSG="${ANTI_PATTERN_MSG}，且错误签名在变化(${DISTINCT}种不同错误)。建议: 停下来做根因分析(5-Why)，错误可能不在你正在改的地方。"
            else
                ANTI_PATTERN_MSG="${ANTI_PATTERN_MSG}，错误签名相同。建议: 当前修复方向可能正确但实现有误，仔细检查最近的改动。"
            fi

            # E5 Build Fail Gate: 写门禁文件，pretool-retry-check 会读取
            if true; then  # was: hc_enabled "e5_build_fail_gate" — dead key removed, feature always-on
                GATE_FILE="$STATE_DIR/build-fail-gate.json"
                ${PYTHON_BIN:-python3} -c "
import json, os, time
gate = {
    'streak': $STREAK,
    'threshold': $FAIL_STREAK_THRESHOLD,
    'last_fail': time.time(),
    'requires_diagnosis': True
}
with open('$GATE_FILE', 'w', encoding="utf-8") as f:
    json.dump(gate, f, indent=2)
" 2>/dev/null
            fi
        fi
    else
        # Build succeeded, reset streak and clear gate
        rm -f "$BUILD_FAIL_FILE" 2>/dev/null
        rm -f "$STATE_DIR/build-fail-gate.json" 2>/dev/null
    fi
fi

# === Hook-Skill 运行时桥: 检测模式 → 建议对应 skill ===
SKILL_ROUTE_MSG=""
if echo "$AUDIT_MSG" | grep -qE "Git提交|Git推送"; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] Git 操作已执行。建议: /lx-pre-commit 验证提交质量 → /lx-pre-push 推送前门禁"
elif echo "$AUDIT_MSG" | grep -q "递归删除\|rm -rf\|destructive"; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] 危险删除操作。建议: 确认操作范围 → /lx-sync 检查变更后一致性"
elif [ -n "$ESCAPE_E4_MSG" ]; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] 证据编造检测。建议: 运行实际测试 → /lx-test-gen 生成测试 → 重新验证"
elif [ -n "$ESCAPE_E3_MSG" ]; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] 上下文规避检测。建议: /compact 释放上下文 → 重新评估是否需要子 agent"
elif [ -n "$ANTI_PATTERN_MSG" ] && echo "$ANTI_PATTERN_MSG" | grep -q "C1"; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] 编译错误盲修(C1)。建议: /lx-stepwise 逐步攻坚 → 收集全部错误 → 从根错误开始修复"
elif [ -n "$ANTI_PATTERN_MSG" ]; then
    SKILL_ROUTE_MSG="[Hook-Skill桥] 反模式检测。建议: /lx-code-review 审查代码 → 对照 anti-patterns.md 检查"
fi

# Merge all messages and output
COMBINED_MSG=""
[ -n "$AUDIT_MSG" ] && COMBINED_MSG="$AUDIT_MSG"
[ -n "$ANTI_PATTERN_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ANTI_PATTERN_MSG}"
[ -n "$ESCAPE_E4_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ESCAPE_E4_MSG}"
[ -n "$ESCAPE_E3_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${ESCAPE_E3_MSG}"
[ -n "$SKILL_ROUTE_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${SKILL_ROUTE_MSG}"

# ── issue-triage 集成: 发现问题 → 分流（合并为单次 sourcing，减少 Python 子进程开销）──
TRIAGE_MSG=""
# 先收集所有检测到的问题，再统一调用一次 triage
COMBINED_ISSUES=""
[ -n "$ESCAPE_E4_MSG" ] && COMBINED_ISSUES="E4证据编造: $ESCAPE_E4_MSG"
if [ -n "$ANTI_PATTERN_MSG" ] && echo "$ANTI_PATTERN_MSG" | grep -q "C1"; then
    COMBINED_ISSUES="${COMBINED_ISSUES:+${COMBINED_ISSUES}; }C1编译错误盲修: $ANTI_PATTERN_MSG"
fi
[ -n "$ESCAPE_E3_MSG" ] && COMBINED_ISSUES="${COMBINED_ISSUES:+${COMBINED_ISSUES}; }E3上下文规避: $ESCAPE_E3_MSG"
# 取最高优先级：E4=P0 > C1=P1 = E3=P1
TRIAGE_PRIORITY="P1"
if [ -n "$ESCAPE_E4_MSG" ]; then
    TRIAGE_PRIORITY="P0"
fi
if [ -n "$COMBINED_ISSUES" ] && [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
    TRIAGE_MSG=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook "posttool-bash-audit" "$COMBINED_ISSUES" "$TRIAGE_PRIORITY" "{}" 2>/dev/null || echo "")
fi
[ -n "$TRIAGE_MSG" ] && COMBINED_MSG="${COMBINED_MSG:+${COMBINED_MSG} | }${TRIAGE_MSG}"

if [ -z "$COMBINED_MSG" ]; then
    echo '{"continue": true}'
    exit 0
fi

flywheel_event "posttool_bash_audit" "detected" "P2" || true
echo "$COMBINED_MSG" | hc_emit_hook_json "PostToolUse" "true"
exit 0
