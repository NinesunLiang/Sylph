#!/usr/bin/env python3
"""
pretool-gate.py — CarrorOS PreToolUse Unified Gate (THIN ROUTER).

This is now the thin routing layer. All gate logic lives in pretool_gates/*.py.

Execution order (prefer REDIRECT; escalate to ASK_USER when needed):
  1. sensitive-edit   — ask for confirmation on sensitive paths
  2. fallback-check   — redirect blocked/waiting_user tasks
  3. action-gate      — ask for confirmation on dangerous commands
  4. plan-gate        — redirect missing task context
  5. edit-scope       — warn or ask for scope clarification
  6. verify-gate      — redirect unverified completion marks
  7. oracle-gate      — L2 oracle classification
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ── Import all gate logic from modular package ──
_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]
os.chdir(str(ROOT))

sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(_script_path.parent))

# U3 (index18 人类裁决)：agentic-ui 标准化输出；库缺失时回退纯文本，不阻断
try:
    from lib.agentic_ui import banner as _au_banner, status as _au_status
except Exception:
    def _au_banner(level, title, message):
        print(f"\n⚠️ [{title}] {message}\n", file=sys.stderr)
    def _au_status(level, title, message, detail=""):
        print(f"\n⚠️ [{title}] {message}", file=sys.stderr)
        if detail:
            print(f"  {detail}", file=sys.stderr)

from pretool_gates.checks import (
    _check_sensitive_edit, _check_governance_bypass, _check_action_gate,
    _check_verify_gate,
    _check_oracle_gate, _check_document_quality,
    _check_g2_large_file, _check_g3_reviews, _check_g5_wide_glob, _check_g6_budget,
    _check_secret_scan,
    _check_numeric_claim, _check_action_loop,
    _check_stall, _check_injection,
    _check_omc_skeleton_readonly,
    _check_sensitive_read, _check_sensitive_write_bash,
)

# ── L1/L2 Gate definitions ──
# L1: 轻量模式（日常任务），仅真安全门（敏感路径/危险命令/密钥/治理绕过/卡死）。
# 降噪·激进砍（index15 后续，人类裁决）：砍 fallback/plan/edit-scope/claim-source/
# source-marker —— 途中防错与强制格式，由前置 schema 引导（scorecard-gate 升级）
# + 末端 TDD 校验（verify_gate/completion-gate）替代，避免每工具调用 6+ 道 gate 的开销。
# G5 (index18 人类裁决)：L1/L2 门列表单一真源——核心门只写一遍，避免改门时两处漏改。
_GATE_CORE = [
    ("sensitive-edit", _check_sensitive_edit),
    # index25(人类裁决修复): 读取侧隐私门禁 + Bash 写敏感路径补漏
    ("sensitive-read", _check_sensitive_read),
    ("sensitive-write-bash", _check_sensitive_write_bash),
    ("governance-bypass", _check_governance_bypass),
    ("action", _check_action_gate),
    ("secret-scan", _check_secret_scan),
    # 骨架只读(worktree 隔离): .omc/**/*.md 在 worktree 内只读, 守护级必须 L1 也生效
    ("omc-skeleton-readonly", _check_omc_skeleton_readonly),
]
_GATE_L2_EXTRA = [
    ("verify", _check_verify_gate),
    ("oracle", _check_oracle_gate),
    ("document-quality", _check_document_quality),
    ("g2-large-file", _check_g2_large_file),
    ("g3-reviews", _check_g3_reviews),
    ("g5-wide-glob", _check_g5_wide_glob),
    ("g6-budget", _check_g6_budget),
    ("action-loop", _check_action_loop),
]
_GATE_STALL = [("stall", _check_stall)]
_GATE_L2_TAIL = [
    ("numeric-claim", _check_numeric_claim),
    ("injection-guard", _check_injection),
]

L1_GATES = _GATE_CORE + _GATE_STALL
GATES = _GATE_CORE + _GATE_L2_EXTRA + _GATE_STALL + _GATE_L2_TAIL
from pretool_gates.helpers import (
    _read_stdin, _extract_tool, _ok, _block, _redirect,
    _check_temp_bypass, _check_trust_breach, _clean_stale_state_token,
    _goal_mode, _append_audit, _get_gate_mode,
    _record_gate_decision, _verify_contract_compliance,
    _is_trust_breach_reason, _record_trust_breach, _increment_streak,
    _active_token,
)

# ── State paths used by main ──
from pretool_gates.constants import TRUST_BREACH


def main() -> int:
    payload = _read_stdin()
    tool_name = _extract_tool(payload).lower() or "unknown"

    # ── Temp bypass check ──
    bypass_active = _check_temp_bypass()

    # ── Trust breach check ──
    breach = _check_trust_breach()
    if breach:
        return _block(f"trust_broken: {breach}",
                       f"信任已破裂。如需恢复：人工删除 .omc/state/trust-breach.json 后重试。")

    _clean_stale_state_token()

    # ── Gate selection ──
    gate_mode = _get_gate_mode()
    active_gates = GATES if gate_mode == "l2" else L1_GATES

    executed_gates: set[str] = set()
    for gate_name, gate_fn in active_gates:
        try:
            result = gate_fn(payload)
            _record_gate_decision(gate_name, result, gate_mode)
            executed_gates.add(gate_name)
        except Exception:
            continue
        if result:
            if result.startswith("REDIRECT"):
                # ── REDIRECT remains recoverable; repeated redirects escalate to ASK_USER ──
                parts = result.split("|", 1)
                reason = parts[0].replace("REDIRECT ", "").strip()
                token = _active_token()
                task = token.get("task", {}) if isinstance(token, dict) else {}
                session = token.get("session", {}) if isinstance(token, dict) else {}
                task_id = session.get("id", "unknown") if isinstance(session, dict) else "unknown"
                step_id = task.get("current_step", "unknown") if isinstance(task, dict) else "unknown"
                streak_key = f"{gate_name}|{reason}|{task_id}|{step_id}"
                cnt = _increment_streak(streak_key)
                if cnt >= 4:
                    _append_audit({
                        "event_type": "redirect_escalated_to_hard_stop",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "redirect_count": cnt,
                        "reason": f"exceeded_{cnt}_redirect_limit",
                    })
                    return _block(
                        f"ASK_USER redirect_limit_{cnt}",
                        "该操作已被 REDIRECT 多次；请确认是否调整计划或继续。",
                    )
                parts = result.split("|", 1)
                reason = parts[0].replace("REDIRECT ", "").strip()
                guidance = parts[1].strip() if len(parts) > 1 else ""
                return _redirect(reason, guidance)
            if result.startswith("BLOCK"):
                parts = result.split("|", 1)
                reason = parts[0].replace("BLOCK ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                if bypass_active:
                    _append_audit({
                        "event_type": "gate_bypassed",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "reason": result,
                    })
                    return _ok(f"BYPASS_ALLOW [{gate_name}] (用户已授权临时跳过)")
                if _is_trust_breach_reason(reason):
                    _record_trust_breach(reason)
                return _block(f"ASK_USER {reason}", suggestion or "请确认是否继续或调整计划。")
            if result == "HARD_BLOCK":
                return _block("ASK_USER hard_boundary", "请人工确认下一步，不自动终止任务。")
            elif result.startswith("ASK_USER"):
                parts = result.split("|", 1)
                reason = parts[0].replace("ASK_USER ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                return _block(reason, suggestion)
            elif result.startswith(("NARROW", "CHECKPOINT_FIRST", "CHECKPOINT", "WARN")):
                _append_audit({
                    "event_type": "gate_soft_warn",
                    "actor": "hook:pretool-gate",
                    "gate": gate_name,
                    "reason": result,
                })
                goal_mode = _goal_mode()
                if not goal_mode:
                    _au_banner("warn", gate_name, result)
                continue

    # ── Gate Contract Compliance (output as int, not string) ──
    contract_result = _verify_contract_compliance(gate_mode, executed_gates)
    if contract_result and contract_result.startswith("BLOCK"):
        return _block(
            "ASK_USER contract_violation",
            "门禁证据不完整；请确认继续，系统不会再以 HARD_BLOCK 终止任务。",
        )

    return _ok(f"ALLOW tool={tool_name}")


if __name__ == "__main__":
    sys.exit(main())
