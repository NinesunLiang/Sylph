#!/usr/bin/env python3
"""
CarrorOS PreToolUse Unified Gate — merged from 7 individual hooks.

Execution order (short-circuit on first BLOCK):
  1. sensitive-edit   — block sensitive path access (.env, .ssh, keys)
  2. fallback-check   — block if task is blocked/waiting_user
  3. action-gate      — block dangerous commands; ask_user for risky ones
  4. plan-gate        — block if task files missing
  5. edit-scope       — block writes outside declared scope
  6. verify-gate      — block unverified step completion marks in plan.md
  7. oracle-gate      — hint (never blocks) for L2 trigger keywords

Design constraints (from data_todo.md / 总结.md):
  - Single Python process per tool call (was 7)
  - Audit once per block decision, not per hook
  - Oracle is hint-only, never blocks
  - First BLOCK short-circuits; later checks skip
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ── Bootstrap: self-locate project root ──
_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]
if not (ROOT / ".claude").is_dir():
    ROOT = Path(".").resolve()
import os
os.chdir(str(ROOT))

# ── Inline minimal hooklib (avoid import overhead for single-process gate) ──
OMC = ROOT / ".omc"
TOKENS = OMC / "tokens"
TASKS = OMC / "tasks"
AUDIT = OMC / "audit"

SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b", r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b", r"cookie",
]

DANGEROUS_COMMANDS = [
    r"(^|\s)rm\s+-rf\s+(/\s|\.\s|~\s|\*\s|/$|\.$|~$|\*$)", r"(^|\s)rm\s+-r\s+(/\s|\.\s|~\s|\*/)", r"^sudo\b",
    r"^chmod\s+777\b", r"^chown\b", r"^git\s+push\s+(-f|--force)",
    r"^dd\s+if=", r"^mkfs\.", r"^fdisk\b", r":\(\)\{\s*:\|:\s*&\s*\};:",
]

ASK_USER_COMMANDS = [
    r"\bcurl\b.*\|\s*(sh|bash)", r"\bwget\b.*\|\s*(sh|bash)",
    r"\bnpm\s+install\b", r"\bpip\s+install\b", r"\bbrew\s+install\b",
    r"\bcargo\s+install\b", r"\bdocker\s+run\b", r"\bkubectl\b",
    r"\bterraform\s+apply\b", r"\bterraform\s+destroy\b",
]

ORACLE_TRIGGER_KW = [
    "oracle", "acceptance", "final", "archive", "phase_end",
    "merge", "release", "deploy", "production",
]
ORACLE_FORCE_KW = ["aut", "payment", "migration", "permission"]

STALE_LOCK_THRESHOLD = 1800  # 30 min: auto-clear blocked state older than this

PLAN_FILE_PATTERNS = ["plan.md", "plan"]
WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}


# ── Helpers ──

def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def _extract_tool(payload: dict) -> str:
    return str(payload.get("tool_name") or payload.get("tool") or payload.get("name") or "")

def _extract_input(payload: dict) -> dict[str, Any]:
    for key in ("tool_input", "input", "arguments", "args"):
        val = payload.get(key)
        if isinstance(val, dict):
            return val
    return payload

def _extract_path(payload: dict) -> str:
    data = _extract_input(payload)
    return str(data.get("file_path") or data.get("filePath") or data.get("path") or data.get("filename") or "")

def _extract_command(payload: dict) -> str:
    data = _extract_input(payload)
    return str(data.get("command") or payload.get("command") or "")

def _ok(msg: str = "OK") -> int:
    print(json.dumps({"continue": True, "message": f"PreToolGate: {msg}"}, ensure_ascii=False))
    return 0

def _block(msg: str) -> int:
    safe = msg[:500]
    print(json.dumps({"continue": False, "message": f"PreToolGate: {safe}"}, ensure_ascii=False))
    sys.stderr.write(safe + "\n")
    return 0

def _match_any(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return pat
    return None

def _is_sensitive(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(re.search(pat, p, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)

def _append_audit(event: dict) -> None:
    try:
        from datetime import datetime, timezone
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event.setdefault("timestamp", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass

def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}

def _latest_token() -> Path | None:
    if not TOKENS.exists():
        return None
    candidates = sorted(
        [p for p in TOKENS.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    return candidates[0] if candidates else None

def _active_token() -> dict[str, Any] | None:
    """Returns normalized token dict, or None."""
    path = _latest_token()
    if not path:
        return None
    token = _read_json(path)
    if not isinstance(token, dict) or not token:
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        token["task"] = {"name": str(task), "status": token.get("status", "active")}
    return token

def _task_dir(token: dict) -> Path | None:
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    explicit = task.get("dir") or token.get("task_dir")
    if explicit:
        p = ROOT / explicit if not Path(explicit).is_absolute() else Path(explicit)
        if p.exists():
            return p
    return None

def _parse_scope(plan_text: str) -> list[str]:
    in_scope = False
    files: list[str] = []
    for line in plan_text.splitlines():
        s = line.strip()
        if s.lower().startswith("## scope") or s.lower().startswith("## scope freeze"):
            in_scope = True
            continue
        if in_scope and s.startswith("## "):
            break
        if in_scope:
            m = re.match(r"[-*]\s+`?([^`\s]+)`?", s)
            if m:
                files.append(m.group(1).replace("\\", "/"))
    return files

def _in_scope(path: str, scope: list[str]) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    for item in scope:
        s = item.replace("\\", "/").lstrip("./")
        if p == s or p.endswith("/" + s) or p.startswith(s.rstrip("/") + "/"):
            return True
    return False

def _check_verified(step_id: str | None) -> bool:
    if not AUDIT.exists():
        return False
    for f in sorted(AUDIT.glob("*.jsonl")):
        with f.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # carros_base.py writes: {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}}
                if e.get("event") == "verify":
                    data = e.get("data", {})
                    if isinstance(data, dict) and data.get("result") == "VERIFIED":
                        if step_id is None or data.get("step") == step_id:
                            return True
                # Legacy compat: {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"}
                if e.get("event_type") == "verify_decision" and e.get("decision") == "VERIFIED":
                    if step_id is None or e.get("step") == step_id:
                        return True
    return False


# ── Gate Checks (ordered, each returns None=pass or str=block_reason) ──

def _check_sensitive_edit(payload: dict) -> str | None:
    """Gate 1: block sensitive path writes only (reads are safe)."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if path and _is_sensitive(path):
        return f"BLOCK sensitive_path path={path}"
    return None

