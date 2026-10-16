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
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_sweep as js  # noqa: E402

REGISTRY = SCRIPTS_DIR / "jev_rules.yaml"
LEDGER = ROOT / ".omc" / "state" / "jev" / "reviews.jsonl"
MAX_STATE_CHARS = 20000  # 1M 窗口时代单次判定预算：20K 字符 ≈ 5K token，足够判一个 commit


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
        f"判定对象：本次 commit 改动（{commit or '未指定'}）+ 交付物",
        f"changed_paths: {changed_paths[:20]}",
        f"交付物事实：\n{_delivery_facts(task_dir, step)}",
        f"--- diff（截断至 {max_chars} 字符）---",
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

    answers = js._aggregate_answers(raw.get("list") or [])
    for rule in jev_rules:
        rid = rule["rule_id"]
        ans = answers.get(rid) or {}
        row = {"rule_id": rid, "verdict": "不能判定"}
        if ans:
            row = js._row(rule)
            js._apply_answer(row, rule, ans)
        rec = {"review_id": f"v-{step}-{rid}", "recorded_at": _now(), "rule_id": rid,
               "registry_version": registry.get("registry_version", "unknown"),
               "source": "jev_verify_loop", "purpose": f"step {step} 验收",
               "change_fingerprint": commit or "", "verdict": row.get("verdict"),
               "jev_noul": row.get("jev_noul"), "jev_choice": row.get("jev_choice"),
               "jev_confidence": row.get("jev_confidence")}
        _append_ledger(rec)
        v = row.get("verdict")
        if v == "不符合":
            conf = row.get("jev_confidence") or row.get("jev_noul") or 0
            accept = float(rule.get("accept_at", 0.85))
            if conf >= accept:
                out["blocks"].append({"rule_id": rid, "verdict": v, "conf": conf,
                                      "evidence": row.get("evidence_refs")})
            else:
                out["low_confidence"].append({"rule_id": rid, "verdict": v, "conf": conf})
        elif v in ("符合", "不适用"):
            out["passed"].append(rid)

    out["judged"] = True
    out["usage"] = js._sum_usage(raw.get("list") or [])
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
