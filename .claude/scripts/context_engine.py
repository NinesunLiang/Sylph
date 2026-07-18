#!/usr/bin/env python3
"""
CarrorOS Context Engine

Purpose:
  Manage compact / resume / state injection without creating completion facts.

Commands:
  compact-check   --token <path> [--task <path>]
  resume-check    --token <path> --task <path>
  state-injection --token <path>

Constraints:
  - Python 3.10+ standard library only
  - Does not mark plan steps done
  - Does not alter executor evidence
  - Does not replace VerifyGate / Oracle / Fallback
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 从自身位置定位项目根目录
_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]  # .claude/scripts/ → .claude/ → 项目根
if not (ROOT / ".claude").is_dir():
    ROOT = Path(".").resolve()
os.chdir(str(ROOT))


@dataclass
class ContextDecision:
    decision: str
    reason: str
    task_id: str
    task_name: str
    level: str
    current_step: str | None
    compact_strategy: str
    requires_fallback: bool = False
    failure_type: str | None = None


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


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def token_task(token: dict[str, Any]) -> dict[str, Any]:
    task = token.get("task", {})
    # 兼容非 carros token（如 lx-goal 物理锁：task 是字符串）
    return task if isinstance(task, dict) else {}


def token_session(token: dict[str, Any]) -> dict[str, Any]:
    session = token.get("session", {})
    return session if isinstance(session, dict) else {}


def task_id(token: dict[str, Any], fallback: str = "unknown_task") -> str:
    return token_task(token).get("id") or fallback


def task_name(token: dict[str, Any], fallback: str = "task") -> str:
    return token_task(token).get("name") or fallback


def level(token: dict[str, Any]) -> str:
    return token_session(token).get("level", "L1_BASE")


def current_step(token: dict[str, Any]) -> str | None:
    return token_task(token).get("current_step")


def count_plan_steps(plan_text: str) -> tuple[int, int, str | None]:
    total = len(re.findall(r"^\s*[-*]\s+\[[ xX]\]\s+", plan_text, flags=re.M))
    done = len(re.findall(r"^\s*[-*]\s+\[[xX]\]\s+", plan_text, flags=re.M))
    pending_match = re.search(r"^\s*[-*]\s+\[\s\]\s+(.+)$", plan_text, flags=re.M)
    pending = pending_match.group(1).strip() if pending_match else None
    return done, total, pending


def compact_decision(token: dict[str, Any]) -> tuple[str, str, str, bool, str | None]:
    session = token_session(token)
    lvl = level(token)

    if lvl == "L2_ENHANCE":
        watermark = session.get("context_watermark")
        if not isinstance(watermark, (int, float)):
            return (
                "DOWNGRADE_REQUIRED",
                "context_watermark_unobservable",
                "watermark",
                True,
                "context_watermark_unobservable",
            )
        if watermark >= 85:
            return ("COMPACT_NOW", "watermark_ge_85", "watermark", False, None)
        if watermark >= 70:
            return ("COMPACT_SOON", "watermark_ge_70", "watermark", False, None)
        return ("CONTINUE", "watermark_lt_70", "watermark", False, None)

    turn = int(session.get("turn", 0) or 0)
    if turn >= 20:
        return ("COMPACT_NOW", "turn_ge_20", "rounds", False, None)
    if turn >= 15:
        return ("COMPACT_SOON", "turn_ge_15", "rounds", False, None)
    return ("CONTINUE", "turn_lt_15", "rounds", False, None)


def build_handoff(token: dict[str, Any], plan_text: str, decision: str, reason: str) -> str:
    task = token_task(token)
    session = token_session(token)
    done, total, pending = count_plan_steps(plan_text)

    scope = task.get("scope", []) or []
    risks = task.get("risk_hints", []) or []
    changed_files = task.get("changed_files", []) or []

    def bullet(items: list[Any], fallback: str = "- none") -> str:
        if not items:
            return fallback
        return "\n".join(f"- {str(item)}" for item in items)

    return f"""# Session Handoff

## Task
- id: {task_id(token)}
- name: {task_name(token)}
- level: {level(token)}
- status: {task.get("status", "active")}
- current_step: {current_step(token)}

## Goal
{task.get("goal", "N/A")}

