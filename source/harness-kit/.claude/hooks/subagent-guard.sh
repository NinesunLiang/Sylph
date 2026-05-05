#!/bin/bash

# harness-kit:managed v1.0.2

# subagent-guard.sh — PreToolUse:Task Hook

# 功能：对高资源消耗类型子 agent 强制要求 max_turns 参数

# 退出码 2 = 阻断（危险 agent 缺少 max_turns）

# 退出码 0 = 放行（安全 agent / 已设 max_turns / fail-open）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "subagent_guard" || exit 0
INPUT=$(cat)

# 提取字段（jq 优先，python3 fallback）
if command -v jq &>/dev/null; then
    AGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
    MAX_TURNS=$(echo "$INPUT" | jq -r '.tool_input.max_turns // empty' 2>/dev/null)
else
    AGENT_TYPE=""
    MAX_TURNS=""
    eval "$(echo "$INPUT" | python3 -c "
import sys, json, re
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    at = str(ti.get('subagent_type', ''))
    mt = str(ti.get('max_turns', ''))
    at = re.sub(r'[^a-zA-Z0-9_:\-]', '', at)
    mt = re.sub(r'[^0-9]', '', mt)
    print(f'AGENT_TYPE=\"{at}\"')
    print(f'MAX_TURNS=\"{mt}\"')
except:
    print('AGENT_TYPE=\"\"')
    print('MAX_TURNS=\"\"')" 2>/dev/null)"
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
if [ -n "$MAX_TURNS" ] && [ "$MAX_TURNS" != "null" ] && [ "$MAX_TURNS" != "0" ]; then
    exit 0
fi

# 阻断：危险 agent 缺少 max_turns
cat >&2 <<EOF
[Subagent Guard] 子 agent "$AGENT_TYPE" 属于高资源消耗类型，必须设置 max_turns。
强制流程: 在 Task 调用中添加 max_turns 参数（建议值: executor ≤25, designer ≤20, scientist ≤15）
 示例: Task(subagent_type="$AGENT_TYPE", max_turns=25, ...)
EOF
exit 2
