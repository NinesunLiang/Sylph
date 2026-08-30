"""test_light_mode_verify.py — 流程规模自适应（index34 S1）

light 任务 verify：无 plan/research ceremony，跳过 F2 依赖树检查，
仅校验 executor.md 的 EV 证据块（含 exit_code: 0）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_carros(name: str = "carros_light_verify"):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/scripts/carros_base.py")
    assert spec is not None and spec.loader is not None, "carros_base.py 加载失败"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _setup_light_task(carros, tmp_path, task_id="light-verify-test"):
    """创建隔离的 light 任务（token + executor），返回任务目录。"""
    from pathlib import Path as _P
    carros.OMC_TOKENS = _P(tmp_path) / "tokens"
    carros.HANDOFF_PATH = _P(tmp_path) / "handoff.md"
    task_dir = _P(tmp_path) / "task"
    carros._init_task_paths(task_id=task_id, task_dir=str(task_dir))
    rc = carros.cmd_init(task_id=task_id, task_dir=str(task_dir), light=True)
    assert rc == 0, f"init light 失败: {rc}"
    return task_dir


EV_EXECUTOR = """# Executor Evidence Ledger (Light Task)

## Key Changes

- 实现了 add 函数并验证。

## S1

### EV-S1

- step: S1
- type: test/review/change
- evidence_level: E3
- source: python3 test_calculator.py
- exit_code: 0
- file: calculator.py
- assertion: add(2,3)==5 通过

---
"""


def test_light_verify_passes_with_ev_evidence(tmp_path):
    """light 任务 executor 含 EV exit_code:0 → verify 通过。"""
    carros = _load_carros()
    task_dir = _setup_light_task(carros, tmp_path)
    (task_dir / "executor.md").write_text(EV_EXECUTOR, encoding="utf-8")
    rc = carros.cmd_verify()
    assert rc == 0, f"有 EV 证据应 verify 通过, 实际 rc={rc}"
    # token 应标记完成
    token_files = list((tmp_path / "tokens").rglob("*.json"))
    token = json.loads(token_files[0].read_text(encoding="utf-8"))
    assert token["task"]["status"] == "completed", f"verify 后应 completed: {token['task']}"


def test_light_verify_rejects_without_ev(tmp_path):
    """light 任务无 EV 证据 → verify 拒绝（exit 2）。"""
    carros = _load_carros()
    task_dir = _setup_light_task(carros, tmp_path)
    (task_dir / "executor.md").write_text("# 没有证据\n", encoding="utf-8")
    rc = carros.cmd_verify()
    assert rc == 2, f"无 EV 证据应拒绝, 实际 rc={rc}"


def test_light_verify_no_plan_required(tmp_path):
    """light 任务无 plan.md 也能 verify（跳过 F2/plan 检查）。"""
    carros = _load_carros()
    task_dir = _setup_light_task(carros, tmp_path)
    # 确认无 plan.md（light 特性）
    assert not (task_dir / "plan.md").exists()
    (task_dir / "executor.md").write_text(EV_EXECUTOR, encoding="utf-8")
    rc = carros.cmd_verify()
    assert rc == 0, f"light 无 plan 应 verify 通过（跳过 F2）, 实际 rc={rc}"


def test_light_verify_rejects_unfilled_template(tmp_path):
    """未填写的 light 模板（exit_code: pending）→ verify 拒绝（防空过）。"""
    carros = _load_carros()
    task_dir = _setup_light_task(carros, tmp_path)
    # 不覆盖 executor，保持 init 生成的模板（exit_code: pending）
    rc = carros.cmd_verify()
    assert rc == 2, f"未填 EV 证据（exit_code pending）应拒绝, 实际 rc={rc}"


def test_light_verify_rejects_forged_empty_evidence(tmp_path):
    """验收加固：伪造空证据（exit_code:0 但 source/file/assertion 为 (none)）→ verify 拒绝。"""
    carros = _load_carros()
    task_dir = _setup_light_task(carros, tmp_path)
    forged = """# Executor Evidence Ledger (Light Task)

## Key Changes

- nothing

## S1

### EV-S1

- step: S1
- type: test/review/change
- evidence_level: E3
- source: (none)
- exit_code: 0
- file: (none)
- assertion: (none)

---
"""
    (task_dir / "executor.md").write_text(forged, encoding="utf-8")
    rc = carros.cmd_verify()
    assert rc == 2, f"伪造空证据应拒绝, 实际 rc={rc}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
