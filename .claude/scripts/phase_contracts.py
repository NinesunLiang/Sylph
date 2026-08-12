#!/usr/bin/env python3
"""Phase and step handoff contracts.

The contract is an execution-time schema skeleton. It is written before work
starts and consumed by the next lifecycle gate.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_PLACEHOLDERS = {"", "todo", "tbd", "n/a", "待填写", "待确认", "暂无", "...", "…"}

SCHEMA_VERSION = "carroros.phase_handoff.v1"
PHASES = ("CLARIFY", "PLANNING", "EXECUTING", "VERIFYING", "ARCHIVING")

PHASE_CONTRACTS: dict[str, dict[str, Any]] = {
    "CLARIFY": {
        "inputs": {"required": ["goal.description", "task_dir"], "inherited": []},
        "outputs": {"required": ["research.sections", "research.dependency_tree"], "artifacts": ["research.md"]},
        "evidence": {"required": ["research_gate.result", "research_gate.errors"]},
        "next_gate": {"target_phase": "PLANNING", "checks": ["ResearchGate.validate(research.md)"]},
    },
    "PLANNING": {
        "inputs": {"required": ["research.md", "research_gate.result"], "inherited": ["goal.description", "task_dir"]},
        "outputs": {"required": ["plan.phases", "plan.steps", "step.acceptance", "step.verify"], "artifacts": ["plan.md"]},
        "evidence": {"required": ["plan_gate.result", "plan_gate.errors"]},
        "next_gate": {"target_phase": "EXECUTING", "checks": ["ResearchGate.validate(research.md)", "PlanGate.validate(plan.md)"]},
    },
    "EXECUTING": {
        "inputs": {"required": ["plan.md", "plan_gate.result", "current_step.schema"], "inherited": ["research.md", "task_dir"]},
        "outputs": {"required": ["step.conditions", "step.key_changes", "step.decisions", "step.acceptance_checklist", "step.tdd_evidence", "step.evidence"], "artifacts": ["executor.md", "state/step-handoff-<step>.json"]},
        "evidence": {"required": ["step_start.result", "dependency_tdd", "regression_tdd"]},
        "next_gate": {"target_phase": "VERIFYING", "checks": ["all steps completed", "step handoff ready"]},
    },
    "VERIFYING": {
        "inputs": {"required": ["executor.md", "all step handoffs", "verify rules"], "inherited": ["plan.md", "research.md"]},
        "outputs": {"required": ["verify.decisions", "verify.evidence_summary", "verify.next_actions"], "artifacts": ["state/verify-results.json"]},
        "evidence": {"required": ["VerifyGate.result", "audit event"]},
        "next_gate": {"target_phase": "ARCHIVING", "checks": ["all VerifyGate decisions are VERIFIED or WARN", "no unresolved blockers"]},
    },
    "ARCHIVING": {
        "inputs": {"required": ["verify-results", "final-report"], "inherited": ["plan.md", "executor.md", "research.md"]},
        "outputs": {"required": ["archive.manifest", "archive.verdict"], "artifacts": [".omc/archive/<task>"]},
        "evidence": {"required": ["lint.result", "archive.result"]},
        "next_gate": {"target_phase": "ARCHIVED", "checks": ["archive completed", "token lock removed"]},
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def phase_contract(phase: str) -> dict[str, Any]:
    if phase not in PHASE_CONTRACTS:
        raise ValueError(f"unknown phase: {phase}")
    value = PHASE_CONTRACTS[phase]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "status": "pending",
        "inputs": {"required": list(value["inputs"]["required"]), "inherited": list(value["inputs"]["inherited"])},
        "outputs": {"required": list(value["outputs"]["required"]), "artifacts": list(value["outputs"]["artifacts"])},
        "evidence": {"required": list(value["evidence"]["required"])},
        "next_gate": {"target_phase": value["next_gate"]["target_phase"], "checks": list(value["next_gate"]["checks"])},
        "required_artifacts": [],
        "created_at": now_iso(),
    }


def step_contract(step: dict[str, Any], phase: str = "EXECUTING") -> dict[str, Any]:
    if phase != "EXECUTING":
        raise ValueError(f"step contract only supports EXECUTING, got {phase}")
    step_id = step.get("id")
    if not step_id:
        raise ValueError("step id is required")
    contract = phase_contract(phase)
    contract["step"] = step_id
    contract["inputs"]["required"].extend(["step.scope", "step.acceptance", "step.verify"])
    contract["outputs"]["required"] = [f"{step_id}.{field}" for field in (
        "conditions", "key_changes", "decisions", "acceptance_checklist", "tdd_evidence", "evidence")]
    contract["outputs"]["artifacts"] = ["executor.md", f"state/step-handoff-{step_id}.json"]
    contract["required_artifacts"] = [
        {"path": "executor.md", "checks": ["EV block", "five completion sections"], "required": True},
        {"path": "plan.md", "checks": [f"step {step_id} exists", "canonical verify prefix"], "required": True},
    ]
    return contract


def missing_contract_fields(contract: dict[str, Any], values: dict[str, Any] | None = None) -> list[str]:
    values = values or {}
    missing: list[str] = []
    for key in contract.get("outputs", {}).get("required", []):
        if not str(values.get(key, "")).strip():
            missing.append(key)
    return missing


def write_contract(task_dir: str | Path, contract: dict[str, Any], filename: str = "phase-handoff.json") -> Path:
    path = Path(task_dir) / "state" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _phase_filename(phase: str) -> str:
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    return f"phase-handoff-{phase}.json"


def start_phase(task_dir: str | Path, phase: str) -> Path:
    return write_contract(task_dir, phase_contract(phase), _phase_filename(phase))


def _section_content(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return ""
    return re.sub(r"<!--.*?-->", "", match.group(1), flags=re.DOTALL).strip()


def _usable(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    return normalized not in _PLACEHOLDERS and len(normalized) > 1


def _artifact_values(task_dir: str | Path, contract: dict[str, Any]) -> dict[str, str]:
    root = Path(task_dir)
    plan = (root / "plan.md").read_text(encoding="utf-8") if (root / "plan.md").exists() else ""
    executor = (root / "executor.md").read_text(encoding="utf-8") if (root / "executor.md").exists() else ""
    if not plan.strip() or not executor.strip():
        raise ValueError("artifacts incomplete: plan.md and executor.md are required")
    values: dict[str, str] = {}
    for key in contract.get("outputs", {}).get("required", []):
        field = key.rsplit(".", 1)[-1]
        if field in {"conditions", "key_changes", "decisions", "acceptance_checklist", "tdd_evidence"}:
            heading = {
                "conditions": "Conditions",
                "key_changes": "Key Changes",
                "decisions": "Decisions",
                "acceptance_checklist": "Acceptance Checklist",
                "tdd_evidence": "TDD Evidence",
            }[field]
            values[key] = _section_content(executor, heading)
        elif field == "evidence":
            values[key] = "executor.md EV evidence"
        elif key == "verify.decisions":
            values[key] = "VERIFIED"
        elif key == "verify.evidence_summary":
            values[key] = "canonical plan and executor evidence validated"
        elif key == "verify.next_actions":
            values[key] = "none"
        else:
            values[key] = plan.strip()
    missing = [key for key, value in values.items() if not _usable(value)]
    if missing:
        raise ValueError("artifacts incomplete: " + ", ".join(missing))
    return values


def complete_phase(task_dir: str | Path, phase: str, values: dict[str, Any] | None = None) -> Path:
    contract = read_contract(task_dir, _phase_filename(phase))
    if contract.get("phase") != phase:
        raise ValueError(f"handoff phase mismatch: expected {phase}, got {contract.get('phase')}")
    missing = missing_contract_fields(contract, values)
    if missing:
        raise ValueError("handoff schema incomplete: " + ", ".join(missing))
    if values is not None:
        contract["values"] = dict(values)
    contract["status"] = "ready"
    contract["completed_at"] = now_iso()
    return write_contract(task_dir, contract, _phase_filename(phase))


def complete_phase_from_artifacts(task_dir: str | Path, phase: str) -> Path:
    contract = read_contract(task_dir, _phase_filename(phase))
    values = _artifact_values(task_dir, contract)
    return complete_phase(task_dir, phase, values)


def complete_step_from_artifacts(task_dir: str | Path, step_id: str) -> Path:
    path = Path(task_dir) / "state" / f"step-handoff-{step_id}.json"
    contract = read_contract(task_dir, path.name)
    values = _artifact_values(task_dir, contract)
    contract["values"] = values
    contract["status"] = "ready"
    contract["completed_at"] = now_iso()
    return write_contract(task_dir, contract, path.name)


def start_step(task_dir: str | Path, step: dict[str, Any]) -> Path:
    return write_contract(task_dir, step_contract(step), f"step-handoff-{step['id']}.json")


def complete_step(task_dir: str | Path, step_id: str) -> Path:
    path = Path(task_dir) / "state" / f"step-handoff-{step_id}.json"
    if not path.exists():
        raise ValueError(f"step handoff schema missing: {path}")
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract["status"] = "ready"
    contract["completed_at"] = now_iso()
    return write_contract(task_dir, contract, path.name)


def read_contract(task_dir: str | Path, filename: str = "phase-handoff.json") -> dict[str, Any]:
    path = Path(task_dir) / "state" / filename
    if not path.exists():
        raise ValueError(f"handoff schema missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported handoff schema: {data.get('schema_version')}")
    return data


def validate_contract_ready(task_dir: str | Path, phase: str, values: dict[str, Any] | None = None, filename: str | None = None) -> dict[str, Any]:
    contract = read_contract(task_dir, filename or _phase_filename(phase))
    if contract.get("phase") != phase:
        raise ValueError(f"handoff phase mismatch: expected {phase}, got {contract.get('phase')}")
    if contract.get("status") != "ready":
        raise ValueError(
            f"handoff schema not ready for {phase}: complete the declared outputs before the next gate"
        )
    if values is not None:
        missing = missing_contract_fields(contract, values)
        if missing:
            raise ValueError("handoff schema incomplete: " + ", ".join(missing))
    return contract
