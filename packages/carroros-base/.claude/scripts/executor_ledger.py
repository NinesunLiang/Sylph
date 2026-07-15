#!/usr/bin/env python3
"""
CarrorOS Executor Evidence Ledger

Purpose:
  Record execution facts (command output, file changes, assertions, user confirmations)
  as standardized evidence in executor.md.
  Does NOT decide step completion - that's VerifyGate's job.

Commands:
  python3 executor_ledger.py command <payload.json> [context_mode]
  python3 executor_ledger.py file_assertion <payload.json>
  python3 executor_ledger.py file_change <payload.json>
  python3 executor_ledger.py user_confirmation <payload.json>

Evidence levels:
  E3 command exit=0  (strongest)
  E2 file_assertion / file_change
  E1 user_confirmation
  E0 narrative (never used as completion evidence)

Constraints:
  - Python 3.10+ standard library only
  - Records facts, does not decide completion
  - Redacts sensitive output
  - Append-only ledger
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LIMITS = {
    "normal": {"output_head_chars": 1000, "output_tail_chars": 2000, "max_output_chars": 3000},
    "mid_context": {"output_head_chars": 500, "output_tail_chars": 1000, "max_output_chars": 1500},
    "high_context": {"output_head_chars": 0, "output_tail_chars": 800, "max_output_chars": 800},
}

SECRET_PATTERNS = [
    r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    r"(?i)authorization:\s*bearer\s+[a-z0-9._\-]+",
]


@dataclass
class Evidence:
    evidence_id: str
    step: str
    type: str
    evidence_level: str
    timestamp: str
    source: str | None = None
    exit_code: int | None = None
    output_head: str | None = None
    output_tail: str | None = None
    duration_ms: int | None = None
    file: str | None = None
    line: int | None = None
    assertion: str | None = None
    snippet_hash: str | None = None
    change_summary: str | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    confirmation: str | None = None
    scope: str | None = None


@dataclass
class Failure:
    failure_id: str
    step: str
    action: str
    exit_code: int | None
    reason: str
    retryable: bool
    timestamp: str
    output_tail: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def event_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}"


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
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


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.DOTALL)
    return redacted


def truncate_output(output: str, mode: str = "normal") -> tuple[str | None, str | None]:
    limits = DEFAULT_LIMITS.get(mode, DEFAULT_LIMITS["normal"])
    clean = redact_secrets(output)

    max_chars = limits["max_output_chars"]
    if len(clean) > max_chars:
        clean = clean[: limits["output_head_chars"]] + "\n...[truncated]...\n" + clean[-limits["output_tail_chars"]:]

    head_chars = limits["output_head_chars"]
    tail_chars = limits["output_tail_chars"]

    output_head = clean[:head_chars] if head_chars > 0 else None
    output_tail = clean[-tail_chars:] if tail_chars > 0 else None
    return output_head, output_tail


def infer_evidence_level(evidence_type: str) -> str:
    if evidence_type == "command":
        return "E3"
    if evidence_type in ("file_change", "file_assertion", "dependency_change"):
        return "E2"
    if evidence_type == "user_confirmation":
        return "E1"
    return "E0"


def validate_evidence(evidence: Evidence) -> list[str]:
    errors: list[str] = []

    if not evidence.step:
        errors.append("missing_step")
    if evidence.type not in ("command", "file_change", "file_assertion", "user_confirmation", "dependency_change"):
        errors.append("invalid_evidence_type")

    if evidence.type == "command":
        if evidence.source is None:
            errors.append("command_missing_source")
        if evidence.exit_code is None:
            errors.append("command_missing_exit_code")

    if evidence.type == "file_assertion":
        if not evidence.file:
            errors.append("file_assertion_missing_file")
        if not evidence.assertion:
            errors.append("file_assertion_missing_assertion")

    if evidence.type == "file_change":
        if not evidence.file:
            errors.append("file_change_missing_file")
        if not evidence.change_summary:
            errors.append("file_change_missing_summary")

    if evidence.type == "user_confirmation":
        if not evidence.confirmation:
            errors.append("user_confirmation_missing_text")
        vague = ["可以", "继续", "都行", "你看着办", "应该没问题"]
        if evidence.confirmation and evidence.confirmation.strip() in vague:
            errors.append("user_confirmation_not_atomic")

    return errors


def render_evidence_md(evidence: Evidence) -> str:
    lines = [
        f"\n### {evidence.evidence_id}",
        f"- step: {evidence.step}",
        f"- type: {evidence.type}",
        f"- evidence_level: {evidence.evidence_level}",
        f"- timestamp: {evidence.timestamp}",
    ]

    for key, value in asdict(evidence).items():
        if key in ("evidence_id", "step", "type", "evidence_level", "timestamp"):
            continue
        if value is not None:
            safe_value = str(value).replace("\n", "\\n")
            lines.append(f"- {key}: {safe_value}")

    return "\n".join(lines) + "\n"


def render_failure_md(failure: Failure) -> str:
    lines = [
        f"\n### {failure.failure_id}",
        f"- step: {failure.step}",
        f"- action: {failure.action}",
        f"- exit_code: {failure.exit_code}",
        f"- reason: {failure.reason}",
        f"- retryable: {str(failure.retryable).lower()}",
        f"- timestamp: {failure.timestamp}",
    ]
    if failure.output_tail:
        lines.append(f"- output_tail: {failure.output_tail.replace(chr(10), '\\n')}")
    return "\n".join(lines) + "\n"


def ensure_executor_sections(path: Path) -> None:
    if path.exists():
        return
    append_text(
        path,
        "# Executor\n\n"
        "## Current Step\n"
        "step: <unset>\n"
        "status: running\n\n"
        "## Evidence\n\n"
        "## Failures\n\n"
        "## Retries\n",
    )


def append_evidence(executor_path: Path, evidence: Evidence) -> None:
    errors = validate_evidence(evidence)
    if errors:
        raise ValueError("invalid evidence: " + ", ".join(errors))

    ensure_executor_sections(executor_path)
    append_text(executor_path, render_evidence_md(evidence))


def append_failure(executor_path: Path, failure: Failure) -> None:
    ensure_executor_sections(executor_path)
    append_text(executor_path, "\n## Failure Entry\n")
    append_text(executor_path, render_failure_md(failure))


def update_token_failure(token_path: Path, reason: str) -> None:
    token = read_json(token_path, {})
    token.setdefault("task", {})
    token["task"]["failed_verifications"] = int(token["task"].get("failed_verifications", 0)) + 1
    token["task"]["last_failure"] = reason
    write_json(token_path, token)


def write_audit(
    token: dict[str, Any],
    event_type: str,
    action: str,
    reason: str,
    evidence_summary: dict[str, Any],
    risk: str = "low",
) -> None:
    audit_dir = Path(".omc/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

    event = {
        "event_type": event_type,
        "timestamp": now_iso(),
        "task_id": token.get("task", {}).get("id", "unknown_task"),
        "level": token.get("session", {}).get("level", "unknown_level"),
        "phase": "execute",
        "current_step": token.get("task", {}).get("current_step"),
        "actor": "model",
        "action": action,
        "paths": [".omc/tasks/*/executor.md"],
        "decision": "RECORDED",
        "reason": reason,
        "evidence": evidence_summary,
        "risk": risk,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def record_command(payload: dict[str, Any], mode: str, executor_path: Path) -> int:
    token = read_json(Path(".omc/state/token.json"), {})
    output = payload.get("output", "")
    head, tail = truncate_output(output, mode)

    step = payload["step"]
    command = payload["command"]
    exit_code = int(payload["exit_code"])

    if exit_code != 0:
        failure = Failure(
            failure_id=event_id("FAIL"),
            step=step,
            action=f"command:{command}",
            exit_code=exit_code,
            reason=payload.get("reason", "test_failed"),
            retryable=bool(payload.get("retryable", True)),
            timestamp=now_iso(),
            output_tail=tail,
        )
        append_failure(executor_path, failure)
        update_token_failure(Path(".omc/state/token.json"), failure.reason)
        write_audit(
            token,
            "execution_event",
            "record_failure",
            failure.reason,
            {"type": "failure", "source": command, "exit_code": exit_code, "summary": tail},
            risk="medium",
        )
        return 1

    evidence = Evidence(
        evidence_id=event_id("EV"),
        step=step,
        type="command",
        evidence_level="E3",
        timestamp=now_iso(),
        source=command,
        exit_code=exit_code,
        output_head=head,
        output_tail=tail,
        duration_ms=payload.get("duration_ms"),
    )
    append_evidence(executor_path, evidence)
    write_audit(
        token,
        "execution_event",
        "record_evidence",
        "command_exit_0",
        {"type": "command", "source": command, "exit_code": exit_code, "summary": tail},
    )
    return 0


def record_file_assertion(payload: dict[str, Any], executor_path: Path) -> int:
    token = read_json(Path(".omc/state/token.json"), {})
    snippet = payload.get("snippet", "")

    evidence = Evidence(
        evidence_id=event_id("EV"),
        step=payload["step"],
        type="file_assertion",
        evidence_level="E2",
        timestamp=now_iso(),
        file=payload["file"],
        line=payload.get("line"),
        assertion=payload["assertion"],
        snippet_hash=sha256_text(snippet) if snippet else payload.get("snippet_hash"),
    )
    append_evidence(executor_path, evidence)
    write_audit(
        token,
        "execution_event",
        "record_evidence",
        "file_assertion_recorded",
        {"type": "file_assertion", "file": payload["file"], "assertion": payload["assertion"]},
    )
    return 0


def record_file_change(payload: dict[str, Any], executor_path: Path) -> int:
    token = read_json(Path(".omc/state/token.json"), {})
    evidence = Evidence(
        evidence_id=event_id("EV"),
        step=payload["step"],
        type="file_change",
        evidence_level="E2",
        timestamp=now_iso(),
        file=payload["file"],
        change_summary=payload["change_summary"],
        before_hash=payload.get("before_hash"),
        after_hash=payload.get("after_hash"),
    )
    append_evidence(executor_path, evidence)
    write_audit(
        token,
        "execution_event",
        "record_evidence",
        "file_change_recorded",
        {"type": "file_change", "file": payload["file"], "summary": payload["change_summary"]},
    )
    return 0


def record_user_confirmation(payload: dict[str, Any], executor_path: Path) -> int:
    token = read_json(Path(".omc/state/token.json"), {})
    evidence = Evidence(
        evidence_id=event_id("EV"),
        step=payload["step"],
        type="user_confirmation",
        evidence_level="E1",
        timestamp=now_iso(),
        confirmation=payload["confirmation"],
        scope=payload.get("scope"),
    )
    append_evidence(executor_path, evidence)
    write_audit(
        token,
        "execution_event",
        "record_evidence",
        "user_confirmation_recorded",
        {"type": "user_confirmation", "summary": payload["confirmation"]},
    )
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: executor_ledger.py <command|file_assertion|file_change|user_confirmation> <payload.json> [mode] [executor_path]",
            file=sys.stderr,
        )
        return 2

    kind = sys.argv[1]
    payload_path = Path(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) >= 4 else "normal"
    executor_path = Path(sys.argv[4]) if len(sys.argv) >= 5 else Path(".omc/tasks/current/executor.md")

    payload = read_json(payload_path)

    if kind == "command":
        return record_command(payload, mode, executor_path)
    if kind == "file_assertion":
        return record_file_assertion(payload, executor_path)
    if kind == "file_change":
        return record_file_change(payload, executor_path)
    if kind == "user_confirmation":
        return record_user_confirmation(payload, executor_path)

    print(f"unsupported evidence kind: {kind}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
