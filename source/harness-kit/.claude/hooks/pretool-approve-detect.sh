#!/usr/bin/env bash
# pretool-approve-detect.sh — UserPromptSubmit — 检测 /approve <token> 或 /deny，自动写入/清除 CAPTCHA 批准文件
# Role: 拦截用户聊天中的 /approve|/deny 指令，实现对话内批准流程

source "$(dirname "$0")/harness_config.sh"
# 不依赖 permission_gate 开关：/approve 是独立机制，即使 permission_gate 禁用时也应正常工作
# 如果禁用时收到 /approve，会报告 "无待批准操作" — 这是正确行为

set -f
PROMPT=$(cat)

# 确定项目路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# CAPTCHA 文件对定义：三套独立验证机制
# 每对: required_file approved_file 描述
CAPTCHA_PAIRS=(
  "$STATE_DIR/permission-required"        "$STATE_DIR/permission-approved"        "permission"
  "$STATE_DIR/sensitive-required"         "$STATE_DIR/sensitive-approved"         "sensitive"
  "$STATE_DIR/oracle-gate-required"       "$STATE_DIR/oracle-gate-approved"       "oracle-gate"
)

# ─── /deny 处理 ───
if echo "$PROMPT" | grep -qiE '\b/deny\b'; then
    FOUND=false
    for ((i=0; i<${#CAPTCHA_PAIRS[@]}; i+=3)); do
        required="${CAPTCHA_PAIRS[i]}"
        approved="${CAPTCHA_PAIRS[i+1]}"
        if [ -f "$required" ] || [ -f "$approved" ]; then
            rm -f "$required" "$approved"
            FOUND=true
        fi
    done
    if [ "$FOUND" = true ]; then
        flywheel_event "pretool_approve_detect" "user_denied" "P2" || true
        echo "🚫 /deny — 危险操作已取消。审批文件已清理。" >&2
    else
        echo "ℹ️ 当前无待批准的危险操作（/deny 忽略）。" >&2
    fi
    printf '%s' "$PROMPT"
    exit 0
fi

# ─── /approve <token> 处理 ───
APPROVE_TOKEN=$(echo "$PROMPT" | grep -oE '(^|[^a-zA-Z0-9_])/approve\s+[0-9a-fA-F]{6,16}\b' | grep -oE '[0-9a-fA-F]{6,16}$' | head -1)

if [ -z "$APPROVE_TOKEN" ]; then
    # 无 /approve 指令 → 透传
    printf '%s' "$PROMPT"
    exit 0
fi

# 有 /approve → 循环验证三套 CAPTCHA
MATCHED=false
for ((i=0; i<${#CAPTCHA_PAIRS[@]}; i+=3)); do
    required="${CAPTCHA_PAIRS[i]}"
    approved="${CAPTCHA_PAIRS[i+1]}"
    desc="${CAPTCHA_PAIRS[i+2]}"

    if [ ! -f "$required" ]; then
        continue
    fi

    EXPECTED=$(cat "$required" 2>/dev/null)

    if [ "$APPROVE_TOKEN" = "$EXPECTED" ]; then
        echo "$APPROVE_TOKEN" > "$approved"
        MATCHED=true
        flywheel_event "pretool_approve_detect" "user_approved" "P2" || true
        echo "✅ /approve 已接受！验证码匹配 $(echo "$APPROVE_TOKEN" | head -c 8)，${desc} 操作已批准。" >&2
        break
    fi
done

if [ "$MATCHED" = false ]; then
    echo "❌ /approve 失败：验证码不匹配或无可匹配的待批准操作。" >&2
    flywheel_event "pretool_approve_detect" "token_mismatch" "P3" || true
fi

# 透传原始输入（Claude Code 协议要求）
printf '%s' "$PROMPT"
exit 0
