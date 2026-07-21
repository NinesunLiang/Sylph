#!/usr/bin/env python3
"""
ROI Data Collector — extracts benefit/cost metrics for every Carror OS component
from flywheel.log, error-dna.jsonl, git history, and static code analysis.

Output: .omc/state/roi-data.json
Usage: python3 .claude/scripts/roi-collector.py [--verbose]
"""

import os, sys, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

VERBOSE = "--verbose" in sys.argv

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_DIR / ".omc" / "state"
FLYWHEEL_LOG = Path.home() / ".claude" / "flywheel.log"
ERROR_DNA = STATE_DIR / "error-dna.jsonl"
SKILL_USAGE = STATE_DIR / "skill-usage.jsonl"
CLAUDE_NEXT = PROJECT_DIR / ".claude" / "claude-next.md"
OUTPUT_FILE = STATE_DIR / "roi-data.json"

# ── Component inventories ──

HOOKS = [
    "context_guard", "ecosystem_probe", "edit_guard", "error_dna", "fuzzy_block",
    "intent_tracker", "knowledge_condenser", "lsp_suggest",
    "meta_oracle_trigger", "permission_gate", "plan_gate", "posttool_bash_audit",
    "posttool_claim_audit", "posttool_completion_audit", "posttool_edit_quality",
    "posttool_handoff_writer", "posttool_output_format", "posttool_read_cite",
    "posttool_subagent_audit", "posttool_write_cite", "posttool_write_lock",
    "pre_completion_gate", "completion_gate", "pretool_edit_scope", "pretool_sensitive_edit",
    "pretool_write_lock", "privacy_gate",
    "read_tracker", "retry_budget_check", "skill_flywheel", "stop_drain", "subagent_guard",
    "token_writer", "turn_counter", "user_correction_detector",
]

SKILLS = [
    "lx-code-review", "lx-dogfood", "lx-ghost", "lx-goal", "lx-learner",
    "lx-oma-gov", "lx-oma-hier", "lx-oma-orch", "lx-oma-split", "lx-pre-commit",
    "lx-pre-push", "lx-race", "lx-root-cause-analysis", "lx-rpe", "lx-skillify",
    "lx-status", "lx-stepwise", "lx-sync", "lx-task-spec", "lx-test-gen",
    "lx-todo", "lx-validate-skill", "lx-varlock", "update-carror-os",
]

SCRIPTS = [
    "hook-production-verify.sh", "lx-oma-gov-human-check.sh", "lx-oma-gov-propagate.sh",
    "lx-oma-gov-resolve.sh", "lx-orch-advance.sh", "lx-orch-gate.sh", "lx-orch-status.sh",
    "pipeline-step.sh", "race_manager.sh", "retry-budget.sh", "session-health-check.sh",
    "snapshot-helper.sh", "test_race.sh", "validate-skill.sh", "ghost-mode.sh",
    "lx-unattended-toggle.sh", "ed-red-team-test.sh", "doc-sync-check.sh",
    "escape-patch-apply.sh", "audit-hooks.sh", "meta-oracle-review.sh",
    "score-self-check.sh", "auto-scope.sh", "pre-commit-self-review.sh",
    "auto-score.sh", "lx-goal.sh", "harness-smoke-test.sh", "lx-ghost.sh",
    "task-workspace.sh",
]

# ── Frequency categories ──

HIGH_FREQ = {
    "completion_gate", "context_guard", "edit_guard",
    "error_dna", "turn_counter", "read_tracker", "token_writer",
    "pretool_edit_scope", "pretool_write_lock", "posttool_write_lock",
    "pre_completion_gate", "intent_tracker",
    "posttool_completion_audit", "ecosystem_probe",
}

MED_FREQ = {
    "posttool_bash_audit", "posttool_claim_audit", "posttool_edit_quality",
    "posttool_handoff_writer", "posttool_output_format", "posttool_read_cite",
    "posttool_write_cite", "posttool_subagent_audit", "knowledge_condenser",
    "lsp_suggest", "stop_drain", "subagent_guard", "auto_snapshot",
    "skill_flywheel",
}

LOW_FREQ = {
    "permission_gate", "plan_gate", "privacy_gate", "pretool_sensitive_edit",
    "fuzzy_block", "meta_oracle_trigger",
}

