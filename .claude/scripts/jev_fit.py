#!/usr/bin/env python3
"""jev_fit.py — JEV-C 判据拟合闭环。

把「Jev 判定 vs 人判定」的差距变成判据改进，并用回放验证改进是否真的有效。

闭环：
    record  记录一次人工判定（Jev 判定已随案例入账）
    analyze 算一致率，列出分歧，指出最该改判据的规则
    replay  用指定版本的登记表重跑历史案例，算与人工判定的一致率
    compare 两个版本并列对比 —— 只有新版一致率更高才允许采纳

核心纪律：
    · 规则原文不可改（来自 AGENTS.md / README.md），只改 criteria 措辞
    · 没有回放验证的判据修改一律不接受
    · 人工判定只作为参考答案，不写回 registry

用法：
    python3 .claude/scripts/jev_fit.py analyze
    python3 .claude/scripts/jev_fit.py record --commit <sha> --rule soul.1.simple \
        --verdict 符合 --note "..." --reviewer human
    python3 .claude/scripts/jev_fit.py replay --registry .claude/scripts/jev_rules.yaml
    python3 .claude/scripts/jev_fit.py compare --a old.yaml --b new.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_sweep as js  # noqa: E402

# 测试隔离：CARROROS_JEV_LEDGER 指向临时账本，避免 pytest 污染真实案例史。
LEDGER = Path(os.environ.get(
    "CARROROS_JEV_LEDGER", str(ROOT / ".omc" / "state" / "jev" / "reviews.jsonl")))

# 人工判定允许的取值；「不确定」视为弃权，不计入一致率分母
HUMAN_VERDICTS = ("符合", "不符合", "不适用", "不确定")

# ── 样本量与一致率的基准（外部参考，非自创）────────────────────────
#
# 样本量分档取自 jev-eval（TypeSafe Jev 的官方校准工具）：
#   标注行 < 50  → 它直接**拒绝**给阈值，要求继续攒标签
#   50 ~ 200     → 只给「临时值」(provisional)
#   >= 200       → 才认为可作正式依据
#   见 https://github.com/CMaintz/jev-eval
#
# 一致率基准取自 LLM-as-judge 领域的通行门槛：
#   Zheng et al. (MT-Bench, NeurIPS 2023)：GPT-4 与人类专家一致 ~85%，
#     而人类之间的一致性本身只有 ~81%，所以 0.80 被当作「可接受」的参照线
#   实践门槛（fare-policy-assistant）：judge-human 原始一致率 >= 0.80，
#     且 Cohen's κ >= 0.60（Landis & Koch：0.61-0.80 为 substantial）
#   见 https://proceedings.iclr.cc/paper_files/paper/2025/... (Trust or Escalate)
#
# 注意：**原始一致率会在类别不平衡时虚高**，所以同时看 κ。
MAX_PENDING_PER_RULE = 50    # 每规则待复核上限（2026-10-18 降噪：超过就不再入队）
MIN_SAMPLES_REFUSE = 50      # 低于此数：拒绝采纳，先去攒样本
MIN_SAMPLES_PROVISIONAL = 200  # 低于此数：只标 provisional
TARGET_AGREEMENT = 0.80      # 参照一致率
TARGET_KAPPA = 0.60          # 参照 Cohen's κ


# ── 账本 ───────────────────────────────────────────────────────────
def _fingerprint(purpose: str, change: str, changed_paths: list[str]) -> str:
    blob = json.dumps(
        {"purpose": purpose, "change": change, "paths": sorted(changed_paths or [])},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_reviews(path: Path = LEDGER) -> list[dict]:
    """读账本并把「待复核」与「复核结论」合起来。

    账本 append-only，三类条目：
      pending    —— 低置信自动入队，human 为空，等人复核
      resolution —— 人对 pending 的判定，只带 review_id + human
      其它        —— 直接记录型（record），自带 human
    """
    if not Path(path).is_file():
        return []

    entries: list[dict] = []
    resolutions: dict[str, dict] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get("kind") == "resolution":
            resolutions[e["review_id"]] = e.get("human") or {}
            continue
        entries.append(e)

    out = []
    for e in entries:
        merged = dict(e)
        if merged.get("human") is None and e["review_id"] in resolutions:
            merged["human"] = resolutions[e["review_id"]]
        out.append(merged)
    return out


def _pending_fingerprint(entry: dict) -> str:
    """待复核去重键：优先用 change_fingerprint，没有就哈希 diff。"""
    fp = str(entry.get("change_fingerprint") or "").strip()
    if fp:
        return fp
    change = str(entry.get("change") or "")
    return hashlib.sha256(change.encode("utf-8")).hexdigest()[:16] if change else ""


def enqueue_pending(entry: dict, path: Path = LEDGER) -> None:
    """把一个低置信条目放进待复核队列，让规则自己攒样本。

    2026-10-18 降噪（475 条无人读 → 信噪比过低）：
      1. 空 diff 无法判定 → 不入队
      2. 同规则 + 同改动指纹 → 不重复入队
      3. 每规则待复核上限 MAX_PENDING_PER_RULE → 超过不再入队
    """
    js.assert_no_secret(json.dumps(entry, ensure_ascii=False))
    if not str(entry.get("change") or "").strip():
        return
    rows = load_reviews(path)
    if any(r["review_id"] == entry["review_id"] and r.get("human") is None for r in rows):
        return  # 幂等：同一条不重复入队
    pending = [r for r in rows if r.get("human") is None]
    rule_id = entry.get("rule_id")
    fp = _pending_fingerprint(entry)
    if fp and any(r.get("rule_id") == rule_id and _pending_fingerprint(r) == fp for r in pending):
        return
    if sum(1 for r in pending if r.get("rule_id") == rule_id) >= MAX_PENDING_PER_RULE:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "pending", **entry}, ensure_ascii=False) + "\n")


def append_review(entry: dict, path: Path = LEDGER) -> None:
    js.assert_no_secret(json.dumps(entry, ensure_ascii=False))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── record ─────────────────────────────────────────────────────────
def cmd_record(args) -> int:
    if args.verdict not in HUMAN_VERDICTS:
        print(f"ERROR: verdict 只能是 {HUMAN_VERDICTS}", file=sys.stderr)
        return 2

    if args.commit:
        purpose, change, paths = js.collect_commit_change(args.commit, None)
    else:
        purpose, change, paths = "", Path(args.change_file).read_text(encoding="utf-8"), []

    registry = js.load_registry(Path(args.rules))
    rule = next((r for r in registry["rules"] if r["rule_id"] == args.rule), None)
    if rule is None:
        print(f"ERROR: 登记表里没有规则 {args.rule}", file=sys.stderr)
        return 2

    # 复算一次 Jev 判定并留档，保证账本自带「当时 Jev 怎么判的」
    jev = {}
    if rule["judge_by"] != "script":
        res = js.run_sweep(
            task_dir=None, out_dir=None, client=js.JevClient(), registry=registry,
            rules_to_judge=[rule], dry_run=True,
            purpose=purpose, change_text=change, changed_paths=paths,
            repo_context=args.context or "",
        )
        row = res["results"][0]
        jev = {
            "verdict": row["verdict"], "noul": row.get("jev_noul"),
            "choice": row.get("jev_choice") or row.get("raw_choice"),
            "confidence": row.get("jev_confidence"),
        }

    append_review({
        "review_id": f"r-{_fingerprint(purpose, change, paths)}-{args.rule}",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "rule_id": args.rule,
        "registry_version": registry.get("registry_version"),
        "change_fingerprint": _fingerprint(purpose, change, paths),
        "purpose": purpose,
        "change": change[:js.MAX_STATE_CHARS],
        "changed_paths": paths,
        "repo_context": args.context or "",
        "jev": jev,
        "human": {
            "verdict": args.verdict,
            "note": args.note or "",
            "reviewer": args.reviewer or "unknown",
            "label_source": args.label_source,
        },
    })
    print(f"已记账：{args.rule}  人判「{args.verdict}」  Jev 判「{jev.get('verdict')}」")
    return 0


# ── analyze ────────────────────────────────────────────────────────
LABEL_SOURCES = ("contemporaneous_human", "hindsight_repo", "llm_proxy")

# 只有「同期人工判定」才算可信参考答案。
#   contemporaneous_human —— 人当场判的，可信
#   hindsight_repo         —— 从「仓库后来怎么处理」反推的，有后见之明偏差
#   llm_proxy              —— 用另一个模型判的，只是占位，不是真值
TRUSTED_LABEL = "contemporaneous_human"


def split_holdout(
    rows: list[dict], frac: float = 0.3, seed: str = "jev-v1"
) -> tuple[list[dict], list[dict]]:
    """按 review_id 的哈希确定性地切出训练集/留出集。

    为什么必须有留出集：如果一边挑阈值、一边在同一批数据上报成绩，
    数字会虚高（jev-eval 实测虚高约 0.7pp）。改进只在训练集上成立、
    在留出集上不成立，就说明是过拟合，不是真改进。

    确定性切分保证：同样的账目、同样的 seed，切出来永远是同一批。
    """
    train, hold = [], []
    for r in rows:
        h = int(hashlib.sha256(f"{seed}:{r['review_id']}".encode()).hexdigest()[:8], 16)
        (hold if (h % 1000) < int(frac * 1000) else train).append(r)
    return train, hold


def label_breakdown(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        if r.get("human") is None:
            continue
        src = (r["human"].get("label_source") or "unspecified")
        out[src] = out.get(src, 0) + 1
    return out


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's κ —— 扣掉「碰巧一致」的那部分。

    只看原始一致率会在类别不平衡时虚高：全判「符合」也能拿到很高的原始一致率。
    κ 把随机一致的期望扣掉，才是真实一致性。
    """
    if len(pairs) < 2:
        return None
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for lab in labels:
        pa = sum(1 for a, _ in pairs if a == lab) / n
        pb = sum(1 for _, b in pairs if b == lab) / n
        pe += pa * pb
    if pe >= 1.0:
        return None
    return round((po - pe) / (1 - pe), 3)


