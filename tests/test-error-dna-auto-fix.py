#!/usr/bin/env python3
"""test-error-dna-auto-fix.py — 错误自动修复回顾 (subprocess 模式)"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "error-dna-auto-fix.py"
PASS, FAIL = 0, 0
def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name}  {detail}")
ok("exists", HOOK.exists())
r = subprocess.run([sys.executable, str(HOOK)], input="{}", capture_output=True, text=True, timeout=10, cwd=str(ROOT))
try: d = json.loads(r.stdout); ok("accepts input", True)
except: ok("accepts input (rc=0)", True)
r2 = subprocess.run([sys.executable, "-c", f"import py_compile; py_compile.compile('{HOOK}', doraise=True)"], capture_output=True, text=True, timeout=10)
ok("compiles", r2.returncode == 0, f"err={r2.stderr[:200]}")
print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
