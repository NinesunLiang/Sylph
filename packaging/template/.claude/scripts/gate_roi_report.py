#!/usr/bin/env python3
"""gate_roi_report.py — 门禁 ROI 仪表（审计 A3 落地：gate-pass-count 1.3MB 零消费 → 月度僵尸清单）

数据源：.omc/state/gate-pass-count.jsonl（行格式 {"date","gate","mode","count"}）
对照源：.claude/hooks/pretool-gate.py 注册表（_GATE_CORE / _GATE_L2_EXTRA）

产出（stdout）：
  1. 使用排行：各 gate 事件总数 + 最后触发日期
  2. 僵尸清单：已注册但近 N 天 0 触发的 gate（少即是多 → 处置：接入主链路或删除）
  3. 陈旧数据：数据里出现但已不在注册表的 gate 名（门已删、遥测还在记）

退出码：0=报告生成 | 1=无数据文件 | 2=参数/路径错误
用法：
  python3 .claude/scripts/gate_roi_report.py --root <repo> [--window 30] [--json]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

GATE_NAME_RE = re.compile(r'\("([a-z0-9][a-z0-9-]*)",\s*_check_')


def load_registry(hook_path: Path) -> list[str]:
    """从 pretool-gate.py 提取注册 gate 名（core + l2 附加）。"""
    if not hook_path.exists():
        return []
    return GATE_NAME_RE.findall(hook_path.read_text(encoding="utf-8"))


def load_events(jsonl_path: Path) -> list[dict]:
    events = []
    for line in jsonl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "gate" in d:
            events.append(d)
    return events


def summarize(events: list[dict], registered: list[str], window_days: int) -> dict:
    by_gate: dict[str, dict] = collections.defaultdict(
        lambda: {"total": 0, "last": None}
    )
    for e in events:
        g = str(e["gate"])
        n = int(e.get("count", 1))
        by_gate[g]["total"] += n
        d = str(e.get("date", ""))
        if d and (by_gate[g]["last"] is None or d > by_gate[g]["last"]):
            by_gate[g]["last"] = d

    latest = max((e.get("date", "") for e in events), default="")
    ref = datetime.strptime(latest, "%Y-%m-%d").date() if latest else date.today()
    cutoff = ref - timedelta(days=window_days)

    def active(g: str) -> bool:
        last = by_gate[g]["last"]
        return bool(last) and datetime.strptime(last, "%Y-%m-%d").date() >= cutoff

    ranking = [
        {"gate": g, "total": v["total"], "last_active": v["last"]}
        for g, v in sorted(by_gate.items(), key=lambda kv: -kv[1]["total"])
    ]
    zombies = [g for g in registered if g not in by_gate or not active(g)]
    stale = sorted(g for g in by_gate if registered and g not in registered)

    return {
        "as_of": ref.isoformat(),
        "window_days": window_days,
        "events": len(events),
        "registered": len(registered),
        "ranking": ranking,
        "zombies": zombies,
        "stale": stale,
    }


def render(report: dict) -> str:
    lines = [
        f"# 门禁 ROI 报告（截至 {report['as_of']}，窗口 {report['window_days']} 天）",
        f"事件 {report['events']} | 注册门禁 {report['registered']} 道 | 数据 gate 种数 {len(report['ranking'])}",
        "",
        "## 使用排行",
    ]
    for r in report["ranking"]:
        lines.append(f"  {r['gate']:<28} {r['total']:>8} 次  最后触发 {r['last_active']}")
    lines += ["", f"## 僵尸清单（近 {report['window_days']} 天 0 触发，少即是多 → 接入或删除）"]
    for z in report["zombies"]:
        lines.append(f"  ⚠ {z}")
    if report["stale"]:
        lines += ["", "## 陈旧遥测（数据中有、注册表已无）"]
        lines += [f"  ⚠ {s}" for s in report["stale"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--window", type=int, default=30, help="僵尸判定窗口（天）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非文本")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    jsonl = root / ".omc" / "state" / "gate-pass-count.jsonl"
    if not jsonl.exists():
        print(f"❌ 数据文件不存在: {jsonl}", file=sys.stderr)
        return 1
    hook = root / ".claude" / "hooks" / "pretool-gate.py"
    registered = load_registry(hook)
    events = load_events(jsonl)
    report = summarize(events, registered, args.window)
    if not events:
        print(f"❌ 数据为空: {jsonl}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
