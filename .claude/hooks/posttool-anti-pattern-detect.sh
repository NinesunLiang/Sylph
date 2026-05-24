#!/usr/bin/env bash
# posttool-anti-pattern-detect.sh — PostToolUse:TaskUpdate|Edit|Write — 反模式自动检测
# Role: 根据 .claude/anti-patterns.md 自动检测 A2/F1/H1 反模式输出
# 哲学 #6：先天对 AI 0 信任 — 自动化检测语义层面的反模式
# 哲学 #4：没通过验证等于没做 — A2 虚假完成硬阻断
#
# 阻断策略设计理由 (Oracle 审计 2026-05-15):
#   A2/H1 → hard block (exit 2): 铁律 #1 违反，可机械验证（软完成语 + 无证据 / 百分比 + 无来源）
#   F1  → hard block (exit 2): 铁律 #1 违反，可机械验证（推测词 + 无 file:line）
#   与 E5 RCA (completion-gate.sh:warning-only) 的区别:
#     E5 检测"缺失的流程步骤"(RCA 是否包含)，主观判断 → warning
#     F1 检测"断言缺乏证据支撑"(是否有 file:line)，客观可验证 → hard block
#   一致性原则: 可机械验证的铁律违反 → hard block；需主观判断的流程缺失 → warning

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "anti_pattern_detect" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 模式检测: ghost/goal 模式下记录但不阻断
MODE=$(is_mode_active "$STATE_DIR")
AUTONOMOUS=false
if [ "$MODE" != "normal" ]; then
    AUTONOMOUS=true
fi

# 解析 tool_response.result
if command -v jq &>/dev/null; then
    RESULT=$(echo "$INPUT" | jq -r '.tool_response.result // empty' 2>/dev/null)
else
    RESULT=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_response', {}).get('result', ''))
except:
    pass" 2>/dev/null)
fi

[ -z "$RESULT" ] && { echo '{"continue": true}'; exit 0; }

# ═══════════════════════════════════════════════
# A2: 虚假完成检测 — 软完成语 + 无证据标记
# ═══════════════════════════════════════════════
A2_SOFT_WORDS='应该没问题了|基本完成|大部分通过|should be fine|basically done|mostly complete'
A2_EVIDENCE='\[已验证:|\[已测试:|exit [0-9]|PASS|✅|VERIFIED'

A2_TRIGGERED=false
if echo "$RESULT" | grep -qiE "$A2_SOFT_WORDS"; then
    if ! echo "$RESULT" | grep -qE "$A2_EVIDENCE"; then
        A2_TRIGGERED=true
    fi
fi

# ═══════════════════════════════════════════════
# F1: 假设驱动检测 — 推测性断言 + 无 file:line 证据
# ═══════════════════════════════════════════════
F1_HEDGE='应该是|通常是|一般来说|probably|seems to|I think|按理说|一般情况下'
F1_EVIDENCE='\[已验证:|\[已测试:'

F1_TRIGGERED=false
if echo "$RESULT" | grep -qiE "$F1_HEDGE"; then
    if ! echo "$RESULT" | grep -qE "$F1_EVIDENCE"; then
        F1_TRIGGERED=true
    fi
fi

# ═══════════════════════════════════════════════
# H1: 语义编造检测 — 百分比/评分 + 无来源
# ═══════════════════════════════════════════════
H1_SCORE='[0-9]+(\.[0-9]+)?%|评分\s*[0-9]+\s*/\s*[0-9]+|得分\s*[0-9]+(\.[0-9]+)?|throughput [0-9]+|accuracy [0-9]+'
H1_SOURCE='(https?://[^\s\)]+|file:line|\[已验证:|\[已测试:|source:|来源:|ref:)'

H1_TRIGGERED=false
if echo "$RESULT" | grep -qiE "$H1_SCORE"; then
    if ! echo "$RESULT" | grep -qiE "$H1_SOURCE"; then
        H1_TRIGGERED=true
    fi
fi

# ═══════════════════════════════════════════════
# 输出响应
# ═══════════════════════════════════════════════

# A2 or H1 → 硬阻断 (exit 2)，自主模式下降级为记录+放行
if [ "$A2_TRIGGERED" = true ] || [ "$H1_TRIGGERED" = true ]; then
    VIOLATION_LOG="$STATE_DIR/ghost-violations.jsonl"
    echo "⛔ [反模式检测] 检测到反模式输出:" >&2
    if [ "$A2_TRIGGERED" = true ]; then
        echo "  🚫 A2 虚假完成: 检测到软完成语（应该没问题了/基本完成/大部分通过），缺少结构化证据标记" >&2
    fi
    if [ "$H1_TRIGGERED" = true ]; then
        echo "  🚫 H1 语义编造: 检测到无来源的百分比/评分指标" >&2
    fi
    if [ "$AUTONOMOUS" = true ]; then
        echo "[$MODE] A2/H1 反模式已记录（自主模式不阻断）" >&2
        ${PYTHON_BIN:-python3} -c "import json,time;open('$VIOLATION_LOG','a').write(json.dumps({'ts':int(time.time()),'type':'A2_H1','mode':'$MODE','result':'$(echo "$RESULT" | head -c 200 | sed 's/"/\\\\"/g')'})+'\n')" 2>/dev/null
        flywheel_event "anti_pattern_detect" "recorded_autonomous" "P2" || true
        echo '{"continue": true}'
        exit 0
    fi
    echo '{"continue": false}' >&2
    flywheel_event "anti_pattern_detect" "blocked" "P2" || true
    exit 2
fi

# F1 单独触发 → 硬阻断 (exit 2)，自主模式下降级为记录+放行
if [ "$F1_TRIGGERED" = true ]; then
    echo "⛔ [反模式检测] 检测到假设驱动断言:" >&2
    echo "  🚫 F1 假设驱动: 检测到推测性断言「应该是/通常是/一般来说」缺少 file:line 证据" >&2
    if [ "$AUTONOMOUS" = true ]; then
        echo "[$MODE] F1 反模式已记录（自主模式不阻断）" >&2
        VIOLATION_LOG="$STATE_DIR/ghost-violations.jsonl"
        ${PYTHON_BIN:-python3} -c "import json,time;open('$VIOLATION_LOG','a').write(json.dumps({'ts':int(time.time()),'type':'F1','mode':'$MODE'})+'\n')" 2>/dev/null
        flywheel_event "anti_pattern_detect" "recorded_autonomous" "P2" || true
        echo '{"continue": true}'
        exit 0
    fi
    echo '{"continue": false}' >&2
    flywheel_event "anti_pattern_detect" "blocked" "P2" || true
    exit 2
fi

echo '{"continue": true}'
exit 0
