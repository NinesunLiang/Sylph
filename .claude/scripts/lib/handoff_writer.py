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