def _check_fallback(_payload: dict) -> str | None:
    """Gate 2: block if task is blocked/waiting."""
    token = _active_token()
    if not token:
        return None  # no active task = no block
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    status = task.get("status") or token.get("status") or "active"
    if status == "blocked":
        reason = task.get("blocked") or task.get("reason") or "blocked"
        return f"BLOCK task_blocked reason={reason}"
    if status == "waiting_user":
        reason = task.get("reason") or "requires_user"
        return f"ASK_USER reason={reason}"
    fallback = task.get("fallback", {}) or {}
    if fallback.get("unresolved"):
        return f"BLOCK unresolved_fallback reason={fallback.get('reason', 'unknown')}"
    session = token.get("session", {}) or {}
    if session.get("fallback"):
        return None  # session fallback is a warning, not a block
    return None

def _check_action_gate(payload: dict) -> str | None:
    """Gate 3: block dangerous commands; ask_user for risky ones."""
    command = _extract_command(payload)
    if not command:
        return None
    hard = _match_any(command, DANGEROUS_COMMANDS)
    if hard:
        _append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "dangerous_command",
            "pattern": hard,
            "command_preview": command[:160],
        })
        return f"BLOCK dangerous_command pattern={hard}"
    ask = _match_any(command, ASK_USER_COMMANDS)
    if ask:
        _append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-gate",
            "decision": "ASK_USER",
            "reason": "approval_required_command",
            "pattern": ask,
            "command_preview": command[:160],
        })
        return f"ASK_USER approval_required pattern={ask}"
    return None

