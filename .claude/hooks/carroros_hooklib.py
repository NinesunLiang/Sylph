#!/usr/bin/env python3
"""
CarrorOS Hook Library

Hook rules:
- Hooks are routing / observation / guardrail only.
- Hooks do not create completion facts.
- Hooks do not replace VerifyGate / Oracle / Fallback / Archive.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Find project root: walk up from CWD until .claude/ is found, or fall back to CARROROS_ROOT
_cwd = Path(".").resolve()
ROOT = _cwd
for _ in range(10):  # max 10 levels up
    if (_cwd / ".claude").is_dir() or (_cwd / ".git").is_dir():
        ROOT = _cwd
        break
    parent = _cwd.parent
    if parent == _cwd:
        break
    _cwd = parent
ROOT = Path(os.environ.get("CARROROS_ROOT", str(ROOT))).resolve()
OMC = ROOT / ".omc"
TOKENS = OMC / "tokens"
TASKS = OMC / "tasks"
AUDIT = OMC / "audit"
CLAUDE_SCRIPTS = ROOT / ".claude" / "scripts"

SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)",
    r"(^|/)\.ssh(/|$)",
    r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)",
    r"(^|/)\.azure(/|$)",
    r"id_rsa",
    r"id_ed25519",
    r"private[_-]?key",
    r"secret",
    r"credential",
    r"password",
    r"token",
    r"cookie",
]

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def read_stdin_json() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        if not raw:
            return {}
        return json.loads(raw)
    except Exception:
        return {}

def hook_continue(message: str | None = None, extra: list[str] | None = None) -> int:
    obj: dict[str, Any] = {"continue": True}
    if message:
        obj["message"] = sanitize_text(message, 300)
    if extra:
        obj["output_additional_context"] = [sanitize_text(x, 500) for x in extra]
    print(json.dumps(obj, ensure_ascii=False))
    return 0

def hook_block(message: str) -> int:
    msg = sanitize_text(message, 500)
    print(json.dumps({"continue": False, "message": msg}, ensure_ascii=False))
    sys.stderr.write(msg + "\n")
    return 0

def sanitize_text(value: Any, max_len: int = 500) -> str:
    text = str(value or "")
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"(?i)(api[_-]?key|token|password|secret|cookie|authorization)\s*[:=]\s*\S+", r"\1=<redacted>", text)
    return text[:max_len]

def is_sensitive_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)

def latest_token_path() -> Path | None:
    if not TOKENS.exists():
        return None
    candidates = sorted(
        [p for p in TOKENS.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None

def read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}

def active_token() -> tuple[dict[str, Any], Path] | tuple[None, None]:
    path = latest_token_path()
    if not path:
        return None, None
    token = read_json(path)
    status = token.get("task", {}).get("status") or token.get("status")
    if status in {"archived", "blocked"}:
        return token, path
    return token, path

def task_dir_from_token(token: dict[str, Any], token_path: Path | None = None) -> Path | None:
    task = token.get("task", {}) or {}
    explicit = task.get("dir") or token.get("task_dir")
    if explicit:
        p = ROOT / explicit if not Path(explicit).is_absolute() else Path(explicit)
        if p.exists():
            return p

    if token_path and len(token_path.parts) >= 3:
        date = token_path.parent.name
        name = token_path.stem
        p = TASKS / date / name
        if p.exists():
            return p

    name = task.get("name") or token_path.stem if token_path else None
    if name:
        candidates = sorted(TASKS.glob(f"*/{name}"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0]
    return None

def append_audit(event: dict[str, Any]) -> bool:
    try:
        AUDIT.mkdir(parents=True, exist_ok=True)
        path = AUDIT / f"{today()}.jsonl"
        event.setdefault("timestamp", now_iso())
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return True
    except OSError:
        return False

def run_script(script_name: str, args: list[str], timeout: int = 10) -> tuple[int, str, str]:
    script = CLAUDE_SCRIPTS / script_name
    if not script.exists():
        return 127, "", f"missing script: {script}"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)] + args,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {script_name}"
    except Exception as exc:
        return 1, "", str(exc)

def extract_tool_name(payload: dict[str, Any]) -> str:
    return str(
        payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or ""
    )

def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("tool_input", "input", "arguments", "args"):
        val = payload.get(key)
        if isinstance(val, dict):
            return val
    return payload

def extract_path(payload: dict[str, Any]) -> str:
    data = extract_tool_input(payload)
    return str(
        data.get("file_path")
        or data.get("filePath")
        or data.get("path")
        or data.get("filename")
        or ""
    )

def extract_command(payload: dict[str, Any]) -> str:
    data = extract_tool_input(payload)
    return str(data.get("command") or payload.get("command") or "")