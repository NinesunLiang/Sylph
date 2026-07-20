#!/usr/bin/env python3
"""
CarrorOS VerifyGate

Purpose:
  Match executor.md evidence against plan.md verify rules to decide step completion.
  Only VerifyGate VERIFIED allows plan.md [x].

Commands:
  verify --step <step_id> --plan <path> --executor <path> [--token <path>]

Output:
  VERIFIED / WARN / BLOCKED / REJECTED

Constraints:
  - Python 3.10+ standard library only
  - Does not execute fixes
  - Does not alter executor evidence
  - Evidence-level enforcement:
    E3 command exit=0 > E2 file_assertion > E1 user_confirmation > E0 narrative (rejected)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOFT_COMPLETION_PHRASES = [
    "应该好了", "看起来可以", "基本完成", "大概没问题",
    "已经处理", "完成了",
    "looks good", "should work", "probably fixed",
    "可以了", "没问题",
]


@dataclass
class VerifyDecision:
    decision: str  # VERIFIED | WARN | BLOCKED | REJECTED
    reason: str
    step: str
    matched: list[str]
    missing: list[str]
    warnings: list[str]
    required_action: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    # H10: 与 carros_base/carros_utils 审计文件名格式统一(%Y%m%d)
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def parse_verify_rules(plan_text: str, step: str) -> list[str]:
    """Extract verify rules for a given step from plan.md."""
    rules: list[str] = []
    in_step = False
    step_prefixes = [f"- [ ] {step}:", f"- [x] {step}:", f"- [X] {step}:"]

    for line in plan_text.splitlines():
        stripped = line.strip()
        # Check if we're entering the target step
        if any(stripped.startswith(p) for p in step_prefixes):
            in_step = True
            continue
        # Exit step on next step heading or step marker
        if in_step and (stripped.startswith("- [") or stripped.startswith("## ")):
            if stripped.startswith("- [") and not any(stripped.startswith(p) for p in step_prefixes):
                break
        if in_step:
            m = re.match(r"- verify:\s*(.+)$", stripped)
            if m:
                rules.append(m.group(1).strip())
    if not rules:
        # Fallback: search globally
        for line in plan_text.splitlines():
            m = re.match(r"- verify:\s*(.+)$", line.strip())
            if m:
                rules.append(m.group(1).strip())
    return rules


def parse_evidence(executor_text: str, step: str) -> list[dict[str, Any]]:
    """Extract evidence entries for a given step from executor.md."""
    evidence: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    in_entry = False

    for line in executor_text.splitlines():
        stripped = line.strip()
        m = re.match(r"^###\s+(EV-\S+)", stripped)
        if m:
            if current and current.get("step") == step:
                evidence.append(current)
            current = {"id": m.group(1)}
            in_entry = True
            continue
        m = re.match(r"^###\s+(FAIL-\S+)", stripped)
        if m:
            if current and current.get("step") == step:
                evidence.append(current)
            current = {"id": m.group(1), "type": "failure"}
            in_entry = True
            continue
        if in_entry:
            for key in ("step", "type", "source", "exit_code", "file", "assertion",
                        "evidence_level", "confirmation", "change_summary"):
                kv = re.match(rf"- {key}:\s*(.+)$", stripped)
                if kv:
                    val = kv.group(1).strip()
                    if key == "exit_code":
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    current[key] = val
            if stripped.startswith("## "):
                if current and current.get("step") == step:
                    evidence.append(current)
                current = {}
                in_entry = False

    if current and current.get("step") == step:
        evidence.append(current)

    return evidence


def is_soft_completion(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase.lower() in lowered for phrase in SOFT_COMPLETION_PHRASES)


def match_verify_rule(rule: str, evidence: list[dict[str, Any]]) -> tuple[bool, str, list[str]]:
    """Match a single verify rule against available evidence."""
    warnings: list[str] = []

    # command: rule
    cm = re.match(r"^command:(.+)$", rule)
    if cm:
        expected_cmd = cm.group(1).strip()
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            src = str(ev.get("source", "")).strip()
            ec = ev.get("exit_code")
            el = str(ev.get("evidence_level", ""))
            if src and (src == expected_cmd or src.endswith("/" + expected_cmd) or expected_cmd.endswith(src)):
                if ec == 0 and el == "E3":
                    return True, f"command match: {src} exit=0", []
                elif ec == 0:
                    warnings.append(f"command {src} exit=0 but evidence_level={el} (expected E3)")
        return False, f"no matching command evidence for: {expected_cmd}", warnings

    # file: rule
    fm = re.match(r"^file:(.+?)\s+contains\s+(.+)$", rule)
    if fm:
        expected_file = fm.group(1).strip()
        expected_assertion = fm.group(2).strip()
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            ef = str(ev.get("file", "")).strip()
            ea = str(ev.get("assertion", "")).strip()
            el = str(ev.get("evidence_level", ""))
            if ef and (ef == expected_file or ef.endswith("/" + expected_file)):
                if is_soft_completion(ea):
                    warnings.append(f"file_assertion for {ef} contains soft completion: '{ea}'")
                    return False, "soft_completion_in_assertion", warnings
                if expected_assertion.lower() in ea.lower():
                    if el in ("E2", "E3"):
                        return True, f"file assertion match: {ef} contains '{expected_assertion}'", []
                    warnings.append(f"file assertion for {ef} has evidence_level={el} (expected E2/E3)")
                else:
                    warnings.append(f"file assertion for {ef} doesn't contain '{expected_assertion}'")
        return False, f"no matching file assertion for: {expected_file}", warnings

    # assertion: rule
    am = re.match(r"^assertion:(.+)$", rule)
    if am:
        expected = am.group(1).strip().lower()
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            if is_soft_completion(str(ev.get("assertion", ""))):
                warnings.append(f"assertion contains soft completion")
                continue
            if expected in str(ev.get("assertion", "")).lower():
                return True, f"assertion match: '{expected}'", []
            txt = str(ev.get("output_tail", "")).lower()
            if expected in txt and ev.get("exit_code") == 0:
                return True, f"assertion in command output: '{expected}'", []
        return False, f"no matching assertion for: {expected}", warnings

    return False, f"unrecognized verify rule: {rule}", warnings


def parse_spec_acs(spec_path: Path, step: str | None = None) -> list[str]:
    """Parse Acceptance Criteria from spec.md — returns list of AC rules

    spec.md 格式:
        - AC1 [command:] <desc>
        - AC2 [file:] <desc>
        - AC3 [assertion:] <desc>
    """
    spec_text = read_text(spec_path)
    if not spec_text:
        return []

    rules = []
    for line in spec_text.splitlines():
        stripped = line.strip()
        # Match: - AC1 [command:] description
        m = re.match(r"^\s*-\s*(AC\d+)\s*\[(command:|file:|assertion:)\]\s*(.+)", stripped)
        if m:
            prefix = m.group(2)  # e.g. "command:"
            desc = m.group(3).strip()
            rules.append(f"{prefix}{desc}")
            continue
        # Match: - AC1: description (no type prefix, default assertion:)
        m2 = re.match(r"^\s*-\s*(AC\d+):\s*(.+)", stripped)
        if m2:
            desc = m2.group(2).strip()
            rules.append(f"assertion:{desc}")

    return rules


def verify_step(step: str, plan_path: Path, executor_path: Path, token_path: Path | None = None,
                spec_path: Path | None = None) -> VerifyDecision:
    plan_text = read_text(plan_path)
    executor_text = read_text(executor_path)

    plan_text = read_text(plan_path)
    if not plan_text:
        return VerifyDecision("REJECTED", "plan_missing", step, [], [], [])

    executor_text = read_text(executor_path)
    if not executor_text:
        return VerifyDecision("BLOCKED", "executor_missing", step, [], [], [])

    # Parse verify rules for this step
    verify_rules = parse_verify_rules(plan_text, step)

    # Also merge AC rules from spec.md (if available)
    spec_acs = []
    if spec_path and spec_path.exists():
        spec_acs = parse_spec_acs(spec_path, step)
    all_rules = verify_rules + [r for r in spec_acs if r not in verify_rules]

    if not all_rules:
        return VerifyDecision("REJECTED", "no_verify_rules", step, [], [], [],
                              "Plan step must have verify rules or spec.md must have ACs.")
    verify_rules = all_rules

    # Check for invalid rule syntax
    valid_prefixes = ("command:", "file:", "assertion:", "user:")
    for rule in verify_rules:
        if not any(rule.startswith(p) for p in valid_prefixes):
            return VerifyDecision("REJECTED", f"invalid_verify_prefix: {rule}", step, [], [], [],
                                  "Verify rule must start with command:/file:/assertion:/user:")

    # Parse evidence
    evidence = parse_evidence(executor_text, step)
    if not evidence:
        return VerifyDecision("BLOCKED", "no_evidence_for_step", step, [], verify_rules, [])

    # Check for soft completion in evidence assertions
    for ev in evidence:
        assertion = str(ev.get("assertion", ""))
        confirmation = str(ev.get("confirmation", ""))
        if is_soft_completion(assertion) or is_soft_completion(confirmation):
            return VerifyDecision("REJECTED", "soft_completion_in_evidence", step, [], verify_rules, [])

    # Check for unresolved failures
    failures = [ev for ev in evidence if ev.get("type") == "failure"]
    # Remove failures that have subsequent covering success evidence
    for fail in failures:
        fail_action = str(fail.get("action", ""))
        # Check if there's a successful command evidence with same source
        covered = False
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            if ev.get("exit_code") == 0:
                src = str(ev.get("source", ""))
                if src and fail_action.endswith(src):
                    covered = True
                    break
        if not covered:
            return VerifyDecision("BLOCKED", f"unresolved_failure:{fail.get('id', 'unknown')}",
                                  step, [], verify_rules, [])

    # Match each verify rule
    matched_rules: list[str] = []
    missing_rules: list[str] = []
    all_warnings: list[str] = []

    for rule in verify_rules:
        ok, reason, warns = match_verify_rule(rule, evidence)
        all_warnings.extend(warns)
        if ok:
            matched_rules.append(reason)
        else:
            missing_rules.append(reason)

    # Check user confirmation rules separately (weaker match needed)
    user_rules = [r for r in missing_rules if r.startswith("no matching")]
    user_verify = [r for r in verify_rules if r.startswith("user:")]
    for vr in user_verify:
        expected = vr[5:].strip().lower()
        for ev in evidence:
            if ev.get("type") != "user_confirmation":
                continue
            conf = str(ev.get("confirmation", "")).lower()
            if is_soft_completion(conf):
                all_warnings.append(f"user confirmation contains soft completion: '{conf}'")
                continue
            if len(conf) >= 8 and expected in conf:
                matched_rules.append(f"user confirmation match: '{expected}'")
                user_rules_to_remove = [r for r in missing_rules if "user:" in r]
                for rr in user_rules_to_remove:
                    if rr in missing_rules:
                        missing_rules.remove(rr)

    # Decision
    if not missing_rules and not all_warnings:
        return VerifyDecision("VERIFIED", "all_verify_rules_matched", step, matched_rules, [], [])
    elif not missing_rules and all_warnings:
        return VerifyDecision("WARN", "all_verify_matched_with_warnings", step, matched_rules, [], all_warnings)
    elif missing_rules:
        return VerifyDecision("BLOCKED", "evidence_missing", step, matched_rules, missing_rules, all_warnings)

    return VerifyDecision("BLOCKED", "unknown", step, matched_rules, missing_rules, all_warnings)


def write_audit(decision: VerifyDecision, token: dict[str, Any] | None = None) -> None:
    event = {
        "event_type": "verify_decision",
        "timestamp": now_iso(),
        "step": decision.step,
        "decision": decision.decision,
        "reason": decision.reason,
        "matched": decision.matched,
        "missing": decision.missing,
        "warnings": decision.warnings,
        "required_action": decision.required_action,
        # Round7 PKG-4(E7 校准账): claim 语义字段——每条 verify_decision 是一条
        # "本步已验证"断言,claim_id 稳定可索引,evidence_ids 回溯支撑证据,
        # status 供 jq 统计 overturn(verified→后被推翻率)。
        "claim_id": f"verify:{decision.step}",
        "evidence_ids": [f"matched:{m}" for m in decision.matched],
        "status": "verified" if decision.decision == "VERIFIED" else "unverified",
    }
    if token:
        event["task_id"] = (token.get("session", {}) or {}).get("id") \
            or token.get("task", {}).get("id", "unknown")
        event["level"] = token.get("session", {}).get("level", "unknown")
    append_jsonl(Path(".omc/audit") / f"{today()}.jsonl", event)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--executor", required=True)
    parser.add_argument("--token", required=False)
    parser.add_argument("--spec", required=False,
                       help="spec.md 路径 — 可选，提供 AC 规则以增强验证")
    args = parser.parse_args()

    token = read_json(Path(args.token)) if args.token else None
    spec_path = Path(args.spec) if args.spec else None
    result = verify_step(args.step, Path(args.plan), Path(args.executor),
                         Path(args.token) if args.token else None, spec_path)

    write_audit(result, token)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.decision == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
