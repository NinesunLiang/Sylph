#!/usr/bin/env python3
"""
tier2-runtime-test.py — 配对机制协同验证
Cross-platform Python resolution (DG-105)
用法: python3 .claude/scripts/tier2-runtime-test.sh
"""
import sys
import os
import json
import subprocess
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
H = PROJECT_ROOT / ".claude" / "hooks"
S_dir = PROJECT_ROOT / ".claude" / "scripts"
SETTINGS = PROJECT_ROOT / ".claude" / "settings.json"
HARNESS = PROJECT_ROOT / ".claude" / "harness.yaml"
INDEX = PROJECT_ROOT / ".claude" / "index.md"
AGENTS = PROJECT_ROOT / "AGENTS.md"

PASS = 0
FAIL = 0
WARN = 0
TOTAL = 0


def run(cmd, **kwargs):
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    return subprocess.run(cmd, **default)


def _test(name, expected, actual):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if re.search(expected, str(actual)):
        print(f"  🟢 PASS: {name}")
        PASS += 1
    else:
        print(f"  🔴 FAIL: {name}")
        print(f"     expected: {expected}")
        print(f"     actual:   {str(actual)[:150]}")
        FAIL += 1


def _warn(msg):
    global TOTAL, WARN
    TOTAL += 1
    WARN += 1
    print(f"  ⚠️  WARN: {msg}")


def _check_data(name, cond):
    if cond == "true":
        global PASS, TOTAL
        PASS += 1
        TOTAL += 1
        print(f"  🟢 PASS: {name}")
    else:
        _warn(f"{name} — data not available (CI/empty session)")


def _hook_exists(base):
    f = H / f"{base}.py"
    if f.exists():
        return "true"
    return ""


def _hook_grep(base, pattern):
    f = H / f"{base}.py"
    if f.exists():
        r = run(f"grep -c '{pattern}' {f}")
        if r.returncode == 0:
            return r.stdout.strip() or "0"
        return "0"
    return "0"


def _grep_true(file, pattern):
    if Path(file).exists():
        r = run(f"grep -q '{pattern}' {file}")
        if r.returncode == 0:
            return "true"
    return ""


def _grep_count(file, pattern):
    if Path(file).exists():
        r = run(f"grep -c '{pattern}' {file}")
        if r.returncode == 0:
            return r.stdout.strip() or "0"
    return "0"


print("╔══════════════════════════════════════════╗")
print("║  Tier 2: 配对机制协同验证 (8对)          ║")
print("╚══════════════════════════════════════════╝")

# [19] completion-gate + posttool-completion-audit
print("")
print("=== [19] completion-gate + posttool-completion-audit ===")
_test("completion-gate exists", "true", _hook_exists("completion-gate"))
_test("posttool-completion-audit exists", "true", _hook_exists("posttool-completion-audit"))
c1 = int(_grep_count(str(SETTINGS), "completion-gate"))
c2 = int(_grep_count(str(SETTINGS), "posttool-completion-audit"))
both_reg = "true" if c1 > 0 and c2 > 0 else ""
_test("both registed in settings.json", "true", both_reg)

# [20] permission-gate + privacy-gate
print("")
print("=== [20] permission-gate + privacy-gate ===")
_test("permission-gate exists", "true", _hook_exists("permission-gate"))
_test("privacy-gate exists", "true", _hook_exists("privacy-gate"))
p1 = int(_grep_count(str(HARNESS), "permission_gate: true"))
p2 = int(_grep_count(str(HARNESS), "privacy_gate: true"))
both_enabled = "true" if p1 > 0 and p2 > 0 else ""
_test("both enabled in harness", "true", both_enabled)

# [21] pretool-edit-scope + intent-tracker
print("")
print("=== [21] pretool-edit-scope + intent-tracker ===")
_test("scope hook exists", "true", _hook_exists("pretool-edit-scope"))
_test("intent-tracker exists", "true", _hook_exists("intent-tracker"))
scope_file = STATE_DIR / "current-scope.txt"
if scope_file.exists():
    lc = sum(1 for _ in scope_file.open())
    cond = "true" if lc > 0 else ""
else:
    cond = ""
_check_data("scope log exists & non-empty", cond)
_check_data("edit-churn log exists", "true" if (STATE_DIR / "edit-churn-log.jsonl").exists() else "")

# [22] error-dna + retry-budget
print("")
print("=== [22] error-dna + retry-budget ===")
_test("error-dna exists", "true", _hook_exists("error-dna"))
_test("pretool-retry-check exists", "true", _hook_exists("pretool-retry-check"))
err_sig = STATE_DIR / "error-signals.jsonl"
if err_sig.exists():
    lc = sum(1 for _ in err_sig.open())
    if lc > 0:
        _test("error-signals pipeline active (>0 records)", "[1-9]", str(lc))
    else:
        _warn("error-signals.jsonl — no data (CI/empty session)")
else:
    _warn("error-signals.jsonl — no data (CI/empty session)")

