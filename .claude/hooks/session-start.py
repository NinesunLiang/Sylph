#!/usr/bin/env python3
"""
session-start.py — CarrorOS SessionStart hook（compact 恢复 / 新会话导航）

注入（stdout additionalContext）：
  1. .omc/session-handoff.md — 会话交接（compact 后恢复）
  2. .omc/state/last-user-prompt.md — 最近用户请求
  3. 活跃 token 状态（task/step/progress）

设计：快速（<200ms）、永不阻断。无活跃任务时静默退出。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))

OMC = ROOT / ".omc"
HANDOFF = OMC / "session-handoff.md"
LAST_PROMPTS = OMC / "state" / "last-user-prompt.md"
TOKENS_DIR = OMC / "tokens"
STEPWISE_STATE = ROOT / ".claude" / "references" / "templates" / "stepwise_cards" / ".state"

MAX_HANDOFF = 2000
MAX_PROMPTS = 1000
STALE_HOURS = 24  # handoff/token 超龄注记阈值(F5 修复: 陈旧注入曾无标注误导恢复)


def _age_str(ts: float) -> str:
    hours = (datetime.now(timezone.utc).timestamp() - ts) / 3600
    if hours < 1:
        return f"{max(int(hours * 60), 0)}m"
    if hours < 48:
        return f"{hours:.0f}h"
    return f"{hours / 24:.0f}d"


def _handoff_ts(text: str, path: Path) -> float:
    """handoff 内容时间戳(头部 compact-write ISO)优先,回退文件 mtime;失败返 0。"""
    m = re.search(r"compact-write 于\s+(\S+)\s+更新", text)
    if m:
        try:
            return datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _active_token_brief() -> str:
    raw_token = os.environ.get("CARROROS_TOKEN_PATH", "").strip()
    if raw_token:
        path = Path(raw_token).expanduser().resolve()
    else:
        raw_task = os.environ.get("CARROROS_TASK_DIR", "").strip()
        if not raw_task:
            return ""
        task_dir = Path(raw_task).expanduser().resolve()
        path = TOKENS_DIR / task_dir.parent.name / f"{task_dir.name}.json"
    if not path.is_file():
        return ""
    data = _read_json(path, {})
    task = data.get("task")
    if not isinstance(task, dict):
        return ""
    stats = data.get("stats", {}) or {}
    session = data.get("session", {}) or {}
    brief = (
        f"[Active Task] id={path.stem} level={session.get('level', '?')} "
        f"step={task.get('current_step', '?')} done={stats.get('done', 0)}/{stats.get('total', '?')} "
        f"status={task.get('status', data.get('status', '?'))}"
    )
    try:
        age_h = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 3600
        brief += f" | token {_age_str(path.stat().st_mtime)}前更新"
        if age_h > STALE_HOURS:
            brief += "(超龄,恢复前先核对磁盘态)"
    except Exception:
        pass
    return brief


def _stepwise_brief() -> str:
    """lx-stepwise 任务恢复入口(抗 compact): 磁盘状态是唯一真相,会话摘要不可依赖。"""
    try:
        live = []
        for p in sorted(STEPWISE_STATE.glob("*.json")):
            s = _read_json(p, {})
            if isinstance(s, dict) and s.get("status") in ("active", "waiting_user"):
                live.append(s)
        if not live:
            return ""
        s = live[0]
        brief = (f"[Active Stepwise] task={s.get('task_id')} card={s.get('current_card')} "
                 f"done={len(s.get('passed', []))}/15 status={s.get('status')}")
        pq = s.get("pending_question")
        if s.get("status") == "waiting_user" and isinstance(pq, dict):
            brief += f" 待答: {str(pq.get('question', ''))[:60]}"
        if len(live) > 1:
            brief += f"(发现 {len(live)} 个 live 任务,状态损坏需人工清理)"
        brief += " — 恢复后先 `lx-stepwise status` 对齐,不凭记忆推进"
        return brief
    except Exception:
        return ""


def _resume_task_docs(resume_note: str) -> str:
    match = re.search(r"^task_dir=(.+)$", resume_note, flags=re.M)
    if not match:
        return ""
    task_dir = Path(match.group(1).strip()).expanduser()
    sources = [
        HANDOFF,
        OMC / "state" / "last-user-prompt.md",
    ]
    chunks = []
    for path in sources:
        try:
            if path.is_file():
                chunks.append(f"## {path.name}\n{path.read_text(encoding='utf-8')[:5000]}")
        except OSError:
            pass
    return "\n\n".join(chunks)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    source = str(payload.get("source") or "startup")
    session_id = str(payload.get("session_id") or payload.get("sessionId") or "")

    parts: list[str] = []
    resume_docs = ""
    if source in ("compact", "resume") and session_id:
        resume_note = OMC / "state" / "resume-note.md"
        if resume_note.exists():
            try:
                text = resume_note.read_text(encoding="utf-8")
                match = re.search(r"^session_id=(\S+)$", text, flags=re.M)
                if match and match.group(1) == session_id:
                    resume_docs = _resume_task_docs(text)
                    if len(text) > 500:
                        _cut = text[:500]
                        _nl = _cut.rfind("\n")
                        if _nl > 0:
                            _cut = _cut[:_nl]
                        text = _cut
                    if text.strip():
                        parts.append(text)
                        try:
                            resume_note.unlink()
                        except OSError:
                            pass
            except Exception:
                pass

    if resume_docs:
        parts.append(resume_docs)
    if source in ("compact", "resume"):
        brief = _active_token_brief()
        if brief:
            parts.append(brief)

    if not parts:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    context = "\n\n".join(parts)
    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
