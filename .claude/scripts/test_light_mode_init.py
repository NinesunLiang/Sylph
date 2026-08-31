"""test_light_mode_init.py — 流程规模自适应（index34 S1）

简单任务 L1-light 直通：init --light 不生成 research/plan 空壳（免 ceremony 卡死），
token 带 task.mode=light + task.status=executing，仅最小 executor.md。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_carros(name: str = "carros_light_init"):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/scripts/carros_base.py")
    assert spec is not None and spec.loader is not None, "carros_base.py 加载失败"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _setup_paths(carros, tmp_path, task_id="light-test"):
    """隔离路径：token 写 tmp/tokens，任务文档写 tmp/task，handoff 写 tmp。"""
    from pathlib import Path as _P
    carros.OMC_TOKENS = _P(tmp_path) / "tokens"
    carros.HANDOFF_PATH = _P(tmp_path) / "handoff.md"
    task_dir = _P(tmp_path) / "task"
    carros._init_task_paths(task_id=task_id, task_dir=str(task_dir))
    return task_dir


def test_light_init_creates_light_token(tmp_path):
    carros = _load_carros()
    task_dir = _setup_paths(carros, tmp_path)
    rc = carros.cmd_init(task_id="light-test", task_dir=str(task_dir), light=True)
    assert rc == 0, f"init --light 应 exit 0, 实际 {rc}"
    # token 带 light 标记 + executing
    token_files = list((tmp_path / "tokens").rglob("*.json"))
    assert token_files, "token 未创建"
    token = json.loads(token_files[0].read_text(encoding="utf-8"))
    assert token["task"].get("mode") == "light", f"task.mode 应为 light: {token['task']}"
    assert token["task"]["status"] == "executing", f"light 任务应直接 executing: {token['task']}"
    assert token["stats"]["total"] == 1


def test_light_init_no_plan_research_skeleton(tmp_path):
    """light 模式不生成 plan/research 空壳（无占位符骨架），仅最小 executor。"""
    carros = _load_carros()
    task_dir = _setup_paths(carros, tmp_path)
    carros.cmd_init(task_id="light-test", task_dir=str(task_dir), light=True)
    assert not (task_dir / "plan.md").exists(), "light 不应生成 plan.md 空壳"
    assert not (task_dir / "research.md").exists(), "light 不应生成 research.md 空壳"
    assert (task_dir / "executor.md").exists(), "light 应生成最小 executor.md"


def test_light_executor_has_ev_template(tmp_path):
    """light executor.md 含 EV 证据模板（verify 靠它校验）。"""
    carros = _load_carros()
    task_dir = _setup_paths(carros, tmp_path)
    carros.cmd_init(task_id="light-test", task_dir=str(task_dir), light=True)
    text = (task_dir / "executor.md").read_text(encoding="utf-8")
    assert "EV-S1" in text and "exit_code" in text, "executor 应含 EV 模板"


def test_light_skips_ceremony_files(tmp_path):
    """index40 L1-light 轻量化：不生成 working-set.yaml / evidence.jsonl / handoff.md。"""
    carros = _load_carros()
    task_dir = _setup_paths(carros, tmp_path)
    carros.cmd_init(task_id="light-test", task_dir=str(task_dir), light=True)
    assert not (task_dir / "working-set.yaml").exists(), "light 不应生成 working-set.yaml"
    assert not (task_dir / "evidence.jsonl").exists(), "light 不应生成 evidence.jsonl"
    assert not (task_dir / "handoff.md").exists(), "light 不应生成 handoff.md"
    # 仍保留 token + executor.md（verify 依赖）
    token_files = list((tmp_path / "tokens").rglob("*.json"))
    assert token_files, "light 仍需 token"
    assert (task_dir / "executor.md").exists(), "light 仍需 executor.md"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
