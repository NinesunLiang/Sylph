"""test_decisions_local_ssot.py — 决策日志本机化（2026-10-24）

人类裁决：人类裁决日志迁到 `.claude/decisions/DECISIONS.md` 并进路由；
但历史文件不入库、不进安装包，每台机器下载后为空。
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_routing_points_to_new_location():
    for rel in ("AGENTS.md", ".claude/kernel.md", ".claude/index.md"):
        text = _read(rel)
        assert ".omc/decisions/DECISIONS.md" not in text, f"{rel} 仍指向旧路径"
        assert ".claude/decisions/" in text, f"{rel} 未指向新路径"


def test_history_is_local_only():
    assert (REPO / ".claude/decisions/README.md").exists(), "缺少空态说明"
    assert ".claude/decisions/DECISIONS.md" in _read(".gitignore"), "历史文件未 gitignore"


def test_installer_has_readme_but_no_history():
    tpl = REPO / "packaging/template/.claude/decisions"
    assert (tpl / "README.md").exists(), "安装包缺少空态说明"
    assert not (tpl / "DECISIONS.md").exists(), "安装包不得带裁决历史"


def test_memory_map_uses_new_path():
    src = _read(".claude/scripts/test_memory_governance_map.py")
    assert ".claude/decisions/DECISIONS.md" in src
    assert ".omc/decisions/DECISIONS.md" not in src
