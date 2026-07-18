#!/usr/bin/env python3
"""
pretool-user-approve.py — CarrorOS Unified UserPromptSubmit Gate

Multiplexes (single hook, Base lightweight philosophy):
  1. /approve <token> /deny — CAPTCHA approval for blocked tasks
  2. Prompt ring — rolling 20 user prompts (.claude/.prompt-ring.json)
  3. Every 5th prompt — detached compact-write (refreshes handoff + last-user-prompt)
  4. Every 5th prompt — U-attention tail injection (task state via additionalContext)
  5. Goal mode — appends goal state when autonomous.active exists

Constraints:
  - Never blocks: always exit 0
  - Fast path <100ms on non-5th rounds (ring append only)
  - compact-write runs detached (Popen, no wait) — hook never waits on it
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))

STATE_DIR = ROOT / ".omc" / "state"
FALLBACK_REQUIRED = STATE_DIR / "fallback-blocked-required"
FALLBACK_APPROVED = STATE_DIR / "fallback-blocked-approved"
GOAL_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
GOAL_STATE = STATE_DIR / "tokens" / "lx-goal.json"
TOKENS_DIR = ROOT / ".omc" / "tokens"
RING_PATH = ROOT / ".claude" / ".prompt-ring.json"
RING_STATE = ROOT / ".claude" / ".prompt-ring-state.json"
CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"

MAX_RING = 20
INJECT_INTERVAL = 5  # 每 5 轮：compact-write + 尾部状态注入（U 型注意力）


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _latest_token() -> Path | None:
    """Latest carros task token (skips lx-goal lock tokens etc. with non-dict task)."""
    if not TOKENS_DIR.exists():
        return None
    candidates = sorted(
        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    for path in candidates[:5]:
        data = _read_json(path, {})
        if isinstance(data.get("task"), dict) and isinstance(data.get("stats"), dict):
            return path
    return candidates[0] if candidates else None


def _extract_prompt(raw: str) -> str:
    """Payload may be JSON {prompt: ...} or raw text."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("prompt", "text", "message", "input"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    except (json.JSONDecodeError, ValueError):
        pass
    return raw.strip()


def _update_ring(prompt: str) -> int:
    """Append prompt to ring (max 20). Returns total prompt count."""
    ring = _read_json(RING_PATH, [])
    if not isinstance(ring, list):
        ring = []
    ring.append({"ts": _now_iso(), "prompt": prompt[:500]})
    ring = ring[-MAX_RING:]
    RING_PATH.write_text(json.dumps(ring, ensure_ascii=False, indent=2), encoding="utf-8")

    state = _read_json(RING_STATE, {})
    total = int(state.get("total", 0)) + 1
    RING_STATE.write_text(json.dumps({"total": total, "updated_at": _now_iso()}), encoding="utf-8")
    return total


def _state_injection_text(token_path: Path) -> str:
    """Inline fast state injection (context_engine state-injection)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(CONTEXT_ENGINE), "state-injection", "--token", str(token_path)],
            capture_output=True, text=True, timeout=5, cwd=str(ROOT),
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def _goal_state_text() -> str:
    data = _read_json(GOAL_STATE, {})
    if not isinstance(data, dict) or not data:
        return ""
    goal = data.get("goal", "")
    done = data.get("done", [])
    skipped = data.get("skipped_risks", [])
    lines = ["[Goal Mode]", f"goal={goal}", f"done={len(done)} skipped={len(skipped)}"]
    if done:
        lines.append(f"last_done={done[-1]}")
    return "\n".join(lines)


def _every_fifth_round(token_path: Path | None) -> str:
    """Returns injection text; kicks off detached compact-write."""
    if token_path:
        # Detached compact-write — refreshes handoff.md + last-user-prompt.md
        try:
            subprocess.Popen(
                [sys.executable, str(CONTEXT_ENGINE), "compact-write", "--token", str(token_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=str(ROOT), start_new_session=True,
            )
        except Exception:
            pass
        injection = _state_injection_text(token_path)
    else:
        injection = ""

    if GOAL_SIGNAL.exists():
        goal_text = _goal_state_text()
        if goal_text:
            injection = f"{injection}\n{goal_text}" if injection else goal_text
    return injection


def main() -> None:
    raw = sys.stdin.read()
    prompt = _extract_prompt(raw)

    # ─── /deny — clear approval state ───
    if re.search(r'(?:^|[^a-zA-Z0-9_])/deny\b', prompt):
        _safe_unlink(FALLBACK_REQUIRED)
        _safe_unlink(FALLBACK_APPROVED)
        print("🚫 /deny — 阻塞状态已清除。如需重新启用可输入 /approve <token>。",
              file=sys.stderr, flush=True)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── /approve <token> — validate and approve ───
    match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', prompt)
    if match:
        token = match.group(1)
        if not FALLBACK_REQUIRED.exists():
            print("ℹ️ /approve 忽略：当前无待解除的阻塞状态。",
                  file=sys.stderr, flush=True)
            print(json.dumps({"continue": True}))
            sys.exit(0)
        expected = FALLBACK_REQUIRED.read_text().strip()
        if token == expected:
            FALLBACK_APPROVED.write_text(token)
            print("✅ /approve 已接受！任务阻塞将在下次操作时自动解除。",
                  file=sys.stderr, flush=True)
        else:
            print("❌ /approve 失败：验证码不匹配。请检查输入的 token。",
                  file=sys.stderr, flush=True)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── Prompt ring (every round, fast) ───
    if prompt and not prompt.startswith("/"):
        try:
            total = _update_ring(prompt)
        except Exception:
            total = 0
    else:
        total = 0

    # ─── Every 5th round: compact-write (detached) + tail injection ───
    if total > 0 and total % INJECT_INTERVAL == 0:
        try:
            injection = _every_fifth_round(_latest_token())
        except Exception:
            injection = ""
        if injection:
            print(json.dumps({
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": injection,
                },
            }, ensure_ascii=False))
            sys.exit(0)

    print(json.dumps({"continue": True}))
    sys.exit(0)


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
