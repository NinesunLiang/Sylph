#!/usr/bin/env python3
"""
posttool-output-schema.py — PostToolUse — 轻量输出 schema 校验

C4 增强：对工具输出做关键字段存在性检查，与已知 schema 对照。
warn-only（不阻断），符合 schemas/README.md 的设计哲学。

Known schemas checked:
  - verdict (pass/blocked/warn/incomplete)
  - gate_result (gate_name/passed/verdict)
  - block_output (continue/block_type/reason)
  - Oracle verdict (verdict/risk/score/reasons)

Usage: via hook-launcher: python3 hook-launcher.py posttool-output-schema.py
"""

import json
import sys
from pathlib import Path


# ── Schema checkers ──

def _check_verdict(data: dict) -> list:
    """Check if output matches verdict schema (atomic/verdict.yaml)"""
    warnings = []
    if "verdict" in data:
        v = data["verdict"]
        if v not in ("pass", "blocked", "warn", "incomplete", "ACCEPT", "ADVISORY", "REJECT", "ESCALATE"):
            warnings.append(f"schema:verdict — unknown verdict value '{v}', "
                            f"expected pass|blocked|warn|incomplete or ACCEPT|ADVISORY|REJECT|ESCALATE")
        if "score" not in data:
            warnings.append("schema:verdict — missing 'score' field")
    return warnings


def _check_gate_result(data: dict) -> list:
    """Check if output matches gate_result schema (atomic/gate_result.yaml)"""
    warnings = []
    if "gate_name" in data or "passed" in data or "blockers" in data:
        if "gate_name" not in data:
            warnings.append("schema:gate_result — missing 'gate_name'")
        if "passed" not in data:
            warnings.append("schema:gate_result — missing 'passed'")
        if "verdict" in data:
            v = data["verdict"]
            if isinstance(v, str) and v not in ("pass", "blocked", "warn"):
                warnings.append(f"schema:gate_result — unknown verdict '{v}'")
    return warnings


def _check_block_output(data: dict) -> list:
    """Check if output matches block-output schema"""
    warnings = []
    if "continue" in data and data.get("continue") is False:
        if "block_type" not in data:
            warnings.append("schema:block_output — continue=false but missing 'block_type'")
        if "reason" not in data:
            warnings.append("schema:block_output — continue=false but missing 'reason'")
    return warnings


def _check_oracle_verdict(data: dict) -> list:
    """Check if output matches Oracle verdict patterns"""
    warnings = []
    if "verdict" in data and data.get("verdict") in ("ACCEPT", "ADVISORY", "REJECT", "ESCALATE"):
        if "risk" not in data:
            warnings.append("schema:oracle — missing 'risk' field")
        if "score" not in data:
            warnings.append("schema:oracle — missing 'score' field")
        if "reasons" not in data or not isinstance(data.get("reasons"), list):
            warnings.append("schema:oracle — missing or malformed 'reasons' array")
    return warnings


def _check_meta_oracle(data: dict) -> list:
    """Check if output matches Meta-Oracle G1-G4 output"""
    warnings = []
    if "final_score" in data or "gates" in data:
        if "final_score" not in data:
            warnings.append("schema:meta_oracle — missing 'final_score'")
        if "gates" not in data or not isinstance(data.get("gates"), dict):
            warnings.append("schema:meta_oracle — missing or malformed 'gates' object")
        else:
            required_gates = {"G1", "G2", "G3", "G4"}
            if "gates" in data and isinstance(data["gates"], dict):
                missing_gates = required_gates - set(data["gates"].keys())
                if missing_gates:
                    warnings.append(f"schema:meta_oracle — missing gates: {missing_gates}")
    return warnings


# ── Main ──

def main():
    # Read CC event data from stdin
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        # Not a JSON response — skip validation silently
        print(json.dumps({"continue": True}))
        return

    data = None

    # PostToolUse: payload has tool_use object
    tool_use = payload.get("tool_use", {})
    if tool_use:
        result = tool_use.get("result", {}) if isinstance(tool_use, dict) else {}
        if isinstance(result, dict) and result:
            data = result
        elif isinstance(result, str):
            try:
                data = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass

    # Also check direct "result" or "output" fields
    if not data:
        for key in ("result", "output", "response", "text"):
            val = payload.get(key)
            if isinstance(val, dict) and val:
                data = val
                break
            elif isinstance(val, str):
                try:
                    data = json.loads(val)
                    if isinstance(data, dict):
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

    # Fallback: entire payload is the data (handles raw JSON pipe and self-contained hooks)
    if not data:
        data = payload

    if not isinstance(data, (dict, list)):
        print(json.dumps({"continue": True}))
        return

    warnings = []

    items = [data] if isinstance(data, dict) else data
    for item in items:
        if not isinstance(item, dict):
            continue
        warnings.extend(_check_verdict(item))
        warnings.extend(_check_gate_result(item))
        warnings.extend(_check_block_output(item))
        warnings.extend(_check_oracle_verdict(item))
        warnings.extend(_check_meta_oracle(item))

    # Output: always continue=true (warn-only), warnings on stderr
    out = {"continue": True}
    if warnings:
        msg = f"[C4:schema] {'; '.join(warnings)}"
        print(msg, file=sys.stderr)
        out["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
