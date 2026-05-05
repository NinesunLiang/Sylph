#!/usr/bin/env bash

# harness-kit:managed v1.0.2

# permission-gate.sh — PreToolUse:Bash Hook

# 功能：当执行危险命令时，检查最近对话是否包含权限申请格式

# 退出码 2 = 阻断（无权限申请上下文）

# 退出码 0 = 放行（已包含申请格式 / 非危险命令）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "permission_gate" || exit 0
INPUT=$(cat)

# 提取 command 字段
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
    COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    pass" 2>/dev/null)
fi

[ -z "$COMMAND" ] && exit 0

# 从 harness.yaml 读取 regex 模式（fallback 为内置默认值）
GIT_COMMIT_RE=$(hc_get "permission_gate.git_commit_regex" 'git\s+(commit|add\s+--?all|\badd\b.*-A)')
GIT_PUSH_FORCE_RE=$(hc_get "permission_gate.git_push_force_regex" 'git\s+push\s+(\S+\s+)?(\S+\s+)?--?force|git\s+push\s+--?force')
GIT_PUSH_RE=$(hc_get "permission_gate.git_push_regex" 'git\s+push\b')
DESTRUCTIVE_RE=$(hc_get "permission_gate.destructive_regex" '\brm\s+-rf\b|\bdrop\s+(table|database|collection|schema)\b|\btruncate(\s+table)?\s+\S|\bdelete\s+from\b')
SUDO_RE=$(hc_get "permission_gate.sudo_regex" '^\s*sudo\b|sudo\s')

# 危险命令检测
IS_DANGEROUS=false
DANGER_TYPE=""

# git commit 检测
if echo "$COMMAND" | grep -qE "$GIT_COMMIT_RE"; then
    # 排除只读操作
    if echo "$COMMAND" | grep -qvE 'git\s+commit\s+--dry-run|git\s+commit\s+--help'; then
        IS_DANGEROUS=true
        DANGER_TYPE="git commit"
    fi
fi

# git push 检测
if echo "$COMMAND" | grep -qE "$GIT_PUSH_FORCE_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="git push --force"
elif echo "$COMMAND" | grep -qE "$GIT_PUSH_RE" && ! echo "$COMMAND" | grep -qE 'git\s+push\s+--?dry-run|git\s+push\s+--help'; then
    IS_DANGEROUS=true
    DANGER_TYPE="git push"
fi

# 删除操作检测（-i 忽略大小写，覆盖 DROP TABLE / TRUNCATE 等 SQL 大写形式）
if echo "$COMMAND" | grep -iqE "$DESTRUCTIVE_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="destructive operation"
fi

# sudo 检测
if echo "$COMMAND" | grep -qE "$SUDO_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="sudo"
fi

# 非危险命令 → 放行
[ "$IS_DANGEROUS" = false ] && exit 0

# 检查权限申请标记文件（由 AI 对话生成）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
PERMISSION_MARKER="$STATE_DIR/permission-approved"

if [ -f "$PERMISSION_MARKER" ]; then
    # 检查标记文件是否在 5 分钟内（防过期）
    if command -v python3 &>/dev/null; then
        FRESH=$(python3 -c "import os, time
try:
    age = time.time() - os.path.getmtime('$PERMISSION_MARKER')
    print('yes' if age < 300 else 'no')
except:
    print('no')" 2>/dev/null)
    else
        FRESH="yes"
    fi
    if [ "$FRESH" = "yes" ]; then
        # 只要标记文件存在且非空，即视为已授权（简化：一句话理由即可）
        if [ -s "$PERMISSION_MARKER" ]; then
            # 有效授权，消费标记文件
            rm -f "$PERMISSION_MARKER"
            exit 0
        fi
    fi
fi

# 阻断：无有效权限申请
case "$DANGER_TYPE" in
    "git push --force")
        SEVERITY="🔴 致命" ;;
    "destructive operation")
        SEVERITY="🔴 致命" ;;
    *)
        SEVERITY="🟡 高危" ;;
esac

cat >&2 <<EOF

[Permission Gate 警报] 请用 Markdown 表格向用户展示以下危险命令，并通过原生 AskUserQuestion 表单询问处置方式（不要让用户手敲数字）：

| 项 | 值 |
|---|---|
| 危险等级 | ${SEVERITY} |
| 命令类型 | ${DANGER_TYPE} |
| 完整命令 | \`${COMMAND}\` |

用户选择后 AI 执行对应动作：
  批准执行 → Bash: echo '用户提供的理由' > ${PERMISSION_MARKER} && 重新触发该命令
  取消操作 → 保持阻断，回到任务循环
  修改命令 → 询问用户新命令，不写标记文件

EOF
exit 2
