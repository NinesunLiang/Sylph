#!/usr/bin/env bash
# permission-gate.sh — PreToolUse:Bash — 执行危险命令前检查权限申请格式
# Role: 执行危险命令前检查权限申请格式

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
GH_WRITE_RE=$(hc_get "permission_gate.gh_write_regex" 'gh\s+(release\s+(upload|create|edit|delete)|pr\s+(create|merge|close|review\s+--approve)|issue\s+(create|close|comment)|repo\s+(create|delete|rename)|variable\s+set|secret\s+set|workflow\s+(run|disable|enable)|api\s+.*-X\s+(PUT|POST|PATCH|DELETE))\b')

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

# gh 写操作检测（release upload/create, pr create/merge, issue create/close, secret set 等）
if echo "$COMMAND" | grep -qE "$GH_WRITE_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="gh external write"
fi

# 非危险命令 → 放行
[ "$IS_DANGEROUS" = false ] && exit 0

# ─── 随机验证码审批机制 ──────────────────────────
# 原理：Hook 生成随机 hex 码写入 state，阻断时仅在用户终端打印该码。
# AI 无法预知验证码，只有用户手动 echo 验证码到标记文件才能放行。
# 这从根本上解决了旧版「AI 自写标记文件绕过审批」的问题。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
PERMISSION_MARKER="$STATE_DIR/permission-approved"
PERMISSION_REQUIRED="$STATE_DIR/permission-required"

# 检查是否有待处理的验证码（即有未完成的审批流程）
if [ -f "$PERMISSION_REQUIRED" ]; then
    EXPECTED_CODE=$(cat "$PERMISSION_REQUIRED" 2>/dev/null)
    if [ -f "$PERMISSION_MARKER" ]; then
        ACTUAL_CODE=$(cat "$PERMISSION_MARKER" 2>/dev/null)
        # 检查标记文件新鲜度（5分钟内有效）
        if [ "$ACTUAL_CODE" = "$EXPECTED_CODE" ]; then
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
                # 验证码匹配 → 有效授权，清理并放行
                rm -f "$PERMISSION_MARKER" "$PERMISSION_REQUIRED"
                exit 0
            fi
        fi
    fi
    # 标记文件过期或验证码不匹配 → 清理旧码，重新生成
    rm -f "$PERMISSION_REQUIRED"
fi

# 阻断：无有效权限申请 → 生成随机验证码，写入 state 文件
case "$DANGER_TYPE" in
    "git push --force")
        SEVERITY="🔴 致命" ;;
    "destructive operation")
        SEVERITY="🔴 致命" ;;
    *)
        SEVERITY="🟡 高危" ;;
esac

# 生成随机 8 位 hex 验证码（AI 无法预知，只在用户终端显示）
APPROVAL_CODE=$(python3 -c "import secrets; print(secrets.token_hex(4))" 2>/dev/null || echo "perm-$$-$(date +%s)")
echo "$APPROVAL_CODE" > "$PERMISSION_REQUIRED"

echo "Permission Gate: 需要你批准后才能执行 ${DANGER_TYPE}" >&2
echo '复制下方内容执行，回车后说"继续"：' >&2
echo "echo '${APPROVAL_CODE}' > ${STATE_DIR##$PROJECT_ROOT/}/permission-approved" >&2
exit 2
