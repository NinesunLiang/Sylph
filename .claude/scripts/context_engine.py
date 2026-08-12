#!/usr/bin/env python3
"""
CarrorOS Context Engine

Purpose:
  Manage compact / resume / state injection without creating completion facts.

Commands:
  resume-check    --token <path> --task <path>
  state-injection --token <path>
  compact-write   --token <path> [--task <path>] [--session-id <id>]

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
ROOT = _script_path.parents[2]
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
    return datetime.now(timezone.utc).strftime("%Y%m%d")


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


def write_context_state(path: Path, token: dict[str, Any], decision: str, strategy: str) -> None:
    session = token_session(token)
    state = {
        "task_id": task_id(token),
        "task_name": task_name(token),
        "level": level(token),
        "compact_strategy": strategy,
        "turn": session.get("turn", 0),
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
                "oracle",
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

    return (
        "[CarrorOS State]\n"
        f"task_id={task_id(token, token_path.stem)}\n"
        f"level={level(token)}\n"
        f"status={task.get('status', 'active')}\n"
        f"current_step={current_step(token)}\n"
        f"verified={stats.get('done', 0)}/{stats.get('total', 0)}\n"
        f"compact={session.get('compact_status', 'unknown')}\n"
        f"fallback={fallback}\n"
        f"oracle_last={session.get('oracle_last_verdict', 'none')}\n"
        "rule=do_not_mark_step_done_without_VerifyGate\n"
    )


def _build_resume_capsule(
    token: dict[str, Any],
    token_path: Path,
    task_path: Path,
    session_id: str,
) -> dict[str, Any]:
    """构建 resume-capsule.json 供 PostCompact hook 注入恢复指令。"""
    plan_text = read_text(task_path / "plan.md")
    done, total, pending = count_plan_steps(plan_text)
    step = token_task(token).get("current_step")
    task = token_task(token)

    # 用第一个未完成的 plan step (如果有), 否则 fallback 到 current_step
    next_action = None
    if pending:
        next_action = pending
    else:
        next_action = step

    # 当前阶段推断
    phase = "unknown"
    if total > 0 and done == 0:
        phase = "initial"
    elif done < total:
        phase = "executing"
    elif done >= total:
        phase = "verifying"

    return {
        "active_token": str(token_path),
        "plan_dir": str(task_path),
        "current_phase": phase,
        "current_step": step,
        "next_action": next_action,
        "source": "compact",
        "task_id": task_id(token, token_path.stem),
        "session_id": session_id,
    }


def compact_write(
    token_path: Path,
    task_path: Path,
    user_prompt: str = "",
    session_id: str | None = None,
) -> int:
    """写入 .omc/session-handoff.md 和 .omc/state/last-user-prompt.md
    供 SessionStart hook(session-start.py, source=compact/resume)注入到
    compact 后的上下文尾部,恢复任务状态。
    无 hook 参与，纯文件写入。
    同时读取 .claude/.prompt-ring.json 收集最近 20 轮用户 prompt。
    """
    handoff_path = ROOT / ".omc" / "session-handoff.md"
    prompt_path = ROOT / ".omc" / "state" / "last-user-prompt.md"
    ring_path = ROOT / ".omc" / ".prompt-ring.json"
    capsule_path = ROOT / ".omc" / "state" / "resume-capsule.json"

    token = read_json(token_path, {})
    task = token_task(token)
    session = token_session(token)
    stats = token.get("stats", {}) or {}
    plan_text = read_text(task_path / "plan.md")

    done, total, pending = count_plan_steps(plan_text)
    scope = task.get("scope", []) or []
    failed_verifications = task.get("failed_verifications", 0)
    oracle_last = session.get("oracle_last_verdict", "none")
    executor_text = read_text(task_path / "executor.md")
    checklist_lines = [
        line.strip() for line in executor_text.splitlines()
        if line.strip().startswith("- [")
    ]
    checklist_summary = "\\n".join(f"  - {line}" for line in checklist_lines[-40:]) or "  - (none)"

    # 写入 session-handoff.md
    scope_bullets = "\n".join(f"  - {s}" for s in scope) if scope else "  - (none)"

    level_str = level(token)
    status = task.get("status", "active")
    current = current_step(token) or "(none)"
    compact_strategy = session.get("compact_strategy", "rounds")

    # Lossless handoff fields: goal, explicit next action, decisions. The
    # handoff must carry enough context to resume without loss on compact.
    goal_meta = token.get("goal", {})
    goal_desc = goal_meta.get("description") if isinstance(goal_meta, dict) else ""
    if not goal_desc:
        # plan.md `## Goal` section content first, then first non-"# Plan" heading
        goal_m = re.search(r"^## Goal\s*$([\s\S]*?)(?=^## |\Z)", plan_text, re.MULTILINE)
        if goal_m:
            for line in goal_m.group(1).splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    goal_desc = s
                    break
    if not goal_desc:
        for line in plan_text.splitlines():
            if line.startswith("#") and not line.startswith("# Plan"):
                goal_desc = line.lstrip("# ").strip()
                break
    goal_desc = (goal_desc or task_id(token, token_path.stem))[:200]
    if pending:
        next_action = f"继续待办步骤: {pending}"
    elif total and done >= total:
        next_action = "任务步骤已全部完成，进入 report/done 收口"
    else:
        next_action = f"继续 current_step: {current}"
    decision_lines = []
    dec_match = re.search(r"^## Decisions\s*$([\s\S]*?)(?=^## |\Z)", executor_text, re.MULTILINE)
    if dec_match:
        for line in dec_match.group(1).splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("```"):
                decision_lines.append(f"  {s[:160]}")
    decisions_summary = "\n".join(decision_lines[:10]) or "  (none)"
    todo_lines = []
    for line in plan_text.splitlines():
        m = re.match(r"^\s*[-*]\s+(\[[ xX]\])\s+(\S+)(?::\s*(.*))?\s*$", line)
        if m:
            mark = "✅" if m.group(1).strip() != "[ ]" else "◻"
            sid = m.group(2)
            tail = (m.group(3) or "").strip()
            todo_lines.append(f"  {mark} {sid}{(': ' + tail[:60]) if tail else ''}")
    todo_summary = "\n".join(todo_lines[:40]) or "  (none)"

    handoff_content = f"""# Session Handoff

