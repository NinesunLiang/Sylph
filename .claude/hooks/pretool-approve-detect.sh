#!/usr/bin/env bash
# pretool-approve-detect.sh — PreToolUse:Bash — 在 permission-gate 之前运行
# Role: 检查用户是否通过 echo 写了 permission-approved → 解锁危险操作
# 策略: 不依赖 UserPromptSubmit（Claude Code 不完全支持），改为被动检测文件
# 哲学 #6 (0信任): 只要 approved 文件存在且匹配，就算用户批准了

source "$(dirname "$0")/harness_config.sh"
hc_enabled "approve_detect" || exit 0

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 只检查 approved 文件是否存在并有效，不做任何修改
# permission-gate.sh 会自己验证
# 这里只是一个哨兵——如果 approved 文件存在，输出提示让 AI 知道可以重试
if [ -f "$STATE_DIR/permission-approved" ]; then
    echo "[Approve] 检测到已批准的验证码，可以重试命令。" >&2
fi

echo '{"continue": true}'
exit 0
