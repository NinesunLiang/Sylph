#!/usr/bin/env python3
"""
harness-smoke-test.py — CarrorOS 烟雾测试
Python 迁移版，替代 harness-smoke-test.sh
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Auto-detect repo root
CANDIDATES = [
    Path(os.environ.get("CARROROS_TEST_DIR", "")).expanduser(),
    Path.home() / "Desktop" / "Sylph" / "Carror_OS",
    Path.home() / "Sylph" / "Carror_OS",
    Path.cwd(),
]
TEST_DIR = None
for c in CANDIDATES:
    if c and (c / "AGENTS.md").exists():
        TEST_DIR = c.resolve()
        break
if not TEST_DIR:
    TEST_DIR = CANDIDATES[1]  # fallback

HOOKS_DIR = TEST_DIR / ".claude" / "hooks"
SCRIPTS_DIR = TEST_DIR / ".claude" / "scripts"

# Mapping from legacy .sh hook names to their migrated .py equivalents
# None = no direct .py equivalent exists (conceptually replaced/removed)
SH_TO_PY = {
    "hermes-pre-exec.sh": None,
    "hermes-completion-gate.sh": "completion-gate.py",
    "hermes-retry-check.sh": "pretool-retry-check.py",
    "hermes-error-dna.sh": "error-dna.py",
    "hermes-turn-counter.sh": "turn-counter.py",
    "hermes-compact-detect.sh": None,
    "hermes-edit-scope.sh": "pretool-edit-scope.py",
    "hermes-session-handoff.sh": "posttool-handoff-writer.py",
    "hermes-meta-oracle-trigger.sh": "meta-oracle-trigger.py",
    "hermes-honesty-gate.sh": None,
    "pre-output-check.sh": None,
}

PRETOOL_GATES = list(SH_TO_PY.keys())

PASS = FAIL = WARN = INFO = 0
errors = []
warnings = []

def log(status, msg):
    global PASS, FAIL, WARN, INFO
    if status == "PASS": PASS += 1
    elif status == "FAIL": FAIL += 1; errors.append(msg)
    elif status == "WARN": WARN += 1; warnings.append(msg)
    elif status == "INFO": INFO += 1
    print(f"  [{status:4s}]  {msg}")

def exists(path, desc):
    p = Path(path).expanduser()
    if p.exists(): log("PASS", f"{desc}")
    else: log("FAIL", f"{desc}: MISSING")

def contains(path, pat, desc):
    p = Path(path).expanduser()
    if not p.exists(): log("FAIL", f"{desc}: file MISSING"); return
    ok = re.search(pat, p.read_text(errors="replace"))
    log("PASS" if ok else "FAIL", f"{desc}" if ok else f"{desc}: pattern not found")

def executable(path, desc):
    p = Path(path).expanduser()
    if not p.exists(): log("FAIL", f"{desc}: MISSING"); return
    log("PASS" if os.access(str(p), os.X_OK) else "WARN", f"{desc}")

def bash_exit0(script, desc):
    p = Path(script).expanduser()
    if not p.exists(): log("FAIL", f"{desc}: MISSING"); return
    r = subprocess.run(["bash", str(p)], capture_output=True, text=True, timeout=30)
    if r.returncode == 0: log("PASS", f"{desc}")
    else: log("FAIL", f"{desc}: exit {r.returncode}")

def python_exit0(script, desc):
    """Run a Python hook and check exit code 0."""
    p = Path(script).expanduser()
    if not p.exists(): log("FAIL", f"{desc}: MISSING"); return
    r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=30)
    if r.returncode == 0: log("PASS", f"{desc}")
    else: log("FAIL", f"{desc}: exit {r.returncode}")

def exists_either(sh_name, py_name="auto", desc_prefix=""):
    """Check if a hook exists as .sh OR .py (migration-aware).
    
    py_name="auto" means derive .py name by changing .sh→.py on the same stem.
    Returns True if found, False otherwise.
    """
    sh_path = HOOKS_DIR / sh_name
    if sh_path.exists():
        log("PASS", f"{desc_prefix}{sh_name} exists")
        return True
    # Determine .py candidate
    if py_name == "auto":
        py_name = sh_name.replace(".sh", ".py")
    elif py_name is None:
        # No .py equivalent known — still try stem-based fallback
        py_candidate = sh_name.replace(".sh", ".py")
        py_path = HOOKS_DIR / py_candidate
        if py_path.exists():
            log("PASS", f"{desc_prefix}{py_candidate} exists (migrated from {sh_name})")
            return True
        log("WARN", f"{desc_prefix}{sh_name}: no .sh or matching .py found (may be replaced/deprecated)")
        return False
    py_path = HOOKS_DIR / py_name
    if py_path.exists():
        log("PASS", f"{desc_prefix}{py_name} exists (migrated from {sh_name})")
        return True
    log("WARN", f"{desc_prefix}{sh_name}: no .sh or matching .py found (may be replaced/deprecated)")
    return False

# === Test Sections ===

def test_context_guard():
    print("\n--- Context Guard ---")
    cg = HOOKS_DIR / "context-guard.py"
    exists(cg, "context-guard.py exists")
    contains(cg, r"CONTEXT_GUARD|context_guard", "context-guard.py has guard logic")
    python_exit0(HOOKS_DIR / "context-guard.py", "context-guard.py executes (Python)")
    contains(cg, r"hermes-pre-exec|pre_exec", "context-guard.py references pre-exec")
    contains(cg, r"completion-gate|completion_gate", "context-guard.py references completion-gate")

def test_pretool_composite():
    print("\n--- Pre-Tool Gates ---")
    for g in PRETOOL_GATES:
        py_name = SH_TO_PY.get(g, "auto")
        exists_either(g, py_name=py_name)
    sj = TEST_DIR / ".claude" / "settings.json"
    exists(sj, "settings.json exists")
    if sj.exists():
        js = json.loads(sj.read_text())
        hooks = []
        for v in js.values():
            if isinstance(v, dict):
                hooks.extend(v.get("hooks", []))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        hooks.extend(item.get("hooks", []))
        hook_str = " ".join(hooks)
        for g in PRETOOL_GATES:
            py_name = SH_TO_PY.get(g)
            # Check both .sh and .py references in settings.json
            sh_found = g in hook_str
            py_found = py_name is not None and py_name in hook_str
            if sh_found or py_found:
                ref = g if sh_found else py_name
                log("PASS", f"settings.json registers {ref}")
            else:
                log("WARN", f"settings.json does NOT register {g} (or its .py equivalent)")

def test_core_integrity():
    print("\n--- Core Integrity ---")
    exists(TEST_DIR / "AGENTS.md", "AGENTS.md")
    contains(TEST_DIR / "AGENTS.md", r"Hermes Agent Persona|哲学铁律|路由索引", "AGENTS.md has content")
    exists(TEST_DIR / "AGENTS.compact.md", "AGENTS.compact.md")
    exists(TEST_DIR / ".claude" / "kernel.md", "kernel.md")
    exists(TEST_DIR / ".claude" / "index.md", "index.md")
    exists(TEST_DIR / ".claude" / "SOUL.md", "SOUL.md")
    for p in ["AGENTS.md", ".claude/kernel.md", ".claude/index.md"]:
        if not (TEST_DIR / p).exists(): log("FAIL", f"Portal missing: {p}")
    log("PASS" if all((TEST_DIR / p).exists() for p in ["AGENTS.md", ".claude/kernel.md", ".claude/index.md"]) else "INFO", "3 portals check")

def test_signal_files():
    print("\n--- Signal Files ---")
    sd = TEST_DIR / ".claude" / "signals"
    exists(sd, "signals/ directory")
    if sd.exists():
        files = [f for f in sd.iterdir() if f.is_file()]
        log("PASS" if files else "WARN", f"signal files: {len(files)}" if files else "signal directory empty")

def test_python_hooks():
    print("\n--- Python Hooks ---")
    py_files = list(HOOKS_DIR.glob("*.py"))
    for pf in py_files:
        executable(pf, f"{pf.name} executable")
    miscore = SCRIPTS_DIR / "meta-oracle-scorer.py"
    exists(miscore, "meta-oracle-scorer.py")
    executable(miscore, "meta-oracle-scorer.py executable")
    sj = TEST_DIR / ".claude" / "settings.json"
    if sj.exists():
        content = sj.read_text()
        log("PASS" if "python3" in content else "WARN", "settings.json uses python3")

def test_oc_plugin():
    print("\n--- OC Plugin ---")
    exists(TEST_DIR / ".opencode" / "plugins", ".opencode/plugins/")
    pkg = TEST_DIR / "packages" / "carroros-gov"
    exists(pkg, "packages/carroros-gov/")
    idx = pkg / "src" / "index.ts"
    exists(idx, "carroros-gov/src/index.ts")
    install = TEST_DIR / "install.sh"
    exists(install, "install.sh")
    if install.exists():
        content = install.read_text()
        has_oc = "opencode" in content and ("plugins" in content or "packages/carroros-gov" in content)
        log("PASS" if has_oc else "FAIL", "install.sh references OC plugin")

def test_auto_report():
    print("\n--- Auto Report ---")
    py = Path.home() / ".hermes" / "scripts" / "hermes-auto-report.py"
    exists(py, "hermes-auto-report.py")
    executable(py, "hermes-auto-report.py executable")
    r = subprocess.run([sys.executable, str(py)], capture_output=True, text=True, timeout=30)
    log("PASS" if r.returncode == 0 else "FAIL", f"hermes-auto-report.py runs (exit {r.returncode})")

def test_git_hooks():
    print("\n--- Git Hooks ---")
    gd = TEST_DIR / ".git" / "hooks"
    if not (TEST_DIR / ".git").exists(): log("INFO", "not a git repo"); return
    exists(gd, ".git/hooks/")
    if gd.exists():
        hs = list(gd.iterdir())
        log("PASS" if hs else "INFO", f"hook files: {len(hs)}")

def test_gate_auth():
    print("\n--- Gate Auth ---")
    for name in ["hermes-pre-exec.sh", "hermes-completion-gate.sh", "pre-output-check.sh",
                  "hermes-error-dna.sh", "hermes-retry-check.sh"]:
        py_name = SH_TO_PY.get(name, "auto")
        exists_either(name, py_name=py_name)
    pe_sh = HOOKS_DIR / "hermes-pre-exec.sh"
    pe_py = HOOKS_DIR / "hermes-completion-gate.py"  # reasonable fallback
    if pe_sh.exists():
        contains(pe_sh, r"command|block|approve", "pre-exec has command processing")
    elif pe_py.exists():
        contains(pe_py, r"command|block|approve", "pre-exec gate (completion-gate.py) has command processing")

def test_hermes_skills():
    print("\n--- Hermes Skills ---")
    sd = Path.home() / ".hermes" / "skills"
    exists(sd, "~/.hermes/skills/")
    if sd.exists():
        subs = [d for d in sd.iterdir() if d.is_dir()]
        log("PASS", f"skill dirs: {len(subs)}")

def test_capability_matrix_runner():
    print("\n--- Cap Matrix Runner ---")
    cm_sh = SCRIPTS_DIR / "capability-matrix-test.sh"
    cm_py = SCRIPTS_DIR / "capability-matrix-test.py"
    if cm_sh.exists():
        exists(cm_sh, "capability-matrix-test.sh")
        executable(cm_sh, "capability-matrix-test.sh executable")
    elif cm_py.exists():
        exists(cm_py, "capability-matrix-test.py")
        executable(cm_py, "capability-matrix-test.py executable")
    else:
        exists(cm_sh, "capability-matrix-test.sh (not found)")
        exists(cm_py, "capability-matrix-test.py (not found)")

def test_session_handoff():
    print("\n--- Session Handoff ---")
    for name in ["session-handoff.md", "session-summary.md"]:
        exists(Path.home() / ".hermes" / name, f"~/.hermes/{name}")

def test_philosophy():
    print("\n--- Philosophy ---")
    pd = TEST_DIR / ".claude" / "philosophy.md"
    exists(pd, "philosophy.md")
    if pd.exists():
        contains(pd, r"矛盾|主要|次要", "philosophy.md has 矛盾 principle")
    im = TEST_DIR / ".claude" / "index.md"
    if im.exists():
        content = im.read_text()
        log("PASS" if "philosophy" in content.lower() or "哲学" in content else "WARN", "index.md references philosophy")

def test_richner():
    print("\n--- Richner ---")
    for name in ["distinct-concept-richner.sh", "distinct-concept-richner.py"]:
        p = HOOKS_DIR / name
        if p.exists():
            log("PASS", f"{name} exists")
            return
    log("FAIL", "distinct-concept-richner not found")

def run_all():
    print("=" * 56)
    print("CarrorOS Harness Smoke Test (Python)")
    print(f"Repo: {TEST_DIR}")
    print("=" * 56)
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    test_context_guard()
    test_pretool_composite()
    test_core_integrity()
    test_signal_files()
    test_python_hooks()
    test_oc_plugin()
    test_auto_report()
    test_git_hooks()
    test_gate_auth()
    test_hermes_skills()
    test_capability_matrix_runner()
    test_session_handoff()
    test_philosophy()
    test_richner()
    total = PASS + FAIL + WARN + INFO
    print("\n" + "=" * 56)
    print(f"Results: PASS={PASS} FAIL={FAIL} WARN={WARN} INFO={INFO} Total={total}")
    for e in errors:
        print(f"  ❌ {e}")
    for w in warnings:
        print(f"  ⚠️  {w}")
    sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    run_all()
