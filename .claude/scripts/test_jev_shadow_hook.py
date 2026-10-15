"""P1-b：JEV-C shadow 接线的边界测试。

接线的全部价值在于「开着也只是记录、关着等于不存在」。
所以这里测的不是「它判得准不准」，而是**它绝不改变任何结论**。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import carros_base as cb  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("CARROROS_JEV_SHADOW", raising=False)
    monkeypatch.delenv("CARROROS_JEV_SAMPLES", raising=False)


def test_off_by_default(monkeypatch, capsys):
    """默认不跑：既不起子进程，也不打印任何东西。"""
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    cb.TASK_DIR = Path("/tmp/nonexistent-task")
    cb._maybe_run_jev_shadow("S1")
    assert calls == [], "默认关闭时不得起任何子进程"
    assert capsys.readouterr().out == "", "默认关闭时不得有任何输出"


@pytest.mark.parametrize("val", ["0", "true", "yes", "", "2"])
def test_only_exactly_one_enables(monkeypatch, val, capsys):
    """只认 CARROROS_JEV_SHADOW=1 —— 避免「有值就开」这类含糊判断。"""
    monkeypatch.setenv("CARROROS_JEV_SHADOW", val)
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    cb.TASK_DIR = Path("/tmp/nonexistent-task")
    cb._maybe_run_jev_shadow("S1")
    assert calls == []
    assert capsys.readouterr().out == ""


def test_no_task_dir_is_noop(monkeypatch, capsys):
    monkeypatch.setenv("CARROROS_JEV_SHADOW", "1")
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    cb.TASK_DIR = None
    cb._maybe_run_jev_shadow("S1")
    assert calls == []


def test_failure_never_raises(monkeypatch, capsys):
    """shadow 崩了只能跳过，绝不能让 verify 挂掉。"""
    monkeypatch.setenv("CARROROS_JEV_SHADOW", "1")
    cb.TASK_DIR = Path("/tmp/nonexistent-task")

    def boom(*a, **k):
        raise RuntimeError("模拟子进程爆炸")

    monkeypatch.setattr("subprocess.run", boom)
    cb._maybe_run_jev_shadow("S1")  # 不得抛出
    assert "跳过" in capsys.readouterr().out


def test_timeout_is_bounded(monkeypatch):
    """必须带超时，否则 shadow 会把 verify 卡死。"""
    monkeypatch.setenv("CARROROS_JEV_SHADOW", "1")
    cb.TASK_DIR = Path("/tmp/nonexistent-task")
    seen = {}

    def capture(cmd, **kw):
        seen.update(kw)

        class R:
            returncode = 0
        return R()

    monkeypatch.setattr("subprocess.run", capture)
    cb._maybe_run_jev_shadow("S1")
    assert seen.get("timeout"), "必须设置超时"
    assert seen["timeout"] <= 300
    assert seen.get("check") is False, "不得因非零退出码抛异常"


def test_hook_sits_between_gate_and_atomic_write():
    """接线位置必须是「机械门禁之后、原子证据写入之前」—— 顺序错了语义就变了。"""
    src = inspect.getsource(cb.cmd_verify)
    i_hook = src.index("_maybe_run_jev_shadow(target)")
    i_gate = src.index("_run_verify_gate(target)")
    i_atomic = src.index("complete_step_atomic(")
    assert i_gate < i_hook < i_atomic, "shadow 必须夹在 VerifyGate 与 complete_step_atomic 之间"


def test_shadow_writes_only_under_jev_state():
    """接线点只允许写 .omc/state/jev/，不得碰 plan / token / executor / audit。

    注意：必须只看**可执行代码**，不能连文档字符串一起搜 ——
    函数的 docstring 里正好写着「不改变 complete_step_atomic 的调用与否」，
    纯文本搜索会把它当成违规。（第一版测试就栽在这里。）
    """
    import ast

    tree = ast.parse(inspect.getsource(cb._maybe_run_jev_shadow))
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # 去掉 docstring，只看真正的代码
    code = "\n".join(ast.unparse(n) for n in body)

    for forbidden in ("PLAN_PATH", "TOKEN_PATH", "EXECUTOR_PATH",
                      "_write_audit", "complete_step_atomic"):
        assert forbidden not in code, f"shadow 不得触碰 {forbidden}"
