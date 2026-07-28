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
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_FAILURE_TYPES = {
    "enhance_model_unavailable",
    "oracle_unavailable",
    "meta_oracle_unavailable",
    "context_watermark_unobservable",
    "context_overflow",       # context 窗口超 70%，跳过重试
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


_LOCK_FD: int | None = None  # module-level lock file descriptor


def _acquire_token_lock(token_path: Path, timeout: float = 5.0) -> bool:
    """Advisory shared file lock on token.json via lock file.

    Prevents concurrent writes from multiple gates (Grok P0 finding).
    Uses a .lock sidecar file with timeout. Retry 3x with 0.5s backoff.
    """
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    deadline = time.monotonic() + timeout
    global _LOCK_FD
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            _LOCK_FD = fd
            os.write(fd, str(os.getpid()).encode())
            return True
        except FileExistsError:
            # Check if lock is stale (>10s old)
            try:
                lock_age = time.monotonic() - lock_path.stat().st_mtime
                if lock_age > 10.0:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(0.5)
    return False


def _release_token_lock() -> None:
    """Release the advisory lock."""
    global _LOCK_FD
    if _LOCK_FD is not None:
        try:
            os.close(_LOCK_FD)
        except OSError:
            pass
        _LOCK_FD = None


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


def task_id_from_token(token: dict[str, Any] | None) -> str:
    if not token:
        return "unknown_task"
    task = token.get("task") or {}
    return (
        task.get("id")
        or token.get("session", {}).get("id")
        or "unknown_task"
    )


def current_step_from_token(token: dict[str, Any] | None) -> str | None:
    if not token:
        return None
    task = token.get("task") or {}
    return task.get("current_step")


def level_from_token(token: dict[str, Any] | None) -> str:
    if not token:
        return "L1_BASE"
    return token.get("session", {}).get("level", "L1_BASE")


def risk_from_token(token: dict[str, Any] | None, explicit_risk: str | None = None) -> str:
    if not token:
        return "low"
    if explicit_risk in {"low", "medium", "high"}:
        return explicit_risk

    hints = set((token.get("task") or {}).get("risk_hints", []) or [])
    if hints & HIGH_RISK_HINTS:
        return "high"

    diff = (token.get("task") or {}).get("diff_summary", {}) or {}
    files_changed = int(diff.get("files_changed", 0) or 0)
    insertions = int(diff.get("insertions", 0) or 0)
    deletions = int(diff.get("deletions", 0) or 0)

    if files_changed >= 5 or insertions + deletions >= 500:
        return "medium"

    return "low"


def decide(failure_type: str, token: dict[str, Any], explicit_risk: str | None = None, context_usage_pct: float | None = None) -> FallbackDecision:
    if failure_type not in VALID_FAILURE_TYPES:
        failure_type = "unknown_failure"

    # Context 溢出检测：超过 70% 窗口，强制 SKIP 不重试
    if context_usage_pct is not None and context_usage_pct > 70.0:
        return FallbackDecision(
            "BLOCKED",
            "context_overflow",
            f"context_overflow:{context_usage_pct:.0f}%_exceeds_70%_threshold",
            level_from_token(token),
            level_from_token(token),
            "high",
            False,  # 不阻塞用户，自动跳过
        )

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

    # context_overflow 直通 SKIP（已在入口检测，这里兜底）
    if failure_type == "context_overflow":
        return FallbackDecision(
            "BLOCKED",
            "context_overflow",
            f"context_overflow:throttled_by_context_window",
            level,
            level,
            "high",
            False,
        )

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
    # 处理 JSON null 值: setdefault 不会覆盖已有的 None
    token["task"] = token.get("task") or {}
    token["session"] = token.get("session") or {}

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
        # Check for governance recovery lock before writing recovery_required
        governance = token.get("governance") if isinstance(token.get("governance"), dict) else {}
        if governance.get("recovery_lock") is True:
            # Locked: do NOT overwrite recovery_ack, skip recovery_required
            token["task"]["status"] = "blocked"
            token["task"]["blocked"] = decision.reason
            token["task"]["fallback"] = {
                "timestamp": now_iso(),
                "reason": decision.failure_type,
                "recovery_required": False,
                "recovery_ack": True,
                "recovery_lock_active": True,
                "note": "Recovery lock active: fallback engine skipped recovery_required write",
            }
        else:
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

    # 重试历史截断：只保留最近 2 次失败上下文
    _truncate_retry_history(path)


def _truncate_retry_history(path: Path, max_entries: int = 2) -> None:
    """截断 executor.md 中的 Fallback 记录，采用夹心饼干策略

    保留: 首条错误(First Error) + 最后 N 条重试
    防止: 丢失关键初始错误上下文

    DeepSeek V4 Flash 在长 context 下重试越多越失败。
    截断早期失败历史，避免衰退循环，同时保留根因。
    """
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8", errors="replace")
    # 按 ## Fallback 分割
    parts = content.split("\n## Fallback\n\n")
    if len(parts) <= max_entries + 1:
        return  # 不需要截断
    # 夹心饼干策略: 首条(parts[1]) + 最后 max_entries-1 条
    first = parts[1]
    kept = parts[0] + "\n## Fallback\n\n" + first
    # 如果 max_entries > 1，再加最后 (max_entries-1) 条
    if max_entries > 1:
        kept += "".join(
            "\n## Fallback\n\n" + p for p in parts[-(max_entries - 1):]
        )
    path.write_text(kept, encoding="utf-8")


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

    # 读取 context watermark 判断是否进入 context 溢出模式
    context_pct = None
    try:
        wm_path = Path(".omc/state/context-watermark.json")
        if wm_path.exists():
            wm = json.loads(wm_path.read_text())
            context_pct = float(wm.get("pct", wm.get("level_pct", 0)))
    except (json.JSONDecodeError, OSError, ValueError):
        pass

    token = read_json(token_path, {})
    decision = decide(failure_type, token, explicit_risk, context_pct)

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
