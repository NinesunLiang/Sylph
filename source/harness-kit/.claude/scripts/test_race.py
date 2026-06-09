#!/usr/bin/env python3
"""
test_race.py — Race 蜂群协调层集成测试
Cross-platform Python resolution (DG-105)

测试范围:
  - register:   注册子任务 → manifest.json + owner.json 结构验证
  - status --all: 聚合子任务状态 (partial completion)
  - report:     完整聚合报告
  - 错误处理:   缺失参数/无效操作
  - clean:      清理

Usage:
  python3 test_race.py            # 运行全部测试
  python3 test_race.py --verbose  # 详细输出
  python3 test_race.py <pattern>  # 运行匹配的测试
"""
import sys
import os
import json
import re
import subprocess
from pathlib import Path

VERBOSE = False
TEST_PATTERN = ".*"
if len(sys.argv) > 1:
    if sys.argv[1] == "--verbose":
        VERBOSE = True
        TEST_PATTERN = sys.argv[2] if len(sys.argv) > 2 else ".*"
    else:
        TEST_PATTERN = sys.argv[1]

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RACE_MANAGER = SCRIPT_DIR / "race_manager.sh"
RACE_DIR = PROJECT_ROOT / ".omc" / "race"

PASS = 0
FAIL = 0
SKIP = 0

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup():
    for d in ["test-swarm-parent", "test-standalone", "test-err"]:
        p = RACE_DIR / d
        if p.exists():
            shutil.rmtree(p)


def teardown():
    for d in ["test-swarm-parent", "test-standalone", "test-err"]:
        p = RACE_DIR / d
        if p.exists():
            shutil.rmtree(p)


def assert_eq(expected, actual, msg=""):
    if str(expected) == str(actual):
        return True
    else:
        if msg:
            print(f"  ASSERT FAIL: {msg}", file=sys.stderr)
        print(f"  expected: '{expected}'", file=sys.stderr)
        print(f"  actual:   '{actual}'", file=sys.stderr)
        return False


def assert_contains(haystack, needle, msg=""):
    if needle in str(haystack):
        return True
    else:
        if msg:
            print(f"  ASSERT FAIL: {msg}", file=sys.stderr)
        print(f"  expected to contain: '{needle}'", file=sys.stderr)
        return False


def assert_file_exists(file, msg=""):
    p = Path(file)
    if p.exists():
        return True
    else:
        if msg:
            print(f"  ASSERT FAIL: {msg}", file=sys.stderr)
        print(f"  file not found: {file}", file=sys.stderr)
        return False


def run_manager(*args):
    cmd = ["bash", str(RACE_MANAGER)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr, r.returncode


import shutil

# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_register_basic():
    """register: 3 subtasks + structure"""
    out, _ = run_manager("register", "test-swarm-parent", "--subtasks", "A,B,C", "--desc", "test parent")
    if "RACE_REGISTERED" not in out:
        return False
    if not assert_file_exists(str(RACE_DIR / "test-swarm-parent" / "manifest.json"), "manifest.json"):
        return False
    if not assert_file_exists(str(RACE_DIR / "test-swarm-parent" / "subtasks" / "A" / "owner.json"), "A/owner.json"):
        return False
    if not assert_file_exists(str(RACE_DIR / "test-swarm-parent" / "subtasks" / "B" / "owner.json"), "B/owner.json"):
        return False
    if not assert_file_exists(str(RACE_DIR / "test-swarm-parent" / "subtasks" / "C" / "owner.json"), "C/owner.json"):
        return False

    manifest_file = RACE_DIR / "test-swarm-parent" / "manifest.json"
    with open(manifest_file) as f:
        d = json.load(f)
    if not assert_eq("3", str(d["total_subtasks"]), "expected 3 subtasks"):
        return False
    if not assert_eq("test-swarm-parent", d["parent_id"], "wrong parent_id"):
        return False

    owner_a = RACE_DIR / "test-swarm-parent" / "subtasks" / "A" / "owner.json"
    with open(owner_a) as f:
        d2 = json.load(f)
    if not assert_eq("registered", d2["status"], "expected registered"):
        return False
    return True


def test_register_missing_subtasks():
    """register: error without --subtasks"""
    out, _ = run_manager("register", "test-swarm-parent")
    if "ERROR: --subtasks is required" not in out:
        return False
    if (RACE_DIR / "test-swarm-parent").exists():
        return False
    return True


def test_register_duplicate():
    """register: error on duplicate parent"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B")
    out, _ = run_manager("register", "test-swarm-parent", "--subtasks", "C,D")
    if "ERROR: race 'test-swarm-parent' already exists" not in out:
        return False
    return True


def test_status_all_basic():
    """status --all: aggregation"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B,C")
    run_manager("complete", "test-swarm-parent/A", "completed", "Task A done")
    run_manager("complete", "test-swarm-parent/B", "failed", "Task B failed")
    out, _ = run_manager("status", "test-swarm-parent", "--all")
    if "1/3 completed" not in out:
        print("no 1/3")
        return False
    if "1 failed" not in out:
        print("no 1 failed")
        return False
    if "1 registered" not in out:
        print("no 1 registered")
        return False
    return True


