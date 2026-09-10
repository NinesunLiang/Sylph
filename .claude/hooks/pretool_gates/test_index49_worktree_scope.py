"""index49：worktree 隔离执行期的写路径门禁（补上上一轮遗留的洞）。

问题：`plan-done` 建立了 worktree，但**没有强制 agent 把代码改动写到 worktree 内**——
靠自觉。若 agent 仍写主树，隔离形同虚设，多进程照样互相踩。

本门：当活跃 goal token 带 `worktree` 字段（完备模式隔离执行中）时，
- 写到 **worktree 内** → 放行
- 写到 **`.omc/`** → 放行（账本按设计共享主树，见 index49 S2 的 symlink 方案）
- 写到 **主树其他路径** → REDIRECT，并给出 worktree 内的等价路径
- 无隔离执行（无 token / 无 worktree 字段）→ 本门 no-op
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pretool_gates import checks  # noqa: E402

ROOT = checks.ROOT
WT = ROOT / ".claude" / "worktrees" / "task-isolated-demo-abc123"


def _payload(path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


def _with_token(monkeypatch, token):
    monkeypatch.setattr(checks, "_active_token", lambda: token)


def test_no_active_token_is_noop(monkeypatch):
    _with_token(monkeypatch, None)
    assert checks._check_worktree_scope(_payload(str(ROOT / "app.py"))) is None


def test_token_without_worktree_is_noop(monkeypatch):
    """非隔离执行（如 L1 简易模式）不受本门管辖。"""
    _with_token(monkeypatch, {"session": {"level": "L1"}})
    assert checks._check_worktree_scope(_payload(str(ROOT / "app.py"))) is None


def test_write_inside_worktree_passes(monkeypatch):
    _with_token(monkeypatch, {"worktree": str(WT)})
    assert checks._check_worktree_scope(_payload(str(WT / "app.py"))) is None


def test_write_to_main_tree_code_is_redirected(monkeypatch):
    """核心：隔离执行中写主树代码 → 必须被拦下并指向 worktree。"""
    _with_token(monkeypatch, {"worktree": str(WT)})
    result = checks._check_worktree_scope(_payload(str(ROOT / "src" / "app.py")))
    assert result is not None and result.startswith("REDIRECT"), result
    assert "worktree" in result.lower(), result


def test_ledger_write_to_main_tree_passes(monkeypatch):
    """账本（.omc/）按设计共享主树，不得拦。"""
    _with_token(monkeypatch, {"worktree": str(WT)})
    assert checks._check_worktree_scope(_payload(str(ROOT / ".omc" / "tasks" / "x" / "plan.md"))) is None


def test_path_outside_repo_passes(monkeypatch):
    _with_token(monkeypatch, {"worktree": str(WT)})
    assert checks._check_worktree_scope(_payload("/tmp/somewhere/app.py")) is None


def test_read_tool_is_not_gated(monkeypatch):
    """只拦写；读不受影响。"""
    _with_token(monkeypatch, {"worktree": str(WT)})
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "app.py")}}
    assert checks._check_worktree_scope(payload) is None
