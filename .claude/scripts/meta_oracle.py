#!/usr/bin/env python3
"""
meta_oracle.py — Mate Oracle (重构版)

职责：
- 元级审核：聚合 static + runtime 裁决（从 oracle_agent.py 的输出文件读取）
- 对抗性测试：同质化检测、裁决冲突检测
- 组合使用：可独立调用 CLI，也可被脚本 import 后调用
- 可单独使用，也可与 oracle_agent.py 组合

Usage:
    python3 .claude/scripts/meta_oracle.py aggregate --task-id <ID> [--policy static|runtime|duo]
    python3 .claude/scripts/meta_oracle.py adversarial-test --task-id <ID>
    python3 .claude/scripts/meta_oracle.py combo --task-id <ID> [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>]

退出码: 0=ACCEPT 1=ADVISORY 2=REJECT 3=ESCALATE 4=UNAVAILABLE
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_ROOT = Path(".omc/state")
VERDICT_DIR = STATE_ROOT / "oracle-verdicts"
OUT_ROOT = STATE_ROOT / "meta-oracle-verdicts"

RETURN_CODES = {"ACCEPT": 0, "ADVISORY": 1, "REJECT": 2, "ESCALATE": 3, "UNAVAILABLE": 4}


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id(prefix: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{prefix}"


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing file: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON: {path}: {exc}"


def _latest_verdict_for(task_id: str) -> dict[str, Any] | None:
    """从 oracle-verdicts 目录获取最新裁决"""
    latest = VERDICT_DIR / task_id / "latest.json"
    data, err = read_json(latest)
    if data:
        return data
    # glob fallback
    candidates = sorted(VERDICT_DIR.glob(f"{task_id}/*.json"), reverse=True)
    if candidates:
        data, _ = read_json(candidates[0])
        return data
    return None


# ═══════════════════════════════════════════════
# 聚合
# ═══════════════════════════════════════════════

def _merge_verdicts(verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    """合并多个裁决为一个元裁决"""
    if not verdicts:
        return {"verdict": "UNAVAILABLE", "score": 0.0, "risk": "HIGH", "reasons": ["no verdicts available"]}

    scores = [float(v.get("score", 5.0)) for v in verdicts if v.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 5.0

    verdict_values = [v.get("verdict", "") for v in verdicts]
    risks = [v.get("risk", "LOW") for v in verdicts]

    all_reasons: list[str] = []
    for v in verdicts:
        for r in v.get("reasons", []):
            all_reasons.append(r)

    if "REJECT" in verdict_values:
        final_verdict = "REJECT"
    elif "ESCALATE" in verdict_values:
        final_verdict = "ESCALATE"
    elif "ADVISORY" in verdict_values or avg_score < 7.0:
        final_verdict = "ADVISORY"
    else:
        final_verdict = "ACCEPT"

    if "CRITICAL" in risks:
        final_risk = "CRITICAL"
    elif "HIGH" in risks:
        final_risk = "HIGH"
    elif "MEDIUM" in risks:
        final_risk = "MEDIUM"
    else:
        final_risk = "LOW"

    return {
        "verdict": final_verdict,
        "score": avg_score,
        "risk": final_risk,
        "reasons": all_reasons,
    }


# ═══════════════════════════════════════════════
# 对抗性测试
# ═══════════════════════════════════════════════

def detect_homogenization(verdicts: list[dict[str, Any]]) -> tuple[bool, float, list[str]]:
    """
    检测同质化——如果多个裁决的输出极端相似，标记告警。

    Returns:
        (is_homogenized: bool, penalty: float, details: list[str])
    """
    if len(verdicts) < 2:
        return False, 0.0, []

    # 检查 verdict 是否完全一致
    verdict_set = set(v.get("verdict", "") for v in verdicts if v.get("verdict"))
    if len(verdict_set) == 1 and len(verdicts) >= 2:
        details = ["所有裁决 verdict 完全一致，疑似同质化"]
        return True, 2.0, details

    # 检查 score 是否极端接近（差值 <= 0.5）
    scores = [v.get("score", 0) for v in verdicts if v.get("score") is not None]
    if len(scores) >= 2:
        max_diff = max(scores) - min(scores)
        if max_diff <= 0.5:
            details = [f"score 差异极小 (max_diff={max_diff}), 疑似同质化"]
            return True, 1.0, details

    return False, 0.0, []


def detect_contradiction(verdicts: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """检测裁决冲突——ACCEPT vs REJECT 等极端冲突"""
    if len(verdicts) < 2:
        return False, []

    verdict_set = set(v.get("verdict", "") for v in verdicts if v.get("verdict"))
    details: list[str] = []

    if "ACCEPT" in verdict_set and "REJECT" in verdict_set:
        details.append("极端冲突: 存在 ACCEPT 与 REJECT 对立裁决")

    return bool(details), details


# ═══════════════════════════════════════════════
# 核心逻辑
# ═══════════════════════════════════════════════

def aggregate_verdicts(task_id: str, policy: str = "duo") -> dict[str, Any]:
    """
    聚合 task_id 对应的所有 oracle 裁决。

    支持策略:
    - static: 只聚合静态裁决
    - runtime: 只聚合运行时裁决
    - duo: 聚合所有可用裁决
    """
    verdict_dir = VERDICT_DIR / task_id
    reasons: list[str] = []
    evidence: list[dict[str, Any]] = []

    # 读取所有可用裁决
    all_verdicts: list[dict[str, Any]] = []
    latest_path = verdict_dir / "latest.json"
    if latest_path.exists():
        data, err = read_json(latest_path)
        if data:
            all_verdicts.append(data)
            evidence.append({
                "file": str(latest_path),
                "verdict": data.get("verdict"),
                "score": data.get("score"),
            })

    # 如果 latest.json 不够，尝试读取其他 oracle-verdict JSON
    if not all_verdicts:
        for f in sorted(verdict_dir.glob("oracle-*.json"), reverse=True):
            data, err = read_json(f)
            if data:
                all_verdicts.append(data)
                evidence.append({
                    "file": str(f),
                    "verdict": data.get("verdict"),
                })
                if len(all_verdicts) >= 3:
                    break

    # 尝试兼容 model-oracle-verdicts
    model_dir = Path(".omc/state/model-oracle-verdicts") / task_id
    if model_dir.exists():
        for f in sorted(model_dir.glob("*.json"), reverse=True):
            if f.name == "latest.json":
                data, _ = read_json(f)
                if data:
                    all_verdicts.append({**data, "_from": "model"})
                    evidence.append({
                        "file": str(f),
                        "verdict": data.get("verdict"),
                        "verdict_agent": data.get("agent"),
                    })

    if not all_verdicts:
        return {
            "version": 2,
            "agent": "meta_oracle",
            "task_id": task_id,
            "run_id": run_id("meta"),
            "verdict": "ESCALATE",
            "risk": "HIGH",
            "score": 0.0,
            "evidence": [],
            "reasons": ["无可用裁决"],
            "checks": {"verdicts_loaded": 0, "homogenization": None, "contradiction": None},
            "timestamp": utc_now(),
            "meta": {"policy": policy},
        }

    # 合成
    merged = _merge_verdicts(all_verdicts)

    # 对抗性测试
    is_homo, homo_penalty, homo_details = detect_homogenization(all_verdicts)
    is_contra, contra_details = detect_contradiction(all_verdicts)

    if is_homo:
        merged["score"] = max(0.0, merged["score"] - homo_penalty)
        reasons.extend(homo_details)
        if merged["verdict"] == "ACCEPT" and merged["score"] < 7.0:
            merged["verdict"] = "ADVISORY"

    if is_contra:
        merged["verdict"] = "ESCALATE"
        reasons.extend(contra_details)

    reasons.extend(merged.get("reasons", []))

    return {
        "version": 2,
        "agent": "meta_oracle",
        "task_id": task_id,
        "run_id": run_id("meta"),
        "verdict": merged["verdict"],
        "risk": merged.get("risk", "LOW"),
        "score": merged["score"],
        "evidence": evidence,
        "reasons": reasons[:20],
        "checks": {
            "verdicts_loaded": len(all_verdicts),
            "homogenization": {"detected": is_homo, "penalty": homo_penalty},
            "contradiction": {"detected": is_contra},
        },
        "bypass": {"active": False, "reason": None, "expires_at": None},
        "timestamp": utc_now(),
        "meta": {"policy": policy, "sources": list(set(v.get("_from", "") for v in all_verdicts))},
    }


def run_adversarial_test(task_id: str) -> dict[str, Any]:
    """对 task_id 的所有可用裁决运行对抗性测试"""
    result = aggregate_verdicts(task_id)
    return {
        "task_id": task_id,
        "adversarial_checks": {
            "homogenization": result["checks"]["homogenization"],
            "contradiction": result["checks"]["contradiction"],
        },
        "meta_verdict": result["verdict"],
        "meta_score": result["score"],
        "reasons": result["reasons"],
    }


def run_combo(task_id: str, plan_text: str = "", executor_text: str = "",
              logs_text: str = "", diff_text: str = "") -> dict[str, Any]:
    """
    组合模式: 先调 oracle_agent 做审核，再聚合 + 对抗性测试。

    这是 oracle_agent + meta_oracle 的组合使用方式。
    """
    # 尝试 import oracle_agent 做审核
    try:
        import oracle_agent

        # 先跑 duo 模式写裁决
        duo_result = oracle_agent.review_duo(task_id, plan_text, executor_text, "", logs_text, diff_text)

        # 保存裁定
        from oracle_agent import _save_verdict
        _save_verdict(task_id, duo_result)
    except ImportError:
        # oracle_agent 不可用，仅做聚合
        return aggregate_verdicts(task_id)

    # 聚合
    meta = aggregate_verdicts(task_id, policy="duo")

    # 对抗性测试
    test = run_adversarial_test(task_id)
    meta["adversarial"] = test["adversarial_checks"]

    # trio_result
    meta["duo_result"] = {
        "verdict": duo_result.get("verdict"),
        "score": duo_result.get("score"),
        "static": duo_result.get("static", {}).get("verdict"),
        "runtime": duo_result.get("runtime", {}).get("verdict"),
    } if "duo_result" not in duo_result else duo_result

    return meta


def write_verdict(verdict: dict[str, Any]) -> Path:
    out_dir = OUT_ROOT / verdict["task_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{verdict['run_id']}.json"
    latest_path = out_dir / "latest.json"

    data = json.dumps(verdict, ensure_ascii=False, indent=2)
    out_path.write_text(data + "\n", encoding="utf-8")
    latest_path.write_text(data + "\n", encoding="utf-8")
    return out_path


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

def handle_aggregate(args: argparse.Namespace) -> int:
    result = aggregate_verdicts(args.task_id, args.policy or "duo")
    out_path = write_verdict(result)
    print(str(out_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return RETURN_CODES.get(result["verdict"], RETURN_CODES["UNAVAILABLE"])


def handle_adversarial_test(args: argparse.Namespace) -> int:
    result = run_adversarial_test(args.task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["meta_verdict"] in ("ACCEPT",) else 1


def handle_combo(args: argparse.Namespace) -> int:
    from pathlib import Path as _Path
    def _rf(p: str) -> str:
        if not p:
            return ""
        pp = _Path(p)
        if pp.exists():
            return pp.read_text(encoding="utf-8", errors="replace")
        return ""

    result = run_combo(
        task_id=args.task_id,
        plan_text=_rf(args.plan),
        executor_text=_rf(args.executor),
        logs_text=_rf(args.logs),
        diff_text=_rf(args.diff),
    )
    out_path = write_verdict(result)
    print(str(out_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return RETURN_CODES.get(result["verdict"], RETURN_CODES["UNAVAILABLE"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Mate Oracle — 元级审核 + 对抗性测试")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("aggregate")
    p.add_argument("--task-id", required=True)
    p.add_argument("--policy", choices=["static", "runtime", "duo"], default="duo")
    p.set_defaults(func=handle_aggregate)

    p2 = sub.add_parser("adversarial-test")
    p2.add_argument("--task-id", required=True)
    p2.set_defaults(func=handle_adversarial_test)

    p3 = sub.add_parser("combo")
    p3.add_argument("--task-id", required=True)
    p3.add_argument("--plan", default="")
    p3.add_argument("--executor", default="")
    p3.add_argument("--token", default="")
    p3.add_argument("--logs", default="")
    p3.add_argument("--diff", default="")
    p3.set_defaults(func=handle_combo)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
