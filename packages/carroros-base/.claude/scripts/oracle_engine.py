#!/usr/bin/env python3
"""
oracle_engine.py — Oracle/Meta-Oracle 高阶复核裁决引擎

Usage:
    python3 .omc/scripts/oracle_engine.py <review_pack_path>

7.md §6: L2 Model-pass-curve (7 维度)
7.md §7: L3 Multi-Judge 投票 (Safety/Correctness/Architecture)
7.md §8: Meta-Oracle 归一裁决

Output: JSON with decision/reason/score fields
"""

import json
import sys
import math
from pathlib import Path
from datetime import datetime, timezone


# ── L2 Pass-curve 评分器 ──
# 7.md §6: 7 个固定维度

SCORE_DIMENSIONS = [
    "evidence_coverage",
    "scope_integrity",
    "regression_risk",
    "security_risk",
    "contract_preservation",
    "failure_resolution",
    "archive_readiness",
]

CRITICAL_FLOOR = 60
ACCEPT_AVERAGE = 80
WARN_AVERAGE = 65


def _calc_evidence_coverage(pack: dict) -> dict:
    """证据覆盖度 (0-100) — 对齐铁律 2"""
    evidence = pack.get("verify_evidence", [])
    if not evidence:
        return {"score": 0, "detail": "no verify evidence"}
    
    # 每个 evidence_level：E3=100, E2=70, E1=40
    scores = []
    for e in evidence:
        lvl = e.get("evidence_level", "E1")
        if lvl == "E3":
            scores.append(100)
        elif lvl == "E2":
            scores.append(70)
        else:
            scores.append(40)
    
    avg = sum(scores) / len(scores)
    
    # 检查是否有 exit_code 证据
    has_command = any(e.get("type") == "command" for e in evidence)
    has_test = any("test" in e.get("source", "").lower() for e in evidence)
    
    bonus = 0
    if has_command:
        bonus += 5
    if has_test:
        bonus += 10
    
    final = min(100, avg + bonus)
    return {"score": round(final, 1), "detail": f"{len(evidence)} evidence items, avg_level={round(avg)}"}


def _calc_scope_integrity(pack: dict) -> dict:
    """范围完整性 (0-100) — 对齐铁律 3"""
    scope = pack.get("scope", [])
    completed = pack.get("completed_steps", [])
    
    if not scope and not completed:
        return {"score": 100, "detail": "no scope constraints"}
    
    # 检查是否所有 scope 文件都被覆盖
    files_changed = pack.get("diff_summary", {}).get("files_changed", 0)
    risk_files = pack.get("diff_summary", {}).get("risk_files", [])
    
    if risk_files:
        # 有风险文件时仅检查已知 scope 覆盖
        score = max(60, 100 - len(risk_files) * 10)
    elif files_changed == 0:
        score = 100
    else:
        score = max(70, 100 - files_changed * 5)
    
    return {"score": round(score, 1), "detail": f"{len(scope)} scope items, {len(completed)} steps"}


def _calc_regression_risk(pack: dict) -> dict:
    """回归风险 (0-100) — 分数越高风险越低"""
    diff = pack.get("diff_summary", {})
    insertions = diff.get("insertions", 0)
    deletions = diff.get("deletions", 0)
    files_changed = diff.get("files_changed", 0)
    
    if files_changed == 0:
        return {"score": 100, "detail": "no diff changes"}
    
    # 大规模变更 = 高回归风险
    total = insertions + deletions
    file_penalty = max(0, files_changed - 3) * 5
    size_penalty = 0
    if total > 500:
        size_penalty = 20
    elif total > 200:
        size_penalty = 10
    
    base = 100 - file_penalty - size_penalty
    
    # 额外惩罚：配置/依赖变更
    risk_files = diff.get("risk_files", [])
    for rf in risk_files:
        if any(k in rf.lower() for k in ["config", "dep", "package", "lock"]):
            base -= 10
    
    return {"score": round(max(0, base), 1), "detail": f"{files_changed} files, {total} line changes"}


def _calc_security_risk(pack: dict) -> dict:
    """安全风险 (0-100) — 对齐铁律 4"""
    risk_hints = pack.get("risk_hints", [])
    
    # 硬扣分项
    score = 100
    hints_lower = [h.lower() for h in risk_hints]
    
    if "auth_change" in hints_lower:
        score -= 30
    if "permission" in hints_lower:
        score -= 25
    if "production" in hints_lower:
        score -= 20
    if "cross_module" in hints_lower:
        score -= 10
    
    # 检查 diff 中是否有 .env / credential 类文件
    diff = pack.get("diff_summary", {})
    risk_files = diff.get("risk_files", [])
    for rf in risk_files:
        if any(k in rf.lower() for k in [".env", "credential", "secret", "key", "token"]):
            score -= 40
    
    return {"score": round(max(0, score), 1), "detail": f"risk_hints: {risk_hints}"}


