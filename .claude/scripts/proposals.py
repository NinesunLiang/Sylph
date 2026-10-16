#!/usr/bin/env python3
"""proposals.py — 进化提案 distiller/approver v1（PLAN_SIMPLIFY C2/C6, Phase 2）

把真实使用沉淀的原料（gate-pass 门禁触发遥测）蒸馏成"进化提案"，供人类采纳台裁决。
Schema（C2 v1）：
  {id: p-YYYY-MM-DD-NNN, source: distiller,
   kind: anti-pattern | gate-zombie | doc-drift | new-gate | delete-candidate,
   evidence: {count, refs[]}, suggestion, impact_estimate,
   status: pending|accepted|rejected|deferred, human_note, test_commit}

注（index48）：原 anti-pattern 一路的数据源 error-dna 已整体移除；
现存 kind 主要由 gate-zombie / delete-candidate 产生。

用法：
  python3 .claude/scripts/proposals.py distill [--threshold N] [--out DIR]
  python3 .claude/scripts/proposals.py list|accept <id>|reject <id> <note>  [proposals.jsonl]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

DEFAULT_OUT = ".omc/proposals"
# 遥测单一真源位置（2026-10-16 遥测卫生：按月分片目录）
GATE_PASS_TELEMETRY = ".omc/state/telemetry/gate-pass"
IMPACTS = ("高", "中", "低")


def make_proposals(zombies: list[dict], threshold: int = 3,
                   asof: date | None = None) -> list[dict]:
    """僵尸门禁(gate-zombie) → proposal 列表。

    index48：原 error-dna 聚类(anti-pattern) 一路已随 error-dna 机制整体移除
    —— 该数据源无生产者、12 天遥测 100% pending 且 81% 为测试噪声。
    现存唯一来源为 gate-pass-count.jsonl 的 0 触发门禁。
    """
    asof = asof or date.today()
    prefix = f"p-{asof.isoformat()}"
    props: list[dict] = []
    seq = 0

    def _next() -> str:
        nonlocal seq
        seq += 1
        return f"{prefix}-{seq:03d}"

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
    zombies = []
    if args.gate_pass:
        try:
            from gate_zombie_report import gate_zombie_report
            rep = gate_zombie_report(args.gate_pass, window_days=args.window)
            for z in rep["zombies"]:
                z["window_days"] = args.window
            zombies = rep["zombies"]
        except Exception as exc:
            print(f"⚠ gate 僵尸读取失败: {exc}")
    asof = date.today()
    props = make_proposals(zombies, threshold=args.threshold, asof=asof)
    # 脚本僵尸 → delete-candidate 提案（新增特性时清理死代码）
    try:
        from zombie_scan import find_zombies
        for rel in find_zombies(".", (".claude/scripts",))[:50]:
            seq = len(props) + 1
            props.append({
                "id": f"p-{asof.isoformat()}-{seq:03d}", "source": "distiller",
                "kind": "delete-candidate",
                "evidence": {"count": 1, "refs": [f"{rel} 无任何引用"]},
                "suggestion": f"删除/归档死代码 {rel}（未被代码/配置/文档引用）",
                "impact_estimate": "低", "status": "pending", "human_note": "", "test_commit": "",
            })
    except Exception as exc:
        print(f"⚠ 脚本僵尸检测跳过: {exc}")
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
    d.add_argument("--threshold", type=int, default=3)
    d.add_argument("--out", default=DEFAULT_OUT)
    d.add_argument("--gate-pass", default=GATE_PASS_TELEMETRY)
    d.add_argument("--window", type=int, default=14)
    l = sub.add_parser("list")
    l.add_argument("proposals", nargs="?", default=str(Path(DEFAULT_OUT) / "proposals.jsonl"))
    for st in ("accept", "reject"):
        s = sub.add_parser(st)
        s.add_argument("id")
        s.add_argument("note", nargs="?")
        s.add_argument("proposals", nargs="?", default=str(Path(DEFAULT_OUT) / "proposals.jsonl"))
    ar = sub.add_parser("anti-regrowth")
    ar.add_argument("--gate-pass", default=GATE_PASS_TELEMETRY)
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
