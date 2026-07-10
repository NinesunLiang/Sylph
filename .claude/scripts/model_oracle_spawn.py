#!/usr/bin/env python3
"""
model_oracle_spawn.py — 并发编排层 (v2, in-process).

用直接函数调用替换 subprocess，共享进程内熔断器和全局状态。
支持：
- 并发执行（Python ThreadPoolExecutor）
- 每个 Oracle 独立超时
- 熔断隔离（一个挂不影响另一个）
- 按风险策略分级降级
- 结果缓存（同一 task 重复提交不重跑）

用法：
    python3 .claude/scripts/model_oracle_spawn.py review \
        --task-id <ID> [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>] [--policy <policy>]
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

import model_static_oracle
import model_runtime_oracle
import model_meta_oracle

from carros_oracle_base import (
    OracleReview,
    RiskPolicy, resolve_risk_policy, policy_to_gate_config,
    check_proxy_health, reset_circuit,
    LLM_AVAILABLE,
    write_oracle_verdict,
)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 60
CACHE_DIR = Path(".omc/state/oracle-cache")


# ═══════════════════════════════════════════════
# 子 Oracle 运行器（in-process 版本）
# ═══════════════════════════════════════════════

def _capture_call(fn, *args, **kwargs) -> tuple[int, str]:
    """
    直接调用函数，捕获其 stdout 输出。

    返回 (exit_code, stdout_string) 以保持与现有解析逻辑兼容。
    """
    old_stdout = sys.stdout
    redirected = io.StringIO()
    try:
        sys.stdout = redirected
        exit_code = fn(*args, **kwargs)
        return exit_code, redirected.getvalue()
    except SystemExit as e:
        # main() 中 raise SystemExit(n) 的情况
        return e.code if isinstance(e.code, int) else 1, redirected.getvalue()
    except Exception as e:
        return 1, f"[error: {type(e).__name__}: {e}]"
    finally:
        sys.stdout = old_stdout


def run_static_oracle_inproc(
    task_id: str,
    plan_path: str = "",
    executor_path: str = "",
    diff_path: str = "",
) -> tuple[int, str]:
    """直接调用 model_static_oracle.review()"""
    import argparse as _ap
    ns = _ap.Namespace(
        cmd="review",
        task_id=task_id,
        plan=plan_path or "",
        executor=executor_path or "",
        diff=diff_path or "",
        target="",
    )
    return _capture_call(model_static_oracle.review, ns)


def run_runtime_oracle_inproc(
    task_id: str,
    executor_path: str = "",
    token_path: str = "",
    logs_path: str = "",
) -> tuple[int, str]:
    """直接调用 model_runtime_oracle.review()"""
    import argparse as _ap
    ns = _ap.Namespace(
        cmd="review",
        task_id=task_id,
        executor=executor_path or "",
        token=token_path or "",
        logs=logs_path or "",
    )
    return _capture_call(model_runtime_oracle.review, ns)


def run_meta_oracle_inproc(task_id: str, policy: str = "") -> tuple[int, str]:
    """直接调用 model_meta_oracle.handle_aggregate()"""
    import argparse as _ap
    ns = _ap.Namespace(
        cmd="aggregate",
        task_id=task_id,
        policy=policy or None,
    )
    return _capture_call(model_meta_oracle.handle_aggregate, ns)


# ═══════════════════════════════════════════════
# 缓存
# ═══════════════════════════════════════════════

def _cache_key(task_id: str, oracle: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{task_id}_{oracle}.json"


def _cache_hit(task_id: str, oracle: str) -> dict | None:
    key = _cache_key(task_id, oracle)
    if not key.exists():
        return None
    try:
        return json.loads(key.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _cache_set(task_id: str, oracle: str, data: dict):
    key = _cache_key(task_id, oracle)
    key.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


# ═══════════════════════════════════════════════
# 主编排
# ═══════════════════════════════════════════════

def _parse_meta_output(stdout: str) -> OracleReview | None:
    """从 meta_oracle 的 stdout 中提取最终裁决。找最后一个有效 JSON 对象。"""
    # 策略：从末尾往前搜，找到第一个顶层 {} 能解析成有效裁决数据的
    lines = stdout.split("\n")
    # 从后向前找 { 开始的行
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith("{") or line.startswith("  {"):
            # 尝试从这行向前拼 JSON
            for j in range(i, max(i - 50, -1), -1):
                candidate = "\n".join(lines[j:i+1]).strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    try:
                        data = json.loads(candidate)
                        if "verdict" in data or "decision" in data:
                            return OracleReview(
                                decision=data.get("decision", "review"),
                                verdict=data.get("verdict", "ESCALATE"),
                                risk=data.get("risk", "HIGH"),
                                score=float(data.get("score", 5.0)),
                                degraded=data.get("degraded", False),
                                degraded_reason=data.get("degraded_reason", ""),
                                missing_oracles=data.get("missing_oracles", []),
                            )
                    except (json.JSONDecodeError, ValueError):
                        continue
    return None


def orchestrate_review(
    task_id: str,
    plan_path: str = "",
    executor_path: str = "",
    token_path: str = "",
    logs_path: str = "",
    diff_path: str = "",
    policy_name: str = "",
    no_cache: bool = False,
) -> dict:
    """编排完整 Oracle 双审流程"""

    start = time.time()

    # 0) 健康检查
    health = check_proxy_health()
    llm_status = health["status"]

    # 1) 确定策略
    if not policy_name:
        task_hint = {"description": f"task_{task_id}", "steps": []}
        resolved_policy = resolve_risk_policy(task_hint)
    else:
        try:
            resolved_policy = RiskPolicy(policy_name)
        except ValueError:
            resolved_policy = RiskPolicy.BALANCED
    gate = policy_to_gate_config(resolved_policy)

    # 2) 并发跑 static + runtime（in-process）
    static_timeout = gate.get("llm_timeout", DEFAULT_TIMEOUT)
    runtime_timeout = gate.get("llm_timeout", DEFAULT_TIMEOUT)

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}

        # static
        static_future = executor.submit(
            run_static_oracle_inproc, task_id, plan_path, executor_path, diff_path
        )

        # runtime（仅在有证据时跑）
        has_runtime_evidence = bool(token_path or logs_path or executor_path)
        if has_runtime_evidence:
            futures["runtime"] = executor.submit(
                run_runtime_oracle_inproc, task_id, executor_path, token_path, logs_path
            )

        # 等 static
        try:
            rc, stdout = static_future.result(timeout=static_timeout + 5)
            results["static"] = {"exit_code": rc, "stdout": stdout[:2000]}
            if rc == 124:
                errors["static"] = "timeout"
        except TimeoutError:
            errors["static"] = "timeout"
            results["static"] = {"exit_code": 124, "stdout": ""}

        # 如果有 runtime
        if "runtime" in futures:
            try:
                rc, stdout = futures["runtime"].result(timeout=runtime_timeout + 5)
                results["runtime"] = {"exit_code": rc, "stdout": stdout[:2000]}
                if rc == 124:
                    errors["runtime"] = "timeout"
            except TimeoutError:
                errors["runtime"] = "timeout"
                results["runtime"] = {"exit_code": 124, "stdout": ""}

    # 3) 判断是否跑 meta
    should_run_meta = True
    if errors.get("static") and gate.get("llm_required") and gate.get("critical_block"):
        should_run_meta = False
        final = OracleReview(
            decision="block",
            verdict="REJECT",
            risk="HIGH",
            score=0.0,
            degraded=True,
            degraded_reason=f"static_unavailable_in_{resolved_policy.value}_mode",
            missing_oracles=["model_static"],
        )
    elif errors.get("static") and gate.get("min_oracles", 0) == 2:
        should_run_meta = False
        final = OracleReview(
            decision="degraded_block",
            verdict="DEGRADED",
            risk="HIGH",
            score=3.0,
            degraded=True,
            degraded_reason="static_unavailable_min_oracles_not_met",
            missing_oracles=["model_static"],
        )
    else:
        if not no_cache:
            cached = _cache_hit(task_id, "meta")
            if cached:
                return cached

        rc, stdout = run_meta_oracle_inproc(task_id, policy_name)
        results["meta"] = {"exit_code": rc, "stdout": stdout[:2000]}

        final = _parse_meta_output(stdout)
        if final is None:
            final = OracleReview(
                decision="review",
                verdict="ESCALATE",
                risk="HIGH",
                score=5.0,
                degraded=True,
                degraded_reason="meta_output_parse_failed",
                missing_oracles=[],
            )

    final.duration_ms = int((time.time() - start) * 1000)

    # 4) 写入最终裁决
    write_oracle_verdict(task_id, "model_orchestrator", final)

    # 5) 缓存（非降级）
    if not final.degraded:
        _cache_set(task_id, "meta", final.to_dict())

    result = {
        "task_id": task_id,
        "policy": resolved_policy.value,
        "llm_status": llm_status,
        "circuit": health["circuit"],
        "errors": errors,
        "oracle_results": results,
        "final": final.to_dict(),
        "duration_ms": final.duration_ms,
    }
    return result


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

def cmd_review(args: argparse.Namespace) -> int:
    result = orchestrate_review(
        task_id=args.task_id,
        plan_path=args.plan or "",
        executor_path=args.executor or "",
        token_path=args.token or "",
        logs_path=args.logs or "",
        diff_path=args.diff or "",
        policy_name=args.policy or "",
        no_cache=args.no_cache,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("final", {}).get("verdict") in ("ACCEPT", "ADVISORY", "DEGRADED") else 2


def cmd_health(args: argparse.Namespace) -> int:
    health = check_proxy_health()
    print(json.dumps(health, ensure_ascii=False, indent=2))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    reset_circuit()
    print("[orchestrator] circuit breaker reset")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    verdict_dir = Path(".omc/state/model-oracle-verdicts") / args.task_id
    latest = verdict_dir / "latest.json"
    if latest.exists():
        print(latest.read_text(encoding="utf-8"))
        return 0
    print(f"[orchestrator] no verdict for task {args.task_id}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Model Oracle Spawn — 并发编排双审")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("review")
    p.add_argument("--task-id", required=True)
    p.add_argument("--plan", default="")
    p.add_argument("--executor", default="")
    p.add_argument("--token", default="")
    p.add_argument("--logs", default="")
    p.add_argument("--diff", default="")
    p.add_argument("--policy", choices=[p.value for p in RiskPolicy], default="")
    p.add_argument("--no-cache", action="store_true")

    p_h = sub.add_parser("health")
    p_r = sub.add_parser("reset")
    p_s = sub.add_parser("status")
    p_s.add_argument("--task-id", required=True)

    args = parser.parse_args()
    if args.cmd == "health":
        return cmd_health(args)
    elif args.cmd == "reset":
        return cmd_reset(args)
    elif args.cmd == "status":
        return cmd_status(args)
    return cmd_review(args)


if __name__ == "__main__":
    raise SystemExit(main())
