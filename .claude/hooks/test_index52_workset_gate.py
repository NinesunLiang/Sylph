"""index52：working-set 路径契约「真实化」回归。

实测背景（改动前）：
- 29/31 个任务的 `allowed_paths` 是 init 占位值 `src/ tests/ docs/`，与本仓实际结构不符
- 加上 `_active_task_dir()` 只认 `.omc/state/active-resume.json`（仅 lx-goal resume 会写）
  → **双重失效**：平时门禁永不上线；一旦上线又因占位值误拦 `.claude/scripts/**`（实测误拦率 33%）

改动：
1. 模板默认 `allowed_paths` 由占位改为 `./`（= 不约束范围），`_path_matches` 认通配写法
2. `_active_task_dir()` 增补「近期活跃 token」回退，并加**新鲜度判据**拒绝陈旧任务
   （实测仓内有 5 个 Aug-31 遗留锁，其 working-set 仍是占位 → 会被拿错数据误拦）
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "sg52", ROOT / ".claude" / "hooks" / "pretool-scorecard-gate.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("sg52", mod)
    spec.loader.exec_module(mod)
    return mod


# ── 通配「不约束范围」──

def test_dot_slash_matches_everything():
    sg = _load()
    for p in ("/repo/.claude/scripts/x.py", "/repo/src/a.py", "docs/b.md"):
        assert sg._path_matches(p, "./") is True, p


def test_dot_and_star_also_match_everything():
    sg = _load()
    assert sg._path_matches("/repo/anything/x.py", ".") is True
    assert sg._path_matches("/repo/anything/x.py", "*") is True


def test_narrowed_scope_still_restricts():
    """收窄后必须真正受限——否则「默认宽松」会变成「永不设防」。"""
    sg = _load()
    assert sg._path_matches("/repo/docs/a.md", "docs/") is True
    assert sg._path_matches("/repo/.claude/scripts/x.py", "docs/") is False


# ── 门禁上线：只认「近期活跃」任务 ──

def _mk_token(tokens_root: Path, date: str, slug: str, task_dir: Path, age_hours: float) -> None:
    d = tokens_root / date
    d.mkdir(parents=True, exist_ok=True)
    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    (d / f"{slug}.json").write_text(json.dumps({
        "session": {"id": slug, "updated_at": ts},
        "task_dir": str(task_dir),
    }), encoding="utf-8")
    (d / f"{slug}.json.lock").write_text("", encoding="utf-8")


def test_active_task_dir_finds_fresh_token(tmp_path, monkeypatch):
    sg = _load()
    task = tmp_path / "task"
    task.mkdir()
    _mk_token(tmp_path / ".omc" / "tokens", "20260911", "fresh-task", task, age_hours=1)
    monkeypatch.setattr(sg, "ROOT", tmp_path)
    assert sg._active_task_dir() == str(task)


def test_active_task_dir_ignores_stale_token(tmp_path, monkeypatch):
    """陈旧未归档任务（如仓内 5 个 Aug-31 遗留锁）不得被当作活跃任务。"""
    sg = _load()
    task = tmp_path / "task"
    task.mkdir()
    _mk_token(tmp_path / ".omc" / "tokens", "20260831", "stale-task", task, age_hours=24 * 10)
    monkeypatch.setattr(sg, "ROOT", tmp_path)
    assert sg._active_task_dir() is None


def test_active_task_dir_prefers_fresh_over_stale(tmp_path, monkeypatch):
    sg = _load()
    fresh = tmp_path / "fresh"
    stale = tmp_path / "stale"
    fresh.mkdir()
    stale.mkdir()
    _mk_token(tmp_path / ".omc" / "tokens", "20260831", "stale-task", stale, age_hours=240)
    _mk_token(tmp_path / ".omc" / "tokens", "20260911", "fresh-task", fresh, age_hours=2)
    monkeypatch.setattr(sg, "ROOT", tmp_path)
    assert sg._active_task_dir() == str(fresh)


def test_active_task_dir_resume_pointer_wins(tmp_path, monkeypatch):
    sg = _load()
    task = tmp_path / "from-ptr"
    task.mkdir()
    state = tmp_path / ".omc" / "state"
    state.mkdir(parents=True)
    (state / "active-resume.json").write_text(
        json.dumps({"task_dir": str(task)}), encoding="utf-8")
    monkeypatch.setattr(sg, "ROOT", tmp_path)
    assert sg._active_task_dir() == str(task)


# ── 模板默认值 ──

def test_template_default_is_unrestricted():
    """模板默认必须是「不约束范围」，否则新任务一出生就误拦。"""
    import yaml
    tmpl = ROOT / ".claude" / "references" / "working-set-template.yaml"
    data = yaml.safe_load(tmpl.read_text(encoding="utf-8"))
    allowed = data.get("allowed_paths") or []
    assert "./" in allowed, f"模板默认应为不约束范围，实际 {allowed}"
    assert "src/" not in allowed, "不得再出现与本仓无关的占位路径"
