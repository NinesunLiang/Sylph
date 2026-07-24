#!/usr/bin/env python3
"""test-e4-inertia.py — Round7 PKG-3 E4 终态惯性 BLOCK 对抗套件

验收(GPT 纪律): 测试只调生产入口(_check_plan_gate / _failure_escalate /
latest_terminal_token),禁复制生产判定逻辑自证;故障注入不得静默放行。

场景矩阵:
  P1 正向: 全新仓库(无 token 目录) → auto-init 放行(不 BLOCK)
  P2 正向: 活跃 token 在库 → 走既有分支,不触发终态惯性
  A1 对抗: 最新任务 token 已 done → BLOCK terminal_inertia,auto-init 未触发
  A2 对抗: 最新已 archived(顶层 status)→ BLOCK(top-level 终态也拦截)
  A3 对抗: 终态 + 同签名 BLOCK 已 3 次 → 升级 ASK_USER(ESCALATE)
  A4 对抗: 终态但 audit 里是同签名仅 2 次 → 维持 BLOCK(不误升级)
  A5 对抗: 仅有非任务 json(lx-goal 锁)与 malformed → auto-init 放行
         (非任务/损坏不算"上一任务已终态")
  A6 对抗: _failure_escalate 窗口截断——3 次命中在 20 条窗口外 → 不升级
  A7 对抗: 读工具(Read)不受终态惯性影响 → 放行

退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))

from task_ssot import latest_terminal_token  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "pretool_gate", ROOT / ".claude" / "hooks" / "pretool-gate.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_token(tokens: Path, day: str, name: str, obj: dict | str, mtime_offset: float = 0.0) -> Path:
    p = tokens / day / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        p.write_text(obj, encoding="utf-8")
    else:
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    ts = time.time() + mtime_offset
    os.utime(p, (ts, ts))
    return p


def _task(status: str = "active", task_id: str = "t1", top_status: str | None = None) -> dict:
    d: dict = {
        "task": {"id": task_id, "status": status, "current_step": "S1"},
        "stats": {"done": 0, "total": 4},
    }
    if top_status is not None:
        d["status"] = top_status
    return d


def _write_payload(path: str = "/tmp/x.md") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


gate = _load_gate()

# ── 每个场景独立沙盒: monkeypatch gate.TOKENS / gate.AUDIT / gate._auto_init ──
orig_tokens, orig_audit, orig_auto_init = gate.TOKENS, gate.AUDIT, gate._auto_init


def run_scenario(name: str, setup, expect):
    """setup(tmp) 建 token/audit;expect(result_str, auto_init_called, gate) 断言。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tokens = tmp_path / "tokens"
        audit = tmp_path / "audit"
        tokens.mkdir()
        audit.mkdir()
        auto_init_calls: list[str | None] = []
        gate.TOKENS = tokens
        gate.AUDIT = audit
        gate._auto_init = lambda p=None: auto_init_calls.append(p)
        try:
            setup(tokens, audit)
            result = gate._check_plan_gate(_write_payload())
            expect(result, auto_init_calls)
        finally:
            gate.TOKENS, gate.AUDIT, gate._auto_init = orig_tokens, orig_audit, orig_auto_init


# ── P1 全新仓库: 无任何 token → auto-init 放行 ──
run_scenario(
    "P1",
    lambda t, a: None,
    lambda result, calls: check(
        "P1 fresh-repo-auto-init-pass", result is None and len(calls) == 1,
        f"result={result!r} auto_init_calls={calls}"),
)

# ── P2 活跃 token 在库 → 不触发终态惯性分支 ──
def setup_p2(t, a):
    _write_token(t, "20260720", "live.json", _task("active", "live-task"))

run_scenario(
    "P2",
    setup_p2,
    lambda result, calls: check(
        "P2 active-token-no-inertia", result is None and len(calls) == 0,
        f"result={result!r}"),
)

# ── A1 最新任务 token done → BLOCK + auto-init 未触发 ──
def setup_a1(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "old-task"))

run_scenario(
    "A1",
    setup_a1,
    lambda result, calls: check(
        "A1 terminal-done-blocks", bool(result) and result.startswith("BLOCK terminal_inertia:old-task")
        and len(calls) == 0,
        f"result={result!r} auto_init_calls={calls}"),
)

# ── A2 顶层 status=archived(task.status=active)→ BLOCK ──
def setup_a2(t, a):
    _write_token(t, "20260720", "arch.json", _task("active", "polluted-task", top_status="archived"))

run_scenario(
    "A2",
    setup_a2,
    lambda result, calls: check(
        "A2 top-level-archived-blocks", bool(result) and result.startswith("BLOCK terminal_inertia:")
        and len(calls) == 0,
        f"result={result!r}"),
)

# ── A3 同签名 BLOCK 已 3 次 → 升级 ASK_USER ──
def setup_a3(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "loop-task"))
    day_file = a / "2026-07-20.jsonl"
    lines = [
        json.dumps({"event_type": "terminal_inertia_block", "decision": "BLOCK",
                    "reason": "terminal_inertia:loop-task", "timestamp": f"2026-07-20T0{i}:00:00+00:00"})
        for i in range(3)
    ]
    day_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

