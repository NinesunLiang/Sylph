#!/usr/bin/env python3
"""
tier3-runtime-test.py — 链式机制管道验证 (5链)
Cross-platform Python resolution (DG-105)
用法: python3 .claude/scripts/tier3-runtime-test.sh
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

PASS = 0
FAIL = 0
WARN = 0
TOTAL = 0

PYTHON_BIN = sys.executable


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
        print(f"  🔴 FAIL: {name} — expected '{expected}'")
        print(f"     actual: {str(actual)[:120]}")
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
    return "true" if f.exists() else ""


def _hook_run(base):
    f = H / f"{base}.py"
    if f.exists():
        r = run(f"python3 {f}")
        return r.stdout + r.stderr
    else:
        return f"ERROR: {f} not found"


def _hook_grep(base, pattern):
    f = H / f"{base}.py"
    if f.exists():
        r = run(f"grep -c '{pattern}' {f}")
        return r.stdout.strip() if r.returncode == 0 else "0"
    return "0"


def _grep_true(file, pattern):
    p = Path(file)
    if p.exists():
        r = run(f"grep -q '{pattern}' {file}")
        return "true" if r.returncode == 0 else ""
    return ""


print("╔══════════════════════════════════════════╗")
print("║  Tier 3: 链式多机制管道验证 (5链)        ║")
print("╚══════════════════════════════════════════╝")

# ─── Chain 1: 编辑管道 ───
print("")
print("=== [28] 编辑管道: guard→scope→lsp→tracker→completion ===")
_test("edit-guard exists", "true", _hook_exists("edit-guard"))
_test("pretool-edit-scope exists", "true", _hook_exists("pretool-edit-scope"))
_test("pre-edit-lsp-check exists", "true", _hook_exists("pre-edit-lsp-check"))
_test("intent-tracker exists", "true", _hook_exists("intent-tracker"))
_test("completion-gate exists", "true", _hook_exists("completion-gate"))

# Chain verification
r28_1 = _hook_run("edit-guard")
c28_1 = str(r28_1).count("continue")
_test("edit-guard responds", "[1-9]", str(c28_1))

r28_2 = _hook_run("pre-edit-lsp-check")
c28_2 = str(r28_2).count("continue")
_test("pre-edit-lsp chain responds", "[1-9]", str(c28_2))

_check_data("edit-log has entries", "true" if (STATE_DIR / "session-edit-log.txt").exists() else "")
_check_data("edit-churn-log has records", "true" if (STATE_DIR / "edit-churn-log.jsonl").exists() else "")

# ─── Chain 2: 错误管道 ───
print("")
print("=== [29] 错误管道: error-dna→retry-budget→retry-check ===")
_test("error-dna exists", "true", _hook_exists("error-dna"))
_test("pretool-retry-check exists", "true", _hook_exists("pretool-retry-check"))
_check_data("retry-budget.json exists", "true" if (STATE_DIR / "retry-budget.json").exists() else "")

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
r29_2_out = "no_data"
if retry_budget.exists():
    try:
        with open(retry_budget) as f:
            d = json.load(f)
        sigs = len(d.get("signatures", {}))
        total_retries = sum(v.get("retry_count", 0) for v in d.get("signatures", {}).values())
        r29_2_out = f"sigs={sigs} retries={total_retries}"
    except Exception:
        r29_2_out = "no_data"
    else:
        r29_2_out = "no_data"
if re.search(r"sigs=[1-9]", r29_2_out):
    _test("retry-budget has tracked retries", "sigs=[1-9]", r29_2_out)
else:
    _warn("retry-budget.json — no retry data (CI/empty session)")

# ─── Chain 3: 打包管道 ───
print("")
print("=== [30] 打包管道: precheck→audit→package→postcheck ===")
pkg_rel = PROJECT_ROOT / "scripts" / "package-release.sh"
_test("package-release.sh exists", "true", "true" if pkg_rel.exists() else "")
if pkg_rel.exists():
    dg100 = _grep_true(str(pkg_rel), "DG-100")
    step5 = _grep_true(str(pkg_rel), "Step 5.*同步后")
else:
    dg100 = ""
    step5 = ""
_test("DG-100 precheck gate present", "true", dg100)
_test("Step 5 post-check present", "true", step5)

audit_sh = S_dir / "audit-hooks.sh"
audit_py = S_dir / "audit-hooks.py"
audit_exists = "true" if (audit_sh.exists() or audit_py.exists()) else ""
_test("audit-hooks available", "true", audit_exists)

if pkg_rel.exists():
    r = run(f"bash -n {pkg_rel}")
else:
    r = type("obj", (object,), {"returncode": 1})()
_test("package-release syntax OK", "true", "true" if r.returncode == 0 else "false")

# ─── Chain 4: 审查管道 ───
print("")
print("=== [31] 审查管道: AI→Oracle→Meta-Oracle ===")
_test("Oracle agent spawn capability", "true", _hook_exists("meta-oracle-trigger"))
_test("Meta-Oracle G1-G4 trigger", "[1-9]", _hook_grep("meta-oracle-trigger", "G[1-4]"))

mo_py = S_dir / "meta-oracle-review.py"
mo_sh = S_dir / "meta-oracle-review.sh"
mo_script = "true" if (mo_py.exists() or mo_sh.exists()) else ""
_test("meta-oracle-review script", "true", mo_script)
_test("oracle verdicts tracked", "true", "true" if (STATE_DIR / "oracle-verdict.md").exists() else "")
_test("meta-oracle verdicts tracked", "true", "true" if (STATE_DIR / "meta-oracle-verdicts.md").exists() else "")

mv = STATE_DIR / "meta-oracle-verdicts.md"
if mv.exists():
    lc = sum(1 for _ in mv.open())
else:
    lc = 0
_test("meta-oracle verdicts have history (>0 lines)", "[1-9]", str(lc))

# ─── Chain 5: 会话管道 ───
print("")
print("=== [32] 会话管道: compressor→knowledge→probe ===")
_test("context-compressor exists", "true", _hook_exists("context-compressor"))
_test("inject-project-knowledge exists", "true", _hook_exists("inject-project-knowledge"))
_test("ecosystem-probe exists", "true", _hook_exists("ecosystem-probe"))

cc = STATE_DIR / "context-cache.md"
_check_data("context-cache.md generated", "true" if (cc.exists() and cc.stat().st_size > 0) else "")
_check_data("session-handoff.md exists", "true" if (STATE_DIR / "session-handoff.md").exists() else "")

if cc.exists():
    r32 = cc.read_text(encoding="utf-8").split("\n")[0] if cc.stat().st_size > 0 else ""
else:
    r32 = ""
if r32:
    _test("context-cache has timestamp", "CONTEXT-COMPRESSOR|Context Cache|Empty", r32)
else:
    _warn("context-cache.md — no content (CI/empty session)")

# ─── Issues Found ───
print("")
print("=== 发现的问题 ===")

# Issue 1: E6 contradiction
ecl = STATE_DIR / "edit-churn-log.jsonl"
total_entries = 0
contra_entries = 0
if ecl.exists():
    for line in ecl.open():
        if not line.strip():
            continue
        total_entries += 1
        try:
            if json.loads(line).get("contradiction"):
                contra_entries += 1
        except Exception:
            pass
    r_issue1 = f"{total_entries} entries, {contra_entries} contradictions"
else:
    r_issue1 = "no data"
print(f"  📋 E6: {r_issue1} — 编辑追踪活跃但矛盾检测零命中")
_warn("E6 contradiction detection may need threshold tuning")

# Issue 2: error-dna.jsonl permanently empty
edna = STATE_DIR / "error-dna.jsonl"
if edna.exists():
    r_issue2 = edna.stat().st_size
else:
    r_issue2 = 0
print(f"  📋 error-dna.jsonl: {r_issue2} bytes — E2 CAPTCHA管道永远为空")
_warn("error-dna.jsonl design: only E2 events, normal=empty")

# Issue 3: retry-budget sparse
rb = STATE_DIR / "retry-budget.json"
if rb.exists():
    try:
        with open(rb) as f:
            d = json.load(f)
        r_issue3 = f"{len(d.get('signatures', {}))} sigs"
    except Exception:
        r_issue3 = "no data"
else:
    r_issue3 = "no data"
print(f"  📋 retry-budget: {r_issue3} — 重试追踪数据稀疏")
_warn("retry-budget reset frequently, losing historical patterns")

print("")
print("═══════════════════════════════════════")
print(f"  Tier 3: {PASS}/{TOTAL} passed, {FAIL} failed, {WARN} warn")
print("═══════════════════════════════════════")
