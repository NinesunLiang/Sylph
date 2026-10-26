#!/usr/bin/env python3
"""
handoff_writer.py — Resume Capsule 生成器

生成 handoff.md（导航-only，非真相源）。
Preflight 验证 token.json CAS + plan 版本一致性。
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def generate_capsule(
    task_id: str,
    token: dict,
    plan_path: Optional[Path] = None,
    executor_path: Optional[Path] = None,
    max_nav_chars: int = 8000,
    archived: bool = False,
) -> str:
    """
    生成 Resume Capsule（导航-only）。
    头部强制 NOT_SOURCE_OF_TRUTH。
    如果 archived=True，标记已归档，无 next_action。
    """
    lines = []
    lines.append("# Resume Capsule — Navigation Only")
    lines.append("")
    lines.append("## ⚠️ NOT SOURCE OF TRUTH")
    lines.append("Resume engine MUST load token.json (CAS) first.")
    lines.append("This handoff is navigation only. Do not parse current state from this file.")
    lines.append("")
    lines.append(f"generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"task_id: {task_id}")
    lines.append("")

    # Goal from token or plan
    lines.append("## Goal")
    if plan_path and plan_path.exists():
        text = plan_path.read_text(encoding="utf-8")
        lines.append(text.splitlines()[0] if text.splitlines() else "?")
    else:
        lines.append(token.get("session", {}).get("id", "?"))
    lines.append("")

    # Confirmed decisions (from executor if available)
    lines.append("## Confirmed Decisions")
    if executor_path and executor_path.exists():
        for line in executor_path.read_text(encoding="utf-8").splitlines()[-10:]:
            stripped = line.strip()
            if stripped.startswith("-") or stripped.startswith("*"):
                lines.append(f"  {stripped[:160]}")
    if len(lines) < 5:
        lines.append("  (pending)")
    lines.append("")

    # ── 步骤交接契约（2026-08-30）：上步 produces → 下步 consumes ──
    # 契约先行（不是事后兜底）：让下步启动前直接读 consumes 字段，
    # 避免"步骤需要的不匹配"在执行中才发现。
    lines.append("## Step Contract (Handoff Boundary)")
    lines.append("")
    lines.append("### Last Step Produces (本步的输出/产物)")
    if executor_path and executor_path.exists():
        # 从 executor.md 提取最近 EV 块的 produces 字段（轻量启发式）
        _ex_text = executor_path.read_text(encoding="utf-8")
        _ev_produces = []
        for _line in _ex_text.splitlines():
            _stripped = _line.strip()
            if _stripped.startswith("produces:") or _stripped.startswith("- produces:"):
                _ev_produces.append(_stripped)
        if _ev_produces:
            lines.append("  " + "\n  ".join(_ev_produces[-3:]))  # 最近3条
        else:
            lines.append("  (从 plan.md 对应 step 的 produces 字段读取)")
    else:
        lines.append("  (executor.md 不存在 — 当前无已完成 step)")
    lines.append("")

    # Next action (or archived)
    if archived:
        lines.append("## ⏹  Status: ARCHIVED")
        lines.append("  This task is archived. Do not resume execution.")
        lines.append("  For reference only. Final report in final-report.md.")
    else:
        lines.append("## Next Action")
        cs = token.get("task", {}).get("current_step", "?")
        st = token.get("task", {}).get("status", "?")
        lines.append(f"  step: {cs} | status: {st}")
        # Next Step Consumes：让 AI 在执行下步前明确知道需要什么
        lines.append("")
        lines.append("### Next Step Consumes (下步的输入/依赖)")
        lines.append("  ⚠ 契约握手：在执行下步前，先 verify 当前 step 的 produces 字段")
        lines.append("    是否满足下步 consumes 字段。不满足 → REDIRECT 回上步补完，不强行跑。")
    lines.append("")

    # Changed files from plan scope
    lines.append("## Changed Files")
    if plan_path and plan_path.exists():
        text = plan_path.read_text(encoding="utf-8")
        in_scope = False
        for line in text.splitlines():
            if line.lower().startswith("## scope"):
                in_scope = True
                continue
            if in_scope and line.startswith("## "):
                break
            if in_scope and line.strip().startswith("-"):
                fname = line.strip().lstrip("- ").strip("`")
                if fname:
                    lines.append(f"  - {fname}")
    lines.append("")

    # Required reads (minimal)
    lines.append("## Required Reads")
    lines.append("  - token.json (CAS)")
    if plan_path:
        lines.append(f"  - {plan_path.relative_to(plan_path.parents[3])}")
    lines.append("")

    # Do not reload
    lines.append("## Do Not Reload")
    lines.append("  - 全部旧 transcript")
    lines.append("  - docs/reviews/**")
    lines.append("  - 完整测试日志")
    lines.append("  - 旧 Oracle 裁决")

    text = "\n".join(lines)
    if len(text) > max_nav_chars:
        text = text[: max_nav_chars - 20] + "\n...[TRUNCATED]"
    return text


def write_handoff(
    task_dir: Path,
    task_id: str,
    token: dict,
    plan_path: Optional[Path] = None,
    executor_path: Optional[Path] = None,
    archived: bool = False,
) -> Path:
    """Write handoff.md to task directory."""
    capsule = generate_capsule(task_id, token, plan_path, executor_path, archived=archived)
    handoff_path = task_dir / "handoff.md"
    handoff_path.write_text(capsule, encoding="utf-8")
    return handoff_path


def run_preflight(task_dir: Path, token: dict) -> list[str]:
    """
    Resume Preflight 检查：
    1) token.json CAS load
    2) plan 版本一致性
    3) external_effects 三界检查
    4) handoff 存在

    Returns list of issues (empty = pass).
    """
    issues = []

    # 1. token.json CAS check
    if not token.get("schema_version"):
        issues.append("⚠ token.json missing schema_version (CAS)")
    if not token.get("stats"):
        issues.append("⚠ token.json missing stats section")

    # 2. plan consistency
    plan_path = task_dir / "plan.md"
    if not plan_path.exists():
        issues.append("⚠ plan.md not found")
    else:
        plan_text = plan_path.read_text(encoding="utf-8")
        if not plan_text.strip():
            issues.append("⚠ plan.md is empty")

    # 3. external_effects — check state/sub_task dirs for IN_FLIGHT markers
    state_dir = task_dir / "state"
    if state_dir.exists():
        for f in state_dir.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    effects = data.get("external_effects", []) if isinstance(data, dict) else []
                    for eff in effects:
                        status = eff.get("status", "")
                        if status in ("IN_FLIGHT", "UNKNOWN"):
                            issues.append(f"⚠ external_effect IN_FLIGHT/UNKNOWN: {eff.get('id', '?')}")
                except (json.JSONDecodeError, OSError):
                    pass

    # 4. handoff exists
    handoff_path = task_dir / "handoff.md"
    if not handoff_path.exists():
        issues.append("ℹ handoff.md not yet written (acceptable for in-progress)")
    else:
        text = handoff_path.read_text(encoding="utf-8")
        if "NOT SOURCE OF TRUTH" not in text:
            issues.append("⚠ handoff.md missing NOT_SOURCE_OF_TRUTH header")

    return issues