> 由 context_engine compact-write 于 {now_iso()} 更新
> 由 SessionStart hook(session-start.py, source=compact/resume)注入 compact 后上下文尾部

## Goal
{goal_desc}

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

## Next Action
{next_action}

## Todo
{todo_summary}

## Decisions
{decisions_summary}

## Scope
{scope_bullets}

## Documents
- task_dir: {task_path.resolve()}
- plan: {task_path / "plan.md"}
- research: {task_path / "research.md"}
- executor: {task_path / "executor.md"}
- checklist: {task_path / "state" / "checklist.md"}
- user_prompts: {prompt_path}

## Checklist
{checklist_summary}

## Oracle
- last_verdict: {oracle_last}

## Resume Rules
- 磁盘状态文件是最终真相源（token / plan / executor）
- session-handoff 只是恢复摘要，不是完成证据
- 不要标记任何 step 完成不经过 VerifyGate
- 最近用户请求见 last-user-prompt.md（最多 20 条）
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
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_content, encoding="utf-8")

    capsule_written = False
    if session_id:
        capsule = _build_resume_capsule(token, token_path, task_path, session_id)
        capsule_path.parent.mkdir(parents=True, exist_ok=True)
        capsule_path.write_text(json.dumps(capsule, ensure_ascii=False, indent=2), encoding="utf-8")
        capsule_written = True

    # audit
    audit_paths = [str(handoff_path), str(prompt_path)]
    if capsule_written:
        audit_paths.append(str(capsule_path))
    append_jsonl(
        ROOT / ".omc" / "audit" / f"{today()}.jsonl",
        {
            "event_type": "compact_write",
            "timestamp": now_iso(),
            "task_id": task_id(token, token_path.stem),
            "level": level_str,
            "phase": "context",
            "actor": "context_engine",
            "paths": audit_paths,
            "session_id": session_id,
        },
    )

    print(json.dumps({
        "handoff_path": str(handoff_path),
        "prompt_path": str(prompt_path),
        "capsule_path": str(capsule_path) if capsule_written else None,
        "prompt_written": bool(user_prompt),
        "status": "OK",
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resume-check", "state-injection", "compact-write"])
    parser.add_argument("--token", required=True)
    parser.add_argument("--task", required=False)
    parser.add_argument("--prompt", required=False, default="")
    parser.add_argument("--session-id", required=False, default="")
    args = parser.parse_args()

    token_path = Path(args.token)
    task_path = Path(args.task) if args.task else Path(".")

    try:
        if args.command == "resume-check":
            result = resume_check(token_path, task_path)
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
            return 0 if result.decision == "RESUME_OK" else 1

        if args.command == "state-injection":
            print(state_injection(token_path))
            return 0

        if args.command == "compact-write":
            return compact_write(token_path, task_path, args.prompt, args.session_id or None)

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
