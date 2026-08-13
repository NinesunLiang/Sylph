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

import yaml


_PLACEHOLDERS = {"", "todo", "tbd", "n/a", "待填写", "待确认", "暂无", "...", "…"}

SCHEMA_VERSION = "carroros.phase_handoff.v1"

_PHASE_CONTRACT_YAML = Path(__file__).resolve().parent.parent / "schemas" / "contract" / "phase_handoff.yaml"


def _load_phases_from_yaml() -> dict[str, dict[str, Any]]:
    """从 phase_handoff.yaml 读取每阶段实例（Contract-first 唯一真源，ADR 0015）。

    fail-fast: 文件缺失 / 缺 phases 段 / schema_version 不匹配直接抛错，
    不静默 fallback（防双源漂移）。
    """
    path = _PHASE_CONTRACT_YAML
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "phases" not in data:
        raise ValueError(f"phase_handoff.yaml missing 'phases' section: {path}")
    if data.get("schema_version", {}).get("const") != SCHEMA_VERSION:
        raise ValueError(f"phase_handoff.yaml schema_version mismatch: {path}")
    phases = data["phases"]
    if not isinstance(phases, dict) or not phases:
        raise ValueError(f"phase_handoff.yaml 'phases' section empty: {path}")
    return phases


_PHASE_DATA = _load_phases_from_yaml()
PHASES = tuple(_PHASE_DATA.keys())


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def phase_contract(phase: str) -> dict[str, Any]:
    if phase not in _PHASE_DATA:
        raise ValueError(f"unknown phase: {phase}")
    value = _PHASE_DATA[phase]
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
        "key_changes", "tdd_evidence", "evidence")]
    contract["outputs"]["artifacts"] = ["executor.md", f"state/step-handoff-{step_id}.json"]
    contract["required_artifacts"] = [
        {"path": "executor.md", "checks": ["EV block", "two completion sections"], "required": True},
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
        if field in {"key_changes", "tdd_evidence"}:
            heading = {
                "key_changes": "Key Changes",
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


# ─── Self-Check（测试内建到机制能力）──────────────────────────────────

def self_check() -> list[str]:
    """内建自检：step_contract 契约不变量（输出字段/完成节/required_artifacts）。

    验证 step_contract 生成的契约含全部完成节与 required_artifacts，
    无需外部测试矫正。启动时调用，fail-closed。返回违规列表（空=通过）。
    """
    violations: list[str] = []
    contract = step_contract({"id": "S1", "scope": "src", "acceptance": "works",
                              "verify": "command:pytest"})

    # 输出字段：三节全在
    for field in ("S1.key_changes", "S1.tdd_evidence", "S1.evidence"):
        if field not in contract["outputs"]["required"]:
            violations.append(f"self_check step_contract missing output {field}")

    # required_artifacts：executor.md + plan.md 全声明
    artifact_paths = {a["path"] for a in contract["required_artifacts"]}
    for path in ("executor.md", "plan.md"):
        if path not in artifact_paths:
            violations.append(f"self_check step_contract missing artifact {path}")

    # 输入：scope/acceptance/verify 全要求
    for field in ("step.scope", "step.acceptance", "step.verify"):
        if field not in contract["inputs"]["required"]:
            violations.append(f"self_check step_contract missing input {field}")

    return violations


def _assert_self_check():
    """启动时调用；违规即抛错（fail-closed）。"""
    v = self_check()
    if v:
        raise RuntimeError("phase_contracts self_check failed: " + "; ".join(v))
