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


# ── goal plan 模板内置格式契约（2026-08-17 用户裁决：提前给模板不返工）──

def test_goal_scaffold_plan_has_format_skeleton(tmp_path, monkeypatch):
    """goal plan.md 模板自带 Phase/step/字段骨架，AI 照填不重排格式。"""
    mod = _load_carros("carros_goal_skeleton", tmp_path)
    mod.RESEARCH_PATH = tmp_path / "research.md"
    mod._write_goal_scaffolds()
    plan = (tmp_path / "plan.md").read_text(encoding="utf-8")
    assert "## Phase 1" in plan
    assert "- [ ] S1:" in plan
    assert "  - scope:" in plan
    assert "  - acceptance:" in plan
    assert "  - verify: assertion:" in plan
    assert "格式契约" in plan
    sys.modules.pop("carros_goal_skeleton", None)


def test_goal_scaffold_skeleton_parses_under_plangate(tmp_path, monkeypatch):
    """骨架示例 step 可被 PlanGate 格式校验识别（verify 前缀合法、无孤儿 step）。"""
    import goal_contracts
    mod = _load_carros("carros_goal_parse", tmp_path)
    mod.RESEARCH_PATH = tmp_path / "research.md"
    mod._write_goal_scaffolds()
    plan = (tmp_path / "plan.md").read_text(encoding="utf-8")
    # 复用 PlanGate 的正则：Phase 头 + step 必须被正确解析
    import re
    phases = re.findall(r"^## Phase\s+\d+\s*$", plan, re.MULTILINE)
    assert len(phases) >= 1, f"Phase 头应为 ## Phase N，实际: {phases}"
    steps = re.findall(r"^- \[ \] (\S+?):", plan, re.MULTILINE)
    assert steps, "骨架应有可解析的 step"
    # 骨架 step 的 verify 带合法前缀（assertion:），引导里列出全部可选项
    assert re.search(r"- verify: assertion:", plan) is not None, "骨架 verify 前缀缺失"
    assert "file:" in plan and "command:" in plan, "引导应列出 file:/command: 可选前缀"
    sys.modules.pop("carros_goal_parse", None)
