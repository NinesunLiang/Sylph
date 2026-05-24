#!/usr/bin/env bash
# pretool-oracle-gate.sh — PreToolUse:Edit|Write — Oracle 审查前置门禁 (DG-115)
# Role: 编辑机制/治理文件前检查是否有 Oracle/Meta-Oracle ACCEPT 裁决
#       无裁决 → 阻断 + CAPTCHA 放行。物化 DG-67 双签强制为硬门禁。
#
# 机制文件定义 (Tier 1 — Oracle 强制):
#   .claude/hooks/**, .claude/scripts/**, settings.json, harness.yaml
# 治理文件定义 (Tier 2 — Oracle 建议):
#   .hooks/unified.yaml, feature-registry.yaml, AGENTS.md, kernel.md,
#   anti-patterns.md, claude-next.md

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "oracle_gate" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 提取文件路径
FILE_PATH=""
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.target_file // .args.file_path // .args.path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    fp = ti.get('file_path') or ti.get('target_file') or ti.get('path') or ''
    if not fp:
        args = ti.get('args', d.get('args', {}))
        if isinstance(args, dict):
            fp = args.get('file_path', args.get('path', ''))
    print(fp)
except: print('')
" 2>/dev/null)
fi

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

# 规范化路径
FILE_PATH=$(echo "$FILE_PATH" | sed 's|^\./||')
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ABS_PATH="${FILE_PATH}"
# 相对路径 → 绝对路径
[[ "$FILE_PATH" != /* ]] && ABS_PATH="${PROJECT_ROOT}/${FILE_PATH}"

# ── 机制文件判断 ──
is_mechanism_file() {
    local path="$1"
    # Tier 1: 机制文件 (hook/script 目录 + 核心配置)
    echo "$path" | grep -qE '(\.claude/hooks/|\.claude/scripts/|settings\.json$|harness\.yaml$)' && return 0
    # Tier 2: 治理文件
    echo "$path" | grep -qE '(\.hooks/unified\.yaml$|feature-registry\.yaml$|AGENTS\.md$|kernel\.md$|anti-patterns\.md$|claude-next\.md$|CLAUDE\.md$)' && return 0
    return 1
}

is_mechanism_file "$FILE_PATH" || { echo '{"continue": true}'; exit 0; }

# ── CAPTCHA 绕过检查 (内容验证 + 5分钟时效，参照 sensitive-edit 模式) ──
STATE_DIR="$PROJECT_ROOT/.omc/state"
CAPTCHA_REQUIRED="$STATE_DIR/oracle-gate-required"
CAPTCHA_APPROVED="$STATE_DIR/oracle-gate-approved"
if [ -f "$CAPTCHA_APPROVED" ] && [ -s "$CAPTCHA_APPROVED" ] && [ -f "$CAPTCHA_REQUIRED" ] && [ -s "$CAPTCHA_REQUIRED" ]; then
    EXPECTED=$(cat "$CAPTCHA_REQUIRED" 2>/dev/null | head -1)
    ACTUAL=$(cat "$CAPTCHA_APPROVED" 2>/dev/null | head -1)
    # 检查 5 分钟时效
    FRESH=0
    if ${PYTHON_BIN:-python3} -c "
import os, time
try:
    mtime = os.path.getmtime('$CAPTCHA_REQUIRED')
    if time.time() - mtime < 300:
        print('fresh')
except: pass
" 2>/dev/null | grep -q "fresh"; then
        FRESH=1
    fi
    if [ "$FRESH" = "1" ] && [ "$EXPECTED" = "$ACTUAL" ] && [ -n "$EXPECTED" ]; then
        rm -f "$CAPTCHA_REQUIRED" "$CAPTCHA_APPROVED" 2>/dev/null
        flywheel_event "oracle_gate" "bypass_used" "P1" || true
        echo "[oracle-gate] BYPASS: CAPTCHA 验证通过，一次性放行 ${FILE_PATH}" >&2
        echo '{"continue": true}'
        exit 0
    fi
    # 验证失败 → 清理过期/错误的标记文件，继续正常门禁流程
    rm -f "$CAPTCHA_REQUIRED" "$CAPTCHA_APPROVED" 2>/dev/null
fi

# ── 裁决检查: 24h 内是否有 Oracle/Meta-Oracle ACCEPT ──
ORACLE_VERDICTS="$STATE_DIR/oracle-verdicts.md"
META_VERDICTS="$STATE_DIR/meta-oracle-verdicts.md"
NOW=$(date +%s)
APPROVED=false

check_verdict_file() {
    local vf="$1"
    [ -f "$vf" ] || return 1
    # 提取最近 3 条裁决，检查是否有 24h 内的 ACCEPT/APPROVED
    local recent
    recent=$(head -20 "$vf" 2>/dev/null)
    if echo "$recent" | grep -qE '(ACCEPT|APPROVED|approve|accept)'; then
        # 检查日期是否在 24h 内
        local vdate
        vdate=$(echo "$recent" | grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' | head -1)
        if [ -n "$vdate" ]; then
            local vts
            vts=$(date -j -f "%Y-%m-%d" "$vdate" +%s 2>/dev/null || date -d "$vdate" +%s 2>/dev/null || echo "0")
            if [ "$vts" -gt 0 ] 2>/dev/null && [ $((NOW - vts)) -lt 86400 ] 2>/dev/null; then
                return 0
            fi
        else
            # 无日期戳的 ACCEPT（通常来自当前会话），视为有效
            return 0
        fi
    fi
    return 1
}

check_verdict_file "$ORACLE_VERDICTS" && APPROVED=true
check_verdict_file "$META_VERDICTS" && APPROVED=true

if [ "$APPROVED" = true ]; then
    echo '{"continue": true}'
    exit 0
fi

# ── 无裁决 → 阻断 ──
MECH_TYPE="机制文件"
echo "$FILE_PATH" | grep -qE '(hooks/|scripts/)' && MECH_TYPE="机制文件"
echo "$FILE_PATH" | grep -qE '(unified\.yaml|feature-registry\.yaml|AGENTS\.md|kernel\.md|anti-patterns\.md|claude-next\.md|CLAUDE\.md)' && MECH_TYPE="治理文件"

CAPTCHA=$(date +%s | md5 2>/dev/null || echo "$RANDOM$RANDOM" | md5sum 2>/dev/null | cut -c1-8 || python3 -c "import hashlib,time; print(hashlib.md5(str(time.time()).encode()).hexdigest()[:8])" 2>/dev/null)

cat <<MSG | hc_emit_hook_json "PreToolUse" "false"
🔐 [Oracle 审查门禁] 编辑${MECH_TYPE}前必须先通过 Oracle 审查

  文件: ${FILE_PATH}
  原因: DG-67 规定机制/治理文件变更必须 Oracle + Meta-Oracle 双签
        DG-115 将此规则物化为硬门禁

  放行条件 (任一):
  1. Oracle 已给出 ACCEPT 裁决 (24h 内)
  2. Meta-Oracle 已给出 ACCEPT 裁决 (24h 内)

  ⚠️ 当前状态: 未检测到 24h 内的 ACCEPT/APPROVED 裁决

  绕过方法 — 在输入框中输入以下命令并按 Enter:
    ! echo '${CAPTCHA}' > .omc/state/oracle-gate-approved

  非 Claude Code 平台（OpenCode 等）去掉 ! 前缀即可。
MSG

flywheel_event "oracle_gate" "blocked" "P1" || true
echo "[oracle-gate] BLOCKED: ${FILE_PATH} — 无 Oracle/Meta-Oracle ACCEPT 裁决 (24h)" >&2
exit 0
