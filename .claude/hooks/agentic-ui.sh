#!/usr/bin/env bash
# agentic-ui.sh — 共享库（非 Hook） — Agentic UI 标准化输出函数
# Role: 提供统一的菜单/确认/CAPTCHA/状态输出，替代各 hook 中分散的纯文本 stderr
#
# 使用方式（hook 脚本中）:
#   source "$(dirname "$0")/agentic-ui.sh"
#

# flywheel instrumentation
source "$(dirname "$0")/harness_config.sh" 2>/dev/null || true
# 设计原则:
#   1. 所有用户可见输出 → stderr（Claude Code 渲染为红色横幅）
#   2. 所有 AI 可见上下文 → additionalContext（stdout JSON）
#   3. 菜单始终 exit 2（阻断），CAPTCHA 始终 exit 2（阻断）
#   4. 遵循哲学 #5（以人为本）：选择 > 文字输入

# ── 配置 ──────────────────────────────────────────────────
AGENTIC_UI_SEPARATOR="═══════════════════════════════════════════════════════════════"
AGENTIC_UI_INDENT="  "

# ── 图标 ──────────────────────────────────────────────────
ICON_BLOCK="⛔"
ICON_WARN="⚠️"
ICON_INFO="ℹ️"
ICON_SUCCESS="✅"
ICON_LOCK="🔐"
ICON_CAPTCHA="🔑"
ICON_MENU="📋"
ICON_DANGER="🚫"

# ── 基础输出 ──────────────────────────────────────────────

# agentic_banner level title message
# level: block | warn | info | success
agentic_banner() {
    local level="$1" title="$2" message="$3"
    local icon
    case "$level" in
        block) icon="$ICON_BLOCK" ;;
        warn)  icon="$ICON_WARN" ;;
        info)  icon="$ICON_INFO" ;;
        success) icon="$ICON_SUCCESS" ;;
        *)     icon="$ICON_INFO" ;;
    esac
    cat >&2 <<EOF

${icon} [${title}] ${message}
EOF
}

# agentic_separator — 输出分隔线
agentic_separator() {
    echo "${AGENTIC_UI_SEPARATOR}" >&2
}

# ── 交互式菜单 ────────────────────────────────────────────

# agentic_menu title reason option1_label option1_desc option2_label option2_desc [option3_label option3_desc]
# 输出标准化三选一菜单到 stderr，然后 exit 2
# 选项 3 始终为"取消操作"
agentic_menu() {
  flywheel_event "agentic_ui" "menu_shown" "P2" "${1:-menu}"
    local title="$1" reason="$2"
    local opt1_label="$3" opt1_desc="$4"
    local opt2_label="$5" opt2_desc="$6"
    local opt3_label="${7:-取消操作}" opt3_desc="${8:-不执行任何操作}"

    cat >&2 <<EOF

${ICON_MENU} [${title}]
${AGENTIC_UI_SEPARATOR}
原因：${reason}

请选择：
${AGENTIC_UI_INDENT}1. ${opt1_label} — ${opt1_desc}
${AGENTIC_UI_INDENT}2. ${opt2_label} — ${opt2_desc}
${AGENTIC_UI_INDENT}3. ${opt3_label} — ${opt3_desc}

输入数字 (1-3):
EOF
    exit 2
}

# agentic_menu_two title reason opt1_label opt1_desc opt2_label opt2_desc
# 二选一菜单（无取消选项）
agentic_menu_two() {
    local title="$1" reason="$2"
    local opt1_label="$3" opt1_desc="$4"
    local opt2_label="$5" opt2_desc="$6"

    cat >&2 <<EOF

${ICON_MENU} [${title}]
${AGENTIC_UI_SEPARATOR}
原因：${reason}

请选择：
${AGENTIC_UI_INDENT}1. ${opt1_label} — ${opt1_desc}
${AGENTIC_UI_INDENT}2. ${opt2_label} — ${opt2_desc}

输入数字 (1-2):
EOF
    exit 2
}

# ── CAPTCHA 验证码 ────────────────────────────────────────

# agentic_captcha title captcha_code approve_file description
# 输出 CAPTCHA 验证码（双通道：stderr 给用户 + additionalContext 给 AI）
# 返回 JSON 到 stdout（continue: false + additionalContext 含验证码）
agentic_captcha() {
  flywheel_event "agentic_ui" "captcha_shown" "P2" "${1:-captcha}"
    local title="$1" captcha_code="$2" approve_file="$3" description="$4"

    # stderr: 用户可见
    cat >&2 <<EOF

${ICON_CAPTCHA} [${title}] 需要人类批准

验证码: ${captcha_code}

${description}

批准方法 — 在输入框中输入以下命令并按 Enter 执行：
${AGENTIC_UI_INDENT}! echo '${captcha_code}' > ${approve_file}

非 Claude Code 平台（OpenCode 等）去掉 ! 前缀即可。
EOF

    # stdout: AI 可见（additionalContext）
    printf '[CAPTCHA] %s | 验证码: %s | 批准文件: %s | AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）' \
        "$title" "$captcha_code" "$approve_file" | hc_emit_hook_json "PreToolUse" "false"
    exit 2
}