def _calc_contract_preservation(pack: dict) -> dict:
    """契约保持 (0-100)"""
    constraints = pack.get("user_constraints", [])
    
    if not constraints:
        return {"score": 90, "detail": "no explicit constraints"}
    
    # 有约束时默认保守给分
    score = max(70, 100 - len(constraints) * 5)
    
    return {"score": round(score, 1), "detail": f"{len(constraints)} constraints"}


def _calc_failure_resolution(pack: dict) -> dict:
    """失败解决 (0-100)"""
    failures = pack.get("recent_failures", [])
    
    if not failures:
        return {"score": 100, "detail": "no recent failures"}
    
    resolved = sum(1 for f in failures if f.get("covered_by"))
    total = len(failures)
    
    if total == 0:
        return {"score": 100, "detail": "no failures"}
    
    ratio = resolved / total
    score = ratio * 100
    
    return {"score": round(score, 1), "detail": f"{resolved}/{total} failures resolved"}


def _calc_archive_readiness(pack: dict) -> dict:
    """归档就绪度 (0-100)"""
    trigger = pack.get("trigger", "")
    completed = pack.get("completed_steps", [])
    
    if trigger == "final_acceptance":
        # 最终归档需要步阶梯完成
        if not completed:
            return {"score": 20, "detail": "no completed steps for final_acceptance"}
        score = min(100, len(completed) * 20)
    else:
        score = 80
    
    return {"score": round(score, 1), "detail": f"trigger={trigger}, {len(completed)} steps"}


def run_l2_pass_curve(pack: dict) -> dict:
    """L2 Model-pass-curve — 7.md §6: 7 维度结构化评分"""
    calculators = {
        "evidence_coverage": _calc_evidence_coverage,
        "scope_integrity": _calc_scope_integrity,
        "regression_risk": _calc_regression_risk,
        "security_risk": _calc_security_risk,
        "contract_preservation": _calc_contract_preservation,
        "failure_resolution": _calc_failure_resolution,
        "archive_readiness": _calc_archive_readiness,
    }
    
    scores = {}
    total = 0.0
    critical_issues = []
    
    for dim, calc_fn in calculators.items():
        result = calc_fn(pack)
        scores[dim] = result["score"]
        total += result["score"]
        
        if result["score"] < CRITICAL_FLOOR:
            critical_issues.append({
                "dimension": dim,
                "score": result["score"],
                "detail": result["detail"],
            })
    
    average = round(total / len(calculators), 2)
    
    return {
        "scores": scores,
        "average": average,
        "critical_issues": critical_issues,
    }


# ── L3 Multi-Judge 投票 ──
# 7.md §7: Safety / Correctness / Architecture

def run_l3_multi_judge(pack: dict, l2_result: dict) -> list:
    """L3 Multi-Judge — 基于 L2 评分推导 Judge 投票"""
    scores = l2_result["scores"]
    judges = []
    
    # Judge-A: Safety — 基于 security_risk + 检查高风险 hint
    security = scores.get("security_risk", 100)
    risk_hints = [h.lower() for h in pack.get("risk_hints", [])]
    
    if security < 60:
        vote = "REJECT"
        reason = "security_risk below critical floor"
    elif security < 75 or any(h in risk_hints for h in ["auth_change", "production", "permission"]):
        vote = "WARN"
        reason = "elevated security risk or sensitive risk hint"
    else:
        vote = "ACCEPT"
        reason = "no significant security concern"
    
    judges.append({
        "judge": "Safety",
        "vote": vote,
        "reason": reason,
        "required_action": "review security impact" if vote != "ACCEPT" else None,
    })
    
    # Judge-B: Correctness — 基于 evidence + regression
    evidence = scores.get("evidence_coverage", 0)
    regression = scores.get("regression_risk", 100)
    
    if evidence < 60 or regression < 60:
        vote = "REJECT"
        reason = "insufficient evidence or high regression risk"
    elif evidence < 75 or regression < 75:
        vote = "WARN"
        reason = "evidence or regression coverage below threshold"
    else:
        vote = "ACCEPT"
        reason = "evidence and regression acceptable"
    
    judges.append({
        "judge": "Correctness",
        "vote": vote,
        "reason": reason,
        "required_action": "strengthen test coverage" if vote != "ACCEPT" else None,
    })
    
    # Judge-C: Architecture — 基于 scope + contract
    scope = scores.get("scope_integrity", 100)
    contract = scores.get("contract_preservation", 100)
    
    if scope < 60 or contract < 60:
        vote = "REJECT"
        reason = "scope violation or contract break"
    elif scope < 75 or contract < 75:
        vote = "WARN"
        reason = "architectural concerns in scope or contract"
    else:
        vote = "ACCEPT"
        reason = "architecture consistent"
    
    judges.append({
        "judge": "Architecture",
        "vote": vote,
        "reason": reason,
        "required_action": "review scope boundaries" if vote != "ACCEPT" else None,
    })
    
    return judges


