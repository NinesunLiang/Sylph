#!/usr/bin/env bash
# posttool-skill-compliance.sh — PostToolUse:Skill — 执行合规审计
# Role: 在 skill 执行后审计 AI 是否按 body.md 执行了，发现偏差则注入警告
# 哲学 #4(验证): 执行后验证，不信任 AI 会自觉遵守 body.md
# 哲学 #6(0信任): 运行时证据 > 静态声明

source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_compliance_audit" || { echo '{"continue": true}'; exit 0; }
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
    flywheel_event "skill_compliance_audit" "mode_skip" "P3" "skill=$SKILL mode=$MODE"
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

# 解析 body_ref 路径
SKILL_DIR="$(dirname "$SKILL_MD")"
BODY_PATH="$SKILL_DIR/$BODY_REF"

# 提取 body.md 中定义的脚本路径（原子化声明）
EXPECTED_SCRIPTS=""
if [ -f "$BODY_PATH" ]; then
    EXPECTED_SCRIPTS=$(${PYTHON_BIN:-python3} -c "
import re
with open('$BODY_PATH', encoding='utf-8') as f:
    content = f.read()
# 提取 scripts/ 目录下的脚本引用
scripts = re.findall(r'[\"\\']?\.\.\/scripts\/([^\"\\' )]+)[\"\\']?', content)
scripts += re.findall(r'[\"\\']?scripts\/([^\"\\' )]+)[\"\\']?', content)
scripts += re.findall(r'[\"\\']?\.\.\/\.\.\/scripts\/([^\"\\' )]+)[\"\\']?', content)
for s in scripts:
    print(s)
" 2>/dev/null || true)
fi

# 审计: 检查 hook-evidence.jsonl 中是否有对应脚本的执行记录
EVIDENCE_FILE="$STATE_DIR/hook-evidence.jsonl"
AUDIT_PASSED=true
AUDIT_DETAILS=""

if [ -n "$EXPECTED_SCRIPTS" ] && [ -f "$EVIDENCE_FILE" ]; then
    while IFS= read -r script; do
        [ -z "$script" ] && continue
        if grep -q "$script" "$EVIDENCE_FILE" 2>/dev/null; then
            AUDIT_DETAILS="${AUDIT_DETAILS}  ✅ $script\n"
        else
            AUDIT_DETAILS="${AUDIT_DETAILS}  ⚠️  $script (无执行证据)\n"
            AUDIT_PASSED=false
        fi
    done <<< "$EXPECTED_SCRIPTS"
fi

# 如果 body.md 定义了脚本但未找到执行证据 → 注入警告
if [ "$AUDIT_PASSED" = false ]; then
    WARN_MSG="[skill-compliance] ⚠️ 执行合规审计: $SKILL
body_ref: $BODY_REF
期望执行但未找到证据:
$(echo -e "$AUDIT_DETAILS" | grep '⚠️')
建议: 验证 body.md 是否被正确执行。如步骤被跳过，请重新执行 skill 或记录偏离原因。"

    echo "$WARN_MSG" | hc_emit_hook_json "PostToolUse" "true"
    flywheel_event "skill_compliance_audit" "non_compliant" "P2" "skill=$SKILL"
else
    flywheel_event "skill_compliance_audit" "compliant" "P3" "skill=$SKILL"
fi

echo '{"continue": true}'
exit 0
