#!/usr/bin/env python3
"""jev_calibrate.py — 用历史 commit 标定 JEV-C 阈值。

阈值不能拍脑袋定。本工具做的是「先收集分布，再让人看着分布定值」：

  1. 取一批历史 commit，逐条跑规则轮询
  2. 收集每条规则的原始 `noul` 概率分布
  3. 给出分布的区间、缺口和建议阈值
  4. **最终取值仍由人裁决** —— 工具只给数据，不替人决定

用法：
    python3 .claude/scripts/jev_calibrate.py --limit 30
    python3 .claude/scripts/jev_calibrate.py --commits a1b2c3d d4e5f6a
    python3 .claude/scripts/jev_calibrate.py --limit 30 --out /tmp/jev_calib.json

环境变量：
    OPENROUTER_API_KEY   仅从环境读，绝不落盘
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_sweep as js  # noqa: E402


def commits_from_git(limit: int, skip_merges: bool = True) -> list[str]:
    import subprocess

    args = ["git", "log", "--pretty=format:%h", f"-n{limit}"]
    if skip_merges:
        args.insert(2, "--no-merges")
    out = subprocess.run(args, capture_output=True, text=True, check=False)
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def collect(commits: list[str], registry: dict, client) -> list[dict]:
    _, jev_rules = js.split_by_judge(registry["rules"])
    rows: list[dict] = []
    for i, sha in enumerate(commits, 1):
        purpose, change_text, changed_paths = js.collect_commit_change(sha)
        # 历史 commit 没有配套任务目录，交付物类规则会走「证据源不可用 → 证据不足」
        result = js.run_sweep(
            task_dir=None,
            out_dir=None,
            client=client,
            registry=registry,
            rules_to_judge=jev_rules,
            dry_run=True,
            purpose=purpose,
            change_text=change_text,
            changed_paths=changed_paths,
            delivery={"available": False, "reason": "历史 commit 无配套任务目录"},
        )
        probs = {}
        for row in result["results"]:
            if row.get("jev_noul") is not None:
                probs[row["rule_id"]] = row["jev_noul"]
        rows.append({
            "commit": sha,
            "purpose": purpose,
            "change_kind": js.classify_change(changed_paths),
            "n_paths": len(changed_paths),
            "probs": probs,
            "verdicts": {r["rule_id"]: r["verdict"] for r in result["results"]},
            "cost": result["summary"]["total_cost"],
        })
        print(f"[{i}/{len(commits)}] {sha} {probs}", flush=True)
    return rows


def _suggest(values: list[float]) -> dict:
    """从分布里找自然缺口，给出建议阈值。工具只建议，不决定。"""
    if not values:
        return {"n": 0}
    vals = sorted(values)
    lo, hi = vals[0], vals[-1]
    # 找最大相邻缺口
    best_gap, best_at = 0.0, None
    for a, b in zip(vals, vals[1:]):
        if b - a > best_gap:
            best_gap, best_at = b - a, (a + b) / 2
    return {
        "n": len(vals),
        "min": round(lo, 3),
        "median": round(statistics.median(vals), 3),
        "max": round(hi, 3),
        "largest_gap": round(best_gap, 3),
        "gap_at": round(best_at, 3) if best_at is not None else None,
        "suggest_reject_at": round(max(0.0, lo - 0.05), 2),
        "suggest_accept_at": round(min(1.0, hi + 0.05), 2),
        "suggest_split_at_gap": round(best_at, 2) if best_at is not None else None,
    }


def report(rows: list[dict], registry: dict) -> dict:
    by_rule: dict[str, list[float]] = {}
    for row in rows:
        for rid, p in row["probs"].items():
            by_rule.setdefault(rid, []).append(p)

    verdict_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        for rid, v in row["verdicts"].items():
            verdict_counts.setdefault(rid, {})
            verdict_counts[rid][v] = verdict_counts[rid].get(v, 0) + 1

    summary = {}
    for rule in registry["rules"]:
        rid = rule["rule_id"]
        if rule["judge_by"] == "script":
            continue
        dist = _suggest(by_rule.get(rid, []))
        dist["current_accept_at"] = rule.get("accept_at")
        dist["current_reject_at"] = rule.get("reject_at")
        dist["verdicts"] = verdict_counts.get(rid, {})
        dist["has_third_state"] = bool(rule.get("allow_not_applicable"))
        dist["requires"] = rule.get("requires")
        summary[rid] = dist
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="用历史 commit 标定 JEV-C 阈值")
    ap.add_argument("--limit", type=int, default=30, help="从 git log 取多少个 commit")
    ap.add_argument("--commits", nargs="*", default=None, help="指定 commit，覆盖 --limit")
    ap.add_argument("--rules", default=str(SCRIPTS_DIR / "jev_rules.yaml"))
    ap.add_argument("--out", default="/tmp/jev_calibration.json")
    args = ap.parse_args(argv)

    root = SCRIPTS_DIR.parents[1]
    registry = js.load_registry(Path(args.rules))
    problems = js.validate_registry(registry) + js.check_sources(registry, root)
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        return 2

    commits = args.commits or commits_from_git(args.limit)
    if not commits:
        print("ERROR: 没取到 commit", file=sys.stderr)
        return 2

    print(f"# 标定样本：{len(commits)} 个 commit\n")
    rows = collect(commits, registry, js.JevClient())
    summary = report(rows, registry)

    total_cost = sum(r["cost"] or 0 for r in rows)
    print("\n" + "=" * 78)
    print("规则分布与建议阈值")
    print("=" * 78)
    print(f"{'rule_id':<26}{'n':>3}{'min':>8}{'中位':>8}{'max':>8}{'缺口':>8}{'建议分割':>10}")
    print("-" * 78)
    for rid, d in summary.items():
        if not d.get("n"):
            print(f"{rid:<26}{'—':>3}  (无 noul 数据，可能用了三值 choice)")
            continue
        print(
            f"{rid:<26}{d['n']:>3}{d['min']:>8}{d['median']:>8}{d['max']:>8}"
            f"{d['largest_gap']:>8}{str(d['suggest_split_at_gap']):>10}"
        )

    print("\n--- 判定分布 ---")
    for rid, d in summary.items():
        if d.get("verdicts"):
            print(f"{rid:<26}{d['verdicts']}")

    print(f"\n总成本 ${total_cost:.6f}；样本 {len(rows)} 个 commit")
    Path(args.out).write_text(
        json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"原始数据：{args.out}")
    print("\n注意：本工具只给分布与建议，阈值最终由人裁决。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
