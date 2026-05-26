#!/usr/bin/env bash
# pretool-approve-detect.sh — UserPromptSubmit — 检测 /approve <token>
# Role: 拦截用户输入中的 /approve 命令 → 写入 permission-approved → 解锁危险操作
# 哲学 #5 (以人为本): Boss 只需打字 "/approve abc123" 而非切终端粘贴 hex
# 哲学 #6 (0信任): 验证 token 必须与 permission-required 中的期望码匹配

source "$(dirname "$0")/harness_config.sh"
hc_enabled "approve_detect" || exit 0

INPUT=$(cat)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
REQUIRED="$STATE_DIR/permission-required"
APPROVED="$STATE_DIR/permission-approved"

# 检测 /approve <token> 模式
# macOS grep -E 兼容：用 [a-zA-Z0-9] 而非 [a-fA-F0-9]（后者在 macOS grep 中不匹配）
APPROVE_TOKEN=$(echo "$INPUT" | awk '{for(i=1;i<=NF;i++) if($i=="/approve" && i<NF) {print $(i+1); exit}}' | grep -E '^[a-zA-Z0-9]{6,16}$')

if [ -z "$APPROVE_TOKEN" ]; then
    exit 0  # 不是 approve 命令，继续
fi

# 验证：检查是否有待处理的验证码
if [ ! -f "$REQUIRED" ]; then
    echo "[Approve] ⚠️ 没有待审批的危险操作。忽略 /approve 命令。" >&2
    exit 0
fi

EXPECTED=$(cat "$REQUIRED" 2>/dev/null)

if [ "$APPROVE_TOKEN" = "$EXPECTED" ]; then
    # Token 匹配 → 写批准标记
    echo "$APPROVE_TOKEN" > "$APPROVED"
    echo "[Approve] ✅ 操作已批准！验证码验证通过，5 分钟内同签名命令自动放行。" >&2
    
    # 移除本次用户输入中的 /approve 命令（清洗后继续处理剩余输入）
    CLEANED=$(echo "$INPUT" | sed -E 's|/approve[[:space:]]+[a-zA-Z0-9]{6,16}[[:space:]]*||g')
    if [ -z "$(echo "$CLEANED" | tr -d '[:space:]')" ]; then
        # 只有 /approve 命令，无其他内容
        echo "Continue"  # 告诉 AI 用户批准了，继续
        exit 0
    fi
    echo "$CLEANED"
else
    echo "[Approve] ❌ 验证码不匹配！期望 ${EXPECTED:0:4}... 收到 ${APPROVE_TOKEN:0:4}..." >&2
fi

exit 0
