#!/usr/bin/env python3
"""gate_zombie_report.py — 门禁僵尸仪表（PLAN_SIMPLIFY C5/M3, Phase 1）

僵尸门禁 = 历史曾真实触发（count>0）、但最近 window_days 内 0 次触发的门禁
→ 简化候选。M3 僵尸率 = 僵尸数 / 历史触发门禁数（目标 ≤10%）。

数据源：.omc/state/gate-pass-count.jsonl（{date, gate, mode, count}）。
用法：
    python3 .claude/scripts/gate_zombie_report.py [gate-pass-count.jsonl] [--window N]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def iter_gate_records(log_path):
    """遍历 gate-pass 记录（兼容按月分片：传目录则读其下 *.jsonl，传文件则读单文件）。"""
    path = Path(log_path)
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path] if path.exists() else []
    for f in files:
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                yield line


def gate_zombie_report(log_path, window_days: int = 14, asof: str | None = None) -> dict:
    """解析 gate-pass 日志（文件或分片目录）→ {gates, zombies, rate}。

    只统计 count>0 的行作为"真实触发"。asof 缺省取日志最大日期（测试确定性）。
    """
    gates: dict[str, list[str]] = {}  # gate -> [触发日期]
    for line in iter_gate_records(log_path):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            count = rec.get("count", 1)
            if not isinstance(count, (int, float)) or count <= 0:
                continue
            g = str(rec.get("gate", "")).strip()
            if not g:
                continue
            d = str(rec.get("date", ""))[:10]
            gates.setdefault(g, []).append(d)

    if asof is None:
        all_dates = sorted(d for ds in gates.values() for d in ds)
        asof = all_dates[-1] if all_dates else date.today().isoformat()
    cutoff = (datetime.fromisoformat(asof) - timedelta(days=window_days)).date().isoformat()

    zombies = []
    for g, dates in gates.items():
        if not any(d >= cutoff for d in dates):
            zombies.append({"gate": g, "last_seen": max(dates), "recent_count": 0})
    zombies.sort(key=lambda z: z["last_seen"])
    total = len(gates)
    rate = round(len(zombies) / total, 4) if total else 0.0
    # 陈旧度：asof 缺省取「数据里最大的日期」，数据断了也会显得新鲜。
    # 用真实今天对比，陈旧时报告必须自我标注，否则会拿死数据发假提案。
    try:
        stale_days = max((date.today() - datetime.fromisoformat(asof).date()).days, 0)
    except ValueError:
        stale_days = 0
    return {"gates": sorted(gates), "zombies": zombies, "rate": rate, "asof": asof,
            "stale_days": stale_days}


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="门禁僵尸仪表")
    ap.add_argument("log", nargs="?", default=".omc/state/gate-pass-count.jsonl")
    ap.add_argument("--window", type=int, default=14, help="近 N 天窗口")
    args = ap.parse_args(argv)
    rep = gate_zombie_report(args.log, window_days=args.window)
    print(f"asof={rep['asof']} | 历史触发门禁 {len(rep['gates'])} | "
          f"僵尸 {len(rep['zombies'])} | M3 僵尸率 {rep['rate']:.1%} (目标 ≤10%)")
    if rep.get("stale_days", 0) > args.window:
        print(f"  ⚠ 数据陈旧：最新遥测 {rep['asof']}，距今 {rep['stale_days']} 天"
              f"（> {args.window} 天窗口）——僵尸率不可信，勿据此发提案")
        return 2
    for z in rep["zombies"]:
        print(f"  ⚠ 僵尸候选: {z['gate']} (最后触发 {z['last_seen']})")
    return 1 if rep["zombies"] else 0


if __name__ == "__main__":
    sys.exit(_main())
