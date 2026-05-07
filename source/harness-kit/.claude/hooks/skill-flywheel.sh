#!/bin/bash

# harness-kit:managed v1.2

# skill-flywheel.sh — Stop Hook
#
# 功能：机械地将 AI skills 写入的飞轮 buffer 刷入全局日志
#
# 设计背景：
#   lx-* skills 在 AI 层写入 buffer（尽力而为，不保证每次执行）
#   本 hook 在每次 Stop 事件（AI 回复结束）时机械刷入，补偿 AI 的不可靠性
#
# 两层架构：
#   Phase 1（AI, best-effort）: echo "..." >> ~/.claude/flywheel-buffer.jsonl
#   Phase 2（Shell, 机械保证）: 本 hook flush buffer → ~/.claude/flywheel.log


source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_flywheel" || exit 0

BUFFER="$HOME/.claude/flywheel-buffer.jsonl"
FLYWHEEL="$HOME/.claude/flywheel.log"

# buffer 不存在或为空则静默退出
[ -f "$BUFFER" ] && [ -s "$BUFFER" ] || exit 0

# 确保 flywheel.log 目录存在
mkdir -p "$(dirname "$FLYWHEEL")"

# flush：将 buffer 内容追加到 flywheel.log
# 去重策略留给分析端（sort | uniq），此处保留时序信息
BUFFER_CONTENT=$(cat "$BUFFER")
if [ -z "$BUFFER_CONTENT" ]; then
    rm -f "$BUFFER"
    exit 0
fi

# 追加到全局日志
cat "$BUFFER" >> "$FLYWHEEL"

# 消费 buffer
rm -f "$BUFFER"

LINES=$(echo "$BUFFER_CONTENT" | wc -l | tr -d ' ')
echo "Flywheel flushed: ${LINES} entries → flywheel.log"
exit 0