def sample_tier(n: int) -> str:
    """样本量分档，决定结论的采信级别。"""
    if n < MIN_SAMPLES_REFUSE:
        return "refuse"
    if n < MIN_SAMPLES_PROVISIONAL:
        return "provisional"
    return "ok"


def analyze(rows: list[dict]) -> dict:
    by_rule: dict[str, dict] = {}
    for r in rows:
        if r.get("human") is None:
            continue  # 待复核条目还没人判，不进一致率
        rid = r["rule_id"]
        d = by_rule.setdefault(rid, {
            "total": 0, "agree": 0, "abstain": 0, "diverged": [],
        })
        human = r["human"]["verdict"]
        jev = (r.get("jev") or {}).get("verdict")
        if human == "不确定":
            d["abstain"] += 1
            continue
        d["total"] += 1
        d.setdefault("_pairs", []).append((human, jev))
        if human == jev:
            d["agree"] += 1
        else:
            d["diverged"].append({
                "review_id": r["review_id"],
                "purpose": (r.get("purpose") or "")[:60],
                "human": human,
                "jev": jev,
                "jev_raw": (r.get("jev") or {}).get("choice"),
                "note": r["human"].get("note", ""),
                "reviewer": r["human"].get("reviewer", ""),
            })
    for d in by_rule.values():
        d["agreement"] = round(d["agree"] / d["total"], 3) if d["total"] else None
        d["kappa"] = cohen_kappa(d.pop("_pairs", []))
        d["tier"] = sample_tier(d["total"])
    return by_rule