def _check_plan_gate(payload: dict) -> str | None:
    """Gate 4: block writes only when a formal task is active but files are missing."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        return None  # no active task → allow
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    if task.get("status") in {"blocked", "waiting_user"}:
        return f"BLOCK task_status_{task.get('status')}"
    task_dir = _task_dir(token)
    if not task_dir:
        return None  # no task_dir → not a formal task, allow writes
    plan = task_dir / "plan.md"
    # Only block if task_dir exists but plan is missing (formal task started but incomplete)
    if not plan.exists():
        return f"BLOCK plan_missing task_dir={task_dir}"
    if not task.get("current_step"):
        return "BLOCK current_step_missing"
    return None

def _check_edit_scope(payload: dict) -> str | None:
    """Gate 5: block writes outside declared scope (only for formal tasks)."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    token = _active_token()
    if not token:
        return None  # no active task → allow writes
    task_dir = _task_dir(token)
    if not task_dir:
        return None  # no task_dir → not a formal task, allow writes
    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        return None  # no plan → not a formal task with scope, allow writes
    scope = _parse_scope(plan_path.read_text(encoding="utf-8"))
    if not scope:
        return None  # no scope declared → allow writes (plan may not need scope)
    if not _in_scope(path, scope):
        _append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "scope_violation",
            "path": path,
            "scope": scope[:10],
        })
        return f"BLOCK scope_violation path={path}"
    return None

