"""test_zombie_scan.py — 僵尸 .py 探测器（新增特性时清理死代码）

CarrorOS 僵尸机制：未被代码/配置/文档引用的 .py = 死代码候选 → 清理(归档)。
排除：test_*.py / conftest / __init__ / __pycache__（测试树由 pytest 全量收集=活着）。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import zombie_scan as Z


def _mk(tmp: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def test_imported_and_referenced_are_alive():
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "main.py": "import helper\nfrom lib.core import x\n",
            "README.md": "启动: python3 main.py\n",  # 入口有引用 → 活
            "helper.py": "def h(): pass\n",
            "lib/core.py": "x=1\n",
            "docs.md": "见 scripts/util.py\n",
            "util.py": "def u(): pass\n",
            "settings.json": '{"hooks": {"p": "runner.py"}}\n',
            "runner.py": "def r(): pass\n",
            "test_dead.py": "def test_x(): pass\n",
            "conftest.py": "x=1\n",
        })
        cands = Z.find_zombies(str(root))
        names = [Path(c).name for c in cands]
        assert names == [], f"全部被引用/测试，不应判僵尸: {names}"


def test_unreferenced_script_is_zombie():
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "main.py": "print('hi')\n",
            "README.md": "启动: python3 main.py\n",  # main 有引用
            "orphan.py": "def dead(): pass\n",
            "also_orphan.py": "print('x')\n",
        })
        cands = Z.find_zombies(str(root))
        names = sorted(Path(c).name for c in cands)
        assert names == ["also_orphan.py", "orphan.py"], names


def test_self_reference_does_not_count_as_alive():
    """孤立文件引用自己/被自己 import 不算被引用。"""
    with tempfile.TemporaryDirectory() as td:
        root = _mk(Path(td), {
            "solo.py": "import solo\nprint('self')\n",
        })
        cands = Z.find_zombies(str(root))
        assert [Path(c).name for c in cands] == ["solo.py"]