def cmd_analyze(args) -> int:
    rows = load_reviews(Path(args.ledger))
    if not rows:
        print(f"账本为空：{args.ledger}")
        print("先跑 record 记几条人工判定，再回来看。")
        return 0

    rep = analyze(rows)
    pending = sum(1 for r in rows if r.get("human") is None)
    print(f"# 判据拟合分析（{len(rows)} 条账目，其中待复核 {pending} 条）\n")
    print(f"{'规则':<26}{'样本':>5}{'一致':>5}{'弃权':>5}{'一致率':>8}{'κ':>7}  采信级")
    print("-" * 66)
    tier_zh = {"refuse": "样本不足·拒绝采纳", "provisional": "临时值", "ok": "可用"}
    for rid, d in sorted(rep.items(), key=lambda kv: (kv[1]["agreement"] is None, kv[1]["agreement"])):
        rate = f"{d['agreement']:.2f}" if d["agreement"] is not None else "—"
        kap = f"{d['kappa']:.2f}" if d.get("kappa") is not None else "—"
        print(f"{rid:<26}{d['total']:>5}{d['agree']:>5}{d['abstain']:>5}{rate:>8}{kap:>7}  {tier_zh[d['tier']]}")

    print(f"\n标签来源：{label_breakdown(rows)}"
          f"（只有 {TRUSTED_LABEL} 算可信参考答案）")
    print(f"参照线（外部基准）：一致率 ≥ {TARGET_AGREEMENT}，κ ≥ {TARGET_KAPPA}；"
          f"样本 < {MIN_SAMPLES_REFUSE} 条拒绝采纳，< {MIN_SAMPLES_PROVISIONAL} 条只算临时值")

    worst = [(rid, d) for rid, d in rep.items() if d["total"] and d["agreement"] < 1.0]
    if worst:
        print("\n## 分歧明细")
        for rid, d in sorted(worst, key=lambda kv: kv[1]["agreement"]):
            print(f"\n### {rid}（一致率 {d['agreement']:.2f}，κ {d.get('kappa')}）")
            for x in d["diverged"]:
                print(f"  - 人判「{x['human']}」 vs Jev 判「{x['jev']}」"
                      f"  模型原选「{x['jev_raw']}」  复核人={x['reviewer']}")
                print(f"    改动：{x['purpose']}")
                if x["note"]:
                    print(f"    备注：{x['note']}")
        print("\n## 建议")
        print("一致率越低的规则越该看判据 —— 八成是 criteria 写得不够具体。")
        print("改判据后必须跑 replay 验证，没有回放的修改不接受。")
    else:
        print("\n全部一致。")

    if pending:
        print(f"\n## 有 {pending} 条待复核 —— 跑 `jev_fit.py pending` 查看，"
              "`jev_fit.py judge --review-id <id> --verdict <值>` 填人工判定。")
    return 0


