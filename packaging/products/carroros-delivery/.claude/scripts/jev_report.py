#!/usr/bin/env python3
"""jev_report.py — 违规捕获入口（人看到违规就记一条）。

设计（2026-10-19 用户提出）：
  · 不要求批量盲评；只在你真的看到违规时记一笔
  · 每条违规 = 一条高质量标签（human verdict=不符合）
  · 违规累积到阈值后，才允许进入「规则增强」提案流程

用法：
  python3 .claude/scripts/jev_report.py --rule soul.1.simple \
      --note "新增脚本但没说明为什么不能用现有实现" \
      --evidence "diff --git ..." --reviewer lucas.liang
  python3 .claude/scripts/jev_report.py --rule soul.7.gain --commit <sha> \
      --note "新增无调用方的脚本" --reviewer lucas.liang
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))

import jev_fit as jf  # noqa: E402
import jev_sweep as js  # noqa: E402

VIOLATIONS = ROOT / ".omc" / "state" / "jev" / "violations.jsonl"
STRENGTHEN_THRESHOLD = 3


def _violation_count(rule_id: str) -> int:
    try:
        rows = jf.load_reviews(jf.LEDGER)
    except Exception:
        return 0
    return sum(1 for r in rows
               if r.get("rule_id") == rule_id
               and (r.get("human") or {}).get("verdict") == "不符合")


def main() -> int:
    ap = argparse.ArgumentParser(description="记录一次规则违规")
    ap.add_argument("--rule", required=True, help="规则 id，如 soul.1.simple")
    ap.add_argument("--note", required=True, help="你看到的违规点")
    ap.add_argument("--reviewer", default="lucas.liang")
    ap.add_argument("--evidence", default="", help="证据文本或文件路径")
    ap.add_argument("--commit", default=None, help="从 git commit 收集改动作为证据")
    ap.add_argument("--path", default="", help="证据文件路径")
    args = ap.parse_args()

    if args.commit:
        purpose, change, paths = js.collect_commit_change(args.commit, None)
        evidence = change
        changed_paths = paths
    else:
        evidence = args.evidence
        if args.path:
            try:
                evidence = Path(args.path).read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                print(f"ERROR: 读取证据失败: {exc}", file=sys.stderr)
                return 2
        changed_paths = []

    if not str(evidence).strip():
        print("ERROR: 需要 --evidence / --path / --commit 之一作为证据", file=sys.stderr)
        return 2

    fp = hashlib.sha256(f"{args.rule}:{evidence}".encode()).hexdigest()[:12]
    review_id = f"v-{fp}-{args.rule}"
    if any(r.get("review_id") == review_id for r in jf.load_reviews(jf.LEDGER)):
        print(f"已存在相同违规记录: {review_id}（未重复写入）")
        return 0
    now = datetime.now(timezone.utc).isoformat()

    rec = {
        "review_id": review_id,
        "recorded_at": now,
        "rule_id": args.rule,
        "source": "violation_report",
        "purpose": args.note[:160],
        "change": evidence[:20000],
        "changed_paths": changed_paths,
        "jev": None,
        "human": {
            "verdict": "不符合",
            "note": args.note,
            "reviewer": args.reviewer,
            "label_source": "contemporaneous_human",
            "reported_at": now,
        },
    }
    jf.append_review(rec)
    VIOLATIONS.parent.mkdir(parents=True, exist_ok=True)
    with VIOLATIONS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"review_id": review_id, "rule_id": args.rule,
                             "note": args.note, "reported_at": now},
                            ensure_ascii=False) + "\n")

    n = _violation_count(args.rule)
    print(f"已记录违规: {args.rule} (review_id={review_id})")
    print(f"该规则累计违规: {n}")
    if n >= STRENGTHEN_THRESHOLD:
        print(f"→ 已达 {STRENGTHEN_THRESHOLD} 条，可进入规则增强提案（需回放 + 人裁决）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