def freq_category(name):
    if name in HIGH_FREQ: return "high"
    if name in MED_FREQ: return "medium"
    if name in LOW_FREQ: return "low"
    return "medium"

def estimated_calls(name):
    return {"high": 30, "medium": 15, "low": 3}.get(freq_category(name), 10)

# ── Time-saved matrix ──

TIME_MATRIX = {
    "permission_gate": 15,
    "context_guard": 10,
    "completion_gate": 15,
    "privacy_gate": 10,
    "posttool_bash_audit": 5,
    "posttool_claim_audit": 5,
    "pretool_edit_scope": 3,
    "subagent_guard": 3,
    "stop_drain": 10,
    "skill_flywheel": 8,
}

# ── Quality boost estimates ──

QUALITY_BOOST = {
    "completion_gate": 0.9, "posttool_claim_audit": 0.9,
    "permission_gate": 0.8, "context_guard": 0.8, "privacy_gate": 0.8,
    "posttool_bash_audit": 0.8,
    "posttool_completion_audit": 0.7, "posttool_edit_quality": 0.7,
    "retry_budget_check": 0.7, "subagent_guard": 0.7,
    "error_dna": 0.6, "stop_drain": 0.6, "skill_flywheel": 0.6,
    "user_correction_detector": 0.6,
    "ecosystem_probe": 0.5,
    "knowledge_condenser": 0.5,
    "turn_counter": 0.3, "read_tracker": 0.3, "token_writer": 0.3,
    "auto_snapshot": 0.3, "lsp_suggest": 0.3,
}

# ── False positive rate estimates ──

FPR = {
    "permission_gate": 0.15,
    "pretool_edit_scope": 0.10, "subagent_guard": 0.10,
    "context_guard": 0.05, "privacy_gate": 0.05, "edit_guard": 0.05,
    "pretool_sensitive_edit": 0.05,
}

# ── Mental burden estimates (1-10) ──

MENTAL_BURDEN = {
    "permission_gate": 7, "context_guard": 7, "completion_gate": 7,
    "pretool_sensitive_edit": 7,
    "privacy_gate": 5, "pretool_edit_scope": 5, "subagent_guard": 5,
    "edit_guard": 5, "plan_gate": 5,
    "retry_budget_check": 5,
    "ecosystem_probe": 1,
    "turn_counter": 1, "read_tracker": 1, "token_writer": 1,
    "auto_snapshot": 1, "lsp_suggest": 1,
    "posttool_read_cite": 1, "posttool_write_cite": 1,
}

# ── Token consumption per call ──

def token_per_call(name):
    return {"high": 150, "medium": 300, "low": 100}.get(freq_category(name), 200)

# ── Parse flywheel.log ──

def parse_flywheel():
    intercepts = {h: 0 for h in HOOKS}
    skill_usage = {s: 0 for s in SKILLS}

    if not FLYWHEEL_LOG.exists():
        if VERBOSE: print(f"[roi-collector] ⚠️  {FLYWHEEL_LOG} not found")
        return intercepts, skill_usage

    csv_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}),(\w+),\w+,')
    skill_pattern = re.compile(r'"skill":"([^"]+)"')

    # Pre-build hook prefix lookup for flexible event matching
    # Events like "permission_gate_blocked_destructive_operation" → hook "permission_gate"
    hook_lookup = {}
    for h in HOOKS:
        hook_lookup[h] = h
    # Map known event prefixes to their hooks
    EVENT_HOOK_MAP = {
        "permission_gate": "permission_gate",
        "context_guard": "context_guard",
        "privacy_gate": "privacy_gate",
        "completion_gate": "completion_gate",
        "pre_completion_gate": "completion_gate",
        "stop_drain": "stop_drain",
        "pretool_edit_scope": "pretool_edit_scope",
        "pretool_sensitive_edit": "pretool_sensitive_edit",
        "subagent_guard": "subagent_guard",
        "edit_guard": "edit_guard",
        "posttool_bash_audit": "posttool_bash_audit",
        "posttool_claim_audit": "posttool_claim_audit",
        "posttool_subagent_audit": "posttool_subagent_audit",
        "error_dna": "error_dna",
        "ghost_exit_report": "stop_drain",  # ghost exit reports → stop_drain hook
    }

    with open(FLYWHEEL_LOG) as f:
        for line in f:
            line = line.strip()
            # Skip comment lines
            if line.startswith("#"):
                continue
            # CSV format: date,event,severity,...
            m = csv_pattern.match(line)
            if m:
                event = m.group(2)
                # Skip test entries (non-P0 events that don't come from real usage)
                # Match by prefix: check if event starts with known hook name
                matched = False
                for prefix, hook_name in EVENT_HOOK_MAP.items():
                    if event.startswith(prefix):
                        intercepts[hook_name] += 1
                        matched = True
                        break
                # Fallback: try removing _triggered/_blocked suffix
                if not matched:
                    hook_name = event.replace("_blocked_destructive_operation", "")
                    hook_name = hook_name.replace("_blocked_git_commit", "")
                    hook_name = hook_name.replace("_blocked_git_push", "")
                    hook_name = hook_name.replace("_blocked_scope_gate_bypass", "")
                    hook_name = hook_name.replace("_token_triggered", "")
                    hook_name = hook_name.replace("_triggered", "")
                    hook_name = hook_name.replace("_blocked", "")
                    if hook_name in intercepts:
                        intercepts[hook_name] += 1
                continue

            # JSON format for skill usage
            m = skill_pattern.search(line)
            if m:
                skill = m.group(1)
                if skill in skill_usage:
                    skill_usage[skill] += 1

    return intercepts, skill_usage


