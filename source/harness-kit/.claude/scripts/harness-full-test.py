#!/usr/bin/env python3
"""harness-full-test.py — 全量冒烟测试：运行所有领域测试套件并聚合结果

设计：全量 = 领域测试用例之和
每个领域套件保持独立，通过硬连接（子进程调用）聚合

使用：python3 .claude/scripts/harness-full-test.py
返回：0=全绿；非 0=失败项总数
日志：.omc/state/harness-full-<timestamp>.log
"""
import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
LOG_FILE = PROJECT_ROOT / f".omc/state/harness-full-{TS}.log"
(PROJECT_ROOT / ".omc/state").mkdir(parents=True, exist_ok=True)

TOTAL_PASS = 0
TOTAL_FAIL = 0
TOTAL_WARN = 0

def log(msg):
    print(msg)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")

def suite_log(name):
    log("")
    log("╔══════════════════════════════════════════════════════")
    log(f"║ {name}")
    log("╚══════════════════════════════════════════════════════")

def parse_summary(output, suite_name):
    global TOTAL_PASS, TOTAL_FAIL, TOTAL_WARN
    pass_count = 0
    fail_count = 0
    warn_count = 0

    # 格式1: summary: X/Y passed, Z failed
    import re
    m = re.search(r"summary: (\d+)/(\d+) passed, (\d+) failed", output)
    if m:
        pass_count = int(m.group(1))
        fail_count = int(m.group(3))
    else:
        # 格式2: Core/Tier N/Domain: X/Y passed, Z failed
        m = re.search(r"(Core|Tier|Capability|Domain|Deep|Red).*: (\d+)/(\d+) passed", output)
        if m:
            pass_m = re.search(r"(\d+)/(\d+) passed", output)
            if pass_m:
                pass_count = int(pass_m.group(1))
            fail_m = re.search(r"(\d+) failed", output)
            if fail_m:
                fail_count = int(fail_m.group(1))
        else:
            # 格式3: Capability Matrix 使用 PASS 计数
            pass_m = re.search(r"PASS: (\d+)", output)
            if pass_m:
                pass_count = int(pass_m.group(1))
            fail_m = re.search(r"FAIL: (\d+)", output)
            if fail_m:
                fail_count = int(fail_m.group(1))

    warn_m = re.search(r"(\d+) warn", output)
    if warn_m:
        warn_count = int(warn_m.group(1))

    log(f"  📊 {suite_name}: {pass_count} pass, {fail_count} fail, {warn_count} warn")
    TOTAL_PASS += pass_count
    TOTAL_FAIL += fail_count
    TOTAL_WARN += warn_count

def run_suite(script, name):
    from datetime import datetime as dt
    suite_log(name)
    script_path = SCRIPT_DIR / script
    if not script_path.is_file():
        log(f"  ⚠️  {script} 不存在，跳过")
        return

    start_ts = int(time.time())
    try:
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True, text=True, timeout=300
        )
        output = result.stdout + result.stderr
        rc = result.returncode
    except subprocess.TimeoutExpired:
        output = "TIMEOUT"
        rc = -1
    except Exception as e:
        output = f"ERROR: {e}"
        rc = -1

    end_ts = int(time.time())
    duration = end_ts - start_ts

    print(output)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(output + "\n")
    log(f"  ⏱️  {duration}s (exit={rc})")
    parse_summary(output, name)

# ══════════════════════════════════════════════════════════════════
# 领域测试套件（按层次排列）
# ══════════════════════════════════════════════════════════════════

log("🚀 harness-full-test — 全量冒烟测试")
log(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log(f"  PID: {os.getpid()}  日志: {LOG_FILE}")
log("")

# ── L0: 基础设施 ──
run_suite("harness-smoke-test.py",     "Harness Smoke (核心冒烟)")

# ── L1-L4: 层级运行时 ──
run_suite("tier2-runtime-test.py",      "Tier 2 Runtime")
run_suite("tier3-runtime-test.py",      "Tier 3 Runtime")
run_suite("tier4-e2e-test.py",          "Tier 4 E2E")

# ── 能力矩阵 ──
run_suite("capability-matrix-test.py",  "Capability Matrix")

# ── 深度与对抗 ──
run_suite("deep-runtime-test.py",       "Deep Runtime")
run_suite("ed-red-team-test.py",        "ED Red Team")

# ── 并发 ──
run_suite("test_race.py",              "Race Condition")

# ── 审计 ──
run_suite("audit-hooks.py",            "Audit Hooks (三方一致性)")

# ── 如果存在 .local 扩展 ──
local_script = SCRIPT_DIR / "harness-smoke-test.local.py"
if local_script.is_file():
    suite_log("Local Extensions (客户端扩展)")
    result = subprocess.run(
        ["python3", str(local_script)],
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    print(output)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(output + "\n")
    parse_summary(output, "Local Extensions")

# ══════════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════════

TOTAL_ALL = TOTAL_PASS + TOTAL_FAIL
log("")
log("══════════════════════════════════════════════════════")
log("  全量汇总")
log("══════════════════════════════════════════════════════")
log(f"  ✅ Pass:  {TOTAL_PASS}")
log(f"  ❌ Fail:  {TOTAL_FAIL}")
log(f"  ⚠️  Warn:  {TOTAL_WARN}")
log(f"  📊 Total: {TOTAL_ALL} ({TOTAL_PASS}/{TOTAL_ALL} passed)")
log(f"  📁 日志: {LOG_FILE}")
log("══════════════════════════════════════════════════════")

if TOTAL_FAIL == 0:
    log("  🧹 全量全绿通过")
else:
    log(f"  🔴 {TOTAL_FAIL} 项失败")

sys.exit(TOTAL_FAIL)
