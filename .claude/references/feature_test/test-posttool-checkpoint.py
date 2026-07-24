#!/usr/bin/env python3
"""test-posttool-checkpoint.py — Checkpoint 生成(subprocess 模式)
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HOOK = PROJECT_ROOT / ".claude" / "hooks" / "posttool-checkpoint.py"
PASS, FAIL = 0, 0
def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name}  {detail}")
ok("exists", HOOK.exists())
r = subprocess.run([sys.executable, str(HOOK)], input="{}", capture_output=True, text=True, timeout=10, cwd=str(PROJECT_ROOT))
try:
    d = json.loads(r.stdout)
    ok("accepts input (or silent)", r.returncode == 0, f"got={r.stdout[:100]}")
except Exception:
    ok("accepts input (or silent)", r.returncode == 0, f"rc={r.returncode}")
r2 = subprocess.run([sys.executable, "-c", f"import py_compile; py_compile.compile('{HOOK}', doraise=True)"], capture_output=True, text=True, timeout=10)
ok("compiles", r2.returncode == 0, f"err={r2.stderr[:200]}")
print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
