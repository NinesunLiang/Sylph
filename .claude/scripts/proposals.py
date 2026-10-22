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
  python3 .claude/scripts/proposals.py distill [--threshold N] [--gov-threshold N] [--out DIR]
  python3 .claude/scripts/proposals.py list|accept <id>|reject <id> <note>  [proposals.jsonl]

  kind=gov-criterion（B 档，A+B 2026-10-22 开启）：判官账本人工复核备注 → 判据调优提案。
  证据必须带 refs（人工备注留痕）+ 规则原文锁定 + 影响估计；accept 只生成判官回放单，
  改登记表需 jev_fit replay 回放验证 + 人类登记版本；冻结域（AGENTS.md/kernel.md/hooks）
  永不自动落盘，必须人工签票（24h TTL）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

DEFAULT_OUT = ".omc/proposals"
# 遥测单一真源位置（2026-10-16 遥测卫生：按月分片目录）
GATE_PASS_TELEMETRY = ".omc/state/telemetry/gate-pass"
IMPACTS = ("高", "中", "低")

# ── B 档：治理域蒸馏（治理部分自迭代，A+B 2026-10-22 人类裁决开启）──
# 判官账本（判官判定 + 人工复核留痕的单一真源）；env 覆盖供测试隔离
JEV_LEDGER = os.environ.get("CARROROS_JEV_LEDGER") or \
    str(Path(__file__).resolve().parents[2] / ".omc" / "state" / "jev" / "reviews.jsonl")
# 治理判官登记表（kind=gov-criterion 提案的 target；冻结域文件本身仍不可自改）
# 展示用相对名 + 绝对真身（防 cwd 漂移）
GOV_RULES = ".claude/scripts/jev_rules.yaml"
GOV_RULES_ABS = str(Path(__file__).resolve().parent / "jev_rules.yaml")
# 冷却期：同一规则自上次治理提案裁决后 N 天内不再提案（控制打扰 ≤1-2 条/周）
GOV_COOLDOWN_DAYS = int(os.environ.get("CARROROS_GOV_COOLDOWN_DAYS", "14"))
# 治理域蒸馏最小证据数（人工备注/复核留痕，非 AI 自证）
GOV_THRESHOLD_DEFAULT = 2
# 判官回放单落盘目录（accept 后供 jev_fit replay 重放；env 覆盖供测试隔离）
GOV_REPLAY_DIR = os.environ.get("CARROROS_GOV_REPLAY_DIR") or \
    str(Path(__file__).resolve().parents[2] / ".omc" / "state" / "jev" / "replay")


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


def load_registry_text(rule_ids: list[str], registry_path: str | None = None) -> dict[str, dict]:
    """读判官登记表 → {rule_id: {text, source}}。读失败/缺规则返回 {}（不造无原文提案）。

    registry_path 为空时从脚本自身位置定位（GOV_RULES 相对仓库根，cwd 无关）。
    """
    out: dict[str, dict] = {}
    if not rule_ids:
        return out
    if registry_path:
        p = Path(registry_path)
    else:
        p = Path(GOV_RULES_ABS)
    if not p.exists():
        print(f"⚠ 判官登记表不存在: {p}（治理域蒸馏跳过）")
        return out
    try:
        import yaml
        reg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for r in reg.get("rules", []):
            rid = r.get("rule_id")
            if rid in rule_ids:
                out[rid] = {"text": (r.get("text") or "").strip(),
                            "source": r.get("source", "")}
    except Exception as exc:
        print(f"⚠ 判官登记表读取失败（治理域蒸馏跳过）: {exc}")
    return out


def _cooldown_map(jsonl_path) -> dict[str, date]:
    """既有治理提案 → {规则id: 最近裁决/创建日期}（pending/rejected 都算在冷却）。"""
    map_: dict[str, date] = {}
    if not jsonl_path:
        return map_
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        return map_
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("kind") != "gov-criterion" or d.get("status") not in ("pending", "rejected"):
            continue
        ts = (d.get("ts") or d.get("created_at") or "")[:10]
        if not ts:
            continue
        for rid in (d.get("evidence") or {}).get("rule_ids", []):
            try:
                cur = map_.get(rid)
                new = date.fromisoformat(ts)
                if cur is None or new > cur:
                    map_[rid] = new
            except ValueError:
                continue
    return map_


