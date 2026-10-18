"""jev_verify_loop.py — JEV 验收 loop（SIA B1，2026-10-16 人类批准 KR）。

挂载点：verify_gate.py（Step 验证链）。职责：
  · 取「本次 commit 改动 + 本次 step 交付物事实」为判定对象
  · 规则集合一（jev_rules.yaml，deliverables 判据）中 judge_by=jev/hybrid 的
    规则送一次 JEV（≤1 次调用，批量问所有语义规则）
  · 降级纪律（fail-soft，永不阻塞 verify）：
      无 key / 超时 / HTTP 错 / 解析失败 → 记「降级：机械门为准」，exit 0
      低置信（choice 且 confidence < accept_at 阈值）→ 记「低置信→人类裁决」，exit 0
  · 语义规则判「不符合」且置信足 → 输出 BLOCK 建议 + 高亮（供 verify 汇总/人审）
  · 判定留痕 .omc/state/jev/reviews.jsonl（喂 jev_fit 拟合闭环）+ 遥测 calibration

用法（verify_gate 自动调用）：
    python3 .claude/scripts/jev_verify_loop.py --step <step> --token <token> \
        [--commit <sha>] [--max-chars 20000]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_sweep as js  # noqa: E402
import jev_fit as jf  # noqa: E402

REGISTRY = SCRIPTS_DIR / "jev_rules.yaml"
# 测试隔离：CARROROS_JEV_LEDGER 指向临时账本，避免 pytest 污染真实案例史。
LEDGER = Path(os.environ.get(
    "CARROROS_JEV_LEDGER", str(ROOT / ".omc" / "state" / "jev" / "reviews.jsonl")))
MAX_STATE_CHARS = 20000  # 1M 窗口时代单次判定预算：20K 字符 ≈ 5K token，足够判一个 commit


def gate_decision(verdict: str, conf: float, accept_at: float, tier: str) -> str:
    """校准分级门：判官的裁决权由「样本量等级」决定。

    jev-eval 官方口径：<50 条拒绝采纳、50–200 provisional、≥200 才可正式使用。
    因此只有 tier=ok 才允许硬阻断；其余一律降级为建议（人类裁决）。
    """
    if verdict not in ("不符合", "符合", "不适用"):
        return "pass"
    if verdict != "不符合":
        return "pass"
    if tier != "ok":
        return "advice"
    try:
        return "block" if float(conf) >= float(accept_at) else "advice"
    except (TypeError, ValueError):
        return "advice"


def _rule_tiers() -> dict[str, str]:
    """从案例账本取每条规则的校准等级；读不到时保守返回 unknown。"""
    try:
        rows = jf.load_reviews(LEDGER)
        return {rid: d["tier"] for rid, d in jf.analyze(rows).items()}
    except Exception:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_token(token_arg: str | None) -> dict:
    if not token_arg:
        return {}
    p = Path(token_arg)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _commit_change(commit: str | None) -> tuple[str, list[str]]:
    """取 commit 的 diff + 路径清单；失败返回空（降级）。"""
    import subprocess
    try:
        if not commit:
            return "", []
        r = subprocess.run(["git", "-C", str(ROOT), "show", "--format=%s", commit],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return "", []
        paths = subprocess.run(
            ["git", "-C", str(ROOT), "show", "--name-only", "--format=", commit],
            capture_output=True, text=True, timeout=30).stdout.split()
        return r.stdout[:MAX_STATE_CHARS], [p for p in paths if p.strip()]
    except Exception:
        return "", []


def _delivery_facts(task_dir: Path | None, step: str) -> str:
    """交付物事实（JEV 判的是产出物客观属性，不是意图）。"""
    facts: list[str] = []
    if task_dir and task_dir.is_dir():
        for name in ("research.md", "design.md", "plan.md", "verify-summary.md", "final-report.md"):
            f = task_dir / name
            if f.is_file():
                facts.append(f"{name}: 存在({f.stat().st_size}字节)")
            else:
                facts.append(f"{name}: 缺失")
    facts.append(f"step: {step}")
    return "\n".join(facts)


def _append_ledger(record: dict) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 留痕失败不阻塞


def _append_telemetry(record: dict) -> None:
    try:
        d = ROOT / ".omc" / "state" / "telemetry" / "calibration"
        d.mkdir(parents=True, exist_ok=True)
        with (d / f"{time.strftime('%Y%m')}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def run(step: str, token_arg: str | None, commit: str | None,
        max_chars: int = MAX_STATE_CHARS, model: str | None = None) -> dict:
    """执行一次 JEV 验收判定。返回结构化结果（供 verify_gate 打印汇总）。"""
    out = {"mode": "jev", "step": step, "judged": False, "degraded_reason": None,
           "blocks": [], "low_confidence": [], "passed": []}

    registry = js.load_registry(REGISTRY)
    _, jev_rules = js.split_by_judge(registry.get("rules", []))
    if not jev_rules:
        out["degraded_reason"] = "无语义规则（集合一为空或全脚本类）→ 机械门为准"
        return out

    token = _read_token(token_arg)
    task_dir = None
    tid = (token.get("session") or {}).get("id")
    if tid:
        task_dir = ROOT / ".omc" / "tasks" / tid
    change_text, changed_paths = _commit_change(commit)
    if commit and not change_text:
        out["degraded_reason"] = "commit 不可读 → 降级：机械门为准"
        _append_telemetry({"event_type": "jev_verify", "ts": _now(), "step": step,
                           "degraded": out["degraded_reason"]})
        return out

    state = "\n".join([
        f"主判定对象：本次代码改动的 diff（{commit or '未指定'}）",
        "文档（plan.md / executor.md / research.md）只作辅助证据，不作为主要判定依据。",
        f"changed_paths: {changed_paths[:20]}",
        f"辅助证据（交付物事实）：\n{_delivery_facts(task_dir, step)}",
        f"--- 代码 diff（截断至 {max_chars} 字符）---",
        change_text[:max_chars],
    ])
    js.assert_no_secret(state)  # 密钥不送 JEV（fail-closed）

    questions = js.build_questions(jev_rules, subject="本次改动")
    model = model or __import__("os").environ.get("CARROROS_JEV_MODEL", js.MODEL_FROZEN)
    client = js.JevClient()
    if not client.api_key:
        out["degraded_reason"] = "无 OPENROUTER_API_KEY → 降级：机械门为准（语义规则本次不判）"
        _append_telemetry({"event_type": "jev_verify", "ts": _now(), "step": step,
                           "degraded": out["degraded_reason"]})
        return out

    raw = client.judge(state, questions, model)
    if "_error" in raw or "_http_error" in raw:
        out["degraded_reason"] = f"JEV 调用失败：{raw.get('_error') or raw.get('_action')} → 降级：机械门为准"
        _append_telemetry({"event_type": "jev_verify", "ts": _now(), "step": step,
                           "degraded": out["degraded_reason"]})
        return out

    # 判官模型版本留痕（漂移追溯：同一个 registry_version 可能对应不同模型快照）
    judge_model = raw.get("model") if isinstance(raw, dict) else None
    # 接口适配：单次响应 = {"answers": {rule_id: ...}, "usage": ...}（list 是多采样聚合的输入形态）
    if "list" not in raw and "answers" in raw:
        raw = {"list": [raw]}
    answers = js._aggregate_answers(raw.get("list") or [])
    n_answered = sum(1 for r in jev_rules if answers.get(r["rule_id"]))
    if n_answered == 0 and len(jev_rules) > 0:
        # 模型应答了但答案结构与规则对不上（接口/判据漂移）——不写「不能判定」假账本
        out["degraded_reason"] = f"JEV 应答 {len(answers)} 项但 {len(jev_rules)} 条规则无匹配 → 降级：机械门为准"
        _append_telemetry({"event_type": "jev_verify", "ts": _now(), "step": step,
                           "degraded": out["degraded_reason"]})
        return out
    tiers = _rule_tiers()
    # 2026-10-18 去重：同一 (rule, commit) 的多步验收不重复入账。
    # 否则一次任务跑 6 个 step 就会把同一份 diff 写 6 遍，稀释标注率。
    existing_pending = {
        (r.get("rule_id"), r.get("change_fingerprint"))
        for r in jf.load_reviews(LEDGER) if not r.get("human")
    }
    for rule in jev_rules:
        rid = rule["rule_id"]
        ans = answers.get(rid) or {}
        row = {"rule_id": rid, "verdict": "不能判定"}
        if ans:
            row = js._row(rule)
            js._apply_answer(row, rule, ans)
        rec = {"review_id": f"v-{step}-{rid}", "recorded_at": _now(), "rule_id": rid,
               "registry_version": registry.get("registry_version", "unknown"),
               "jev_model": judge_model,
               "source": "jev_verify_loop", "purpose": f"step {step} 验收",
               "change_fingerprint": commit or "", "verdict": row.get("verdict"),
               "jev_noul": row.get("jev_noul"), "jev_choice": row.get("jev_choice"),
               "jev_confidence": row.get("jev_confidence")}
        # 2026-10-18 降噪：没有 diff 的验收不写账本；同 (rule, commit) 只写一次。
        if change_text.strip() and (rid, commit or "") not in existing_pending:
            _append_ledger(rec)
            existing_pending.add((rid, commit or ""))
        v = row.get("verdict")
        conf = row.get("jev_confidence") or row.get("jev_noul") or 0
        accept = float(rule.get("accept_at", 0.85))
        tier = tiers.get(rid, "unknown")
        decision = gate_decision(v, conf, accept, tier)
        if decision == "block":
            out["blocks"].append({"rule_id": rid, "verdict": v, "conf": conf,
                                  "tier": tier, "evidence": row.get("evidence_refs")})
        elif decision == "advice":
            out["low_confidence"].append({"rule_id": rid, "verdict": v, "conf": conf,
                                          "tier": tier})
        elif v in ("符合", "不适用"):
            out["passed"].append(rid)

    out["judged"] = True
    out["usage"] = js._sum_usage(raw.get("list") or []) or (raw.get("usage") or {"input_tokens": 0, "output_tokens": 0, "cost": 0.0})
    if all(v == 0 for v in (out["usage"].get("input_tokens") or 0, out["usage"].get("output_tokens") or 0)) and raw.get("usage"):
        out["usage"] = raw["usage"]
    _append_telemetry({"event_type": "jev_verify", "ts": _now(), "step": step,
                       "judged": True, "blocks": len(out["blocks"]),
                       "low_confidence": len(out["low_confidence"]),
                       "passed": len(out["passed"]), "usage": out["usage"]})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="JEV 验收 loop（verify 挂载，fail-soft）")
    ap.add_argument("--step", required=True)
    ap.add_argument("--token", default=None)
    ap.add_argument("--commit", default=None,
                    help="判定对象 commit；缺省取 token.delivery.commit / HEAD")
    ap.add_argument("--max-chars", type=int, default=MAX_STATE_CHARS)
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)

    # 密钥兜底：CC 会话会注入 settings.local.json 的 env；独立终端/脚本调用时
    # 环境里可能没有 —— 从 settings.local.json 读一次（不修改该文件、不打印值）。
    import os
    if not os.environ.get("OPENROUTER_API_KEY"):
        for cand in (ROOT / ".claude" / "settings.local.json",
                     ROOT / ".claude" / "settings_ds.json"):
            try:
                envs = json.loads(cand.read_text()).get("env") or {}
                k = envs.get("OPENROUTER_API_KEY") or ""
                if not k:
                    k = (json.loads(cand.read_text()) or {}).get("OPENROUTER_API_KEY", "")
                if k:
                    os.environ["OPENROUTER_API_KEY"] = k
                    break
            except Exception:
                continue
    token = _read_token(args.token)
    commit = args.commit or (token.get("delivery") or {}).get("commit")
    if not commit:
        import subprocess
        try:
            commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True, timeout=10).stdout.strip() or None
        except Exception:
            commit = None

    result = run(args.step, args.token, commit, args.max_chars, args.model)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # fail-soft：本模块永不以非零码阻塞 verify；block 是建议，由人/verify 汇总裁决
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
