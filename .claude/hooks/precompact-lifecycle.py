#!/usr/bin/env python3
"""PreCompact: fail-closed SSOT flush + compact-write 同步刷新。

刷新链(owner 2026-07-20 规格): compact 前先把 handoff(任务态)与
last-user-prompts(最近 20 条 prompt)刷新到最新,再写快照——
compact 后 session-start.py 注入的就是此刻的最新状态。
compact-write 为 best-effort(失败不阻断 compact,记 stderr);
快照为 fail-closed(失败 exit 2)。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.lifecycle_ssot import (  # noqa: E402
    ROOT,
    read_stdin_json,
    stderr,
    stdout_json,
    write_precompact_snapshot,
)

TOKENS_DIR = ROOT / ".omc" / "tokens"
TASKS_DIR = ROOT / ".omc" / "tasks"
CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"


def _latest_token() -> Path | None:
    if not TOKENS_DIR.exists():
        return None
    candidates = sorted(
        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates[:5]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data.get("task"), dict):
            return path
    return candidates[0] if candidates else None


def _resolve_task_dir(token_path: Path) -> Path | None:
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    task = data.get("task")
    explicit = task.get("dir") if isinstance(task, dict) else None
    explicit = explicit or data.get("task_dir")
    if isinstance(explicit, str) and explicit:
        p = Path(explicit)
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            return p
    stem = token_path.stem
    slug = stem[: -len("_token")] if stem.endswith("_token") else stem
    candidate = TASKS_DIR / token_path.parent.name / slug
    return candidate if candidate.exists() else None


def _refresh_compact_write() -> str:
    """compact 前同步刷新 handoff.md + last-user-prompt.md(best-effort)。"""
    token = _latest_token()
    if token is None:
        return "skipped:no_token"
    cmd = [sys.executable, str(CONTEXT_ENGINE), "compact-write", "--token", str(token)]
    task_dir = _resolve_task_dir(token)
    if task_dir:
        cmd += ["--task", str(task_dir)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8, cwd=str(ROOT))
    except Exception as exc:
        stderr(f"PRECOMPACT_COMPACT_WRITE_FAIL:{exc!r}")
        return f"failed:{type(exc).__name__}"
    if proc.returncode != 0:
        stderr(f"PRECOMPACT_COMPACT_WRITE_FAIL:rc={proc.returncode} {proc.stderr[:200]}")
        return f"failed:rc{proc.returncode}"
    return "ok"


def main() -> int:
    try:
        hook_input = read_stdin_json()
        refresh = _refresh_compact_write()
        session_id = hook_input.get("session_id") or hook_input.get("sessionId") or ""
        basis = (
            f"precompact:{session_id}:"
            f"{hook_input.get('transcript_path') or hook_input.get('transcriptPath') or ''}"
        )
        event_id = "pc-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
        path, digest, hb = write_precompact_snapshot(hook_input, event_id=event_id)
        stdout_json(
            {
                "ok": True,
                "event": "PreCompact",
                "snapshot": str(path),
                "sha256": digest,
                "compact_write": refresh,
                "handoff_written": hb.get("written"),
                "handoff_claimed": hb.get("claimed"),
                "reconciled": hb.get("reconciled"),
            }
        )
        return 0
    except Exception as exc:
        stderr(f"PRECOMPACT_FAIL:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
