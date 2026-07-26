#!/usr/bin/env python3
"""test-posttool-claim-audit.py — Claim Audit (subprocess 模式)
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK = PROJECT_ROOT / ".claude" / "hooks" / "posttool-claim-audit.py"
PASS, FAIL = 0, 0
def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name}  {detail}")

ok("exists", HOOK.exists())
# write harness cache to enable hook
CACHE = PROJECT_ROOT / ".omc" / "state" / ".harness-cache"
CACHE.parent.mkdir(parents=True, exist_ok=True)
CACHE.write_text("__parsed_count__=1\nhooks_enabled.posttool_claim_audit=true\n")
r = subprocess.run([sys.executable, str(HOOK)], input='{"tool_name":"Edit","tool_input":{"file_path":"test.py"}}', capture_output=True, text=True, timeout=10, cwd=str(PROJECT_ROOT))
try:
    d = json.loads(r.stdout); ok("accepts Edit input", "continue" in d, f"got={r.stdout[:100]}")
except: ok("accepts Edit input", False, f"rc={r.returncode} out={r.stdout[:100]}")
r2 = subprocess.run([sys.executable, "-c", f"import py_compile; py_compile.compile('{HOOK}', doraise=True)"], capture_output=True, text=True, timeout=10)
ok("compiles", r2.returncode == 0, f"err={r2.stderr[:200]}")
print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
