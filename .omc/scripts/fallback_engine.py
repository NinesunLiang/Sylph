#!/usr/bin/env python3
"""
fallback_engine.py — CarrorOS Fallback Protocol

8.md §17 核心实现

Purpose:
  Convert capability failures into auditable governance decisions.
  15 failure types, 4 decisions: CONTINUE / DOWNGRADE_TO_BASE / ASK_USER / BLOCKED

Usage:
  python3 fallback_engine.py <failure_type> [risk] [token_path]

Constraints:
  - Python 3.10+ standard library only
  - Does not mark plan steps done
  - Does not alter executor evidence
  - Does not replace VerifyGate or Oracle
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_FAILURE_TYPES = {
    "enhance_model_unavailable",
    "oracle_unavailable",
    "meta_oracle_unavailable",
    "context_watermark_unobservable",
    "cli_hook_failed",
    "python_script_failed",
    "audit_write_failed",
    "state_conflict",
    "verify_not_completed",
    "scope_violation",
    "authorization_missing",
    "production_approval_missing",
    "dependency_risk_unreviewed",
    "resume_state_unrecoverable",
    "unknown_failure",
}

VALID_DECISIONS = {
    "CONTINUE",
    "DOWNGRADE_TO_BASE",
    "ASK_USER",
    "BLOCKED",
}

HIGH_RISK_HINTS = {
    "auth_change",
    "payment_change",
    "permission_change",
    "production",
    "migration",
    "dependency_change",
    "cross_module",
    "irreversible",
}


@dataclass
class FallbackDecision:
    decision: str
    failure_type: str
    reason: str
    level_before: str
    level_after: str
    risk: str
    requires_user: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def task_id_from_token(token: dict[str, Any]) -> str:
    return token.get("task", {}).get("id", "unknown_task")


def current_step_from_token(token: dict[str, Any]) -> str | None:
    return token.get("task", {}).get("current_step")


def level_from_token(token: dict[str, Any]) -> str:
    return token.get("session", {}).get("level", "L1_BASE")


def risk_from_token(token: dict[str, Any], explicit_risk: str | None = None) -> str:
    if explicit_risk in {"low", "medium", "high"}:
        return explicit_risk

    hints = set(token.get("task", {}).get("risk_hints", []) or [])
    if hints & HIGH_RISK_HINTS:
        return "high"

    diff = token.get("task", {}).get("diff_summary", {}) or {}
    files_changed = int(diff.get("files_changed", 0) or 0)
    insertions = int(diff.get("insertions", 0) or 0)
    deletions = int(diff.get("deletions", 0) or 0)

    if files_changed >= 5 or insertions + deletions >= 500:
        return "medium"

    return "low"


def decide(failure_type: str, token: dict[str, Any], explicit_risk: str | None = None) -> FallbackDecision:
    if failure_type not in VALID_FAILURE_TYPES:
        failure_type = "unknown_failure"

    level = level_from_token(token)
    risk = risk_from_token(token, explicit_risk)

    non_downgradeable = {
        "audit_write_failed",
        "state_conflict",
        "verify_not_completed",
        "scope_violation",
        "production_approval_missing",
        "resume_state_unrecoverable",
        "python_script_failed",
        "unknown_failure",
    }

    if failure_type in non_downgradeable:
        return FallbackDecision(
            "BLOCKED",
            failure_type,
            f"{failure_type}:non_downgradeable",
            level,
            level,
            "high" if failure_type != "verify_not_completed" else risk,
            failure_type != "verify_not_completed",
        )

    if failure_type == "cli_hook_failed":
        return FallbackDecision(
            "CONTINUE",
            failure_type,
            "cli_hook_failed:status_display_only",
            level,
            level,
            risk,
            False,
        )

    if failure_type == "context_watermark_unobservable":
        return FallbackDecision(
            "DOWNGRADE_TO_BASE",
            failure_type,
            "context_watermark_unobservable:base_fallback",
            level,
            "L1_BASE",
            "low",
            False,
        )

    if failure_type in {
        "enhance_model_unavailable",
        "oracle_unavailable",
        "meta_oracle_unavailable",
    }:
        if risk == "high":
            return FallbackDecision(
                "BLOCKED",
                failure_type,
                f"{failure_type}:high_risk_requires_enhance",
                level,
                level,
                risk,
                True,
            )
        if risk == "medium":
            return FallbackDecision(
                "ASK_USER",
                failure_type,
                f"{failure_type}:medium_risk_requires_user",
                level,
                level,
                risk,
                True,
            )
        return FallbackDecision(
            "DOWNGRADE_TO_BASE",
            failure_type,
            f"{failure_type}:low_risk_base_fallback",
            level,
            "L1_BASE",
            risk,
            False,
        )

    if failure_type in {"authorization_missing", "dependency_risk_unreviewed"}:
        if risk == "high":
            return FallbackDecision(
                "BLOCKED",
                failure_type,
                f"{failure_type}:high_risk_blocked",
                level,
                level,
                risk,
                True,
            )
        return FallbackDecision(
            "ASK_USER",
            failure_type,
            f"{failure_type}:requires_user_decision",
            level,
            level,
            risk,
            True,
        )

    return FallbackDecision(
        "BLOCKED",
        "unknown_failure",
        "unknown_failure:blocked",
        level,
        level,
        "high",
        True,
    )


def update_token(token_path: Path, token: dict[str, Any], decision: FallbackDecision) -> None:
    token.setdefault("task", {})
    token.setdefault("session", {})

    if decision.decision == "DOWNGRADE_TO_BASE":
        token["session"]["level"] = "L1_BASE"
        token["session"]["compact_strategy"] = "rounds"
        token["session"]["compact_threshold"] = [15, 20]
        token["session"]["fallback"] = {
            "timestamp": now_iso(),
            "from_level": decision.level_before,
            "reason": decision.failure_type,
        }

    elif decision.decision == "ASK_USER":
        token["task"]["status"] = "waiting_user"
        token["task"]["blocked"] = None
        token["task"]["fallback"] = {
            "reason": decision.reason,
            "requires_decision": True,
        }

    elif decision.decision == "BLOCKED":
        token["task"]["status"] = "blocked"
        token["task"]["blocked"] = decision.reason
        token["task"]["fallback"] = {
            "timestamp": now_iso(),
            "reason": decision.failure_type,
            "recovery_required": True,
        }

    write_json_atomic(token_path, token)


def append_handoff(path: Path, decision: FallbackDecision) -> None:
    if decision.decision == "CONTINUE":
        return

    text = (
        "\n## Fallback\n\n"
        f"- timestamp: {now_iso()}\n"
        f"- failure_type: {decision.failure_type}\n"
        f"- decision: {decision.decision}\n"
        f"- level_before: {decision.level_before}\n"
        f"- level_after: {decision.level_after}\n"
        f"- reason: {decision.reason}\n"
        f"- resume_mode: {decision.level_after}\n"
    )
    append_text(path, text)


def append_executor_note(path: Path, token: dict[str, Any], decision: FallbackDecision) -> None:
    if decision.decision == "CONTINUE":
        return

    text = (
        "\n## Fallback\n\n"
        f"- timestamp: {now_iso()}\n"
        f"- failure_type: {decision.failure_type}\n"
        f"- decision: {decision.decision}\n"
        f"- reason: {decision.reason}\n"
        f"- current_step: {current_step_from_token(token)}\n"
    )
    append_text(path, text)


def write_audit(token: dict[str, Any], decision: FallbackDecision, paths: list[str]) -> None:
    audit_dir = Path(".omc/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{today()}.jsonl"

    event = {
        "event_type": "fallback_event",
        "timestamp": now_iso(),
        "task_id": task_id_from_token(token),
        "level_before": decision.level_before,
        "level_after": decision.level_after,
        "phase": "fallback",
        "current_step": current_step_from_token(token),
        "actor": "fallback_engine",
        "failure_type": decision.failure_type,
        "decision": decision.decision,
        "reason": decision.reason,
        "paths": paths,
        "risk": decision.risk,
        "requires_user": decision.requires_user,
    }

    required = {
        "event_type", "timestamp", "task_id", "level_before", "level_after",
        "phase", "current_step", "actor", "failure_type", "decision", "reason",
        "paths", "risk", "requires_user",
    }
    missing = [key for key in required if key not in event]
    if missing:
        raise OSError("audit_field_missing:" + ",".join(missing))

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def task_paths(token: dict[str, Any]) -> tuple[Path, Path, list[str]]:
    tid = task_id_from_token(token)
    date = today()
    handoff = Path(".omc/tasks") / date / tid / "state" / "session-handoff.md"
    executor = Path(".omc/tasks") / date / tid / "executor.md"
    path_strings = [
        str(Path(".omc/tokens") / date / f"{tid}.json"),
        str(handoff),
        str(executor),
    ]
    return handoff, executor, path_strings


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: fallback_engine.py <failure_type> [risk] [token_path]"}, indent=2))
        return 2

    failure_type = sys.argv[1]
    explicit_risk = sys.argv[2] if len(sys.argv) >= 3 else None
    token_path = Path(sys.argv[3]) if len(sys.argv) >= 4 else Path(".omc/state/token.json")

    token = read_json(token_path, {})
    decision = decide(failure_type, token, explicit_risk)

    try:
        handoff_path, executor_path, audit_paths = task_paths(token)
        update_token(token_path, token, decision)
        append_handoff(handoff_path, decision)
        append_executor_note(executor_path, token, decision)
        write_audit(token, decision, audit_paths)
    except OSError as exc:
        fallback = FallbackDecision(
            "BLOCKED",
            "audit_write_failed",
            "audit_write_failed:cant_persist_fallback",
            decision.level_before,
            decision.level_before,
            "high",
            True,
        )
        print(json.dumps(asdict(fallback), ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
    return 0 if decision.decision in {"CONTINUE", "DOWNGRADE_TO_BASE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
