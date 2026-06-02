#!/usr/bin/env bash
# permission-gate.sh — PreToolUse:Bash — 执行危险命令前检查权限申请格式
# Role: 执行危险命令前检查权限申请格式

source "$(dirname "$0")/harness_config.sh"
hc_enabled "permission_gate" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
set -f
INPUT=$(cat)

# 提取 command 字段
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
else
    COMMAND=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('command', data.get('tool_input', {}).get('command', '')))
except:
    pass" 2>/dev/null)
fi

# 命令提取失败 → fail-closed: 不确定时阻断，不允许静默放行
if [ -z "$COMMAND" ]; then
    echo "⛔ [Permission Gate] 无法解析命令文本 — 安全门禁默认阻断。请在终端手动执行或确认命令。" >&2
    printf '{"continue":false,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[Permission Gate] 命令提取失败，安全门禁默认阻断。请人类在终端手动执行此命令，或明确确认放行。"}}\n'
    exit 2
fi

# 从 harness.yaml 读取 regex 模式（fallback 为内置默认值）
GIT_COMMIT_RE=$(hc_get "permission_gate.git_commit_regex" 'git\s+(commit|add\s+--?all|\badd\b.*-A)')
GIT_PUSH_FORCE_RE=$(hc_get "permission_gate.git_push_force_regex" 'git\s+push\s+(\S+\s+)?(\S+\s+)?--?force|git\s+push\s+--?force')
GIT_PUSH_RE=$(hc_get "permission_gate.git_push_regex" 'git\s+push\b')
DESTRUCTIVE_RE=$(hc_get "permission_gate.destructive_regex" '\brm\s+-rf\b|\bdrop\s+(table|database|collection|schema)\b|\btruncate(\s+table)?\s+\S|\bdelete\s+from\b')
SUDO_RE=$(hc_get "permission_gate.sudo_regex" '^\s*sudo\b|sudo\s')
GH_WRITE_RE=$(hc_get "permission_gate.gh_write_regex" 'gh\s+(release\s+(upload|create|edit|delete)|pr\s+(create|merge|close|review)|issue\s+(create|close|comment)|repo\s+(create|delete|rename)|variable\s+set|secret\s+set|workflow\s+(run|disable|enable)|gist\s+create|api\s+.*(-X\s+(PUT|POST|PATCH|DELETE)|--method\s+(PUT|POST|PATCH|DELETE)|-f\b))')
BYPASS_RE=$(hc_get "permission_gate.bypass_regex" $'base64\\s+(-d|--decode).*\\|.*\\b(bash|sh|dash|zsh)\\b|xxd\\s+-r.*\\|.*\\b(bash|sh)\\b|printf\\s+[\\"\\x27\\\\047]%[bdh]|eval\\s+\\\\$\\(echo')
SCOPE_WRITE_RE=$(hc_get "permission_gate.scope_write_regex" 'current-scope\.txt|sensitive-approved|permission-approved')

