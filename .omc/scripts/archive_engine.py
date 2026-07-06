#!/usr/bin/env python3
"""
CarrorOS Archive Engine — 10.md §11

Purpose:
  Seal completed task artifacts and write final sovereign verdict.

Constraints:
  - Python 3.10+ standard library only
  - Does not decide step completion
  - Does not alter executor evidence
  - Does not replace VerifyGate or Oracle
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARCHIVE_VERDICTS = {"ARCHIVED", "BLOCKED", "ASK_USER", "REJECTED"}


@dataclass
class ArchiveResult:
    verdict: str
    reason: str
    task_id: str
    task_name: str
    level: str
    archive_path: str | None
    required_action: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "task"


# ── 辅助 ──

def task_id(token: dict[str, Any], fallback: str) -> str:
    return token.get("task", {}).get("id") or fallback


def task_name(token: dict[str, Any], fallback: str) -> str:
    return safe_slug(token.get("task", {}).get("name") or fallback)


def task_level(token: dict[str, Any]) -> str:
    return token.get("session", {}).get("level", "L1_BASE")


def task_status(token: dict[str, Any]) -> str:
    return token.get("task", {}).get("status", "active")


def stats(token: dict[str, Any]) -> tuple[int, int]:
    data = token.get("stats", {}) or {}
    return int(data.get("done", 0) or 0), int(data.get("total", 0) or 0)


def checked_steps(plan_text: str) -> int:
    return len(re.findall(r"^\s*[-*]\s+\[[xX]\]\s+", plan_text, flags=re.M))


def total_steps(plan_text: str) -> int:
    return len(re.findall(r"^\s*[-*]\s+\[[ xX]\]\s+", plan_text, flags=re.M))


def has_unchecked_steps(plan_text: str) -> bool:
    return bool(re.search(r"^\s*[-*]\s+\[\s\]\s+", plan_text, flags=re.M))


def audit_events_for_task(task_id_value: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    audit_root = Path(".omc/audit")
    if not audit_root.exists():
        return events

    for audit_file in sorted(audit_root.glob("*.jsonl")):
        with audit_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("task_id") == task_id_value:
                    events.append(event)
    return events


def latest_oracle_decision(events: list[dict[str, Any]]) -> str | None:
    decisions = [
        event.get("decision")
        for event in events
        if event.get("event_type") == "oracle_decision"
        and event.get("trigger") in {"final_acceptance", "final"}
    ]
    return decisions[-1] if decisions else None


def unresolved_fallback(events: list[dict[str, Any]]) -> tuple[bool, str | None]:
    for event in events:
        if event.get("event_type") != "fallback_event":
            continue
        decision = event.get("decision")
        if decision in {"BLOCKED", "ASK_USER"}:
            return True, str(event.get("reason", "fallback_unresolved"))
        if decision == "DOWNGRADE_TO_BASE" and event.get("risk") == "high":
            return True, "high_risk_downgrade_to_base"
    return False, None


def all_steps_verified(events: list[dict[str, Any]], expected_total: int) -> bool:
    verified = [
        event for event in events
        if event.get("event_type") == "verify_decision"
        and event.get("decision") == "VERIFIED"
    ]
    return len(verified) >= expected_total


def evidence_summary(events: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for event in events:
        if event.get("event_type") != "verify_decision":
            continue
        if event.get("decision") != "VERIFIED":
            continue
        step = event.get("step") or event.get("current_step") or "unknown_step"
        source = None
        ev = event.get("evidence")
        if isinstance(ev, dict):
            source = ev.get("source")
        if source:
            lines.append(f"- {step}: {str(source)[:120]}")
        else:
            lines.append(f"- {step}: VERIFIED")
    return lines


def residual_risk(events: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    for event in events:
        if event.get("event_type") == "oracle_decision":
            value = event.get("residual_risk")
            if isinstance(value, list):
                risks.extend(str(item) for item in value)
            elif isinstance(value, str) and value:
                risks.append(value)
        if event.get("event_type") == "fallback_event" and event.get("decision") == "DOWNGRADE_TO_BASE":
            risks.append(f"fallback: {event.get('reason')}")
    return risks


def fallback_history(events: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for event in events:
        if event.get("event_type") != "fallback_event":
            continue
        rows.append(f"- {event.get('failure_type')}: {event.get('decision')} ({event.get('reason')})")
    return "\n".join(rows) if rows else "- none"


# ── 前置检查 ──

def validate_archive_preconditions(
    token: dict[str, Any],
    plan_text: str,
    executor_text: str,
    events: list[dict[str, Any]],
) -> tuple[bool, str, str | None]:
    """10.md §4 — Archive 前置条件"""
    status = task_status(token)
    if status == "blocked":
        return False, "task_blocked", "resolve blocked task before archive"
    if status == "waiting_user":
        return False, "waiting_user", "resolve user decision before archive"

    if not plan_text:
        return False, "plan_missing", "restore plan.md"
    if not executor_text:
        return False, "executor_missing", "restore executor.md"

    done, total = stats(token)
    plan_done = checked_steps(plan_text)
    plan_total = total_steps(plan_text)

    if total == 0 or plan_total == 0:
        return False, "no_steps", "create plan steps before archive"
    if done != plan_done or total != plan_total:
        return False, "state_conflict", "repair token stats or plan state"
    if has_unchecked_steps(plan_text):
        return False, "verify_not_completed", "complete VerifyGate for all steps"
    if not all_steps_verified(events, plan_total):
        return False, "verify_not_completed", "missing verify_decision VERIFIED events"

    fallback_bad, fallback_reason = unresolved_fallback(events)
    if fallback_bad:
        return False, "fallback_unresolved", fallback_reason

    level = task_level(token)
    if level == "L2_ENHANCE":
        oracle = latest_oracle_decision(events)
        if oracle is None:
            return False, "oracle_final_missing", "run final_acceptance Oracle"
        if oracle in {"REJECT", "ESCALATE"}:
            return False, "oracle_not_accepted", "resolve Oracle REJECT/ESCALATE"
        if oracle not in {"ACCEPT", "WARN"}:
            return False, "oracle_invalid", "repair Oracle final decision"

    return True, "ok", None


# ── 文件复制 ──

def copy_if_exists(source: Path, dest: Path) -> bool:
    if not source.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return True


# ── 报告生成 ──

def generate_final_report(
    token: dict[str, Any],
    plan_text: str,
    events: list[dict[str, Any]],
    archive_path: Path,
) -> str:
    """10.md §7 — final-report.md 模板"""
    tid = task_id(token, archive_path.name)
    name = task_name(token, archive_path.name)
    level = task_level(token)
    done, total = stats(token)
    oracle = latest_oracle_decision(events) or "N/A"
    risks = residual_risk(events)
    evidence = evidence_summary(events)

    goal = token.get("task", {}).get("goal", "")
    scope = token.get("task", {}).get("scope", []) or []
    changed_files = token.get("task", {}).get("changed_files", []) or []

    def bullet(items, fallback="- none"):
        if not items:
            return fallback
        return "\n".join(f"- {str(item)}" for item in items)

    return f"""# CarrorOS Final Report

