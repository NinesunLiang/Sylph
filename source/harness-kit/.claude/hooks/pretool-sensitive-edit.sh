#!/usr/bin/env bash
# pretool-sensitive-edit.sh — PreToolUse:Edit|Write — 治理文件编辑验证码门禁（哲学 #6 物化）
# Role: 对 CLAUDE.md/AGENTS.md/harness.yaml/settings.json 等治理文件的 Edit/Write 要求用户 CAPTCHA 确认
# 哲学 #6：先天对 AI 0 信任 — 治理文件变更须经用户显式授权

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_sensitive_edit" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 模式检测: ghost/goal 降级为 log+skip
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    echo "[${MODE}] 敏感文件编辑已记录（模式降级，不阻断）" >&2
    echo '{"continue": true}'
    exit 0
fi

# 提取 file_path 字段（兼容 Edit 和 Write 工具）
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    print(ti.get('file_path', ti.get('path', '')))
except:
    pass" 2>/dev/null)
fi

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

# 敏感文件匹配列表
_BASE=$(basename "$FILE_PATH")
_IS_SENSITIVE=false

# basename 直接匹配
for _name in CLAUDE.md AGENTS.md; do
    [ "$_BASE" = "$_name" ] && { _IS_SENSITIVE=true; break; }
done

# 路径片段匹配（允许绝对/相对路径）
if [ "$_IS_SENSITIVE" = false ]; then
    for _frag in .claude/harness.yaml .claude/settings.json .claude/kernel.md .claude/anti-patterns.md; do
        case "$FILE_PATH" in
            *"$_frag") _IS_SENSITIVE=true; break ;;
        esac
    done
fi

[ "$_IS_SENSITIVE" = false ] && { echo '{"continue": true}'; exit 0; }

# ─── 随机验证码审批机制 ──────────────────────────
# 先检查是否有待处理的 CAPTCHA 批准（回退路径）
SENSITIVE_MARKER="$STATE_DIR/sensitive-approved"
SENSITIVE_REQUIRED="$STATE_DIR/sensitive-required"

if [ -f "$SENSITIVE_REQUIRED" ]; then
    EXPECTED_CODE=$(cat "$SENSITIVE_REQUIRED" 2>/dev/null)
    if [ -f "$SENSITIVE_MARKER" ]; then
        ACTUAL_CODE=$(cat "$SENSITIVE_MARKER" 2>/dev/null)
        if [ "$ACTUAL_CODE" = "$EXPECTED_CODE" ]; then
            if command -v python3 &>/dev/null; then
                FRESH=$(python3 -c "import os, time
try:
    age = time.time() - os.path.getmtime('$SENSITIVE_MARKER')
    print('yes' if age < 300 else 'no')
except:
    print('no')" 2>/dev/null)
            else
                FRESH="yes"
            fi
            if [ "$FRESH" = "yes" ]; then
                rm -f "$SENSITIVE_MARKER" "$SENSITIVE_REQUIRED"
                echo '{"continue": true}'
                exit 0
            fi
        fi
    fi
    rm -f "$SENSITIVE_REQUIRED"
fi

# 生成新验证码备用
APPROVAL_CODE=$(python3 -c "import secrets; print(secrets.token_hex(4))" 2>/dev/null || echo "sen-$$-$(date +%s)")
echo "$APPROVAL_CODE" > "$SENSITIVE_REQUIRED"

echo "🔴 敏感文件编辑: $_BASE" >&2
echo "验证码: $APPROVAL_CODE" >&2
echo "方法 A — 在输入框中按 Enter 执行：" >&2
echo "  ! echo '$APPROVAL_CODE' > .omc/state/sensitive-approved" >&2
echo "方法 B — 在终端中直接运行：" >&2
echo "  approve-sen" >&2
echo "AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）。" >&2
exit 2

