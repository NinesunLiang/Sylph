#!/usr/bin/env bash
# pretool-user-correction.sh — UserPromptSubmit — 检测用户纠正信号，强制记录到 claude-next.md
# Role: 检测用户纠正信号，强制记录到 claude-next.md

source "$(dirname "$0")/harness_config.sh"
hc_enabled "user_correction_detector" || { cat; exit 0; }

# 从 stdin 读取完整用户输入
PROMPT=$(cat)

# 从配置读取纠正信号词列表
CORRECTION_SIGNALS=$(hc_get "correction_detector.signals" "不对 错了 你搞错了 应该是 不是这样 重新来 这不对 你弄错了 纠正一下 弄错了 理解错了 你理解错了 理解有误")

# 检测是否命中信号词
TRIGGERED=false
MATCHED_SIGNAL=""
set -f
for signal in $CORRECTION_SIGNALS; do
    if echo "$PROMPT" | grep -qF "$signal"; then
        TRIGGERED=true
        MATCHED_SIGNAL="$signal"
        break
    fi
done
set +f

if [ "$TRIGGERED" = "true" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
    TODAY=$(date +%Y-%m-%d)

    # 当天已有新写入 → 静默（不重复提醒）
    ALREADY_WRITTEN=false
    if [ -f "$CLAUDE_NEXT" ] && grep -qF "### [$TODAY]" "$CLAUDE_NEXT" 2>/dev/null; then
        ALREADY_WRITTEN=true
    fi

    if [ "$ALREADY_WRITTEN" = "false" ]; then
        # Auto-write skeleton entry to claude-next.md
        _TITLE=$(echo "$PROMPT" | head -c 50 | tr '\n' ' ' | sed 's/[[:space:]]*$//')
        cat >> "$CLAUDE_NEXT" << CORRECTEOF

### [${TODAY}] 用户纠正: ${MATCHED_SIGNAL}
@${TODAY} hits:1
**触发场景**：检测到纠正信号「${MATCHED_SIGNAL}」（${_TITLE}）
**问题**：（待本对话补充具体纠正内容）
**纠正**：（AI 完成任务前应引用此记录并补充根因分析）

CORRECTEOF
    fi

    # Always output the visual reminder (regardless of whether we wrote to file)
    echo ""
    echo "╔══ [纠正检测] 检测到纠正信号（'$MATCHED_SIGNAL'）══════════════════╗"
    if [ "$ALREADY_WRITTEN" = "true" ]; then
        echo "║ 今日记录已存在，跳过重复写入 claude-next.md                      ║"
    else
        echo "║ 已自动写入骨架到 .claude/claude-next.md                          ║"
    fi
    echo "║ ⛔ 停止当前执行流！用户纠正信号 = 方向错误，先确认再继续              ║"
    echo "║ AI 应在当前输出中引用并补充：问题+根因+纠正                      ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
fi

# 透传原始输入（Claude Code 协议要求：UserPromptSubmit hook 必须将用户输入回写 stdout）
printf '%s' "$PROMPT"
flywheel_event "pretool_user_correction" "correction_detected" "P2" "correction_signal"
exit 0
