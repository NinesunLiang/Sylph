"""test_md_ref_lint.py — md 引用实体存在性 lint（PLAN_SIMPLIFY B3 / Phase1）

抓 .md 里指向不存在本地文件/目录的悬空链接（philosophy 悬空引用类）。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omc_lint import lint_md_references


def _mk(tmp: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def test_dangling_relative_link_detected():
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "README.md": "见 [A](docs/a.md) 与 [坏](docs/missing.md)。",
            "docs/a.md": "# A",
        })
        dangling, total = lint_md_references(root)
        assert total == 2, f"应统计 2 个本地链接: {total}"
        assert any(f == "README.md" and t == "docs/missing.md" for f, t in dangling), (
            f"应抓到悬空 docs/missing.md: {dangling}")


def test_url_and_anchor_links_ignored():
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "README.md": "看 [web](https://x.com) [节](#sec) [mail](mailto:a@b.c)。",
        })
        dangling, total = lint_md_references(root)
        assert total == 0 and dangling == [], f"http/#/mailto 不应算本地引用: {dangling}"


def test_existing_root_and_sibling_resolve():
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "guide.md": "回 [根](CLAUDE.md)，看 [深](docs/sub/note.md)。",
            "CLAUDE.md": "@AGENTS.md",
            "docs/sub/note.md": "# n",
        })
        dangling, total = lint_md_references(root)
        assert dangling == [], f"应全部解析: {dangling}"


def test_archive_and_dotdirs_excluded():
    """悬空链接若藏在 .omc/.omo/archive 等运行时区，不报（非活跃文档）。"""
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "README.md": "正常 [a](docs/a.md)。",
            "docs/a.md": "x",
            ".omc/archive/old.md": "[坏](ghost.md)",
            "Benchmarking/index0.md": "[悬](no_such.md)",
        })
        dangling, total = lint_md_references(root)
        # Benchmarking 属活跃文档，应报；.omc 属运行时，跳过
        assert any(f.startswith("Benchmarking") for f, _ in dangling), dangling
        assert not any(f.startswith(".omc") for f, _ in dangling), dangling