## Scope Freeze
{bullet(scope)}

## Progress
- total_steps: {total}
- verified_steps: {done}
- pending_step: {pending or "none"}

## Current Work
- step: {current_step(token)}
- files_in_scope:
{bullet(changed_files)}

## Risks
{bullet(risks)}

## Context
- compact_strategy: {session.get("compact_strategy", "rounds")}
- context_watermark: {session.get("context_watermark", "unknown")}
- turn: {session.get("turn", 0)}
- compact_status: {decision}
- compact_reason: {reason}

## Oracle
- last_verdict: {session.get("oracle_last_verdict", "none")}
- residual_risk: {len(session.get("residual_risk", []) or [])}

## Fallback
- unresolved: {bool(task.get("blocked") or task.get("status") == "waiting_user")}
- last_event: {task.get("blocked") or "none"}

## Resume Instructions
- read token first
- read plan second
- read executor tail third
- do not mark any step complete without VerifyGate
"""


def write_context_state(path: Path, token: dict[str, Any], decision: str, strategy: str) -> None:
    session = token_session(token)
    state = {
        "task_id": task_id(token),
        "task_name": task_name(token),
        "level": level(token),
        "compact_strategy": strategy,
        "turn": session.get("turn", 0),
        "context_watermark": session.get("context_watermark"),
        "compact_status": decision,
        "last_handoff_at": now_iso(),
        "last_state_injection_at": session.get("last_state_injection_at"),
        "resume": session.get("resume", {}),
    }
    write_json_atomic(path, state)


def audit_event(token: dict[str, Any], decision: str, reason: str, strategy: str, paths: list[str]) -> dict[str, Any]:
    session = token_session(token)
    return {
        "event_type": "context_compact",
        "timestamp": now_iso(),
        "task_id": task_id(token),
        "level": level(token),
        "phase": "context",
        "actor": "context_engine",
        "decision": decision,
        "reason": reason,
        "compact_strategy": strategy,
        "context_watermark": session.get("context_watermark"),
        "turn": session.get("turn", 0),
        "current_step": current_step(token),
        "paths": paths,
    }


def latest_audit_events(task_id_value: str, limit: int = 50) -> list[dict[str, Any]]:
    audit_root = ROOT / ".omc" / "audit"
    events: list[dict[str, Any]] = []
    if not audit_root.exists():
        return events

    for path in sorted(audit_root.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("task_id") == task_id_value:
                    events.append(event)
    return events[-limit:]


def unresolved_failure(events: list[dict[str, Any]]) -> str | None:
    for event in reversed(events):
        if event.get("event_type") == "fallback_event" and event.get("decision") in {"BLOCKED", "ASK_USER"}:
            return str(event.get("reason", "fallback_unresolved"))
    return None


def resume_check(token_path: Path, task_path: Path) -> ContextDecision:
    token = read_json(token_path, {})
    if not token:
        return ContextDecision(
            "RESUME_BLOCKED",
            "token_missing",
            token_path.stem,
            task_path.name,
            "L1_BASE",
            None,
            "unknown",
            True,
            "resume_state_unrecoverable",
        )

    plan_text = read_text(task_path / "plan.md")
    executor_text = read_text(task_path / "executor.md")

    if not plan_text:
        reason = "plan_missing"
    elif not executor_text:
        reason = "executor_missing"
    else:
        done, total, pending = count_plan_steps(plan_text)
        stats = token.get("stats", {}) or {}
        if stats.get("done") != done or stats.get("total") != total:
            reason = "state_conflict"
        elif pending and current_step(token) and current_step(token) not in (pending or ""):
            reason = "state_conflict"
        else:
            events = latest_audit_events(task_id(token))
            failure = unresolved_failure(events)
            if failure:
                reason = failure
            else:
                reason = "ok"

    if reason != "ok":
        return ContextDecision(
            "RESUME_BLOCKED",
            reason,
            task_id(token, token_path.stem),
            task_name(token, task_path.name),
            level(token),
            current_step(token),
            token_session(token).get("compact_strategy", "unknown"),
            True,
            "resume_state_unrecoverable" if reason != "state_conflict" else "state_conflict",
        )

    append_jsonl(
        ROOT / ".omc" / "audit" / f"{today()}.jsonl",
        {
            "event_type": "context_resume",
            "timestamp": now_iso(),
            "task_id": task_id(token),
            "level": level(token),
            "phase": "context",
            "actor": "context_engine",
            "decision": "RESUME_OK",
            "current_step": current_step(token),
            "source_order": [
                "token",
                "session-handoff",
                "plan",
                "executor-tail",
                "audit-tail",
                "oracle-verdicts",
                "error-dna",
                "fallback-tail",
            ],
        },
    )

    return ContextDecision(
        "RESUME_OK",
        "state_consistent",
        task_id(token, token_path.stem),
        task_name(token, task_path.name),
        level(token),
        current_step(token),
        token_session(token).get("compact_strategy", "unknown"),
    )


def compact_check(token_path: Path, task_path: Path) -> ContextDecision:
    token = read_json(token_path, {})
    if not token:
        return ContextDecision(
            "RESUME_BLOCKED",
            "token_missing",
            token_path.stem,
            task_path.name,
            "L1_BASE",
            None,
            "unknown",
            True,
            "resume_state_unrecoverable",
        )

    plan_text = read_text(task_path / "plan.md")
    decision, reason, strategy, needs_fallback, failure_type = compact_decision(token)

    handoff_path = task_path / "state" / "session-handoff.md"
    context_state_path = task_path / "state" / "context-state.json"
    audit_path = ROOT / ".omc" / "audit" / f"{today()}.jsonl"

    if decision in {"COMPACT_SOON", "COMPACT_NOW"}:
        write_text(handoff_path, build_handoff(token, plan_text, decision, reason))
        write_context_state(context_state_path, token, decision, strategy)
        append_jsonl(
            audit_path,
            audit_event(
                token,
                decision,
                reason,
                strategy,
                [str(handoff_path), str(context_state_path)],
            ),
        )

    return ContextDecision(
        decision,
        reason,
        task_id(token, token_path.stem),
        task_name(token, task_path.name),
        level(token),
        current_step(token),
        strategy,
        needs_fallback,
        failure_type,
    )


def state_injection(token_path: Path) -> str:
    token = read_json(token_path, {})
    task = token_task(token)
    session = token_session(token)
    stats = token.get("stats", {}) or {}

    fallback = "none"
    if task.get("status") == "waiting_user":
        fallback = "waiting_user"
    elif task.get("status") == "blocked":
        fallback = str(task.get("blocked", "blocked"))

    watermark = session.get("context_watermark", "unknown")
    return (
        "[CarrorOS State]\n"
        f"task_id={task_id(token, token_path.stem)}\n"
        f"level={level(token)}\n"
        f"status={task.get('status', 'active')}\n"
        f"current_step={current_step(token)}\n"
        f"verified={stats.get('done', 0)}/{stats.get('total', 0)}\n"
        f"compact={session.get('compact_status', 'unknown')} watermark={watermark}\n"
        f"fallback={fallback}\n"
        f"oracle_last={session.get('oracle_last_verdict', 'none')}\n"
        "rule=do_not_mark_step_done_without_VerifyGate\n"
    )


def compact_write(token_path: Path, task_path: Path, user_prompt: str = "") -> int:
    """写入 .omc/session-handoff.md 和 .omc/state/last-user-prompt.md
    供 @ 引用，下次会话自动注入上下文。
    无 hook 参与，纯文件写入。
    同时读取 .claude/.prompt-ring.json 收集最近 20 轮用户 prompt。
    """
    handoff_path = ROOT / ".omc" / "session-handoff.md"
    prompt_path = ROOT / ".omc" / "state" / "last-user-prompt.md"
    ring_path = ROOT / ".claude" / ".prompt-ring.json"

    token = read_json(token_path, {})
    task = token_task(token)
    session = token_session(token)
    stats = token.get("stats", {}) or {}
    plan_text = read_text(task_path / "plan.md")

    done, total, pending = count_plan_steps(plan_text)
    scope = task.get("scope", []) or []
    failed_verifications = task.get("failed_verifications", 0)
    oracle_last = session.get("oracle_last_verdict", "none")

    # 写入 session-handoff.md（完整任务状态）
    scope_bullets = "\n".join(f"  - {s}" for s in scope) if scope else "  - (none)"

    level_str = level(token)
    status = task.get("status", "active")
    current = current_step(token) or "(none)"
    compact_strategy = session.get("compact_strategy", "rounds")

    handoff_content = f"""# Session Handoff

