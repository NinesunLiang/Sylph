#!/usr/bin/env python3
"""sessionstart-gate-check.py — SessionStart — 门禁禁用状态通知
Role: 在会话启动时检查 harness.yaml 中显式禁用的门禁/功能并输出警告
"""
import json
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_get, flywheel_event


_KNOWN_HOOKS = [
    "auto_snapshot", "build_validator", "completion_gate", "context_guard",
    "context_compressor", "ecosystem_probe", "edit_guard", "error_dna_auto_fix",
    "error_dna", "fuzzy_block", "inject_project_knowledge", "intent_tracker",
    "knowledge_condenser", "lsp_suggest", "meta_oracle_trigger", "permission_gate",
    "posttool_bash_audit", "posttool_claim_audit", "posttool_completion_audit",
    "posttool_checkpoint", "posttool_edit_quality", "posttool_handoff_writer",
    "posttool_subagent_audit", "posttool_write_cite", "posttool_write_lock",
    "pre_completion_gate", "pre_ask_guard", "session_resume",
    "pretool_edit_scope", "pretool_plan_gate", "pretool_purify_gate",
    "pretool_node_reference", "posttool_template_check", "pretool_rules_inject",
    "pretool_skill_version_guard", "pretool_sensitive_edit", "pretool_terminal_safety",
    "cross_platform_smoke_test", "phase_state_tracker", "pretool_b1_detect",
    "pretool_git_gate", "pretool_scope_gate", "permission_frequency_tracker",
    "lsp_gate", "oracle_gate", "posttool_read_cite",
]


def main():
    disabled = []

    # 1. Check knowledge.inject_files
    inject_files = hc_get("knowledge.inject_files", "true")
    if inject_files == "false":
        disabled.append("  • knowledge.inject_files — 知识文件自动注入已禁用")

    # 2. Check all known hooks_enabled
    for hook in _KNOWN_HOOKS:
        val = hc_get(f"hooks_enabled.{hook}", "")
        if val == "false":
            disabled.append(f"  • hooks_enabled.{hook} — 钩子门禁已禁用")

    # 3. Check other gate configurations
    exit_report = hc_get("ghost_mode.exit_report_gate", "true")
    if exit_report == "false":
        disabled.append("  • ghost_mode.exit_report_gate — 幽灵模式退出报告门禁已关闭")

    privacy = hc_get("terminal_safety.privacy_gate", "true")
    if privacy == "false":
        disabled.append("  • terminal_safety.privacy_gate — 隐私门禁已关闭")

    # 4. Output notification if any disabled
    if disabled:
        disabled_str = "\\n".join(disabled)
        result = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[harness-gate-check] ⚠️ 以下门禁/功能当前处于禁用状态:\n{disabled_str}"
                )
            }
        }
        print(json.dumps(result, ensure_ascii=True))
        flywheel_event("sessionstart-gate-check", "disabled_gates_detected", "P2")
    else:
        print('{"continue": true}')

    sys.exit(0)


if __name__ == "__main__":
    main()
