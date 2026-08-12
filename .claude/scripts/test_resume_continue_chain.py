"""recovery 完整链 E2E：resume --continue 自动续跑（C9/E8 提分）。

验证 cmd_resume(auto_continue=True)：
1. 有 pending step 时触发 tick + verify
2. 无 pending（终态）时不触发
"""
import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
# 让 `from lib.task_paths import ...` 在 carros_base 内可解析
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent))  # .claude/ 使 lib 包在 .claude/scripts/lib 下可寻

SCRIPT = SCRIPTS_DIR / "carros_base.py"
spec = importlib.util.spec_from_file_location("carros_base_under_test", SCRIPT)
assert spec is not None
carros_base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(carros_base)


def _make_task(tmp_path, plan_text):
    """构造一个可 resume 的任务目录。"""
    task = tmp_path / "tasks" / "20260812" / "my-task"
    (task / "plan.md").parent.mkdir(parents=True, exist_ok=True)
    (task / "plan.md").write_text(plan_text, encoding="utf-8")
    (task / "executor.md").write_text("# Executor\n", encoding="utf-8")
    (task / "state").mkdir(parents=True, exist_ok=True)
    tokens = tmp_path / "tokens" / "20260812"
    tokens.mkdir(parents=True, exist_ok=True)
    (tokens / "my-task.json").write_text(json.dumps({
        "session": {"id": "my-task", "level": "L1"},
        "task_dir": str(task),
        "status": "active",
        "task": {"status": "active", "current_step": None},
        "stats": {"done": 0, "total": 2},
    }, ensure_ascii=False), encoding="utf-8")
    return task, tokens


def _patch_resolve(tmp_path, task, tokens, monkeypatch):
    """绕过 resolve_task_document 的路径校验（tmp_path 不在真实 .omc/tasks 下）。

    cmd_resume 内 `from lib.task_paths import resolve_task_document` 在每次调用时
    从 sys.modules 取 lib.task_paths。这里注入一个 fake 模块，使 import 返回
    fake resolve_task_document —— 不依赖 .claude/scripts 是否已在 sys.path。
    """
    monkeypatch.setattr(carros_base, "OMC_TOKENS", tmp_path / "tokens")
    monkeypatch.setattr(carros_base, "OMC_TASKS", tmp_path / "tasks")
    monkeypatch.setattr(carros_base, "OMC_ROOT", tmp_path)
    monkeypatch.setenv("CARROROS_TOKEN_PATH", str(tokens / "my-task.json"))
    fake_doc = {"task_dir": task, "token_path": tokens / "my-task.json",
                "slug": "my-task", "date": "20260812"}
    fake_lib = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("lib", str(SCRIPTS_DIR / "lib" / "task_paths.py"))
    )
    # 预置一个最小 lib 包命名空间（__path__ 使子模块可注册）
    lib_ns = type(sys)("lib")
    lib_ns.__path__ = [str(SCRIPTS_DIR / "lib")]
    lib_ns.resolve_task_document = lambda task_doc: fake_doc
    monkeypatch.setitem(sys.modules, "lib", lib_ns)
    fake_tp = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location("lib.task_paths", str(SCRIPTS_DIR / "lib" / "task_paths.py"))
    )
    fake_tp.resolve_task_document = lambda task_doc: fake_doc
    monkeypatch.setitem(sys.modules, "lib.task_paths", fake_tp)


def test_resume_continue_triggers_tick_for_pending(tmp_path, monkeypatch):
    task, tokens = _make_task(
        tmp_path,
        "# Plan\n- [x] S1: done\n- [ ] S2: pending\n",
    )
    _patch_resolve(tmp_path, task, tokens, monkeypatch)

    calls = {"tick": [], "verify": []}

    def fake_tick(step_id=None, **kw):
        calls["tick"].append(step_id)
        return 0

    def fake_verify(step_id=None, **kw):
        calls["verify"].append(step_id)
        return 0

    monkeypatch.setattr(carros_base, "cmd_tick", fake_tick)
    monkeypatch.setattr(carros_base, "cmd_verify", fake_verify)

    rc = carros_base.cmd_resume(task_doc=str(task), auto_continue=True)
    assert rc == 0
    assert "S2" in calls["tick"], f"应 tick S2, got {calls['tick']}"
    assert "S2" in calls["verify"], f"应 verify S2, got {calls['verify']}"


def test_resume_continue_noop_when_terminal(tmp_path, monkeypatch):
    task, tokens = _make_task(
        tmp_path,
        "# Plan\n- [x] S1: done\n- [x] S2: done\n",
    )
    _patch_resolve(tmp_path, task, tokens, monkeypatch)

    calls = {"tick": []}

    def fake_tick(step_id=None, **kw):
        calls["tick"].append(step_id)
        return 0

    monkeypatch.setattr(carros_base, "cmd_tick", fake_tick)

    rc = carros_base.cmd_resume(task_doc=str(task), auto_continue=True)
    assert rc == 0
    assert calls["tick"] == [], f"终态任务不应 tick, got {calls['tick']}"
