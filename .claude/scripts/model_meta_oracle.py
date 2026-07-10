#!/usr/bin/env python3
"""
model_meta_oracle.py — 动态聚合 Meta Oracle。

接收 static + runtime 两个子 Oracle 的裁决，按风险策略做动态融合：
- 策略路由决定权重和门禁
- 跨 Oracle 的 Finding 合并去重
- 同质化对抗：如果两个 agent 的 findings 完全一致，标记为"疑似同质化"附加一致性惩罚
- 降级决策：LLM 不可用时标记 degraded 但不阻塞

用法：
    python3 .claude/scripts/model_meta_oracle.py aggregate --task-id <ID> [--policy <policy>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from carros_oracle_base import (
    Evidence as _Evidence,
    OracleReview, Finding, Severity, RiskType,
    RiskPolicy, resolve_risk_policy, policy_to_gate_config,
    write_oracle_verdict,
)

ORACLE_NAME = "model_meta"
VERDICT_DIR = Path(".omc/state/model-oracle-verdicts")
PROMPT_VERSION = "model_meta_v1"
_PROXY_MODEL = __import__("carros_oracle_base").PROXY_MODEL

RISK_ORDER: dict[str, int] = {"critical": 40, "high": 30, "medium": 20, "low": 10, "info": 5}
VERDICT_ORDER: dict[str, int] = {"REJECT": 30, "ESCALATE": 25, "DEGRADED": 20, "ADVISORY": 10, "ACCEPT": 0}


# ═══════════════════════════════════════════════
# 加载子 Oracle 裁决
# ═══════════════════════════════════════════════

def load_oracle_verdict(task_id: str, oracle_name: str) -> dict | None:
    """从 model-oracle-verdicts 加载最新裁决"""
    latest = VERDICT_DIR / task_id / "latest.json"
    if not latest.exists():
        return None
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        if data.get("agent") == oracle_name:
            return data
        # fallback: glob 找
        for f in sorted(VERDICT_DIR.glob(f"{task_id}/*-{oracle_name}.json"), reverse=True):
            return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return None


def load_fallback_verdict(task_id: str, old_verdict_dir: str) -> dict | None:
    """从旧版 verdict 目录加载（降级兼容）"""
    base = Path(".omc/state") / old_verdict_dir
    latest = base / task_id / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════
# Finding 融合
# ═══════════════════════════════════════════════

def merge_findings(static_findings: list[dict], runtime_findings: list[dict]) -> list[Finding]:
    """合并两个 Oracle 的 findings，去重、标注冲突（S7: 增强去重签名）"""
    merged: list[Finding] = []
    seen_signatures: set[str] = set()

    all_items = [("model_static", f) for f in static_findings] + \
                [("model_runtime", f) for f in runtime_findings]

    for source, item in all_items:
        # sig: risk_type + evidence location + evidence content hash（全量，不截断50）
        evidence_locs = [e.get("location", "") for e in item.get("evidence", [])]
        evidence_texts = [e.get("content", "") for e in item.get("evidence", [])]
        sig = f"{source}:{item.get('risk_type')}:{'|'.join(evidence_locs)}:{hashlib.sha256('|'.join(evidence_texts).encode()).hexdigest()[:16]}"

        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        finding = _dict_to_finding(source, item)
        merged.append(finding)

    return merged


def _dict_to_finding(source: str, item: dict) -> Finding:
    """把 dict 转成 Finding 对象（兼容 model_static/model_runtime 的输出格式）"""
    sev = Severity.LOW
    try:
        sev = Severity(item.get("severity", "low").lower())
    except ValueError:
        pass

    rt = RiskType.UNKNOWN
    try:
        rt = RiskType(item.get("risk_type", "unknown").lower().replace(" ", "_"))
    except ValueError:
        pass

    evidence = []
    for ev in item.get("evidence", []):
        evidence.append(_Evidence(
            type=ev.get("type", "text"),
            location=ev.get("location", ""),
            content=ev.get("content", ""),
        ))

    return Finding(
        oracle=source,
        severity=sev,
        confidence=float(item.get("confidence", 0.5)),
        risk_type=rt,
        evidence=evidence,
        reason=item.get("reason", ""),
        recommendation=item.get("recommendation", ""),
    )


def detect_homogenization(
    static: dict | None,
    runtime: dict | None,
) -> tuple[bool, float]:
    """
    检测同质化——如果两个 agent 的输出极端相似，降低一致性权重。

    Returns:
        (is_homogenized: bool, penalty: float)
    """
    if not static or not runtime:
        return False, 0.0

    s_findings = static.get("findings", [])
    r_findings = runtime.get("findings", [])

    if not s_findings or not r_findings:
        return False, 0.0

    # 检查 risk_type 分布是否完全一致
    s_types = sorted(f.get("risk_type", "") for f in s_findings)
    r_types = sorted(f.get("risk_type", "") for f in r_findings)

    if s_types == r_types:
        return True, 2.0  # 高度同质化

    # 检查重叠度
    s_set = set(s_types)
    r_set = set(r_types)
    if not s_set or not r_set:
        return False, 0.0

    overlap = len(s_set & r_set) / max(len(s_set), len(r_set))
    if overlap > 0.8:
        return True, 1.0

    return False, 0.0


def detect_contradiction(static: dict | None, runtime: dict | None) -> bool:
    """检测两个子 Oracle 是否存在裁决冲突"""
    if not static or not runtime:
        return False

    s_v = static.get("verdict", "ACCEPT")
    r_v = runtime.get("verdict", "ACCEPT")

    # REJECT vs ACCEPT 极端冲突
    if (s_v == "REJECT" and r_v == "ACCEPT") or (s_v == "ACCEPT" and r_v == "REJECT"):
        return True
    return False


# ═══════════════════════════════════════════════
# 聚合决策
# ═══════════════════════════════════════════════

def aggregate_verdict(task_id: str, policy: str | None = None) -> OracleReview:
    """聚合两个子 Oracle 的裁决，输出最终 Meta Oracle 裁决"""

    # 1) 加载子裁决
    static = load_oracle_verdict(task_id, "model_static")
    runtime = load_oracle_verdict(task_id, "model_runtime")

    # 如果没有 LLM 版本，尝试加载 fallback 版本的裁决
    if static is None:
        static = load_fallback_verdict(task_id, "static-oracle-verdicts")
    if runtime is None:
        runtime = load_fallback_verdict(task_id, "runtime-oracle-verdicts")

    # 2) 确定策略
    if policy:
        try:
            resolved_policy = RiskPolicy(policy)
        except ValueError:
            resolved_policy = RiskPolicy.BALANCED
    else:
        # 从 static/runtime 裁决推断策略
        task_hint = {}
        if static:
            task_hint["description"] = str(static.get("task_id", ""))
        resolved_policy = resolve_risk_policy(task_hint)

    gate = policy_to_gate_config(resolved_policy)

    # 3) 获取 findings
    static_findings = (static or {}).get("findings", [])
    runtime_findings = (runtime or {}).get("findings", [])

    # 4) 检测同质化
    homogenized, homogeneity_penalty = detect_homogenization(static, runtime)

    # 5) 检测冲突
    contradictory = detect_contradiction(static, runtime)

    # 6) 计算动态分数
    static_score = float((static or {}).get("score", 5.0))
    runtime_score = float((runtime or {}).get("score", 5.0))

    # 动态权重
    if resolved_policy == RiskPolicy.SECURITY_STRICT:
        sw, rw, cw = 0.6, 0.3, 0.1  # 静态偏重
    elif resolved_policy == RiskPolicy.RUNTIME_STRICT:
        sw, rw, cw = 0.3, 0.6, 0.1  # 运行时偏重
    elif resolved_policy == RiskPolicy.FAST_PATH:
        sw, rw, cw = 1.0, 0.0, 0.0  # 仅静态
    else:
        sw, rw, cw = 0.45, 0.45, 0.1  # 均衡

    consistency = 10.0
    if static and runtime:
        s_v = static.get("verdict", "")
        r_v = runtime.get("verdict", "")
        if s_v == r_v:
            consistency = 10.0
        else:
            consistency = 5.0  # 不一致减半

    # 同质化惩罚
    if homogenized:
        consistency = max(0.0, consistency - homogeneity_penalty)

    # 7) 最终分数
    final_score = round(static_score * sw + runtime_score * rw + consistency * cw, 2)

    # 8) 风险定级
    risks = []
    if static:
        risks.append(static.get("risk", "LOW"))
    if runtime:
        risks.append(runtime.get("risk", "LOW"))
    if "CRITICAL" in risks:
        final_risk = "CRITICAL"
    elif "HIGH" in risks:
        final_risk = "HIGH"
    elif "MEDIUM" in risks:
        final_risk = "MEDIUM"
    else:
        final_risk = "LOW"

    # 9) 合并 findings
    merged_findings = merge_findings(static_findings, runtime_findings)

    # 10) 最终裁决
    findings_verdicts = []
    if static:
        findings_verdicts.append(static.get("verdict", ""))
    if runtime:
        findings_verdicts.append(runtime.get("verdict", ""))

    missing_oracles = []
    if static is None:
        missing_oracles.append("model_static")
    if runtime is None:
        missing_oracles.append("model_runtime")

    is_degraded = (static is None) or (runtime is None) or homogenized
    degraded_reason_parts = []
    if static is None:
        degraded_reason_parts.append("static_unavailable")
    if runtime is None:
        degraded_reason_parts.append("runtime_unavailable")
    if homogenized:
        degraded_reason_parts.append("homogenization_detected")

    # ═══════════════════════════════════════════════
    # 最终裁决（S4/S6: 硬门禁优先, S5: 降级 not ACCEPT）
    # ═══════════════════════════════════════════════
    # 规则 1: 任何验证过的 critical finding → REJECT
    verified_critical = any(
        f.get("severity") == "critical" and f.get("verified", False)
        for f in static_findings + runtime_findings
    )
    if verified_critical and gate["critical_block"]:
        final_verdict = "REJECT"
        decision = "block"
    # 规则 2: required oracle 缺失且 llm_required → REJECT
    elif gate["llm_required"] and missing_oracles:
        final_verdict = "REJECT"
        decision = "block"
        if "static_unavailable" not in degraded_reason_parts and "model_static" in missing_oracles:
            degraded_reason_parts.append("static_required_missing")
        if "runtime_unavailable" not in degraded_reason_parts and "model_runtime" in missing_oracles:
            degraded_reason_parts.append("runtime_required_missing")
    # 规则 3: 极端冲突（一个 ACCEPT + 一个 REJECT）→ ESCALATE
    elif contradictory:
        final_verdict = "ESCALATE"
        decision = "review"
    # 规则 4: 降级 + llm_required → ESCALATE（不能 ACCEPT）
    elif is_degraded and gate.get("llm_required", False):
        final_verdict = "ESCALATE"
        decision = "review"
    # 规则 5: 降级 + SECURITY_STRICT → DEGRADED + review
    elif is_degraded and resolved_policy == RiskPolicy.SECURITY_STRICT:
        final_verdict = "DEGRADED"
        decision = "degraded_block"
    # 规则 6: 降级 + ACCEPT 导向 → DEGRADED + degraded_allow
    elif is_degraded and not gate.get("llm_required", False):
        final_verdict = "DEGRADED"
        decision = "degraded_allow"
    # 规则 7: 同质化告警
    elif homogenized and resolved_policy in (RiskPolicy.SECURITY_STRICT, RiskPolicy.RUNTIME_STRICT):
        final_verdict = "ADVISORY"
        decision = "review"
    # 规则 8: 分数门禁（单调规则：score 只细化 severity 不覆盖）
    elif "ADVISORY" in findings_verdicts:
        final_verdict = "ADVISORY"
        decision = "review"
    elif final_score < 8.0:
        final_verdict = "ADVISORY"
        decision = "review"
    else:
        final_verdict = "ACCEPT"
        decision = "allow"

    return OracleReview(
        decision=decision,
        verdict=final_verdict,
        risk=final_risk,
        score=final_score,
        findings=merged_findings,
        degraded=is_degraded,
        degraded_reason=";".join(degraded_reason_parts) if degraded_reason_parts else "",
        missing_oracles=missing_oracles,
        model=_PROXY_MODEL,
        prompt_version=PROMPT_VERSION,
    )


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

def handle_aggregate(args: argparse.Namespace) -> int:
    review = aggregate_verdict(args.task_id, args.policy)
    write_oracle_verdict(args.task_id, ORACLE_NAME, review)

    print(json.dumps(review.to_dict(), ensure_ascii=False, indent=2))
    print(f"\n[meta_oracle] verdict={review.verdict} score={review.score} risk={review.risk} decision={review.decision}")

    codes = {"ACCEPT": 0, "ADVISORY": 1, "REJECT": 2, "ESCALATE": 3, "DEGRADED": 4}
    return codes.get(review.verdict, 4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Model Meta Oracle — 动态聚合双审裁决")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("aggregate")
    p.add_argument("--task-id", required=True)
    p.add_argument("--policy", choices=[p.value for p in RiskPolicy], default=None)

    args = parser.parse_args()
    return handle_aggregate(args)


if __name__ == "__main__":
    raise SystemExit(main())
