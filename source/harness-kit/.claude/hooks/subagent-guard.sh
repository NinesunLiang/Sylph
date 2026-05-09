#!/bin/bash
# subagent-guard.sh — PreToolUse:Task — 约束子 agent 用量，防账单雪崩（软约束+事后对账）
# Role: 约束子 agent 用量，防账单雪崩（软约束+事后对账）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "subagent_guard" || exit 0
INPUT=$(cat)

# R25: Task 工具 schema 没有 max_turns 字段，AI 无法在 tool_input 合法传入。
# 产品策略：危险 agent 有默认上限（可配置，默认 20）；prompt/description 里的 max_turns=N 声明优先。
DEFAULT_MAX_TURNS=$(hc_get "subagent_guard.default_max_turns" "20")

# 提取字段（jq 优先，python3 fallback）
if command -v jq &>/dev/null; then
    AGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
    # 优先级：1) tool_input.max_turns (未来若 schema 支持) 2) description/prompt 里 max_turns=N 3) 默认值
    MAX_TURNS=$(echo "$INPUT" | jq -r '.tool_input.max_turns // empty' 2>/dev/null)
    if [ -z "$MAX_TURNS" ] || [ "$MAX_TURNS" = "null" ]; then
        COMBINED=$(echo "$INPUT" | jq -r '((.tool_input.description // "") + " " + (.tool_input.prompt // ""))' 2>/dev/null)
        MAX_TURNS=$(echo "$COMBINED" | grep -oE 'max_turns[[:space:]]*[=:][[:space:]]*[0-9]+' | head -1 | grep -oE '[0-9]+' | head -1)
    fi
    EFFECTIVE_SOURCE="explicit"
    if [ -z "$MAX_TURNS" ]; then
        MAX_TURNS="$DEFAULT_MAX_TURNS"
        EFFECTIVE_SOURCE="default"
    fi
else
    AGENT_TYPE=""
    MAX_TURNS=""
    EFFECTIVE_SOURCE=""
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    STATE_DIR="$PROJECT_ROOT/.omc/state"
    mkdir -p "$STATE_DIR" 2>/dev/null
    TMPFILE=$(mktemp "${STATE_DIR}/subagent-guard-XXXXXX")
    echo "$INPUT" | python3 -c "
import sys, json, re, os
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    at = str(ti.get('subagent_type', ''))
    mt = str(ti.get('max_turns', ''))
    src = 'explicit'
    if not mt or mt == 'None':
        text = str(ti.get('description', '')) + ' ' + str(ti.get('prompt', ''))
        m = re.search(r'max_turns[\s]*[=:][\s]*(\d+)', text)
        if m:
            mt = m.group(1)
    if not mt:
        mt = os.environ.get('DEFAULT_MAX_TURNS', '20')
        src = 'default'
    at = re.sub(r'[^a-zA-Z0-9_:\-]', '', at)
    mt = re.sub(r'[^0-9]', '', mt)
    print(f'AGENT_TYPE={json.dumps(at)}')
    print(f'MAX_TURNS={json.dumps(mt)}')
    print(f'EFFECTIVE_SOURCE={json.dumps(src)}')
except:
    print('AGENT_TYPE=\"\"')
    print(f'MAX_TURNS={json.dumps(os.environ.get(\"DEFAULT_MAX_TURNS\", \"20\"))}')
    print('EFFECTIVE_SOURCE=\"default\"')" > "$TMPFILE" 2>/dev/null
    source "$TMPFILE"
    rm -f "$TMPFILE"
fi

# Fail-open: 无法解析 agent 类型 → 放行
if [ -z "$AGENT_TYPE" ]; then
    exit 0
fi

# 判断是否为危险类型（从配置读取危险关键词列表）
DANGEROUS_TYPES=$(hc_get "subagent_guard.dangerous_types" "executor designer scientist")
IS_DANGEROUS=false
for dtype in $DANGEROUS_TYPES; do
    case "$AGENT_TYPE" in
        *${dtype}*) IS_DANGEROUS=true; break ;;
    esac
done

# 安全类型 → 放行
if [ "$IS_DANGEROUS" = "false" ]; then
    exit 0
fi

# 危险类型 + 有 max_turns（非空、非 null、非 0）→ 放行
# 默认兜底: 即使 AI 未声明也会用 DEFAULT_MAX_TURNS 放行（见文件头逻辑）
if [ -n "$MAX_TURNS" ] && [ "$MAX_TURNS" != "null" ] && [ "$MAX_TURNS" != "0" ]; then
    if [ "$EFFECTIVE_SOURCE" = "default" ]; then
        # 走默认值，以 additionalContext 提醒（不阻断）
        printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "[Subagent Guard] %s 未显式声明 max_turns，已使用默认上限 %s 轮。如需其他上限请在 description/prompt 写 max_turns=N。"}}\n' "$AGENT_TYPE" "$MAX_TURNS"
    fi
    exit 0
fi

# 兜底阻断：MAX_TURNS 为 0 / null 的异常情况
cat >&2 <<EOF
[Subagent Guard] 子 agent "$AGENT_TYPE" 的 max_turns 无效 (value=$MAX_TURNS)。
建议: executor ≤25, designer ≤20, scientist ≤15
  在 description/prompt 声明 max_turns=N 覆盖默认值 $DEFAULT_MAX_TURNS
EOF
exit 2
