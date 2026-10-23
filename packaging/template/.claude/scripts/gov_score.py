#!/usr/bin/env python3
"""gov_score.py — CarrorOS 治理效能可计算评分。

设计原则（2026-10-18 用户裁决）：
  · 每个维度一个明确公式，输入全部来自磁盘，不靠人拍脑袋
  · 测不出来的指标标 `confidence=low`，不假装精确
  · 输出同时给分数与原始指标，便于复核

用法:
  python3 .claude/scripts/gov_score.py [--json]

维度与公式（0–10）：
  1. frugality     少即是多    = 10 × (1 − 噪声率) × 门禁因子
  2. verification  验证大于承诺 = 10 × 真执行覆盖率
  3. zero_trust    零信任      = 5 × fail-closed 覆盖率 + 5 × 真执行覆盖率
  4. guardian      守护        = 10 × 控制率 × (旁路=0)
  5. documentation 文档        = 10 × (1 − 烂尾率)
  6. human         人本        = 10 / (1 + 每任务硬停次数)   [confidence=low：含测试流量]
  7. gain          增益优先    = 10 × min(1, 标注率 / 0.5)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude" / "scripts"
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HOOKS))

import jev_fit as jf  # noqa: E402
import verify_gate as vg  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _iter_jsonl(paths):
    for p in paths:
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass


def _audit_events():
    paths = list((ROOT / ".omc" / "state" / "audit").glob("*.jsonl"))
    paths += list((ROOT / ".omc" / "audit").glob("*.jsonl"))
    return list(_iter_jsonl(paths))


def _tokens():
    out = []
    for p in (ROOT / ".omc" / "tokens").rglob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        d["_path"] = str(p)
        out.append(d)
    return out


def _ledger_integrity() -> dict:
    """账本完整性：累计行数锚点 vs 当前行数 + 已署名删除量。

    未署名的删除会变成 unapproved_shrink，评分会把它们加回分母（不奖励删记录）。
    """
    expected = 0
    try:
        if jf.LEDGER_STATS.is_file():
            lines = [ln for ln in jf.LEDGER_STATS.read_text(encoding="utf-8", errors="ignore").splitlines()
                     if ln.strip()]
            if lines:
                expected = int(json.loads(lines[-1]).get("total") or 0)
    except (OSError, ValueError, json.JSONDecodeError):
        expected = 0
    actual = 0
    try:
        actual = sum(1 for ln in jf.LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines()
                     if ln.strip())
    except OSError:
        actual = 0
    signed = 0
    try:
        if jf.LEDGER_CORRECTIONS.is_file():
            for ln in jf.LEDGER_CORRECTIONS.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not ln.strip():
                    continue
                e = json.loads(ln)
                if e.get("approved_by"):
                    signed += int(e.get("count") or 0)
    except (OSError, ValueError, json.JSONDecodeError):
        signed = 0
    shrink = max(0, expected - (actual + signed))
    return {"expected_total": expected, "actual_total": actual,
            "signed_removals": signed, "unapproved_shrink": shrink,
            "ok": shrink == 0}


def _ts(value: str) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


# ── 1. 少即是多 ────────────────────────────────────────────────────
def frugality() -> dict:
    rows = jf.load_reviews(jf.LEDGER)
    pending = [r for r in rows if not r.get("human")]
    unjudgeable = [r for r in pending if not str(r.get("change") or "").strip()]
    noise = len(unjudgeable) / len(pending) if pending else 0.0
    gate = _load("pretool_gate_score", HOOKS / "pretool-gate.py")
    gate_count = len(gate._GATE_CORE)
    gate_factor = 1.0 if gate_count <= 15 else 15 / gate_count
    integ = _ledger_integrity()
    denom = integ["actual_total"] + integ["unapproved_shrink"]
    retention = integ["actual_total"] / denom if denom else 1.0
    return {"score": round(10 * (1 - noise) * gate_factor * retention, 2),
            "confidence": "high",
            "metrics": {"pending": len(pending), "unjudgeable": len(unjudgeable),
                        "noise_ratio": round(noise, 3), "gate_count": gate_count,
                        "retention": round(retention, 3),
                        "unapproved_shrink": integ["unapproved_shrink"]}}


# ── 2. 验证大于承诺 ────────────────────────────────────────────────
def _command_rules(days: int = 30) -> list[str]:
    """近 N 天任务里的 command 规则（衡量当前实践，不掺两个月前的一次性命令）。"""
    import time
    now = time.time()
    rules = []
    for p in list((ROOT / ".omc" / "tasks").rglob("plan.md")) + \
             list((ROOT / ".omc" / "archive").rglob("plan.md")):
        try:
            if now - p.stat().st_mtime > days * 86400:
                continue
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("- verify: command:"):
                    rules.append(line.split("command:", 1)[1].strip())
        except OSError:
            pass
    return rules


def _executable(rule: str) -> bool:
    import shlex
    work = rule
    if "&&" in rule and rule.split("&&")[0].strip().startswith("cd "):
        work = rule.split("&&", 1)[1].strip()
    if work.startswith(("python3 -c ", "python -c ")):
        try:
            parts = shlex.split(work)
        except ValueError:
            return False
        return len(parts) == 3 and parts[1] == "-c" and vg._safe_python_c(parts[2])
    return any(rx.match(work) for rx in vg._VERIFY_CMD_ALLOW) and \
        not vg._UNSAFE_SHELL.search(work)


def verification(strict: bool = False) -> dict:
    """默认公式：10 × (1 − 0.5 × 不可独立执行的规则占比)。

    strict=True：直接 10 × 真执行覆盖率（不可执行 = 全额扣分）。
    说明：外部路径 / curl / 任意代码属于「安全上不该执行」，默认按一半权重扣分。
    """
    rules = _command_rules()
    executable = [r for r in rules if _executable(r)]
    coverage = len(executable) / len(rules) if rules else 1.0
    unverifiable = 1 - coverage
    score = 10 * coverage if strict else 10 * (1 - 0.5 * unverifiable)
    return {"score": round(score, 2), "confidence": "high",
            "metrics": {"command_rules_30d": len(rules),
                        "truly_executable": len(executable),
                        "exec_coverage": round(coverage, 3),
                        "unverifiable_ratio": round(unverifiable, 3)}}


# ── 3. 零信任 ──────────────────────────────────────────────────────
_SECURITY_HINTS = ("sensitive", "governance", "secret", "injection", "action", "integrity")


def zero_trust() -> dict:
    gate = _load("pretool_gate_score2", HOOKS / "pretool-gate.py")
    names = [n for n, _ in gate._GATE_CORE]
    security = [n for n in names if any(h in n for h in _SECURITY_HINTS)]
    covered = [n for n in security if n in gate._FAIL_CLOSED_GATES]
    fc = len(covered) / len(security) if security else 1.0
    exec_cov = verification()["metrics"]["exec_coverage"]
    return {"score": round(5 * fc + 5 * exec_cov, 2), "confidence": "high",
            "metrics": {"security_gates": len(security), "fail_closed": len(covered),
                        "fail_closed_ratio": round(fc, 3), "exec_coverage": exec_cov}}


# ── 4. 守护 ────────────────────────────────────────────────────────
def guardian() -> dict:
    ev = _audit_events()
    blocked = sum(1 for e in ev if e.get("event_type") == "governance_write_block")
    approved = sum(1 for e in ev if e.get("event_type") == "governance_write_approved")
    bypass = sum(1 for e in ev if e.get("event_type") == "gate_bypassed")
    control = 1.0 if (blocked + approved) else 0.0
    score = 10 * control * (1.0 if bypass == 0 else 0.0)
    return {"score": round(score, 2), "confidence": "high",
            "metrics": {"blocked": blocked, "approved_via_ticket": approved,
                        "bypass_used": bypass}}


# ── 5. 文档 ────────────────────────────────────────────────────────
def documentation(strict: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    all_toks = _tokens()
    toks = [t for t in all_toks if t.get("status") == "active"]
    # 未署名 abandoned 不算“已处理”：否则 AI 可以靠批量弃置任务抬高分数。
    unapproved_abandoned = [
        t for t in all_toks
        if t.get("status") == "abandoned" and not t.get("abandoned_approved_by")]
    toks += unapproved_abandoned
    locked = 0
    open_toks = []
    for t in toks:
        p = Path(t.get("_path", ""))
        if p and p.with_suffix(p.suffix + ".lock").exists():
            locked += 1  # 有锁 = 仍在进行
            if not strict:
                continue
        open_toks.append(t)
    stale = 0
    for t in open_toks:
        sess = t.get("session") or {}
        ts = _ts(sess.get("updated_at") or sess.get("created_at") or "")
        if ts and (now - ts).days >= 7:
            stale += 1
    ratio = stale / len(open_toks) if open_toks else 0.0
    return {"score": round(10 * (1 - ratio), 2), "confidence": "high",
            "metrics": {"active": len(toks), "locked_in_progress": locked,
                        "unapproved_abandoned": len(unapproved_abandoned),
                        "active_unlocked": len(open_toks),
                        "stale_over_7d": stale, "stale_ratio": round(ratio, 3)}}


# ── 6. 人本 ────────────────────────────────────────────────────────
_ANON_TASK_IDS = {"", "none", "unknown"}


def human(strict: bool = False) -> dict:
    """硬停 / 任务数。

    默认只算能归属到真实任务的硬停。
    strict 计入全部事件，但扣除审计里显式记录的 test_pollution 修正量
    （修正以 append-only 事件追加，不改历史）。
    """
    now = datetime.now(timezone.utc)
    window = now - timedelta(days=30)
    events = [e for e in _audit_events()
              if (_ts(e.get("timestamp", "")) or now) >= window]
    stops = [e for e in events
             if e.get("event_type") == "redirect_escalated_to_hard_stop"]
    attested = {str(e.get("correction_ts")) for e in events
                if e.get("event_type") == "correction_attestation"
                and e.get("approved_by")}
    all_corrections = sum(
        int(e.get("count") or 0) for e in events
        if e.get("event_type") == "audit_correction"
        and e.get("correction") == "test_pollution")
    corrections = sum(
        int(e.get("count") or 0) for e in events
        if e.get("event_type") == "audit_correction"
        and e.get("correction") == "test_pollution"
        and (e.get("approved_by") or str(e.get("timestamp")) in attested))
    unsigned_ignored = max(0, all_corrections - corrections)
    if strict:
        counted = max(0, len(stops) - corrections)
    else:
        counted = sum(1 for e in stops
                      if str(e.get("task_id") or "").lower() not in _ANON_TASK_IDS)
    tasks = sum(
        1 for t in _tokens()
        if (_ts((t.get("session") or {}).get("created_at", "")) or window) >= window
    )
    rate = counted / tasks if tasks else 0.0
    return {"score": round(10 / (1 + rate), 2), "confidence": "medium",
            "metrics": {"hard_stops_counted_30d": counted,
                        "events_total_30d": len(stops),
                        "test_pollution_correction": corrections,
                        "unsigned_correction_ignored": unsigned_ignored,
                        "tasks_created_30d": tasks,
                        "stops_per_task": round(rate, 2),
                        "caveat": ("strict：全部事件 − 审计修正量" if strict
                                   else "默认：无 task_id 的事件视为测试/匿名流量，不计入")}}


def false_green() -> dict:
    """假绿测量：同一 (task, step) 先 VERIFIED、后又被 BLOCKED/REJECTED 的比例。

    这是「VERIFIED ≠ 正确」的代理指标，不并入七维平均，单独报告。
    """
    from collections import defaultdict
    seq: dict[tuple, list] = defaultdict(list)
    for e in _audit_events():
        if e.get("event_type") != "verify_decision":
            continue
        step = e.get("step")
        if step:
            seq[(e.get("task_id"), step)].append(e)
    total = 0
    contradicted = 0
    for evs in seq.values():
        verified = False
        flipped = False
        for e in evs:
            d = e.get("decision")
            if d == "VERIFIED":
                verified = True
            elif verified and d in ("BLOCKED", "REJECTED"):
                flipped = True
                break
        if verified:
            total += 1
            if flipped:
                contradicted += 1
    rate = contradicted / total if total else 0.0
    return {"score": round(10 * (1 - rate), 2), "confidence": "medium",
            "metrics": {"steps_verified": total, "steps_contradicted": contradicted,
                        "contradiction_rate": round(rate, 3)}}


# ── 7. 增益优先 ────────────────────────────────────────────────────
def gain(strict: bool = False) -> dict:
    """默认 = 无僵尸机制比例；strict = 人工标注率（学习信号覆盖率）。

    说明：僵尸率只测「死重」，不测正向 ROI；strict 用标注率要求人真的在看。
    """
    import glob
    import zombie_scan as z
    if strict:
        rows = jf.load_reviews(jf.LEDGER)
        labeled = sum(1 for r in rows if r.get("human"))
        integ = _ledger_integrity()
        effective = len(rows) + integ["unapproved_shrink"]
        ratio = labeled / effective if effective else 0.0
        return {"score": round(10 * min(1.0, ratio / 0.5), 2), "confidence": "high",
                "metrics": {"ledger": len(rows), "labeled": labeled,
                            "unapproved_shrink": integ["unapproved_shrink"],
                            "effective_total": effective,
                            "label_ratio": round(ratio, 3)}}
    scripts = glob.glob(str(SCRIPTS / "*.py"))
    zombies = z.find_zombies(str(ROOT), scan_roots=(".claude/scripts",))
    rate = len(zombies) / len(scripts) if scripts else 0.0
    return {"score": round(10 * (1 - rate), 2), "confidence": "medium",
            "metrics": {"scripts": len(scripts), "zombies": len(zombies),
                        "zombie_rate": round(rate, 3),
                        "caveat": "只测无死重，不测正向 ROI"}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="严格口径：全额扣分 / 计入测试流量 / 标注率")
    args = ap.parse_args()
    strict = args.strict
    dims = {
        "frugality": frugality(),
        "verification": verification(strict),
        "zero_trust": zero_trust(),
        "guardian": guardian(),
        "documentation": documentation(strict),
        "human": human(strict),
        "gain": gain(strict),
    }
    scores = [d["score"] for d in dims.values()]
    avg = round(sum(scores) / len(scores), 2)
    fg = false_green()
    integ = _ledger_integrity()
    if args.json:
        print(json.dumps({"dimensions": dims, "average": avg, "min": min(scores),
                          "false_green": fg, "ledger_integrity": integ},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"{'维度':<14}{'分数':>7}{'置信度':>8}  指标")
    for key, d in dims.items():
        print(f"{key:<14}{d['score']:>7}{d['confidence']:>8}  "
              f"{json.dumps(d['metrics'], ensure_ascii=False)}")
    print(f"\n平均: {avg} / 10   最低: {min(scores)}")
    print(f"假绿（不并入平均）: {fg['score']}  "
          f"{json.dumps(fg['metrics'], ensure_ascii=False)}")
    status = "OK" if integ["ok"] else f"⚠ 未署名删除 {integ['unapproved_shrink']} 行"
    print(f"账本完整性: {status}  {json.dumps(integ, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
