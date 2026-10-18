"""文档引用门禁的人本改进（TDD / RED 先行）。

背景：107 次硬停里 90 次来自 `doc-reference-before-delete`。
旧提示只说「某个文档还在引用」，模型不知道改哪一行 → 重试删除 → 硬停。
新契约：
  1. 提示给出 `文件:行号` 前 3 条
  2. 仅该门禁的重试阈值放宽到 3（其余门禁保持 2）
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

from pretool_gates import checks  # noqa: E402


def test_doc_reference_lines_returns_file_and_line(tmp_path):
    (tmp_path / "doc.md").write_text(
        "first line\nsee foo.py here\nlast line\n", encoding="utf-8"
    )
    hits = checks._doc_reference_lines(str(tmp_path), "foo.py", limit=3)
    assert hits, "应找到引用"
    assert "doc.md:2" in hits[0]
    assert "foo.py" in hits[0]


def test_doc_reference_lines_respects_limit(tmp_path):
    (tmp_path / "doc.md").write_text(
        "\n".join(f"foo.py line {i}" for i in range(10)), encoding="utf-8"
    )
    hits = checks._doc_reference_lines(str(tmp_path), "foo.py", limit=2)
    assert len(hits) == 2


def test_doc_reference_lines_boundary_match(tmp_path):
    """`stop-foo.py` 不算 `foo.py` 的引用（沿用 index48 的边界精确口径）。"""
    (tmp_path / "doc.md").write_text("uses stop-foo.py only\n", encoding="utf-8")
    assert checks._doc_reference_lines(str(tmp_path), "foo.py", limit=3) == []


def _load_pretool_gate():
    spec = importlib.util.spec_from_file_location(
        "pretool_gate_docref_under_test", HOOKS / "pretool-gate.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_docref_redirect_limit_is_relaxed_to_3():
    gate = _load_pretool_gate()
    assert gate._REDIRECT_LIMITS["doc-reference-before-delete"] == 3


def test_other_gates_keep_default_limit_2():
    gate = _load_pretool_gate()
    assert gate._REDIRECT_LIMITS.get("commit-soft-completion", 2) == 2
