#!/usr/bin/env python3
"""
pretool-compact-writer.py — compact 前写 handoff.md

CC hook: UserPromptSubmit
检测 compact 信号（用户发 /compact），在 compact 前写入 handoff.md。

读取 carros_base.py 同一套 token 路径（.omc/tokens/{date}/{task_id}.json），
写出与 carros_base.py _write_handoff() 一致的 handoff.md。

兼容性：同时写 .omc/state/session-handoff.md + .claude/session-handoff.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path.cwd()
OMC_ROOT = PROJECT_ROOT / ".omc"
OMC_TOKENS = OMC_ROOT / "tokens"
OMC_STATE = OMC_ROOT / "state"

HANDOFF_PATHS = [
    OMC_STATE / "session-handoff.md",
    Path(".claude/session-handoff.md"),
]


def _get_terminal_id():
    """获取终端唯一标识，用于多终端隔离 last-user-prompts。
    优先级: tty > OPENCODE_SESSION_ID > CLAUDE_SESSION_ID > PID
    """
    try:
        tty_id = os.popen("tty 2>/dev/null").read().strip()
        if tty_id and tty_id != "not a tty":
            return tty_id.replace("/dev/", "")
    except Exception:
        pass
    oc_id = os.environ.get("OPENCODE_SESSION_ID", "")
    if oc_id:
        return "oc-" + oc_id[:8]
    cc_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if cc_id:
        return "cc-" + cc_id[:8]
    return "pid-" + str(os.getpid())


def _record_last_prompt(user_msg: str):
    """记录当前终端的最近一条用户 query 到 last-user-prompts/<term_id>。
    每次 UserPromptSubmit 时调用，保留最近20条。
    """
    if not user_msg:
        return
    try:
        prompts_dir = OMC_STATE / "last-user-prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        term_id = _get_terminal_id()
        prompt_path = prompts_dir / term_id

        text = user_msg.strip()[:200]
        if not text:
            return
        existing = []
        if prompt_path.exists():
            existing = prompt_path.read_text(encoding="utf-8", errors="replace").splitlines()
        existing.append(text)
        if len(existing) > 20:
            existing = existing[-20:]
        prompt_path.write_text("\n".join(existing), encoding="utf-8")
    except OSError:
        pass


def _find_latest_token():
    """找到最新活跃的 token — 与 carros_base.py _find_latest_token 逻辑一致"""
    if not OMC_TOKENS.exists():
        return None
    candidates = []
    for dd in sorted(OMC_TOKENS.iterdir(), reverse=True):
        if dd.is_dir():
            for jf in dd.glob("*.json"):
                try:
                    candidates.append((jf.stat().st_mtime, jf))
                except OSError:
                    continue
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _, jf in candidates:
        try:
            token = json.loads(jf.read_text())
            if token.get("status") == "active":
                return token, jf
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _write_handoff(token_data: dict = None, token_path: Path = None):
    """写 handoff.md — 格式与 carros_base.py _write_handoff 兼容"""
    from datetime import timezone

    token = None
    if not token_data:
        result = _find_latest_token()
        if result:
            token, token_path = result
    else:
        token = token_data

    if not token:
        content = (
            f"# Session Handoff\n"
            f"ts: {datetime.now().isoformat()}\n"
            f"status: no_active_task\n"
        )
        for hp in HANDOFF_PATHS:
            hp.parent.mkdir(parents=True, exist_ok=True)
            hp.write_text(content)
        return

    pending = [s["id"] for s in token.get("steps", []) if s.get("status") == "pending"]
    done = token.get("stats", {}).get("done", 0)
    total = token.get("stats", {}).get("total", 0)
    steps_summary = "\n".join(
        f"  {'✅' if s['status'] == 'completed' else '⬜'} {s['id']}: {s['status']}"
        for s in token.get("steps", [])
    )
    token_file = str(token_path) if token_path else ""
    task_dir = token.get("task_dir", "")

    content = (
        f"# Session Handoff\n"
        f"ts: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"id: {token.get('session', {}).get('id', 'unknown')}\n"
        f"level: {token.get('session', {}).get('level', 'L1_BASE')}\n"
        f"status: {token.get('status', 'unknown')}\n"
        f"progress: {done}/{total}\n"
        f"token_path: {token_file}\n"
        f"task_dir: {task_dir}\n"
        f"pending: {','.join(pending) if pending else 'none'}\n"
        f"\n"
        f"## Steps\n"
        f"{steps_summary}\n"
    )

    # 同时写两个位置，确保兼容
    for hp in HANDOFF_PATHS:
        hp.parent.mkdir(parents=True, exist_ok=True)
        hp.write_text(content)


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    user_msg = stdin_data.strip() if stdin_data else ""

    # ─── 记录当前终端用户 query（last-user-prompts 多终端隔离）───
    _record_last_prompt(user_msg)

    # ─── 检测 compact 信号 ───
    is_compact = user_msg.lower().startswith("/compact")

    if is_compact:
        _write_handoff()
        msg = "Handoff: written before compact"
        print(json.dumps({"continue": True, "message": msg}))
        sys.stderr.write(msg + "\n")
        return 0

    # ─── 默认放行 ───
    print(json.dumps({"continue": True, "message": "Handoff: no action"}))
    return 0


if __name__ == "__main__":
    main()