# ── Meta-Oracle 归一裁决 ──
# 7.md §8: 冲突归一规则

META_RULES = {
    "accept_accept": "ACCEPT",
    "accept_warn": "WARN",
    "warn_accept": "WARN",
    "warn_warn": "WARN",
}


def run_meta_oracle(l2_result: dict, judges: list) -> dict:
    """Meta-Oracle 归一裁决 — 7.md §8"""
    l2_decision = _l2_decision(l2_result)
    l3_vote_map = {j["judge"]: j["vote"] for j in judges}
    
    # 任一安全类 REJECT → 不允许自动覆盖
    safety_vote = l3_vote_map.get("Safety", "")
    if safety_vote == "REJECT":
        return {
            "decision": "REJECT",
            "reason": "l3_reject:Safety",
            "required_action": "obtain human security approval",
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # 其他 REJECT
    if any(v == "REJECT" for v in l3_vote_map.values()):
        reject_judges = [j for j in judges if j["vote"] == "REJECT"]
        return {
            "decision": "REJECT",
            "reason": f"l3_reject:{','.join(j['judge'] for j in reject_judges)}",
            "required_action": "rerun VerifyGate or repair evidence",
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # L2 决定
    if l2_decision == "REJECT":
        return {
            "decision": "REJECT",
            "reason": "l2_reject",
            "required_action": "rerun VerifyGate or repair evidence",
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    if l2_decision == "ESCALATE":
        return {
            "decision": "ESCALATE",
            "reason": "l2_escalate",
            "required_action": "human decision required",
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # 两个及以上 WARN
    warn_count = sum(1 for v in l3_vote_map.values() if v == "WARN")
    if warn_count >= 2:
        return {
            "decision": "WARN",
            "reason": "l3_multi_warn",
            "required_action": "address all warnings before next phase",
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # 一个 WARN + 两个 ACCEPT → 由 Meta-Oracle 裁断
    if warn_count == 1:
        if l2_decision == "ACCEPT":
            decision = "ACCEPT"
            reason = "l2_accept_with_notes"
        else:
            decision = "WARN"
            reason = "l2_or_l3_warn"
        return {
            "decision": decision,
            "reason": reason,
            "required_action": None,
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # 三个 ACCEPT
    if l2_decision == "ACCEPT":
        return {
            "decision": "ACCEPT",
            "reason": "l2_l3_accept",
            "required_action": None,
            "l2_decision": l2_decision,
            "l3_votes": l3_vote_map,
        }
    
    # L2 WARN + L3 全 ACCEPT → WARN
    return {
        "decision": "WARN",
        "reason": "l2_warn",
        "required_action": "address l2 warnings before proceeding",
        "l2_decision": l2_decision,
        "l3_votes": l3_vote_map,
    }


def _l2_decision(l2_result: dict) -> str:
    """从 L2 pass-curve 推导裁决"""
    average = l2_result["average"]
    critical = l2_result["critical_issues"]
    
    if critical:
        return "REJECT"
    
    if average >= ACCEPT_AVERAGE:
        return "ACCEPT"
    
    if average >= WARN_AVERAGE:
        return "WARN"
    
    return "REJECT"


# ── 主入口 ──

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: oracle_engine.py <review_pack_path>"}))
        return 1
    
    pack_path = Path(sys.argv[1])
    if not pack_path.exists():
        print(json.dumps({"error": f"Review pack not found: {pack_path}"}))
        return 1
    
    pack = json.loads(pack_path.read_text())
    
    # L2 pass-curve
    l2 = run_l2_pass_curve(pack)
    
    # L3 Multi-Judge
    judges = run_l3_multi_judge(pack, l2)
    
    # Meta-Oracle 归一
    meta = run_meta_oracle(l2, judges)
    
    # 构建输出
    output = {
        "decision": meta["decision"],
        "reason": meta["reason"],
        "trigger": pack.get("trigger", "unknown"),
        "phase": pack.get("phase", "execute"),
        "l2_average": l2["average"],
        "l2_scores": l2["scores"],
        "l2_critical_issues": l2["critical_issues"],
        "l3_votes": meta["l3_votes"],
        "required_action": meta.get("required_action"),
        "residual_risk": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # 构建 residual_risk
    for issue in l2["critical_issues"]:
        output["residual_risk"].append(
            f"{issue['dimension']} score={issue['score']}: {issue['detail']}"
        )
    for j in judges:
        if j["vote"] != "ACCEPT":
            output["residual_risk"].append(
                f"{j['judge']}: {j['reason']}"
            )
    
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
