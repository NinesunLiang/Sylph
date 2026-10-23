"""test_rsi_dead_fuel.py — 死燃料蒸馏器已摘除（2026-10-24）

error_dna 数据流 2026-09-10 已断（83 条存量，之后零写入）。
实时失败信号不足（真实判官记录 9 条，仅 1 条失败），不具备「换燃料」条件，
按僵尸机制退役：脚本移入 retired/，archive 不再挂钩。
"""
from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def test_dead_distiller_moved_to_retired():
    assert not (SCRIPTS / "error_dna_distill.py").exists(), "死蒸馏器不应留在活跃目录"
    archived = SCRIPTS.parent / "archive" / "zombies-20261024" / "error_dna_distill.py"
    assert archived.exists(), "退役文件应保留在 archive 以便追溯"


def test_archive_no_longer_calls_dead_distiller():
    src = (SCRIPTS / "carros_base.py").read_text(encoding="utf-8")
    assert "error_dna_distill" not in src, "archive 不应再调用已断流的蒸馏器"