def make_gov_proposals(ledger_entries: list[dict], threshold: int = GOV_THRESHOLD_DEFAULT,
                       registry: dict[str, dict] | None = None,
                       asof: date | None = None,
                       jsonl_path=None,
                       cooldown_days: int = GOV_COOLDOWN_DAYS) -> list[dict]:
    """B 档：判官账本 → 治理判据调优提案（kind=gov-criterion）。

    蒸馏对象 = 判官登记表的判据措辞（AI 可治理的治理本体），不是冻结文件原文。
    证据 = 人工备注/复核（真实人判，非 AI 自证）；规则原文随提案锁定（防漂移）。
    冷却期：同规则自上次裁决 N 天内不再造（默认 14 天，控制打扰）。
    安全：只造提案，不落盘、不改任何文件；accept 走回放验证（见 _mutate）。
    """
    asof = asof or date.today()
    if registry is None:
        registry = load_registry_text(sorted({e.get("rule_id") for e in ledger_entries
                                              if e.get("rule_id")}))
    prefix = f"p-{asof.isoformat()}-gov"
    cool = _cooldown_map(jsonl_path)
    # 聚合：规则 → 人工备注/复核记录
    by_rule: dict[str, list[dict]] = {}
    for e in ledger_entries:
        rid = e.get("rule_id") or (e.get("review_id") or "").rsplit("-", 1)[-1]
        h = e.get("human") or {}
        if h.get("note"):
            by_rule.setdefault(rid, []).append(h)
    props: list[dict] = []
    seq = 0
    for rid, notes in by_rule.items():
        if len(notes) < threshold:
            continue
        last = cool.get(rid)
        if last is not None and (asof - last).days < cooldown_days:
            print(f"  ⏸ gov {rid} 冷却中（上次 {last}，{cooldown_days} 天内不重复提案）")
            continue
        info = registry.get(rid)
        if not info or not info["text"]:
            print(f"  ⚠ gov {rid} 登记表无规则原文，跳过（不造无原文提案）")
            continue
        seq += 1
        # refs 用账本里对应条目（与 notes 顺序一致）
        src = [x for x in ledger_entries
               if (x.get("rule_id") or (x.get("review_id") or "").rsplit("-", 1)[-1]) == rid
               and (x.get("human") or {}).get("note")]
        refs = [f"jev-ledger: 判官={x.get('verdict', '?')} 人工复核={x['human']['verdict']} | {x['human']['note'][:120]}"
                for x in src]
        props.append({
            "id": f"{prefix}-{seq:03d}", "source": "distiller",
            "kind": "gov-criterion", "target": GOV_RULES,
            "evidence": {"count": len(notes), "refs": refs[:10], "rule_ids": [rid],
                          "locked_rule_text": info["text"], "locked_source": info["source"]},
            "suggestion": (f"判官规则 {rid} 判据疑似过严/过宽（近窗 {len(notes)} 次人工复核备注）"
                           f" → 调 criteria 措辞 + jev_fit replay 回放验证；"
                           f"规则原文锁定自 {info['source']}，改措辞不改原文"),
            "impact_estimate": "高", "replay_required": True,
            "status": "pending", "human_note": "", "test_commit": "",
            "ts": asof.isoformat(),
        })
    return props


