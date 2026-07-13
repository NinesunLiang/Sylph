#!/usr/bin/env python3
"""
formal_seal.py — generate CarrorOS RC2 formal evidence seal artifacts.

This seals RC2 evidence only. It must not mark GA complete.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

PROJECT = Path(__file__).resolve().parents[2]
VERIFY_DIR = PROJECT / ".omc" / "metrics" / "runtime-verify"
FINAL_DIR = PROJECT / "improve_plan" / "final_round"
EVIDENCE = VERIFY_DIR / "evidence.jsonl"
CAS_EVIDENCE = VERIFY_DIR / "h-cas-stale-evidence.json"
GA_EVIDENCE = {
    "GA-CAS-01": VERIFY_DIR / "h-concurrent-writer-conflict.json",
    "GA-CAS-02": VERIFY_DIR / "h-concurrent-writer-conflict.json",
    "GA-L5-01": VERIFY_DIR / "h-l5-recovery.json",
    "GA-L5-02": VERIFY_DIR / "h-artifact-missing.json",
    "GA-WATER-01": VERIFY_DIR / "h-water-critical-hard-pause.json",
    "GA-WATER-02": VERIFY_DIR / "h-water-pretool-whitelist.json",
}
GA_OBSERVABILITY = PROJECT / ".omc" / "metrics" / "ga" / "observability.json"
MANIFEST = VERIFY_DIR / "manifest.json"
SHA256SUMS = VERIFY_DIR / "sha256sums.txt"
ACCEPTANCE_IDENTITY = FINAL_DIR / "acceptance-identity.yaml"
FINAL_MANIFEST = FINAL_DIR / "rc2-formal-seal-manifest.json"
README = FINAL_DIR / "README.md"
GA_GATES = FINAL_DIR / "remaining-ga-gates.md"
ALIGNMENT = FINAL_DIR / "00-final-alignment.md"

SECRET_KEYS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "AUTH")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, cwd=str(PROJECT), capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = {"test": "MALFORMED_JSONL", "status": "FAIL", "raw": line[:200]}
        if isinstance(obj, dict):
            records.append(obj)
    return records


def test_id(record: dict[str, Any]) -> str:
    value = record.get("test") or record.get("test_id") or record.get("id") or record.get("name") or "UNKNOWN"
    return str(value)


def status_of(record: dict[str, Any]) -> str:
    return str(record.get("status") or "UNKNOWN").upper()


def collect_environment() -> dict[str, Any]:
    rc, commit, _ = run(["git", "rev-parse", "HEAD"])
    rc_status, status, _ = run(["git", "status", "--short"])
    # Do not call `claude --version` here: some installs trigger login checks even
    # when this project uses ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN API routing.
    claude_version = "not_checked_api_key_mode"
    env: dict[str, str] = {}
    for key in sorted(os.environ):
        if key.startswith(("ANTHROPIC_", "CLAUDE_", "CARROROS_")):
            if any(secret in key.upper() for secret in SECRET_KEYS):
                env[key] = "<redacted>"
            else:
                env[key] = os.environ.get(key, "")
    return {
        "generated_at": now_iso(),
        "git_commit_full": commit if rc == 0 else "UNKNOWN",
        "git_dirty_current_worktree": bool(status.strip()) if rc_status == 0 else None,
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "claude_version": claude_version,
        "env": env,
    }


def cas_evidence_ok() -> bool:
    if not CAS_EVIDENCE.exists():
        return False
    try:
        data = json.loads(CAS_EVIDENCE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        data.get("test_id") == "H-CAS-STALE"
        and data.get("status") == "PASS"
        and data.get("stale_write_applied") is False
        and data.get("writer_b", {}).get("result") == "CAS_CONFLICT"
    )


def structured_evidence_ok(path: Path, expected_test_id: str | None = None) -> tuple[bool, dict[str, Any] | None]:
    if not path.exists():
        return False, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, None
    if expected_test_id and data.get("test_id") != expected_test_id:
        return False, data
    return data.get("status") == "PASS", data


def build_ga_gates() -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    labels = {
        "GA-CAS-01": "cross-process serialized writer lock",
        "GA-CAS-02": "concurrent writer conflict proof",
        "GA-L5-01": "L5 recovery does not use summary as SOOT",
        "GA-L5-02": "missing artifact returns MISSING_ARTIFACT",
        "GA-WATER-01": "persistent PAUSED_CONTEXT_CRITICAL",
        "GA-WATER-02": "PreToolUse hard whitelist while paused",
    }
    expected = {
        "GA-CAS-01": "H-CONCURRENT-WRITER-CONFLICT",
        "GA-CAS-02": "H-CONCURRENT-WRITER-CONFLICT",
        "GA-L5-01": "H-L5-RECOVERY",
        "GA-L5-02": "H-ARTIFACT-MISSING",
        "GA-WATER-01": "H-WATER-CRITICAL-HARD-PAUSE",
        "GA-WATER-02": "H-WATER-PRETOOL-WHITELIST",
    }
    for gate, path in GA_EVIDENCE.items():
        ok, data = structured_evidence_ok(path, expected.get(gate))
        gates[gate] = {
            "label": labels[gate],
            "status": "PASS" if ok else "PENDING",
            "evidence": str(path.relative_to(PROJECT)) if path.exists() else None,
            "sha256": sha256_file(path) if path.exists() else None,
        }
        if data and gate == "GA-L5-02":
            gates[gate]["result"] = data.get("result")
        if data and gate == "GA-WATER-01":
            gates[gate]["pause_state_persisted"] = data.get("pause_state_persisted")
    if GA_OBSERVABILITY.exists():
        try:
            obs_data = json.loads(GA_OBSERVABILITY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            obs_data = {}
        obs_status = obs_data.get("gate_status", {}) if isinstance(obs_data, dict) else {}
        for gate in ("GA-OBS-01", "GA-OBS-02", "GA-OBS-03", "GA-OBS-04"):
            gates[gate] = {
                "label": {
                    "GA-OBS-01": "30+ turn session distribution",
                    "GA-OBS-02": "L5 ratio",
                    "GA-OBS-03": "cost per session/task",
                    "GA-OBS-04": "cache or stable-prefix metric",
                }[gate],
                "status": obs_status.get(gate, "INSTRUMENTED_PENDING_SAMPLE"),
                "evidence": str(GA_OBSERVABILITY.relative_to(PROJECT)),
                "sha256": sha256_file(GA_OBSERVABILITY),
            }
    else:
        gates.update({
            "GA-OBS-01": {"label": "30+ turn session distribution", "status": "PENDING", "reason": "requires real longitudinal session population"},
            "GA-OBS-02": {"label": "L5 ratio", "status": "PENDING", "reason": "requires longitudinal compact/L5 counts"},
            "GA-OBS-03": {"label": "cost per session/task", "status": "PENDING", "reason": "requires real cost data"},
            "GA-OBS-04": {"label": "cache or stable-prefix metric", "status": "PENDING", "reason": "requires cache usage or stable-prefix sample"},
        })
    gates["GA-OC-01"] = {"label": "OpenCode independent certification", "status": "PENDING", "reason": "requires separate OpenCode proof package"}
    return gates


def build_manifest() -> dict[str, Any]:
    records = read_jsonl(EVIDENCE)
    latest_by_test: dict[str, dict[str, Any]] = {}
    for record in records:
        latest_by_test[test_id(record)] = record
    latest_records = list(latest_by_test.values())
    statuses = [status_of(r) for r in latest_records]
    tests = [test_id(r) for r in latest_records]
    passed = statuses.count("PASS")
    failed = statuses.count("FAIL")
    skipped = statuses.count("SKIP") + statuses.count("SKIPPED")
    unique_tests = sorted(set(tests))
    env = collect_environment()
    ga_gates = build_ga_gates()
    evidence_sha = sha256_file(EVIDENCE) if EVIDENCE.exists() else None
    cas_sha = sha256_file(CAS_EVIDENCE) if CAS_EVIDENCE.exists() else None
    seal_blockers: list[str] = []
    if not EVIDENCE.exists():
        seal_blockers.append("missing evidence.jsonl")
    if failed:
        seal_blockers.append(f"evidence contains {failed} failed record(s)")
    if not cas_evidence_ok():
        seal_blockers.append("H-CAS-STALE structured evidence missing or invalid")

    return {
        "schema": "carroros.rc2.runtime_acceptance_manifest.v1",
        "seal_type": "RC2_FORMAL_EVIDENCE",
        "formal_evidence_seal": "SEALED" if not seal_blockers else "BLOCKED",
        "ga_ready": False,
        "ga_readiness": "BLOCKED",
        "generated_at": env["generated_at"],
        "product": "CarrorOS Base 1.0 RC2 — Claude Code",
        "git": {
            "commit_full": env["git_commit_full"],
            "dirty_current_worktree": env["git_dirty_current_worktree"],
        },
        "environment": env,
        "suite": {
            "total_executions": len(records),
            "latest_execution_counted": len(latest_records),
            "total_unique_tests": len(unique_tests),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "unique_test_ids": unique_tests,
        },
        "artifacts": {
            "evidence_path": str(EVIDENCE.relative_to(PROJECT)),
            "evidence_sha256": evidence_sha,
            "h_cas_stale_evidence_path": str(CAS_EVIDENCE.relative_to(PROJECT)) if CAS_EVIDENCE.exists() else None,
            "h_cas_stale_evidence_sha256": cas_sha,
        },
        "ga_gates": ga_gates,
        "runner_commands": [
            "python3 .claude/scripts/negative_tests.py",
            "python3 .claude/scripts/runtime_verify.py",
            "python3 .claude/scripts/capture_evidence.py",
            "python3 .claude/scripts/formal_seal.py",
        ],
        "seal_blockers": seal_blockers,
        "not_certified": [
            "CarrorOS GA",
            "OpenCode path",
            "dual-stack base",
            "multi-session concurrent writing",
            "unattended production operation",
            "L5 recovery verified",
            "Qwen3.6-27B production certification",
        ],
    }


def update_final_round(manifest: dict[str, Any]) -> None:
    sealed = manifest["formal_evidence_seal"] == "SEALED"
    evidence_records = manifest["suite"]["total_executions"]
    evidence_sha = manifest["artifacts"]["evidence_sha256"]
    cas_sha = manifest["artifacts"]["h_cas_stale_evidence_sha256"]
    manifest_sha = sha256_file(MANIFEST)

    acceptance = {
        "acceptance_identity": {
            "product": "CarrorOS Base 1.0 RC2 — Claude Code",
            "verdict": "APPROVE_RC2_ENGINEERING_RELEASE",
            "formal_evidence_status": "SEALED" if sealed else "BLOCKED",
            "generated_at": manifest["generated_at"],
            "git_commit_full": manifest["git"]["commit_full"],
            "git_dirty_current_worktree": manifest["git"]["dirty_current_worktree"],
            "certification_scope": {
                "platform": "Claude Code only",
                "writers": 1,
                "sessions_per_task": 1,
                "unattended": False,
                "modes": ["L1 short tasks", "L1 medium tasks with human checkpoint", "L2 supervised tasks with explicit human gate"],
            },
        },
        "suite": manifest["suite"],
        "observed_artifacts": {
            "evidence": {
                "path": manifest["artifacts"]["evidence_path"],
                "records": evidence_records,
                "sha256": evidence_sha,
            },
            "h_cas_stale_evidence": {
                "path": manifest["artifacts"]["h_cas_stale_evidence_path"],
                "sha256": cas_sha,
            },
            "manifest": {
                "path": str(MANIFEST.relative_to(PROJECT)),
                "sha256": manifest_sha,
                "status": "PRESENT",
            },
            "sha256sums": {
                "path": str(SHA256SUMS.relative_to(PROJECT)),
            },
        },
        "formal_seal": {
            "status": "SEALED" if sealed else "BLOCKED",
            "blockers": manifest["seal_blockers"],
        },
        "ga_gates": manifest.get("ga_gates", {}),
        "ga_ready": False,
        "not_certified": manifest["not_certified"],
    }
    write_yaml(ACCEPTANCE_IDENTITY, acceptance)

    final_manifest = {
        "schema": "carroros.rc2.formal_seal_manifest.v1",
        "generated_at": manifest["generated_at"],
        "product": "CarrorOS Base 1.0 RC2 — Claude Code",
        "aligned_verdict": {
            "engineering_release": "APPROVED",
            "formal_evidence_seal": "SEALED" if sealed else "BLOCKED",
            "ga_ready": False,
            "round_4_architecture_required": False,
        },
        "certified_scope": acceptance["acceptance_identity"]["certification_scope"],
        "review_inputs": [
            {"path": "improve_plan/final_round/opus-4.8.md", "verdict": "APPROVE_RC2", "score": "8.4/10"},
            {"path": "improve_plan/final_round/gpt-5.6Sol.md", "verdict": "CONDITIONAL_APPROVE_RC2", "score": "8.1/10"},
            {"path": "improve_plan/final_round/grok-4.5.md", "verdict": "APPROVE_RC2", "score": "8.35/10"},
        ],
        "aligned_outputs": [
            "improve_plan/final_round/README.md",
            "improve_plan/final_round/00-final-alignment.md",
            "improve_plan/final_round/acceptance-identity.yaml",
            "improve_plan/final_round/remaining-ga-gates.md",
            "improve_plan/final_round/h-cas-stale-evidence-template.json",
            "improve_plan/final_round/rc2-formal-seal-manifest.json",
        ],
        "observed_evidence": {
            "git_commit_full": manifest["git"]["commit_full"],
            "git_dirty_current_worktree": manifest["git"]["dirty_current_worktree"],
            "evidence_path": manifest["artifacts"]["evidence_path"],
            "evidence_records": evidence_records,
            "evidence_sha256": evidence_sha,
            "runtime_verify_manifest_path": str(MANIFEST.relative_to(PROJECT)),
            "runtime_verify_manifest_sha256": manifest_sha,
            "h_cas_stale_evidence_path": manifest["artifacts"]["h_cas_stale_evidence_path"],
            "h_cas_stale_evidence_sha256": cas_sha,
        },
        "suite": manifest["suite"],
        "ga_gates": manifest.get("ga_gates", {}),
        "formal_seal_blockers": manifest["seal_blockers"],
        "not_certified": manifest["not_certified"],
    }
    write_json(FINAL_MANIFEST, final_manifest)

    if README.exists():
        text = README.read_text(encoding="utf-8")
        text = text.replace("formal_evidence_seal: PARTIAL_SEALED", f"formal_evidence_seal: {'SEALED' if sealed else 'BLOCKED'}")
        text = text.replace("Two things are intentionally not marked complete because the repo evidence does not support doing so:", "Formal RC2 evidence seal status:")
        text = text.replace(
            "1. Formal evidence seal is still partial until a real `manifest.json` exists with unique test IDs, execution counts, environment fingerprint, and hashes generated in the same acceptance run.\n2. `H-CAS-STALE` is clarified at the document level, but still needs structured raw evidence showing `stale_write_applied=false` and `CAS_CONFLICT`.\n\nThese are not RC2 engineering blockers. They are formal archive blockers and GA hardening inputs.",
            "1. Formal RC2 evidence seal is sealed when `formal_evidence_seal: SEALED`.\n2. GA remains incomplete and blocked by the gates listed in `remaining-ga-gates.md`.\n\nThe seal does not certify GA, OpenCode, multi-writer support, unattended production, or L5 recovery.",
        )
        README.write_text(text, encoding="utf-8")

    if GA_GATES.exists():
        text = GA_GATES.read_text(encoding="utf-8")
        text = text.replace("- formal RC2 archive seal blockers\n- GA blockers", "- formal RC2 archive seal status\n- remaining GA blockers")
        text = text.replace("## 1. Formal RC2 Archive Seal Blockers", "## 1. Formal RC2 Archive Seal Status")
        start = text.find("| ID | Item | Current status | Required evidence |")
        end = text.find("---", start)
        if start != -1 and end != -1:
            replacement = (
                "```yaml\n"
                f"formal_evidence_seal: {'SEALED' if sealed else 'BLOCKED'}\n"
                f"manifest: {str(MANIFEST.relative_to(PROJECT))}\n"
                f"sha256sums: {str(SHA256SUMS.relative_to(PROJECT))}\n"
                "ga_ready: false\n"
                "```\n\n"
            )
            text = text[:start] + replacement + text[end:]
        GA_GATES.write_text(text, encoding="utf-8")

    if ALIGNMENT.exists():
        text = ALIGNMENT.read_text(encoding="utf-8")
        text = text.replace("formal_evidence_seal: PARTIAL_SEALED", f"formal_evidence_seal: {'SEALED' if sealed else 'BLOCKED'}")
        text = text.replace("formal_evidence_status: \"PARTIAL_SEALED\"", f"formal_evidence_status: \"{'SEALED' if sealed else 'BLOCKED'}\"")
        text = text.replace("next_required_artifact: \"acceptance manifest with hashes and unique test accounting\"", "next_required_artifact: \"GA gates remain; RC2 formal evidence manifest is generated\"")
        ALIGNMENT.write_text(text, encoding="utf-8")


def write_sha256sums(paths: list[Path]) -> None:
    lines = []
    for path in paths:
        if path.exists():
            lines.append(f"{sha256_file(path)}  {path.relative_to(PROJECT)}")
    SHA256SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    write_json(MANIFEST, manifest)
    seal_paths = [EVIDENCE, CAS_EVIDENCE, MANIFEST] + list(GA_EVIDENCE.values()) + [GA_OBSERVABILITY]
    write_sha256sums(seal_paths)
    # Recompute manifest after sha file exists is unnecessary for seal status; update docs with manifest hash.
    update_final_round(manifest)
    print(json.dumps({
        "formal_evidence_seal": manifest["formal_evidence_seal"],
        "ga_ready": False,
        "manifest": str(MANIFEST.relative_to(PROJECT)),
        "sha256sums": str(SHA256SUMS.relative_to(PROJECT)),
        "blockers": manifest["seal_blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["formal_evidence_seal"] == "SEALED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
