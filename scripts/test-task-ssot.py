#!/usr/bin/env python3
"""test-task-ssot.py — Round7 PKG-1 状态SSOT 对抗套件

覆盖 2026-07-20 幻影 token 事故全形态 + 四 reader 委托:
  P1 正向: archived 新于 active → 仍取 active
  A1 对抗: 仅 archived/malformed/非任务三类 → None(幻影形态全灭)
  A2 对抗: archived mtime 最新 → 跳过,取次新 active
  A3 对抗: require_stats=True 过滤无 stats 的任务 token
  A4 对抗: statusline.latest_token 对全 archived 目录 → None(第4 reader 幻影类死)
  L1 活体: 真仓库 .omc/tokens 若有活跃任务,四 reader 结论一致

退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))

from task_ssot import latest_active_token  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def _write(path: Path, obj: dict | str, mtime_offset: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    ts = time.time() + mtime_offset
    os.utime(path, (ts, ts))


def _task(status: str = "active", *, stats: bool = True, top_status: str | None = None) -> dict:
    d: dict = {"task": {"id": "t", "status": status, "current_step": "S1"}}
    if stats:
        d["stats"] = {"done": 0, "total": 4}
    if top_status is not None:
        d["status"] = top_status
    return d


with tempfile.TemporaryDirectory() as tmp:
    tokens = Path(tmp) / "tokens"

    # ── P1 正向: active(mtime 旧) vs archived(mtime 新) → 取 active ──
    _write(tokens / "20260719" / "old-active.json", _task("active"), mtime_offset=-100)
    _write(tokens / "20260720" / "new-archived.json", _task("done"), mtime_offset=0)
    got = latest_active_token(tokens)
    check("P1 active-old-vs-archived-new", got is not None and got.stem == "old-active", f"got={got}")

    # ── A1 对抗: 幻影全形态(archived/malformed/非任务) → None ──
    with tempfile.TemporaryDirectory() as tmp2:
        t2 = Path(tmp2) / "tokens"
        _write(t2 / "20260720" / "a.json", _task("completed"), 0)
        _write(t2 / "20260720" / "b.json", _task("active", top_status="archived"), -1)
        _write(t2 / "20260720" / "c.json", "{not json", -2)
        _write(t2 / "20260720" / "d.json", {"goal": "x", "lock": True}, -3)  # lx-goal 物理锁形态
        _write(t2 / "20260720" / "e.json", {}, -4)
        check("A1 phantom-forms-all-dead", latest_active_token(t2) is None)

    # ── A2 对抗: archived 最新 + active 次新 → 跳过 archived ──
    with tempfile.TemporaryDirectory() as tmp3:
        t3 = Path(tmp3) / "tokens"
        _write(t3 / "20260720" / "z-archived.json", _task("archived"), 0)
        _write(t3 / "20260720" / "y-active.json", _task("active"), -5)
        got = latest_active_token(t3)
        check("A2 archived-newest-skipped", got is not None and got.stem == "y-active", f"got={got}")

    # ── A3 对抗: require_stats 过滤 ──
    with tempfile.TemporaryDirectory() as tmp4:
        t4 = Path(tmp4) / "tokens"
        _write(t4 / "20260720" / "no-stats.json", _task("active", stats=False), 0)
        check("A3 require-stats-filters", latest_active_token(t4, require_stats=True) is None)
        check("A3 default-keeps", latest_active_token(t4) is not None)

    # ── A4 对抗: statusline 第4 reader 幻影类死 ──
    import statusline  # noqa: E402

    with tempfile.TemporaryDirectory() as tmp5:
        root5 = Path(tmp5)
        t5 = root5 / ".omc" / "tokens"
        _write(t5 / "20260720" / "old.json", _task("done"), 0)
        check("A4 statusline-archived-none", statusline.latest_token(root5) is None)

# ── L1 活体: 真仓库四 reader 一致性(有活跃任务时) ──
live_tokens = ROOT / ".omc" / "tokens"
live = latest_active_token(live_tokens)
if live is not None:
    import importlib

    statusline_mod = importlib.import_module("statusline")
    st = statusline_mod.latest_token(ROOT)
    check("L1 statusline-matches-ssot", st == live, f"ssot={live} statusline={st}")

    import importlib.util

    spec = importlib.util.spec_from_file_location("ua", ROOT / ".claude" / "hooks" / "pretool-user-approve.py")
    ua = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ua)
    check("L1 user-approve-matches-ssot", ua._latest_token() == live, f"ua={ua._latest_token()} live={live}")
else:
    print("SKIP  L1 (无活跃任务 token)")

# ── PKG-2 追加: 二期三 reader + error_dna 死导入修复 ──
import importlib.util  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pg = _load("posttool_gate", ROOT / ".claude" / "hooks" / "posttool-gate.py")
pc = _load("precompact_lifecycle", ROOT / ".claude" / "hooks" / "precompact-lifecycle.py")
mo = _load("meta_oracle_review", ROOT / ".claude" / "scripts" / "meta-oracle-review.py")

# ── A5 对抗: 二期三 reader 对幻影形态全灭(archived 最新也不得复活) ──
with tempfile.TemporaryDirectory() as tmp6:
    t6 = Path(tmp6) / "tokens"
    _write(t6 / "20260720" / "phantom.json", _task("done"), mtime_offset=0)
    _write(t6 / "20260720" / "arch-top.json", _task("active", top_status="archived"), mtime_offset=1)

    orig_pg, orig_pc, orig_mo = pg.TOKENS_DIR, pc.TOKENS_DIR, mo.TOKENS_DIR
    try:
        pg.TOKENS_DIR = pc.TOKENS_DIR = mo.TOKENS_DIR = t6
        td, _step = pg._active_task()
        check("A5 posttool-phantom-dead", td is None, f"got={td}")
        check("A5 precompact-phantom-dead", pc._latest_token() is None)
        check("A5 meta-oracle-phantom-dead", mo._latest_task_id() is None)
    finally:
        pg.TOKENS_DIR, pc.TOKENS_DIR, mo.TOKENS_DIR = orig_pg, orig_pc, orig_mo

# ── A6 对抗: error_dna 死导入修复回归(2026-07-20 前: lib.error_dna 解析到
#    hooks/lib 空包 → ImportError 被 except 吞 → error DNA 静默死) ──
check("A6 error-dna-import-live", pg._record_error is not None)

# ── A7 对抗: 同 task 多 token(皆 active)→ 取 mtime 最新(SSOT 确定契约) ──
with tempfile.TemporaryDirectory() as tmp7:
    t7 = Path(tmp7) / "tokens"
    older = _task("active")
    older["task"]["id"] = "same-task"
    newer = _task("active")
    newer["task"]["id"] = "same-task"
    _write(t7 / "20260719" / "old.json", older, mtime_offset=-50)
    _write(t7 / "20260720" / "new.json", newer, mtime_offset=0)
    got = latest_active_token(t7)
    check("A7 same-task-multi-token", got is not None and got.stem == "new", f"got={got}")

# ── A8 对抗: 跨天 active(仅旧日期有 active,新日期全 archived)→ 跨天取到 ──
with tempfile.TemporaryDirectory() as tmp8:
    t8 = Path(tmp8) / "tokens"
    _write(t8 / "20260718" / "cross-day.json", _task("active"), mtime_offset=-200)
    _write(t8 / "20260720" / "today-archived.json", _task("archived"), mtime_offset=0)
    got = latest_active_token(t8)
    check("A8 cross-day-active-found", got is not None and got.stem == "cross-day", f"got={got}")

# ── L2 活体: 七 reader 一致性(SSOT + 一期 4 + 二期 3) ──
if live is not None:
    check("L2 precompact-matches-ssot", pc._latest_token() == live,
          f"pc={pc._latest_token()} live={live}")
    td2, _s2 = pg._active_task()
    data = json.loads(live.read_text(encoding="utf-8"))
    exp = data.get("task_dir")
    exp_dir = (ROOT / exp) if isinstance(exp, str) and exp else None
    check("L2 posttool-task-dir-matches", td2 == exp_dir, f"got={td2} exp={exp_dir}")
    check("L2 meta-oracle-id-matches", mo._latest_task_id() in (data.get("session", {}).get("id"), live.stem),
          f"got={mo._latest_task_id()}")
else:
    print("SKIP  L2 (无活跃任务 token)")

print("---")
if failures:
    print(f"FAILED: {len(failures)} 项: {failures}")
    sys.exit(1)
print("ALL PASS (task_ssot 对抗套件)")
sys.exit(0)
