#!/usr/bin/env python3
"""proposals.py — 进化提案 distiller/approver v1（PLAN_SIMPLIFY C2/C6, Phase 2）

把真实使用沉淀的原料（error-dna / gate-pass）蒸馏成"进化提案"，供人类采纳台裁决。
Schema（C2 v1）：
  {id: p-YYYY-MM-DD-NNN, source: distiller,
   kind: anti-pattern | gate-zombie | doc-drift | new-gate | delete-candidate,
   evidence: {count, refs[]}, suggestion, impact_estimate,
   status: pending|accepted|rejected|deferred, human_note, test_commit}

用法：
  python3 .claude/scripts/proposals.py distill [error-dna.jsonl] [--threshold N] [--out DIR]
  python3 .claude/scripts/proposals.py list|accept <id>|reject <id> <note>  [proposals.jsonl]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

DEFAULT_ERROR_DNA = ".omc/state/error-dna.jsonl"
DEFAULT_OUT = ".omc/proposals"
IMPACTS = ("高", "中", "低")


def load_error_dna(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def make_proposals(rows: list[dict], zombies: list[dict], threshold: int = 3,
                   asof: date | None = None) -> list[dict]:
    """error-dna 聚类(anti-pattern) + 僵尸(gate-zombie) → proposal 列表。"""
    asof = asof or date.today()
    prefix = f"p-{asof.isoformat()}"
    props: list[dict] = []
    seq = 0

    def _next() -> str:
        nonlocal seq
        seq += 1
        return f"{prefix}-{seq:03d}"

    # ── anti-pattern：error_type 聚类，pending 且达到阈值 ──
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        t = str(r.get("error_type") or "unknown").strip()
        by_type[t].append(r)
    for t, recs in sorted(by_type.items()):
        pending = [r for r in recs if str(r.get("resolution", "pending")) == "pending"]
        if len(pending) < threshold:
            continue
        max_retry = max((int(r.get("retry_count") or 0) for r in pending), default=0)
        sample = next((r.get("message") or r.get("cmd") or "") for r in pending)
        impact = "高" if max_retry >= 3 else "中"
        props.append({
            "id": _next(), "source": "distiller", "kind": "anti-pattern",
            "evidence": {"count": len(pending),
                         "refs": [f"error-dna.jsonl: error_type={t}"]},
            "suggestion": f"为 error_type「{t}」注册已知失败签名/疏导，压 retry（峰值 {max_retry}）",
            "impact_estimate": impact, "status": "pending", "human_note": "", "test_commit": "",
            "sample": (sample or "")[:120],
        })

    # ── gate-zombie：近窗口 0 触发 → 简化候选 ──
    for z in zombies:
        props.append({
            "id": _next(), "source": "distiller", "kind": "gate-zombie",
            "evidence": {"count": 0, "refs": [f"gate-pass-count.jsonl: {z['gate']} last={z['last_seen']}"]},
            "suggestion": f"门禁「{z['gate']}」近 {z.get('window_days', 14)} 天 0 触发 → 删除或降 warn 观察（少即是多）",
            "impact_estimate": "低", "status": "pending", "human_note": "", "test_commit": "",
        })
    return props


def write_proposals(props: list[dict], jsonl_out, md_out) -> tuple[Path, Path]:
    jsonl_out = Path(jsonl_out)
    md_out = Path(md_out)
    jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    # 幂等：已存在的 id 跳过（防重跑重复）
    seen: set[str] = set()
    if jsonl_out.exists():
        for line in jsonl_out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                seen.add(json.loads(line).get("id", ""))
            except json.JSONDecodeError:
                pass
    with jsonl_out.open("a", encoding="utf-8") as f:
        for p in props:
            if p["id"] in seen:
                continue
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with md_out.open("w", encoding="utf-8") as f:
        f.write("# 进化提案台\n\n")
        for p in props:
            f.write(f"- `{p['id']}` [{p['kind']}/{p['impact_estimate']}] {p['suggestion']}\n")
    return jsonl_out, md_out


def anti_regrowth_check(zombies: list[dict], round_note: str = "") -> dict:
    """C4/C6#4 防膨胀闸：归档前必须「删≥1 僵尸」或「证明无僵尸」。

    zombies 非空且无删除证据 → 不通过（需人类删/归档僵尸后重验）。
    """
    if not zombies:
        return {"ok": True, "zombies": [], "note": "证明无僵尸（近窗口 0 触发）"}
    deleted = [z for z in zombies if z.get("deleted_this_round")]
    if deleted:
        return {"ok": True, "zombies": deleted, "note": f"本轮删/归档僵尸 {len(deleted)} 个"}
    return {"ok": False, "zombies": zombies,
            "note": f"存在 {len(zombies)} 个僵尸候选且本轮无删除证据；需删/归档 ≥1 后重验",
            "round_note": round_note}


def _anti_regrowth(args) -> int:
    rep = {}
    try:
        from gate_zombie_report import gate_zombie_report
        rep = gate_zombie_report(args.gate_pass, window_days=args.window)
    except Exception as exc:
        print(f"⚠ 僵尸读取失败: {exc}")
        return 1
    r = anti_regrowth_check(rep["zombies"])
    print(f"[anti-regrowth] M3 僵尸率 {rep['rate']:.1%} | 判定: {'PASS' if r['ok'] else 'BLOCK'} — {r['note']}")
    for z in r["zombies"]:
        print(f"  ⚠ {z['gate']} (last {z['last_seen']})")
    return 0 if r["ok"] else 1


def _distill(args) -> int:
    rows = load_error_dna(args.error_dna)
    zombies = []
    if args.gate_pass:
        try:
            from gate_zombie_report import gate_zombie_report
            rep = gate_zombie_report(args.gate_pass, window_days=args.window)
            for z in rep["zombies"]:
                z["window_days"] = args.window
            zombies = rep["zombies"]
        except Exception as exc:
            print(f"⚠ gate 僵尸读取失败(不影响 anti-pattern): {exc}")
    asof = date.today()
    props = make_proposals(rows, zombies, threshold=args.threshold, asof=asof)
    jsonl, md = write_proposals(props, Path(args.out) / "proposals.jsonl", Path(args.out) / "proposals.md")
    print(f"[distill] {asof} | 提案 {len(props)} 条 | -> {jsonl}")
    for p in props:
        print(f"  {p['id']} [{p['kind']}/{p['impact_estimate']}] {p['suggestion']}")
    return 0


def _list_proposals(jsonl) -> int:
    p = Path(jsonl)
    if not p.exists():
        print("无提案文件"); return 1
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        note = f" | note={d['human_note']}" if d.get("human_note") else ""
        print(f"  {d['id']} [{d['kind']}/{d['impact_estimate']}/{d['status']}] {d['suggestion']}{note}")
    return 0


def _mutate(jsonl, pid: str, status: str, note: str) -> int:
    p = Path(jsonl)
    if not p.exists():
        print("无提案文件"); return 1
    if status == "rejected" and not note:
        print("❌ reject 必须写原因（human_note），供 distiller 学习不重复提案")
        return 1
    lines = p.read_text(encoding="utf-8").splitlines()
    hit = False
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("id") == pid:
            d["status"] = status
            if note:
                d["human_note"] = note
            lines[i] = json.dumps(d, ensure_ascii=False)
            hit = True
    if not hit:
        print(f"未找到 {pid}"); return 1
    p.write_text("\n".join(l for l in lines if l.strip()) + "\n", encoding="utf-8")
    print(f"{pid} -> {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="进化提案 distiller/approver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("distill")
    d.add_argument("error_dna", nargs="?", default=DEFAULT_ERROR_DNA)
    d.add_argument("--threshold", type=int, default=3)
    d.add_argument("--out", default=DEFAULT_OUT)
    d.add_argument("--gate-pass", default=".omc/state/gate-pass-count.jsonl")
    d.add_argument("--window", type=int, default=14)
    l = sub.add_parser("list")
    l.add_argument("proposals", nargs="?", default=str(Path(DEFAULT_OUT) / "proposals.jsonl"))
    for st in ("accept", "reject"):
        s = sub.add_parser(st)
        s.add_argument("id")
        s.add_argument("note", nargs="?")
        s.add_argument("proposals", nargs="?", default=str(Path(DEFAULT_OUT) / "proposals.jsonl"))
    ar = sub.add_parser("anti-regrowth")
    ar.add_argument("--gate-pass", default=".omc/state/gate-pass-count.jsonl")
    ar.add_argument("--window", type=int, default=14)
    args = ap.parse_args(argv)
    if args.cmd == "distill":
        return _distill(args)
    if args.cmd == "list":
        return _list_proposals(args.proposals)
    if args.cmd in ("accept", "reject"):
        status = {"accept": "accepted", "reject": "rejected"}[args.cmd]
        return _mutate(args.proposals, args.id, status, args.note or "")
    if args.cmd == "anti-regrowth":
        return _anti_regrowth(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
