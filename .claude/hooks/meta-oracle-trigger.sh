#!/usr/bin/env bash
# meta-oracle-trigger.sh — PostToolUse:.* — Oracle ACCEPT/高分时自动触发 Meta-Oracle 二审提醒
# Role: 检测 Oracle 审查输出中的 ACCEPT/高分模式，提醒 AI 执行 Meta-Oracle 独立验证
# 哲学 #4(没验证=没做) + #6(0信任): Oracle 的结论需要被独立验证

source "$(dirname "$0")/harness_config.sh"
hc_enabled "meta_oracle_trigger" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 提取工具名和输出内容
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // .tool_response.stdout // .tool_response.content // empty' 2>/dev/null)
    # Agent 返回的 text 也在 content 中
    AGENT_TEXT=$(echo "$INPUT" | jq -r '.tool_response.message // .tool_response.text // empty' 2>/dev/null)
    COMBINED="${TOOL_OUTPUT} ${AGENT_TEXT}"
else
    TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
    COMBINED=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); tr=d.get('tool_response',{}); print(tr.get('stdout',tr.get('content',tr.get('message',''))))" 2>/dev/null)
fi

[ -z "$COMBINED" ] && { echo '{"continue": true}'; exit 0; }

# Meta-Oracle 触发模式检测
# 模式1: Oracle 明确给出 ACCEPT / APPROVED 裁决
# 模式2: Oracle 给出高分 (≥8.5)
# 模式3: Oracle audit report 中的 "PASS" 或 "通过"
TRIGGERED=false
TRIGGER_REASON=""

# 检测 Oracle ACCEPT/APPROVED
if echo "$COMBINED" | grep -qE '(Oracle|oracle).*(ACCEPT|APPROVED|approve|accept)' 2>/dev/null; then
    TRIGGERED=true
    TRIGGER_REASON="Oracle ACCEPT/APPROVED 裁决检测"
fi

# 检测高分评分 (≥8.5)
if [ "$TRIGGERED" = false ]; then
    HIGH_SCORE=$(echo "$COMBINED" | grep -oE '(score|Score|评分|得分)[:： ]*[0-9]+\.[0-9]+' 2>/dev/null | head -3)
    if [ -n "$HIGH_SCORE" ]; then
        MAX_SCORE=$(echo "$HIGH_SCORE" | grep -oE '[0-9]+\.[0-9]+' | sort -rn | head -1)
        if [ -n "$MAX_SCORE" ] && python3 -c "exit(0 if float('$MAX_SCORE') >= 8.5 else 1)" 2>/dev/null; then
            TRIGGERED=true
            TRIGGER_REASON="Oracle 高分评分 (${MAX_SCORE} ≥ 8.5)"
        fi
    fi
fi

# 检测 "综合评分" 或 "总分" ≥ 8.5
if [ "$TRIGGERED" = false ]; then
    OVERALL_SCORE=$(echo "$COMBINED" | grep -oE '(综合|总分|平均|overall)[:： ]*[0-9]+\.[0-9]+' 2>/dev/null | head -3)
    if [ -n "$OVERALL_SCORE" ]; then
        MAX_OS=$(echo "$OVERALL_SCORE" | grep -oE '[0-9]+\.[0-9]+' | sort -rn | head -1)
        if [ -n "$MAX_OS" ] && python3 -c "exit(0 if float('$MAX_OS') >= 8.5 else 1)" 2>/dev/null; then
            TRIGGERED=true
            TRIGGER_REASON="综合评分 ≥ 8.5 (${MAX_OS})"
        fi
    fi
fi

# 输出 Meta-Oracle 触发提醒
if [ "$TRIGGERED" = true ]; then
    printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"🔍 [Meta-Oracle 触发] %s\n独立于 Oracle 的第二审查者。请执行 Meta-Oracle 验证:\n1. Oracle 评分方法论是否合理（有无系统性虚高/虚低）\n2. 关键发现是否经运行时验证（而非仅静态检查）\n3. 是否有遗漏的盲区（Oracle 视角的偏见）\n→ 使用不同的审查方法（运行时验证 > 静态检查，烟雾日志 > 文件存在性）\n→ 如发现虚高，产出 Meta-Oracle 纠正报告"}}\n' "$TRIGGER_REASON"
    echo "[meta-oracle] ${TRIGGER_REASON} — Meta-Oracle 二审提醒已注入" >&2
    exit 0
fi

echo '{"continue": true}'
exit 0