run_scenario(
    "A3",
    setup_a3,
    lambda result, calls: check(
        "A3 repeat-3x-escalates", bool(result) and result.startswith("ASK_USER terminal_inertia:loop-task"),
        f"result={result!r}"),
)

# ── A4 同签名仅 1 次历史 → 维持 BLOCK(阈值=3:本次+历史共 2 次,不误升级) ──
# 注:生产实现先写本次 BLOCK 审计再计数,故历史 1 次+本次 1 次=2 < 3 → 不升级。
def setup_a4(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "two-task"))
    day_file = a / "2026-07-20.jsonl"
    day_file.write_text(
        json.dumps({"event_type": "terminal_inertia_block", "decision": "BLOCK",
                    "reason": "terminal_inertia:two-task", "timestamp": "2026-07-20T00:00:00+00:00"})
        + "\n", encoding="utf-8")

run_scenario(
    "A4",
    setup_a4,
    lambda result, calls: check(
        "A4 history-1x-stays-block", bool(result) and result.startswith("BLOCK terminal_inertia:two-task"),
        f"result={result!r}"),
)

# ── A4b 边界: 历史 2 次 + 本次 1 次 = 3 → 升级(阈值精确命中) ──
def setup_a4b(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "edge-task"))
    day_file = a / "2026-07-20.jsonl"
    lines = [
        json.dumps({"event_type": "terminal_inertia_block", "decision": "BLOCK",
                    "reason": "terminal_inertia:edge-task", "timestamp": f"2026-07-20T0{i}:00:00+00:00"})
        for i in range(2)
    ]
    day_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

run_scenario(
    "A4b",
    setup_a4b,
    lambda result, calls: check(
        "A4b history-2x-plus-current-escalates", bool(result) and result.startswith("ASK_USER terminal_inertia:edge-task"),
        f"result={result!r}"),
)

# ── A5 仅非任务 json + malformed → auto-init 放行 ──
def setup_a5(t, a):
    _write_token(t, "20260720", "goal-lock.json", {"goal": "x", "lock": True})
    _write_token(t, "20260720", "broken.json", "{not json", mtime_offset=1)

run_scenario(
    "A5",
    setup_a5,
    lambda result, calls: check(
        "A5 non-task-and-malformed-pass", result is None and len(calls) == 1,
        f"result={result!r} auto_init_calls={calls}"),
)

# ── A6 命中在 20 条窗口外 → 不升级 ──
def setup_a6(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "deep-task"))
    day_file = a / "2026-07-20.jsonl"
    lines = []
    # 3 次命中在最旧,然后 20 条其他 gate BLOCK 把它们挤出窗口
    for i in range(3):
        lines.append(json.dumps({"event_type": "terminal_inertia_block", "decision": "BLOCK",
                                 "reason": "terminal_inertia:deep-task",
                                 "timestamp": f"2026-07-19T0{i}:00:00+00:00"}))
    for i in range(20):
        lines.append(json.dumps({"event_type": "scope_violation", "decision": "BLOCK",
                                 "reason": f"token_scope_violation:{i}",
                                 "timestamp": f"2026-07-20T10:{i:02d}:00+00:00"}))
    day_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

run_scenario(
    "A6",
    setup_a6,
    lambda result, calls: check(
        "A6 hits-outside-window-no-escalate", bool(result) and result.startswith("BLOCK terminal_inertia:deep-task"),
        f"result={result!r}"),
)

# ── A7 读工具不受影响 → 放行 ──
def setup_a7(t, a):
    _write_token(t, "20260720", "done-task.json", _task("done", "read-task"))

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    tokens, audit = tmp_path / "tokens", tmp_path / "audit"
    tokens.mkdir(); audit.mkdir()
    gate.TOKENS, gate.AUDIT = tokens, audit
    gate._auto_init = lambda p=None: None
    try:
        setup_a7(tokens, audit)
        result = gate._check_plan_gate({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x.md"}})
        check("A7 read-tool-pass", result is None, f"result={result!r}")
    finally:
        gate.TOKENS, gate.AUDIT, gate._auto_init = orig_tokens, orig_audit, orig_auto_init

# ── A8 latest_terminal_token 契约: 活跃 + 终态混合 → 仍取到终态(SSOT 自身) ──
with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp) / "tokens"
    _write_token(t, "20260719", "term.json", _task("archived", "term-task"), mtime_offset=-10)
    _write_token(t, "20260720", "live.json", _task("active", "live-task"), mtime_offset=0)
    got = latest_terminal_token(t)
    check("A8 ssot-terminal-found-despite-active", got is not None and got.stem == "term",
          f"got={got}")

# ── A9 _failure_escalate fail-open: audit 目录不存在 → False(不炸不升级) ──
with tempfile.TemporaryDirectory() as tmp:
    gate.AUDIT = Path(tmp) / "nonexistent-audit"
    try:
        check("A9 escalate-fail-open", gate._failure_escalate("terminal_inertia:x") is False)
    finally:
        gate.AUDIT = orig_audit

print("---")
if failures:
    print(f"FAILED: {len(failures)} 项: {failures}")
    sys.exit(1)
print("ALL PASS (E4 终态惯性 BLOCK 对抗套件)")
sys.exit(0)
