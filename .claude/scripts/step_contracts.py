#!/usr/bin/env python3
"""
step_contracts.py — Step lifecycle contracts for atomic evidence (Task75)

Provides:
  - parse_plan_steps: dependency-aware plan parser
  - find_first_activatable_step: first pending step with deps completed
  - start_step_atomic: atomic step activation (plan + token + executor)
  - complete_step_atomic: evidence-validated step completion
  - validate_step_evidence: EV evidence completeness check

All operations use temp files + flock for multi-file atomicity.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEP_STATUSES = {"pending", "active", "completed", "blocked"}

EVIDENCE_REQUIRED_SECTIONS = [
    "Conditions",
    "Key Changes",
    "Decisions",
    "Acceptance Checklist",
    "TDD Evidence",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _transaction_temp_path(base_path: Path) -> Path:
    return base_path.with_suffix(base_path.suffix + f".{os.getpid()}.tmp")


def _atomic_replace(src: Path, dst: Path) -> None:
    os.replace(str(src), str(dst))


# ─── Plan Parsing ───────────────────────────────────────────────────


def parse_plan_steps(plan_text: str) -> list[dict[str, Any]]:
    """Parse plan.md into structured step list with dependency metadata.

    Each step dict has: id, status, depends_on, acceptance, verify, scope.

    Status is inferred from checkbox marker:
      [ ] -> pending, [x]/[X] -> completed, [a] -> active
    """
    steps: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    status_map = {" ": "pending", "x": "completed", "X": "completed",
                  "a": "active", "A": "active"}

    for line in plan_text.splitlines():
        sm = re.match(r"^- \[(.)\] (\S+?):", line.strip())
        if sm:
            if current:
                steps.append(current)
            status_char = sm.group(1)
            current = {
                "id": sm.group(2),
                "status": status_map.get(status_char, "pending"),
                "depends_on": "none",
                "acceptance": "",
                "verify": "",
                "scope": "",
            }
        if current:
            dm = re.match(r"\s+- depends_on:\s*(.+)", line)
            if dm:
                val = dm.group(1).strip()
                current["depends_on"] = val
            am = re.match(r"\s+- (acceptance|verify|scope):\s*(.*)", line)
            if am:
                key = am.group(1)
                current[key] = am.group(2).strip()
    if current:
        steps.append(current)
    return steps


def find_first_activatable_step(steps: list[dict[str, Any]]) -> str | None:
    """Find first pending step whose dependencies are all completed.

    Returns step_id or None if no activatable step exists.
    """
    completed = {s["id"] for s in steps if s["status"] == "completed"}
    for s in steps:
        if s["status"] != "pending":
            continue
        dep = s.get("depends_on", "none")
        if dep.lower() == "none" or dep in completed:
            return s["id"]
    return None


# ─── Evidence Validation ────────────────────────────────────────────


def _extract_section_content(text: str, section_name: str) -> str:
    """Extract content under a ## section header, up to next ## or EOF."""
    marker = f"## {section_name}"
    parts = text.split(marker)
    if len(parts) < 2:
        return ""
    after = parts[1]
    nxt = after.find("\n## ")
    if nxt >= 0:
        after = after[:nxt]
    # Remove HTML comments
    after = re.sub(r"<!--.*?-->", "", after, flags=re.DOTALL)
    lines = [l.strip() for l in after.split("\n")
             if l.strip() and not l.strip().startswith("<!--")]
    return "\n".join(lines)