def parse_error_dna():
    """Count hook references in error-dna.jsonl using structured JSON field matching.
    Matches hook names in: message, error_type, escape_type, origin fields.
    This is more accurate than raw substring counting which inflates counts
    for hooks whose names appear in stack traces or system paths.
    """
    counts = {h: 0 for h in HOOKS}
    dna_files = [ERROR_DNA] + sorted(
        [p for p in STATE_DIR.glob("error-dna.jsonl.*") if p.suffix.lstrip(".").isdigit()],
        key=lambda p: int(p.suffix.lstrip("."))
    )
    for dna_file in dna_files:
        if not dna_file.exists():
            continue
        try:
            with open(dna_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # Search specific structured fields only (not raw substring)
                    search_text = " ".join(str(record.get(f, "")) for f in
                        ["error_type", "origin", "message", "escape_type"])
                    for h in HOOKS:
                        if h in search_text:
                            counts[h] += 1
        except Exception:
            continue
    return counts


def count_claude_next_refs(name):
    if not CLAUDE_NEXT.exists():
        return 0
    with open(CLAUDE_NEXT) as f:
        return f.read().count(name)


def file_line_count(path):
    try:
        with open(path) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def git_changes_3m(rel_path):
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_DIR), "log", "--since=2026-02-17", "--oneline", rel_path],
            capture_output=True, text=True
        )
        return len([l for l in result.stdout.strip().split("\n") if l])
    except Exception:
        return 0


