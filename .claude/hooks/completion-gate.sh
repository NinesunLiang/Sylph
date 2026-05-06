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
        # 原子消费：mv 在同一文件系统是原子操作
        # 并发场景下只有一个进程能 mv 成功，其余进程到此发现源文件已不存在
        CONSUMED="${EVIDENCE_FILE}.consumed.$$"
        if ! mv "$EVIDENCE_FILE" "$CONSUMED" 2>/dev/null; then
            echo "⛔ COMPLETION BLOCKED: 证据已被其他进程消费" >&2
            exit 2
        fi

        # 证据内容验证：必须包含至少 20 字符实际描述 + VERIFIED 关键字
        CONTENT=$(cat "$CONSUMED" 2>/dev/null)
        CONTENT_LEN=${#CONTENT}
        MIN_CHARS=$(hc_get "completion_gate.min_evidence_chars" "20")
        REQ_KEYWORD=$(hc_get "completion_gate.required_keyword" "VERIFIED")

        if [ "$CONTENT_LEN" -lt "$MIN_CHARS" ]; then
            echo "⛔ COMPLETION BLOCKED: 证据内容过短（${CONTENT_LEN} 字符 < ${MIN_CHARS} 字符最低要求）。" >&2
            echo "证据必须包含至少 ${MIN_CHARS} 字符的实际验证描述，不能只有 '${REQ_KEYWORD}' 等占位符。" >&2
            rm -f "$CONSUMED"
            exit 2
        fi

        if ! echo "$CONTENT" | grep -q "$REQ_KEYWORD"; then
            echo "⛔ COMPLETION BLOCKED: 证据文件中未找到 '${REQ_KEYWORD}' 关键字。" >&2
            rm -f "$CONSUMED"
            exit 2
        fi

        # 验证通过，清理消费文件
        rm -f "$CONSUMED"

        # --- 检测方案/验收类任务 → A→B→A 交叉验证（两阶段匹配） ---
        # 高精确率词：单命中即触发
        if echo "$CONTENT" | grep -qiE '(验收|benchmark|scorecard|通过率|口径|mapping|合规)'; then
            TRIGGER="yes"
        # 中等精确率词：需 2+ 匹配避免日常用语误报
        elif [ "$(echo "$CONTENT" | grep -ioE '(报告|方案|评估|design|proposal|review|analysis|评审|分析)' | sort -u | wc -l)" -ge 2 ]; then
            TRIGGER="yes"
        fi
        if [ "${TRIGGER:-no}" = "yes" ]; then
            # 构建手off内容（同时写文件 + 打印 stderr）
            HANDOFF_FILE="$PROJECT_ROOT/.omc/state/cross-verify-handoff.md"
            # 扫描近期修改的方案/报告文件
            RECENT_DOCS=$(find "$PROJECT_ROOT/docs" "$PROJECT_ROOT/rpe" "$PROJECT_ROOT/.omc/plans" -name "*.md" -mmin -10 2>/dev/null | head -5)
            cat > "$HANDOFF_FILE" <<HANDOFF
***** 复制以下全部内容到 B 终端 *****

【当前终端：A | 方案方】

【对抗性验收提示词】
换一个不同模型（如 A 用 Claude 则 B 用 GPT/Gemini），
你是一个对抗性验收官。逐条审查以下方案中每个断言：
· 有行业标准来源吗？有 file:line 吗？
· 是自创指标/口径含糊/结论夸大吗？→ ❌
· 输出格式: 断言 → 证据 → 判定(✅/⚠️/❌) + 理由

【以下为待验收方案内容】
任务描述: ${CONTENT}

近期修改的相关文件（10分钟内）:
$(echo "${RECENT_DOCS}" | sed 's/^/  - /')

（如方案内容在以上文件中，B 终端直接读取对应文件审查）

***** 以上复制到 B 终端 *****
***** 以下为 B 返回报告 *****

【当前终端：B | 验收方】
（B 终端贴在这里）

***** 验收报告结束 *****
HANDOFF
            # 读回文件打印到 stderr
            cat "$HANDOFF_FILE" >&2
            echo "" >&2
            echo "📁 手off文件已写入: .omc/state/cross-verify-handoff.md" >&2
            echo "   B 终端启动后直接执行: cat .omc/state/cross-verify-handoff.md" >&2
            echo "" >&2
            echo "同模型交叉验证效果有限（盲区重叠），必须不同模型才能真正发现断言造假。" >&2
            echo "比对一致 → 验收通过 | 不一致 → 返回 A 重新生成方案，重复此流程" >&2
            echo "══════════════════════════" >&2
        fi
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
