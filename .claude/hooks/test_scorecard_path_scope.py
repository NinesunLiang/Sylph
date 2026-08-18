"""test_scorecard_path_scope.py — pretool-scorecard-gate 路径门禁回归。

背景（2026-08-17 人类裁决）: 桌面个人文件被活跃任务 working-set 误拦。
修复方向:
  ① 仓库外绝对路径不适用任务产物路径契约 → 放行（桌面/daily_tasks 等）
  ② 仓库内越界路径 → ASK_USER（permissionDecision=ask），不 BLOCK（用户底线）
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS))


def _load_gate():
    """文件名含连字符，不能直接 import；按路径加载为模块。"""
    spec = importlib.util.spec_from_file_location(
        "pretool_scorecard_gate", _HOOKS / "pretool-scorecard-gate.py")
    assert spec is not None and spec.loader is not None, "hook 加载失败"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load_gate()


def _ws_yaml(allowed, denied=None) -> str:
    import yaml
    data = {
        "schema_version": "carros.working_set.v1",
        "level": "L2",
        "allowed_paths": list(allowed),
        "denied_paths": list(denied or []),
    }
    return yaml.safe_dump(data, allow_unicode=True)


def _task_dir(allowed=("src/", "tests/", "docs/")) -> Path:
    td = Path(tempfile.mkdtemp(prefix="sc-gate-"))
    (td / "working-set.yaml").write_text(_ws_yaml(allowed), encoding="utf-8")
    return td


# ── ① 仓库外路径放行 ──────────────────────────────────────────────────────

def test_out_of_repo_absolute_path_allowed():
    """桌面/外部个人文件 → 不适用任务产物契约 → 放行(None)。"""
    td = _task_dir()
    r = gate.check_path_scope("/Users/someone/Desktop/daily_tasks/心得.md", task_dir=str(td))
    assert r is None, f"仓库外路径应放行, 实际: {r}"


def test_out_of_repo_path_ignores_undeclared():
    """仓库外路径即使不匹配 allowed 也不 REDIRECT。"""
    td = _task_dir(allowed=("src/",))
    r = gate.check_path_scope("/tmp/random.txt", task_dir=str(td))
    assert r is None, f"仓库外未声明路径不应 REDIRECT, 实际: {r}"


# ── 仓库内路径仍受契约约束 ────────────────────────────────────────────────

def test_in_repo_allowed_relative_path_passes():
    td = _task_dir(allowed=("src/",))
    r = gate.check_path_scope("src/main.py", task_dir=str(td))
    assert r is None


def test_in_repo_allowed_absolute_path_passes():
    td = _task_dir(allowed=("src/",))
    r = gate.check_path_scope(str(Path.cwd() / "src" / "main.py"), task_dir=str(td))
    assert r is None


def test_in_repo_undeclared_path_redirects():
    """仓库内未声明路径 → 仍返回 REDIRECT（引导补声明），不静默放行。"""
    td = _task_dir(allowed=("src/",))
    r = gate.check_path_scope("misc/notes.txt", task_dir=str(td))
    assert r and "REDIRECT" in r, f"仓库内越界应 REDIRECT, 实际: {r}"


# ── ①b AI 生成白名单（SKILL step 11b）：任务路径声明进 allowed_paths ──────

def test_external_path_declared_in_allowed_passes():
    """AI 把仓库外输入/输出路径写入 allowed_paths（绝对声明）→ 放行。"""
    td = _task_dir(allowed=("/Users/someone/Desktop/daily_tasks/",))
    r = gate.check_path_scope("/Users/someone/Desktop/daily_tasks/心得.md", task_dir=str(td))
    assert r is None, f"声明进白名单的外部路径应放行, 实际: {r}"


def test_absolute_declaration_matches_prefix():
    """绝对路径声明按前缀匹配生效（契约权威，非仅靠仓库外豁免）。"""
    td = _task_dir(allowed=(str(Path.cwd() / "docs"),))
    r = gate.check_path_scope(str(Path.cwd() / "docs" / "sub" / "x.md"), task_dir=str(td))
    assert r is None, f"绝对声明应前缀匹配放行, 实际: {r}"


# ── ② 决策输出: ASK_USER 而非 BLOCK（用户底线）────────────────────────────

def test_scope_ask_payload_uses_ask():
    payload = gate._scope_ask_payload("REDIRECT 路径未声明: x")
    hso = payload["hookSpecificOutput"]
    assert hso["permissionDecision"] == "ask", \
        f"应 ASK 而非 BLOCK, 实际: {hso['permissionDecision']}"
    assert "路径未声明" in hso["permissionDecisionReason"]


def test_scope_ask_payload_contains_context():
    payload = gate._scope_ask_payload("REDIRECT 路径越界: y")
    assert "路径越界" in payload["hookSpecificOutput"]["additionalContext"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