def main():
    if VERBOSE:
        print("[roi-collector] Starting ROI data collection...")

    # 1. Parse flywheel.log
    intercepts, skill_usage = parse_flywheel()
    if VERBOSE:
        total_i = sum(intercepts.values())
        total_s = sum(skill_usage.values())
        print(f"[roi-collector] flywheel.log: {total_i} hook intercepts, {total_s} skill usages")

    # 2. Parse error-dna.jsonl
    edna_counts = parse_error_dna()
    if VERBOSE:
        total_e = sum(edna_counts.values())
        print(f"[roi-collector] error-dna.jsonl: {total_e} hook references")

    # 3. Count maintenance metrics
    flywheel_lines = file_line_count(FLYWHEEL_LOG)
    edna_lines = file_line_count(ERROR_DNA)

    # ── Build component data ──

    # Hooks
    hooks_data = {}

    def find_hook_file(hook_name):
        """Find the actual hook .sh file for a given snake_case hook name.
        Tries: kebab-case, snake_case, posttool- prefix, pretool- prefix.
        Returns (file_path, git_log_path) or (None, None) if not found.
        """
        hooks_dir = PROJECT_DIR / ".claude" / "hooks"
        kebab = hook_name.replace("_", "-")
        candidates = [
            kebab + ".sh",                      # standard: privacy-gate.sh
            hook_name + ".sh",                  # legacy: token_writer.sh
            "posttool-" + kebab + ".sh",         # posttool-anti-pattern-detect.sh
            "pretool-" + kebab + ".sh",          # pretool-retry-check.sh
        ]
        for filename in candidates:
            path = hooks_dir / filename
            if path.exists():
                return path, f".claude/hooks/{filename}"
        # Return the kebab-case default (may not exist)
        return hooks_dir / (kebab + ".sh"), f".claude/hooks/{kebab}.sh"

    for h in HOOKS:
        hook_file, git_path = find_hook_file(h)
        lines = file_line_count(hook_file)
        changes = git_changes_3m(git_path)
        knowledge = count_claude_next_refs(h)
        ic = intercepts.get(h, 0)
        tpm = TIME_MATRIX.get(h, 5)
        time_saved = ic * tpm

        hooks_data[h] = {
            "intercept_count": ic,
            "call_frequency_est": estimated_calls(h),
            "time_saved_minutes": time_saved,
            "quality_boost": QUALITY_BOOST.get(h, 0.4),
            "knowledge_deposit_refs": knowledge,
            "token_consumption_per_call": token_per_call(h),
            "maintenance_lines": lines,
            "maintenance_changes_3m": changes,
            "false_positive_rate": FPR.get(h, 0.03),
            "mental_burden": MENTAL_BURDEN.get(h, 3),
            "error_dna_refs": edna_counts.get(h, 0),
        }

    # Skills
    skills_data = {}
    for s in SKILLS:
        skill_file = PROJECT_DIR / ".claude" / "skills" / s / "SKILL.md"
        lines = file_line_count(skill_file)
        changes = git_changes_3m(f".claude/skills/{s}/")
        knowledge = count_claude_next_refs(s)
        usage = skill_usage.get(s, 0)

        # Special handling for key skills
        if s in ("lx-goal", "lx-ghost", "lx-status", "lx-oma-orch"):
            qb = 0.8
        elif s in ("lx-oma-split", "lx-oma-hier", "lx-code-review", "lx-sync"):
            qb = 0.7
        elif s.startswith("lx-pre-") or s in ("lx-varlock", "lx-stepwise"):
            qb = 0.6
        elif s in ("lx-dogfood", "lx-skillify", "lx-learner", "update-carror-os"):
            qb = 0.5
        else:
            qb = 0.4

        skills_data[s] = {
            "usage_count": usage,
            "call_frequency_est": 5,
            "time_saved_minutes": usage * 10,
            "quality_boost": qb,
            "knowledge_deposit_refs": knowledge,
            "token_consumption_per_call": 500,
            "maintenance_lines": lines,
            "maintenance_changes_3m": changes,
            "false_positive_rate": 0.02,
            "mental_burden": 2,
            "error_dna_refs": 0,
        }

    # Scripts
    scripts_data = {}
    for sc in SCRIPTS:
        script_file = PROJECT_DIR / ".claude" / "scripts" / sc
        lines = file_line_count(script_file)
        changes = git_changes_3m(f".claude/scripts/{sc}")
        knowledge = count_claude_next_refs(sc.replace(".sh", ""))

        if sc in ("harness-smoke-test.sh", "audit-hooks.sh", "auto-score.sh"):
            fe = 15; qb = 0.8
        elif sc in ("lx-goal.sh", "lx-ghost.sh", "task-workspace.sh"):
            fe = 10; qb = 0.7
        elif sc in ("meta-oracle-review.sh", "pre-commit-self-review.sh"):
            fe = 5; qb = 0.7
        elif sc in ("roi-collector.py",):
            fe = 5; qb = 0.6
        else:
            fe = 3; qb = 0.4

        scripts_data[sc] = {
            "usage_count": 0,
            "call_frequency_est": fe,
            "time_saved_minutes": fe * 5,
            "quality_boost": qb,
            "knowledge_deposit_refs": knowledge,
            "token_consumption_per_call": 200,
            "maintenance_lines": lines,
            "maintenance_changes_3m": changes,
            "false_positive_rate": 0.01,
            "mental_burden": 1,
            "error_dna_refs": 0,
        }

    # ── Assemble output ──

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_sources": {
            "flywheel_log": str(FLYWHEEL_LOG),
            "error_dna": str(ERROR_DNA),
            "flywheel_lines": flywheel_lines,
            "error_dna_lines": edna_lines,
        },
        "components": {
            "hooks": hooks_data,
            "skills": skills_data,
            "scripts": scripts_data,
        },
    }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    line_count = len(json.dumps(output, indent=2, ensure_ascii=False).split("\n"))
    print(f"[roi-collector] Complete: {line_count} lines JSON -> {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
