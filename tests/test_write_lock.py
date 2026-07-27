#!/usr/bin/env python3
"""test_write_lock.py — TDD: 先写测试，再验证 write_lock.py 实现

依赖树: write_lock.py (无依赖) → 先测
覆盖:
  1. write_with_lock 写入成功并验证内容
  2. 并发写入时锁互斥
  3. 超时返回 False
  4. 锁文件清理
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

# 先导入待测模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from write_lock import write_with_lock, set_lock_dir

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp-test-write-lock"
PASS, FAIL = 0, 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")

def setup():
    TMP.mkdir(parents=True, exist_ok=True)
    set_lock_dir(TMP)

def teardown():
    import shutil
    shutil.rmtree(str(TMP), ignore_errors=True)

# ── TDD Round 1: 测试先行 ──
setup()

# Test 1: write_with_lock 写入文件并验证内容
f1 = TMP / "test1.json"
r1 = write_with_lock(f1, {"key": "value", "num": 42})
ok("T1: write_with_lock 返回 True", r1 is True, f"got={r1}")
if f1.exists():
    d1 = json.loads(f1.read_text(encoding="utf-8"))
    ok("T1: 写入内容正确", d1 == {"key": "value", "num": 42}, f"got={d1}")
else:
    ok("T1: 文件存在", False, "文件未创建")

# Test 2: 覆盖写入
f2 = TMP / "test1.json"
r2 = write_with_lock(f2, {"updated": True})
ok("T2: 覆盖写入成功", r2 is True)
if f2.exists():
    d2 = json.loads(f2.read_text(encoding="utf-8"))
    ok("T2: 覆盖后内容正确", d2 == {"updated": True}, f"got={d2}")

# Test 3: 锁文件不残留
lock_files = list(TMP.glob("*.lock"))
ok("T3: 锁文件已清理", len(lock_files) == 0, f"lock_files={lock_files}")

# Test 4: 并发写入互斥
results = []
errors = []
def concurrent_write(name, data):
    try:
        fp = TMP / "concurrent.json"
        ok = write_with_lock(fp, data, timeout=3.0)
        results.append((name, ok))
    except Exception as e:
        errors.append((name, str(e)))

t1 = threading.Thread(target=concurrent_write, args=("A", {"writer": "A", "ts": time.time()}))
t2 = threading.Thread(target=concurrent_write, args=("B", {"writer": "B", "ts": time.time()}))
t1.start()
t2.start()
t1.join()
t2.join()

ok("T4: 并发写入无异常", len(errors) == 0, f"errors={errors}")
ok("T4: 至少一个写入成功", any(r for _, r in results), f"results={results}")

# Test 5: 超时返回 False
# 模拟持锁: 创建一个锁文件
stale_lock = TMP / "stale.json.lock"
stale_lock.write_text("99999")
# 立即写入应失败
r5 = write_with_lock(TMP / "stale.json", {"test": True}, timeout=0.5)
# 清除 stale lock (超过10s的会被自动清理，刚创建不到10s的会锁住)
# 所以这个测试应该是 timeout=0.5 后返回 False
ok("T5: 锁被占有时超时返回False", r5 is False)

# Test 6: 写列表数据
f6 = TMP / "list.json"
r6 = write_with_lock(f6, [1, 2, 3])
ok("T6: 列表写入成功", r6 is True)
if f6.exists():
    d6 = json.loads(f6.read_text(encoding="utf-8"))
    ok("T6: 列表内容正确", d6 == [1, 2, 3], f"got={d6}")

# Test 7: 写嵌套dict
f7 = TMP / "nested.json"
r7 = write_with_lock(f7, {"a": {"b": {"c": [1, 2, 3]}}, "d": None})
ok("T7: 嵌套数据写入成功", r7 is True)

teardown()

print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
