#!/usr/bin/env python3
"""error_dna_distill.py — 错误 DNA 蒸馏（审计 C1：学习飞轮断链的解药）

背景：error-dna 机制 2026-09-10（index48）随 hook 移除后，`.omc/state/error-dna.jsonl`
停止流入，83 条存量永远无人提炼 → 失败模式只进不出（C1）。
本脚本在任务 archive 时被调用：未蒸馏条目 ≥ 阈值（默认 20）→ 按 error_type
聚类提炼成「蒸馏草案」（.omc/state/error-dna-distill/draft-<日期>.md），供人类确认
后落 references/；已蒸馏条目用标记文件记账（不改源 jsonl，零破坏）。

用法: error_dna_distill.py [--root <repo>] [--threshold 20] [--dry-run]
退出: 0=完成（含「未达阈值无事可做」）| 2=数据文件缺失
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def load_entries(jsonl_path: Path) -> list[dict]:
    out = []
    for line in jsonl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def undistilled(entries: list[dict], marker_path: Path) -> list[dict]:
    done: set[str] = set()
    if marker_path.exists():
        for line in marker_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                done.add(line)
    return [e for e in entries if str(e.get("signature", "")) not in done or not e.get("signature")]


def classify(entries: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        groups[str(e.get("error_type") or f"exit{e.get('exit_code', '?')}")].append(e)
    out = {}
    for key, items in groups.items():
        retries = [int(i.get("retry_count", 0) or 0) for i in items]
        out[key] = {
            "count": len(items),
            "max_retry": max(retries) if retries else 0,
            "sample_cmd": next((i.get("cmd", "") for i in items if i.get("cmd")), ""),
            "sample_msg": next((i.get("message", "") for i in items if i.get("message")), "")[:200],
            "signatures": sorted({str(i.get("signature")) for i in items if i.get("signature")}),
        }
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["count"]))


def render_draft(groups: dict[str, dict], root: Path) -> str:
    lines = [
        "# 错误 DNA 蒸馏草案（待人类确认）",
        f"- 生成: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 覆盖条目: {sum(g['count'] for g in groups.values())}，模式: {len(groups)} 类",
        "",
        "> 确认方式：逐类裁决「采纳 → 落入 references/ 对应文档 / 驳回」；确认后由人工",
        "> 把已确认模式写入 `.omc/state/error-dna-distill/confirmed.jsonl`。",
        "",
    ]
    for key, g in groups.items():
        lines += [
            f"## {key}（{g['count']} 次，max retry {g['max_retry']}）",
            f"- 样例命令: `{g['sample_cmd'][:120]}`",
            f"- 样例信息: {g['sample_msg']}",
            f"- 建议处置: 待人类确认（候选：写入 anti-patterns.md / practices.md / 忽略）",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="仓库根目录")
    ap.add_argument("--threshold", type=int, default=20, help="触发蒸馏的未蒸馏条目阈值")
    ap.add_argument("--dry-run", action="store_true", help="只打印不记账")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    jsonl = root / ".omc" / "state" / "error-dna.jsonl"
    if not jsonl.exists():
        print(f"ℹ️ error-dna 不存在: {jsonl}（无事可做）", file=sys.stderr)
        return 2
    distill_dir = root / ".omc" / "state" / "error-dna-distill"
    marker = distill_dir / "last-distilled.jsonl"

    entries = load_entries(jsonl)
    todo = undistilled(entries, marker)
    if len(todo) < args.threshold:
        print(f"ℹ️ 未蒸馏 {len(todo)} 条 < 阈值 {args.threshold}，跳过蒸馏")
        return 0

    groups = classify(todo)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    draft = distill_dir / f"draft-{day}.md"
    if not args.dry_run:
        distill_dir.mkdir(parents=True, exist_ok=True)
        draft.write_text(render_draft(groups, root), encoding="utf-8")
        with marker.open("a", encoding="utf-8") as f:
            for g in groups.values():
                f.write("\n".join(g["signatures"]) + "\n")
    print(f"✅ 蒸馏完成：{len(todo)} 条 → {len(groups)} 类模式 → {draft}")
    print("   待人类确认（见草案「建议处置」行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
