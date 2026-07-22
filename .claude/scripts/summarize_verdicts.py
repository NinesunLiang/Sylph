#!/usr/bin/env python3
"""
summarize_verdicts.py -- 汇总 Oracle 裁决文件的 C5 工具生命周期指标。

遍历 .omc/state/oracle-verdicts/ 下所有 oracle-*.json 文件，
提取并输出汇总表：每个裁决的 verdict / score / timestamp。

Usage:
    python3 .claude/scripts/summarize_verdicts.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

VERDICTS_DIR = Path(".omc/state/oracle-verdicts")


def _safe_load(path: Path) -> dict[str, Any] | None:
    """安全加载 JSON 文件，解析失败返回 None。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  WARN: skipped {path.name} -- {exc}", file=sys.stderr)
        return None


def _extract_verdict(data: dict[str, Any]) -> str:
    """从 verdict 对象中提取裁决值。

    新版格式: {"verdict": {"verdict": "ACCEPT", ...}}
    旧版格式: {"verdict": {"mode": "local_prompt", "status": "pending"}}
    缺失格式: 返回 "N/A"
    """
    v = data.get("verdict", {})
    if not isinstance(v, dict):
        return "N/A"
    result = v.get("verdict", "")
    if result:
        return result
    return v.get("status", "N/A")


def _extract_score(data: dict[str, Any]) -> str:
    """从 verdict 对象中提取评分。"""
    v = data.get("verdict", {})
    if not isinstance(v, dict):
        return "N/A"
    raw = v.get("score")
    if raw is not None:
        return f"{raw:.1f}"
    return "N/A"


def _extract_mode(data: dict[str, Any]) -> str:
    """从 verdict 对象中提取裁决模式。"""
    v = data.get("verdict", {})
    if not isinstance(v, dict):
        return "N/A"
    return v.get("mode", "N/A")


def _summarize_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    """生成汇总统计。"""
    verdict_counts: Counter[str] = Counter()
    numeric_scores: list[float] = []

    for row in rows:
        v = row["verdict"]
        if v not in ("N/A", "pending", "bypassed"):
            verdict_counts[v] += 1
        s = row["score"]
        if s != "N/A":
            try:
                numeric_scores.append(float(s))
            except ValueError:
                pass

    avg = round(sum(numeric_scores) / len(numeric_scores), 2) if numeric_scores else None
    return {
        "total_files": len(rows),
        "verdict_counts": dict(verdict_counts),
        "score_avg": avg,
        "score_min": min(numeric_scores) if numeric_scores else None,
        "score_max": max(numeric_scores) if numeric_scores else None,
    }


def main() -> int:
    if not VERDICTS_DIR.is_dir():
        print(f"ERROR: verdicts directory not found: {VERDICTS_DIR}", file=sys.stderr)
        return 1

    files = sorted(VERDICTS_DIR.glob("oracle-*.json"))
    if not files:
        print("No oracle verdict files found.")
        return 0

    rows: list[dict[str, str]] = []

    for f in files:
        data = _safe_load(f)
        if data is None:
            continue

        ts = data.get("timestamp", "N/A")
        target = data.get("target", "N/A")
        verdict_str = _extract_verdict(data)
        score_str = _extract_score(data)
        mode = _extract_mode(data)

        rows.append({
            "filename": f.name,
            "timestamp": ts,
            "target": target,
            "verdict": verdict_str,
            "score": score_str,
            "mode": mode,
        })

    if not rows:
        print("No readable oracle verdict files.")
        return 0

    # Table output
    header = f"{'File':<30} {'Timestamp':<18} {'Verdict':<10} {'Score':<7} {'Mode':<18} {'Target'}"
    sep = "-" * len(header)
    print(sep)
    print("Oracle Verdicts Summary")
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print(f"{row['filename']:<30} {row['timestamp']:<18} {row['verdict']:<10} {row['score']:<7} {row['mode']:<18} {row['target']}")
    print(sep)

    # Summary statistics
    stats = _summarize_stats(rows)
    print()
    print(f"Total verdict files: {stats['total_files']}")
    print(f"Verdict distribution: {stats['verdict_counts']}")
    if stats["score_avg"] is not None:
        print(f"Score range: {stats['score_min']} -- {stats['score_max']}  (avg: {stats['score_avg']})")
    else:
        print("Score range: N/A")

    # JSON output
    print()
    print(json.dumps({"rows": rows, "summary": stats}, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
