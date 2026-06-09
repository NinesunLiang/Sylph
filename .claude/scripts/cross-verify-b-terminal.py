#!/usr/bin/env python3
"""cross-verify-b-terminal.py — B 终端跨会话独立验证
Cross-platform Python resolution (DG-105)

Role: 在独立终端中运行 verification 任务，不与 AI 主会话共享上下文
三扇门 A→B→A 的 B 环节：盲执行验证

用法:
  python3 cross-verify-b-terminal.py                    # 运行标准验证套件
  python3 cross-verify-b-terminal.py --quick             # 快速验证
  python3 cross-verify-b-terminal.py --full              # 全量验证 + smoke test

原理:
  - 独立 python 进程，不读取 AI 上下文
  - 只信任文件系统事实（exit code, file content, checksum）
  - 输出 JSON 结果供 AI 读取（Source III 运行时事实）

哲学映射:
  #4 没验证=没做 — 独立验证是最后一步
  #6 0信任 — 不信任 AI 上下文中的任何断言
"""
import sys
import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc/state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

MODE = sys.argv[1] if len(sys.argv) > 1 else "--standard"
RESULT_FILE = STATE_DIR / "b-terminal-result.json"
START_TS = int(time.time())

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def run(cmd, **kwargs):
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    result = subprocess.run(cmd, **default)
    return result.stdout.strip(), result.returncode, result.stderr

print("=== B-Terminal Cross-Verify ===")
print(f"Started: {now_iso()}")
print(f"Mode: {MODE}")
print()

PASSED = 0
FAILED = 0
CHECKS = []

def run_check(name, cmd):
    global PASSED, FAILED
    print(f"[ ] {name} ... ", end="", flush=True)
    stdout, rc, stderr = run(cmd)
    if rc == 0:
        print("PASS")
        PASSED += 1
        CHECKS.append({"name": name, "status": "PASS"})
    else:
        print("FAIL")
        FAILED += 1
        CHECKS.append({"name": name, "status": "FAIL"})

# ─── 核心验证 ───────────────────────────────────────────────
run_check("harness-smoke-test", f"python3 {PROJECT_ROOT}/.claude/scripts/harness-smoke-test.py 2>&1 | grep -q 'summary:.*0 failed'")
run_check("audit-hooks-zero-critical", f"python3 {PROJECT_ROOT}/.claude/scripts/audit-hooks.py 2>&1 | grep -q '🔴 严重: 0'")
run_check("source-mirror-consistent", f"python3 {PROJECT_ROOT}/.claude/scripts/audit-hooks.py --check-source-mirror 2>&1 | grep -q '全部一致'")

# 快速验证只跑核心
if MODE == "--quick":
    print()
    print("=== Quick Check Complete ===")
    result = {
        "terminal": "B", "mode": "quick", "passed": PASSED, "failed": FAILED,
        "total": PASSED + FAILED, "duration_sec": int(time.time()) - START_TS,
        "checks": CHECKS, "timestamp": now_iso()
    }
    RESULT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(FAILED)

# ─── 扩展验证 ───────────────────────────────────────────────
run_check("flywheel-log-exists", "[ -f ~/.claude/flywheel.log ] && [ -s ~/.claude/flywheel.log ]")
run_check("error-signals-exists", f"[ -f {STATE_DIR}/error-signals.jsonl ] && [ -s {STATE_DIR}/error-signals.jsonl ]")
run_check("hook-syntax-all", f"for f in {PROJECT_ROOT}/.claude/hooks/*.py {PROJECT_ROOT}/.claude/hooks/*.sh; do [ -f \"$f\" ] && python3 -c \"compile(open('$f').read(), '$(basename $f)', 'exec')\" 2>/dev/null || exit 1; done")

rc_check = 0
if MODE == "--full":
    run_check("auto-score-above-8.6", f"python3 {PROJECT_ROOT}/.claude/scripts/auto-score.py 2>&1 | grep -q '>= 8.6'")
    # bash-audit may have .py version
    run_check("audit-no-critical", f"python3 {PROJECT_ROOT}/.claude/scripts/audit-hooks.py 2>&1 | grep -qv 'CRITICAL'")

# ─── 输出结果 ───────────────────────────────────────────────
print()
print("=== B-Terminal Result ===")
print(f"Passed: {PASSED} | Failed: {FAILED} | Total: {PASSED+FAILED}")
print(f"Duration: {int(time.time()) - START_TS}s")

result = {
    "terminal": "B", "mode": MODE, "passed": PASSED, "failed": FAILED,
    "total": PASSED + FAILED, "duration_sec": int(time.time()) - START_TS,
    "checks": CHECKS, "timestamp": now_iso()
}
RESULT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))

sys.exit(FAILED)
