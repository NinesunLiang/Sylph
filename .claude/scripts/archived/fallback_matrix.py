#!/usr/bin/env python3
"""
fallback_matrix.py — L2→L1 降级决策矩阵

Usage:
    python3 .omc/scripts/fallback_matrix.py [--check <trigger_id>] [--watermark <pct>] [--no-verify <N>] [--parse-errors <N>]

如果没有参数，检查所有触发条件。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _count_consecutive_no_verify():
    """检查最近 3 个 tick 是否有 verify 事件"""
    audit_dir = Path(".omc/state/audit")
    if not audit_dir.exists():
        return 0
    jsonl_files = sorted(audit_dir.glob("*.jsonl"), reverse=True)
    if not jsonl_files:
        return 0
    verify_count = 0
    tick_count = 0
    for jf in jsonl_files[:3]:
        with open(jf) as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        if rec.get("event") == "verify":
                            verify_count += 1
                        elif rec.get("event") == "tick":
                            tick_count += 1
                    except json.JSONDecodeError:
                        pass
    if tick_count >= 3 and verify_count == 0:
        return 3
    return 0


def _check_idle_time():
    """检查最后人类消息时间"""
    handoff = Path(".omc/state/session-handoff.md")
    if not handoff.exists():
        return 0
    mtime = handoff.stat().st_mtime
    now = datetime.now(timezone.utc).timestamp()
    idle = now - mtime
    return idle


def check_trigger(trigger_id: str, watermark_pct: float = None,
                  no_verify_count: int = None, parse_errors: int = None) -> dict:
    """检查单个或默认触发条件"""
    triggers = {
        "context_full": {
            "condition": lambda: (watermark_pct or 0) >= 70,
            "action": "demote_to_L1",
            "reason_template": "context_pct={pct}% >= 70%",
        },
        "no_verify_3_ticks": {
            "condition": lambda: (no_verify_count if no_verify_count is not None
                                  else _count_consecutive_no_verify()) >= 3,
            "action": "pause_complex_ops",
            "reason_template": "连续 {n} tick 无 verify",
        },
        "oracle_slow_3x": {
            "condition": lambda: False,  # 需要外部传入 Oracle RTT
            "action": "skip_oracle:ACCEPT",
            "reason_template": "Oracle 响应过慢",
        },
        "parse_error_3x": {
            "condition": lambda: (parse_errors or 0) >= 3,
            "action": "demote_to_L1",
            "reason_template": "连续 {n} 次解析异常",
        },
        "long_idle": {
            "condition": lambda: _check_idle_time() > 3600,
            "action": "limit_L2_scope",
            "reason_template": "idle={idle:.0f}s > 3600s",
        },
    }

    if trigger_id:
        rule = triggers.get(trigger_id)
        if not rule:
            return {"should_fallback": False, "action": "none",
                    "reason": f"Unknown trigger: {trigger_id}"}
        triggered = rule["condition"]()
        if triggered:
            return {
                "should_fallback": True,
                "action": rule["action"],
                "reason": rule["reason_template"].format(
                    pct=watermark_pct, n=no_verify_count or parse_errors or 0,
                    idle=_check_idle_time()),
            }
        return {"should_fallback": False, "action": "none", "reason": "OK"}

    # 无特定 trigger_id → 检查所有
    for tid, rule in triggers.items():
        try:
            if rule["condition"]():
                return {
                    "should_fallback": True,
                    "action": rule["action"],
                    "trigger": tid,
                    "reason": rule["reason_template"].format(
                        pct=watermark_pct, n=no_verify_count or parse_errors or 0,
                        idle=_check_idle_time()),
                }
        except Exception:
            continue

    return {"should_fallback": False, "action": "none", "reason": "All triggers OK"}


def main():
    args = sys.argv[1:]
    trigger_id = None
    watermark_pct = None
    no_verify_count = None
    parse_errors = None
    i = 0
    while i < len(args):
        if args[i] == "--check" and i + 1 < len(args):
            trigger_id = args[i + 1]
            i += 2
        elif args[i] == "--watermark" and i + 1 < len(args):
            watermark_pct = float(args[i + 1])
            i += 2
        elif args[i] == "--no-verify" and i + 1 < len(args):
            no_verify_count = int(args[i + 1])
            i += 2
        elif args[i] == "--parse-errors" and i + 1 < len(args):
            parse_errors = int(args[i + 1])
            i += 2
        else:
            i += 1

    result = check_trigger(trigger_id, watermark_pct=watermark_pct,
                           no_verify_count=no_verify_count,
                           parse_errors=parse_errors)
    print(json.dumps(result))
    return 2 if result["should_fallback"] else 0


if __name__ == "__main__":
    sys.exit(main())