def _check_verify_gate(payload: dict) -> str | None:
    """Gate 6: block unverified step [x] marks in plan.md."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not any(path.replace("\\", "/").endswith(p) for p in PLAN_FILE_PATTERNS):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not re.search(r"\[x\]", content, re.IGNORECASE):
        return None
    token = _active_token()
    if not token:
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    current_step = task.get("current_step")
    if not _check_verified(current_step):
        _append_audit({
            "event_type": "verifygate_preaction_block",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "step_not_verified",
            "path": path,
            "current_step": current_step,
        })
        return f"BLOCK step_{current_step}_not_VERIFIED"
    return None

def _check_oracle_gate(payload: dict) -> str | None:
    """Gate 7: hint for L2 oracle triggers (never blocks)."""
    token = _active_token()
    if not token:
        return None
    session = token.get("session", {}) or {}
    if session.get("level", "L1_BASE") != "L2_ENHANCE":
        return None
    command = _extract_command(payload)
    if not command:
        return None
    cmd_lower = command.lower()
    force = any(kw in cmd_lower for kw in ORACLE_FORCE_KW)
    trigger = force or any(kw in cmd_lower for kw in ORACLE_TRIGGER_KW)
    if not trigger:
        return None
    task = token.get("task", {})
    phase = task.get("phase", "execute") if isinstance(task, dict) else "execute"
    _append_audit({
        "event_type": "oracle_gate_trigger",
        "actor": "hook:pretool-gate",
        "decision": "REVIEW",
        "reason": "potential_oracle_trigger_detected",
        "current_step": task.get("current_step") if isinstance(task, dict) else None,
        "phase": phase,
    })
    # Oracle never blocks — returns a hint string that gets logged but passes through
    return None  # always passes


# ── Main dispatcher ──

STATE_TOKEN = OMC / "state" / "token.json"


def _clean_stale_state_token() -> None:
    """Auto-clear .omc/state/token.json if blocked/waiting longer than threshold.
    Prevents stale lock accumulation (ref: GPT-5.5 audit finding)."""
    if not STATE_TOKEN.exists():
        return
    try:
        data = json.loads(STATE_TOKEN.read_text(encoding="utf-8"))
    except Exception:
        return
    task = data.get("task") if isinstance(data.get("task"), dict) else {}
    status = task.get("status") or (data.get("task") or {}).get("status") or ""
    if status not in ("blocked", "waiting_user"):
        return
    fb = task.get("fallback", {}) or {}
    ts_str = fb.get("timestamp") or data.get("session", {}).get("fallback", {}).get("timestamp") or ""
    if not ts_str:
        return
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(ts_str)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception:
        return
    if age < STALE_LOCK_THRESHOLD:
        return
    # Stale lock detected — auto-clear
    cleared = {
        "schema_version": 3,
        "session": {"clean": True, "note": f"Auto-cleared stale {status} from {ts_str}",
                     "cleaned_at": datetime.now(timezone.utc).isoformat()},
        "task": None,
    }
    STATE_TOKEN.write_text(json.dumps(cleared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_audit({
        "event_type": "state_lock_auto_cleared",
        "actor": "hook:pretool-gate",
        "reason": f"stale_{status}_age_{int(age)}s",
        "original_timestamp": ts_str,
    })


# Dialogue residue patterns — content that indicates AI chat output left in spec docs
HARD_BLOCK_DOC_PATTERNS = [
    r"(^|/)重构指导文档/",
    r"(^|/)AGENTS\.md$",
    r"(^|/)kernel\.md$",
    r"(^|/)README\.md$",
]

_DIALOGUE_RESIDUE_PATTERNS = [
    r"我明白了[，,。!！]?",
    r"好的[，,。!！]?(,|，)?" + r"让我",
    r"下面给你一版",
    r"下面是一版(调整|优化|完整|修改|补充)",
    r"根据你(给|上传|提供)的",
    r"我对.*进行了全面(优化|调整|更新|修改)",
    r"我明白你的意思",
    r"可以[。.]\s*依?据?现在(已经)?定稿",
    r"对[，,]刚才那版确实",
    r"I understand[.,]",
    r"Here is a (complete|revised|optimized|updated) version",
    r"Based on your (uploaded|provided|given)",
]


def _check_document_quality(payload: dict) -> str | None:
    """Gate 8: detect dialogue residue in spec document writes.
    — Critical paths (重构指导文档, AGENTS, kernel, README): BLOCK
    — Other .md: WARN (audit only, passes through)."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content:
        return None
    for pat in _DIALOGUE_RESIDUE_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            is_critical = any(re.match(hp, path.replace("\\", "/"), re.IGNORECASE) for hp in HARD_BLOCK_DOC_PATTERNS)
            decision = "BLOCK" if is_critical else "WARN"
            _append_audit({
                "event_type": "document_quality_warning",
                "actor": "hook:pretool-gate",
                "decision": decision,
                "reason": f"dialogue_residue pattern={pat}",
                "path": path,
            })
            if is_critical:
                return f"BLOCK dialogue_residue_in_spec_doc pattern={pat} path={path}"
            return None  # WARN passes through
    return None


GATES = [
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("action", _check_action_gate),
    ("plan", _check_plan_gate),
    ("edit-scope", _check_edit_scope),
    ("verify", _check_verify_gate),
    ("oracle", _check_oracle_gate),
    ("document-quality", _check_document_quality),
]


def main() -> int:
    payload = _read_stdin()
    tool_name = _extract_tool(payload).lower() or "unknown"

    _clean_stale_state_token()  # auto-clear stale locks before gate checks

    for gate_name, gate_fn in GATES:
        try:
            result = gate_fn(payload)
        except Exception:
            # Gate crash = pass through (fail-open for safety)
            continue
        if result:
            if result.startswith("BLOCK"):
                return _block(f"BLOCK [{gate_name}] {result}")
            elif result.startswith("ASK_USER"):
                return _block(f"ASK_USER [{gate_name}] {result}")
            # Non-blocking hints are logged but don't stop execution

    return _ok(f"ALLOW tool={tool_name}")


if __name__ == "__main__":
    raise SystemExit(main())
