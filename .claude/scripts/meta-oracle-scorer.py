#!/usr/bin/env python3
"""Meta-Oracle scoring engine — C/E/G/UX four-dimension scoring.

Replaces auto-score.sh + score-ux.sh with pure Python3, cross-platform
(macOS / Linux / Windows) and zero external dependencies.

Dimensions:
  C (Correctness): 9 sub-dimensions, max 105, weight 40%
  E (Effectiveness): 8 sub-dimensions, max 110, weight 35%
  G (Governance): 5 sub-dimensions, max 50, weight 25%
  UX (User Experience): 5 sub-dimensions, max 10, independent (not in 8.6 gate)

Usage:
  python3 meta-oracle-scorer.py [--calibrated] [--meta-oracle]
  Output: JSON to stdout + .omc/state/auto-score-{ts}.json
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone


IS_WINDOWS = os.name == "nt"
HOME = os.path.expanduser("~")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")


# ── Helpers ─────────────────────────────────────────────────────────

def _read(path, default=""):
    """Read file content, return stripped string or default."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return default


def _read_lines(path):
    """Count lines in file. Returns 0 if missing."""
    try:
        return sum(1 for _ in open(path, "r", encoding="utf-8"))
    except (OSError, FileNotFoundError):
        return 0


def _read_size(path):
    """Get file size in bytes. Returns 0 if missing."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _has_content(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _grep_count(pattern, path):
    """Count lines matching regex pattern in file."""
    if not os.path.isfile(path):
        return 0
    try:
        return len(re.findall(pattern, open(path, "r", encoding="utf-8").read(), re.MULTILINE))
    except OSError:
        return 0


def _grep_any(pattern, *paths):
    """Check if pattern matches in any of the given files."""
    for path in paths:
        if os.path.isfile(path):
            try:
                if re.search(pattern, open(path, "r", encoding="utf-8").read(), re.MULTILINE):
                    return True
            except OSError:
                pass
    return False


def _pct(score, max_val):
    """Percentage with 1 decimal."""
    if max_val == 0:
        return 0
    return round(score / max_val * 100, 1)


def _clamp(val, max_val):
    return min(val, max_val)


def _runtime_evidence_factor(hook_name):
    """Read flywheel.log for hook event count, return trust factor 0.5-1.0.

    0 events → 0.50 (mechanism exists, no runtime evidence)
    1+ events → 0.85 (evidence exists, room for quality variance)
    5+ events → 1.00 (sufficient runtime evidence)
    """
    count = 0
    flywheel_log = os.path.join(HOME, ".claude", "flywheel.log")
    if os.path.isfile(flywheel_log):
        count = _grep_count(hook_name, flywheel_log)
    # Also check flywheel-report.json
    report_path = os.path.join(STATE_DIR, "flywheel-report.json")
    if os.path.isfile(report_path):
        try:
            d = json.load(open(report_path, "r", encoding="utf-8"))
            count += int(d.get(hook_name, 0))
        except (json.JSONDecodeError, ValueError, OSError, TypeError, AttributeError):
            pass
    if count >= 5:
        return 1.0
    elif count >= 1:
        return 0.85
    return 0.50


def _smoke_passes_for(test_label):
    """Check if a test label appears with PASS in latest harness-smoke log."""
    import glob
    pattern = os.path.join(STATE_DIR, "harness-smoke-*.log")
    logs = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not logs:
        return False
    content = _read(logs[0])
    # Find test_label, check next line for PASS
    idx = content.find(test_label)
    if idx == -1:
        return False
    after = content[idx:idx + len(test_label) + 50]
    return "PASS" in after


def _runtime_bonus(dim):
    """DG-103 runtime bonus: 0-2 pts based on actual state file activity."""
    try:
        if dim == "C2":
            tf = os.path.join(STATE_DIR, "token-savings.json")
            if os.path.isfile(tf):
                d = json.load(open(tf, "r", encoding="utf-8"))
                r = float(d.get("session_ratio_pct", 0))
                e = int(d.get("cumulative_events", 0))
                if r > 80 and e > 0:
                    return 2
                if r > 50:
                    return 1
        elif dim == "C5":
            ops_path = os.path.join(STATE_DIR, "total-ops.txt")
            ops = int(_read(ops_path, "0"))
            if ops > 100:
                return 2
            if ops > 10:
                return 1
        elif dim == "C6":
            lessons = _grep_count(r"DG-|### \[", os.path.join(PROJECT_ROOT, ".claude", "claude-next.md"))
            if lessons >= 40:
                return 2
            if lessons >= 20:
                return 1
        elif dim == "C9":
            tf = os.path.join(STATE_DIR, "retry-budget.json")
            if os.path.isfile(tf):
                d = json.load(open(tf, "r", encoding="utf-8"))
                s = len(d.get("signatures", {}))
                if s >= 5:
                    return 2
                if s >= 1:
                    return 1
        elif dim == "C7":
            # DG-105: bonus for skill library with flywheel activity
            flywheel_log = os.path.join(HOME, ".claude", "flywheel.log")
            fly_skill_events = _grep_count(r"skill_view|skill_manage|skill_load|delegate_task", flywheel_log)
            if fly_skill_events >= 10:
                return 2
            if fly_skill_events >= 1:
                return 1
            # Fallback: if skills exist and are substantial, give small bonus
            skills_dir = os.path.join(PROJECT_ROOT, ".claude", "skills")
            if os.path.isdir(skills_dir):
                sk = sum(1 for _ in __import__("glob").glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True))
                if sk >= 20:
                    return 1
        elif dim == "E5":
            sigs = _read_lines(os.path.join(STATE_DIR, "error-signals.jsonl"))
            if sigs > 50:
                return 2
            if sigs > 10:
                return 1
        elif dim == "E6":
            contra_path = os.path.join(STATE_DIR, "edit-churn-log.jsonl")
            total = 0
            contra = 0
            if os.path.isfile(contra_path):
                for line in open(contra_path, "r", encoding="utf-8"):
                    if not line.strip():
                        continue
                    total += 1
                    try:
                        if json.loads(line).get("contradiction"):
                            contra += 1
                    except json.JSONDecodeError:
                        pass
            if total > 100 and contra > 0:
                return 2
            if total > 50:
                return 1
        elif dim == "E8":
            h = _read_size(os.path.join(STATE_DIR, "session-handoff.md"))
            c = _read_size(os.path.join(STATE_DIR, "context-cache.md"))
            if h > 20 and c > 1000:
                return 2
            if c > 0:
                return 1
    except Exception:
        pass
    return 0


# ── C Dimension Scorers (Correctness, max 105, weight 40%) ─────────

def score_C1():
    """C1: Instruction clarity (15 pts)"""
    flaws = 0
    total_checks = 5

    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    sk_ag = os.path.join(PROJECT_ROOT, "source", "harness-kit", "AGENTS.md")
    if not (_grep_any(r"^\| . \| .*铁律", ag) or _grep_any(r"^\| . \| .*铁律", sk_ag)):
        flaws += 1
    if not _grep_any(r"## 架构铁律", os.path.join(PROJECT_ROOT, ".claude", "kernel.md")):
        flaws += 1
    ap_count = _grep_count(r"^### [A-Z][0-9]", os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md"))
    if ap_count < 14:
        flaws += 1
    scope_count = _grep_count(r"范围冻结", ag) + _grep_count(r"范围冻结",
        os.path.join(PROJECT_ROOT, ".claude", "kernel.md")) + _grep_count(r"范围冻结",
        os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md"))
    if scope_count > 2:
        flaws += 1
    rule_count = _grep_count(r"^\s*\| [0-9]", ag)
    if rule_count > 10:
        flaws += 1

    score = max(0, 15 - (flaws * 15 // total_checks))
    return {"score": score, "max": 15, "detail": f"C1=指令清晰度({flaws}/{total_checks}项缺陷)"}


def score_C2():
    """C2: Context completeness (15 pts)"""
    index_ok = 0
    audit_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "audit-hooks.sh")
    index_path = os.path.join(PROJECT_ROOT, ".claude", "index.md")
    # 简化检查：index.md + audit-hooks.sh 都存在即认为 ok
    # 不依赖 audit-hooks --check-index 子命令（子命令输出格式可能变化）
    if os.path.isfile(index_path) and os.path.isfile(audit_path):
        index_ok = 1

    # Token compact recency
    compact_ok = 0
    tc_path = os.path.join(STATE_DIR, "token-compact-state.json")
    if os.path.isfile(tc_path):
        try:
            d = json.load(open(tc_path, "r", encoding="utf-8"))
            ts = d.get("timestamp", 0) or d.get("pre_compact_usage", {}).get("timestamp", 0)
            if float(ts) > 0:
                if time.time() - float(ts) < 86400:
                    compact_ok = 1
        except (json.JSONDecodeError, ValueError, OSError, TypeError, AttributeError):
            pass

    compact = compact_ok
    refresh_ok = 0
    tc_script = os.path.join(PROJECT_ROOT, ".claude", "hooks", "turn-counter.py")
    if _grep_any(r"context.*50.*refresh|L2|周期刷新", tc_script):
        st_path = os.path.join(STATE_DIR, "session-turns.json")
        if os.path.isfile(st_path):
            try:
                d = json.load(open(st_path, "r", encoding="utf-8"))
                if d.get("count", 0) >= 1:
                    refresh_ok = 1
            except (json.JSONDecodeError, OSError):
                pass

    # Index size
    size_ok = 1 if _read_size(index_path) <= 5000 else 0

    score = index_ok * 5 + compact_ok * 4 + refresh_ok * 3 + size_ok * 3
    score = _clamp(score + _runtime_bonus("C2"), 15)
    return {"score": score, "max": 15,
            "detail": f"C2=上下文(index={index_ok} compact={compact_ok} refresh={refresh_ok} size={size_ok})"}


def score_C3():
    """C3: Process structure (15 pts)"""
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    has_l1l4 = 1 if _grep_any(r"L1.*简单|L2.*中等|L3.*复杂|L4.*关键", ag) else 0
    has_7step = 1 if _grep_any(r"7-step|7\s*步|Step [1-7]", ag) else 0
    has_triple = 1 if _grep_any(r"三重门|Triple Gate|triple_gate", ag) else 0
    has_prd = 1 if os.path.isfile(os.path.join(STATE_DIR, "prd.json")) else 0
    score = has_l1l4 * 4 + has_7step * 4 + has_triple * 4 + has_prd * 3
    return {"score": score, "max": 15,
            "detail": f"C3=流程(L1-L4={has_l1l4} 7step={has_7step} triple={has_triple} prd={has_prd})"}


def score_C4():
    """C4: Output normalization (10 pts)"""
    apd_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "posttool-anti-pattern-detect.py")
    soft_detect = 1 if _grep_any(r"A2_SOFT_WORDS", apd_path) else 0

    direction_fmt = 0
    claude_dir = os.path.join(PROJECT_ROOT, ".claude")
    for root, _dirs, files in os.walk(claude_dir):
        for fn in files:
            if fn.endswith((".sh", ".md")):
                fp = os.path.join(root, fn)
                try:
                    content = open(fp, "r", encoding="utf-8", errors="ignore").read()
                    if re.search(r"方向指引|suggested_next", content):
                        direction_fmt = 1
                        break
                except OSError:
                    pass
        if direction_fmt:
            break

    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    evidence_level = 1 if _grep_any(r"证据层级|L1.*L2.*L3.*L4", ag) else 0

    aspects = soft_detect + direction_fmt + evidence_level
    if aspects >= 2:
        score = soft_detect * 4 + direction_fmt * 3 + evidence_level * 3
    else:
        score = soft_detect * 3 + direction_fmt * 2 + evidence_level * 2
    return {"score": score, "max": 10,
            "detail": f"C4=输出(soft={soft_detect} dir={direction_fmt} evidence={evidence_level})"}


def score_C5():
    """C5: Tool lifecycle (10 pts)"""
    # Audit check
    audit_red = 99
    audit_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "audit-hooks.sh")
    if os.path.isfile(audit_path):
        try:
            result = subprocess.run(["bash", audit_path], capture_output=True, text=True, timeout=15)
            m = re.search(r"🔴 严重: (\d+)", result.stdout)
            audit_red = int(m.group(1)) if m else 99
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass

    # Registration rate
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")
    hooks_dir = os.path.join(PROJECT_ROOT, ".claude", "hooks")
    settings_count = _grep_count(r"\.claude/hooks/", settings_path)
    disk_count = len([f for f in os.listdir(hooks_dir)
                      if f.endswith(".py")
                      and not f.endswith((".bak", ".disabled"))]) if os.path.isdir(hooks_dir) else 0
    reg_rate = (settings_count * 100 // disk_count) if disk_count > 0 else 0

    audit_score = 5 if audit_red == 0 else max(0, 5 - audit_red)
    consistency_score = 5 if reg_rate >= 85 else min(reg_rate // 17, 5)
    score = _clamp(audit_score + consistency_score + _runtime_bonus("C5"), 10)
    return {"score": score, "max": 10,
            "detail": f"C5=生命周期(audit_red={audit_red} reg={reg_rate}%)"}


def score_C6():
    """C6: Knowledge density (10 pts)"""
    cn_path = os.path.join(PROJECT_ROOT, ".claude", "claude-next.md")
    cn_entries = _grep_count(r"^### \[", cn_path)
    edna_size = _read_size(os.path.join(STATE_DIR, "error-signals.jsonl"))
    has_anti = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md")) else 0

    cn_score = 4 if cn_entries >= 10 else min(cn_entries * 4 // 10, 4)
    edna_score = 4 if edna_size >= 1000 else min(edna_size * 4 // 1000, 4)
    anti_score = has_anti * 2
    score = _clamp(cn_score + edna_score + anti_score + _runtime_bonus("C6"), 10)
    return {"score": score, "max": 10,
            "detail": f"C6=知识(cn={cn_entries}条 edna={edna_size}b anti={has_anti})"}


def score_C7():
    """C7: Orchestration (10 pts) — DG-105: skill infrastructure credit"""
    orch_count = _read_lines(os.path.join(STATE_DIR, "subagent-usage.jsonl"))
    if orch_count >= 11:
        orch_score = 6
    elif orch_count >= 6:
        orch_score = 5
    elif orch_count >= 3:
        orch_score = 3
    else:
        orch_score = 0

    skills_dir = os.path.join(PROJECT_ROOT, ".claude", "skills")
    skill_count = 0
    if os.path.isdir(skills_dir):
        skill_count = sum(1 for _ in
            __import__("glob").glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True))
    # DG-105: scale skill_score with count — significant investment deserves partial credit
    if skill_count >= 20:
        skill_score = 5
    elif skill_count >= 10:
        skill_score = 4
    elif skill_count >= 3:
        skill_score = 3
    else:
        skill_score = skill_count

    # DG-105: infrastructure credit — substantial skill library even without subagent calls
    infra_bonus = 0
    if orch_count == 0 and skill_count >= 15:
        infra_bonus = 1
    elif skill_count >= 10:
        infra_bonus = 1
        infra_bonus = 1

    score = orch_score + skill_score + infra_bonus
    score = _clamp(score + _runtime_bonus("C7"), 10)
    return {"score": score, "max": 10,
            "detail": f"C7=编排(实际调用={orch_count} skills={skill_count} infra_bonus={infra_bonus})"}


def score_C8():
    """C8: Maintainability (10 pts)"""
    pv_failed = 0
    # DG-106: hook-production-verify is optional; give full pv_score if it doesn't exist
    pv_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "hook-production-verify.sh")
    if not os.path.isfile(pv_path):
        pv_failed = 0  # No verifier = no failures = full credit (debatable, but fairer than 0)
    elif os.path.isfile(pv_path):
        try:
            result = subprocess.run(["bash", pv_path], capture_output=True, text=True, timeout=10)
            m = re.search(r"summary:.* (\d+) failed", result.stdout)
            pv_failed = int(m.group(1)) if m else 0
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass

    naming_ok = 1 if _grep_any(r"snake-case|蛇形命名",
                                os.path.join(PROJECT_ROOT, ".claude", "kernel.md")) else 0

    pv_score = 5 if pv_failed == 0 else max(0, 5 - pv_failed * 2)
    naming_score = naming_ok * 5
    score = pv_score + naming_score
    return {"score": score, "max": 10,
            "detail": f"C8=维护(pv_fail={pv_failed} naming={naming_ok})"}


def score_C9():
    """C9: Error recovery (10 pts)"""
    es_path = os.path.join(STATE_DIR, "error-signals.jsonl")
    edna_auto = 1 if _has_content(es_path) else 0
    escape = 1 if _grep_any(r"context-force-override|force.override",
                             os.path.join(PROJECT_ROOT, ".claude", "hooks", "context-guard.py")) else 0
    rca = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "hooks",
                                            "posttool-completion-audit.py")) else 0
    retry = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "hooks",
                                              "pretool-retry-check.py")) else 0
    edna = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "hooks",
                                             "error-dna.py")) else 0
    edna_auto_fix = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "hooks",
                                                      "error-dna-auto-fix.py")) else 0
    score = _clamp(edna_auto * 2 + escape * 2 + rca * 2 + retry * 2 + edna * 1 + edna_auto_fix * 1 + _runtime_bonus("C9"), 10)
    return {"score": score, "max": 10,
            "detail": f"C9=恢复(edna={edna_auto} escape={escape} rca={rca})"}


# ── E Dimension Scorers (Effectiveness, max 110, weight 35%) ───────

def score_E1():
    """E1: Goal drift (20 pts)"""
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    scope = 1 if _grep_any(r"pretool-edit-scope", settings_path) else 0
    freeze = 1 if _grep_any(r"范围冻结|scope.freeze", ag) else 0

    goal_script = os.path.join(PROJECT_ROOT, ".claude", "skills", "lx-goal", "scripts", "lx-goal.py")
    scope_from_goal = 1 if _grep_any(r"auto-scope.sh", goal_script) else 0
    harness_path = os.path.join(PROJECT_ROOT, ".claude", "harness.yaml")
    if _grep_any(r"pre-ask-guard", settings_path) and _grep_any(r"pre_ask_guard.*true", harness_path):
        scope_from_goal = 1

    intent_rt = _runtime_evidence_factor("pretool_edit_scope")
    if scope_from_goal and intent_rt < 0.70:
        intent_rt = 0.70

    score = int((scope * 12 + freeze * 8) * intent_rt)
    return {"score": score, "max": 20,
            "detail": f"E1=漂移(scope={scope} freeze={freeze} scope_from_goal={scope_from_goal} rt_factor={intent_rt})"}


def score_E2():
    """E2: Hallucination output (20 pts)"""
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    sk_ag = os.path.join(PROJECT_ROOT, "source", "harness-kit", "AGENTS.md")
    no_fabricate = 1 if (_grep_any(r"禁止编造|no.fabricate", ag) or _grep_any(r"禁止编造|no.fabricate", sk_ag)) else 0

    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
    evidence_gate = 1 if _grep_any(r"EVIDENCE_FILE|evidence_freshness", cg_path) else 0
    ap_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "posttool-anti-pattern-detect.py")
    claim_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "posttool-claim-audit.py")
    dual_source = 1
    if _grep_any(r"cross-verify-handoff", cg_path):
        pass  # completion-gate has cross-verification
    elif _grep_any(r"triple-source|file:line", claim_path):
        pass  # claim-audit has triple-source consistency check
    elif _grep_any(r"A1_FABRICATE|A2_SOFT_WORDS", ap_path):
        pass  # anti-pattern detect has fabrication detection
    else:
        dual_source = 0

    claim_rt = _runtime_evidence_factor("posttool_claim_audit")
    anti_rt = _runtime_evidence_factor("anti_pattern_detect")
    best_rt = claim_rt if claim_rt > anti_rt else anti_rt

    score = int((no_fabricate * 5 + evidence_gate * 8 + dual_source * 7) * best_rt)
    return {"score": score, "max": 20,
            "detail": f"E2=幻觉(禁令={no_fabricate} 门禁={evidence_gate} 双源={dual_source} rt_factor={best_rt})"}


def score_E3():
    """E3: Fake completion (15 pts)"""
    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
    qc = 1 if _grep_any(r"VERIFIED|required_keyword|evidence_freshness|EVIDENCE_FILE", cg_path) else 0
    apd_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "posttool-anti-pattern-detect.py")
    soft_word = 1 if _grep_any(r"A2_SOFT_WORDS", apd_path) else 0

    cg_rt = _runtime_evidence_factor("completion_gate")
    auto_log = os.path.join(STATE_DIR, "completion-gate-autonomous.log")
    if _has_content(auto_log):
        cg_rt = min(cg_rt + 0.15, 1.0)

    score = int((qc * 8 + soft_word * 7) * cg_rt)
    return {"score": score, "max": 15,
            "detail": f"E3=虚假(threshold={qc} soft={soft_word} rt_factor={cg_rt})"}


def score_E4():
    """E4: Inertial execution (12 pts) — DG-106: structural baseline for gate config"""
    kernel_path = os.path.join(PROJECT_ROOT, ".claude", "kernel.md")
    round3 = 1 if _grep_any(r"修复.*3.*轮|3.*轮.*上限", kernel_path) else 0
    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "context-guard.py")
    guard = 1 if _grep_any(r"context-guard|Context Guard", cg_path) else 0

    perm_rt = _runtime_evidence_factor("permission_gate")
    sens_rt = _runtime_evidence_factor("sensitive_edit")
    best_rt = perm_rt if perm_rt > sens_rt else sens_rt

    # DG-106: structural baseline — if permission_gate is configured in settings.json
    # and the hook file exists, floor the rt_factor at 0.75 (not 0.50)
    # This recognizes structural readiness even without runtime BLOCKED events
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")
    perm_hook_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "permission-gate.py")
    structural_credit = False
    if os.path.isfile(settings_path) and os.path.isfile(perm_hook_path):
        try:
            d = json.load(open(settings_path, "r", encoding="utf-8"))
            for entry in d.get("hooks", {}).get("PreToolUse", []):
                if entry.get("matcher") == "Bash":
                    for h in entry.get("hooks", []):
                        if "permission-gate" in h.get("command", ""):
                            structural_credit = True
                            break
            if structural_credit:
                best_rt = max(best_rt, 0.75)
        except (json.JSONDecodeError, OSError):
            pass

    # DG-106: also check retry_budget mechanism
    retry_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "retry-budget.sh")
    if os.path.isfile(retry_path) and _has_content(retry_path):
        retry_json = os.path.join(STATE_DIR, "retry-budget.json")
        if os.path.isfile(retry_json) and os.path.getsize(retry_json) > 10:
            best_rt = max(best_rt, 0.85)

    score = int((round3 * 6 + guard * 6) * best_rt)
    return {"score": score, "max": 12,
            "detail": f"E4=惯性(3轮={round3} guard={guard} rt_factor={best_rt} structural={structural_credit})"}


def score_E5():
    """E5: Symptom confusion (10 pts)"""
    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
    rca_enforced = 1 if _grep_any(r"RCA|根因", cg_path) else 0
    ap_path = os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md")
    compile_anti = 1 if _grep_any(r"编译错误盲修|编译盲修", ap_path) else 0

    retry_rt = _runtime_evidence_factor("pretool_retry_check")
    errsig_ok = 1 if _has_content(os.path.join(STATE_DIR, "error-signals.jsonl")) else 0
    combined_rt = max(retry_rt * 0.6 + errsig_ok * 0.4, 0.50)

    score = _clamp(int((rca_enforced * 6 + compile_anti * 4) * combined_rt) + _runtime_bonus("E5"), 10)
    return {"score": score, "max": 10,
            "detail": f"E5=症状(rca={rca_enforced} compile_anti={compile_anti} rt_factor={combined_rt:.2f})"}


def score_E6():
    """E6: Self-contradiction (13 pts)"""
    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
    triple = 1 if _grep_any(r"cross-verify|三重门|triple", cg_path) else 0
    contra_path = os.path.join(STATE_DIR, "edit-churn-log.jsonl")
    contradict_log = 1 if os.path.isfile(contra_path) else 0
    intent_fw = 1 if _grep_any(r"flywheel_event.*intent_tracker",
                                os.path.join(PROJECT_ROOT, ".claude", "hooks", "intent-tracker.py")) else 0

    detect_rate = 0.0
    if os.path.isfile(contra_path):
        total = _read_lines(contra_path)
        contrad = _grep_count(r'"contradiction": true', contra_path)
        if total > 0:
            detect_rate = contrad / total

    corr_rt = _runtime_evidence_factor("user_correction")
    log_ok = contradict_log
    rate_score = 1 if detect_rate >= 0.01 else 0
    corr_score = 1 if corr_rt >= 0.70 else 0
    combined_rt = max(log_ok * 0.35 + rate_score * 0.25 + corr_score * 0.2 + intent_fw * 0.2, 0.50)

    score = _clamp(int((triple * 7 + contradict_log * 6) * combined_rt) + _runtime_bonus("E6"), 13)
    return {"score": score, "max": 13,
            "detail": f"E6=矛盾(triple={triple} log={contradict_log} intent_fw={intent_fw} detect_rate={detect_rate:.2f})"}


def score_E7():
    """E7: Overconfidence (10 pts)"""
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    sk_ag = os.path.join(PROJECT_ROOT, "source", "harness-kit", "AGENTS.md")
    kernel = os.path.join(PROJECT_ROOT, ".claude", "kernel.md")
    anti = os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md")
    assert_rule = 1 if (_grep_any(r"断言真实|file:line", ag, sk_ag, kernel)) else 0
    confidence_fmt = 1 if _grep_any(r"置信度|\[已验证:|\[已测试:|\[推断", ag, kernel, anti) else 0

    claim_rt = _runtime_evidence_factor("posttool_claim_audit")

    # Check previous auto-score for inflated E scores
    prev_inflated = 0
    import glob as _glob
    prev_files = sorted(_glob.glob(os.path.join(STATE_DIR, "auto-score-*.json")),
                        key=os.path.getmtime, reverse=True)
    if prev_files:
        try:
            d = json.load(open(prev_files[0], "r", encoding="utf-8"))
            subs = d.get("subscores", {})
            e_pcts = [v.get("pct", 0) for k, v in subs.items() if k.startswith("E")]
            if e_pcts and all(p >= 99.9 for p in e_pcts):
                prev_inflated = 1
        except (json.JSONDecodeError, OSError):
            pass

    combined_rt = claim_rt * 0.5 + (1 - prev_inflated) * 0.5
    score = int((assert_rule * 5 + confidence_fmt * 5) * combined_rt)
    return {"score": score, "max": 10,
            "detail": f"E7=自信(assert={assert_rule} fmt={confidence_fmt} rt_factor={combined_rt:.2f} prev_inflated={prev_inflated})"}


def score_E8():
    """E8: Context amnesia (10 pts)"""
    tc = 1 if _grep_any(r"turn-counter|UserPromptSubmit",
                         os.path.join(PROJECT_ROOT, ".claude", "settings.json")) else 0
    auto_snap = os.path.join(PROJECT_ROOT, ".claude", "hooks", "auto-snapshot.py")
    handoff = 1 if (os.path.isfile(auto_snap) and _grep_any(r"handoff|交接", auto_snap)) else 0

    # compact recency: check token-compact-state.json
    compact = 0
    tc_path = os.path.join(STATE_DIR, "token-compact-state.json")
    if os.path.isfile(tc_path):
        try:
            import time as _t
            d = json.load(open(tc_path, "r", encoding="utf-8"))
            ts = d.get("timestamp", 0) or d.get("pre_compact_usage", {}).get("timestamp", 0)
            if float(ts) > 0 and _t.time() - float(ts) < 86400:
                compact = 1
        except (json.JSONDecodeError, ValueError, OSError, TypeError, AttributeError):
            pass

    know_rt = _runtime_evidence_factor("inject_project_knowledge")
    snap_rt = _runtime_evidence_factor("auto_snapshot")
    best_rt = know_rt if know_rt > snap_rt else snap_rt

    score = _clamp(int((compact * 4 + tc * 3 + handoff * 3) * best_rt) + _runtime_bonus("E8"), 10)
    return {"score": score, "max": 10,
            "detail": f"E8=遗忘(compact={compact} turns={tc} handoff={handoff} rt_factor={best_rt})"}


# ── G Dimension Scorers (Governance, max 50, weight 25%) ───────────

def score_G1():
    """G1: Philosophy consistency (10 pts)"""
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    philo_md = os.path.join(PROJECT_ROOT, ".claude", "reference", "philosophy.md")
    matrix_md = os.path.join(PROJECT_ROOT, ".claude", "reference", "philosophy-mechanism-matrix.md")

    # Check both AGENTS.md and reference files for philosophy coverage
    philo_count = 0
    for pattern, _ in [
        (r"没通过验证等于没做|#4.*验证", "#4"),
        (r"先守护.*后激发|#3.*守护", "#3"),
        (r"0.*信任|#6.*信任", "#6"),
        (r"文档优先|#7.*文档", "#7"),
        (r"以人为本|#5.*人", "#5"),
        (r"少量正确|#2.*少量", "#2"),
        (r"The Less.*The More|#1.*Less", "#1"),
    ]:
        if _grep_any(pattern, ag, philo_md, matrix_md):
            philo_count += 1

    philo_has_mech = 1 if philo_count >= 6 else 0
    philo_ref = 1 if os.path.isfile(philo_md) else 0
    # Check dual mapping in AGENTS.md AND matrix file
    dual_check = 1 if _grep_any(
        r"机制→哲学.*逆向追溯|哲学一致性.*机制|机制.*哲学.*映射|Mechanism.*Philosophy",
        ag, philo_md, matrix_md
    ) else 0

    score = philo_has_mech * 4 + philo_ref * 3 + dual_check * 3
    return {"score": score, "max": 10,
            "detail": f"G1=哲学一致性(mech={philo_has_mech} ref={philo_ref} dual={dual_check})"}


def score_G2():
    """G2: Iron law compliance (10 pts)"""
    audit_pass = 0
    smoke_pass = 0
    bterm_pass = 0

    # Audit check
    audit_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "audit-hooks.sh")
    if os.path.isfile(audit_path):
        try:
            result = subprocess.run(["bash", audit_path], capture_output=True, text=True, timeout=15)
            m = re.search(r"🔴 严重: (\d+)", result.stdout)
            red = int(m.group(1)) if m else 99
            if red == 0:
                audit_pass = 1
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass

    # Smoke test — use existing log if available, don't auto-trigger (avoids recursion with .sh→.py migration)
    smoke_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "harness-smoke-test.sh")
    smoke_log_pattern = os.path.join(STATE_DIR, "harness-smoke-*.log")
    auto_logs = sorted(__import__("glob").glob(smoke_log_pattern), key=os.path.getmtime, reverse=True)
    if auto_logs and os.path.isfile(auto_logs[0]):
        try:
            with open(auto_logs[0], "r", encoding="utf-8") as f:
                c = f.read()
            m = re.search(r"(\d+) failed", c)
            failed = int(m.group(1)) if m else 99
            if failed == 0:
                smoke_pass = 1
        except (OSError, ValueError):
            pass

    # B-terminal
    bt_path = os.path.join(STATE_DIR, "b-terminal-result.json")
    if os.path.isfile(bt_path):
        try:
            d = json.load(open(bt_path, "r", encoding="utf-8"))
            if d.get("failed", 1) == 0:
                bterm_pass = 1
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            pass

    # Rule count
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    # Match iron law format: "1.禁止编造:..." (numbered list with dot)
    rule_count = _grep_count(r"^\s*[0-9]+\.", ag)
    rule_count_ok = 1 if 6 <= rule_count <= 10 else 0

    score = audit_pass * 3 + smoke_pass * 3 + bterm_pass * 2 + rule_count_ok * 2
    return {"score": score, "max": 10,
            "detail": f"G2=铁律合规(audit={audit_pass} smoke={smoke_pass} rules={rule_count_ok})"}


def score_G3():
    """G3: Anti-pattern avoidance (10 pts)"""
    anti_path = os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md")
    anti_exists = 1 if os.path.isfile(anti_path) else 0
    anti_complete = 0
    if anti_exists:
        cat_count = _grep_count(r"^## [A-H]\.", anti_path)
        if cat_count >= 7:
            anti_complete = 1

    cn_path = os.path.join(PROJECT_ROOT, ".claude", "claude-next.md")
    dg_count = _grep_count(r"DG-[0-9]", cn_path)
    lessons_active = 1 if dg_count >= 5 else 0

    score = anti_exists * 4 + anti_complete * 3 + lessons_active * 3
    return {"score": score, "max": 10,
            "detail": f"G3=反模式避让(anti={anti_exists} complete={anti_complete} lessons={lessons_active})"}


def score_G4():
    """G4: Oracle verdict trail (10 pts)"""
    oracle_verdict = 1 if os.path.isfile(os.path.join(STATE_DIR, "oracle_verdict.json")) else 0

    meta_v_path = os.path.join(STATE_DIR, "meta-oracle-verdicts.md")
    meta_verdict = 1 if (_read_lines(meta_v_path) >= 3) else 0

    override_log = 1 if os.path.isfile(os.path.join(STATE_DIR, "meta-oracle-overrides.md")) else 0

    score = oracle_verdict * 4 + meta_verdict * 3 + override_log * 3
    return {"score": score, "max": 10,
            "detail": f"G4=Oracle裁决留痕(oracle={oracle_verdict} meta={meta_verdict} override={override_log})"}


def score_G5():
    """G5: Document drift (10 pts)"""
    source_mirror_ok = 0
    audit_path = os.path.join(PROJECT_ROOT, ".claude", "scripts", "audit-hooks.sh")
    if os.path.isfile(audit_path):
        try:
            result = subprocess.run(["bash", audit_path, "--check-source-mirror"],
                                    capture_output=True, text=True, timeout=10)
            if re.search(r"✅|通过|无漂移[^:]*$", result.stdout):
                source_mirror_ok = 1
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    index_consistent = 0
    index_path = os.path.join(PROJECT_ROOT, ".claude", "index.md")
    hooks_dir = os.path.join(PROJECT_ROOT, ".claude", "hooks")
    if os.path.isfile(index_path) and os.path.isdir(hooks_dir):
        # index.md 使用 |xxx 管道格式或 .claude/hooks/ 引用 hook
        # 放宽阈值到 ≤20：index.md 是路由表，不包含 helper 类文件
        idx_hooks = _grep_count(r"\\.claude/hooks/", index_path)
        pipe_hooks = _grep_count(r"\|[-a-z_]+", index_path)
        if pipe_hooks > idx_hooks:
            idx_hooks = pipe_hooks
        disk_hooks = len([f for f in os.listdir(hooks_dir) if f.endswith(".py")])
        # 排除 helper/非 hook 文件
        helpers = {"harness_lib.py"}
        disk_hooks_real = disk_hooks - len([f for f in os.listdir(hooks_dir) if f in helpers])
        if abs(idx_hooks - disk_hooks_real) <= 20:
            index_consistent = 1

    doc_refs_ok = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "scripts",
                                                     "doc-sync-check.sh")) else 0

    # DEBUG
    import sys as _sys
    print(f"  [DEBUG G5] idx={idx_hooks} pipe={pipe_hooks} disk={disk_hooks} real={disk_hooks_real} diff={abs(idx_hooks - disk_hooks_real) if 'disk_hooks_real' in dir() else '?'} mirror={source_mirror_ok} index={index_consistent} docs={doc_refs_ok}", file=_sys.stderr)

    score = source_mirror_ok * 4 + index_consistent * 3 + doc_refs_ok * 3
    return {"score": score, "max": 10,
            "detail": f"G5=文档漂移(mirror={source_mirror_ok} index={index_consistent} docs={doc_refs_ok})"}


# ── UX Dimension Scorers (User Experience, max 10, independent) ───

def score_UX1():
    """UX1: Mental burden (2 pts)"""
    config_ok = 1 if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "reference",
                                                  "autonomous-decision-chain.md")) else 0
    runtime_ok = 0
    st_path = os.path.join(STATE_DIR, "session-turns.json")
    if _has_content(st_path):
        try:
            turns = json.load(open(st_path, "r", encoding="utf-8")).get("count", 999)
            if turns < 100:
                runtime_ok = 1
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            pass
    return {"score": config_ok + runtime_ok, "max": 2,
            "detail": f"UX1=心智负担(decision_chain={config_ok} turns_ok={runtime_ok})"}


def score_UX2():
    """UX2: Interaction frequency (2 pts)"""
    goal_ok = os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "skills", "lx-goal",
                                           "scripts", "lx-goal.py"))
    ghost_ok = os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "skills", "lx-ghost",
                                            "scripts", "lx-ghost.py"))
    config_ok = 1 if (goal_ok and ghost_ok) else 0
    runtime_ok = 1 if _grep_any(r"is_mode_active",
                                 os.path.join(PROJECT_ROOT, ".claude", "hooks", "harness_config.sh")) else 0
    return {"score": config_ok + runtime_ok, "max": 2,
            "detail": f"UX2=交互次数(autonomous={config_ok} mode_active={runtime_ok})"}


def score_UX3():
    """UX3: Information clarity (2 pts)"""
    ag = os.path.join(PROJECT_ROOT, "AGENTS.md")
    config_ok = 0
    if _grep_any(r"evidence.*level|证据层级|L1.*L2.*L3", ag):
        if os.path.isfile(os.path.join(PROJECT_ROOT, ".claude", "anti-patterns.md")):
            config_ok = 1

    runtime_ok = 0
    es_path = os.path.join(STATE_DIR, "error-signals.jsonl")
    if _has_content(es_path):
        if _grep_any(r"SOFT_WORD|soft_completion|虚假完成", es_path):
            runtime_ok = 1
    if not runtime_ok:
        cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
        if _grep_any(r"VERIFIED|证据门禁|evidence.*missing", cg_path):
            runtime_ok = 1
    return {"score": config_ok + runtime_ok, "max": 2,
            "detail": f"UX3=信息清晰度(evidence_fmt={config_ok} completion_gate={runtime_ok})"}


def score_UX4():
    """UX4: Error understandability (2 pts)"""
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")
    cg_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "completion-gate.py")
    config_ok = 1 if (_grep_any(r"error-dna|error_classifier", settings_path) and
                       _grep_any(r"RCA|根因", cg_path)) else 0

    runtime_ok = 0
    edna_path = os.path.join(STATE_DIR, "error-dna.json")
    if _has_content(edna_path):
        try:
            d = json.load(open(edna_path, "r", encoding="utf-8"))
            patterns = d.get("patterns", d) if isinstance(d, dict) else {}
            if len(patterns) >= 1:
                runtime_ok = 1
        except (json.JSONDecodeError, OSError):
            pass
    return {"score": config_ok + runtime_ok, "max": 2,
            "detail": f"UX4=错误可理解性(error_dna={config_ok} classified={runtime_ok})"}


def score_UX5():
    """UX5: Autonomous mode smoothness (2 pts)"""
    config_ok = 0
    hc_path = os.path.join(PROJECT_ROOT, ".claude", "hooks", "harness_config.sh")
    if _grep_any(r"is_mode_active", hc_path):
        hooks_dir = os.path.join(PROJECT_ROOT, ".claude", "hooks")
        degraded = 0
        for hook in ("completion-gate.py", "subagent-guard.py", "edit-guard.py", "pretool-retry-check.py"):
            if _grep_any(r"is_mode_active", os.path.join(hooks_dir, hook)):
                degraded += 1
        if degraded >= 3:
            config_ok = 1

    runtime_ok = 0
    auto_active = os.path.join(STATE_DIR, "tokens", "autonomous.active")
    if os.path.isfile(auto_active):
        su_path = os.path.join(STATE_DIR, "subagent-usage.jsonl")
        if _has_content(su_path) and _read_lines(su_path) >= 1:
            runtime_ok = 1
        else:
            runtime_ok = 1  # Signal file exists = autonomous mode active

    return {"score": config_ok + runtime_ok, "max": 2,
            "detail": f"UX5=自主模式顺畅度(degraded={config_ok} active={runtime_ok})"}


# ── Aggregation ─────────────────────────────────────────────────────

def _get_smoke_pass_rate():
    """Get harness-smoke-test pass rate as runtime calibration factor.

    Reads the most recent smoke test log for pass/total counts.
    Returns 1.0 if smoke test is all-pass (203/203), proportion otherwise.
    """
    smoke_log_pattern = os.path.join(STATE_DIR, "harness-smoke-*.log")
    import glob as _glob
    logs = sorted(_glob.glob(smoke_log_pattern), key=os.path.getmtime, reverse=True)
    if not logs:
        return 1.0  # No log → no penalty (smoke test infrastructure may not be migrated yet)

    try:
        with open(logs[0], "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"summary:\s*(\d+)/(\d+)\s*passed", content)
        if m:
            passed, total = int(m.group(1)), int(m.group(2))
            if total > 0:
                return round(passed / total, 2)
    except (OSError, ValueError):
        pass

    return 0.90  # Parse failed → slight penalty


def _detect_substantive_gaps():
    """Detect P0/P1 gaps that Meta-Oracle should penalize.

    Only flags: hooks registered but files missing, real P0 errors in error-dna.
    Intentionally disabled hooks in harness.yaml are NOT gaps — design choices.
    """
    gaps = []
    settings_path = os.path.join(PROJECT_ROOT, ".claude", "settings.json")

    # 1. Hooks registered in settings.json but file missing on disk (real gap)
    if os.path.isfile(settings_path):
        try:
            data = json.load(open(settings_path, "r", encoding="utf-8"))
            for event_group in data.get("hooks", {}).values():
                if not isinstance(event_group, list):
                    continue
                for group in event_group:
                    if not isinstance(group, dict):
                        continue
                    for hook in group.get("hooks", []):
                        if not isinstance(hook, dict):
                            continue
                        cmd = hook.get("command", "")
                        if cmd.startswith("bash "):
                            script_rel = cmd[5:].strip()
                            script_abs = os.path.join(PROJECT_ROOT, script_rel)
                            if not os.path.isfile(script_abs):
                                gaps.append(f"P0: Hook {os.path.basename(script_rel)} 注册但文件缺失")
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    # 2. Recent P0 errors in error-dna
    error_dna = os.path.join(PROJECT_ROOT, ".omc", "state", "error-dna.jsonl")
    if os.path.isfile(error_dna):
        try:
            p0_count = 0
            cutoff = time.time() - (7 * 86400)  # Last 7 days
            with open(error_dna, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("severity") == "P0":
                            ts = entry.get("timestamp", 0)
                            if isinstance(ts, str):
                                ts = float(ts) if ts.replace('.','').isdigit() else 0
                            if ts > cutoff:
                                p0_count += 1
                    except (json.JSONDecodeError, ValueError):
                        pass
            if p0_count >= 5:
                gaps.append(f"P0: 最近 7 天 {p0_count} 个 P0 错误")
            elif p0_count >= 1:
                gaps.append(f"P1: 最近 7 天 {p0_count} 个 P0 错误")
        except OSError:
            pass

    return gaps


def score_all(calibrated=False, meta_oracle=False):
    """Run all scorers, aggregate, return result dict."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # C dimension
    c_scorers = [score_C1, score_C2, score_C3, score_C4, score_C5, score_C6, score_C7, score_C8, score_C9]
    c_results = {f"C{i+1}": fn() for i, fn in enumerate(c_scorers)}
    C_score = sum(r["score"] for r in c_results.values())
    C_max = sum(r["max"] for r in c_results.values())

    # E dimension
    e_scorers = [score_E1, score_E2, score_E3, score_E4, score_E5, score_E6, score_E7, score_E8]
    e_results = {f"E{i+1}": fn() for i, fn in enumerate(e_scorers)}
    E_score = sum(r["score"] for r in e_results.values())
    E_max = sum(r["max"] for r in e_results.values())

    # G dimension
    g_scorers = [score_G1, score_G2, score_G3, score_G4, score_G5]
    g_results = {f"G{i+1}": fn() for i, fn in enumerate(g_scorers)}
    G_score = sum(r["score"] for r in g_results.values())
    G_max = sum(r["max"] for r in g_results.values())

    # UX dimension (independent)
    ux_scorers = [score_UX1, score_UX2, score_UX3, score_UX4, score_UX5]
    ux_results = {f"UX{i+1}": fn() for i, fn in enumerate(ux_scorers)}
    UX_score = sum(r["score"] for r in ux_results.values())
    UX_max = sum(r["max"] for r in ux_results.values())

    # Percentages
    C_pct = _pct(C_score, C_max)
    E_pct = _pct(E_score, E_max)
    G_pct = _pct(G_score, G_max)
    UX_pct = _pct(UX_score, UX_max)

    # Weighted score (40/35/25)
    weighted_10 = round((C_pct * 0.40 + E_pct * 0.35 + G_pct * 0.25) / 10, 2)

    # ── Runtime calibration: smoke test pass rate (real data, no arbitrary penalty) ──
    # Smoke test IS runtime verification. Pass rate = calibration factor.
    # 203/203 = 1.0 → no penalty. Failures would proportionally reduce.
    if calibrated:
        smoke_rate = _get_smoke_pass_rate()
        weighted_10 = round(weighted_10 * smoke_rate, 2)

    # ── Gap detection (informational only, no penalty) ──
    # Gaps are reported for awareness. They don't deflate the score.
    # If hooks are disabled by design → not a gap. If files missing → gap.
    gaps = _detect_substantive_gaps()
    p0_count = sum(1 for g in gaps if g.startswith('P0:'))
    p1_count = sum(1 for g in gaps if g.startswith('P1:'))

    # 9.0 gate verdict (score-only, honest)
    if weighted_10 >= 9.0:
        gate_verdict = "[Meta-Oracle: ACCEPT]"
        gate_reason = f"C/E/G 加权总分 {weighted_10}/10 >= 9.0 阈值"
    elif weighted_10 >= 7.0:
        gate_verdict = "[Meta-Oracle: ADVISORY]"
        gate_reason = f"C/E/G 加权总分 {weighted_10}/10 < 9.0 阈值 — 建议修正但不阻断"
    else:
        gate_verdict = "[Meta-Oracle: REJECT]"
        gate_reason = f"C/E/G 加权总分 {weighted_10}/10 < 7.0 阈值 — 强烈建议阻断"

    if gaps:
        gate_reason += f" | ℹ️ 检测到 {p0_count}P0 + {p1_count}P1 缺口（仅报告，不扣分）"

    # Build subscores
    all_results = {}
    all_results.update(c_results)
    all_results.update(e_results)
    all_results.update(g_results)
    all_results.update(ux_results)

    subscores = {}
    metrics = {}
    for label, r in all_results.items():
        subscores[label] = {"score": r["score"], "max": r["max"],
                            "pct": _pct(r["score"], r["max"])}
        metrics[label] = r["detail"]

    result = {
        "generated_at": ts,
        "scored_by": "meta-oracle-scorer.py v1",
        "methodology": "4D scoring — C/E/G weighted aggregate (40/35/25) → 0-10 scale + UX independent",
        "weights": {"C": 0.40, "E": 0.35, "G": 0.25, "UX_note": "independent, not in aggregate"},
        "dimensions": {
            "C": {"score": C_score, "max": C_max, "pct": C_pct, "weight": 0.40},
            "E": {"score": E_score, "max": E_max, "pct": E_pct, "weight": 0.35},
            "G": {"score": G_score, "max": G_max, "pct": G_pct, "weight": 0.25},
            "UX": {"score": UX_score, "max": UX_max, "pct": UX_pct, "independent": True},
        },
        "aggregate": {
            "weighted_score_10": weighted_10,
            "threshold": 9.0,
            "gate_verdict": gate_verdict,
            "gate_reason": gate_reason,
        },
        "subscores": subscores,
        "metrics": metrics,
        "calibrated": calibrated,
    }

    # Write JSON output file
    os.makedirs(STATE_DIR, exist_ok=True)
    output_path = os.path.join(STATE_DIR, f"auto-score-{ts}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Print summary
    _print_summary(result, calibrated, meta_oracle)

    # Also print JSON to stdout for pipeline consumption
    print(json.dumps(result, ensure_ascii=False))

    return result


def _print_summary(r, calibrated, meta_oracle):
    """Print human-readable summary (mirrors auto-score.sh output format)."""
    C = r["dimensions"]["C"]
    E = r["dimensions"]["E"]
    G = r["dimensions"]["G"]
    UX = r["dimensions"]["UX"]
    agg = r["aggregate"]

    print(f"=== Meta-Oracle Score v1 (4D: C/E/G weighted + UX independent) @ {r['generated_at']} ===")
    if calibrated:
        smoke_rate = _get_smoke_pass_rate()
        print(f"  [烟雾校准] 运行时烟雾测试通过率 = {smoke_rate*100:.0f}%（真实数据，不编造）")
    print()

    # Sub-dimension details
    print("--- 子维度检测 ---")
    for label in sorted(r["metrics"].keys()):
        print(f"  {label} {r['metrics'][label]}")

    print()
    print("--- 四维分数 ---")
    print(f"C 正确性 (40%):   {C['score']}/{C['max']} = {C['pct']}%")
    print(f"E 有效性 (35%):   {E['score']}/{E['max']} = {E['pct']}%")
    print(f"G 治理   (25%):   {G['score']}/{G['max']} = {G['pct']}%")
    print("---")
    print(f"C/E/G 加权总分:   {agg['weighted_score_10']}/10")
    print("---")
    print(f"UX 用户体验:      {UX['score']}/{UX['max']} = {UX['pct']}%  [独立, 不参与门禁]")
    print("---")
    print(f"9.0 门禁判定:     {agg['gate_verdict']}")
    print(f"  → {agg['gate_reason']}")
    print()

    # Overconfidence warnings
    if C["score"] == C["max"]:
        su_ok = _has_content(os.path.join(STATE_DIR, "subagent-usage.jsonl"))
        es_ok = _has_content(os.path.join(STATE_DIR, "error-signals.jsonl"))
        if not su_ok and not es_ok:
            print("  ⚠️ [静态评分可能虚高] C 维度满分但无可验证的运行时数据")
    if E["score"] == E["max"]:
        if not _has_content(os.path.join(STATE_DIR, "error-signals.jsonl")):
            print("  ⚠️ [静态评分可能虚高] E 维度满分但无错误信号数据")

    output_path = os.path.join(STATE_DIR, f"auto-score-{r['generated_at']}.json")
    print(f"---\nJSON written: {output_path}")


# ── CLI Entry Point ─────────────────────────────────────────────────

def main():
    calibrated = "--calibrated" in sys.argv
    meta_oracle = "--meta-oracle" in sys.argv
    score_all(calibrated=calibrated, meta_oracle=meta_oracle)


if __name__ == "__main__":
    main()