def test_status_all_json():
    """status --all: JSON output"""
    run_manager("register", "test-swarm-parent", "--subtasks", "X,Y")
    run_manager("complete", "test-swarm-parent/X", "completed", "X done")
    out, _ = run_manager("status", "test-swarm-parent", "--all", "--json")
    try:
        data = json.loads(out)
        assert data['race_id'] == 'test-swarm-parent', f"wrong race_id: {data['race_id']}"
        assert data['total'] == 2, f"wrong total: {data['total']}"
        assert data['completed'] == 1, f"wrong completed: {data['completed']}"
        assert data['running'] == 0, f"wrong running: {data['running']}"
        assert len(data['subtasks']) == 2, f"wrong subtask count: {len(data['subtasks'])}"
    except (json.JSONDecodeError, AssertionError, KeyError) as e:
        return False
    return True


def test_status_all_non_parent():
    """status --all: error on non-parent race"""
    run_manager("init", "test-standalone", "standalone task")
    out, _ = run_manager("status", "test-standalone", "--all")
    if "ERROR" not in out:
        return False
    return True


def test_complete_updates_manifest():
    """complete: updates parent manifest"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B")
    run_manager("complete", "test-swarm-parent/A", "completed", "A done")
    run_manager("complete", "test-swarm-parent/B", "completed", "B done")
    manifest_file = RACE_DIR / "test-swarm-parent" / "manifest.json"
    with open(manifest_file) as f:
        d = json.load(f)
    if not assert_eq("2", str(d["completed_subtasks"]), "expected 2 completed"):
        return False
    return True


def test_report_basic():
    """report: full aggregation"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B,C", "--desc", "Integration test")
    run_manager("complete", "test-swarm-parent/A", "completed", "A output")
    run_manager("complete", "test-swarm-parent/B", "completed", "B output")
    run_manager("complete", "test-swarm-parent/C", "failed", "C error")
    out, _ = run_manager("report", "test-swarm-parent")
    if "Race Report: test-swarm-parent" not in out:
        return False
    if "2/3 completed" not in out:
        print("no 2/3")
        return False
    if "1 failed" not in out:
        print("no 1 failed")
        return False
    if "A output" not in out:
        return False
    if "C error" not in out:
        return False
    return True


def test_report_no_manifest():
    """report: error on non-parent race"""
    run_manager("init", "test-standalone", "standalone")
    out, _ = run_manager("report", "test-standalone")
    if "ERROR" not in out:
        return False
    return True


def test_list_shows_swarm():
    """list: shows X/Y for parent races"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B")
    run_manager("complete", "test-swarm-parent/A", "completed", "")
    out, _ = run_manager("list")
    if "swarm 1/2" not in out:
        return False
    return True


def test_clean_subtask_parent():
    """clean: removes parent race"""
    run_manager("register", "test-swarm-parent", "--subtasks", "A,B")
    run_manager("complete", "test-swarm-parent/A", "completed", "")
    run_manager("complete", "test-swarm-parent/B", "completed", "")
    run_manager("clean", "test-swarm-parent")
    if (RACE_DIR / "test-swarm-parent").exists():
        return False
    return True


def test_bad_complete_status():
    """complete: invalid status error"""
    run_manager("init", "test-err", "error test")
    out, _ = run_manager("complete", "test-err", "in_progress")
    if "ERROR: status must be 'completed' or 'failed'" not in out:
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TEST_NAMES = []
TEST_FUNCS = []


def register_test(name, func):
    TEST_NAMES.append(name)
    TEST_FUNCS.append(func)


register_test("register: 3 subtasks + structure", test_register_basic)
register_test("register: error without --subtasks", test_register_missing_subtasks)
register_test("register: error on duplicate parent", test_register_duplicate)
register_test("status --all: aggregation", test_status_all_basic)
register_test("status --all: JSON output", test_status_all_json)
register_test("status --all: error on non-parent", test_status_all_non_parent)
register_test("complete: updates parent manifest", test_complete_updates_manifest)
register_test("report: full aggregation", test_report_basic)
register_test("report: error on non-parent", test_report_no_manifest)
register_test("list: shows swarm X/Y", test_list_shows_swarm)
register_test("clean: removes parent race", test_clean_subtask_parent)
register_test("complete: invalid status error", test_bad_complete_status)


def run_test(name, func):
    global PASS, FAIL, SKIP
    if not re.search(TEST_PATTERN, name):
        SKIP += 1
        return

    print(f"  [TEST] {name} ... ", end="")

    # Reset workspace for each test
    teardown()
    setup()

    if VERBOSE:
        print("")
        if func():
            print("    → PASS")
            PASS += 1
        else:
            print("    → FAIL")
            FAIL += 1
    else:
        try:
            result = func()
            if result:
                print(f"{GREEN}PASS{NC}")
                PASS += 1
            else:
                print(f"{RED}FAIL{NC}")
                FAIL += 1
        except Exception as e:
            print(f"{RED}FAIL{NC}")
            print(f"  exception: {e}")
            FAIL += 1


print("")
print("==========================================")
print("  Race Manager Integration Tests")
print("==========================================")
print("")

for i in range(len(TEST_NAMES)):
    run_test(TEST_NAMES[i], TEST_FUNCS[i])

# Final teardown
teardown()

print("")
print("==========================================")
print(f"  Results: {GREEN}{PASS} PASS{NC} / {RED}{FAIL} FAIL{NC} / {YELLOW}{SKIP} SKIP{NC}")
print("==========================================")
print("")

sys.exit(0 if FAIL == 0 else 1)