# ── 状态输出（非阻断）─────────────────────────────────────

# agentic_status level title message [detail]
# 输出结构化状态信息到 stderr（不阻断，用于信息展示）
agentic_status() {
    local level="$1" title="$2" message="$3" detail="${4:-}"
    local icon
    case "$level" in
        block) icon="$ICON_BLOCK" ;;
        warn)  icon="$ICON_WARN" ;;
        info)  icon="$ICON_INFO" ;;
        success) icon="$ICON_SUCCESS" ;;
        danger) icon="$ICON_DANGER" ;;
        *)     icon="$ICON_INFO" ;;
    esac

    cat >&2 <<EOF

${icon} [${title}]
${AGENTIC_UI_SEPARATOR}
${message}
EOF
    if [ -n "$detail" ]; then
        echo "${AGENTIC_UI_INDENT}${detail}" >&2
    fi
    echo "" >&2
}

# agentic_breakdown title items...
# 输出评分/分解信息（用于 completion-gate 等）
# items: "label1: value1" "label2: value2" ...
agentic_breakdown() {
    local title="$1"
    shift

    cat >&2 <<EOF

${ICON_INFO} [${title}]
${AGENTIC_UI_SEPARATOR}
EOF
    for item in "$@"; do
        echo "${AGENTIC_UI_INDENT}${item}" >&2
    done
    echo "" >&2
}

# ── 结构化摘要表 ──────────────────────────────────────────

# agentic_table title headers rows...
# 输出对齐的结构化表格到 stderr
# headers: "H1|H2|H3"  rows: "v1|v2|v3" "v4|v5|v6" ...
agentic_table() {
    local title="$1"
    local header="$2"
    shift 2
    local rows=("$@")

    # Parse headers and rows
    IFS='|' read -ra HDR <<< "$header"
    local NC=${#HDR[@]}

    # Calculate column widths
    local widths=()
    for ((c=0; c<NC; c++)); do
        widths[$c]=${#HDR[$c]}
    done
    for row in "${rows[@]}"; do
        IFS='|' read -ra COLS <<< "$row"
        for ((c=0; c<NC; c++)); do
            [ "${#COLS[$c]}" -gt "${widths[$c]}" ] && widths[$c]=${#COLS[$c]}
        done
    done

    # Build separator
    local sep="+"
    for ((c=0; c<NC; c++)); do
        sep+=$(printf '%*s' "${widths[$c]}" '' | tr ' ' '-')
        [ $c -lt $((NC-1)) ] && sep+="+"
    done
    sep+="+"

    cat >&2 <<EOF

${ICON_INFO} ${title}
${sep}
EOF
    # Header row
    printf "|" >&2
    for ((c=0; c<NC; c++)); do
        printf " %-${widths[$c]}s |" "${HDR[$c]}" >&2
    done
    printf "\n" >&2
    echo "${sep}" >&2
    # Data rows
    for row in "${rows[@]}"; do
        IFS='|' read -ra COLS <<< "$row"
        printf "|" >&2
        for ((c=0; c<NC; c++)); do
            printf " %-${widths[$c]}s |" "${COLS[$c]:-}" >&2
        done
        printf "\n" >&2
    done
    echo "${sep}" >&2
    echo "" >&2
}

# ── 步骤进度指示 ──────────────────────────────────────────

# agentic_progress step total description
# 输出 "[1/5] Compiling..." 风格的步骤进度
agentic_progress() {
    local step="$1" total="$2" description="$3"
    printf "${ICON_INFO} [%d/%d] %s...\n" "${step}" "${total}" "${description}" >&2
}

# ── additionalContext 辅助 ─────────────────────────────────

# agentic_context message — 注入 AI 可见上下文（非阻断）
agentic_context() {
    local message="$1"
    printf '[AGENTIC] %s' "$message" | hc_emit_hook_json "PreToolUse" "true"
}

# agentic_context_block message — 注入 AI 可见上下文 + 阻断
agentic_context_block() {
    local message="$1"
    printf '[AGENTIC:BLOCK] %s' "$message" | hc_emit_hook_json "PreToolUse" "false"
    exit 2
}
