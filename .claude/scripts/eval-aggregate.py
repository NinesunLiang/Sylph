#!/usr/bin/env python3
"""
eval-aggregate.py — 评测聚合器

从 scorecard.md + meta-oracle verdicts 聚合生成 eval-report.md。
对应 evaluation-framework.md 四层架构的层间合成器。

用法:
  python3 .claude/scripts/eval-aggregate.py \\
    --scorecard .claude/references/scorecard.md \\
    --meta-verdict .omc/state/oracle/ \\
    --output .omc/state/eval-report.md
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_scorecard(path: Path) -> dict:
    """从 scorecard.md 提取 C1-C9/E1-E8/治理/UX 的最近评分."""
    text = path.read_text(encoding="utf-8")
    result: dict[str, float] = {}
    # 摘 C 维加权
    m = re.search(r'C1-C9.*加权.*?([\d.]+)', text)
    if m:
        result["c_weighted"] = float(m.group(1))
    m = re.search(r'E1-E8.*加权.*?([\d.]+)', text)
    if m:
        result["e_weighted"] = float(m.group(1))
    m = re.search(r'24 项总加权.*?([\d.]+)', text)
    if m:
        result["total_weighted"] = float(m.group(1))
    return result


def parse_oracle_verdicts(dir_path: Path) -> list[dict]:
    """收集 oracle verdict 目录中的最近评审记录."""
    verdicts = []
    if not dir_path.is_dir():
        return verdicts
    for sub in sorted(dir_path.iterdir()):
        if sub.is_dir():
            v_file = sub / "verdict.json"
            if v_file.exists():
                try:
                    data = json.loads(v_file.read_text(encoding="utf-8"))
                    verdicts.append({"dir": sub.name, **data})
                except (json.JSONDecodeError, Exception):
                    pass
    return verdicts


def aggregate(scorecard_path: Path, oracle_dir: Path, output_path: Path) -> int:
    scores = parse_scorecard(scorecard_path) if scorecard_path.exists() else {}
    verdicts = parse_oracle_verdicts(oracle_dir) if oracle_dir.exists() else []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# Eval Report — {now}",
        "",
        "## 评分解读",
        "",
        f"| 维度 | 分数 |",
        f"|------|:----:|",
        f"| C1-C9 加权 | **{scores.get('c_weighted', '?')}** |",
        f"| E1-E8 加权 | **{scores.get('e_weighted', '?')}** |",
        f"| 24项总加权 | **{scores.get('total_weighted', '?')}** |",
        "",
        "## 分歧分析",
        "",
        f"Oracle 评审记录: {len(verdicts)} 条",
    ]
    for v in verdicts:
        vd = v.get("verdict", "?")
        sc = v.get("score", 0)
        lines.append(f"- {v['dir']}: {vd} (score={sc})")

    lines.extend([
        "",
        "## 下轮建议",
        "",
        "详见 .claude/references/design-docs/r8-convergence-plan.md",
        "",
        "---",
        f"> 由 eval-aggregate.py 于 {now} 生成",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Eval report: {output_path}")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    sc_path = root / ".claude" / "references" / "scorecard.md"
    oracle_path = root / ".omc" / "state" / "oracle"
    out_path = root / ".omc" / "state" / "eval-report.md"

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--scorecard" and i + 1 < len(sys.argv):
            sc_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--meta-verdict" and i + 1 < len(sys.argv):
            oracle_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            out_path = Path(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    sys.exit(aggregate(sc_path, oracle_path, out_path))