> 由 context_engine compact-write 于 {now_iso()} 更新
> AGENTS.md 已 @ 引用本文件，启动时自动加载

## Task
- id: {task_id(token, token_path.stem)}
- level: {level_str}
- status: {status}
- current_step: {current}

## Progress
- verified: {done}/{total}
- pending: {pending or "(none)"}
- compact_strategy: {compact_strategy}
- failed_verifications: {failed_verifications}

## Scope
{scope_bullets}

## Oracle
- last_verdict: {oracle_last}

## Resume Rules
- 磁盘状态文件是最终真相源（token / plan / executor）
- session-handoff 只是恢复摘要，不是完成证据
- 不要标记任何 step 完成不经过 VerifyGate
"""
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(handoff_content, encoding="utf-8")

    # 读取 prompt ring 写入 last-user-prompt.md
    ring = []
    if ring_path.exists():
        try:
            ring = json.loads(ring_path.read_text(encoding="utf-8"))
            if not isinstance(ring, list):
                ring = []
        except (json.JSONDecodeError, OSError):
            ring = []

    # 用传入的 --prompt 补上最新一条
    if user_prompt and (not ring or ring[-1].get("prompt", "") != user_prompt[:500]):
        ring.append({
            "ts": now_iso(),
            "prompt": user_prompt[:500],
        })
    if len(ring) > 20:
        ring = ring[-20:]

    if ring:
        prompt_lines = []
        for i, entry in enumerate(ring):
            ts = entry.get("ts", "?")
            p = entry.get("prompt", "").replace("\n", " ")
            prompt_lines.append(f"[{i+1}] ({ts}) {p[:200]}")
        prompt_text = "\n".join(prompt_lines)
    else:
        prompt_text = "(无历史 prompt)"

    prompt_content = f"""> 由 context_engine compact-write 于 {now_iso()} 更新
