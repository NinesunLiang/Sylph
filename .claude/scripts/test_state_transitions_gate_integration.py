"""state_transitions gate 集成测试（ADR 0015 补全）。

守护点：cmd_verify 任务全绿完成（stats.done >= stats.total）必须经过
state_transitions.require_transition("executing", "done")——覆盖 step_contracts
与 legacy 两条完成路径。若有人移除 gate 调用，本测试红。
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _FakeST:
    """替换 carros.state_transitions，记录 require_transition 调用。"""

    def __init__(self):
        self.calls = []

    def require_transition(self, from_state, to_state):
        self.calls.append((from_state, to_state))


PLAN_TEXT = """- [a] S1: first
  - verify: assertion: step S1 evidence is recorded
"""

EXECUTOR_TEXT = """## Conditions
- scope: gate integration test fixture
## Key Changes
- change: wire require_transition into verify completion
## Decisions
- Rationale: ADR 0015 guard executing->done via YAML transitions
## Acceptance Checklist
- [x] gate wired
## TDD Evidence
- Dependency TDD command: pytest -> exit 0
- Regression TDD command: pytest -> exit 0
### EV-S1
- step: S1
- type: test
- source: integration fixture
- exit_code: 0
- file: test_state_transitions_gate_integration.py
- assertion: step S1 evidence is recorded; require_transition invoked on full completion
"""


def _make_token(tmp_path):
    return {
        "schema_version": "v1.0",
        "status": "active",
        "session": {"id": "st-gate-test", "level": "L1",
                    "created_at": "x", "updated_at": "x"},
        "task": {"current_step": "S1", "status": "planning", "blocked": None},
        "stats": {"done": 0, "total": 1, "tick": 0},
        "task_dir": str(tmp_path),
    }


def test_verify_full_completion_invokes_state_transitions_gate(tmp_path, monkeypatch):
    """任务全绿完成必须经过 require_transition("executing","done")。"""
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_st_gate")
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(PLAN_TEXT, encoding="utf-8")
    executor.write_text(EXECUTOR_TEXT, encoding="utf-8")
    token.write_text(json.dumps(_make_token(tmp_path)), encoding="utf-8")
    monkeypatch.setattr(carros, "TOKEN_PATH", token)
    monkeypatch.setattr(carros, "TASK_DIR", tmp_path)
    monkeypatch.setattr(carros, "PLAN_PATH", plan)
    monkeypatch.setattr(carros, "EXECUTOR_PATH", executor)
    monkeypatch.setattr(carros, "HANDOFF_PATH", tmp_path / "handoff.md")
    fake = _FakeST()
    monkeypatch.setattr(carros, "state_transitions", fake)

    assert carros.cmd_verify("S1") == 0
    assert ("executing", "done") in fake.calls, \
        "verify 完成任务必须调用 state_transitions.require_transition('executing','done')"
    sys.modules.pop("carros_st_gate", None)
