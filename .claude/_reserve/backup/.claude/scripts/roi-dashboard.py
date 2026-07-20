#!/usr/bin/env python3
"""ROI Dashboard — reads roi-scores.json and renders a compact ROI panel.
Usage: python3 .claude/scripts/roi-dashboard.py [--top N] [--bottom N]
Called by: lx-status SKILL.md for ROI view
"""

import json, sys
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent.parent / ".omc" / "state"
SCORES_FILE = STATE_DIR / "roi-scores.json"

TOP_N = 10
BOTTOM_N = 5

if "--top" in sys.argv:
    idx = sys.argv.index("--top")
    TOP_N = int(sys.argv[idx + 1])
if "--bottom" in sys.argv:
    idx = sys.argv.index("--bottom")
    BOTTOM_N = int(sys.argv[idx + 1])


def main():
    if not SCORES_FILE.exists():
        print("ROI data not yet generated. Run: python3 .claude/scripts/roi-collector.py && python3 .claude/scripts/roi-score.py")
        return 1

    with open(SCORES_FILE) as f:
        data = json.load(f)

    results = data["results"]
    summary = data["summary"]

    # Header
    print()
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│           📊 Carror OS ROI 量化面板                          │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│  组件总数: {summary['total_components']:3d}  │  🔴高ROI: {summary['high_roi_count']:2d}  │  🟡中ROI: {summary['medium_roi_count']:2d}  │  🟢低ROI: {summary['low_roi_count']:2d}  │")
    print("├─────────────────────────────────────────────────────────────┤")

    # Top N
    print(f"│  ▲ Top {TOP_N} 高价值组件                                        │")
    print("│  {:4s} {:5s} {:6s} {:25s} {:6s} │".format("排名", "ROI", "类型", "名称", "拦截次数"))
    for i, r in enumerate(results[:TOP_N]):
        name = r['name'][:24]
        cat = r['category'][:5]
        ic = r.get('intercept_count', 0)
        score = r['roi_score']
        tier = "🔴" if score >= 60 else ("🟡" if score >= 30 else "🟢")
        print(f"│  {tier} {i+1:2d}  {score:5.1f}  {cat:6s} {name:25s} {ic:6d} │")

    print("├─────────────────────────────────────────────────────────────┤")

    # Bottom N
    print(f"│  ▼ Bottom {BOTTOM_N} 低价值组件（瘦身候选）                      │")
    print("│  {:4s} {:5s} {:6s} {:25s} {:>6s} │".format("排名", "ROI", "类型", "名称", "建议"))
    for i, r in enumerate(results[-BOTTOM_N:]):
        name = r['name'][:24]
        cat = r['category'][:5]
        score = r['roi_score']
        if score < 5:
            sug = "🔴移除"
        elif score < 15:
            sug = "🟡简化"
        else:
            sug = "评估"
        print(f"│  {i+1:2d}  {score:5.1f}  {cat:6s} {name:25s} {sug:>6s} │")

    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│  数据: flywheel.log + error-dna.jsonl + git history         │")
    print(f"│  详情: .omc/state/roi-recommendations.md                    │")
    print("└─────────────────────────────────────────────────────────────┘")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
