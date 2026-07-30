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
  - Fast path <100ms on non-5th rounds (ring append)
  - compact-write runs detached (Popen, no wait) — hook never waits on it
"""
from __future__ import annotations
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
TASKS_DIR = ROOT / ".omc" / "tasks"
RING_PATH = ROOT / ".omc" / ".prompt-ring.json"
RING_STATE = ROOT / ".omc" / ".prompt-ring-state.json"
CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"
COMPACT_WRITE_LOG = STATE_DIR / "compact-write.log"

# Round7 PKG-1: token 读取委托 SSOT(单一真相源,禁第二实现)
# 直插 lib 目录按顶层模块导入——hooks/lib 正规包会遮蔽 lib.* 包路径
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
except Exception:  # SSOT 不可用时本钩降级为跳过 token 回写/注入(永不阻断 prompt)
    _ssot_latest_active_token = None

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
    """Latest ACTIVE carros task token — 委托 task_ssot(单一真相源)。

    保 stats 要求(SSOT 写入目标必须有 stats dict);SSOT 不可用 → None(降级跳过)。
    根因(2026-07-20 幻影 token 事件):mtime 取最新 + 本文件每轮回写 → 陈旧任务自我续命。
    """
    if _ssot_latest_active_token is None:
        return None
    return _ssot_latest_active_token(TOKENS_DIR, require_stats=True)


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


def _resolve_task_dir(token_path: Path) -> Path | None:
    """从 token 解析任务目录(compact-write 需要读 plan.md 得到真实进度)。

    顺序: task.dir / token.task_dir → .omc/tasks/<date>/<slug>(slug=token 文件名去 _token)。
    """
    data = _read_json(token_path, {})
    task = data.get("task")
    explicit = None
    if isinstance(task, dict):
        explicit = task.get("dir")
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
        # R5 留痕: stdout 丢弃、stderr 落 .omc/state/compact-write.log,
        # spawn 异常也记档——detached 不再静默(仍不阻塞 prompt,exit 0)
        # #17: 传 --task 让 handoff 拿到 plan.md 真实进度(此前缺参恒 verified 0/0)
        cmd = [sys.executable, str(CONTEXT_ENGINE), "compact-write", "--token", str(token_path)]
        task_dir = _resolve_task_dir(token_path)
        if task_dir:
            cmd += ["--task", str(task_dir)]
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            err_log = COMPACT_WRITE_LOG.open("ab")
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL, stderr=err_log,
                cwd=str(ROOT), start_new_session=True,
            )
        except Exception as exc:
            try:
                with COMPACT_WRITE_LOG.open("a", encoding="utf-8") as f:
                    f.write(f"{_now_iso()} compact-write spawn FAILED: {exc!r}\n")
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
