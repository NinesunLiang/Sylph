"""发行包防过期（2026-10-24 D-025）。

packaging/template/ 按 main 的做法提交进仓库，安装器直接用、零构建步骤。
代价是它可能和源码脱节——本测试就是那道闸：逐文件比对哈希，不一致即红。

修法：跑 python3 packaging/build.py，然后把 packaging/template/ 一起提交。
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging" / "build.py"
TEMPLATE = ROOT / "packaging" / "template"

pytestmark = pytest.mark.skipif(not BUILD.is_file(), reason="打包能力未启用")


def _load_build():
    spec = importlib.util.spec_from_file_location("packaging_build", BUILD)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_template_is_committed():
    assert TEMPLATE.is_dir(), "packaging/template/ 不存在：安装器将无法工作"
    assert (TEMPLATE / "AGENTS.md").is_file()
    assert (TEMPLATE / ".claude" / "hooks" / "pretool-gate.py").is_file()


def test_template_has_no_secrets_tests_or_runtime_data():
    assert list(TEMPLATE.rglob("test_*.py")) == [], "包内不得含测试文件"
    assert list(TEMPLATE.rglob("settings.local.json")) == [], "包内不得含密钥文件"
    assert list(TEMPLATE.rglob("*.jsonl")) == [], "包内不得含运行数据"
    assert not (TEMPLATE / ".omc").exists(), "包内不得含 .omc"


def test_template_matches_source():
    """模板必须等于当前源码按白名单组装的结果（防提交后忘记重新生成）。"""
    build = _load_build()
    manifest = build.yaml.safe_load(build.MANIFEST.read_text(encoding="utf-8"))
    expected = {rel: src for src, rel in build._collect(manifest)}

    actual = {
        p.relative_to(TEMPLATE).as_posix(): p
        for p in TEMPLATE.rglob("*")
        if p.is_file() and p.name != "VERSION.json"
    }

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    assert not missing, f"模板缺少 {len(missing)} 个文件，例如 {missing[:5]}；请重新 build"
    assert not extra, f"模板多出 {len(extra)} 个文件，例如 {extra[:5]}；请重新 build"

    drift = []
    for rel, src in expected.items():
        if rel == ".claude/settings.json":
            want = build._sanitize_settings(src.read_text(encoding="utf-8"))
            got = actual[rel].read_text(encoding="utf-8")
            if want != got:
                drift.append(rel)
            continue
        if _sha(src) != _sha(actual[rel]):
            drift.append(rel)
    assert not drift, f"模板内容已过期（{len(drift)} 个文件，例如 {drift[:5]}）；请重新 build"
