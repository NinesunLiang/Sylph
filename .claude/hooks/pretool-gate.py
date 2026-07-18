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
import secrets
import shutil
import sys
from datetime import datetime, timezone
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
CRITICAL_STATE = OMC / "state" / "context-critical.json"
FALLBACK_REQUIRED = OMC / "state" / "fallback-blocked-required"
FALLBACK_APPROVED = OMC / "state" / "fallback-blocked-approved"
TEMP_BYPASS = OMC / "state" / "temp-bypass.json"

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

READ_TOOLS = {"read", "grep", "glob", "search_files", "list", "ls", "find", "cat"}
WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
PLAN_FILE_PATTERNS = ["plan.md", "plan"]


# ── Helpers ──

def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def _check_temp_bypass() -> bool:
    """Check if a user-authorized temp bypass is active.

    Bypass file: .omc/state/temp-bypass.json
    Format: {"reason": "...", "expires_at": "ISO8601"}
    If expired, auto-delete the file.
    """
    if not TEMP_BYPASS.exists():
        return False
    try:
        data = json.loads(TEMP_BYPASS.read_text(encoding="utf-8"))
        expires = data.get("expires_at", "")
        if expires:
            try:
                from datetime import datetime, timezone
                exp = datetime.fromisoformat(expires)
                if datetime.now(timezone.utc) >= exp:
                    TEMP_BYPASS.unlink(missing_ok=True)
                    return False
            except Exception:
                pass
        return True
    except Exception:
        TEMP_BYPASS.unlink(missing_ok=True)
        return False

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

def _block(reason: str, suggestion: str = "") -> int:
    """Block a tool call with HUMAN-READABLE reason and next step.

    Sylph-inspired pattern: instead of a terse machine-only message,
    give the user the context they need to decide what to do next.
    Also supports a TEMP_KEY bypass mechanism for user-authorized overrides.
    """
    safe_reason = reason[:300]
    msg_parts = [f"⛔ 操作被阻断: {safe_reason}"]
    if suggestion:
        msg_parts.append(f"💡 建议: {suggestion}")
    bypass_hint = (
        "🔑 如需临时授权跳过此检查，请运行: "
        "`! python3 .claude/scripts/temp-bypass.py --minutes 60 --reason \"你的理由\"`"
    )
    msg_parts.append(bypass_hint)
    full_msg = "\n".join(msg_parts)

    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": full_msg,
        }
    }, ensure_ascii=False))
    sys.stderr.write(f"PreToolGate: BLOCKED - {safe_reason}\n")
    return 2

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

def _auto_init(target_path: str | None = None) -> None:
    """自动 init：无 token 写操作时后台初始化 task 文档系统"""
    import subprocess
    try:
        script = ROOT / ".claude/scripts/carros_base.py"
        if not script.exists():
            return
        cmd = [sys.executable, str(script), "init", "--auto"]
        if target_path:
            cmd += ["--target", target_path]
        subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=10)
    except Exception:
        pass

