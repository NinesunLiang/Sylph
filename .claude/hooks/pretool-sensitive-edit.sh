#!/usr/bin/env bash
# pretool-sensitive-edit.sh — PreToolUse:Edit|Write|Bash — 治理文件编辑验证码门禁（哲学 #6 物化）
# Role: 对 CLAUDE.md/AGENTS.md/harness.yaml/settings.json 等治理文件的 Edit/Write/Bash 要求用户 CAPTCHA 确认
# 哲学 #6：先天对 AI 0 信任 — 治理文件变更须经用户显式授权
# Bash 支持 (DF-04): 扫描命令字符串中的文件操作目标，检测 sed/tee/>/>>/cp/mv 操作治理文件路径

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_sensitive_edit" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
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

# Bash 工具：从命令字符串提取操作的文件路径（E1 逃逸检测）
if [ -z "$FILE_PATH" ] && command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    if [ "$TOOL_NAME" = "Bash" ]; then
        BASH_CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
        # 扫描命令中的治理文件路径（sed/tee/>/>>/cp/mv/cat/echo 操作）
        for _pat in CLAUDE.md AGENTS.md harness.yaml settings.json kernel.md anti-patterns.md; do
            case "$BASH_CMD" in
                *"$_pat"*) FILE_PATH="$_pat"; break ;;
            esac
        done
        # 也检测 .claude/hooks/ 和 .claude/scripts/ 的修改
        if [ -z "$FILE_PATH" ]; then
            case "$BASH_CMD" in
                *".claude/hooks/"*) FILE_PATH="$(echo "$BASH_CMD" | grep -o '[^ ]*\.claude/hooks/[^ ]*' | head -1)" ;;
                *".claude/scripts/"*) FILE_PATH="$(echo "$BASH_CMD" | grep -o '[^ ]*\.claude/scripts/[^ ]*' | head -1)" ;;
            esac
        fi
    fi
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

flywheel_event "pretool_sensitive_edit" "blocked" "P2" || true
agentic_captcha \
    "敏感文件编辑: $_BASE" \
    "$APPROVAL_CODE" \
    ".omc/state/sensitive-approved" \
    "治理文件变更须经用户显式授权。AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）。"

