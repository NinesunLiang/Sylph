#!/usr/bin/env bash
# agentic-ui.sh — 共享库（非 Hook） — Agentic UI 标准化输出函数
# Role: 提供统一的菜单/确认/CAPTCHA/状态输出，替代各 hook 中分散的纯文本 stderr

source "$(dirname "$0")/harness_config.sh" 2>/dev/null || true

AGENTIC_UI_SEPARATOR="═══════════════════════════════════════════════════════════════"
AGENTIC_UI_INDENT="  "

ICON_BLOCK="⛔"
ICON_WARN="⚠️"
ICON_INFO="ℹ️"
ICON_SUCCESS="✅"
ICON_LOCK="🔐"
ICON_CAPTCHA="🔑"
ICON_MENU="📋"
ICON_DANGER="🚫"

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

agentic_separator() {
    echo "${AGENTIC_UI_SEPARATOR}" >&2
}

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

agentic_captcha() {
    flywheel_event "agentic_ui" "captcha_shown" "P2" "${1:-captcha}"
    local title="$1" captcha_code="$2" approve_file="$3" description="$4"
    echo "${ICON_CAPTCHA} [${title}] 需要批准 — 请查看 AI 的说明" >&2
    printf '[CAPTCHA] %s | 验证码: %s | 批准文件: %s | %s | 终端执行: echo "%s" > %s | 批准后 AI 行动协议: 检查批准文件是否存在(cat %s 2>/dev/null)，存在则重试被阻断的原操作，不存在则等待用户批准' \
        "$title" "$captcha_code" "$approve_file" "$description" "$captcha_code" "$approve_file" "$approve_file" | hc_emit_hook_json "PreToolUse" "true"
    exit 2
}

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
    [ -n "$detail" ] && echo "${AGENTIC_UI_INDENT}${detail}" >&2
    echo "" >&2
}

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

agentic_table() {
    local title="$1" header="$2"
    shift 2
    local rows=("$@")
    IFS='|' read -ra HDR <<< "$header"
    local NC=${#HDR[@]}
    local widths=()
    for ((c=0; c<NC; c++)); do widths[$c]=${#HDR[$c]}; done
    for row in "${rows[@]}"; do
        IFS='|' read -ra COLS <<< "$row"
        for ((c=0; c<NC; c++)); do
            [ "${#COLS[$c]}" -gt "${widths[$c]}" ] && widths[$c]=${#COLS[$c]}
        done
    done
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
    printf "|" >&2
    for ((c=0; c<NC; c++)); do printf " %-${widths[$c]}s |" "${HDR[$c]}" >&2; done
    printf "\n" >&2
    echo "${sep}" >&2
    for row in "${rows[@]}"; do
        IFS='|' read -ra COLS <<< "$row"
        printf "|" >&2
        for ((c=0; c<NC; c++)); do printf " %-${widths[$c]}s |" "${COLS[$c]:-}" >&2; done
        printf "\n" >&2
    done
    echo "${sep}" >&2
    echo "" >&2
}

agentic_progress() {
    local step="$1" total="$2" description="$3"
    printf "${ICON_INFO} [%d/%d] %s...\n" "${step}" "${total}" "${description}" >&2
}

agentic_context() {
    local message="$1"
    printf '[AGENTIC] %s' "$message" | hc_emit_hook_json "PreToolUse" "true"
}

agentic_context_block() {
    local message="$1"
    printf '[AGENTIC:BLOCK] %s' "$message" | hc_emit_hook_json "PreToolUse" "false"
    exit 2
}
