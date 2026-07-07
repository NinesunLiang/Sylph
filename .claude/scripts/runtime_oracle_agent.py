#!/usr/bin/env python3
"""
Runtime Oracle Agent.

Reviews runtime evidence only:
- token progress
- executor verification evidence
- audit verify events
- soft completion language
- obvious FAIL/error markers

It writes verdicts to:
.omc/state/runtime-oracle-verdicts/{task_id}/{run_id}.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_ROOT = Path(".omc/state")
OUT_ROOT = STATE_ROOT / "runtime-oracle-verdicts"

FAIL_PATTERNS = [
    r"\bFAIL\b",
    r"\bFAILED\b",
    r"\bERROR\b",
    r"\bTraceback\b",
    r"\btimed out\b",
    r"\bexit code [1-9]\b",
]

PASS_PATTERNS = [
    r"\bPASS\b",
    r"\bPASSED\b",
    r"\bOK\b",
    r"\b0 failed\b",
    r"\bexit code 0\b",
]

SOFT_COMPLETION_PATTERNS = [
    r"差不多",
    r"应该可以",
    r"我觉得完成",
    r"大概完成",
    r"基本完成",
    r"looks good",
    r"should be fine",
    r"probably done",
]

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def run_id(prefix: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{prefix}"

def read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")

def read_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_malformed": True}

def count_patterns(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits

def collect_audit_text(audit_dir: str | None, task_id: str) -> str:
    if not audit_dir:
        return ""

    root = Path(audit_dir)
    if not root.exists():
        return ""

    chunks: list[str] = []
    for path in sorted(root.glob("*.jsonl"))[-5:]:
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if task_id in line or "verify" in line.lower():
                    chunks.append(line)
        except OSError:
            continue
    return "\n".join(chunks)

def token_progress(token: dict[str, Any]) -> dict[str, Any]:
    if token.get("_malformed"):
        return {"malformed": True, "done": None, "total": None, "pass": False}

    done = token.get("done")
    total = token.get("total")

    if done is None:
        done = token.get("stats", {}).get("done")
    if total is None:
        total = token.get("stats", {}).get("total")

    try:
        done_i = int(done)
        total_i = int(total)
    except (TypeError, ValueError):
        return {"malformed": False, "done": done, "total": total, "pass": False}

    return {
        "malformed": False,
        "done": done_i,
        "total": total_i,
        "pass": total_i > 0 and done_i >= total_i,
    }

def build_verdict(task_id: str, token: dict[str, Any], executor: str, audit_text: str) -> dict[str, Any]:
    reasons: list[str] = []
    score = 10.0
    risk = "LOW"

    combined = "\n".join([executor, audit_text])

    progress = token_progress(token)
    if progress.get("malformed"):
        score -= 3.0
        risk = "HIGH"
        reasons.append("token JSON 格式错误")
    elif not progress["pass"]:
        score -= 2.0
        risk = "MEDIUM"
        reasons.append(f"token 进度未完成: done={progress.get('done')} total={progress.get('total')}")

    fail_hits = count_patterns(combined, FAIL_PATTERNS)
    pass_hits = count_patterns(combined, PASS_PATTERNS)
    soft_hits = count_patterns(combined, SOFT_COMPLETION_PATTERNS)

    if fail_hits:
        score -= 3.0
        risk = "HIGH"
        reasons.append("运行时证据命中失败模式: " + ", ".join(fail_hits))

    if not pass_hits:
        score -= 1.5
        reasons.append("未发现明确 PASS/OK/exit code 0 证据")

    if soft_hits:
        score -= 1.0
        reasons.append("命中软完成语: " + ", ".join(soft_hits))

    has_verify_audit = "verify" in audit_text.lower()
    if not has_verify_audit:
        score -= 1.0
        reasons.append("audit 中未发现 verify 事件")

    score = max(0.0, round(score, 2))

    if fail_hits and progress["pass"]:
        verdict = "REJECT"
        reasons.append("存在失败证据但 token 显示完成")
    elif risk == "HIGH" and score < 6:
        verdict = "REJECT"
    elif risk == "HIGH":
        verdict = "ESCALATE"
    elif score < 7:
        verdict = "ADVISORY"
    else:
        verdict = "ACCEPT"

    return {
        "version": 3,
        "agent": "runtime_oracle",
        "task_id": task_id,
        "run_id": run_id("runtime"),
        "verdict": verdict,
        "risk": risk,
        "score": score,
        "checks": {
            "token_progress": progress,
            "fail_hits": fail_hits,
            "pass_hits": pass_hits,
            "soft_completion_hits": soft_hits,
            "has_verify_audit": has_verify_audit,
        },
        "evidence": [],
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

def review(args: argparse.Namespace) -> int:
    token = read_json(args.token)
    audit_text = collect_audit_text(args.audit_dir, args.task_id)

    verdict = build_verdict(
        task_id=args.task_id,
        token=token,
        executor=read_text(args.executor),
        audit_text=audit_text,
    )
    out_path = write_verdict(verdict)
    print(str(out_path))
    return 0 if verdict["verdict"] in {"ACCEPT", "ADVISORY"} else 2

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("review")
    p.add_argument("--task-id", required=True)
    p.add_argument("--token")
    p.add_argument("--executor")
    p.add_argument("--audit-dir", default=".omc/state/audit")
    p.set_defaults(func=review)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())