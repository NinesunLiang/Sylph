#!/usr/bin/env bash
# sessionstart-gate-check.sh — SessionStart — 门禁禁用状态通知
# Role: 在会话启动时检查 harness.yaml 中显式禁用的门禁/功能并输出警告
# 哲学 #3 (先守护后激发): 确保用户知晓哪些防护已关闭
# 哲学 #6 (0信任): 禁用门禁相当于降级防护等级，需通知用户

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f

_DISABLED=""

# 1. 检查 knowledge.inject_files（唯一已知显式禁用的标量配置）
_INJECT_FILES=$(hc_get "knowledge.inject_files" "true")
if [ "$_INJECT_FILES" = "false" ]; then
    _DISABLED="${_DISABLED}  • knowledge.inject_files — 知识文件自动注入已禁用\n"
fi

# 2. 检查所有 hooks_enabled 中显式设为 false 的项
_KNOWN_HOOKS="
auto_snapshot build_validator completion_gate context_guard context_compressor
ecosystem_probe edit_guard error_dna_auto_fix error_dna fuzzy_block
inject_project_knowledge intent_tracker knowledge_condenser lsp_suggest
meta_oracle_trigger permission_gate posttool_bash_audit posttool_claim_audit
posttool_completion_audit posttool_checkpoint posttool_edit_quality
posttool_handoff_writer posttool_subagent_audit posttool_write_cite
posttool_write_lock pre_completion_gate pre_ask_guard session_resume
pretool_edit_scope pretool_plan_gate pretool_purify_gate pretool_node_reference
posttool_template_check pretool_rules_inject pretool_skill_version_guard
pretool_sensitive_edit pretool_terminal_safety cross_platform_smoke_test
phase_state_tracker pretool_b1_detect pretool_git_gate pretool_scope_gate
permission_frequency_tracker lsp_gate oracle_gate posttool_read_cite
"

for _hook in $_KNOWN_HOOKS; do
    _val=$(hc_get "hooks_enabled.${_hook}" "")
    if [ "$_val" = "false" ]; then
        _DISABLED="${_DISABLED}  • hooks_enabled.${_hook} — 钩子门禁已禁用\n"
    fi
done

# 3. 检查其他 gate 配置
_EXIT_REPORT=$(hc_get "ghost_mode.exit_report_gate" "true")
if [ "$_EXIT_REPORT" = "false" ]; then
    _DISABLED="${_DISABLED}  • ghost_mode.exit_report_gate — 幽灵模式退出报告门禁已关闭\n"
fi

_PRIVACY=$(hc_get "terminal_safety.privacy_gate" "true")
if [ "$_PRIVACY" = "false" ]; then
    _DISABLED="${_DISABLED}  • terminal_safety.privacy_gate — 隐私门禁已关闭\n"
fi

# 4. 输出通知（如果有禁用项）
if [ -n "$_DISABLED" ]; then
    printf '{\"continue\":true,\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"[harness-gate-check] ⚠️ 以下门禁/功能当前处于禁用状态:\\n%s\"}}\n' \
        "$_DISABLED"
    flywheel_event "sessionstart-gate-check" "disabled_gates_detected" "P2"
else
    echo '{"continue": true}'
fi
exit 0