def _check_sensitive_edit(payload: dict) -> str | None:
    """Gate 1: block sensitive path writes only (reads are safe)."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if path and _is_sensitive(path):
        return f"BLOCK 敏感路径 {path}，需要确认后才能修改|请确认是否确实要修改敏感文件。如果确认，请使用临时 bypass 授权"
    return None

def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _auto_archive_token(token_path: Path, token_data: dict, reason: str) -> None:
    """Move a stale/broken token out of the way so it stops blocking the project.

    Token is copied to archive/tokens/{date}/ with a note, then deleted from tokens/.
    Never raises — silence any I/O errors.
    """
    try:
        archive_dir = OMC / "archive" / "tokens" / token_path.parent.name
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / token_path.name
        # Mark as archived in the token data
        token_data["status"] = "archived"
        token_data.setdefault("session", {})
        token_data["session"]["archived_at"] = datetime.now(timezone.utc).isoformat()
        token_data.setdefault("task", {})
        if isinstance(token_data.get("task"), dict):
            token_data["task"]["archive_reason"] = reason
        archive_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        token_path.unlink()
        _append_audit({
            "event_type": "token_auto_archived",
            "actor": "hook:pretool-gate",
            "reason": reason,
            "token": token_path.name,
            "archived_to": str(archive_path),
        })
    except OSError:
        pass


def _check_fallback(_payload: dict) -> str | None:
    """Gate 2: block if task is blocked/waiting.

    Stale lock protection: if a token has been blocked longer than
    STALE_LOCK_THRESHOLD, auto-archive it instead of blocking.
    Historical bad state must not freeze the project (Boss ruling 2026-07-15).
    """
    token_path = _latest_token()
    if not token_path:
        return None
    token_data = _read_json(token_path)
    if not token_data:
        return None
    token = token_data
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    status = task.get("status") or token.get("status") or "active"
    if status != "blocked":
        # Normal path: check waiting_user or unresolved fallback
        if status == "waiting_user":
            reason = task.get("reason") or "requires_user"
            return f"ASK_USER Bypass 临时授权状态：{reason}|如需继续，运行 temp-bypass 命令创建临时授权"
        fallback = task.get("fallback", {}) or {}
        if fallback.get("unresolved"):
            return f"BLOCK fallback 状态未解决：{fallback.get('reason', 'unknown')}|请先解决fallback问题后再操作，或使用临时bypass授权跳过"
        session = token.get("session", {}) or {}
        if session.get("fallback"):
            return None
        return None
    # --- Blocked token detected ---
    reason = task.get("blocked") or task.get("reason") or "blocked"
    # Check staleness: use fallback timestamp or token created_at
    ts_str = (
        (task.get("fallback") or {}).get("timestamp")
        or (token.get("session") or {}).get("created_at")
        or ""
    )
    age = 0.0
    if ts_str:
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(ts_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            pass
    if age >= STALE_LOCK_THRESHOLD:
        # Stale blocked token — auto-archive so it stops freezing the project
        _auto_archive_token(token_path, token_data, f"stale_blocked age={int(age)}s reason={reason}")
        return None  # pass through, project is unblocked

    # ─── Not stale enough for auto-archive → CAPTCHA approval pattern ───
    # Check if user already approved via /approve <token>
    if FALLBACK_APPROVED.exists():
        _auto_archive_token(token_path, token_data, f"user_approved reason={reason}")
        _safe_unlink(FALLBACK_REQUIRED)
        _safe_unlink(FALLBACK_APPROVED)
        return None  # pass through

    # Generate CAPTCHA for user to approve
    captcha = secrets.token_hex(3)  # 6-char hex
    try:
        FALLBACK_REQUIRED.parent.mkdir(parents=True, exist_ok=True)
        FALLBACK_REQUIRED.write_text(captcha)
    except OSError:
        pass

    # Build helpful message
    task = token.get("task", {})
    session = token.get("session", {})
    task_name = session.get("id") or task.get("name") or token_path.stem
    blocked_since = (task.get("fallback") or {}).get("timestamp") or \
                    session.get("created_at", "")[:19] or "?"
    current_step = task.get("current_step", "?")
    age_str = f"（阻塞 {int(age)} 秒）" if age > 0 else ""

    msg = (
        f"\n"
        f"╔══ CarrorOS 任务阻塞 ══════════════════════════════\n"
        f"║  任务: {task_name}\n"
        f"║  状态: blocked  {age_str}\n"
        f"║  原因: {reason}\n"
        f"║  当前步骤: {current_step}\n"
        f"║  阻塞自: {blocked_since[:19]}\n"
        f"║\n"
        f"║  📌 如需解除阻塞并归档此任务，请输入:\n"
        f"║     /approve {captcha}\n"
        f"║\n"
        f"║  📌 如需保持阻塞状态:\n"
        f"║     /deny\n"
        f"║\n"
        f"║  ⏱ 或等待 {max(1, int(STALE_LOCK_THRESHOLD/60 - age/60))} 分钟后自动解除\n"
        f"╚══════════════════════════════════════════════════\n"
    )
    print(msg, file=sys.stderr, flush=True)

    return f"BLOCK task_blocked reason={reason}"

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
    """Gate 4: 自适应自治 — 无 token 自动 init，不阻断"""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        # 无 token → auto-init（不会阻阻断）
        path = _extract_path(payload)
        _auto_init(path)
        return None  # 放行
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    if task.get("status") in {"blocked", "waiting_user"}:
        return f"BLOCK task_status_{task.get('status')}"
    task_dir = _task_dir(token)
    if not task_dir:
        return None
    plan = task_dir / "plan.md"
    if not plan.exists():
        return f"BLOCK plan_missing task_dir={task_dir}"
    if not task.get("current_step"):
        return "BLOCK current_step_missing"
    return None

def _check_edit_scope(payload: dict) -> str | None:
    """Gate 5: 越界不阻断，记录 audit（方案二：柔性约束）"""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    token = _active_token()
    if not token:
        return None
    # 检查 token scope（比 plan scope 优先）
    token_scope = token.get("scope") or []
    if token_scope:
        in_scope = _in_scope(path, token_scope)
        if in_scope:
            return None
        # 越界 → audit 不阻断
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "token_scope_violation",
            "path": path,
            "scope": token_scope[:10],
        })
        return None  # 放行
    # 回退到 plan scope 检查
    task_dir = _task_dir(token)
    if not task_dir:
        return None
    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        return None
    scope = _parse_scope(plan_path.read_text(encoding="utf-8"))
    if not scope:
        return None
    if not _in_scope(path, scope):
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "plan_scope_violation",
            "path": path,
            "scope": scope[:10],
        })
        return None  # 放行
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
    # Oracle never blocks — but emits a real hint so the L2 operator sees it
    level = "FORCE" if force else "TRIGGER"
    print(
        f"🔮 [oracle-gate] L2 {level} 触发检测：建议完成后执行双审判 "
        f"`python3 .claude/scripts/carros_base.py oracle review` 或 /lx-oracle review",
        file=sys.stderr, flush=True,
    )
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
    r"(^|/)\.claude/references/design-docs/",
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


# ── Context-control gates (G2/G3/G5/G6) ──
# H2 修复注记：G1（单 tick 读文件计数）已删除——计数器是进程内存，
# hook 每次调用都是新进程，结构性不可能工作（死代码）。


def _check_g2_large_file(payload: dict) -> str | None:
    """G2: read without offset/limit and >200 lines → NARROW"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    ti = _extract_input(payload)
    if ti.get("offset") or ti.get("limit"):
        return None
    path = _extract_path(payload)
    if not path:
        return None
    p = ROOT / path.removeprefix("./") if not path.startswith("/") else Path(path)
    if not p.exists():
        return None
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        if len(lines) > 200:
            return f"NARROW large_file_no_offset path={path} lines={len(lines)} hint='use offset=1 limit=200'"
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _check_g3_reviews(payload: dict) -> str | None:
    """G3: docs/carros/reviews/** → BLOCK"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    normalized = path.replace("\\", "/")
    if "docs/carros/reviews/" in normalized:
        return f"BLOCK reviews path={path}"
    return None


def _check_g5_wide_glob(payload: dict) -> str | None:
    """G5: glob '**/*' without type narrowing → NARROW"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    ti = _extract_input(payload)
    glob_val = ti.get("glob") or ti.get("pattern") or _extract_path(payload)
    if isinstance(glob_val, str) and ("**/*" in glob_val or glob_val.strip() in ("*", ".", "./*")):
        return f"NARROW wide_glob pattern={glob_val} hint='add file_glob=*.py or type filter'"
    return None


