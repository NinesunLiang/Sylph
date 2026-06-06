#!/usr/bin/env bash
# pretool-oracle-gate.sh — PreToolUse:Edit|Write — Oracle 审查前置门禁 (DG-115)
# Role: 编辑机制/治理文件前检查是否有 Oracle/Meta-Oracle ACCEPT 裁决
#       无裁决 → 阻断 + CAPTCHA 放行。物化 DG-67 双签强制为硬门禁。
#
# 爆炸半径分级 (DG-132 blast-radius 分层):
# L0 — AI生产文件 (双审): .claude/hooks/*, .claude/scripts/*, settings.json, harness.yaml
# L1 — AI治理文档 (双审): AGENTS.md, kernel.md, CLAUDE.md
# L2 — AI治理参考 (双审): .claude/reference/*, .claude/nodes/*, .claude/schemas/*, feature-registry.yaml, anti-patterns.md
# L3 — 学习笔记 (不触发双审): claude-next.md, docs/story/*, dogfood/*

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

# ── 爆炸半径分层判断 ──
# return 0 = 需双审 (L0-L2)
# return 1 = 不触发双审 (L3 / 豁免)
is_mechanism_file() {
    local path="$1"
    # 豁免: 烟雾测试文件 — 能力测试不需要 Oracle 门禁
    echo "$path" | grep -q 'harness-smoke-test\.sh$' && return 1
    # L0: AI生产文件 (hook/script 目录 + 核心配置)
    echo "$path" | grep -qE '(\.claude/hooks/|\.claude/scripts/|settings\.json$|harness\.yaml$)' && return 0
    # L1: AI治理文档
    echo "$path" | grep -qE '(AGENTS\.md$|kernel\.md$|CLAUDE\.md$)' && return 0
    # L2: AI治理参考
    echo "$path" | grep -qE '(\.claude/reference/|\.claude/nodes/|\.claude/schemas/|feature-registry\.yaml$|anti-patterns\.md$|\.hooks/unified\.yaml$)' && return 0
    # L3: 学习笔记/狗粮/故事 — 不触发双审 (DG-132)
    return 1
}

is_mechanism_file "$FILE_PATH" || { echo '{"continue": true}'; exit 0; }

hc_gate_mode_warn "oracle_gate" && { echo '{"continue": true}'; exit 0; }

# ── CAPTCHA 绕过检查 (内容验证 + 5分钟时效，参照 sensitive-edit 模式) ──
STATE_DIR="$PROJECT_ROOT/.omc/state"
CAPTCHA_REQUIRED="$STATE_DIR/oracle-gate-required"
CAPTCHA_APPROVED="$STATE_DIR/oracle-gate-approved"
SESSION_APPROVED="$STATE_DIR/.oracle-gate-session-approved"

# 会话级豁免: 一次 CAPTCHA 通过后，同会话内后续治理文件编辑自动放行
# 解决高频编辑场景 (如本次会话的治理重构) 中重复阻断的 UX 问题
if [ -f "$SESSION_APPROVED" ]; then
    echo '{"continue": true}'
    exit 0
fi

if [ -f "$CAPTCHA_APPROVED" ] && [ -s "$CAPTCHA_APPROVED" ] && [ -f "$CAPTCHA_REQUIRED" ] && [ -s "$CAPTCHA_REQUIRED" ]; then
    EXPECTED=$(cat "$CAPTCHA_REQUIRED" 2>/dev/null | head -1)
    ACTUAL=$(cat "$CAPTCHA_APPROVED" 2>/dev/null | head -1)
    # 检查时效（从 harness.yaml 读取 TTL，默认 1800 秒）
    TTL=$(hc_get "permission_gate.approved_ops_ttl" "1800")
    FRESH=0
    if ${PYTHON_BIN:-python3} -c "
import os, time
try:
    mtime = os.path.getmtime('$CAPTCHA_REQUIRED')
    if time.time() - mtime < $TTL:
        print('fresh')
except: pass
" 2>/dev/null | grep -q "fresh"; then
        FRESH=1
    fi
    if [ "$FRESH" = "1" ] && [ "$EXPECTED" = "$ACTUAL" ] && [ -n "$EXPECTED" ]; then
        touch "$SESSION_APPROVED" 2>/dev/null || true
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

