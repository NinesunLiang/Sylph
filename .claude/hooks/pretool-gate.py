#!/usr/bin/env python3
"""
pretool-gate.py — CarrorOS PreToolUse Unified Gate (THIN ROUTER).

This is now the thin routing layer. All gate logic lives in pretool_gates/*.py.

Execution order (short-circuit on first BLOCK):
  1. sensitive-edit   — block sensitive path access
  2. fallback-check   — block if task is blocked/waiting_user
  3. action-gate      — block dangerous commands
  4. plan-gate        — block if task files missing
  5. edit-scope       — block writes outside declared scope
  6. verify-gate      — block unverified step completion marks
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

from pretool_gates.checks import (
    _check_sensitive_edit, _check_fallback, _check_action_gate,
    _check_plan_gate, _check_edit_scope, _check_verify_gate,
    _check_oracle_gate, _check_document_quality,
    _check_g2_large_file, _check_g3_reviews, _check_g5_wide_glob, _check_g6_budget,
    _check_context_critical_pause, _check_secret_scan, _check_watermark_gate,
    _check_numeric_claim, _check_claim_source, _check_action_loop,
    _check_stall, _check_injection,
)

# ── L1/L2 Gate definitions ──
# L1: 轻量模式（日常任务），仅核心安全门
# L2: 完整模式（复杂/危险任务），全量 Gate
L1_GATES = [
    ("watermark", _check_watermark_gate),
    ("context-critical", _check_context_critical_pause),
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("edit-scope", _check_edit_scope),
    ("action", _check_action_gate),
    ("secret-scan", _check_secret_scan),
    ("stall", _check_stall),
    ("claim-source", _check_claim_source),
]

GATES = [
    ("watermark", _check_watermark_gate),
    ("context-critical", _check_context_critical_pause),
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("action", _check_action_gate),
    ("secret-scan", _check_secret_scan),
    ("plan", _check_plan_gate),
    ("edit-scope", _check_edit_scope),
    ("verify", _check_verify_gate),
    ("oracle", _check_oracle_gate),
    ("document-quality", _check_document_quality),
    ("g2-large-file", _check_g2_large_file),
    ("g3-reviews", _check_g3_reviews),
    ("g5-wide-glob", _check_g5_wide_glob),
    ("g6-budget", _check_g6_budget),
    ("action-loop", _check_action_loop),
    ("stall", _check_stall),
    ("numeric-claim", _check_numeric_claim),
    ("claim-source", _check_claim_source),
    ("injection-guard", _check_injection),
]
from pretool_gates.helpers import (
    _read_stdin, _extract_tool, _ok, _block, _redirect,
    _check_temp_bypass, _check_trust_breach, _clean_stale_state_token,
    _goal_mode, _append_audit, _get_gate_mode,
    _record_gate_decision, _verify_contract_compliance,
    _is_trust_breach_reason, _record_trust_breach,
)

# ── State paths used by main ──
from pretool_gates.constants import REDIRECT_STREAK, GOAL_SIGNAL, TRUST_BREACH


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
                # ── Three-strike limit ──
                _REDIRECT_TTL_S = 21600  # 6 hours
                _REDIRECTS: dict[str, dict] = {}
                try:
                    if REDIRECT_STREAK.is_file():
                        raw = json.loads(REDIRECT_STREAK.read_text(encoding="utf-8"))
                        now_s = int(time.time())
                        _REDIRECTS = {}
                        for k, v in raw.items():
                            if isinstance(v, dict) and "c" in v and "t" in v:
                                if now_s - v["t"] < _REDIRECT_TTL_S:
                                    _REDIRECTS[k] = v
                except Exception:
                    _REDIRECTS = {}
                now_s = int(time.time())
                prev = _REDIRECTS.get(gate_name, {}).get("c", 0)
                _REDIRECTS[gate_name] = {"c": prev + 1, "t": now_s}
                try:
                    REDIRECT_STREAK.parent.mkdir(parents=True, exist_ok=True)
                    REDIRECT_STREAK.write_text(json.dumps(_REDIRECTS), encoding="utf-8")
                except Exception:
                    pass
                if _REDIRECTS[gate_name]["c"] >= 3:
                    _append_audit({
                        "event_type": "redirect_escalated_to_block",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "redirect_count": _REDIRECTS[gate_name]["c"],
                        "reason": "exceeded_3_redirect_limit",
                    })
                    return _block(
                        f"该操作已被 REDIRECT 拦截 {_REDIRECTS[gate_name]['c']} 次仍未修正",
                        "放弃当前操作方向，不要重复被拒的操作。")
                parts = result.split("|", 1)
                reason = parts[0].replace("REDIRECT ", "").strip()
                guidance = parts[1].strip() if len(parts) > 1 else ""
                return _redirect(reason, guidance)
            if result.startswith("BLOCK"):
                if bypass_active:
                    _append_audit({
                        "event_type": "gate_bypassed",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "reason": result,
                    })
                    return _ok(f"BYPASS_ALLOW [{gate_name}] (用户已授权临时跳过)")
                parts = result.split("|", 1)
                reason = parts[0].replace("BLOCK ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                if _is_trust_breach_reason(reason):
                    _record_trust_breach(reason)
                return _block(reason, suggestion)
            if result == "HARD_BLOCK":
                return 0
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
                    print(f"⚠️ [{gate_name}] {result}", file=sys.stderr, flush=True)
                continue

    # ── Gate Contract Compliance ──
    contract_result = _verify_contract_compliance(gate_mode, executed_gates)
    if contract_result and contract_result.startswith("BLOCK"):
        return contract_result

    return _ok(f"ALLOW tool={tool_name}")


if __name__ == "__main__":
    sys.exit(main())
