#!/usr/bin/env python3
"""
water_level.py — CarrorOS 三段式水位运行时

互斥区间定义:
  safe:   [0.00, 0.40) — 正常执行
  warn:   [0.40, 0.70) — 建议 checkpoint，禁止扩张
  crit:   [0.70, 1.00] — 暂停 + 写 handoff + 请求 compact

分子：可控注入 token 数（_estimate_current_tokens）
分母：可控预算上限（MAX_TOKENS = 12000）
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path.cwd()
sys.path.insert(0, str(PROJECT / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT / ".omc" / "scripts"))
STATE_DIR = PROJECT / ".omc" / "state"
CRITICAL_STATE = STATE_DIR / "context-critical.json"

# 可控预算上限
MAX_TOKENS = 12000

# 三级水位互斥定义（左闭右开 / 闭区间）
LEVELS = [
    ("safe",  0.00, 0.40, "OK: <40% — safe to continue"),
    ("warn",  0.40, 0.70, "WARNING: >=40% — checkpoint suggested, no expansion"),
    ("crit",  0.70, 1.01, "CRITICAL: >=70% — pause, write handoff, request compact"),
]


def _estimate_current_tokens() -> int:
    """估算当前可控注入 token 数（基于文件大小）。"""
    total = 0
    for path, _name in [
        (PROJECT / "AGENTS.md", "AGENTS"),
        (PROJECT / ".claude/kernel.md", "kernel"),
        (PROJECT / ".claude/index.md", "index"),
        (PROJECT / ".claude/settings.json", "settings"),
    ]:
        if path.exists():
            total += path.stat().st_size
    return total // 4  # chars/4 ≈ tokens


def _ratio_to_level(ratio: float) -> str:
    """将 ratio 映射到互斥水位区间。"""
    for name, low, high, _msg in LEVELS:
        if low <= ratio < high:
            return name
    return "crit"  # fallback (ratio >= 1.0)


def get_water_level(controllable_tokens: int = None) -> str:
    """获取当前水位：safe / warn / crit"""
    if controllable_tokens is None:
        controllable_tokens = _estimate_current_tokens()
    ratio = controllable_tokens / MAX_TOKENS if MAX_TOKENS > 0 else 0
    return _ratio_to_level(ratio)


def get_water_detail(controllable_tokens: int = None) -> dict:
    """获取水位详情。"""
    if controllable_tokens is None:
        controllable_tokens = _estimate_current_tokens()
    ratio = controllable_tokens / MAX_TOKENS if MAX_TOKENS > 0 else 0
    level = _ratio_to_level(ratio)

    # 根据互斥区间找到对应消息
    suggestion = ""
    for _name, _low, _high, msg in LEVELS:
        if _name == level:
            if level == "crit":
                if _is_task_active():
                    suggestion = "PAUSE: >=70%, task not stopping — write handoff, compact, then resume"
                else:
                    suggestion = "COMPACT: >=70%, task is stopping or done — run compact"
            else:
                suggestion = msg
            break

    return {
        "level": level,
        "ratio": round(ratio, 3),
        "controllable_tokens": controllable_tokens,
        "max_tokens": MAX_TOKENS,
        "suggestion": suggestion,
    }


def _is_task_active() -> bool:
    for token_file in sorted(PROJECT.rglob(".omc/tokens/*/*.json")):
        try:
            t = json.loads(token_file.read_text())
            if t.get("status") == "active":
                return True
        except (json.JSONDecodeError, OSError):
            continue
    return False


def _persist_critical_pause(water: dict) -> Path:
    """Persist GA critical-context pause state for PreToolUse hard gating."""
    from datetime import datetime, timezone
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "status": "PAUSED_CONTEXT_CRITICAL",
        "reason": "context water level is critical",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "water": water,
        "allowed_actions": ["status", "checkpoint", "compact", "resume", "archive"],
    }
    CRITICAL_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return CRITICAL_STATE


def clear_critical_pause() -> None:
    CRITICAL_STATE.unlink(missing_ok=True)


def _write_handoff_and_compact():
    try:
        from lib.handoff_writer import write_handoff
        for token_file in sorted(PROJECT.rglob(".omc/tokens/*/*.json")):
            try:
                t = json.loads(token_file.read_text())
                if t.get("status") == "active":
                    tid = t.get("session", {}).get("id", "unknown")
                    write_handoff(
                        PROJECT / ".omc/tasks" / Path(token_file.parent.name) / tid,
                        tid, t
                    )
                    t["water_level_triggered"] = "compact"
                    token_file.write_text(json.dumps(t, indent=2))
                    return True
            except (json.JSONDecodeError, OSError):
                continue
    except Exception:
        pass
    return False


def run_water_gate(action: str = None, step: str = None) -> dict:
    water = get_water_detail()

    if water["level"] == "safe":
        return {"continue": True, "message": "water safe", "water": water}

    if water["level"] == "warn":
        return {"continue": True, "message": f"water warn ({water['ratio']:.0%}) — consider compact", "water": water}

    if water["level"] == "crit":
        _persist_critical_pause(water)
        if _is_task_active() and action not in ("archive",):
            _write_handoff_and_compact()
            return {"continue": False, "message": f"water crit ({water['ratio']:.0%}) — PAUSED_CONTEXT_CRITICAL. Handoff written.", "water": water}
        return {"continue": True, "message": f"water crit ({water['ratio']:.0%}) — compact suggested", "water": water}

    return {"continue": True, "message": "unknown", "water": water}