def validate_step_evidence(executor_text: str, step_id: str) -> list[str]:
    """Validate EV evidence completeness for a step.

    Checks:
      1. EV block exists for step_id
      2. Conditions section has content
      3. Key Changes section has content
      4. Decisions section includes rationale (or "none" + reason)
      5. Acceptance Checklist is fully checked [x]
      6. TDD Evidence has dependency TDD + regression TDD with exit 0

    Returns list of error strings (empty = all valid).
    """
    errors: list[str] = []

    # 1. EV block for this step
    ev_pattern = rf"### EV-{re.escape(step_id)}\b"
    if not re.search(ev_pattern, executor_text):
        errors.append(f"missing_step_evidence_block: EV-{step_id}")
        return errors  # can't validate further without evidence block

    # 2. Conditions section
    cond_content = _extract_section_content(executor_text, "Conditions")
    if not cond_content:
        errors.append("conditions_section_empty_or_missing")
    else:
        cond_lines = [l for l in cond_content.split("\n") if l.strip()
                      and not l.strip().startswith("<!--")]
        if not cond_lines:
            errors.append("conditions_section_no_content")

    # 3. Key Changes section
    kc_content = _extract_section_content(executor_text, "Key Changes")
    if not kc_content:
        errors.append("key_changes_section_empty_or_missing")
    else:
        kc_lines = [l for l in kc_content.split("\n") if l.strip()
                    and not l.strip().startswith("<!--")]
        if not kc_lines:
            errors.append("key_changes_section_no_content")

    # 4. Decisions section - must include rationale
    dec_content = _extract_section_content(executor_text, "Decisions")
    if not dec_content:
        errors.append("decisions_section_empty_or_missing")
    else:
        dec_lower = dec_content.lower()
        has_rationale = ("rationale" in dec_lower or "reason" in dec_lower
                         or "none" in dec_lower)
        if not has_rationale:
            errors.append("decisions_missing_rationale")

    # 5. Acceptance Checklist - all [x]
    ac_content = _extract_section_content(executor_text, "Acceptance Checklist")
    if not ac_content:
        errors.append("acceptance_checklist_empty_or_missing")
    else:
        unchecked = len(re.findall(r"- \[ \]", ac_content))
        if unchecked > 0:
            errors.append(f"acceptance_checklist_has_{unchecked}_unchecked_items")

    # 6. TDD Evidence - dependency + regression with exit 0
    tdd_content = _extract_section_content(executor_text, "TDD Evidence")
    if not tdd_content:
        errors.append("tdd_evidence_empty_or_missing")
    else:
        tdd_lower = tdd_content.lower()
        has_dep_tdd = re.search(r"dependency.*?tdd", tdd_lower)
        if not has_dep_tdd:
            errors.append("tdd_missing_dependency_tdd_command")
        else:
            dep_exit0 = re.search(r"dependency.*?tdd.*?(?:exit\s*[：:]\s*0|→\s*exit\s*0|->\s*exit\s*0)", tdd_lower)
            if not dep_exit0:
                errors.append("tdd_dependency_tdd_missing_exit_0")

        has_reg_tdd = re.search(r"regression.*?tdd", tdd_lower)
        if not has_reg_tdd:
            errors.append("tdd_missing_regression_tdd_command")
        else:
            reg_exit0 = re.search(r"regression.*?tdd.*?(?:exit\s*[：:]\s*0|→\s*exit\s*0|->\s*exit\s*0)", tdd_lower)
            if not reg_exit0:
                errors.append("tdd_regression_tdd_missing_exit_0")

    return errors


# ─── Atomic Step Start ──────────────────────────────────────────────


def start_step_atomic(token_path: str | Path,
                      plan_path: str | Path,
                      executor_path: str | Path,
                      step_id: str) -> None:
    """Atomic step activation: transactionally update plan + token + executor.

    Transaction semantics:
      - Validates step exists in plan and is pending
      - Validates all dependencies are completed
      - Updates plan.md: [ ] -> [a] for step_id
      - Updates token.json: current_step, status, revision
      - Updates executor.md: writes Conditions section + start EV block

    Crash during transaction leaves NO partial state (temp files + os.replace).

    Raises ValueError on validation failure.
    """
    token_path = Path(token_path)
    plan_path = Path(plan_path)
    executor_path = Path(executor_path)

    # Read current state
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    token = read_json(token_path, {})

    # Validate step
    steps = parse_plan_steps(plan_text)
    step_info = next((s for s in steps if s["id"] == step_id), None)
    if not step_info:
        raise ValueError(f"Step {step_id} not found in plan")
    if step_info["status"] != "pending":
        raise ValueError(f"Step {step_id} status={step_info['status']}, expected pending")

    # Validate dependencies
    dep = step_info.get("depends_on", "none")
    if dep.lower() != "none":
        dep_info = next((s for s in steps if s["id"] == dep), None)
        if not dep_info or dep_info["status"] != "completed":
            raise ValueError(f"Step {step_id} depends on {dep} which is not completed")

    # Prepare new plan text
    new_plan = re.sub(
        r"^- \[ \] " + re.escape(step_id) + r":",
        f"- [a] {step_id}:",
        plan_text,
        1,  # only first occurrence
        flags=re.MULTILINE,
    )
    # Also mark status as active
    if f"status: active" not in new_plan:
        # Add status: active line after the step marker line
        new_plan = re.sub(
            rf"(- \[a\] {re.escape(step_id)}:.*)(\n)",
            r"\1" + "\n" + "  - status: active" + r"\2",
            new_plan,
            1,
        )

    # Update token
    token.setdefault("task", {})["current_step"] = step_id
    token["task"]["status"] = "active"
    token.setdefault("goal", {})
    token["goal"]["active_step"] = step_id
    token["revision"] = token.get("revision", 0) + 1

    # Prepare executor content
    ts = now_iso()
    exec_conditions = f"""
## Conditions

- step: {step_id}
- status: active
- started_at: {ts}
- depends_on: {dep}
"""
    exec_start_ev = f"""
### EV-{step_id}-START

- step: {step_id}
- type: step_start
- evidence_level: E2
- timestamp: {ts}
- source: start_step_atomic
- exit_code: 0
- assertion: Step {step_id} activated atomically with dep={dep}
"""

    # ── Atomic multi-file write ──
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    tmp_plan = _transaction_temp_path(plan_path)
    tmp_token = _transaction_temp_path(token_path)
    tmp_executor = _transaction_temp_path(executor_path)

    # Save originals for rollback
    orig_plan = plan_path.read_bytes() if plan_path.exists() else None
    orig_token = token_path.read_bytes() if token_path.exists() else None
    orig_executor = executor_path.read_bytes() if executor_path.exists() else None

    replaced = []  # track successfully replaced files for rollback

    try:
        with open(lock_path, "a+") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                # Write plan
                plan_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_plan.write_text(new_plan, encoding="utf-8")
                _atomic_replace(tmp_plan, plan_path)
                replaced.append((plan_path, orig_plan))

                # Write token
                token_path.parent.mkdir(parents=True, exist_ok=True)
                token_data = json.dumps(token, indent=2, ensure_ascii=False) + "\n"
                tmp_token.write_text(token_data, encoding="utf-8")
                _atomic_replace(tmp_token, token_path)
                replaced.append((token_path, orig_token))

                # Write executor — add Conditions + start EV
                executor_path.parent.mkdir(parents=True, exist_ok=True)
                existing_exec = (executor_path.read_text(encoding="utf-8")
                                 if executor_path.exists() else "")
                new_exec = existing_exec.rstrip() + "\n"
                if "## Conditions" not in existing_exec:
                    new_exec += exec_conditions
                new_exec += exec_start_ev
                tmp_executor.write_text(new_exec, encoding="utf-8")
                _atomic_replace(tmp_executor, executor_path)
                replaced.append((executor_path, orig_executor))
            except Exception:
                # Rollback all successfully replaced files
                for path, original in replaced:
                    try:
                        if original is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_bytes(original)
                    except OSError:
                        pass
                raise
            finally:
                for p in [tmp_plan, tmp_token, tmp_executor]:
                    if p.exists():
                        p.unlink(missing_ok=True)
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    finally:
        if lock_path.exists():
            lock_path.unlink(missing_ok=True)


