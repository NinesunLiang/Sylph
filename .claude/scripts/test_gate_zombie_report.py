"""test_gate_zombie_report.py — 门禁僵尸仪表（PLAN_SIMPLIFY C5/M3, Phase1）

僵尸门禁 = 历史出现过、但最近窗口内 0 触发 → 简化候选（防"只加不减"）。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from gate_zombie_report import gate_zombie_report


def _mk(log: Path, rows: list[dict]) -> Path:
    log.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return log


def test_zombie_gates_detected_and_rate():
    with tempfile.TemporaryDirectory() as td:
        rows = [
            # 活跃门禁：近 14 天仍触发
            {"date": "2026-09-08", "gate": "secret-scan", "mode": "l2", "count": 3},
            {"date": "2026-09-01", "gate": "secret-scan", "mode": "l2", "count": 1},
            # 僵尸候选1：最后触发在 30 天前（窗口外）
            {"date": "2026-08-01", "gate": "doc-quality", "mode": "l2", "count": 2},
            # 窗口边缘：14 天整内仍算活跃
            {"date": "2026-08-26", "gate": "stall", "mode": "l2", "count": 1},
            # count=0 行不构成历史基线（不会写入真实 pass 日志），忽略
            {"date": "2026-08-20", "gate": "wide-glob", "mode": "l2", "count": 0},
        ]
        log = _mk(Path(td) / "gate-pass-count.jsonl", rows)
        rep = gate_zombie_report(str(log), window_days=14, asof="2026-09-08")
        zs = {z["gate"] for z in rep["zombies"]}
        assert zs == {"doc-quality"}, f"应仅判 doc-quality 僵尸: {zs}"
        assert "secret-scan" not in zs and "stall" not in zs and "wide-glob" not in zs, zs
        # 历史门禁（count>0）= secret-scan / doc-quality / stall = 3，僵尸 1 → 率 1/3
        assert rep["rate"] == round(1 / 3, 4), rep["rate"]


def test_empty_and_missing_log_no_crash():
    with tempfile.TemporaryDirectory() as td:
        rep = gate_zombie_report(str(Path(td) / "none.jsonl"), window_days=14)
        assert rep["zombies"] == [] and rep["rate"] == 0.0, rep


def test_skip_zero_count_rows_for_history():
    """历史出现门禁以 count>0 为准；仅 0 触发记录不算历史活跃基线。"""
    with tempfile.TemporaryDirectory() as td:
        rows = [
            {"date": "2026-07-01", "gate": "never-fired", "mode": "l2", "count": 0},
            {"date": "2026-09-08", "gate": "secret-scan", "mode": "l2", "count": 1},
        ]
        log = _mk(Path(td) / "gate-pass-count.jsonl", rows)
        rep = gate_zombie_report(str(log), window_days=14, asof="2026-09-08")
        # never-fired 只有 0 记录 → 不在历史基线，也不判僵尸（无注册证据）
        assert all(z["gate"] != "never-fired" for z in rep["zombies"]), rep["zombies"]
        assert rep["rate"] == 0.0, rep["rate"]
