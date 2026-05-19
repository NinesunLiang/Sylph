#!/usr/bin/env bash
# skill-usage-tracker.sh — UserPromptSubmit — 记录 skill 调用频率
# Role: 无侵入 skill 使用率追踪 — 检测 /lx-xxx 命令，追加 JSONL
# 哲学 #5(以人为本): 用户无感知，零心智负担

source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_usage_tracker" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)

[ -z "$PROMPT" ] && { echo '{"continue": true}'; exit 0; }

# 检测 /lx-xxx 或 lx-xxx 命令模式
SKILL=$(echo "$PROMPT" | grep -oE '/?(lx-[a-z][a-z0-9-]*)' | head -1 | sed 's|^/||')

[ -z "$SKILL" ] && { echo '{"continue": true}'; exit 0; }

# 验证是已知 skill（目录存在）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$SCRIPT_DIR/../skills/$SKILL"
[ -d "$SKILL_DIR" ] || { echo '{"continue": true}'; exit 0; }

# 追加 JSONL
LOG_DIR="$SCRIPT_DIR/../../.omc/state"
mkdir -p "$LOG_DIR"
echo "{\"skill\":\"$SKILL\",\"ts\":$(date +%s)}" >> "$LOG_DIR/skill-usage.jsonl"
flywheel_event "skill_usage_tracker" "skill_invoked" "P2" "$SKILL"

echo '{"continue": true}'
exit 0
