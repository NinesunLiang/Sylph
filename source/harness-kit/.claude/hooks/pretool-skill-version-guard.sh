#!/usr/bin/env bash
# pretool-skill-version-guard.sh — PreToolUse:Edit|Write — SKILL.md 版本格式 + 引用有效性门禁
# Role: 拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式（指向 VERSION.json 单一真相源）
#       拦截 @references 指向不存在文件的写入

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_skill_version_guard" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

# 解析 file_path 和 content
if command -v jq >/dev/null 2>&1; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
    CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .args.content // .tool_input.new_str // .args.new_str // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {}) or data.get('args', {})
    print(ti.get('file_path', ti.get('filePath', '')))
except: pass" 2>/dev/null)
    CONTENT=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {}) or data.get('args', {})
    print(ti.get('content', ti.get('new_str', '')))
except: pass" 2>/dev/null)
fi

# 只检查 SKILL.md
BASENAME=$(basename "$FILE_PATH" 2>/dev/null)
[ "$BASENAME" != "SKILL.md" ] && [ "$BASENAME" != "TEMPLATE.md" ] && { echo '{"continue": true}'; exit 0; }

# 无内容 → 不检查（可能是删除操作）
[ -z "$CONTENT" ] && { echo '{"continue": true}'; exit 0; }

WARNINGS=""

# ── Check 1: harness_version 必须是 >= 格式 ──
HV_LINE=$(echo "$CONTENT" | grep -E '^harness_version:[[:space:]]*"' 2>/dev/null | head -1)
if [ -n "$HV_LINE" ]; then
    # 提取引号内的值
    HV_VALUE=$(echo "$HV_LINE" | sed -n 's/.*harness_version:[[:space:]]*"\([^"]*\)".*/\1/p')
    if [ -n "$HV_VALUE" ]; then
        if ! echo "$HV_VALUE" | grep -qE '^>='; then
            # 硬编码版本号 — 阻断
            echo "❌ [version-guard] $FILE_PATH: harness_version=\"$HV_VALUE\" 是硬编码版本号" >&2
            echo "   规则: SKILL.md 必须使用 >= 格式（如 \">=6.3.0\"），不能写具体版本号" >&2
            echo "   原因: 版本号唯一真相源是 VERSION.json，SKILL.md 只声明最低兼容版本" >&2
            echo '{"continue": true, "reason": "harness_version must use >= format (e.g. \">=6.3.0\"), not hardcoded version. See VERSION.json for current version."}'
            exit 2
        fi
    fi
fi

# ── Check 2: @references 必须指向存在的文件 ──
# 提取所有 @../../ 引用
SKILL_DIR=$(dirname "$FILE_PATH")
BAD_REFS=""
while IFS= read -r ref; do
    # 跳过非文件引用（目录指针、纯文本）
    echo "$ref" | grep -qE '\.(md|yaml|json|py|sh)$' || continue
    # 去掉 @ 前缀和反引号
    CLEAN=$(echo "$ref" | sed 's/^@//; s/`//g')
    RESOLVED="$SKILL_DIR/$CLEAN"
    if [ ! -f "$RESOLVED" ]; then
        BAD_REFS="$BAD_REFS  $ref → $RESOLVED\n"
    fi
done < <(echo "$CONTENT" | grep -oE '@[`]?\.\./[`]?[^ `\n]+' 2>/dev/null)

if [ -n "$BAD_REFS" ]; then
    echo "⚠️  [version-guard] $FILE_PATH: @references 指向不存在的文件:" >&2
    echo "$BAD_REFS" >&2
    echo "   建议: 先创建目标文件，再引用；或使用 .claude/scripts/validate-skill.sh 校验" >&2
    # 不阻断 — 可能是先写引用后创建文件
    WARNINGS="$WARNINGS\n  - @references 指向不存在的文件"
fi

# 通过
if [ -n "$WARNINGS" ]; then
    echo "⚠️  [version-guard] 通过但有警告:$WARNINGS" >&2
else
    echo "✅ [version-guard] $BASENAME 版本格式 + 引用检查通过" >&2
fi
echo '{"continue": true}'
exit 0