def write_gov_replay_sheet(p: dict, out_path) -> Path:
    """accept 后生成判官回放单：锁定规则原文 + 证据引用 + 回放要求。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ev = p.get("evidence", {})
    lines = [
        f"# 治理判据回放单 — {p['id']}",
        "",
        f"- 目标：`{p.get('target', GOV_RULES)}`（规则原文来源 `{ev.get('locked_source', '?')}`，AI 不可自改原文）",
        f"- 建议：{p.get('suggestion', '')}",
        f"- 证据（{ev.get('count', 0)} 条人工复核留痕）：",
    ]
    lines += [f"  - {r}" for r in ev.get("refs", [])]
    lines += [
        f"- 锁定规则原文：`{ev.get('locked_rule_text', '')}`",
        "",
        "## 回放要求（未过 = 提案退回，不得落盘）",
        "1. 新判据在历史案例账本上重放：`python3 .claude/scripts/jev_fit.py replay --registry <新版登记表>`",
        "2. 与现版对照：`jev_fit.py compare --a <现版> --b <新版>` — 只有新版一致率 ≥ 现版才采纳",
        "3. 采纳后人类在判官登记表登记新 registry_version（AI 不直接改登记表语义）",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


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
    # B 档：判官账本 → 治理判据调优提案（kind=gov-criterion，冷却期控制打扰）
    try:
        ledger = [json.loads(l) for l in Path(args.ledger).read_text(encoding="utf-8").splitlines()
                  if l.strip()]
        gov = make_gov_proposals(ledger, threshold=args.gov_threshold,
                                 asof=asof, jsonl_path=Path(args.out) / "proposals.jsonl")
        props.extend(gov)
    except Exception as exc:
        print(f"⚠ 治理域蒸馏跳过（不影响其他通道）: {exc}")
    # 防重复（2026-10-17 人类反馈：每天蒸馏出同批提案刷屏）：
    # 同 suggestion 已有 pending/accepted 提案 → 保留原提案，跳过新造（证据计数不动，
    # 遥测趋势本身就是证据）。rejected 的不复活 —— 人已裁决的不再打扰。
    existing: dict = {}
    try:
        existing = {json.loads(l).get("suggestion"): json.loads(l)
                    for l in Path(args.out, "proposals.jsonl").read_text().splitlines() if l.strip()}
        kept = []
        for p in props:
            ex = existing.get(p["suggestion"])
            if ex and ex.get("status") in ("pending", "accepted"):
                kept.append(ex)  # 已在桌上的，不重复造
            else:
                kept.append(p)
        props = kept
    except FileNotFoundError:
        pass
    # 输出时合并既有全量（含裁决历史）+ 真正的新提案，而不是只写本次蒸馏结果
    if existing:
        ex_suggestions = {e.get("suggestion") for e in existing.values()}
        merged = list(existing.values()) + [p for p in props if p["suggestion"] not in ex_suggestions]
        seen = set()
        out_all = []
        for x in merged:
            k = (x.get("suggestion"), x.get("status"))
            if k in seen:
                continue
            seen.add(k)
            out_all.append(x)
        props = out_all
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
            if status == "accepted" and d.get("kind") == "gov-criterion":
                # B 档安全边界：accept 只登记 + 生成判官回放单；
                # 冻结域（AGENTS.md/kernel.md/hooks）与判官登记表一律不自动落盘。
                d["replay_required"] = True
                d["replay_sheet"] = str(write_gov_replay_sheet(
                    d, Path(GOV_REPLAY_DIR) / f"{pid}.md"))
            lines[i] = json.dumps(d, ensure_ascii=False)
            hit = True
    if not hit:
        print(f"未找到 {pid}"); return 1
    p.write_text("\n".join(l for l in lines if l.strip()) + "\n", encoding="utf-8")
    extra = ""
    if status == "accepted" and hit:
        try:
            extra = "（治理判据提案：回放单已生成，待 jev_fit replay 验证）"
        except Exception:
            extra = ""
    print(f"{pid} -> {status}{extra}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="进化提案 distiller/approver")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("distill")
    d.add_argument("--threshold", type=int, default=3)
    d.add_argument("--out", default=DEFAULT_OUT)
    d.add_argument("--gate-pass", default=GATE_PASS_TELEMETRY)
    d.add_argument("--window", type=int, default=14)
    d.add_argument("--ledger", default=JEV_LEDGER, help="判官账本（治理域蒸馏数据源）")
    d.add_argument("--gov-threshold", type=int, default=GOV_THRESHOLD_DEFAULT,
                   help="治理判据提案最小证据数（人工复核备注条数）")
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
