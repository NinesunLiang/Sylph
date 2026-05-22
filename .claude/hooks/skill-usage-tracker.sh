#!/usr/bin/env bash
# skill-usage-tracker.sh — UserPromptSubmit|PostToolUse:Skill — 记录 skill 调用频率
# Role: 无侵入 skill 使用率追踪 — 双路径: UserPromptSubmit(扫描/命令文本) + PostToolUse:Skill(工具调用)
# C7 fix: 原仅 UserPromptSubmit 路径，Skill 工具调用完全不追踪 → 添加 PostToolUse:Skill 路径
# 哲学 #5(以人为本): 用户无感知，零心智负担

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "skill_usage_tracker" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
TOOL_NAME="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../../.omc/state"
mkdir -p "$LOG_DIR"

# 路径 A: PostToolUse:Skill — 实际 Skill 工具调用（C7 fix: 此为 skill 调用的主要路径）
if [ "$TOOL_NAME" = "Skill" ]; then
    SKILL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('skill',''))" 2>/dev/null)
    if [ -n "$SKILL" ]; then
        SKILL_DIR="$SCRIPT_DIR/../skills/$SKILL"
        [ -d "$SKILL_DIR" ] || { echo '{"continue": true}'; exit 0; }
        echo "{\"skill\":\"$SKILL\",\"ts\":$(date +%s)}" >> "$LOG_DIR/skill-usage.jsonl"
        flywheel_event "skill_usage_tracker" "skill_invoked" "P2" "$SKILL"
    fi
    echo '{"continue": true}'
    exit 0
fi

# 路径 B: UserPromptSubmit — 扫描 /lx-xxx 命令文本（兜底路径）
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
[ -z "$PROMPT" ] && { echo '{"continue": true}'; exit 0; }

SKILL=$(echo "$PROMPT" | grep -oE '/?(lx-[a-z][a-z0-9-]*)' | head -1 | sed 's|^/||')
[ -z "$SKILL" ] && { echo '{"continue": true}'; exit 0; }

SKILL_DIR="$SCRIPT_DIR/../skills/$SKILL"
[ -d "$SKILL_DIR" ] || { echo '{"continue": true}'; exit 0; }

echo "{\"skill\":\"$SKILL\",\"ts\":$(date +%s)}" >> "$LOG_DIR/skill-usage.jsonl"
flywheel_event "skill_usage_tracker" "skill_invoked" "P2" "$SKILL"

echo '{"continue": true}'
exit 0