def _check_g6_budget(payload: dict) -> str | None:
    """G6: budget soft reached → CHECKPOINT_FIRST"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS and tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        return None
    budget = token.get("budget", {})
    if not budget:
        return None
    stats = token.get("stats", {})
    turns = stats.get("tick", 0) + stats.get("turns", 0)
    soft = budget.get("max_turns_soft", 0) or 0
    hard = budget.get("max_turns_hard", 0) or 0
    if soft > 0 and turns >= soft:
        return f"CHECKPOINT_FIRST budget_soft_reached turns={turns} soft={soft} hard={hard}"
    return None


def _check_context_critical_pause(payload: dict) -> str | None:
    """GA water hard gate: while PAUSED_CONTEXT_CRITICAL, allow only recovery-class actions."""
    if not CRITICAL_STATE.exists():
        return None
    try:
        state = json.loads(CRITICAL_STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    if state.get("status") != "PAUSED_CONTEXT_CRITICAL":
        return None

    tool = _extract_tool(payload).lower()
    command = _extract_command(payload).lower()
    path = _extract_path(payload).lower()
    allowed_terms = (
        "status", "checkpoint", "compact", "resume", "archive",
        "context_engine.py", "carros_base.py status", "formal_seal.py",
    )
    text = " ".join([tool, command, path])
    if any(term in text for term in allowed_terms):
        return None
    return "BLOCK CONTEXT_CRITICAL_PAUSED allowed=status/checkpoint/compact/resume/archive"


# ── Gate registry ──

GATES = [
    ("context-critical", _check_context_critical_pause),
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("action", _check_action_gate),
    ("plan", _check_plan_gate),
    ("edit-scope", _check_edit_scope),
    ("verify", _check_verify_gate),
    ("oracle", _check_oracle_gate),
    ("document-quality", _check_document_quality),
    # Context-control gates (G2/G3/G5/G6)
    ("g2-large-file", _check_g2_large_file),
    ("g3-reviews", _check_g3_reviews),
    ("g5-wide-glob", _check_g5_wide_glob),
    ("g6-budget", _check_g6_budget),
]


def main() -> int:
    payload = _read_stdin()
    tool_name = _extract_tool(payload).lower() or "unknown"

    # 如果用户已创建临时 bypass token，跳过所有 gate 检查
    bypass_active = _check_temp_bypass()

    _clean_stale_state_token()

    for gate_name, gate_fn in GATES:
        try:
            result = gate_fn(payload)
        except Exception:
            continue
        if result:
            if result.startswith("BLOCK"):
                if bypass_active:
                    _append_audit({
                        "event_type": "gate_bypassed",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "reason": result,
                    })
                    return _ok(f"BYPASS_ALLOW [{gate_name}] (用户已授权临时跳过)")
                parts = result.split("|", 1)
                reason = parts[0].replace("BLOCK ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                return _block(reason, suggestion)
            elif result.startswith("ASK_USER"):
                parts = result.split("|", 1)
                reason = parts[0].replace("ASK_USER ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                return _block(reason, suggestion)
            elif result.startswith(("NARROW", "CHECKPOINT_FIRST")):
                # 软门（G1/G2/G5/G6）：柔性约束——WARN 提示 + audit，不阻断
                _append_audit({
                    "event_type": "gate_soft_warn",
                    "actor": "hook:pretool-gate",
                    "gate": gate_name,
                    "reason": result,
                })
                goal_mode = (OMC / "state" / "tokens" / "autonomous.active").exists()
                if not goal_mode:
                    print(f"⚠️ [{gate_name}] {result}", file=sys.stderr, flush=True)
                continue

    return _ok(f"ALLOW tool={tool_name}")


if __name__ == "__main__":
    raise SystemExit(main())