# _c1_block — C1 编码绕过阻断函数（DG-11）
_c1_block() {
    local BYPASS_TOKEN
    BYPASS_TOKEN=$(${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(6))" 2>/dev/null || printf '%08x' "$(( ($(od -vAn -N2 -tu2 /dev/urandom 2>/dev/null || echo $RANDOM) * $RANDOM) & 0xFFFFFFFF ))")
    cat >&2 <<EOF

🚫 [Permission Gate] 编码绕过检测 — 强制终端执行模式

检测到编码执行绕过企图 (base64|xxd|printf|eval 管道)。AI 不被允许执行编码命令。
请复制以下命令到您自己的终端执行：

  ${COMMAND}

验证 Token: ${BYPASS_TOKEN}

EOF
    printf '[Permission Gate] 编码绕过检测触发。AI 永远不能执行编码/动态执行命令。请人类在自己的终端中执行（Token: %s）。' "$BYPASS_TOKEN" | hc_emit_hook_json "PreToolUse" "false"
    flywheel_event "permission_gate" "blocked_encoding_bypass" "P1" || true
    exit 2
}

# C1: encoding bypass detection (DG-11) — 白名单优先，白名单匹配则跳过
C1_WHITELIST=$(hc_get "permission_gate.c1_whitelist" "")
if echo "$COMMAND" | grep -qE "$BYPASS_RE"; then
    if [ -n "$C1_WHITELIST" ] && echo "$COMMAND" | grep -qE "$C1_WHITELIST"; then
        :  # 白名单匹配，跳过 C1 阻断
    else
        _c1_block
    fi
fi

# 危险命令检测
IS_DANGEROUS=false
DANGER_TYPE=""

# git commit 检测 — token 模式: AI 永不代提交，用户必须在自己的终端手动执行
if echo "$COMMAND" | grep -qE "$GIT_COMMIT_RE"; then
    if echo "$COMMAND" | grep -qvE 'git\s+commit\s+--dry-run|git\s+commit\s+--help'; then
        # 生成验证 token 并强制用户在终端执行
        COMMIT_TOKEN=$(${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(6))" 2>/dev/null || printf '%08x' "$(( ($(od -vAn -N2 -tu2 /dev/urandom 2>/dev/null || echo $RANDOM) * $RANDOM) & 0xFFFFFFFF ))")
        cat >&2 <<EOF

🔐 [Permission Gate] Git Commit — 强制终端执行模式

AI 不被允许执行 git commit。请复制以下命令到您自己的终端执行：

  ${COMMAND}

验证 Token: ${COMMIT_TOKEN}

EOF
        printf '[Permission Gate] Git commit 已阻断。AI 永远不能代执行 git commit。请人类在自己的终端中执行命令（Token: %s）。执行后可继续其他操作。' "$COMMIT_TOKEN" | hc_emit_hook_json "PreToolUse" "false"
        flywheel_event "permission_gate" "blocked_git_commit" "P1" || true
        exit 2
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

# 删除/破坏性操作检测 — token 模式: AI 永不代执行，用户必须在自己的终端手动执行
if echo "$COMMAND" | grep -iqE "$DESTRUCTIVE_RE"; then
    DESTROY_TOKEN=$(${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(6))" 2>/dev/null || printf '%08x' "$(( ($(od -vAn -N2 -tu2 /dev/urandom 2>/dev/null || echo $RANDOM) * $RANDOM) & 0xFFFFFFFF ))")
    cat >&2 <<EOF

🚫 [Permission Gate] 破坏性操作 — 强制终端执行模式

AI 不被允许执行破坏性操作。请复制以下命令到您自己的终端执行：

  ${COMMAND}

验证 Token: ${DESTROY_TOKEN}

EOF
    printf '[Permission Gate] 破坏性操作已阻断。AI 永远不能代执行 rm/drop/truncate/delete。请人类在自己的终端中执行命令（Token: %s）。执行后可继续其他操作。' "$DESTROY_TOKEN" | hc_emit_hook_json "PreToolUse" "false"
    flywheel_event "permission_gate" "blocked_destructive" "P1" || true
    exit 2
fi

# sudo 检测
if echo "$COMMAND" | grep -qE "$SUDO_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="sudo"
fi

# gh 写操作检测（release upload/create, pr create/merge/review, issue create/close, gist create, secret set, api POST/PUT/PATCH/DELETE 等）
if echo "$COMMAND" | grep -qE "$GH_WRITE_RE"; then
    IS_DANGEROUS=true
    DANGER_TYPE="gh external write"
fi

# scope 文件写入检测（防止 AI 自绕过 scope gate）
# 注意：排除只读操作（ls/cat/echo 无重定向/python 读/变量赋值等）
if echo "$COMMAND" | grep -qE "$SCOPE_WRITE_RE"; then
    # 使用 ! grep -qE（而非 grep -qvE）支持多行命令正确匹配
    if ! echo "$COMMAND" | grep -qE '^\s*ls\b|^\s*cat\b|echo\s+"[^">]*"$|echo\s+'\''[^'\'']*'\''$|echo\s+['\''"][^'\''"]+['\''"]\s*>>|${PYTHON_BIN:-python3}\s+-c\s|^\s*source\b|^\s*\.\s|grep\b|wc\b|head\b|tail\b|^f=|^d=|^fn=|^a='; then
        IS_DANGEROUS=true
        DANGER_TYPE="scope gate bypass"
    fi
fi

# 非危险命令 → 放行
[ "$IS_DANGEROUS" = false ] && { echo '{"continue": true}'; exit 0; }

# 危险命令已确认 → 先解析路径（无人值守 + 验证码共用）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# ─── 缓存 ──────────────────────────
# approved-ops 缓存: TTL 秒内相同签名自动放行（UX-2.3）
CACHE_FILE="$STATE_DIR/approved-ops.json"
APPROVED_OPS_TTL=$(hc_get "permission_gate.approved_ops_ttl" "1800")

# 检查缓存：相同命令签名在 APPROVED_OPS_TTL 秒内是否已批准
check_cache() {
    local cmd_sig="$1"
    if [ ! -f "$CACHE_FILE" ]; then
        return 1
    fi
    ${PYTHON_BIN:-python3} - "$cmd_sig" "$CACHE_FILE" "$APPROVED_OPS_TTL" <<'CACHEPY' >/dev/null
import json, time, sys
try:
    sig = sys.argv[1]
    ttl = int(sys.argv[3])
    d = json.load(open(sys.argv[2], encoding="utf-8"))
    entry = d.get(sig)
    if entry and time.time() - entry.get('ts', 0) < ttl:
        sys.exit(0)  # cache hit
    sys.exit(1)      # cache miss
except:
    sys.exit(1)      # parse error → miss
CACHEPY
}

write_cache() {
    local cmd_sig="$1"
    local ts
    ts=$(${PYTHON_BIN:-python3} -c "import time; print(int(time.time()))" 2>/dev/null)
    ${PYTHON_BIN:-python3} - "$cmd_sig" "$CACHE_FILE" "$ts" "$DANGER_TYPE" <<'CACHEPY'
import json, os, sys
sig = sys.argv[1]
cache_file = sys.argv[2]
ts = sys.argv[3]
dtype = sys.argv[4]
try:
    d = json.load(open(cache_file, encoding="utf-8"))
except:
    d = {}
d[sig] = {'ts': int(ts), 'type': dtype}
tmp = cache_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding="utf-8") as f:
    json.dump(d, f)
os.rename(tmp, cache_file)
CACHEPY
}

# 统一模式检测: ghost/unattended 降级为"记录+跳过"，不阻断
# 使用 is_mode_active 检测信号文件（兼容 goal/ghost/rpe 模式）
MODE="$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")"
if [ "$MODE" != "normal" ]; then
    flywheel_event "permission_gate" "mode_skip_${DANGER_TYPE// /_}" "P1" || true
    SKIPPED_FILE="$STATE_DIR/skipped-errors.md"
    {
        echo ""
        echo "## $(date '+%Y-%m-%d %H:%M:%S') — permission-gate ${MODE} mode [${DANGER_TYPE}]"
        echo '```'
        echo "$COMMAND"
        echo '```'
    } >> "$SKIPPED_FILE"
    # 同步写入模式 JSON 的 skipped_risks（修复 P0-3: JSON 字段死代码）
    _TS=$(${PYTHON_BIN:-python3} -c "from datetime import datetime; print(datetime.now().isoformat())" 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%S)
    _ESCAPED_CMD=$(${PYTHON_BIN:-python3} -c "import json,sys; print(json.dumps(sys.argv[1]))" "$COMMAND" 2>/dev/null || echo "\"\"")
    _RISK_JSON=$(${PYTHON_BIN:-python3} -c "import json; print(json.dumps({'type':'$DANGER_TYPE','command':${_ESCAPED_CMD},'timestamp':'$_TS'}))" 2>/dev/null)
    if [ -n "$_RISK_JSON" ]; then
        _mode_append_to_list "$STATE_DIR" "$MODE" "skipped_risks" "$_RISK_JSON"
    fi
    echo "[${MODE}] 已记录 ${DANGER_TYPE}: ${COMMAND:0:120}...（模式降级，不阻断）" >&2
    echo '{"continue": true}'
    exit 0
fi

# 检查缓存：TTL 秒内已批准的同签名操作 → 自动放行
CMD_SIG=$(echo "$COMMAND" | head -c 120)
if check_cache "$CMD_SIG"; then
    echo "[权限缓存] ${APPROVED_OPS_TTL} 秒内已批准的同签名操作: ${COMMAND:0:80}..." >&2
    echo '{"continue": true}'
    exit 0
fi

# ─── 随机验证码审批机制 ──────────────────────────
# 原理：Hook 生成随机 hex 码写入 state，阻断时仅在用户终端打印该码。
# AI 无法预知验证码，只有用户手动 echo 验证码到标记文件才能放行。
# 这从根本上解决了旧版「AI 自写标记文件绕过审批」的问题。
PERMISSION_MARKER="$STATE_DIR/permission-approved"
PERMISSION_REQUIRED="$STATE_DIR/permission-required"

# 检查是否有待处理的验证码（即有未完成的审批流程）
if [ -f "$PERMISSION_REQUIRED" ]; then
    EXPECTED_CODE=$(cat "$PERMISSION_REQUIRED" 2>/dev/null)
    if [ -f "$PERMISSION_MARKER" ]; then
        ACTUAL_CODE=$(cat "$PERMISSION_MARKER" 2>/dev/null)
        # 检查标记文件新鲜度（APPROVED_OPS_TTL 秒内有效）
        if [ "$ACTUAL_CODE" = "$EXPECTED_CODE" ]; then
            if command -v python3 &>/dev/null; then
                FRESH=$(${PYTHON_BIN:-python3} -c "import os, time
try:
    age = time.time() - os.path.getmtime('$PERMISSION_MARKER')
    print('yes' if age < $APPROVED_OPS_TTL else 'no')
except:
    print('no')" 2>/dev/null)
            else
                FRESH="yes"
            fi
            if [ "$FRESH" = "yes" ]; then
                # 验证码匹配 → 有效授权，清理并放行 + 写入缓存
                CMD_SIG=$(echo "$COMMAND" | head -c 120)
                write_cache "$CMD_SIG"
                rm -f "$PERMISSION_MARKER" "$PERMISSION_REQUIRED"
                echo '{"continue": true}'
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

# 生成随机 8 位 hex 验证码 — 多级降级，兼容 Claude Code / OpenCode / 任意平台
# L1: python3 secrets (加密级) — L2: python3 random — L3: /dev/urandom — L4: openssl — L5: shell fallback
APPROVAL_CODE=$(
  ${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(4))" 2>/dev/null ||
  ${PYTHON_BIN:-python3} -c "import random,string; print(''.join(random.choice(string.hexdigits.lower()) for _ in range(8)))" 2>/dev/null ||
  { od -vAn -N4 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n'; } ||
  openssl rand -hex 4 2>/dev/null ||
  printf '%08x' "$(( ($(od -vAn -N2 -tu2 /dev/urandom 2>/dev/null || echo $RANDOM) * $RANDOM) & 0xFFFFFFFF ))"
)
# 终极兜底：如果以上全失败（几乎不可能），用 pid+time 组合
[ -z "$APPROVAL_CODE" ] && APPROVAL_CODE=$(printf '%08x' "$(( ($$ * $(date +%s) * $RANDOM) & 0xFFFFFFFF ))")
echo "$APPROVAL_CODE" > "$PERMISSION_REQUIRED"

# 保存原操作到 pending-retry.json，批准后 AI 可读取并重放

flywheel_event "permission_gate" "blocked_captcha_${DANGER_TYPE// /_}" "P1" || true

agentic_captcha \
    "Permission Gate: ${SEVERITY} ${DANGER_TYPE}" \
    "$APPROVAL_CODE" \
    ".omc/state/permission-approved" \
    "🚫 危险操作已阻断！AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）。"
