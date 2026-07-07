#!/usr/bin/env python3
"""
Static Oracle Agent.

Reviews static task evidence only:
- plan/executor file-scope consistency
- dangerous path references
- dangerous command/API references
- file:line evidence sanity

It writes verdicts to:
.omc/state/static-oracle-verdicts/{task_id}/{run_id}.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_ROOT = Path(".omc/state")
OUT_ROOT = STATE_ROOT / "static-oracle-verdicts"

DANGEROUS_PATH_PATTERNS = [
    r"\.ssh/",
    r"\.env\b",
    r"credentials?",
    r"secrets?",
    r"/etc/",
    r"/usr/local/",
    r"/var/lib/",
]

DANGEROUS_COMMAND_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bsudo\b",
    r"\bchmod\s+777\b",
    r"\bchown\b",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\bdeploy\b",
    r"\bpublish\b",
    r"\bnpm\s+publish\b",
    r"\bpip\s+upload\b",
]

EXCLUDED_GOVERNANCE_FILES = {
    ".claude/AGENTS.md",
    ".claude/kernel.md",
    ".claude/index.md",
    ".claude/CLAUDE.md",
}

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

def extract_backticked_files(text: str) -> set[str]:
    files: set[str] = set()
    for item in re.findall(r"`([^`]+)`", text):
        if item.startswith(("http://", "https://", "/")):
            continue
        if re.search(r"[\w./-]+\.\w+", item):
            files.add(item.strip())
    return files

def extract_file_line_refs(text: str) -> list[tuple[str, int]]:
    refs: list[tuple[str, int]] = []
    for match in re.findall(r"([\w./-]+\.\w+):(\d+)", text):
        refs.append((match[0], int(match[1])))
    return refs

def check_file_line_refs(text: str) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    checked = 0
    missing = 0
    out_of_range = 0

    for rel_path, line_no in extract_file_line_refs(text):
        checked += 1
        path = Path(rel_path)
        if not path.exists():
            missing += 1
            reasons.append(f"file:line 引用文件不存在: {rel_path}:{line_no}")
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            missing += 1
            reasons.append(f"file:line 引用文件不可读: {rel_path}:{line_no}")
            continue
        if line_no < 1 or line_no > len(lines):
            out_of_range += 1
            reasons.append(f"file:line 行号越界: {rel_path}:{line_no}")

    return {
        "checked": checked,
        "missing": missing,
        "out_of_range": out_of_range,
        "pass": missing == 0 and out_of_range == 0,
    }, reasons

def pattern_hits(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits

def build_verdict(task_id: str, plan: str, executor: str, target: str | None) -> dict[str, Any]:
    reasons: list[str] = []
    score = 10.0
    risk = "LOW"

    combined = "\n".join([plan, executor, target or ""])

    plan_files = extract_backticked_files(plan)
    executor_files = extract_backticked_files(executor)
    outside = sorted(executor_files - plan_files - EXCLUDED_GOVERNANCE_FILES)

    if outside:
        score -= min(3.0, len(outside) * 0.8)
        risk = "MEDIUM"
        reasons.append("executor 出现 plan 未声明文件: " + ", ".join(outside[:8]))

    dangerous_paths = pattern_hits(combined, DANGEROUS_PATH_PATTERNS)
    if dangerous_paths:
        score -= 2.0
        risk = "HIGH"
        reasons.append("命中危险路径模式: " + ", ".join(dangerous_paths))

    dangerous_commands = pattern_hits(combined, DANGEROUS_COMMAND_PATTERNS)
    if dangerous_commands:
        score -= 2.5
        risk = "HIGH"
        reasons.append("命中危险命令/API 模式: " + ", ".join(dangerous_commands))

    line_check, line_reasons = check_file_line_refs(combined)
    if not line_check["pass"]:
        score -= 1.5
        reasons.extend(line_reasons[:8])

    score = max(0.0, round(score, 2))

    if risk == "HIGH" and score < 6:
        verdict = "REJECT"
    elif risk == "HIGH":
        verdict = "ESCALATE"
    elif score < 7:
        verdict = "ADVISORY"
    else:
        verdict = "ACCEPT"

    return {
        "version": 3,
        "agent": "static_oracle",
        "task_id": task_id,
        "run_id": run_id("static"),
        "verdict": verdict,
        "risk": risk,
        "score": score,
        "checks": {
            "plan_files": sorted(plan_files),
            "executor_files": sorted(executor_files),
            "outside_plan_files": outside,
            "dangerous_paths": dangerous_paths,
            "dangerous_commands": dangerous_commands,
            "file_line_refs": line_check,
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
    verdict = build_verdict(
        task_id=args.task_id,
        plan=read_text(args.plan),
        executor=read_text(args.executor),
        target=args.target,
    )
    out_path = write_verdict(verdict)
    print(str(out_path))
    return 0 if verdict["verdict"] in {"ACCEPT", "ADVISORY"} else 2

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("review")
    p.add_argument("--task-id", required=True)
    p.add_argument("--target")
    p.add_argument("--plan")
    p.add_argument("--executor")
    p.set_defaults(func=review)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())