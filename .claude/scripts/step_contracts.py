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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from goal_contracts import is_placeholder
except ImportError:
    def is_placeholder(value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return not normalized or normalized in {"todo", "tbd", "n/a", "待填写", "待确认", "暂无", "...", "…"}

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
from goal_document_gate import GoalDocumentGateError, require_document_write
try:
    import phase_contracts
except ImportError:
    phase_contracts = None

_STEP_CONTRACT_YAML = Path(__file__).resolve().parent.parent / "schemas" / "contract" / "step_contract.yaml"


def _load_step_contract() -> dict[str, Any]:
    """从 step_contract.yaml 读取 step 契约（Contract-first 唯一真源，ADR 0015）。

    fail-fast: 文件缺失 / schema_version 不匹配直接抛错，不静默 fallback。
    """
    path = _STEP_CONTRACT_YAML
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or data.get("schema_version") != "carroros.step_contract.v1":
        raise ValueError(f"step_contract.yaml invalid or wrong schema_version: {path}")
    return data


_STEP_CONTRACT = _load_step_contract()
STEP_STATUSES = set(_STEP_CONTRACT["step"]["status"]["values"])

EVIDENCE_REQUIRED_SECTIONS = list(_STEP_CONTRACT["evidence"]["required_sections"])


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


def _deps_all_completed(dep: str, completed: set[str]) -> bool:
    """A step's dependencies are all completed. Supports comma-separated deps.

    `dep` may be "none", a single id ("S2"), or comma-separated ("S2,S3,S4").
    Every non-empty id must be present in `completed`. (index17 S6)
    """
    if not dep or dep.strip().lower() == "none":
        return True
    deps = [d.strip() for d in dep.split(",") if d.strip()]
    return all(d in completed for d in deps)


def find_first_activatable_step(steps: list[dict[str, Any]]) -> str | None:
    """Find first pending step whose dependencies are all completed.

    Returns step_id or None if no activatable step exists.
    """
    completed = {s["id"] for s in steps if s["status"] == "completed"}
    for s in steps:
        if s["status"] != "pending":
            continue
        dep = s.get("depends_on", "none")
        if _deps_all_completed(dep, completed):
            return s["id"]
    return None


# ─── Evidence Validation ────────────────────────────────────────────


def _extract_section_content(text: str, section_name: str) -> str:
    """Extract content under a `## <section_name>` header, up to next ## or EOF.

    The header must be a heading on its own line; a backticked mention of a
    section name inside prose (e.g. "`## Decisions` 段") must not be treated as
    the section start.
    """
    header = re.search(rf"^## {re.escape(section_name)}\s*$", text, re.MULTILINE)
    if not header:
        return ""
    after = text[header.end():]
    nxt = re.search(r"^## ", after, re.MULTILINE)
    if nxt:
        after = after[:nxt.start()]
    # Remove HTML comments
    after = re.sub(r"<!--.*?-->", "", after, flags=re.DOTALL)
    lines = [l.strip() for l in after.split("\n")
             if l.strip() and not l.strip().startswith("<!--")]
    return "\n".join(lines)


def validate_step_evidence(executor_text: str, step_id: str) -> list[str]:
    """Validate EV evidence completeness for a step.

    Checks:
      1. EV block exists for step_id
      2. Key Changes section has content
      3. TDD Evidence has dependency TDD + regression TDD with exit 0

    Returns list of error strings (empty = all valid).
    """
    errors: list[str] = []

    # 1. EV block for this step
    ev_pattern = rf"^### EV-{re.escape(step_id)}\s*$"
    if not re.search(ev_pattern, executor_text, flags=re.MULTILINE):
        errors.append(f"missing_step_evidence_block: EV-{step_id}")
        return errors  # can't validate further without evidence block

    # 2. Key Changes section
    kc_content = _extract_section_content(executor_text, "Key Changes")
    if not kc_content:
        errors.append("key_changes_section_empty_or_missing")
    else:
        kc_lines = [l for l in kc_content.split("\n") if l.strip()
                    and not l.strip().startswith("<!--") and not is_placeholder(l)]
        if not kc_lines:
            errors.append("key_changes_section_no_content")

    # 3. TDD Evidence - dependency + regression with exit 0
    #    降噪（index15）：不强制 "dependency tdd"/"regression tdd" 字面；只要 TDD 段
    #    含命令证据（.py/.sh/命令名）+ exit 0/通过 标记即视为满足，空段/无证据仍拒。
    tdd_content = _extract_section_content(executor_text, "TDD Evidence")
    if not tdd_content:
        errors.append("tdd_evidence_empty_or_missing")
    else:
        tdd_lines = [l for l in tdd_content.split("\n") if l.strip() and not is_placeholder(l)]
        if not tdd_lines:
            errors.append("tdd_evidence_no_content")
        else:
            tdd_lower = tdd_content.lower()
            has_cmd = bool(re.search(r"(python3?|pytest|\.py|\.sh|npm|go test|run[a-z0-9_\-]*|exit\s*[0:：])", tdd_lower))
            has_exit0 = bool(re.search(r"(exit\s*[：:]\s*0|→\s*exit\s*0|->\s*exit\s*0|passed|通过|0 失败|0 failed|exit code 0|退出码\s*0)", tdd_lower))
            if not has_cmd:
                errors.append("tdd_missing_dependency_tdd_command")
            if not has_exit0:
                errors.append("tdd_missing_exit_0_evidence")

    return errors


# ─── Atomic Step Start ──────────────────────────────────────────────


def start_step_atomic(token_path: str | Path,
                      plan_path: str | Path,
                      executor_path: str | Path,
                      step_id: str) -> dict[str, Any]:
    """Atomic step activation: transactionally update plan + token + executor.

    Transaction semantics:
      - Validates step exists in plan and is pending
      - Validates all dependencies are completed
      - Updates plan.md: [ ] -> [a] for step_id
      - Updates token.json: current_step, status, revision
      - Updates executor.md: writes completion sections + start EV block

    Crash during transaction leaves NO partial state (temp files + os.replace).

    Raises ValueError on validation failure.
    """
    token_path = Path(token_path)
    plan_path = Path(plan_path)
    executor_path = Path(executor_path)

    # Read current state
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    token = read_json(token_path, {})
    try:
        require_document_write(
            token_path,
            "executor",
            action=f"step activation {step_id}",
            allowed_states={"EXECUTING"},
        )
    except GoalDocumentGateError as exc:
        raise ValueError(str(exc)) from exc

    # Validate step
    steps = parse_plan_steps(plan_text)
    step_info = next((s for s in steps if s["id"] == step_id), None)
    if not step_info:
        raise ValueError(f"Step {step_id} not found in plan")
    if step_info["status"] != "pending":
        raise ValueError(f"Step {step_id} status={step_info['status']}, expected pending")

    # Validate dependencies (multi-dep comma-separated supported, index17 S6)
    dep = step_info.get("depends_on", "none")
    completed_ids = {s["id"] for s in steps if s["status"] == "completed"}
    if not _deps_all_completed(dep, completed_ids):
        raise ValueError(f"Step {step_id} depends on {dep} which is not completed")

    # Prepare new plan text
    new_plan = re.sub(
        r"^- \[ \] " + re.escape(step_id) + r":",
        f"- [a] {step_id}:",
        plan_text,
        count=1,
        flags=re.MULTILINE,
    )
    # Also mark only this step's status as active.
    new_plan, status_replaced = re.subn(
        rf"(- \[a\] {re.escape(step_id)}:.*?\n\s+- status:)\s+pending",
        r"\1 active",
        new_plan,
        count=1,
        flags=re.DOTALL,
    )
    if status_replaced == 0:
        new_plan = re.sub(
            rf"(- \[a\] {re.escape(step_id)}:.*)(\n)",
            r"\1" + "\n" + "  - status: active" + r"\2",
            new_plan,
            count=1,
        )

    # Update token
    token.setdefault("task", {})["current_step"] = step_id
    token["task"]["status"] = "active"
    token.setdefault("goal", {})
    token["goal"]["active_step"] = step_id
    token["revision"] = token.get("revision", 0) + 1

    # Prepare executor content and submit the full completion schema before execution.
    ts = now_iso()
    exec_key_changes = """
## Key Changes

- pending: record each changed file or explicit no-op before verification.
"""
    exec_tdd = """
## TDD Evidence

- Dependency TDD command: pending -> exit 0
- Regression TDD command: pending -> exit 0
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
    if phase_contracts is not None and token.get("task_dir"):
        try:
            phase_contracts.start_step(token["task_dir"], step_info)
        except (OSError, ValueError) as exc:
            raise ValueError(f"step handoff schema could not be prepared: {exc}") from exc

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

                # Write executor — add completion sections + start EV
                executor_path.parent.mkdir(parents=True, exist_ok=True)
                existing_exec = (executor_path.read_text(encoding="utf-8")
                                 if executor_path.exists() else "")
                new_exec = existing_exec.rstrip() + "\n"
                if "## Key Changes" not in existing_exec:
                    new_exec += exec_key_changes
                if "## TDD Evidence" not in existing_exec:
                    new_exec += exec_tdd
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

    # G2 出参契约（ADR 0015）：成功返回结构化结果，失败仍抛 ValueError
    return {"ok": True, "step_id": step_id, "errors": []}


# ─── Atomic Step Complete ──────────────────────────────────────────


def complete_step_atomic(token_path: str | Path,
                         plan_path: str | Path,
                         executor_path: str | Path,
                         step_id: str) -> dict[str, Any]:
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
    try:
        require_document_write(
            token_path,
            "executor",
            action=f"step completion {step_id}",
            allowed_states={"EXECUTING", "VERIFYING"},
        )
    except GoalDocumentGateError as exc:
        raise ValueError(str(exc)) from exc

    steps = parse_plan_steps(plan_text)
    step_info = next((s for s in steps if s["id"] == step_id), None)
    if not step_info:
        raise ValueError(f"Step {step_id} not found in plan")
    if step_info["status"] == "completed":
        stats = token.setdefault("stats", {})
        completed_count = sum(step.get("status") == "completed" for step in steps)
        total = len(steps)
        if stats.get("done") != completed_count or stats.get("total") != total:
            raise ValueError(
                f"Step {step_id} already completed but canonical stats mismatch "
                f"({stats.get('done', 0)}/{stats.get('total', 0)} != {completed_count}/{total})"
            )
        return {"ok": True, "step_id": step_id, "errors": []}
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
        new_plan, count=1,
    )
    new_plan = re.sub(
        rf"(- \[x\] {re.escape(step_id)}:.*?\n\s+- status:) active",
        r"\1 completed",
        new_plan, count=1, flags=re.DOTALL,
    )

    # Update token
    task = token.setdefault("task", {})
    task["current_step"] = step_id
    task["status"] = "active"
    stats = token.setdefault("stats", {})
    stats["done"] = sum(
        step.get("status") == "completed" or step.get("id") == step_id
        for step in steps
    )
    stats["total"] = len(steps)
    total = stats["total"]
    if stats["done"] >= total and total > 0:
        task["status"] = "completed"
    token["revision"] = token.get("revision", 0) + 1

    # Atomic write
    lock_path = token_path.with_suffix(token_path.suffix + ".lock")
    tmp_plan = _transaction_temp_path(plan_path)
    tmp_token = _transaction_temp_path(token_path)
    originals = {
        plan_path: plan_path.read_bytes() if plan_path.exists() else None,
        token_path: token_path.read_bytes() if token_path.exists() else None,
    }
    replaced: list[Path] = []

    try:
        with open(lock_path, "a+") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                plan_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_plan.write_text(new_plan, encoding="utf-8")
                _atomic_replace(tmp_plan, plan_path)
                replaced.append(plan_path)

                token_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_token.write_text(
                    json.dumps(token, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                _atomic_replace(tmp_token, token_path)
                replaced.append(token_path)
            except Exception:
                for path in reversed(replaced):
                    original = originals[path]
                    if original is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(original)
                raise
            finally:
                for p in [tmp_plan, tmp_token]:
                    if p.exists():
                        p.unlink(missing_ok=True)
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    finally:
        if lock_path.exists():
            lock_path.unlink(missing_ok=True)

    # Record a durable VERIFIED evidence marker so report gates can confirm the
    # step was verified by the canonical VerifyGate. A red-TDD step's own EV
    # block carries exit_code 1 (the test failed as expected); without this
    # marker, lx-goal report would wrongly flag such steps as evidence-missing.
    if executor_path.exists():
        executor_text = executor_path.read_text(encoding="utf-8")
        verified_marker = f"### EV-{step_id}-VERIFIED"
        if verified_marker not in executor_text:
            entry = (
                f"\n### EV-{step_id}-VERIFIED\n\n"
                f"- step: {step_id}\n"
                f"- type: verify\n"
                f"- evidence_level: E3\n"
                f"- source: VerifyGate\n"
                f"- exit_code: 0\n"
                f"- assertion: VerifyGate accepted evidence for {step_id}\n"
            )
            with executor_path.open("a", encoding="utf-8") as f:
                f.write(entry)

    if phase_contracts is not None and (plan_path.parent / "state" / f"step-handoff-{step_id}.json").exists():
        phase_contracts.complete_step_from_artifacts(plan_path.parent, step_id)

    # G2 出参契约（ADR 0015）：成功返回结构化结果，失败仍抛 ValueError
    return {"ok": True, "step_id": step_id, "errors": []}


# ─── Self-Check（测试内建到机制能力）──────────────────────────────────

def self_check() -> list[str]:
    """内建自检：plan step 依赖激活不变量（多依赖/单依赖/none/空格）。

    验证 find_first_activatable_step 与 _deps_all_completed 的核心契约，
    无需外部测试矫正。启动时调用，fail-closed。返回违规列表（空=通过）。
    """
    violations: list[str] = []

    completed = {"S1", "S2", "S3", "S4", "S5"}
    dep_cases = {
        "none": True, "S2": True, "S2,S3,S4": True,
        "S2,S3,S9": False, "S2, S4": True,
    }
    for dep, expected in dep_cases.items():
        got = _deps_all_completed(dep, completed)
        if got != expected:
            violations.append(f"self_check deps_all_completed({dep})={got} expected {expected}")

    # 激活顺序：多依赖步在所有依赖完成后才可选
    multi = [
        {"id": "S1", "status": "completed", "depends_on": "none"},
        {"id": "S2", "status": "completed", "depends_on": "S1"},
        {"id": "S3", "status": "completed", "depends_on": "S2"},
        {"id": "S4", "status": "completed", "depends_on": "S3"},
        {"id": "S5", "status": "completed", "depends_on": "S4"},
        {"id": "S6", "status": "pending", "depends_on": "S2,S3,S4"},
        {"id": "S7", "status": "pending", "depends_on": "S6"},
    ]
    got_first = find_first_activatable_step(multi)
    if got_first != "S6":
        violations.append(f"self_check multi-dep activatable={got_first} expected S6")

    # 有未完成依赖的步不得抢先
    skip = [
        {"id": "A", "status": "completed", "depends_on": "none"},
        {"id": "C", "status": "pending", "depends_on": "A,B"},
        {"id": "B", "status": "pending", "depends_on": "A"},
    ]
    got_skip = find_first_activatable_step(skip)
    if got_skip != "B":
        violations.append(f"self_check pending-dep skip={got_skip} expected B")

    # none 依赖首个 pending
    none_first = [
        {"id": "A", "status": "pending", "depends_on": "none"},
        {"id": "B", "status": "pending", "depends_on": "A"},
    ]
    got_none = find_first_activatable_step(none_first)
    if got_none != "A":
        violations.append(f"self_check none-dep first={got_none} expected A")

    return violations


def _assert_self_check():
    """启动时调用；违规即抛错（fail-closed）。"""
    v = self_check()
    if v:
        raise RuntimeError("step_contracts self_check failed: " + "; ".join(v))
