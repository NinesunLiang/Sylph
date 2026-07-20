#!/usr/bin/env python3
"""
pretool-user-approve.py — CarrorOS Unified UserPromptSubmit Gate

Multiplexes (single hook, Base lightweight philosophy):
  1. /approve <token> /deny — CAPTCHA approval for blocked tasks
  2. Prompt ring — rolling 20 user prompts (.claude/.prompt-ring.json)
  3. Every 5th prompt — detached compact-write (refreshes handoff + last-user-prompt)
  4. Every 5th prompt — U-attention tail injection (task state via additionalContext)
  5. Goal mode — appends goal state when autonomous.active exists
  6. Context watermark — 每轮从 transcript 实测上下文水位(owner 规格: 50%提醒/70%只读/80%强制),
     写 .omc/state/context-watermark.json + token session(供 state-injection 与 pretool-gate 水位门)

Constraints:
  - Never blocks: always exit 0
  - Fast path <100ms on non-5th rounds (ring append + tail-read watermark)
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
TASKS_DIR = ROOT / ".omc" / "tasks"
RING_PATH = ROOT / ".claude" / ".prompt-ring.json"
RING_STATE = ROOT / ".claude" / ".prompt-ring-state.json"
CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"
COMPACT_WRITE_LOG = STATE_DIR / "compact-write.log"
WATERMARK_PATH = STATE_DIR / "context-watermark.json"

MAX_RING = 20
INJECT_INTERVAL = 5  # 每 5 轮：compact-write + 尾部状态注入（U 型注意力）

# 水位规格(owner 2026-07-20 裁决): 50% 提醒 / 70% 只读 / 80% 强制
# limit 默认 170k = 2026-07-19 实测 auto-compact 触发点(preTokens=170,508);
# 标称 1M 是模型宣传上限,有效窗口以实测为准;env CARROROS_CONTEXT_LIMIT 可覆盖
WATERMARK_REMIND = 50.0
WATERMARK_READONLY = 70.0
WATERMARK_FORCE = 80.0
DEFAULT_CONTEXT_LIMIT = 170_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# 终态集合：archived/done/completed 的 token 不参与水位回写与状态注入。
# 根因(2026-07-20 幻影 token 事件)：mtime 取最新 + 本文件每轮回写 → 陈旧任务自我续命。
_TERMINAL_TOKEN_STATUS = ("archived", "done", "completed")


def _latest_token() -> Path | None:
    """Latest ACTIVE carros task token (skips terminal-status and non-dict-task tokens)."""
    if not TOKENS_DIR.exists():
        return None
    candidates = sorted(
        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    for path in candidates:
        data = _read_json(path, {})
        if not isinstance(data, dict) or not data:
            continue
        if str(data.get("status", "")).lower() in _TERMINAL_TOKEN_STATUS:
            continue
        task = data.get("task")
        if not isinstance(task, dict):
            continue  # lx-goal 物理锁等非任务 token
        if str(task.get("status", "")).lower() in _TERMINAL_TOKEN_STATUS:
            continue
        if not isinstance(data.get("stats"), dict):
            continue
        return path
    return None


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


def _extract_transcript_path(raw: str) -> Path | None:
    """Hook payload 里的 transcript_path(用于水位实测)。"""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tp = data.get("transcript_path") or data.get("transcriptPath")
    if not isinstance(tp, str) or not tp.strip():
        return None
    p = Path(tp)
    return p if p.exists() else None


def _context_limit() -> int:
    try:
        return int(os.environ.get("CARROROS_CONTEXT_LIMIT", "") or DEFAULT_CONTEXT_LIMIT)
    except ValueError:
        return DEFAULT_CONTEXT_LIMIT


def _measure_used_tokens(transcript: Path) -> int | None:
    """尾部扫描 transcript 找最近一次 usage,返回 input+cache_read+cache_creation 总量。

    尾读 512KB(transcript 可达数十 MB);usage 只出现在 assistant 消息上,
    最后一次 usage ≈ 当前上下文总量(每轮 cache_read 重放几乎全部历史)。
    """
    try:
        size = transcript.stat().st_size
        with transcript.open("rb") as f:
            f.seek(max(0, size - 512 * 1024))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(tail.splitlines()):
        if '"usage"' not in line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message")
        usage = msg.get("usage") if isinstance(msg, dict) else None
        if not isinstance(usage, dict):
            continue
        return int(usage.get("input_tokens", 0)) + int(usage.get("cache_read_input_tokens", 0)) + int(
            usage.get("cache_creation_input_tokens", 0)
        )
    return None


def _watermark_level(pct: float) -> str:
    if pct >= WATERMARK_FORCE:
        return "FORCE"
    if pct >= WATERMARK_READONLY:
        return "READONLY"
    if pct >= WATERMARK_REMIND:
        return "REMIND"
    return "SAFE"


def _update_watermark(transcript: Path | None) -> dict | None:
    """实测水位 → 写 state 文件 + 同步 token session。返回 {pct, used, limit, level}。"""
    if transcript is None:
        return None
    used = _measure_used_tokens(transcript)
    if used is None or used <= 0:
        return None
    limit = _context_limit()
    pct = round(used / limit * 100, 1)
    level_name = _watermark_level(pct)
    data = {"pct": pct, "used": used, "limit": limit, "level": level_name, "at": _now_iso()}
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        WATERMARK_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return data
    # 同步进最新 token 的 session(state-injection/compact_decision 据此工作)——best-effort
    token_path = _latest_token()
    if token_path:
        token = _read_json(token_path, {})
        session = token.get("session")
        if isinstance(session, dict):
            session["context_watermark"] = pct
            session["compact_status"] = level_name
            try:
                token_path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
    return data


def _watermark_injection_line(wm: dict | None) -> str:
    if not wm:
        return ""
    level_name = wm.get("level", "SAFE")
    pct = wm.get("pct", 0)
    if level_name == "FORCE":
        return f"🔴 W: {pct}% ≥80% — 强制 compact: 立即停止一切操作并运行 /compact"
    if level_name == "READONLY":
        return f"🟠 W: {pct}% ≥70% — 只读模式: 禁止写操作,收尾验证后立即 /compact"
    if level_name == "REMIND":
        return f"🟡 W: {pct}% ≥50% — 建议 /compact 释放上下文"
    return ""


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


def _every_fifth_round(token_path: Path | None, watermark: dict | None) -> str:
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

    wm_line = _watermark_injection_line(watermark)
    if wm_line:
        injection = f"{wm_line}\n{injection}" if injection else wm_line
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

    # ─── 水位实测(每轮,尾读 transcript;永不阻断) ───
    try:
        watermark = _update_watermark(_extract_transcript_path(raw))
    except Exception:
        watermark = None

    # ─── Every 5th round: compact-write (detached) + tail injection ───
    if total > 0 and total % INJECT_INTERVAL == 0:
        try:
            injection = _every_fifth_round(_latest_token(), watermark)
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
