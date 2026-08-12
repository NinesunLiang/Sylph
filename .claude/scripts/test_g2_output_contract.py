"""G2 出参契约测试（ADR 0015 二期）。

start_step_atomic / complete_step_atomic 必须返回结构化结果
{"ok": bool, "step_id": str, "errors": list}，成功路径可被调用方消费。
失败路径保留 ValueError（向后兼容既有 raise 语义）。
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SC = load_module(ROOT / ".claude/scripts/step_contracts.py", "step_contracts_g2")


def _start_fixture(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text("- [ ] S1: start\n  - status: pending\n", encoding="utf-8")
    executor.write_text("## Conditions\n\n", encoding="utf-8")
    token.write_text(json.dumps({"task": {}, "revision": 0}), encoding="utf-8")
    return token, plan, executor


def _complete_fixture(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        "- [x] S1: done\n  - status: completed\n  - verify: assertion:done\n",
        encoding="utf-8",
    )
    executor.write_text(
        """## Conditions
ok
## Key Changes
ok
## Decisions
- Rationale: test
## Acceptance Checklist
- [x] done
## TDD Evidence
- Dependency TDD command: exit 0
- Regression TDD command: exit 0
### EV-S1
- step: S1
- type: test
- source: test
- evidence_level: E3
- exit_code: 0
- file: test
- assertion: done
""",
        encoding="utf-8",
    )
    token.write_text(json.dumps({"stats": {"done": 1, "total": 1}}), encoding="utf-8")
    return token, plan, executor


def test_start_step_atomic_returns_structured_result(tmp_path):
    token, plan, executor = _start_fixture(tmp_path)
    result = SC.start_step_atomic(token, plan, executor, "S1")
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}: {result!r}"
    assert result["ok"] is True
    assert result["step_id"] == "S1"
    assert result["errors"] == []
    # 副作用仍生效（行为不变）
    assert "status: active" in plan.read_text(encoding="utf-8")


def test_complete_step_atomic_returns_structured_result(tmp_path):
    token, plan, executor = _complete_fixture(tmp_path)
    result = SC.complete_step_atomic(token, plan, executor, "S1")
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}: {result!r}"
    assert result["ok"] is True
    assert result["step_id"] == "S1"
    assert result["errors"] == []


def test_start_step_atomic_failure_keeps_valueerror(tmp_path):
    token, plan, executor = _start_fixture(tmp_path)
    with pytest.raises(ValueError):
        SC.start_step_atomic(token, plan, executor, "S999")  # 不存在的 step
