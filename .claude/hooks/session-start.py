#!/usr/bin/env python3
"""
session-start.py — CarrorOS SessionStart hook（compact 恢复 / 新会话导航）

注入（stdout additionalContext）：
  1. .omc/session-handoff.md — 会话交接（compact 后恢复）
  2. .omc/state/last-user-prompt.md — 最近用户请求
  3. 活跃 token 状态（task/step/progress）

副作用（唯一）:source=compact/resume 时 boundary-aware 重测水位快照——
  pua 常规测量读 transcript 最后一条 usage,compact 刚完成时该记录仍是压缩前的
  (2026-07-20 实测: 84.3% 陈旧快照 FORCE 误拦 compact 后续跑)。owner 裁决:
  SessionStart 触发重测,最后锚点为 boundary 且无 post-usage 时按
  used = postTokens + overhead(上一 boundary 实测,fallback 30k) 刷新。

设计：快速（<200ms，尾读 512KB）、永不阻断。无活跃任务时静默退出。
"""
from __future__ import annotations

import importlib.util
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

# Round7 PKG-1: token 读取委托 SSOT(单一真相源,禁第二实现)
# 直插 lib 目录按顶层模块导入——hooks/lib 正规包会遮蔽 lib.* 包路径
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
except Exception:  # SSOT 不可用 → 跳过 token brief(注入类 hook,永不阻断)
    _ssot_latest_active_token = None

# Round7 Task#14: 水位重测复用 pua 写口(_write_watermark_state 唯一写口,禁第二实现)
_pua = None
try:
    _spec = importlib.util.spec_from_file_location(
        "pretool_user_approve", HOOK_DIR / "pretool-user-approve.py")
    if _spec is not None and _spec.loader is not None:
        _pua = importlib.util.module_from_spec(_spec)
        sys.modules["pretool_user_approve"] = _pua  # dataclass 反查需先注册(本项目教训)
        _spec.loader.exec_module(_pua)  # 模块级仅常量/导入,main 有 __name__ 守卫
except Exception:  # pua 不可用 → 跳过重测(注入类 hook,永不阻断)
    _pua = None

WM_TAIL_BYTES = 512 * 1024  # 与 pua._measure_used_tokens 尾读口径一致
WM_OVERHEAD_FALLBACK = 30000  # 固定开销(系统提示+工具 schema+记忆)实测区间 26.4k-31.6k


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
    if _ssot_latest_active_token is None:
        return ""
    path = _ssot_latest_active_token(TOKENS_DIR)
    if path is None:
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


def _usage_total(line: str) -> int | None:
    """与 pua._measure_used_tokens 同口径: input+cache_read+cache_creation。"""
    if '"usage"' not in line:
        return None
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        return None
    msg = rec.get("message")
    usage = msg.get("usage") if isinstance(msg, dict) else None
    if not isinstance(usage, dict):
        return None
    return (int(usage.get("input_tokens", 0))
            + int(usage.get("cache_read_input_tokens", 0))
            + int(usage.get("cache_creation_input_tokens", 0)))


def _remeasure_watermark(transcript: Path | None) -> None:
    """compact/resume 后第一轮刷新水位快照(boundary-aware)。

    常规测量(pua._update_watermark)取 transcript 最后一条 usage——compact 刚完成时
    该记录仍是压缩前的(2026-07-20 实测: 84.3% 陈旧快照 FORCE 误拦 compact 后续跑,
    下一轮才自愈为 27.8%)。本函数仅在「最后锚点 = compact_boundary 且其后无 usage」
    时走估算: used = postTokens + overhead(上一 boundary 实测,fallback 30k);
    其余情形委托 pua 常规路径。任何异常静默跳过(注入 hook 永不阻断)。
    """
    if transcript is None or _pua is None:
        return
    try:
        if not transcript.exists():
            return
        size = transcript.stat().st_size
        with transcript.open("rb") as f:
            f.seek(max(0, size - WM_TAIL_BYTES))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return
    last_post: int | None = None         # 最后一条 boundary 的 postTokens
    usage_after_last: int | None = None  # 最后 boundary 之后的第一条 usage
    overhead: int | None = None          # 上一 boundary 实测固定开销
    prev_post: int | None = None
    prev_usage: int | None = None
    for line in lines:
        if '"compact_boundary"' in line:
            try:
                meta = json.loads(line).get("compactMetadata") or {}
                post = meta.get("postTokens")
            except json.JSONDecodeError:
                continue
            if isinstance(post, int) and post > 0:
                if prev_post is not None and prev_usage is not None and prev_usage > prev_post:
                    overhead = prev_usage - prev_post
                prev_post, prev_usage = post, None
                last_post, usage_after_last = post, None
            continue
        u = _usage_total(line)
        if u is not None and u > 0:
            if prev_post is not None and prev_usage is None:
                prev_usage = u
            if last_post is not None and usage_after_last is None:
                usage_after_last = u
    try:
        if last_post is not None and usage_after_last is None:
            # 最后锚点是 boundary: compact 后尚无 usage,陈旧快照必须刷新
            _pua._write_watermark_state(last_post + (overhead or WM_OVERHEAD_FALLBACK))
        else:
            # 常规: 最后锚点是 usage(或无 boundary)——pua 原路径
            _pua._update_watermark(transcript)
    except Exception:
        pass


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


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    source = str(payload.get("source") or "startup")

    if source in ("compact", "resume"):
        _tp = payload.get("transcript_path")
        _remeasure_watermark(Path(_tp) if isinstance(_tp, str) and _tp.strip() else None)

    parts: list[str] = []

    token_brief = _active_token_brief()
    if token_brief:
        parts.append(token_brief)

    stepwise_brief = _stepwise_brief()
    if stepwise_brief:
        parts.append(stepwise_brief)

    if HANDOFF.exists():
        try:
            raw = HANDOFF.read_text(encoding="utf-8")
            ts = _handoff_ts(raw, HANDOFF)
            banner = ""
            if ts:
                age_h = (datetime.now(timezone.utc).timestamp() - ts) / 3600
                if age_h > STALE_HOURS:
                    banner = (
                        f"⚠️ [STALE handoff — 更新于 {_age_str(ts)}前,超 {STALE_HOURS}h] "
                        "内容可能过期;以 token/plan 磁盘态为准,勿直接按其恢复旧任务\n"
                    )
            text = raw[:MAX_HANDOFF]
            if text.strip():
                parts.append(f"[Session Handoff — {source} 恢复导航]\n{banner}{text}")
        except Exception:
            pass

    if source in ("compact", "resume") and LAST_PROMPTS.exists():
        try:
            text = LAST_PROMPTS.read_text(encoding="utf-8")[:MAX_PROMPTS]
            if text.strip():
                parts.append(f"[Last User Prompts]\n{text}")
        except Exception:
            pass

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
