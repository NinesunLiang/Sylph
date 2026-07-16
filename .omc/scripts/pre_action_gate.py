#!/usr/bin/env python3
"""
CarrorOS PreActionGate

Purpose:
  Decide whether a concrete action may execute before it runs.

Constraints:
  - Python 3.10+ standard library only
  - No task execution
  - No secret content reading
  - Audit-first decision model
  - Aligns with .omc/tasks/ and rpe/ doc structure
  - Compatible with CarrorOS token format (session.level, steps[])

Usage:
  python3 pre_action_gate.py action_spec.json [policy.json]

Exit codes:
  0 = ALLOW
  1 = non-ALLOW (ASK_USER / BLOCK / ESCALATE / audit_failure)
  2 = usage error
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_POLICY = {
    "sensitive_paths": [
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "id_rsa",
        "id_ed25519",
        "*secret*",
        "*token*",
        "*credential*",
        "*password*",
        "production.*",
        "prod.*",
        "kubeconfig",
        "~/.ssh/*",
        ".ssh/*",
        ".aws/credentials",
        ".gcp/*",
        ".azure/*",
    ],
    "dangerous_commands": [
        "rm -rf",
        "sudo",
        "chmod -R",
        "chown -R",
        "git reset --hard",
        "git clean -fd",
        "git push --force",
        "docker compose down -v",
        "kubectl delete",
        "terraform apply",
        "terraform destroy",
        "migration:run",
        "db:migrate",
        "DROP TABLE",
        "TRUNCATE TABLE",
        "ALTER TABLE",
        "npm publish",
        "pnpm publish",
        "pip upload",
        "twine upload",
    ],
    "safe_commands": [
        "npm test",
        "pnpm test",
        "yarn test",
        "pytest",
        "python -m pytest",
        "npm run lint",
        "pnpm lint",
        "git status",
        "git diff",
        "git log",
    ],
}


@dataclass
class ActionSpec:
    action_type: str
    command: str | None
    paths: list[str]
    current_step: str
    intent: str
    risk_hint: str | None = None
    requires_network: bool = False
    requires_production: bool = False
    requires_database: bool = False
    metadata: dict[str, Any] | None = None


@dataclass
class GateDecision:
    decision: str
    reason: str
    risk: str
    required_confirmations: list[str]
    sanitized_paths: list[str]
    evidence_summary: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def path_hash(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


def matches_pattern(path: str, patterns: list[str]) -> bool:
    normalized = normalize_path(path)
    name = Path(normalized).name
    return any(
        fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in patterns
    )


def is_sensitive_path(path: str, policy: dict[str, Any]) -> bool:
    return matches_pattern(path, policy["sensitive_paths"])


def sanitize_paths(paths: list[str], policy: dict[str, Any]) -> list[str]:
    result = []
    for item in paths:
        normalized = normalize_path(item)
        if is_sensitive_path(normalized, policy):
            result.append(path_hash(normalized))
        else:
            result.append(normalized)
    return result


def command_contains(command: str, patterns: list[str]) -> bool:
    lowered = command.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def is_safe_command(command: str, policy: dict[str, Any]) -> bool:
    lowered = command.lower().strip()
    return any(lowered.startswith(item.lower()) for item in policy["safe_commands"])


def is_scope_match(paths: list[str], scope: list[str]) -> bool:
    if not paths:
        return False
    normalized_scope = [normalize_path(item) for item in scope]
    for path in paths:
        normalized = normalize_path(path)
        if normalized not in normalized_scope:
            return False
    return True


def load_current_scope(token: dict[str, Any]) -> list[str]:
    """从 token 获取 scope——支持 task.scope 和 task_dir/plan.md 两种方式"""
    scope = token.get("scope") or token.get("task", {}).get("scope", []) or []
    return scope if isinstance(scope, list) else []


def load_current_step(token: dict[str, Any]) -> str | None:
    """从 token 获取 current_step——兼容新旧 token 格式"""
    # 新格式: task.current_step
    step = token.get("task", {}).get("current_step")
    if step:
        return step
    # 旧格式: steps 数组中找第一个 pending 的
    steps = token.get("steps", [])
    if steps:
        for s in steps:
            if s.get("status") == "pending":
                return s.get("id")
        # 全部完成就取最后一个
        return steps[-1].get("id")
    return None


def resolve_doc_root(token: dict[str, Any]) -> Path:
    """根据 token 解析文档根路径——兼容新旧格式"""
    level = token.get("session", {}).get("level", "L1")
    # L1_BASE -> L1
    level_short = level.replace("_BASE", "").replace("_ENHANCE", "")
    if level_short == "L2":
        feature = token.get("task", {}).get("feature", "unknown")
        return Path(f"rpe/{feature}")

    # L1: 从 task_dir 或 session.id 推断
    task_dir = token.get("task_dir", "")
    if task_dir:
        # 从绝对路径提取 .omc/tasks/{date}/{id} 相对路径
        parts = Path(task_dir).parts
        try:
            idx = parts.index("tasks")
            return Path(*parts[idx - 1:])  # .omc/tasks/{date}/{id}
        except (ValueError, IndexError):
            pass

    date_str = token.get("task", {}).get("date", datetime.now(timezone.utc).strftime("%Y%m%d"))
    task_name = token.get("session", {}).get("id", "task")
    return Path(f".omc/tasks/{date_str}/{task_name}")


def update_blocked(token_path: Path, reason: str) -> None:
    token = read_json(token_path, {})
    token.setdefault("task", {})
    # 也兼容旧格式
    if "steps" in token:
        _steps = token.get("steps", [])
        for s in _steps:
            if s.get("status") == "pending":
                s["status"] = "blocked"
                break
        token["steps"] = _steps
    token["task"]["status"] = "blocked"
    token["task"]["blocked"] = reason
    write_json(token_path, token)


def classify_action(
    spec: ActionSpec, token: dict[str, Any], policy: dict[str, Any]
) -> GateDecision:
    token_step = load_current_step(token)
    scope = load_current_scope(token)

    if token_step is None:
        return GateDecision(
            decision="BLOCK",
            reason="missing_current_step",
            risk="high",
            required_confirmations=[],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="token.task.current_step is missing",
        )

    if spec.current_step != token_step:
        return GateDecision(
            decision="BLOCK",
            reason="state_conflict_current_step",
            risk="high",
            required_confirmations=[],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary=f"action step {spec.current_step} != token step {token_step}",
        )

    sensitive = any(is_sensitive_path(path, policy) for path in spec.paths)
    scope_match = is_scope_match(spec.paths, scope) if spec.paths else False
    command = spec.command or ""
    dangerous_command = bool(command) and command_contains(
        command, policy["dangerous_commands"]
    )

    if sensitive:
        if spec.action_type == "read_file":
            return GateDecision(
                decision="BLOCK",
                reason="secret_path_access_forbidden",
                risk="critical",
                required_confirmations=[],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="sensitive path matched; content_logged=false",
            )
        if spec.action_type == "delete_file":
            return GateDecision(
                decision="BLOCK",
                reason="sensitive_delete_requires_exact_approval",
                risk="critical",
                required_confirmations=["exact_path", "exact_reason", "user_approval"],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="sensitive delete blocked without exact approval",
            )
        return GateDecision(
            decision="ESCALATE",
            reason="sensitive_path_write_or_operation",
            risk="high",
            required_confirmations=["l2_review"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="sensitive path requires L2 review",
        )

    if spec.requires_production:
        if spec.action_type in (
            "write_file",
            "delete_file",
            "run_command",
            "production_operation",
        ):
            return GateDecision(
                decision="ESCALATE",
                reason="production_operation_requires_l2",
                risk="high",
                required_confirmations=["production_confirmation", "l2_review"],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="production operation cannot run in L1 without escalation",
            )

    if spec.requires_database:
        return GateDecision(
            decision="ESCALATE",
            reason="database_operation_requires_l2",
            risk="high",
            required_confirmations=["migration_plan", "l2_review"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="database operation requires migration governance",
        )

    if dangerous_command:
        hard_block_patterns = [
            "rm -rf /",
            "git reset --hard",
            "git clean -fd",
            "DROP TABLE",
            "TRUNCATE TABLE",
        ]
        if command_contains(command, hard_block_patterns):
            return GateDecision(
                decision="BLOCK",
                reason="destructive_command_forbidden",
                risk="critical",
                required_confirmations=[],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="destructive command matched hard block pattern",
            )
        return GateDecision(
            decision="ASK_USER",
            reason="dangerous_command_requires_approval",
            risk="high",
            required_confirmations=["explicit_command_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="dangerous command matched policy",
        )

    if spec.action_type == "install_dependency":
        return GateDecision(
            decision=(
                "ESCALATE"
                if spec.risk_hint == "runtime_dependency"
                else "ASK_USER"
            ),
            reason="dependency_change_requires_approval",
            risk="medium",
            required_confirmations=["dependency_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="dependency changes affect supply chain",
        )
    if spec.action_type == "network_call" or spec.requires_network:
        return GateDecision(
            decision="ASK_USER",
            reason="network_access_requires_approval",
            risk="medium",
            required_confirmations=["network_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="network call requested",
        )

    if spec.action_type == "git_operation":
        cmd = spec.command or ""
        cmd_lower = cmd.lower()
        # Safe git operations
        if any(op in cmd_lower for op in ["status", "diff", "log", "branch"]):
            return GateDecision(
                decision="ALLOW",
                reason="safe_git_operation",
                risk="low",
                required_confirmations=[],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="safe git read operation",
            )
        # Destructive git operations
        if any(op in cmd_lower for op in ["reset --hard", "clean -fd", "push --force", "push -f"]):
            return GateDecision(
                decision="BLOCK",
                reason="destructive_git_operation",
                risk="critical",
                required_confirmations=["explicit_git_approval"],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="destructive git operation blocked",
            )
        # Other git writes
        if any(op in cmd_lower for op in ["add", "commit", "push", "checkout", "merge", "rebase"]):
            return GateDecision(
                decision="ASK_USER",
                reason="git_write_operation",
                risk="medium",
                required_confirmations=["git_operation_approval"],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="git write operation requires approval",
            )
        return GateDecision(
            decision="ASK_USER",
            reason="unknown_git_operation",
            risk="medium",
            required_confirmations=["git_operation_review"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="unknown git operation requires review",
        )

    if spec.action_type == "delete_file":
        return GateDecision(
            decision="ASK_USER",
            reason="delete_requires_approval",
            risk="medium",
            required_confirmations=["delete_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="delete operation is irreversible",
        )

    if spec.action_type == "run_command":
        if is_safe_command(command, policy):
            return GateDecision(
                decision="ALLOW",
                reason="safe_command_matched",
                risk="low",
                required_confirmations=[],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="command matched safe command prefix",
            )
        return GateDecision(
            decision="ASK_USER",
            reason="unknown_command_requires_approval",
            risk="medium",
            required_confirmations=["command_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="command is not in safe command allowlist",
        )

    if spec.action_type in ("write_file", "read_file"):
        if scope_match:
            return GateDecision(
                decision="ALLOW",
                reason="scope_match_and_no_policy_hit",
                risk="low",
                required_confirmations=[],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="path in scope; no sensitive path; no dangerous command",
            )
        if spec.action_type == "read_file":
            return GateDecision(
                decision="ASK_USER",
                reason="scope_out_read_requires_approval",
                risk="low",
                required_confirmations=["scope_read_approval"],
                sanitized_paths=sanitize_paths(spec.paths, policy),
                evidence_summary="read path outside frozen scope",
            )
        return GateDecision(
            decision="ASK_USER",
            reason="scope_out_write_requires_approval",
            risk="medium",
            required_confirmations=["scope_change_approval"],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary="write path outside frozen scope",
        )

    return GateDecision(
        decision="ASK_USER",
        reason="unknown_action_type",
        risk="medium",
        required_confirmations=["action_type_review"],
        sanitized_paths=sanitize_paths(spec.paths, policy),
        evidence_summary="action type not explicitly allowed",
    )


def write_audit(
    decision: GateDecision,
    spec: ActionSpec,
    token: dict[str, Any],
    audit_dir: Path,
) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    event = {
        "event_type": "pre_action_decision",
        "timestamp": now_iso(),
        "task_id": token.get("session", {}).get("id", "unknown_task"),
        "level": token.get("session", {}).get("level", "unknown_level"),
        "phase": "execute",
        "current_step": spec.current_step,
        "actor": "model",
        "action": (
            spec.action_type if not spec.command else f"{spec.action_type}:{spec.command}"
        ),
        "paths": decision.sanitized_paths,
        "decision": decision.decision,
        "reason": decision.reason,
        "evidence": {
            "type": "policy_check",
            "summary": decision.evidence_summary,
        },
        "risk": decision.risk,
        "content_logged": (
            False
            if any(path.startswith("sha256:") for path in decision.sanitized_paths)
            else None
        ),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def write_executor_note(
    spec: ActionSpec, decision: GateDecision, executor_path: Path
) -> None:
    if decision.decision == "ALLOW":
        return

    command_line = f"- command: {spec.command}\n" if spec.command else ""
    text = (
        "\n## PreActionGate\n\n"
        f"- step: {spec.current_step}\n"
        f"- action: {spec.action_type}\n"
        f"{command_line}"
        f"- decision: {decision.decision}\n"
        f"- reason: {decision.reason}\n"
        f"- next: {'waiting_user_approval' if decision.decision == 'ASK_USER' else decision.decision.lower()}\n"
    )
    append_text(executor_path, text)


def load_action_spec(path: Path) -> ActionSpec:
    data = read_json(path)
    return ActionSpec(
        action_type=data["action_type"],
        command=data.get("command"),
        paths=data.get("paths", []),
        current_step=data["current_step"],
        intent=data.get("intent", ""),
        risk_hint=data.get("risk_hint"),
        requires_network=bool(data.get("requires_network", False)),
        requires_production=bool(data.get("requires_production", False)),
        requires_database=bool(data.get("requires_database", False)),
        metadata=data.get("metadata") or {},
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: pre_action_gate.py action_spec.json [policy.json] [--token token_path]",
            file=sys.stderr,
        )
        return 2

    # Parse --token arg
    token_path_str = ".omc/state/token.json"
    filtered = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--token" and i + 1 < len(sys.argv):
            token_path_str = sys.argv[i + 1]
            i += 2
        else:
            filtered.append(sys.argv[i])
            i += 1

    action_path = Path(filtered[0])
    policy_path = (
        Path(filtered[1])
        if len(filtered) >= 2
        else Path(".omc/config/policy.json")
    )

    spec = load_action_spec(action_path)
    policy = read_json(policy_path, DEFAULT_POLICY)
    token_path = Path(token_path_str)
    token = read_json(token_path, {})

    decision = classify_action(spec, token, policy)

    try:
        write_audit(decision, spec, token, Path(".omc/audit"))
    except OSError as exc:
        decision = GateDecision(
            decision="BLOCK",
            reason="audit_write_failed",
            risk="high",
            required_confirmations=[],
            sanitized_paths=sanitize_paths(spec.paths, policy),
            evidence_summary=f"audit write failed: {exc.__class__.__name__}",
        )
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
        return 1

    doc_root = resolve_doc_root(token)
    executor_path = doc_root / "executor.md"
    write_executor_note(spec, decision, executor_path)

    if decision.decision == "BLOCK":
        update_blocked(token_path, decision.reason)

    print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
    return 0 if decision.decision == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