# ── replay ─────────────────────────────────────────────────────────
def replay(rows: list[dict], registry_path: Path, client) -> dict:
    """用指定登记表重跑历史案例，与人工判定比一致率。"""
    registry = js.load_registry(registry_path)
    by_rule: dict[str, dict] = {}
    for r in rows:
        if r["human"]["verdict"] == "不确定":
            continue
        rule = next((x for x in registry["rules"] if x["rule_id"] == r["rule_id"]), None)
        if rule is None or rule["judge_by"] == "script":
            continue
        res = js.run_sweep(
            task_dir=None, out_dir=None, client=client, registry=registry,
            rules_to_judge=[rule], dry_run=True,
            purpose=r.get("purpose", ""), change_text=r.get("change", ""),
            changed_paths=r.get("changed_paths") or [],
            repo_context=r.get("repo_context", ""),
        )
        row = res["results"][0]
        d = by_rule.setdefault(r["rule_id"], {"total": 0, "agree": 0, "diverged": []})
        d["total"] += 1
        if row["verdict"] == r["human"]["verdict"]:
            d["agree"] += 1
        else:
            d["diverged"].append({
                "human": r["human"]["verdict"], "jev": row["verdict"],
                "purpose": (r.get("purpose") or "")[:60],
            })
    for d in by_rule.values():
        d["agreement"] = round(d["agree"] / d["total"], 3) if d["total"] else None
    return by_rule


def _print_replay(title: str, rep: dict) -> None:
    print(f"\n## {title}")
    print(f"{'规则':<26}{'样本':>5}{'一致':>5}{'一致率':>9}")
    print("-" * 46)
    for rid, d in sorted(rep.items()):
        rate = f"{d['agreement']:.2f}" if d["agreement"] is not None else "—"
        print(f"{rid:<26}{d['total']:>5}{d['agree']:>5}{rate:>9}")


def cmd_replay(args) -> int:
    rows = load_reviews(Path(args.ledger))
    if not rows:
        print("账本为空，先 record。")
        return 0
    rep = replay(rows, Path(args.registry), js.JevClient())
    print(f"# 签据回放（{len(rows)} 条账目，登记表 {args.registry}）")
    _print_replay("回放一致率", rep)
    return 0


