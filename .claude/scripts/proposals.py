#!/usr/bin/env python3
"""proposals.py — 进化提案 distiller/approver v1（PLAN_SIMPLIFY C2/C6, Phase 2）

把真实使用沉淀的原料（gate-pass 门禁触发遥测）蒸馏成"进化提案"，供人类采纳台裁决。
Schema（C2 v1）：
  {id: p-YYYY-MM-DD-NNN, source: distiller,
   kind: anti-pattern | gate-zombie | doc-drift | new-gate | delete-candidate | gov-criterion,
   evidence: {count, refs[]}, suggestion, impact_estimate,
   status: pending|accepted|rejected|deferred, human_note, test_commit}
  gov-criterion 额外字段：target, replay_required, ts,
   evidence.{rule_ids, locked_rule_text, locked_source, human_judged, trust}

注（index48）：原 anti-pattern 一路的数据源 error-dna 已整体移除；
现存 kind 主要由 gate-zombie / delete-candidate / gov-criterion 产生。

用法：
  python3 .claude/scripts/proposals.py distill [--threshold N] [--gov-threshold N]
                                              [--gov-trust strict|inform] [--out DIR]
  python3 .claude/scripts/proposals.py list|accept <id>|reject <id> <note>  [proposals.jsonl]
  python3 .claude/scripts/proposals.py stats [--json]   # M1 采纳数 / M2 转化率 / M5 体重

  kind=gov-criterion（B 档，A+B 2026-10-22 开启）：判官账本人判备注 → 判据调优提案。
  证据闸门（note_trust）：reviewer 必须是真人 且 label_source=contemporaneous_human；
  repo-history / *-proxy / 缺 label_source 一律不算人判 —— 默认 strict 档不计入证据
  阈值（宁可不提案，也不把 AI 自证包装成「人工复核」），--gov-trust inform 可放宽，
  但会降级影响估计并在正文标注成色。
  范围闸门：首批只动 GOV_ALLOWED_SOURCES（AGENTS.md）；kernel.md 源规则在判官样本
  < GOV_KERNEL_MIN_SAMPLES(200) 前不蒸馏。
  accept 只生成判官回放单；改登记表需 jev_fit replay/compare 回放验证（新版一致率
  必须【更高】）+ 人类登记 registry_version；冻结域（AGENTS.md/kernel.md/hooks）
  永不自动落盘，必须人工签票（24h TTL）。
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_OUT = ".omc/proposals"
# 遥测单一真源位置（2026-10-16 遥测卫生：按月分片目录）
GATE_PASS_TELEMETRY = ".omc/state/gate-pass-count.jsonl"
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
# 语义：asof - 上次裁决日 >= N 天才允许再提（N=14 即第 15 天起可提）
GOV_COOLDOWN_DAYS = int(os.environ.get("CARROROS_GOV_COOLDOWN_DAYS", "14"))
# 通用冷却期（2026-10-24 RSI 修复）：被拒绝/搁置的提案，同 key 在 N 天内不再重提。
PROPOSAL_COOLDOWN_DAYS = int(os.environ.get("CARROROS_PROPOSAL_COOLDOWN_DAYS", "14"))
# 治理域蒸馏最小证据数（人工备注/复核留痕，非 AI 自证）
GOV_THRESHOLD_DEFAULT = 2
# 判官回放单落盘目录（accept 后供 jev_fit replay 重放；env 覆盖供测试隔离）
GOV_REPLAY_DIR = os.environ.get("CARROROS_GOV_REPLAY_DIR") or \
    str(Path(__file__).resolve().parents[2] / ".omc" / "state" / "jev" / "replay")

# ── 证据可信度闸门（P0，2026-10-22 审计修复）──
# 只有「同期人工判定」才算可信参考答案（沿用 jev_fit.py:248 的教义：
# hindsight_repo 是事后反推有偏差，llm_proxy 是模型代理占位）。
# 账本里 human.reviewer 必须是真人；repo-history / *-proxy / 缺省 一律视为非人判。
TRUSTED_LABEL_SOURCES = ("contemporaneous_human",)
NON_HUMAN_REVIEWER_MARKERS = ("proxy", "repo-history", "bot", "ai", "agent", "model")
# 弃权不是证据：与 jev_fit.py「不确定视为弃权，不计入一致率分母」同一口径
ABSTAIN_VERDICTS = ("不确定", "不适用")
# strict = 非人判不计入证据阈值（默认，宁可不提案也不虚报证据成色）
# inform = 非人判也可提案，但降级影响估计并在正文显著标注（探索用）
GOV_TRUST_MODES = ("strict", "inform")
GOV_TRUST_MODE = os.environ.get("CARROROS_GOV_TRUST", "strict")
# 首批范围：只允许来源为 AGENTS.md 的规则（人类裁决的 B 档首批边界，编码为白名单）
GOV_ALLOWED_SOURCES = tuple(
    s.strip() for s in os.environ.get("CARROROS_GOV_ALLOWED_SOURCES", "AGENTS.md").split(",")
    if s.strip())
# 冻结域闸门：kernel.md 来源的规则在判官样本量达标前不进入蒸馏（人类裁决约束）
GOV_KERNEL_MIN_SAMPLES = int(os.environ.get("CARROROS_GOV_KERNEL_MIN_SAMPLES", "200"))


def _max_seq_for_day(jsonl_path, asof: date) -> int:
    """既有提案里同一天已占用的最大流水号（防新提案撞号被 write_proposals 静默丢弃）。"""
    if not jsonl_path:
        return 0
    p = Path(jsonl_path)
    if not p.exists():
        return 0
    import re as _re
    pat = _re.compile(rf"^p-{asof.isoformat()}-(\d{{3}})$")
    mx = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            m = pat.match(str(json.loads(line).get("id", "")))
        except json.JSONDecodeError:
            continue
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


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


def proposal_key(p: dict) -> str:
    """提案稳定身份（跨天比对，不依赖日期编号）。"""
    kind, sug = p.get("kind"), str(p.get("suggestion") or "")
    m = (re.search(r"门禁「(.+?)」", sug) if kind == "gate-zombie"
         else re.search(r"死代码\s+(\S+?)（", sug) if kind == "delete-candidate" else None)
    if m:
        return ("gate:" if kind == "gate-zombie" else "path:") + m.group(1)
    ids = sorted((p.get("evidence") or {}).get("rule_ids") or []) if kind == "gov-criterion" else []
    return "rule:" + ",".join(ids) if ids else f"suggestion:{sug}"


def decision_date(p: dict) -> date | None:
    """裁决日期：显式字段优先，其次提案 id 的日期前缀。"""
    vals = [p.get(f) for f in ("decided_at", "rejected_at", "accepted_at", "created_at", "ts")]
    m = re.match(r"p-(\d{4}-\d{2}-\d{2})-", str(p.get("id") or ""))
    vals.append(m.group(1) if m else None)
    for v in vals:
        try:
            return date.fromisoformat(str(v)[:10])
        except (TypeError, ValueError):
            continue
    return None


def filter_distilled(props: list[dict], existing_rows: list[dict],
                     asof: date, cooldown_days: int = PROPOSAL_COOLDOWN_DAYS
                     ) -> tuple[list[dict], list[dict]]:
    """去重 + 冷却：pending/accepted 保留；rejected/deferred 冷却期内抑制，期满可复活。"""
    latest: dict = {}
    for row in existing_rows:
        k, d = proposal_key(row), decision_date(row)
        if k not in latest or (d and (latest[k][1] is None or d > latest[k][1])):
            latest[k] = (row, d)
    kept: list[dict] = []
    suppressed: list[dict] = []
    for p in props:
        row, d = latest.get(proposal_key(p), (None, None))
        if row and row.get("status") in ("pending", "accepted"):
            kept.append(row)
            continue
        if row and row.get("status") in ("rejected", "deferred") and d \
                and (asof - d).days < cooldown_days:
            suppressed.append(row)
            continue
        kept.append(p)
    return kept, suppressed


def rsi_stats(jsonl_path, root=None) -> dict:
    """RSI 三指标（磁盘真相源）：M1 采纳数 / M2 转化率 / M5 体重。"""
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    p = Path(jsonl_path)
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()] if p.exists() else []
    c = Counter(r.get("status") for r in rows)
    accepted, rejected, deferred = c.get("accepted", 0), c.get("rejected", 0), c.get("deferred", 0)
    decided = accepted + rejected + deferred

    def _lines(paths) -> int:
        return sum(len(q.read_text(encoding="utf-8", errors="ignore").splitlines())
                   for q in paths)

    code = [q for d in ("scripts", "hooks") for q in (root / ".claude" / d).rglob("*.py")
            if "__pycache__" not in q.parts]
    docs = [q for q in (root / ".claude").rglob("*.md") if "archived" not in q.parts]
    docs += [q for q in (root / n for n in ("AGENTS.md", "CLAUDE.md")) if q.exists()]
    return {
        "total": len(rows), "accepted": accepted, "rejected": rejected,
        "deferred": deferred, "pending": c.get("pending", 0), "decided": decided,
        "adoption_rate": (accepted / decided) if decided else 0.0,
        "unverified_decisions": sum(
            1 for r in rows if r.get("status") in ("accepted", "rejected", "deferred")
            and not (r.get("decided_by") or r.get("rejected_by"))),
        "weight": {"code_lines": _lines(code), "doc_lines": _lines(docs)},
    }


def is_abstain(entry: dict) -> bool:
    """人判是否为弃权（不确定/不适用）。

    通行做法（也与 jev_fit.py:76 的「不确定视为弃权，不计入一致率分母」一致）：
    弃权不是证据，既不进证据计数，也不构成冲突。
    """
    h = entry.get("human") or {}
    return str(h.get("verdict") or "").strip() in ABSTAIN_VERDICTS


def entry_rule_id(entry: dict) -> str:
    """账本条目 → 规则 id。resolution 记录没有 rule_id，靠 review_id 尾段回连。"""
    rid = entry.get("rule_id")
    if rid:
        return str(rid)
    return (entry.get("review_id") or "").rsplit("-", 1)[-1]


def note_trust(entry: dict) -> tuple[bool, str]:
    """判断一条账本备注是否「人判」→ (可信?, 依据/原因)。

    守 jev_fit.py 的参考答案教义：只有 contemporaneous_human 且 reviewer 是真人时可信。
    否则返回 False + 原因（repo-history / *-proxy / 缺 label_source 等），
    供提案正文如实标注，绝不把 AI 自证包装成「人工复核」。
    """
    h = entry.get("human") or {}
    reviewer = str(h.get("reviewer") or "").strip()
    label = str(h.get("label_source") or "").strip()
    if not reviewer:
        return False, "缺 reviewer"
    low = reviewer.lower()
    for marker in NON_HUMAN_REVIEWER_MARKERS:
        if marker in low:
            return False, f"reviewer={reviewer}"
    if not label:
        return False, f"缺 label_source（reviewer={reviewer}）"
    if label not in TRUSTED_LABEL_SOURCES:
        return False, f"label_source={label}"
    return True, f"reviewer={reviewer}"


def load_rules_full(registry_path: str | None = None) -> dict[str, dict]:
    """读判官登记表全量规则（还原判官判定需要 accept_at/reject_at/confidence_at）。"""
    p = Path(registry_path) if registry_path else Path(GOV_RULES_ABS)
    if not p.exists():
        return {}
    try:
        import yaml
        reg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"⚠ 判官登记表读取失败（冲突检测跳过）: {exc}")
        return {}
    return {r.get("rule_id"): r for r in reg.get("rules", []) if r.get("rule_id")}


def make_gov_proposals(ledger_entries: list[dict], threshold: int = GOV_THRESHOLD_DEFAULT,
                       registry: dict[str, dict] | None = None,
                       asof: date | None = None,
                       jsonl_path=None,
                       cooldown_days: int = GOV_COOLDOWN_DAYS,
                       seq_start: int = 0,
                       trust_mode: str = GOV_TRUST_MODE,
                       require_conflict: bool = True) -> list[dict]:
    """B 档：判官账本 → 治理判据调优提案（kind=gov-criterion）。

    蒸馏对象 = 判官登记表的判据措辞（AI 可治理的治理本体），不是冻结文件原文。
    证据 = 人判备注（note_trust 闸门：非人判不计入阈值，只在正文如实标注成色）；
    规则原文随提案锁定（防漂移）。
    范围 = GOV_ALLOWED_SOURCES 白名单（首批 AGENTS.md）；kernel.md 另设样本量闸门。
    冷却期：同规则自上次裁决 >= N 天前才允许再提（默认 14 天，控制打扰）。
    ID：沿用 schema p-YYYY-MM-DD-NNN，seq_start 由调用方给已有提案数，避免撞号。
    安全：只造提案，不落盘、不改任何文件；accept 走回放验证（见 _mutate）。
    """
    asof = asof or date.today()
    if trust_mode not in GOV_TRUST_MODES:
        raise ValueError(f"trust_mode 必须是 {GOV_TRUST_MODES}，收到 {trust_mode!r}")
    orig = {x.get("review_id"): x for x in ledger_entries if x.get("rule_id")}
    if registry is None:
        registry = load_registry_text(sorted({
            entry_rule_id(orig.get(e.get("review_id"), e) if not e.get("rule_id") else e)
            for e in ledger_entries if (e.get("human") or {}).get("note")}))
    cool = _cooldown_map(jsonl_path)
    # 冲突驱动（用户口径 2026-10-23）：只有「判官结论 vs 人判结论」相反才请人裁决一次，
    # 不做日常排队。require_conflict=False 可退回旧的「证据量驱动」。
    conflicts = find_conflicts(ledger_entries, load_rules_full(),
                               trust_mode=trust_mode) if require_conflict else []
    conflicts_by_rule: dict[str, list[dict]] = {}
    for c in conflicts:
        conflicts_by_rule.setdefault(c["rule_id"], []).append(c)
    # 聚合：规则 → [(条目, 可信?, 原因)]；弃权（不确定/不适用）不是证据
    by_rule: dict[str, list[tuple[dict, bool, str]]] = {}
    abstained: dict[str, int] = {}
    for e in ledger_entries:
        rid = entry_rule_id(orig.get(e.get("review_id"), e) if not e.get("rule_id") else e)
        h = e.get("human") or {}
        if not h.get("note"):
            continue
        if is_abstain(e):
            abstained[rid] = abstained.get(rid, 0) + 1
            continue
        ok, why = note_trust(e)
        by_rule.setdefault(rid, []).append((e, ok, why))
    props: list[dict] = []
    seq = 0
    for rid, rows in by_rule.items():
        trusted = [r for r in rows if r[1]]
        untrusted = [r for r in rows if not r[1]]
        # 阈值只数人判：strict 下非人判不算证据；inform 下允许但降级
        counted = rows if trust_mode == "inform" else trusted
        if len(counted) < threshold:
            if untrusted and len(rows) >= threshold:
                why = "、".join(sorted({r[2] for r in untrusted}))
                print(f"  ⚠ gov {rid} 有 {len(rows)} 条备注但 0 条人判（{why}）"
                      f" → 不计入证据；请用 jev_fit.py judge --label-source contemporaneous_human 补人判")
            continue
        rid_conflicts = conflicts_by_rule.get(rid, [])
        opposite = [c for c in rid_conflicts if c["kind"] == "opposite"]
        if require_conflict and not opposite:
            # 无相反结论 → 不打扰（判官弃权的「判据不足」只做记录，不升级为裁决）
            if rid_conflicts:
                print(f"  ⏸ gov {rid} 有 {len(rid_conflicts)} 条判官弃权记录但无相反结论冲突"
                      f" → 不请人裁决（判据不足信号已留在备注）")
            continue
        last = cool.get(rid)
        if last is not None and (asof - last).days < cooldown_days:
            print(f"  ⏸ gov {rid} 冷却中（上次 {last}，需满 {cooldown_days} 天才可再提）")
            continue
        info = registry.get(rid)
        if not info or not info["text"]:
            print(f"  ⚠ gov {rid} 登记表无规则原文，跳过（不造无原文提案）")
            continue
        # 范围闸门：首批只动 AGENTS.md 源，kernel.md 需样本量达标
        src = str(info.get("source") or "")
        src_file = src.split(":")[0]
        if any(m in src_file for m in ("kernel.md",)):
            if len(ledger_entries) < GOV_KERNEL_MIN_SAMPLES:
                print(f"  ⏸ gov {rid} 源为冻结域 {src}（判官样本 {len(ledger_entries)}"
                      f" < {GOV_KERNEL_MIN_SAMPLES}，暂不蒸馏）")
                continue
        elif GOV_ALLOWED_SOURCES and src_file not in GOV_ALLOWED_SOURCES:
            print(f"  ⏸ gov {rid} 源 {src} 不在首批白名单 {GOV_ALLOWED_SOURCES}，跳过")
            continue
        seq += 1
        refs: list[str] = []
        for c in opposite:
            ref = (f"jev-ledger [冲突] 判官={c['judge']} vs 人判={c['human']} | "
                   f"{c['note'][:120]}")
            if ref not in refs:
                refs.append(ref)
        for e, ok, why in rows:
            h = e["human"]
            verdict = h.get("verdict") or "?"
            judge = e.get("verdict")
            judge_txt = judge if judge else "账本无 verdict（缺口）"
            tag = "[人判]" if ok else f"[非人判:{why}]"
            ref = (f"jev-ledger {tag} 判官={judge_txt} 人工判定={verdict} | "
                   f"{h['note'][:120]}")
            if ref not in refs:  # 去重（同一备注重复记两次不算两条证据）
                refs.append(ref)
        n_trusted = len(trusted)
        if trust_mode == "inform" and n_trusted < threshold:
            impact = "中"
            caveat = (f"⚠ 证据含非人判标签（人判仅 {n_trusted}/{len(rows)} 条），"
                      f"需人工先确认成色再采纳；")
        else:
            impact = "高"
            caveat = ""
        props.append({
            "id": f"p-{asof.isoformat()}-{seq_start + seq:03d}", "source": "distiller",
            "kind": "gov-criterion", "target": GOV_RULES,
            "evidence": {"count": len(refs), "refs": refs[:10], "rule_ids": [rid],
                          "locked_rule_text": info["text"], "locked_source": info["source"],
                          "human_judged": n_trusted,
                          "conflicts": [{"review_id": c["review_id"], "judge": c["judge"],
                                          "human": c["human"]} for c in opposite],
                          "trust": "human" if n_trusted >= threshold else "mixed"},
            "suggestion": (f"{caveat}判官规则 {rid} 判据与人判结论冲突 "
                           f"{len(opposite)} 次（人判备注 {n_trusted} 条）"
                           f" → 需人类裁决一次：调 criteria 措辞 + jev_fit replay 回放验证；"
                           f"规则原文锁定自 {info['source']}，改措辞不改原文"),
            "impact_estimate": impact, "replay_required": True,
            "status": "pending", "human_note": "", "test_commit": "",
            "ts": asof.isoformat(),
        })
    return props


# 判官「没给结论」的判定：与人判明确结论不一致时，属判据不足信号，不算真冲突
NO_CONCLUSION_VERDICTS = ("不能判定", "证据不足", "不可用")


def judge_verdict_of(entry: dict, rules_by_id: dict) -> str | None:
    """账本条目 → 判官当时的判定。verdict 字段多为 null，需从 jev 原始信号还原。"""
    v = entry.get("verdict")
    if v:
        return str(v)
    jev = entry.get("jev") or {}
    rule = rules_by_id.get(entry_rule_id(entry))
    if not jev or not rule:
        return None
    try:
        from jev_sweep import verdict_from_answer
    except Exception:
        return None
    try:
        return verdict_from_answer(jev, rule)
    except Exception:
        return None


def find_conflicts(ledger_entries: list[dict], rules_by_id: dict,
                   trust_mode: str = GOV_TRUST_MODE) -> list[dict]:
    """规则级冲突检测：可信人判 vs 判官判定，双方都有明确结论且相反。

    用户口径（2026-10-23）：不搞日常排队，只有结论冲突才请人类裁决一次。
    弃权（不确定/不适用）不算；判官没给结论也不算真冲突（另计 undecided_band）。
    返回 [{rule_id, review_id, judge, human, note, kind}]，按规则聚合。
    """
    # 原判定位（2026-10-24）：明确结论存在 kind=None 原始记录里；只查 pending 配不上对。
    by_id: dict = {}
    for x in ledger_entries:
        rid = x.get("review_id")
        if not rid:
            continue
        prev = by_id.get(rid)
        if prev is None or (not judge_verdict_of(prev, rules_by_id)
                            and judge_verdict_of(x, rules_by_id)):
            by_id[rid] = x
    out: list[dict] = []
    for e in ledger_entries:
        if e.get("kind") != "resolution":
            continue
        h = e.get("human") or {}
        hv = str(h.get("verdict") or "").strip()
        if not hv or hv in ABSTAIN_VERDICTS:
            continue
        ok, _why = note_trust(e)
        if not ok and trust_mode != "inform":
            continue
        src = by_id.get(e.get("review_id")) or e
        judge = judge_verdict_of({**src, **{k: v for k, v in e.items() if k != "human"}},
                                 rules_by_id)
        if not judge:
            continue
        # 规则 id 从原判取：resolution 不带 rule_id，回落到 review_id 尾段会截断
        rid = entry_rule_id(src)
        if judge in NO_CONCLUSION_VERDICTS:
            # 判官没结论、人判有结论 → 判据不足（不是相反结论的冲突）
            out.append({"rule_id": rid, "review_id": e.get("review_id"), "judge": judge,
                        "human": hv, "note": h.get("note") or "", "kind": "undecided"})
        elif judge != hv:
            out.append({"rule_id": rid, "review_id": e.get("review_id"), "judge": judge,
                        "human": hv, "note": h.get("note") or "", "kind": "opposite"})
    return out


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
        f"- 证据（{ev.get('count', 0)} 条；其中人判 {ev.get('human_judged', 0)} 条，"
        f"成色 `{ev.get('trust', '?')}`）：",
    ]
    lines += [f"  - {r}" for r in ev.get("refs", [])]
    if ev.get("trust") == "mixed":
        lines += ["", "> ⚠ 本条证据含非人判标签（AI 代理/仓库回溯），"
                      "采纳前须由人复核成色；不得据此直接改判据。"]
    lines += [
        f"- 锁定规则原文：`{ev.get('locked_rule_text', '')}`",
        "",
        "## 回放要求（未过 = 提案退回，不得落盘）",
        "1. 新判据在历史案例账本上重放：`python3 .claude/scripts/jev_fit.py replay --registry <新版登记表>`",
        "2. 与现版对照：`jev_fit.py compare --a <现版> --b <新版>` — 只有新版一致率【更高】才允许采纳"
        "（jev_fit.py 教义原文：更高，不是不低于；回放与留出集两侧都须成立）",
        "3. 采纳后人类在判官登记表登记新 registry_version（AI 不直接改登记表语义）",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def write_proposals(props: list[dict], jsonl_out, md_out) -> tuple[Path, Path]:
    jsonl_out = Path(jsonl_out)
    md_out = Path(md_out)
    jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    # 幂等：已存在的 id 跳过（防重跑重复）。区分两种情况：
    #   同 id 同内容 → 幂等跳过（静默，重跑不该报警）
    #   同 id 不同内容 → 真撞号，提案会凭空消失，必须喊出来（2026-10-22 审计发现）
    seen: dict[str, str] = {}
    if jsonl_out.exists():
        for line in jsonl_out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            seen[d.get("id", "")] = json.dumps(d, ensure_ascii=False, sort_keys=True)
    with jsonl_out.open("a", encoding="utf-8") as f:
        collided = []
        for p in props:
            key = json.dumps(p, ensure_ascii=False, sort_keys=True)
            if p["id"] in seen:
                if seen[p["id"]] != key:
                    collided.append(p["id"])
                continue
            seen[p["id"]] = key  # 同批内重复也要拦，否则文件里出现重复 id
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    if collided:
        print(f"⚠ 提案 ID 撞号且内容不同，被跳过 {len(collided)} 条: {sorted(set(collided))}"
              f" —— 检查蒸馏编号（同一天多轮蒸馏需接续已用号）")
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
        # seq_start 取「已造方案数」与「既有同日最大号」的较大值：
        # 沿用 schema p-YYYY-MM-DD-NNN，且绝不与其他通道/历史提案撞号
        gov = make_gov_proposals(ledger, threshold=args.gov_threshold,
                                 asof=asof, jsonl_path=Path(args.out) / "proposals.jsonl",
                                 seq_start=max(len(props),
                                               _max_seq_for_day(Path(args.out) / "proposals.jsonl",
                                                                asof)),
                                 trust_mode=args.gov_trust)
        props.extend(gov)
    except Exception as exc:
        print(f"⚠ 治理域蒸馏跳过（不影响其他通道）: {exc}")
    # 防重复 + 冷却（2026-10-24 RSI 修复）：
    #   同 key 已有 pending/accepted → 保留原提案；
    #   同 key 已被 rejected/deferred 且未过冷却期 → 抑制（拒绝必须真的生效）；
    #   冷却期满 → 允许重新提案。
    out_jsonl = Path(args.out) / "proposals.jsonl"
    existing_rows: list[dict] = []
    if out_jsonl.exists():
        for line in out_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing_rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    kept, suppressed = filter_distilled(props, existing_rows, asof, PROPOSAL_COOLDOWN_DAYS)
    props = kept
    # 输出时合并既有全量（含裁决历史）+ 真正的新提案，而不是只写本次蒸馏结果
    merged = list(existing_rows)
    seen_ids = {r.get("id") for r in merged}
    for p in props:
        if p.get("id") in seen_ids:
            continue
        merged.append(p)
        seen_ids.add(p.get("id"))
    props = merged
    jsonl, md = write_proposals(props, out_jsonl, Path(args.out) / "proposals.md")
    pending_n = sum(1 for p in props if p.get("status") == "pending")
    print(f"[distill] {asof} | 提案 {len(props)} 条 | -> {jsonl}")
    for p in props:
        print(f"  {p['id']} [{p['kind']}/{p['impact_estimate']}] {p['suggestion']}")
    if suppressed:
        print(f"⏳ 冷却期内抑制重复提案 {len(suppressed)} 条（人已裁决，"
              f"{PROPOSAL_COOLDOWN_DAYS} 天内不打扰）")
    print(f"⏳ 待裁决 {pending_n} 条 — 查看: carros_base.py propose list")
    return 0


def _list_proposals(jsonl) -> int:
    p = Path(jsonl)
    if not p.exists():
        print("无提案文件"); return 1
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    counts = Counter(r.get("status") for r in rows)
    print(f"# 提案 {len(rows)} 条 | 待裁决 {counts.get('pending', 0)} | "
          f"采纳 {counts.get('accepted', 0)} | 拒绝 {counts.get('rejected', 0)} | "
          f"搁置 {counts.get('deferred', 0)}")
    for d in rows:
        note = f" | note={d['human_note']}" if d.get("human_note") else ""
        by = d.get("decided_by") or d.get("rejected_by")
        who = f" | by={by}" if by else ""
        if d.get("status") in ("accepted", "rejected", "deferred") and not by:
            who = " | ⚠ 无归属裁决"
        print(f"  {d['id']} [{d['kind']}/{d['impact_estimate']}/{d['status']}] "
              f"{d['suggestion']}{who}{note}")
    return 0


def _stats(args) -> int:
    s = rsi_stats(Path(args.out) / "proposals.jsonl")
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    print("# RSI 指标（磁盘真相源）")
    print(f"M1 闭环数（采纳后落地）: {s['accepted']}")
    print(f"M2 转化率（采纳/已裁决）: {s['adoption_rate']:.1%} ({s['accepted']}/{s['decided']})")
    print(f"   待裁决 {s['pending']} | 拒绝 {s['rejected']} | 搁置 {s['deferred']} | 总 {s['total']}")
    if s["unverified_decisions"]:
        print(f"   ⚠ 无归属裁决 {s['unverified_decisions']} 条（历史遗留，无法追溯裁决人）")
    print(f"M5 体重: 代码 {s['weight']['code_lines']} 行（含测试）| "
          f"文档 {s['weight']['doc_lines']} 行")
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
            # 归属留痕（2026-10-24 RSI 修复）：谁、何时、通过什么渠道裁决。
            # 历史提案无此字段 → list/stats 显式标为「无归属裁决」，不再装作有记录。
            try:
                d["decided_by"] = (os.environ.get("CARROROS_DECIDED_BY")
                                   or getpass.getuser())
            except Exception:  # noqa: BLE001 — 取不到用户也不能吞掉裁决
                d["decided_by"] = "unknown"
            d["decided_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            d["decision_source"] = "propose_cli"
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
                   help="治理判据提案最小证据数（人判备注条数）")
    d.add_argument("--gov-trust", default=GOV_TRUST_MODE, choices=list(GOV_TRUST_MODES),
                   help="strict=非人判不计证据（默认）；inform=可提案但降级并标注成色")
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
    s = sub.add_parser("stats", help="RSI 三指标：采纳数 / 转化率 / 体重")
    s.add_argument("--out", default=DEFAULT_OUT)
    s.add_argument("--gate-pass", default=GATE_PASS_TELEMETRY)
    s.add_argument("--json", action="store_true")
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
    if args.cmd == "stats":
        return _stats(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