HAS_ORACLE=false; HAS_META=false
check_verdict_file "$ORACLE_VERDICTS" && HAS_ORACLE=true
check_verdict_file "$META_VERDICTS" && HAS_META=true

# 强制交接：Oracle ACCEPT 后、Meta-Oracle 未完成前，阻断编辑操作
if [ "$HAS_ORACLE" = true ] && [ "$HAS_META" = false ]; then
    # 检查是否有交接文档生成（表示 Meta-Oracle 流程已启动但未完成）
    HANDOFF_DIR="$PROJECT_ROOT/.omc/plans/$(date +%Y-%m-%d)"
    HAS_HANDOFF=false
    [ -d "$HANDOFF_DIR" ] && find "$HANDOFF_DIR" -name 'v*.md' 2>/dev/null | head -1 | grep -q . && HAS_HANDOFF=true

    if [ "$HAS_HANDOFF" = false ]; then
        # Oracle ACCEPT 但无交接文档 → 需要先走交接流程
        cat >&2 <<EOF

⛔ [Oracle Gate] Oracle 已 ACCEPT 但 Meta-Oracle 二审尚未启动。

五阶段流程要求 Oracle + Meta-Oracle 双签才能编辑机制文件。
请先完成 Oracle → Meta-Oracle 交接流程：

  1. 查看交接文档: ls .omc/plans/$(date +%Y-%m-%d)/
  2. 选择路径: 本终端继续 / 其他终端不同模型 / 跳过
  3. Meta-Oracle 完成后重试此操作

EOF
        flywheel_event "oracle_gate" "blocked_meta_pending" "P1" || true
        exit 2
    fi
    # 有交接文档但 Meta-Oracle 未完成 → 提示用户选择路径
    LATEST_HANDOFF=$(find "$HANDOFF_DIR" -name 'v*.md' 2>/dev/null | sort | tail -1)
    cat >&2 <<EOF

⏳ [Oracle Gate] Oracle 已 ACCEPT，Meta-Oracle 二审待完成。

  交接文档: ${LATEST_HANDOFF}

  请告知 AI 您的选择:
  [A] 本终端继续 → 当前模型执行 Meta-Oracle 审查
  [B] 其他终端 → 用不同模型执行
  [C] 跳过 → 信任 Oracle，跳过 Meta-Oracle

EOF
        flywheel_event "oracle_gate" "blocked_meta_handoff_pending" "P1" || true
        exit 2
fi

# 双签通过（Oracle + Meta-Oracle 都 ACCEPT）或仅 Meta-Oracle ACCEPT → 放行
if [ "$HAS_META" = true ] || [ "$APPROVED" = true ]; then
    echo '{"continue": true}'
    exit 0
fi

# ── 无裁决 → 阻断 ──
MECH_TYPE="机制文件"
echo "$FILE_PATH" | grep -qE '(hooks/|scripts/)' && MECH_TYPE="L0 生产文件"
echo "$FILE_PATH" | grep -qE '(AGENTS\.md|kernel\.md|CLAUDE\.md)' && MECH_TYPE="L1 治理文档"
echo "$FILE_PATH" | grep -qE '(reference/|nodes/|schemas/|feature-registry\.yaml|anti-patterns\.md|unified\.yaml)' && MECH_TYPE="L2 治理参考"

CAPTCHA=$(date +%s | md5 2>/dev/null || echo "$RANDOM$RANDOM" | md5sum 2>/dev/null | cut -c1-8 || ${PYTHON_BIN:-python3} -c "import hashlib,time; print(hashlib.md5(str(time.time()).encode()).hexdigest()[:8])" 2>/dev/null)
echo "$CAPTCHA" > "$CAPTCHA_REQUIRED"  # DG-115 fix: CAPTCHA must be written for bypass to work

cat <<MSG | hc_emit_hook_json "PreToolUse" "true"
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

  自主模式 (lx-goal/lx-ghost): AI 应自动 spawn Oracle+Meta-Oracle 双审，
  获取 ACCEPT 裁决后重试编辑，无需等待人类输入绕过命令。
MSG

flywheel_event "oracle_gate" "blocked" "P1" || true
echo "[oracle-gate] BLOCKED: ${FILE_PATH} — 无 Oracle/Meta-Oracle ACCEPT 裁决 (24h)" >&2
# exit 2 = 阻断工具但不打断工作流链，AI 继续其他任务
# continue:true (via hc_emit_hook_json) = 不停止工具链
exit 2