def cmd_compare(args) -> int:
    rows = [r for r in load_reviews(Path(args.ledger)) if r.get("human") is not None]
    if not rows:
        print("账本为空，先 record。")
        return 0
    client = js.JevClient()

    # 标签来源审查：参考答案不可信时，一致率再好看也不能作为采纳依据
    breakdown = label_breakdown(rows)
    trusted = breakdown.get(TRUSTED_LABEL, 0)
    total = sum(breakdown.values())
    print(f"# 判据版本对比（{total} 条账目）")
    print(f"标签来源：{breakdown}")
    if trusted < total:
        print(f"⚠️ 其中只有 {trusted}/{total} 条是同期人工判定，"
              f"其余来自事后反推或模型代理 —— **有偏差，结论只能作参考**\n")
    else:
        print()

    train_rows, hold_rows = split_holdout(rows, frac=args.holdout_frac)
    print(f"留出集切分（frac={args.holdout_frac}, seed={args.holdout_seed}）："
          f"训练 {len(train_rows)} 条 / 留出 {len(hold_rows)} 条")
    print("> 一边挑阈值一边在同一批数据上报成绩会虚高；改进必须**在留出集上也成立**才算数。\n")

    a = replay(train_rows, Path(args.a), client)
    b = replay(train_rows, Path(args.b), client)
    _print_replay(f"训练集 · A（旧）：{args.a}", a)
    _print_replay(f"训练集 · B（新）：{args.b}", b)

    if hold_rows:
        ha = replay(hold_rows, Path(args.a), client)
        hb = replay(hold_rows, Path(args.b), client)
        _print_replay(f"留出集 · A（旧）：{args.a}", ha)
        _print_replay(f"留出集 · B（新）：{args.b}", hb)
    else:
        ha = hb = {}
        print("\n（留出集为空，无法做泛化检验；账目再多一些再跑）")

    print("\n## 结论")
    for rid in sorted(set(a) | set(b)):
        ra = (a.get(rid) or {}).get("agreement")
        rb = (b.get(rid) or {}).get("agreement")
        n = (a.get(rid) or b.get(rid) or {}).get("total", 0)
        tier = sample_tier(n)
        if tier == "refuse":
            print(f"- `{rid}`：**训练集仅 {n} 条，低于 {MIN_SAMPLES_REFUSE} 条下限 → 拒绝采纳**。"
                  f"参考 jev-eval：先攒够再动，现在改参数等于拟合噪声。")
            continue
        if ra is None or rb is None:
            print(f"- `{rid}`：样本不足，不下结论")
            continue
        if rb < ra:
            print(f"- `{rid}`：**新版更差**（{ra:.2f} → {rb:.2f}），退回旧版")
            continue
        if rb == ra:
            print(f"- `{rid}`：训练集无差别（{ra:.2f}），改了等于没改，不必采纳")
            continue

        # 训练集上更好 —— 再看留出集上是否也更好
        ha_v = (ha.get(rid) or {}).get("agreement")
        hb_v = (hb.get(rid) or {}).get("agreement")
        if ha_v is None or hb_v is None:
            print(f"- `{rid}`：训练集更好（{ra:.2f} → {rb:.2f}），"
                  f"但留出集样本不足，**无法验证泛化 → 暂不采纳**")
        elif hb_v > ha_v:
            print(f"- `{rid}`：训练集更好（{ra:.2f} → {rb:.2f}），"
                  f"留出集也更好（{ha_v:.2f} → {hb_v:.2f}）→ **可采纳**")
        elif hb_v == ha_v:
            print(f"- `{rid}`：训练集更好（{ra:.2f} → {rb:.2f}），"
                  f"但留出集无变化（{ha_v:.2f}）→ **疑似过拟合训练集，不采纳**")
        else:
            print(f"- `{rid}`：训练集更好（{ra:.2f} → {rb:.2f}），"
                  f"**留出集反而更差（{ha_v:.2f} → {hb_v:.2f}）→ 过拟合，退回**")

    print(
        f"\n纪律：① 样本 < {MIN_SAMPLES_REFUSE} 条不动、< {MIN_SAMPLES_PROVISIONAL} 条只算临时值；"
        "② 训练集一致率更高；③ **留出集上也必须更好**（只涨在训练集上就是过拟合）；"
        "④ 无差别或更差一律退回。"
    )
    return 0


# ── 待复核队列：让低置信自己攒样本 ─────────────────────────────────
def cmd_pending(args) -> int:
    rows = [r for r in load_reviews(Path(args.ledger)) if r.get("human") is None]
    if not rows:
        print("没有待复核条目。")
        print("低置信条目会在 jev_sweep 跑到该规则时自动入队。")
        return 0
    print(f"# 待复核 {len(rows)} 条（低置信，模型自己说拿不准）\n")
    print("复核目的**不是**判这一次，而是看是不是**规则判据**有问题。\n")
    all_ids = [r["review_id"] for r in rows]
    for i, r in enumerate(rows, 1):
        j = r.get("jev") or {}
        short = shortest_unique_substring(r["review_id"], all_ids)
        print(f"[{i}] {r['rule_id']}  模型原选「{j.get('choice')}」"
              f"  noul={j.get('noul')}  置信度={j.get('confidence')}")
        print(f"    改动 {(r.get('purpose') or '')[:70]}")
        # 给出的前缀保证唯一，直接可复制可用
        print(f"    →  python3 .claude/scripts/jev_fit.py judge "
              f"--review-id {short} --verdict 符合 --reviewer <你的名字>")

    print("\n填判定时 --review-id 可以只给**唯一前缀**，不必抄整串。")
    print(f"取值只能是：{' / '.join(HUMAN_VERDICTS)}")
    return 0


