#!/bin/bash

# harness-kit:managed v1.0.0

# pretool-user-correction.sh — UserPromptSubmit Hook

# 功能：检测用户输入中的纠正信号词，强制提示 AI 将教训写入 claude-next.md

# 设计：透传原始输入（必须），纯 stdout 输出提醒，exit 0 放行

#

# 触发逻辑：

# - 检测到纠正信号词（如"不对"/"错了"/"你搞错了"）

# - 且当天 claude-next.md 尚无新条目

# → 输出强制写入提醒

#

# 防误报：

# - 纯英文指令不匹配中文信号词

# - 当天已写入则不重复提醒（避免骚扰）

# - fail-open：任何错误直接透传输入，不阻断


source "$(dirname "$0")/harness_config.sh"
hc_enabled "user_correction_detector" || { cat; exit 0; }

# 从 stdin 读取完整用户输入
PROMPT=$(cat)

# 从配置读取纠正信号词列表
CORRECTION_SIGNALS=$(hc_get "correction_detector.signals" "不对 错了 你搞错了 应该是 不是这样 重新来 这不对 你弄错了 纠正一下 弄错了 理解错了 你理解错了 理解有误")

# 检测是否命中信号词
TRIGGERED=false
MATCHED_SIGNAL=""
for signal in $CORRECTION_SIGNALS; do
    if echo "$PROMPT" | grep -qF "$signal"; then
        TRIGGERED=true
        MATCHED_SIGNAL="$signal"
        break
    fi
done

if [ "$TRIGGERED" = "true" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
    TODAY=$(date +%Y-%m-%d)

    # 当天已有新写入 → 静默（不重复提醒）
    ALREADY_WRITTEN=false
    if [ -f "$CLAUDE_NEXT" ] && grep -q "## \\[$TODAY\\]" "$CLAUDE_NEXT" 2>/dev/null; then
        ALREADY_WRITTEN=true
    fi

    if [ "$ALREADY_WRITTEN" = "false" ]; then
        echo ""
        echo "╔══ [纠正检测] 检测到纠正信号（'$MATCHED_SIGNAL'）══════════════════╗"
        echo "║ 宪法工作流原则 2（Self-Improvement Loop）强制触发               ║"
        echo "╠══════════════════════════════════════════════════════════════════╣"
        echo "║ 完成修复后，必须将此教训追加到 .claude/claude-next.md：         ║"
        echo "║                                                                 ║"
        printf "║ ## [%s] {教训标题，≤20字}                                       ║\n" "$TODAY"
        printf "║ <!-- @%s hits:1 -->                                              ║\n" "$TODAY"
        echo "║ **问题**：{描述发生了什么}                                      ║"
        echo "║ **根因**：{为什么发生}                                          ║"
        echo "║ **纠正**：{正确做法，可直接复用的结论}                          ║"
        echo "╚══════════════════════════════════════════════════════════════════╝"
        echo ""
    fi
fi

# 透传原始输入（Claude Code 协议要求：UserPromptSubmit hook 必须将用户输入回写 stdout）
printf '%s' "$PROMPT"
exit 0
