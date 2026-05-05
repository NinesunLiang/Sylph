#!/bin/bash

# harness-kit:managed v1.0.2

# completion-gate.sh — PreToolUse:TaskUpdate Hook

# 功能：当 AI 尝试将任务标记为 completed 时，强制阻断并要求提供证据

# 退出码 2 = 阻断工具执行（Claude Code 硬阻断，AI 无法绕过）


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
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
EVIDENCE_DIR=$(hc_get "completion_gate.evidence_dir" ".omc/state")
EVIDENCE_FILE="$PROJECT_ROOT/$EVIDENCE_DIR/.completion-evidence-$(date +%Y%m%d)"
EVIDENCE_FRESHNESS_SEC=$(hc_get "completion_gate.evidence_freshness_sec" "300")
if [ -f "$EVIDENCE_FILE" ]; then
    # 证据文件存在，检查是否在 ${EVIDENCE_FRESHNESS_SEC} 秒内写入
    if command -v python3 &>/dev/null; then
        FRESH=$(python3 -c "import os, time
try:
    age = time.time() - os.path.getmtime('$EVIDENCE_FILE')
    print('yes' if age < $EVIDENCE_FRESHNESS_SEC else 'no')
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
REQ_KW=$(hc_get "completion_gate.required_keyword" "VERIFIED")
MIN_CH=$(hc_get "completion_gate.min_evidence_chars" "20")

# 从 feature-registry.yaml 读取预期证据级别（AC-5.6）
EVIDENCE_LEVEL_LABEL="L3"
REGISTRY_PATH="$(cd "$(dirname "$0")/.." && pwd)/feature-registry.yaml"
if [ -f "$REGISTRY_PATH" ]; then
    L=$(grep -A2 "^  - name: completion-gate" "$REGISTRY_PATH" | grep "evidence_level:" | sed 's/.*evidence_level: *//')
    [ -n "$L" ] && EVIDENCE_LEVEL_LABEL="$L"
fi

cat >&2 <<EOF

[Completion Gate 警报] 请用 Markdown 表格向用户展示以下未完成证据阻断，并通过原生 AskUserQuestion 表单询问处置方式（不要让用户手敲数字）：

| 项 | 值 |
|---|---|
| 拦截原因 | 任务标记 completed 但无验证证据 |
| 预期证据级别 | ${EVIDENCE_LEVEL_LABEL} |
| 证据文件路径 | \`${EVIDENCE_FILE}\` |

用户选择后 AI 执行对应动作：
  运行测试重试 → 回到任务循环，先跑测试/编译/端到端，结果写入证据文件后重试 completed
  强制覆盖     → 询问用户理由，理由写入证据文件后继续（风险自负）
  压缩上下文   → 调 /compact 后重试

EOF
exit 2