def _resolve_review_id(prefix: str, rows: list[dict]) -> tuple[str | None, str]:
    """按唯一子串匹配 review_id。返回 (完整id, 错误说明)。"""
    exact = [r["review_id"] for r in rows if r["review_id"] == prefix]
    if exact:
        return exact[0], ""
    hits = sorted({r["review_id"] for r in rows if prefix in r["review_id"]})
    if not hits:
        return None, f"没有匹配 '{prefix}' 的条目"
    if len(hits) > 1:
        return None, f"'{prefix}' 不唯一，匹配到 {len(hits)} 条：{hits[:3]}"
    return hits[0], ""


def shortest_unique_substring(rid: str, all_ids: list[str]) -> str:
    """给一条 id 找到**最短且能唯一定位它**的子串，供人类少打字。

    不能用「末 8 位」这种偷懒办法 —— 同一规则可能有多条待复核，
    末几位会撞车，打印出来的命令跑不通。
    """
    others = [x for x in all_ids if x != rid]
    for length in range(4, len(rid) + 1):
        for start in range(0, len(rid) - length + 1):
            sub = rid[start:start + length]
            if all(sub not in o for o in others):
                return sub
    return rid


def cmd_judge(args) -> int:
    if args.verdict not in HUMAN_VERDICTS:
        print(f"ERROR: verdict 只能是 {HUMAN_VERDICTS}", file=sys.stderr)
        return 2
    rows = load_reviews(Path(args.ledger))
    full_id, err = _resolve_review_id(args.review_id, rows)
    if full_id is None:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    target = next((r for r in rows if r["review_id"] == full_id), None)
    if target is None:
        print(f"ERROR: 账本里没有 review_id = {full_id}", file=sys.stderr)
        return 2
    append_review({
        "kind": "resolution",
        "review_id": full_id,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "human": {
            "verdict": args.verdict,
            "note": args.note or "",
            "reviewer": args.reviewer or "unknown",
            "label_source": args.label_source,
        },
    })
    print(f"已复核：{full_id} → 「{args.verdict}」 复核人={args.reviewer or 'unknown'}")
    print("再跑 analyze 看一致率变化。")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="JEV-C 判据拟合闭环")
    ap.add_argument("--ledger", default=str(LEDGER))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("record", help="记录一次人工判定")
    p.add_argument("--commit")
    p.add_argument("--change-file")
    p.add_argument("--rule", required=True)
    p.add_argument("--verdict", required=True, choices=list(HUMAN_VERDICTS))
    p.add_argument("--note", default="")
    p.add_argument("--reviewer", default="unknown")
    p.add_argument(
        "--label-source", default="hindsight_repo", choices=list(LABEL_SOURCES),
        help="参考答案怎么来的。contemporaneous_human 才可信；"
             "hindsight_repo 是事后反推（有偏差）；llm_proxy 是模型代理（占位）",
    )
    p.add_argument("--context", default="")
    p.add_argument("--rules", default=str(SCRIPTS_DIR / "jev_rules.yaml"))
    p.set_defaults(func=cmd_record)

    sub.add_parser("analyze", help="算一致率并列分歧").set_defaults(func=cmd_analyze)

    sub.add_parser("pending", help="列出待复核条目").set_defaults(func=cmd_pending)

    p = sub.add_parser("judge", help="对一条待复核填人工判定")
    p.add_argument("--review-id", required=True)
    p.add_argument("--verdict", required=True, choices=list(HUMAN_VERDICTS))
    p.add_argument("--note", default="")
    p.add_argument("--reviewer", default="unknown")
    p.add_argument("--label-source", default="contemporaneous_human",
                   choices=list(LABEL_SOURCES),
                   help="默认同期人工判定（人当场填的）")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("replay", help="用指定登记表回放")
    p.add_argument("--registry", required=True)
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("compare", help="两个版本并列对比（含留出集泛化检验）")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--holdout-frac", type=float, default=0.3,
                   help="留出集比例（默认 0.3）。改进必须在留出集上也成立")
    p.add_argument("--holdout-seed", default="jev-v1", help="切分种子，保证可复现")
    p.set_defaults(func=cmd_compare)

    args = ap.parse_args(argv)
    if args.cmd == "record" and not (args.commit or args.change_file):
        print("ERROR: record 需要 --commit 或 --change-file", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
