#!/usr/bin/env python3
"""
CarrorOS PlanBuilder

Purpose:
  Convert an IntakeGate decision into a frozen, verifiable plan.md.

Constraints:
  - Python 3.10+ standard library only
  - No task execution
  - No secret reading
  - Every executable step must have scope and verify rules
  - L1/L2 are task governance levels, not model tiers
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Step:
    step_id: str
    title: str
    scope: list[str]
    verify: list[str]
    risk: str | None = None
    oracle: str | None = None


@dataclass
class Plan:
    task_id: str
    level: str
    risk_level: str
    task_type: str
    goal: str
    scope: list[str]
    steps: list[Step]
    pending_decisions: list[str]
    blocked_reason: str | None
    doc_root: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(content)
    tmp.replace(path)


def sanitize_goal(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    return value[:240] if value else "Unspecified task"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    slug = slug.strip("-._")
    return slug[:64] or "task"


def resolve_doc_root(level: str, task_id: str, feature: str | None = None) -> str:
    if level == "L2":
        name = safe_slug(feature or task_id)
        return f"rpe/{name}"
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f".omc/tasks/{d}/{safe_slug(task_id)}"


def infer_default_verify(task_type: str, scope: list[str], title: str) -> list[str]:
    if task_type == "doc":
        target = scope[0] if scope else "<doc-file>"
        return [f"file:{target} contains expected update"]

    if task_type == "config":
        if any(path.endswith(".json") for path in scope):
            return ["command:python -m json.tool <config-file>"]
        if any(path.endswith((".yaml", ".yml", ".toml")) for path in scope):
            return ["command:<project config validation command>"]
        return ["file:<config-file> contains expected value"]

    if task_type in ("code", "security"):
        return [
            "command:<project test command>",
            f"assertion:{title}",
        ]

    if task_type == "data":
        return [
            "command:<migration dry-run or schema check>",
            f"assertion:{title}",
        ]

    if task_type == "infra":
        return [
            "command:<infra validate command>",
            f"assertion:{title}",
        ]

    return [f"assertion:{title}"]


def validate_step(step: Step) -> list[str]:
    errors: list[str] = []

    if not step.step_id:
        errors.append("missing_step_id")
    if not step.title:
        errors.append(f"{step.step_id}:missing_title")
    if not step.scope:
        errors.append(f"{step.step_id}:missing_scope")
    if not step.verify:
        errors.append(f"{step.step_id}:missing_verify")

    invalid_verify = {"none", "n/a", "todo", ""}
    if any(rule.strip().lower() in invalid_verify for rule in step.verify):
        errors.append(f"{step.step_id}:invalid_verify")

    vague_words = [
        "优化系统",
        "完善代码",
        "处理问题",
        "修一下",
        "相关文件",
        "所有东西",
        "看情况",
    ]
    if any(word in step.title for word in vague_words):
        errors.append(f"{step.step_id}:vague_title")

    return errors


def build_l1_steps(task_type: str, scope: list[str]) -> list[Step]:
    if not scope:
        scope = ["<pending-user-confirmation>"]

    title_map = {
        "doc": "更新文档内容并保持现有结构",
        "config": "修改配置项并保持格式有效",
        "code": "实现目标代码修改",
        "security": "实现安全相关修改",
        "data": "准备数据变更并验证可回滚性",
        "infra": "修改基础设施配置并验证语法",
        "unknown": "完成用户确认范围内的修改",
    }

    title = title_map.get(task_type, "完成用户确认范围内的修改")
    return [
        Step(
            step_id="S1",
            title=title,
            scope=scope,
            verify=infer_default_verify(task_type, scope, title),
        )
    ]


def build_l2_steps(task_type: str, scope: list[str], risk_level: str) -> list[Step]:
    if not scope:
        scope = ["<discovery-required>"]

    return [
        Step(
            step_id="A.1",
            title="确认目标、边界、约束与验收标准",
            scope=scope,
            verify=["file:research.md contains goal, boundaries, constraints, acceptance criteria"],
            risk="scope_drift",
        ),
        Step(
            step_id="B.1",
            title="冻结方案、scope 与 step 状态机",
            scope=scope,
            verify=["file:plan.md contains Gate, Four Factors, Scope, Steps"],
            risk="plan_drift",
        ),
        Step(
            step_id="C.1",
            title="完成方案审核",
            scope=scope,
            verify=["file:oracle-verdicts.md contains ACCEPT or ADVISORY"],
            risk="review_required",
            oracle="plan_review",
        ),
        Step(
            step_id="D.1",
            title="实施核心变更",
            scope=scope,
            verify=infer_default_verify(task_type, scope, "实施核心变更"),
            risk=risk_level,
        ),
        Step(
            step_id="E.1",
            title="完成验收与残余风险记录",
            scope=scope,
            verify=["file:acceptance.md contains verification evidence and residual risks"],
            risk=risk_level,
            oracle="final_acceptance" if risk_level in ("high", "critical") else None,
        ),
    ]


def build_plan(
    intake: dict[str, Any],
    user_request: str,
    task_id: str,
    feature: str | None = None,
) -> Plan:
    decision = intake.get("decision")
    if decision not in {"L1", "L2", "ASK_USER", "BLOCKED"}:
        raise ValueError(f"unsupported intake decision: {decision}")

    risk_level = intake.get("risk_level", "medium")
    task_type = intake.get("task_type", "unknown")
    scope = intake.get("scope") or []
    goal = sanitize_goal(user_request)

    if decision == "L1":
        level = "L1"
        steps = build_l1_steps(task_type, scope)
        pending = []
        blocked_reason = None
    elif decision == "L2":
        level = "L2"
        steps = build_l2_steps(task_type, scope, risk_level)
        pending = []
        blocked_reason = None
    elif decision == "ASK_USER":
        level = intake.get("level", "L1")
        steps = []
        pending = intake.get("required_confirmations", []) or ["clarify_goal_or_scope"]
        blocked_reason = "pending_user_decision"
    else:
        level = intake.get("level", "L2")
        steps = []
        pending = []
        reasons = intake.get("reasons", [])
        blocked_reason = reasons[-1] if reasons else "blocked_by_intake"

    doc_root = resolve_doc_root(level, task_id, feature)

    plan = Plan(
        task_id=task_id,
        level=level,
        risk_level=risk_level,
        task_type=task_type,
        goal=goal,
        scope=scope,
        steps=steps,
        pending_decisions=pending,
        blocked_reason=blocked_reason,
        doc_root=doc_root,
    )

    errors: list[str] = []
    for step in plan.steps:
        errors.extend(validate_step(step))

    if errors:
        raise ValueError("invalid plan: " + ", ".join(errors))

    return plan


def render_gate(plan: Plan) -> list[str]:
    oracle_required = "true" if plan.level == "L2" else "false"
    phase = "B" if plan.level == "L2" else "A"
    return [
        "## Gate",
        f"- level: {plan.level}",
        f"- phase: {phase}",
        f"- oracle_required: {oracle_required}",
        f"- meta_oracle_required: {oracle_required}",
        "",
    ]


def render_four_factors(plan: Plan) -> list[str]:
    if plan.level == "L1":
        return [
            "## Four Factors",
            "- Philosophy: 验证优先 + 最小改动",
            "- Iron Rules: 范围冻结 + 不假完成",
            "- ROI: low-to-medium; simple bounded task",
            "- Current State: optional for L1",
            "",
        ]

    return [
        "## Four Factors",
        "- Philosophy: 验证优先 + 零信任 + 守护优先",
        "- Iron Rules: 范围冻结；证据门禁；危险操作审批",
        "- ROI: required for L2 before execution",
        "- Current State: must be supported by research.md evidence",
        "",
    ]


def render_plan_md(plan: Plan) -> str:
    lines: list[str] = ["# Plan", ""]

    lines.extend(render_gate(plan))

    lines.append("## Goal")
    lines.append(plan.goal)
    lines.append("")

    lines.extend(render_four_factors(plan))

    lines.append("## Classification")
    lines.append(f"- task_id: {plan.task_id}")
    lines.append(f"- risk: {plan.risk_level}")
    lines.append(f"- task_type: {plan.task_type}")
    lines.append(f"- doc_root: {plan.doc_root}")
    lines.append("")

    lines.append("## Scope")
    if plan.scope:
        for path in plan.scope:
            lines.append(f"- {path}")
    else:
        lines.append("- <pending-user-confirmation>")
    lines.append("")

    lines.append("## Scope Freeze")
    if plan.level == "L2":
        lines.append("- status: frozen")
        lines.append("- change_policy: requires_user_confirmation_or_l2_review")
    else:
        lines.append("- status: frozen")
        lines.append("- change_policy: requires_user_confirmation")
    lines.append("")

    lines.append("## User Decisions")
    lines.append("- <none>")
    lines.append("")

    if plan.pending_decisions:
        lines.append("## Pending Decisions")
        for item in plan.pending_decisions:
            lines.append(f"- {item}")
        lines.append("")

    if plan.blocked_reason:
        lines.append("## Blocked")
        lines.append(f"- reason: {plan.blocked_reason}")
        lines.append("- next_action: wait_for_user_or_update_intake")
        lines.append("")

    lines.append("## Steps")
    if not plan.steps:
        lines.append("- <blocked-or-waiting-user>")
    else:
        current_phase = None
        for step in plan.steps:
            if plan.level == "L2":
                phase = step.step_id.split(".", 1)[0]
                phase_title = {
                    "A": "A Cognition",
                    "B": "B Plan",
                    "C": "C Review",
                    "D": "D Execute",
                    "E": "E Acceptance",
                }.get(phase, phase)
                if phase != current_phase:
                    lines.append("")
                    lines.append(f"### {phase_title}")
                    current_phase = phase

            lines.append(f"- [ ] {step.step_id}: {step.title}")
            lines.append(f"  - scope: {', '.join(step.scope)}")
            for rule in step.verify:
                lines.append(f"  - verify: {rule}")
            if step.risk:
                lines.append(f"  - risk: {step.risk}")
            if step.oracle:
                lines.append(f"  - oracle: {step.oracle}")

    lines.append("")
    return "\n".join(lines)


def update_token(token_path: Path, plan: Plan) -> None:
    token = read_json(token_path) if token_path.exists() else {}

    token.setdefault("session", {})
    token.setdefault("task", {})
    token.setdefault("stats", {})
    token.setdefault("context", {})

    if plan.blocked_reason == "pending_user_decision":
        status = "waiting_human"
    elif plan.blocked_reason:
        status = "blocked"
    else:
        status = "planning"

    token["status"] = "active"
    token["session"]["level"] = plan.level
    token["session"]["id"] = plan.task_id
    token["session"]["created_at"] = token["session"].get("created_at", now_iso())
    token["session"]["updated_at"] = now_iso()
    token["task"]["id"] = plan.task_id
    token["task"]["status"] = status
    token["task"]["phase"] = "B" if plan.level == "L2" else "A"
    token["task"]["current_step"] = plan.steps[0].step_id if plan.steps else None
    token["task"]["scope"] = plan.scope
    token["task"]["blocked"] = plan.blocked_reason
    token["task"]["failed_verifications"] = token["task"].get("failed_verifications", 0)
    token["task"]["risk_level"] = plan.risk_level
    token["task"]["task_type"] = plan.task_type
    token["task"]["doc_root"] = plan.doc_root

    token["stats"]["done"] = 0
    token["stats"]["total"] = len(plan.steps)
    token["stats"]["turns"] = token["stats"].get("turns", 0)
    token["stats"]["tool_calls"] = token["stats"].get("tool_calls", 0)

    token["context"].setdefault("token_used", None)
    token["context"].setdefault("token_limit", None)
    token["context"].setdefault("watermark_source", "unknown")

    write_json(token_path, token)


def write_plan_audit(plan: Plan, audit_dir: Path, intake_decision: str) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

    if intake_decision == "BLOCKED":
        event_type = "plan_blocked"
    elif intake_decision == "ASK_USER":
        event_type = "plan_waiting_user"
    else:
        event_type = "plan_created"

    event = {
        "event_type": event_type,
        "timestamp": now_iso(),
        "task_id": plan.task_id,
        "level": plan.level,
        "phase": "B" if plan.level == "L2" else "A",
        "current_step": plan.steps[0].step_id if plan.steps else None,
        "actor": "model",
        "action": "create_plan",
        "paths": [
            f"{plan.doc_root}/plan.md",
            ".omc/state/token.json",
        ],
        "decision": intake_decision,
        "reason": "intake_decision_converted_to_plan",
        "evidence": {
            "type": "plan_schema",
            "summary": f"{len(plan.steps)} steps generated with verify rules",
        },
        "risk": plan.risk_level,
        "blocked": plan.blocked_reason,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    return path


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: plan_builder.py <intake_json_path> '<user request>' [task_id] [feature]",
            file=sys.stderr,
        )
        return 2

    intake_path = Path(sys.argv[1])
    user_request = sys.argv[2]
    task_id = sys.argv[3] if len(sys.argv) >= 4 else "task_0001"
    feature = sys.argv[4] if len(sys.argv) >= 5 else None

    intake = read_json(intake_path)
    decision = intake.get("decision")

    if decision not in {"L1", "L2", "ASK_USER", "BLOCKED"}:
        print(f"invalid intake decision: {decision}", file=sys.stderr)
        return 1

    plan = build_plan(intake, user_request, task_id, feature)
    plan_md = render_plan_md(plan)

    write_text(Path(plan.doc_root) / "plan.md", plan_md)

    # 写入 token: 优先环境变量指定路径，回退到 .omc/state/token.json
    token_path_env = os.environ.get("CARROROS_TOKEN_PATH", "")
    if token_path_env:
        token_path = Path(token_path_env)
        token_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        token_path = Path(".omc/state/token.json")
    update_token(token_path, plan)

    write_plan_audit(plan, Path(".omc/audit"), decision)

    print(plan_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