retry_budget = STATE_DIR / "retry-budget.json"
r22_2_out = "no_data"
if retry_budget.exists():
    try:
        with open(retry_budget) as f:
            d = json.load(f)
        sigs = len(d.get("signatures", {}))
        total = sum(v.get("retry_count", 0) for v in d.get("signatures", {}).values())
        r22_2_out = f"sigs={sigs} retries={total}"
    except Exception:
        r22_2_out = "no_data"
if re.search(r"sigs=[1-9]", r22_2_out):
    _test("retry-budget has tracked retries", "sigs=[1-9]", r22_2_out)
else:
    _warn("retry-budget.json — no retry data (CI/empty session)")

# [24] lsp-suggest + pre-edit-lsp
print("")
print("=== [24] lsp-suggest + pre-edit-lsp ===")
_test("lsp-suggest exists", "true", _hook_exists("lsp-suggest"))
_test("pre-edit-lsp exists", "true", _hook_exists("pre-edit-lsp-check"))
pre_lsp = H / "pre-edit-lsp-check.py"
if pre_lsp.exists():
    r = run(f"echo '{{}}' | python3 {pre_lsp}", capture_output=True, text=True)
    passthrough = "true" if "continue" in r.stdout else ""
else:
    passthrough = ""
_test("pre-edit-lsp echo true passthrough", "true", passthrough)
grep_result = _grep_count(str(pre_lsp), "soft_fail\\|return True\\|exit 0")
_test("pre-edit-lsp tolerance", "[1-9]", grep_result)

# [25] Oracle + Meta-Oracle
print("")
print("=== [25] Oracle + Meta-Oracle ===")
oracle_gate = H / "oracle-gate.py"
_test("oracle-gate exists", "true", "true" if oracle_gate.exists() else "")
_check_data("oracle-verdicts.md exists", "true" if (STATE_DIR / "oracle-verdicts.md").exists() else "")
_test("meta-oracle-trigger exists", "true", _hook_exists("meta-oracle-trigger"))
meta_oracle_py = S_dir / "meta-oracle-review.py"
meta_oracle_sh = S_dir / "meta-oracle-review.sh"
if meta_oracle_py.exists():
    moe = "true"
elif meta_oracle_sh.exists():
    moe = "true"
else:
    moe = ""
_test("meta-oracle-review exists", "true", moe)
_check_data("oracle-verdicts.md exists (2)", "true" if (STATE_DIR / "oracle-verdicts.md").exists() else "")
_check_data("meta-oracle-verdicts.md exists", "true" if (STATE_DIR / "meta-oracle-verdicts.md").exists() else "")

# [26] blast-radius + permission-gate
print("")
print("=== [26] blast-radius + permission-gate ===")
blast_radius = H / "pretool-blast-radius.py"
if blast_radius.exists():
    r = run(f"echo '{{\"tool_name\":\"Bash\",\"tool_input\":{{\"command\":\"git checkout .\"}}}}' | python3 {blast_radius}", capture_output=True, text=True)
    br_result = "true" if r.returncode == 2 else ""
else:
    br_result = ""
_test("blast-radius blocks checkout .", "true", br_result)

perm_gate = H / "permission-gate.py"
if perm_gate.exists():
    r = run(f"echo '{{\"tool_name\":\"Bash\",\"tool_input\":{{\"command\":\"echo test\"}}}}' | python3 {perm_gate}", capture_output=True, text=True)
    pg_result = "true" if "continue" in r.stdout else ""
else:
    pg_result = ""
_test("permission-gate catches safe command", "true", pg_result)

# [27] package-release DG-100
print("")
print("=== [27] package-release DG-100 门禁 ===")
pkg_rel = PROJECT_ROOT / "scripts" / "package-release.sh"
if pkg_rel.exists():
    dg100 = _grep_true(str(pkg_rel), "DG-100")
else:
    dg100 = ""
_test("DG-100 gate in package-release", "true", dg100)
if pkg_rel.exists():
    r = run(f"bash -n {pkg_rel}")
    bash_ok = "true" if r.returncode == 0 else ""
else:
    bash_ok = ""
_test("package-release bash syntax OK", "true", bash_ok)

audit_sh = S_dir / "audit-hooks.sh"
audit_py = S_dir / "audit-hooks.py"
if audit_sh.exists():
    r = run(f"bash {audit_sh} --check-source-mirror", capture_output=True, text=True)
    mirror_clean = "true" if "🔴" not in r.stdout else ""
elif audit_py.exists():
    r = run(f"python3 {audit_py} --check-source-mirror", capture_output=True, text=True)
    mirror_clean = "true" if "🔴" not in r.stdout else ""
else:
    mirror_clean = ""
_test("source mirror clean", "true", mirror_clean)

print("")
print("══════════════════════════════════════════════")
print(f"  Tier 2: {PASS}/{TOTAL} passed, {FAIL} failed, {WARN} warn")
print("══════════════════════════════════════════════")