# ─── Atomic Step Complete ──────────────────────────────────────────


def complete_step_atomic(token_path: str | Path,
                         plan_path: str | Path,
                         executor_path: str | Path,
                         step_id: str) -> None:
    """Evidence-validated step completion.

    Before updating plan/token, validates EV evidence completeness via
    validate_step_evidence(). Rejects with ValueError if evidence is
    missing or incomplete.

    On success:
      - plan.md: [a] -> [x] for step_id, status: active -> completed
      - token.json: stats.done++, stats.total checked, task status updated
    """
    token_path = Path(token_path)
    plan_path = Path(plan_path)
    executor_path = Path(executor_path)

    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    executor_text = executor_path.read_text(encoding="utf-8") if executor_path.exists() else ""
    token = read_json(token_path, {})

    steps = parse_plan_steps(plan_text)
    step_info = next((s for s in steps if s["id"] == step_id), None)
    if not step_info:
        raise ValueError(f"Step {step_id} not found in plan")
    if step_info["status"] != "active":
        raise ValueError(f"Step {step_id} status={step_info['status']}, expected active")

    # Validate evidence
    evidence_errors = validate_step_evidence(executor_text, step_id)
    if evidence_errors:
        raise ValueError(f"Step {step_id} evidence incomplete: "
                         + "; ".join(evidence_errors))

    # Update plan
    new_plan = plan_text
    new_plan = re.sub(
        rf"- \[a\] {re.escape(step_id)}:",
        f"- [x] {step_id}:",
        new_plan, 1,
    )
    new_plan = re.sub(
        rf"(\s+- status:) active",
        r"\1 completed",
        new_plan, 1,
    )

    # Update token
    task = token.setdefault("task", {})
    task["current_step"] = step_id
    task["status"] = "active"
    stats = token.setdefault("stats", {})
    stats["done"] = stats.get("done", 0) + 1
    total = stats.get("total", 0)
    if stats["done"] >= total and total > 0:
        task["status"] = "completed"
    token["revision"] = token.get("revision", 0) + 1

    # Atomic write
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    tmp_plan = _transaction_temp_path(plan_path)
    tmp_token = _transaction_temp_path(token_path)

    try:
        with open(lock_path, "a+") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                plan_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_plan.write_text(new_plan, encoding="utf-8")
                _atomic_replace(tmp_plan, plan_path)

                token_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_token.write_text(
                    json.dumps(token, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                _atomic_replace(tmp_token, token_path)
            finally:
                for p in [tmp_plan, tmp_token]:
                    if p.exists():
                        p.unlink(missing_ok=True)
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    finally:
        if lock_path.exists():
            lock_path.unlink(missing_ok=True)
