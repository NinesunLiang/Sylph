#!/bin/bash

# harness-kit:managed v1.0.2

# completion-gate.sh — PreToolUse:TaskUpdate Hook

# 功能：当 AI 尝试将任务标记为 completed 时，强制阻断并要求提供证据

# 退出码 2 = 阻断工具执行（Claude Code 硬阻断，AI 无法绕过）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "completion_gate" || exit 0
INPUT=$(cat)

# 提取 status 字段
if command -v jq &>/dev/null; then
    STATUS=$(echo "$INPUT" | jq -r '.tool_input.status // empty' 2>/dev/null)
else
    STATUS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('status', ''))
except:
    pass" 2>/dev/null)
fi

# 非 completed 状态 → 放行
if [ "$STATUS" != "completed" ]; then
    exit 0
fi

# 检查证据文件是否存在（AI 必须先运行验证并写入证据文件才能标记完成）
EVIDENCE_FILE="/tmp/.completion-evidence-$(date +%Y%m%d)"
if [ -f "$EVIDENCE_FILE" ]; then
    # 证据文件存在，检查是否在 5 分钟内写入
    if command -v python3 &>/dev/null; then
        FRESH=$(python3 -c "import os, time
try:
    age = time.time() - os.path.getmtime('$EVIDENCE_FILE')
    print('yes' if age < 300 else 'no')
except:
    print('no')" 2>/dev/null)
    else
        FRESH="yes"
    fi
    if [ "$FRESH" = "yes" ]; then
        # 证据内容验证：必须包含至少 20 字符实际描述 + VERIFIED 关键字
        CONTENT=$(cat "$EVIDENCE_FILE" 2>/dev/null)
        CONTENT_LEN=${#CONTENT}
        MIN_CHARS=$(hc_get "completion_gate.min_evidence_chars" "20")
        REQ_KEYWORD=$(hc_get "completion_gate.required_keyword" "VERIFIED")

        if [ "$CONTENT_LEN" -lt "$MIN_CHARS" ]; then
            echo "⛔ COMPLETION BLOCKED: 证据内容过短（${CONTENT_LEN} 字符 < ${MIN_CHARS} 字符最低要求）。" >&2
            echo "证据必须包含至少 ${MIN_CHARS} 字符的实际验证描述，不能只有 '${REQ_KEYWORD}' 等占位符。" >&2
            exit 2
        fi

        if ! echo "$CONTENT" | grep -q "$REQ_KEYWORD"; then
            echo "⛔ COMPLETION BLOCKED: 证据文件中未找到 '${REQ_KEYWORD}' 关键字。" >&2
            exit 2
        fi

        # 防重复使用：同一文件 5 分钟内只能使用一次，标记已消费
        echo "CONSUMED at $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$EVIDENCE_FILE"
        exit 0
    fi
fi

# 阻断：无有效证据文件
echo "⛔ COMPLETION BLOCKED: 你正在标记任务为 completed，但未提供验证证据。" >&2
echo "" >&2
echo "强制流程：" >&2
echo " 1. 运行验证命令（测试/模拟/编译）" >&2
REQ_KW=$(hc_get "completion_gate.required_keyword" "VERIFIED")
MIN_CH=$(hc_get "completion_gate.min_evidence_chars" "20")
echo " 2. 执行: echo '${REQ_KW}: [具体验证结果描述]' > /tmp/.completion-evidence-$(date +%Y%m%d)" >&2
echo " 3. 证据必须包含至少 ${MIN_CH} 字符的实际描述" >&2
echo " 4. 再次标记 completed" >&2
echo "" >&2
echo "宪法依据：第一条（证据门禁）— L4 语法合法不可单独作为完成证据" >&2
exit 2
