#!/usr/bin/env python3
"""
Meta Oracle.

Aggregates independent static/runtime oracle verdicts.

Input:
.omc/state/static-oracle-verdicts/{task_id}/latest.json
.omc/state/runtime-oracle-verdicts/{task_id}/latest.json

Output:
.omc/state/meta-oracle-verdicts/{task_id}/{run_id}.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_ROOT = Path(".omc/state")
STATIC_ROOT = STATE_ROOT / "static-oracle-verdicts"
RUNTIME_ROOT = STATE_ROOT / "runtime-oracle-verdicts"
OUT_ROOT = STATE_ROOT / "meta-oracle-verdicts"

RETURN_CODES = {
    "ACCEPT": 0,
    "ADVISORY": 1,
    "REJECT": 2,
    "ESCALATE": 3,
    "UNAVAILABLE": 4,
}

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def run_id(prefix: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{prefix}"

def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing verdict: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"malformed verdict: {path}: {exc}"

def validate_verdict(verdict: dict[str, Any], expected_agent: str, task_id: str) -> list[str]:
    errors: list[str] = []

    if verdict.get("version") != 3:
        errors.append(f"{expected_agent} version != 3")
    if verdict.get("agent") != expected_agent:
        errors.append(f"{expected_agent} agent 字段不匹配")
    if verdict.get("task_id") != task_id:
        errors.append(f"{expected_agent} task_id 不匹配")
    if verdict.get("verdict") not in {"ACCEPT", "ADVISORY", "REJECT", "ESCALATE"}:
        errors.append(f"{expected_agent} verdict 非法")
    if verdict.get("risk") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        errors.append(f"{expected_agent} risk 非法")
    if not isinstance(verdict.get("score"), (int, float)):
        errors.append(f"{expected_agent} score 非数字")

    return errors

def aggregate_verdict(task_id: str) -> dict[str, Any]:
    reasons: list[str] = []
    evidence: list[Any] = []

    static_path = STATIC_ROOT / task_id / "latest.json"
    runtime_path = RUNTIME_ROOT / task_id / "latest.json"

    static, static_error = read_json(static_path)
    runtime, runtime_error = read_json(runtime_path)

    if static_error:
        reasons.append(static_error)
    if runtime_error:
        reasons.append(runtime_error)

    if static is None or runtime is None:
        final_verdict = "ESCALATE"
        final_risk = "HIGH"
        final_score = 0.0
    else:
        errors = []
        errors.extend(validate_verdict(static, "static_oracle", task_id))
        errors.extend(validate_verdict(runtime, "runtime_oracle", task_id))
        reasons.extend(errors)

        static_verdict = static.get("verdict")
        runtime_verdict = runtime.get("verdict")
        static_risk = static.get("risk")
        runtime_risk = runtime.get("risk")
        static_score = float(static.get("score", 0))
        runtime_score = float(runtime.get("score", 0))

        evidence.extend(
            [
                {
                    "agent": "static_oracle",
                    "path": str(static_path),
                    "verdict": static_verdict,
                    "risk": static_risk,
                    "score": static_score,
                },
                {
                    "agent": "runtime_oracle",
                    "path": str(runtime_path),
                    "verdict": runtime_verdict,
                    "risk": runtime_risk,
                    "score": runtime_score,
                },
            ]
        )

        reasons.extend([f"static: {r}" for r in static.get("reasons", [])])
        reasons.extend([f"runtime: {r}" for r in runtime.get("reasons", [])])

        consistency_score = 10.0 if static_verdict == runtime_verdict else 6.0
        final_score = round(
            static_score * 0.45 + runtime_score * 0.45 + consistency_score * 0.10,
            2,
        )

        risks = [static_risk, runtime_risk]
        if "CRITICAL" in risks:
            final_risk = "CRITICAL"
        elif "HIGH" in risks:
            final_risk = "HIGH"
        elif "MEDIUM" in risks:
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"

        verdicts = [static_verdict, runtime_verdict]

        if errors:
            final_verdict = "ESCALATE"
        elif "REJECT" in verdicts or final_risk == "CRITICAL":
            final_verdict = "REJECT"
        elif "ESCALATE" in verdicts:
            final_verdict = "ESCALATE"
        elif "ADVISORY" in verdicts or final_score < 8.0:
            final_verdict = "ADVISORY"
        else:
            final_verdict = "ACCEPT"

    return {
        "version": 3,
        "agent": "meta_oracle",
        "task_id": task_id,
        "run_id": run_id("meta"),
        "verdict": final_verdict,
        "risk": final_risk,
        "score": final_score,
        "checks": {
            "static_latest": str(static_path),
            "runtime_latest": str(runtime_path),
            "aggregation": {
                "static_weight": 0.45,
                "runtime_weight": 0.45,
                "consistency_weight": 0.10,
            },
        },
        "evidence": evidence,
        "reasons": reasons,
        "bypass": {
            "active": False,
            "reason": None,
            "expires_at": None,
        },
        "timestamp": utc_now(),
    }

def write_verdict(verdict: dict[str, Any]) -> Path:
    out_dir = OUT_ROOT / verdict["task_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{verdict['run_id']}.json"
    latest_path = out_dir / "latest.json"

    data = json.dumps(verdict, ensure_ascii=False, indent=2)
    out_path.write_text(data + "\n", encoding="utf-8")
    latest_path.write_text(data + "\n", encoding="utf-8")
    return out_path

def aggregate(args: argparse.Namespace) -> int:
    verdict = aggregate_verdict(args.task_id)
    out_path = write_verdict(verdict)
    print(str(out_path))
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return RETURN_CODES.get(verdict["verdict"], RETURN_CODES["UNAVAILABLE"])

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("aggregate")
    p.add_argument("--task-id", required=True)
    p.set_defaults(func=aggregate)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())