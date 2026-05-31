#!/usr/bin/env bash
# pretool-approve-detect.sh — UserPromptSubmit — 检测 /approve <token> 或 /deny，自动写入/清除 permission-approved
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
REQUIRED="$STATE_DIR/permission-required"
APPROVED="$STATE_DIR/permission-approved"

# ─── /deny 处理 ───
if echo "$PROMPT" | grep -qiE '\b/deny\b'; then
    if [ -f "$REQUIRED" ]; then
        rm -f "$REQUIRED" "$APPROVED"
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

# 有 /approve → 验证
if [ ! -f "$REQUIRED" ]; then
    echo "ℹ️ 当前无待批准的危险操作（/approve 忽略）。" >&2
    printf '%s' "$PROMPT"
    exit 0
fi

EXPECTED=$(cat "$REQUIRED" 2>/dev/null)

if [ "$APPROVE_TOKEN" = "$EXPECTED" ]; then
    # 验证码匹配 → 写入批准标记
    echo "$APPROVE_TOKEN" > "$APPROVED"
    flywheel_event "pretool_approve_detect" "user_approved" "P2" || true
    echo "✅ /approve 已接受！验证码匹配 $(echo "$APPROVE_TOKEN" | head -c 8)，危险操作已批准（5分钟有效）。" >&2
else
    echo "❌ /approve 失败：验证码不匹配（输入=$(echo "$APPROVE_TOKEN" | head -c 8)，期望=$(echo "$EXPECTED" | head -c 8)）。" >&2
    flywheel_event "pretool_approve_detect" "token_mismatch" "P3" || true
fi

# 透传原始输入（Claude Code 协议要求）
printf '%s' "$PROMPT"
exit 0