## Task
- id: {tid}
- name: {name}
- level: {level}
- status: archived
- archived_at: {now_iso()}

## Goal
{goal or "N/A"}

## Scope
{bullet(scope)}

## Completion
- total_steps: {total}
- verified_steps: {done}
- verify_gate: passed
- oracle_final: {oracle}

## Evidence Summary
{chr(10).join(evidence) if evidence else "- VERIFIED events recorded in audit"}

## Changed Files
{bullet(changed_files)}

## Fallback History
{fallback_history(events)}

## Residual Risk
{bullet(risks)}

## Archive Basis
- VerifyGate: all planned steps VERIFIED
- Oracle: {oracle}
- Fallback: no unresolved event
- Audit: sealed
- Scope: unchanged

## Sovereign Verdict
ARCHIVED
"""


def write_audit_slice(path: Path, events: list[dict[str, Any]]) -> None:
    """10.md §10 — audit-slice.jsonl"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


# ── 主函数 ──

def archive_task(token_path: Path, task_path: Path) -> ArchiveResult:
    """10.md §11 — archive_task 主流程"""
    token = read_json(token_path, {})
    tid = task_id(token, token_path.stem)
    name = task_name(token, task_path.name)
    level = task_level(token)

    plan_path = task_path / "plan.md"
    executor_path = task_path / "executor.md"
    handoff_path = task_path / "state" / "session-handoff.md"
    oracle_verdicts_path = task_path / "oracle-verdicts.md"
    error_dna_path = task_path / "state" / "error-dna.json"

    plan_text = read_text(plan_path)
    executor_text = read_text(executor_path)
    events = audit_events_for_task(tid)

    # §4 前置检查
    ok, reason, action = validate_archive_preconditions(token, plan_text, executor_text, events)
    if not ok:
        return ArchiveResult("BLOCKED", reason, tid, name, level, None, action)

    # 创建归档目录
    archive_path = Path(".omc/archive") / today() / name
    archive_path.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []

    # 复制文件
    file_map = [
        ("plan", plan_path, archive_path / "plan.md"),
        ("executor", executor_path, archive_path / "executor.md"),
        ("session_handoff", handoff_path, archive_path / "session-handoff.md"),
        ("oracle_verdicts", oracle_verdicts_path, archive_path / "oracle-verdicts.md"),
        ("error_dna", error_dna_path, archive_path / "error-dna.json"),
    ]
    for kind, source, dest in file_map:
        if copy_if_exists(source, dest):
            copied.append({"kind": kind, "source": str(source), "archive": str(dest), "sha256": sha256_file(dest)})

    # final-report.md
    report_path = archive_path / "final-report.md"
    write_text(report_path, generate_final_report(token, plan_text, events, archive_path))
    copied.append({"kind": "final_report", "source": "generated", "archive": str(report_path), "sha256": sha256_file(report_path)})

    # audit-slice.jsonl
    audit_slice_path = archive_path / "audit-slice.jsonl"
    write_audit_slice(audit_slice_path, events)
    copied.append({"kind": "audit_slice", "source": ".omc/audit/*.jsonl", "archive": str(audit_slice_path), "sha256": sha256_file(audit_slice_path)})

    # sovereign-verdict.json — §6
    risks = residual_risk(events)
    oracle = latest_oracle_decision(events) or "N/A"
    verdict = {
        "verdict": "ARCHIVED",
        "timestamp": now_iso(),
        "task_id": tid,
        "task_name": name,
        "level": level,
        "basis": {
            "verify_gate": "all_steps_verified",
            "oracle": oracle,
            "fallback": "no_unresolved_fallback",
            "audit": "sealed",
            "scope": "unchanged",
        },
        "residual_risk": risks,
        "archive_path": str(archive_path),
    }
    verdict_path = archive_path / "sovereign-verdict.json"
    write_json_atomic(verdict_path, verdict)
    copied.append({"kind": "sovereign_verdict", "source": "generated", "archive": str(verdict_path), "sha256": sha256_file(verdict_path)})

    # token-tombstone.json — §9
    tombstone = {
        "task_id": tid,
        "task_name": name,
        "status": "archived",
        "level": level,
        "archived_at": now_iso(),
        "archive_path": str(archive_path),
        "final_verdict": "ARCHIVED",
        "stats": token.get("stats", {}),
        "active_token_path": str(token_path),
        "deleted_active_token": False,
    }
    tombstone_path = archive_path / "token-tombstone.json"
    write_json_atomic(tombstone_path, tombstone)
    copied.append({"kind": "token_tombstone", "source": str(token_path), "archive": str(tombstone_path), "sha256": sha256_file(tombstone_path)})

    # manifest.json — §8
    manifest = {
        "task_id": tid,
        "task_name": name,
        "archived_at": now_iso(),
        "level": level,
        "files": copied,
        "audit_slice": str(audit_slice_path),
    }
    manifest_path = archive_path / "manifest.json"
    write_json_atomic(manifest_path, manifest)

    # archive_completed audit event
    append_jsonl(
        Path(".omc/audit") / f"{today()}.jsonl",
        {
            "event_type": "archive_completed",
            "timestamp": now_iso(),
            "task_id": tid,
            "level": level,
            "phase": "archive",
            "actor": "archive_engine",
            "decision": "ARCHIVED",
            "archive_path": str(archive_path),
            "paths": [str(manifest_path), str(report_path), str(verdict_path), str(tombstone_path)],
        },
    )

    return ArchiveResult("ARCHIVED", "archive_completed", tid, name, level, str(archive_path))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="CarrorOS Archive Engine")
    parser.add_argument("--token", required=True, help="Path to .omc/tokens/{date}/{task_name}.json")
    parser.add_argument("--task", required=True, help="Path to .omc/tasks/{date}/{task_name}")
    args = parser.parse_args()

    result = archive_task(Path(args.token), Path(args.task))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.verdict == "ARCHIVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
