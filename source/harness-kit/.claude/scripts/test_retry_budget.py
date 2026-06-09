#!/usr/bin/env python3
"""
test_retry_budget.py — R39 预算单元测试
验证 retry-budget.sh 在边界条件下的行为：
  - 0 次重试 (初始状态)
  - 正数重试 (1, 2, 3 = MAX_RETRIES)
  - 越界 (> MAX_RETRIES)
  - 签名隔离
  - 空/特殊签名 (防御性)
  - clear 重置

用法: python3 test_retry_budget.py
不修改生产代码，使用真实项目路径（因为 retry-budget.sh 硬编码了 PROJECT_ROOT）
"""
import sys
import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

PASS = 0
FAIL = 0

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RETRY_SCRIPT = PROJECT_ROOT / ".claude" / "scripts" / "retry-budget.sh"

ACTUAL_BUDGET = PROJECT_ROOT / ".omc" / "state" / "retry-budget.json"

# Save backup
backup_budget = None
if ACTUAL_BUDGET.exists():
    backup_budget = ACTUAL_BUDGET.read_text()

# Start fresh test budget
if ACTUAL_BUDGET.exists():
    ACTUAL_BUDGET.unlink()
(PROJECT_ROOT / ".omc" / "state").mkdir(parents=True, exist_ok=True)


def cleanup():
    if backup_budget is not None:
        ACTUAL_BUDGET.write_text(backup_budget)
    elif ACTUAL_BUDGET.exists():
        ACTUAL_BUDGET.unlink()


def assert_eq(desc, expected, actual):
    global PASS, FAIL
    if str(actual) == str(expected):
        print(f"  {GREEN}✅ PASS{NC} {desc}")
        PASS += 1
    else:
        print(f"  {RED}❌ FAIL{NC} {desc}")
        print(f"     expected: {expected}")
        print(f"     actual:   {actual}")
        FAIL += 1


def assert_contains(desc, expected_substring, actual):
    global PASS, FAIL
    if expected_substring in str(actual):
        print(f"  {GREEN}✅ PASS{NC} {desc}")
        PASS += 1
    else:
        print(f"  {RED}❌ FAIL{NC} {desc}")
        print(f"     expected substring: {expected_substring}")
        print(f"     actual: {actual}")
        FAIL += 1


def assert_exit_code(desc, expected_code, actual_code, output=""):
    global PASS, FAIL
    if int(actual_code) == int(expected_code):
        print(f"  {GREEN}✅ PASS{NC} {desc}")
        PASS += 1
    else:
        print(f"  {RED}❌ FAIL{NC} {desc} (exit: {actual_code}, expected: {expected_code})")
        if output:
            print(f"     output: {output}")
        FAIL += 1


def get_count(sig):
    if not ACTUAL_BUDGET.exists():
        return "0"
    try:
        d = json.loads(ACTUAL_BUDGET.read_text())
        return str(d.get("signatures", {}).get(sig, {}).get("retry_count", 0))
    except Exception:
        return "0"


def run_script(*args):
    """Run retry-budget.sh with given args"""
    cmd = ["bash", str(RETRY_SCRIPT)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr, r.returncode


print("=== R39 预算单元测试 ===")
print(f"测试脚本: {RETRY_SCRIPT}")
print(f"预算文件: {ACTUAL_BUDGET}")
print("")

# ── Test 1: 初始状态 ──
print("【1/9】初始状态 — 无重试记录")
if ACTUAL_BUDGET.exists():
    ACTUAL_BUDGET.unlink()
output, _ = run_script("status")
assert_contains("status 输出含 'no retry data'", "(no retry data)", output)
_, ec = run_script("check")
assert_exit_code("check 无文件返回 0", 0, ec, "")
print("")

# ── Test 2: 第1次 record ──
print("【2/9】正数重试 — 第1次")
output, _ = run_script("record", "test_sig_1", "test error 1")
assert_contains("record 输出含 retry 1/3", "retry 1/3", output)
if ACTUAL_BUDGET.exists():
    print(f"  {GREEN}✅ PASS{NC} budget file created")
    PASS += 1
else:
    print(f"  {RED}❌ FAIL{NC} budget file not created")
    FAIL += 1
assert_eq("retry_count == 1", "1", get_count("test_sig_1"))
print("")

# ── Test 3: 第2次 → 未超限 ──
print("【3/9】正数重试 — 第2次 (未超限)")
output, _ = run_script("record", "test_sig_1", "test error 1")
assert_contains("record 输出含 retry 2/3", "retry 2/3", output)
_, ec = run_script("check")
assert_exit_code("check 未超限返回 0", 0, ec, "")
print("")

# ── Test 4: 第3次 → 达到上限 ──
print("【4/9】正数重试 — 第3次 (达到上限)")
output, _ = run_script("record", "test_sig_1", "test error 1")
assert_contains("record 输出含 BLOCKED", "BLOCKED", output)
output, ec = run_script("check")
assert_exit_code("check 超限返回 2", 2, ec, output)
assert_contains("check 输出含 BLOCKED", "BLOCKED", output)
print("")

# ── Test 5: 第4次 → 越界 ──
print("【5/9】越界重试 — 第4次 (> MAX_RETRIES=3)")
output, _ = run_script("record", "test_sig_1", "test error 1")
assert_contains("record 第4次仍输出 BLOCKED", "BLOCKED", output)
assert_eq("retry_count == 4 (仍在累加)", "4", get_count("test_sig_1"))
print("")

# ── Test 6: 签名隔离 ──
print("【6/9】签名隔离 — 不同签名互不影响")
run_script("record", "test_sig_2", "another error")
run_script("record", "test_sig_2", "another error")
output, _ = run_script("status")
assert_contains("status 显示 sig_1 为 BLOCKED", "BLOCKED", output)
assert_contains("status 显示 sig_2 为 ok", "ok", output)
assert_eq("sig_2 retry_count == 2", "2", get_count("test_sig_2"))
print("")

# ── Test 7: 空签名 ──
print("【7/9】边界输入 — 空签名")
output, ec = run_script("record", "", "empty sig")
if "retry 1/3" in output:
    print(f"  {GREEN}✅ PASS{NC} 空签名可 record (无报错)")
    PASS += 1
else:
    print(f"  {YELLOW}⚠️  INFO{NC} 空签名可能失败: {output.strip().split(chr(10))[-1] if output else 'no output'}")
print("")

# ── Test 8: 特殊/长签名 ──
print("【8/9】边界输入 — 特殊字符 + 长签名")
output, _ = run_script("record", "sig_special_!@#$%", "special")
assert_contains("特殊字符签名可 record", "retry", output)
long_sig = "a" * 500
output, _ = run_script("record", long_sig, "very long sig")
assert_contains("长签名(500字符)可 record", "retry", output)
print("")

# ── Test 9: clear 重置 ──
print("【9/9】clear 重置 — 清除后恢复正常")
run_script("clear", "test_sig_1")
_, ec = run_script("check")
assert_exit_code("clear 后 check 返回 0", 0, ec, "")
output, _ = run_script("record", "test_sig_1", "fresh start")
assert_contains("clear 后 record 从 1 开始", "retry 1/3", output)
print("")

# ── Summary ──
TOTAL = PASS + FAIL
print("==============================")
print("  R39 预算单元测试: ")
print(f"  通过: {PASS} / {TOTAL}")
print(f"  失败: {FAIL} / {TOTAL}")
print("==============================")

# Auto-cleanup restores actual budget
cleanup()

sys.exit(0 if FAIL == 0 else 1)
