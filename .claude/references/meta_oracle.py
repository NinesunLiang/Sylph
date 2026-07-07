#!/usr/bin/env python3
"""
meta_oracle.py — Meta-Oracle 二阶评审评分器

对已完成的任务做回顾性审查：G1-G4 门禁检查 + 加权评分。

G1: 证据质量（file:line 引用、命令输出）
G2: 范围冻结（只改 plan 声明文件）
G3: 验收（VERIFIED 标记、verify 事件）
G4: 哲学一致性（不编造、不软完成、有证据）

Usage:
    python3 .claude/scripts/meta_oracle.py score --task <task-id>
    python3 .claude/scripts/meta_oracle.py score --all
    python3 .claude/scripts/meta_oracle.py audit [--days 7] [--threshold 6.0]
    python3 .claude/scripts/meta_oracle.py verify --step S1 [--token <path>]
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──
META_VERDICTS_DIR = Path(".omc/state/meta-oracle-verdicts")
TOKENS_DIR = Path(".omc/tokens")
PLANS_DIR = Path(".omc/plan")
AUDIT_DIR = Path(".omc/state/audit")

# ── G1-G4 门禁评分权重 ──
GATE_WEIGHTS = {
    "G1": 0.35,  # 证据质量
    "G2": 0.25,  # 范围冻结
    "G3": 0.20,  # 验收
    "G4": 0.20,  # 哲学一致性
}

# ── 哲学违规模式 ──
PHILOSOPHY_PATTERNS = {
    "编造证据": re.compile(r"(我觉得|我认为|应该是|可能需要)\s*(?:修改|加|删|改)"),
    "软完成": re.compile(r"(完成了|做好了|差不多了|先这样|我觉得可以)"),
}


# ═══════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════

def _ensure_dirs():
    META_VERDICTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path) -> dict | None:
    """安全加载 JSON 文件"""
    try:
        p = Path(path)
        if not p.exists():
            return None
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _find_token_for_task(task_id: str) -> tuple:
    """找到与 task_id 关联的 token 文件"""
    for f in sorted(TOKENS_DIR.rglob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            tid = data.get("task_id") or data.get("session", {}).get("id", "")
            if tid == task_id or task_id in str(f):
                return data, f
        except (json.JSONDecodeError, OSError):
            continue
    return None, None


def _find_plan_for_task(task_id: str) -> str:
    """找到与 task_id 关联的 plan.md"""
    # 尝试多级深度匹配（支持 .omc/plan/{date}/{taskid}_{time}/plan.md）
    for f in PLANS_DIR.rglob(f"**/{task_id}/plan.md"):
        return f.read_text(errors="replace")
    for f in PLANS_DIR.rglob("**/plan.md"):
        try:
            content = f.read_text(errors="replace")
            if task_id in content[:200]:
                return content
        except OSError:
            continue
    return ""


def _find_executor_for_task(task_id: str) -> str:
    """找到与 task_id 关联的 executor.md"""
    for f in PLANS_DIR.rglob(f"**/{task_id}/executor.md"):
        return f.read_text(errors="replace")
    # fallback: 全局搜索
    for f in Path(".omc").rglob("**/executor.md"):
        try:
            content = f.read_text(errors="replace")
            if task_id in str(f) or task_id in content[:100]:
                return content
        except OSError:
            continue
    return ""


def _find_audit_events(task_id: str) -> list:
    """找到与 task_id 关联的审计事件"""
    events = []
    if AUDIT_DIR.exists():
        for f in sorted(AUDIT_DIR.glob("*.json"), reverse=True)[:50]:
            try:
                data = json.loads(f.read_text())
                if data.get("task_id", "") == task_id or task_id in str(f):
                    events.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return events


# ═══════════════════════════════════════════
# G1-G4 门禁
# ═══════════════════════════════════════════

def _check_evidence(ctx: dict) -> dict:
    """G1: 证据质量——检查 file:line 引用和命令输出"""
    text = ctx.get("combined", "")
    score = 0
    reasons = []

    # file:line 引用检查
    file_line_matches = re.findall(r'[\w./-]+\.\w+:\d+', text)
    if file_line_matches:
        count = len(file_line_matches)
        if count >= 3:
            score += 6
        elif count >= 1:
            score += 3
        reasons.append(f"file:line 引用 {count}处")
    else:
        reasons.append("缺少 file:line 引用")

    # 命令输出检查
    has_output = bool(re.search(r'(exit code|exit_code|[✅❌✔✘]|PASS|FAIL|timed out)', text))
    if has_output:
        score += 4
        reasons.append("有命令输出证据")
    else:
        reasons.append("缺少命令输出证据")

    passed = score >= 6
    return {"score": min(score, 10), "reasons": reasons, "pass": passed}


def _check_scope(ctx: dict) -> dict:
    """G2: 范围冻结——检查修改是否在 plan 声明范围内"""
    plan = ctx.get("plan", "")
    executor = ctx.get("executor", "")

    score = 8  # 默认高分，扣分制
    reasons = ["未发现范围外修改"]

    # 从 plan.md 提取声明文件
    plan_files = set()
    for m in re.findall(r'`([\w./-]+\.\w+)`', plan):
        # 过滤非目标文件（URL、系统路径等）
        if m.startswith("http") or m.startswith("/"):
            continue
        plan_files.add(m)

    # 从 executor.md 提取操作文件
    executor_files = set()
    for m in re.findall(r'`([\w./-]+\.\w+)`', executor):
        if m.startswith("http") or m.startswith("/"):
            continue
        executor_files.add(m)

    # 排除治理文件
    excluded = {".claude/AGENTS.md", ".claude/kernel.md", ".claude/index.md", ".claude/CLAUDE.md"}
    outside = executor_files - plan_files - excluded

    if outside:
        outside_list = list(outside)[:5]
        score -= 2 * len(outside_list)
        reasons.append(f"修改 plan 未声明文件: {', '.join(outside_list)}")

    score = max(0, score)
    return {"score": score, "reasons": reasons, "pass": score >= 5}


def _check_verification(ctx: dict) -> dict:
    """G3: 验收——检查 VERIFIED 标记和 verify 事件"""
    text = ctx.get("combined", "")
    audit_events = ctx.get("audit_events", [])
    token = ctx.get("token", {})

    score = 0
    reasons = []

    # 1. VERIFIED 标记
    if "VERIFIED" in text:
        score += 4
        reasons.append("有 VERIFIED 标记")

    # 2. 验证关键词
    if re.search(r'verify|验收|验证通过', text, re.IGNORECASE):
        score += 2
        reasons.append("有验证记录")

    # 3. 审计事件
    verify_events = [e for e in audit_events if e.get("event") == "verify"]
    if verify_events:
        score += 3
        reasons.append(f"审计事件 {len(verify_events)}条")

    # 4. token progress
    if token and "stats" in token:
        done = token["stats"].get("done", 0)
        total = token["stats"].get("total", 0)
        if total > 0 and done >= total:
            score += 1
            reasons.append("所有步骤完成")

    if score == 0:
        reasons.append("缺少验收证据")

    return {"score": min(score, 10), "reasons": reasons, "pass": score >= 6}


def _check_philosophy(ctx: dict) -> dict:
    """G4: 哲学一致性——检查不编造/不软完成/有证据"""
    text = ctx.get("combined", "")
    score = 8
    reasons = ["哲学一致性检查通过"]
    violations = []

    # 检测违规
    for name, pattern in PHILOSOPHY_PATTERNS.items():
        if pattern.search(text):
            violations.append(name)

    # 检查无证据断言：行末无 [已验证 标记的断言行
    unverified_claims = re.findall(r'^(?!.*\[已验证|.*file:line|.*exit.code).*(?:修改了|删除了|创建了|改好了).*$', text, re.MULTILINE)
    if unverified_claims:
        violations.append("无证据断言")

    if violations:
        score -= 3
        reasons.append(f"违规: {', '.join(violations[:3])}")
        score = max(0, score)

    return {"score": score, "reasons": reasons, "pass": score >= 5}


# ═══════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════

def _calculate_final_score(gate_results: dict, token_data: dict = None) -> float:
    """加权计算最终评分"""
    total_weight = sum(GATE_WEIGHTS.values())
    if total_weight == 0:
        return 0.0

    weighted = 0.0
    for gid, result in gate_results.items():
        w = GATE_WEIGHTS.get(gid, 0)
        weighted += result["score"] * w

    final_score = weighted / total_weight

    # token progress 修正
    token_data = token_data or {}
    if "steps" in token_data:
        completed = sum(1 for s in token_data["steps"] if s.get("status") == "completed")
        total = len(token_data["steps"])
        if total > 0:
            progress = completed / total
            final_score = final_score * 0.8 + (progress * 10) * 0.2

    return round(final_score, 1)


def _collect_context(task_id: str, token_data: dict = None) -> dict:
    """收集评审所需的所有上下文"""
    ctx = {"task_id": task_id}

    plan = _find_plan_for_task(task_id)
    executor = _find_executor_for_task(task_id)
    audit_events = _find_audit_events(task_id)

    ctx["plan"] = plan
    ctx["executor"] = executor
    ctx["audit_events"] = audit_events

    if token_data:
        ctx["token"] = token_data

    # 合并所有文本用于模式匹配
    parts = [plan, executor]
    if token_data:
        parts.append(json.dumps(token_data, indent=2))
    ctx["combined"] = "\n".join(parts)

    return ctx


# ═══════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════

def score_task(task_id: str) -> dict:
    """对单个任务完整评分"""
    _ensure_dirs()

    token_data, token_file = _find_token_for_task(task_id)
    ctx = _collect_context(task_id, token_data)

    # G1-G4 门禁检查
    gate_results = {}
    all_pass = True
    gate_checks = {
        "G1": _check_evidence,
        "G2": _check_scope,
        "G3": _check_verification,
        "G4": _check_philosophy,
    }

    for gid, check_fn in gate_checks.items():
        result = check_fn(ctx)
        gate_results[gid] = result
        if not result["pass"]:
            all_pass = False

    final_score = _calculate_final_score(gate_results, token_data)

    # 裁决
    if final_score >= 8.0 and all_pass:
        verdict = "ACCEPT"
    elif final_score >= 5.0:
        verdict = "ADVISORY"
    else:
        verdict = "REJECT"

    meta_result = {
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_score": final_score,
        "verdict": verdict,
        "gates": {
            gid: {
                "score": r["score"],
                "pass": r["pass"],
                "reasons": r["reasons"],
            }
            for gid, r in gate_results.items()
        },
    }

    # 保存
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = META_VERDICTS_DIR / f"meta-{task_id}-{ts}.json"
    with open(out, "w") as f:
        json.dump(meta_result, f, indent=2, ensure_ascii=False)

    return meta_result


def score_all() -> list:
    """评分所有活跃任务"""
    _ensure_dirs()
    results = []

    if not TOKENS_DIR.exists():
        return results

    for f in TOKENS_DIR.rglob("*.json"):
        try:
            data = json.loads(f.read_text())
            task_id = data.get("task_id", "") or data.get("session", {}).get("id", f.stem)
            if data.get("status") == "archived":
                continue
            result = score_task(task_id)
            results.append(result)
        except Exception:
            continue

    return results


# ═══════════════════════════════════════════
# CLI commands
# ═══════════════════════════════════════════

def cmd_score(args: list) -> int:
    task_id = None
    all_tasks = False

    i = 0
    while i < len(args):
        if args[i] == "--task" and i + 1 < len(args):
            task_id = args[i + 1]
            i += 2
        elif args[i] == "--all":
            all_tasks = True
            i += 1
        else:
            i += 1

    if all_tasks:
        results = score_all()
        if not results:
            print(json.dumps({"error": "No active tasks found"}, ensure_ascii=False))
            return 0
        summary = {
            "total": len(results),
            "accepted": sum(1 for r in results if r["verdict"] == "ACCEPT"),
            "advisory": sum(1 for r in results if r["verdict"] == "ADVISORY"),
            "rejected": sum(1 for r in results if r["verdict"] == "REJECT"),
            "avg_score": round(sum(r["final_score"] for r in results) / len(results), 1),
        }
        print(json.dumps({"summary": summary, "tasks": results}, indent=2, ensure_ascii=False))
        return 0

    if task_id:
        result = score_task(task_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print("Usage: meta_oracle.py score --task <task-id> | --all")
    return 1


def cmd_audit(args: list) -> int:
    """审计近期任务质量"""
    days = 7
    threshold = 6.0

    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--threshold" and i + 1 < len(args):
            try:
                threshold = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    cutoff = time.time() - days * 86400
    results = []

    for f in sorted(META_VERDICTS_DIR.glob("meta-*.json"), reverse=True):
        if f.stat().st_mtime < cutoff:
            continue
        try:
            data = json.loads(f.read_text())
            results.append(data)
        except Exception:
            continue

    if not results:
        print(json.dumps({"message": f"过去 {days} 天无 Meta-Oracle 裁决"}, ensure_ascii=False))
        return 0

    below_threshold = [r for r in results if r.get("final_score", 10) < threshold]

    summary = {
        "period": f"过去 {days} 天",
        "total_reviews": len(results),
        "verdicts": {
            "ACCEPT": sum(1 for r in results if r.get("verdict") == "ACCEPT"),
            "ADVISORY": sum(1 for r in results if r.get("verdict") == "ADVISORY"),
            "REJECT": sum(1 for r in results if r.get("verdict") == "REJECT"),
        },
        "avg_score": round(sum(r.get("final_score", 0) for r in results) / max(len(results), 1), 1),
        "below_threshold": len(below_threshold),
    }
    print(json.dumps({"summary": summary, "reviews": results[:10]}, indent=2, ensure_ascii=False))
    return 0 if not below_threshold else 1


def cmd_verify_step(args: list) -> int:
    """验证单个 step"""
    step = None
    token_path = None

    i = 0
    while i < len(args):
        if args[i] == "--step" and i + 1 < len(args):
            step = args[i + 1]
            i += 2
        elif args[i] == "--token" and i + 1 < len(args):
            token_path = args[i + 1]
            i += 2
        else:
            i += 1

    if not step:
        print("Usage: meta_oracle.py verify --step S1 [--token <path>]")
        return 1

    token_data = None
    if token_path:
        token_data = _load_json(token_path)

    if not token_data:
        for f in sorted(TOKENS_DIR.rglob("*.json"), reverse=True)[:5]:
            token_data = _load_json(f)
            if token_data:
                break

    task_id = token_data.get("task_id", "") or token_data.get("session", {}).get("id", "unknown") if token_data else "unknown"
    ctx = _collect_context(task_id, token_data)

    # S1→G1, S2→G2, S3→G3, S4→G4
    gate_map = {"S1": "G1", "S2": "G2", "S3": "G3", "S4": "G4"}
    gate_id = gate_map.get(step, "G1")

    check_fns = {"G1": _check_evidence, "G2": _check_scope, "G3": _check_verification, "G4": _check_philosophy}
    check_fn = check_fns.get(gate_id, _check_evidence)

    result = check_fn(ctx)
    result["gate_id"] = gate_id
    result["step"] = step
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["pass"] else 1


# ═══════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════

def main() -> int:
    _ensure_dirs()

    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 1

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    commands = {
        "score": cmd_score,
        "audit": cmd_audit,
        "verify": cmd_verify_step,
    }

    handler = commands.get(cmd)
    if not handler:
        print(f"Unknown command: {cmd}")
        print(__doc__.strip())
        return 1

    try:
        return handler(rest)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
