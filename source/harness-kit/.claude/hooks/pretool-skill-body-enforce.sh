#!/usr/bin/env bash
# pretool-skill-body-enforce.sh — PreToolUse:Skill — 强制执行合约注入
# Role: 在 skill 执行前自动将 body.md 内容注入 additionalContext，
#       确保 AI 无法"选择不看"执行合约。
# 哲学 #3(先守护): 执行前确保 AI 有完整的执行合约
# 哲学 #6(0信任): 不信任 AI 会主动读 body.md，强制注入

source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_body_enforce" || { echo '{"continue": true}'; exit 0; }
set -f
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
SKILLS_DIR="$PROJECT_ROOT/.claude/skills"

# 解析 skill 名称
SKILL=""
if command -v jq >/dev/null 2>&1; then
    SKILL=$(echo "$INPUT" | jq -r '.tool_input.skill // .args.skill // empty' 2>/dev/null)
else
    SKILL=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {}) or data.get('args', {})
    print(ti.get('skill', ''))
except: pass" 2>/dev/null)
fi

[ -z "$SKILL" ] && { echo '{"continue": true}'; exit 0; }

# 定位 SKILL.md
SKILL_MD="$SKILLS_DIR/$SKILL/SKILL.md"
[ ! -f "$SKILL_MD" ] && { echo '{"continue": true}'; exit 0; }

# 检查 ghost/goal 模式降级
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    flywheel_event "skill_body_enforce" "mode_skip" "P3" "skill=$SKILL mode=$MODE"
    echo '{"continue": true}'
    exit 0
fi

# 读取 body_ref
BODY_REF=""
if command -v python3 >/dev/null 2>&1; then
    BODY_REF=$(${PYTHON_BIN:-python3} -c "
import re
with open('$SKILL_MD', encoding='utf-8') as f:
    content = f.read()
m = re.search(r'^body_ref:\s*(.+)$', content, re.MULTILINE)
print(m.group(1).strip() if m else '')
" 2>/dev/null)
fi

# 没有 body_ref → 静默放行
[ -z "$BODY_REF" ] && { echo '{"continue": true}'; exit 0; }

# 解析 body_ref 路径（相对于 SKILL.md 目录）
SKILL_DIR="$(dirname "$SKILL_MD")"
BODY_PATH="$SKILL_DIR/$BODY_REF"

# 读取 body.md 内容
BODY_CONTENT=""
if [ -f "$BODY_PATH" ]; then
    BODY_CONTENT=$(head -c 3000 "$BODY_PATH" 2>/dev/null || true)
else
    BODY_CONTENT="[body.md 缺失] 文件不存在: $BODY_PATH"
fi

# 构建注入消息
INJECT_MSG="[skill-body-enforce] === 强制执行合约 ===
Skill: $SKILL
body_ref: $BODY_REF
--- body.md 内容 ---
$BODY_CONTENT
--- end body.md ---
你必须严格按 body.md 定义的步骤执行，不可跳过或自行发挥。
如 body.md 中定义的脚本缺失，使用 body.md 中的降级策略。"

# 通过 hc_emit_hook_json 注入 additionalContext
echo "$INJECT_MSG" | hc_emit_hook_json "PreToolUse" "true"

flywheel_event "skill_body_enforce" "injected" "P2" "skill=$SKILL body_ref=$BODY_REF"
exit 0
