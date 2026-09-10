"""index50：pre-commit（轻）与 pre-push（深）检查脚本回归。

人类要求：
- `lx-pre-commit` 要**轻**、**聚焦改动内容**、查**必要性/语法/格式**
- `lx-pre-push` 要**深**、查**安全/边界/破坏性/依赖性**
- 两者都**不得依赖未必安装的外部工具**（原版依赖 pip-audit/gosec → 本仓均未装 → 恒阻塞）
- 两者都**不得靠猜项目类型**（本仓无 go.mod/package.json/pyproject.toml → 原版会空转或恒阻塞）
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def pc():
    return _load("pre_commit_check_t", "pre_commit_check.py")


@pytest.fixture
def pp():
    return _load("pre_push_check_t", "pre_push_check.py")


# ── pre-commit：必要性 ──

def test_noise_detection(pc):
    assert pc.is_noise("__pycache__/x.pyc") is True
    assert pc.is_noise("a/.pytest_cache/b.json") is True
    assert pc.is_noise("node_modules/x/index.js") is True
    assert pc.is_noise("app.py") is False
    assert pc.is_noise("docs/readme.md") is False


def test_necessity_empty_is_blocking(pc):
    ok, msgs = pc.check_necessity([])
    assert ok is False and msgs


def test_necessity_all_noise_warns_but_passes(pc):
    ok, msgs = pc.check_necessity(["__pycache__/a.pyc"])
    assert ok is True
    assert any("缓存" in m or "生成物" in m for m in msgs)


def test_necessity_real_change_passes(pc):
    ok, msgs = pc.check_necessity(["app.py"])
    assert ok is True and msgs == []


# ── pre-commit：语法（只查改动文件）──

def test_syntax_catches_broken_python(tmp_path, pc, monkeypatch):
    (tmp_path / "bad.py").write_text("def f(:\n", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert pc.check_syntax("bad.py") is not None


def test_syntax_passes_valid_python(tmp_path, pc, monkeypatch):
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert pc.check_syntax("ok.py") is None


def test_syntax_catches_broken_json(tmp_path, pc, monkeypatch):
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert pc.check_syntax("bad.json") is not None


def test_syntax_skips_uncheckable_type(tmp_path, pc, monkeypatch):
    (tmp_path / "a.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert pc.check_syntax("a.png") is None


# ── pre-commit：格式 ──

def test_format_flags_trailing_whitespace(tmp_path, pc, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1   \ny = 2\n", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    issues = pc.check_format("a.py")
    assert any("行尾空白" in i for i in issues)


def test_format_flags_missing_final_newline(tmp_path, pc, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert any("末尾缺换行" in i for i in pc.check_format("a.py"))


def test_format_clean_file_is_empty(tmp_path, pc, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    assert pc.check_format("a.py") == []


# ── pre-push：边界 ──

def test_boundary_blocks_denied_paths(pp):
    ok, msgs = pp.check_boundary([".env"])
    assert ok is False and msgs
    assert pp.check_boundary(["secrets/key.txt"])[0] is False
    assert pp.check_boundary(["docs/carros/reviews/x.md"])[0] is False


def test_boundary_passes_normal_paths(pp):
    ok, msgs = pp.check_boundary(["app.py", "docs/readme.md"])
    assert ok is True and msgs == []


# ── pre-push：安全（不依赖外部工具）──

def test_security_no_external_tool_dependency(pp):
    """关键回归：原版依赖未安装的 pip-audit/gosec → 恒阻塞；新版用仓库自带模式库。"""
    assert pp._secret_patterns() is not None, "不得依赖外部工具，须用仓库自带模式"


def test_security_detects_secret_in_changed_file(tmp_path, pp, monkeypatch):
    fake = "sk-" + "A" * 24
    (tmp_path / "cfg.py").write_text(f'KEY = "{fake}"\n', encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    ok, msgs = pp.check_security(["cfg.py"])
    assert ok is False and msgs


def test_security_passes_clean_file(tmp_path, pp, monkeypatch):
    (tmp_path / "cfg.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    assert pp.check_security(["cfg.py"])[0] is True


# ── pre-push：破坏性 ──

def test_destructive_empty_is_ok(pp):
    assert pp.check_destructive([])[0] is True


def test_destructive_flags_orphan_reference(tmp_path, pp, monkeypatch):
    (tmp_path / "user.py").write_text("from helper import x\n", encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    monkeypatch.setattr(pp, "_tracked_files", lambda: ["user.py"])
    ok, msgs = pp.check_destructive(["helper.py"])
    assert ok is False and msgs


def test_destructive_passes_when_no_reference(tmp_path, pp, monkeypatch):
    (tmp_path / "user.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    monkeypatch.setattr(pp, "_tracked_files", lambda: ["user.py"])
    assert pp.check_destructive(["helper.py"])[0] is True


# ── pre-push：比对基线（实跑教训）──

def test_baseline_prefers_upstream(pp):
    """当前分支是 release，其 upstream 是 origin/release；若错用 origin/HEAD(=origin/main)
    会得到 391 个「改动」，完全失真。"""
    assert pp._baseline() in ("@{u}", "origin/HEAD", "HEAD")
    assert pp._baseline() == "@{u}", "本地 release 分支有 upstream，应优先用它"


def test_test_fixture_downgraded_to_warning(tmp_path, pp, monkeypatch):
    """测试夹具里的假密钥不得阻断（业界密钥扫描器惯例）。"""
    fake = "sk-" + "B" * 24
    (tmp_path / "test_fixture.py").write_text(f'K = "{fake}"\n', encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    ok, msgs = pp.check_security(["test_fixture.py"])
    assert ok is True and msgs == [], f"测试夹具不应阻断: {msgs}"


def test_real_key_in_non_test_file_still_blocks(tmp_path, pp, monkeypatch):
    fake = "sk-" + "C" * 24
    (tmp_path / "config.py").write_text(f'K = "{fake}"\n', encoding="utf-8")
    monkeypatch.setattr(pp, "ROOT", tmp_path)
    ok, msgs = pp.check_security(["config.py"])
    assert ok is False and msgs
