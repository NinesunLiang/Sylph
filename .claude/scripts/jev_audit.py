#!/usr/bin/env python3
"""jev_audit.py — 自迭代基座审计层（盲评 + 诚实指标）。

设计依据（官方优先）：
  · jev-eval（TypeSafe 官方）：<50 条拒绝采纳、50–200 provisional、≥200 才可正式使用；
    阈值必须用带标签数据校准，并用 bootstrap 防止样本内过拟合。
  · LLM-as-Judge 共识（MLflow / arXiv 2026）：人类标注必须盲评；原始一致率会虚高，
    必须报告混淆矩阵、TPR/TNR、弃权与覆盖率、chance-corrected κ。

本模块只做三件事：
  1. sample  —— 分层、确定性、**盲评**队列（不暴露判官结论，防锚定偏差）
  2. metrics —— 每规则：混淆矩阵 / TPR / TNR / 一致率 / κ / bootstrap 95% CI / 覆盖率 / 校准等级
  3. status  —— 账本概览（待复核、已标注、各规则校准等级）

不做：改规则、自动采纳、写判官结论。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_fit as jf  # noqa: E402

LABELS = ("符合", "不符合", "不适用")
ABSTAIN_TOKENS = {"不能判定", "证据不足", "不确定", "", None}
DEFAULT_ACCEPT_AT = 0.85


# ── 归一 ───────────────────────────────────────────────────────────
def _label(value) -> str | None:
    v = str(value).strip() if value is not None else None
    if v in ABSTAIN_TOKENS:
        return None
    return v if v in LABELS else None


def normalize_row(row: dict) -> dict:
    """把两种账本形态（sweep 嵌套 jev / verify_loop 顶层字段）归一。"""
    jev = row.get("jev") if isinstance(row.get("jev"), dict) else {}
    judge_raw = jev.get("verdict") or row.get("verdict")
    human_raw = (row.get("human") or {}).get("verdict")
    conf = jev.get("confidence")
    if conf is None:
        conf = jev.get("noul")
    if conf is None:
        conf = row.get("jev_confidence")
    if conf is None:
        conf = row.get("jev_noul")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return {
        "review_id": row.get("review_id", ""),
        "rule_id": row.get("rule_id", ""),
        "purpose": row.get("purpose", ""),
        "judge": _label(judge_raw),
        "human": _label(human_raw),
        "human_raw": human_raw,
        "conf": conf,
    }


# ── 盲评抽样 ───────────────────────────────────────────────────────
def _order_key(seed: int, review_id: str) -> str:
    """跨进程/跨版本稳定的排序键（不用 random 的内部实现）。"""
    return hashlib.sha256(f"{seed}:{review_id}".encode()).hexdigest()


def blind_sample(rows: list[dict], per_rule: int = 10, seed: int = 0) -> list[dict]:
    """按规则分层抽样，返回**盲评**条目（不含判官结论）。"""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        norm = normalize_row(row)
        if norm["human"] is not None or norm.get("human_raw") == "不确定":
            continue  # 已有人类结论的不再抽样
        if not norm["review_id"]:
            continue
        groups.setdefault(norm["rule_id"], []).append(norm)

    out: list[dict] = []
    for rule_id in sorted(groups):
        items = sorted(groups[rule_id], key=lambda r: _order_key(seed, r["review_id"]))
        for norm in items[: max(0, per_rule)]:
            out.append({
                "review_id": norm["review_id"],
                "rule_id": rule_id,
                "purpose": (norm["purpose"] or "")[:160],
            })
    return out


# ── 指标 ───────────────────────────────────────────────────────────
def _agreement(pairs: list[tuple[str, str]]) -> float | None:
    return round(sum(1 for a, b in pairs if a == b) / len(pairs), 3) if pairs else None


def _bootstrap_ci(pairs: list[tuple[str, str]], seed: int, resamples: int,
                  statistic) -> list[float] | None:
    if len(pairs) < 2:
        return None
    rng = random.Random(seed)
    vals: list[float] = []
    n = len(pairs)
    for _ in range(resamples):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        v = statistic(sample)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(0.975 * (len(vals) - 1))]
    return [round(lo, 3), round(hi, 3)]


def metrics(rows: list[dict], accept_at: dict[str, float] | None = None,
            seed: int = 0, resamples: int = 1000) -> dict:
    """按规则计算诚实指标。"""
    accept_at = accept_at or {}
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        norm = normalize_row(row)
        if norm["review_id"]:
            grouped.setdefault(norm["rule_id"], []).append(norm)

    out: dict[str, dict] = {}
    for rule_id, items in sorted(grouped.items()):
        labeled = [r for r in items if r["human"] is not None]
        abstain = sum(1 for r in items if r.get("human_raw") == "不确定")
        if not labeled:
            continue

        confusion = {h: {j: 0 for j in LABELS} | {"弃权": 0} for h in LABELS}
        pairs: list[tuple[str, str]] = []
        judge_abstain = 0
        for r in labeled:
            if r["judge"] is None:
                confusion[r["human"]]["弃权"] += 1
                judge_abstain += 1
                continue
            confusion[r["human"]][r["judge"]] += 1
            pairs.append((r["human"], r["judge"]))

        n = len(labeled)
        agree = sum(1 for a, b in pairs if a == b)
        pos_total = sum(confusion["不符合"].values())
        neg_total = sum(confusion["符合"].values())
        tpr = round(confusion["不符合"]["不符合"] / pos_total, 3) if pos_total else None
        tnr = round(confusion["符合"]["符合"] / neg_total, 3) if neg_total else None

        threshold = float(accept_at.get(rule_id, DEFAULT_ACCEPT_AT))
        covered = [r for r in labeled if r["conf"] is not None and r["conf"] >= threshold]
        coverage = round(len(covered) / n, 3) if n else None

        out[rule_id] = {
            "n": n,
            "abstain": abstain,
            "judge_abstain": judge_abstain,
            "confusion": confusion,
            "tpr": tpr,
            "tnr": tnr,
            "agreement": round(agree / n, 3) if n else None,
            "kappa": jf.cohen_kappa(pairs),
            "agreement_ci": _bootstrap_ci(pairs, seed, resamples, _agreement),
            "kappa_ci": _bootstrap_ci(pairs, seed + 1, resamples, jf.cohen_kappa),
            "coverage": coverage,
            "tier": jf.sample_tier(n),
        }
    return out


# ── CLI ────────────────────────────────────────────────────────────
def _load_ledger(path: str | None) -> list[dict]:
    return jf.load_reviews(Path(path) if path else jf.LEDGER)


def _print_metrics(rep: dict) -> None:
    print(f"{'规则':<26}{'n':>5}{'弃权':>5}{'TPR':>7}{'TNR':>7}{'一致':>7}{'κ':>7}{'覆盖':>7}  等级")
    for rid, d in sorted(rep.items(),
                         key=lambda kv: (kv[1]["agreement"] is None, kv[1]["agreement"])):
        def fmt(v, pct=False):
            if v is None:
                return "—"
            return f"{v:.0%}" if pct else f"{v:.2f}"
        print(f"{rid:<26}{d['n']:>5}{d['abstain']:>5}"
              f"{fmt(d['tpr'], True):>7}{fmt(d['tnr'], True):>7}"
              f"{fmt(d['agreement'], True):>7}{fmt(d['kappa']):>7}"
              f"{fmt(d['coverage'], True):>7}  {d['tier']}")
    print("\n等级：refuse(<50) / provisional(50–200) / ok(≥200)；"
          "只有 ok 才允许判官硬阻断。")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="自迭代基座审计：盲评抽样 + 诚实指标")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sample", help="按规则分层抽取盲评队列")
    p.add_argument("--per-rule", type=int, default=10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ledger", default=None)
    p.add_argument("--out", default=None, help="输出 JSONL 路径（默认只打印）")

    p = sub.add_parser("metrics", help="按规则输出诚实指标")
    p.add_argument("--ledger", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--seed", type=int, default=0)

    p = sub.add_parser("status", help="账本概览")
    p.add_argument("--ledger", default=None)
    p.add_argument("--seed", type=int, default=0)

    args = ap.parse_args(argv)
    rows = _load_ledger(getattr(args, "ledger", None))

    if args.cmd == "sample":
        queue = blind_sample(rows, per_rule=args.per_rule, seed=args.seed)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            with Path(args.out).open("w", encoding="utf-8") as fh:
                for item in queue:
                    fh.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"盲评队列 {len(queue)} 条 → {args.out}")
        else:
            print(f"# 盲评队列 {len(queue)} 条（已隐藏判官结论）\n")
            for item in queue:
                print(f"{item['review_id']}  [{item['rule_id']}]  {item['purpose'][:70]}")
        print("\n判完后用：python3 .claude/scripts/jev_fit.py judge "
              "--review-id <id> --verdict <值>")
        return 0

    if args.cmd == "metrics":
        rep = metrics(rows, seed=args.seed)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            if not rep:
                print("还没有任何人工标注 —— 先跑 sample 抽盲评队列。")
                return 0
            _print_metrics(rep)
        return 0

    labeled = sum(1 for r in rows if (r.get("human") or {}).get("verdict"))
    print(f"账本: {jf.LEDGER}")
    print(f"总记录: {len(rows)} | 已标注: {labeled} | 待复核: {len(rows) - labeled}")
    rep = metrics(rows, seed=args.seed)
    if rep:
        tiers: dict[str, int] = {}
        for d in rep.values():
            tiers[d["tier"]] = tiers.get(d["tier"], 0) + 1
        print("校准等级分布:", tiers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
