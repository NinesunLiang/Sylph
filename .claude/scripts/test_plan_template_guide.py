"""plan 模板引导（还债 S2）：默认 plan.md 引导 AI 写可验证的 verify 规则。

背景：默认 verify 是水规则 `assertion: step S1 evidence is recorded`，
VerifyGate 只能做语义自述比对，无法自动验证。模板引导 AI 优先写
file:/command: 规则（VerifyGate 真实读文件/真实执行），减少水规则。
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_carros(name, tmp_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/scripts/carros_base.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.PLAN_PATH = tmp_path / "plan.md"
    mod.EXECUTOR_PATH = tmp_path / "executor.md"
    return mod


def test_default_plan_guides_verifiable_verify_rules(tmp_path, monkeypatch):
    mod = _load_carros("carros_plan_guide", tmp_path)
    mod._write_default_plan(["S1"])
    plan = (tmp_path / "plan.md").read_text(encoding="utf-8")
    assert "verify" in plan
    assert "file:" in plan
    assert "command:" in plan
    assert "真实读文件" in plan
    sys.modules.pop("carros_plan_guide", None)


def test_guided_rules_still_parseable(tmp_path, monkeypatch):
    """引导示例必须是可被 parse_verify_rules 识别的格式（file: 前缀合法）。"""
    import verify_gate
    plan_text = (
        "# Plan\n\n## Goal\n\n## Scope\n\n"
        "> 引导：\n"
        "> 1. file: src/module.py contains \"def handle\"\n"
        "> 2. command: pytest tests/test_x.py -q\n"
        "> 3. assertion: step S1 done\n\n"
        "## Phase 1\n"
        "- [ ] S1: task\n"
        "  - verify: file: src/module.py contains def handle\n"
    )
    rules = verify_gate.parse_verify_rules(plan_text, "S1")
    assert rules == ["file: src/module.py contains def handle"]