> 记录 compact 前的最近 {len(ring)} 轮用户请求，帮助恢复上下文

## 最近用户请求（共 {len(ring)} 条）

{prompt_text}

---
"""
    prompt_path.write_text(prompt_content, encoding="utf-8")

    # audit
    append_jsonl(
        ROOT / ".omc" / "audit" / f"{today()}.jsonl",
        {
            "event_type": "compact_write",
            "timestamp": now_iso(),
            "task_id": task_id(token, token_path.stem),
            "level": level_str,
            "phase": "context",
            "actor": "context_engine",
            "paths": [str(handoff_path), str(prompt_path)],
        },
    )

    # 同时更新 task_dir 下的 state/session-handoff.md（已有逻辑兼容）
    state_handoff = task_path / "state" / "session-handoff.md"
    state_handoff.parent.mkdir(parents=True, exist_ok=True)
    state_handoff.write_text(handoff_content, encoding="utf-8")

    print(json.dumps({
        "handoff_path": str(handoff_path),
        "prompt_path": str(prompt_path),
        "prompt_written": bool(user_prompt),
        "status": "OK",
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["compact-check", "resume-check", "state-injection", "compact-write"])
    parser.add_argument("--token", required=True)
    parser.add_argument("--task", required=False)
    parser.add_argument("--prompt", required=False, default="")
    args = parser.parse_args()

    token_path = Path(args.token)
    task_path = Path(args.task) if args.task else Path(".")

    try:
        if args.command == "compact-check":
            result = compact_check(token_path, task_path)
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
            return 1 if result.requires_fallback else 0

        if args.command == "resume-check":
            result = resume_check(token_path, task_path)
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
            return 0 if result.decision == "RESUME_OK" else 1

        if args.command == "state-injection":
            print(state_injection(token_path))
            return 0

        if args.command == "compact-write":
            return compact_write(token_path, task_path, args.prompt)

    except OSError as exc:
        result = ContextDecision(
            "RESUME_BLOCKED",
            "audit_or_state_write_failed",
            token_path.stem,
            task_path.name,
            "L1_BASE",
            None,
            "unknown",
            True,
            "audit_write_failed",
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
