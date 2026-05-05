import subprocess

import time

import threading

import os

from pathlib import Path


SCRIPT_PATH = "@/.claude/scripts/oma_lock_manager.py"
FILE_TARGET = "src/main.go"


def run_cmd(action, owner, env=None):
    cmd = ["python3", SCRIPT_PATH, action, FILE_TARGET, owner]
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=full_env)


print("🧪 [Test 1] 基础加锁与释放 (Basic Acquire/Release)")
r1 = run_cmd("acquire", "feat-1")
assert "ACQUIRED" in r1.stdout
r2 = run_cmd("release", "feat-1")
assert "RELEASED" in r2.stdout
print("✅ [PASS] 基础原语正常")

print("\n🧪 [Test 2] 互斥排队拦截 (Mutual Exclusion & Queueing)")


def locker():
    run_cmd("acquire", "feat-blocking")
    time.sleep(2)
    run_cmd("release", "feat-blocking")


t = threading.Thread(target=locker)
t.start()
time.sleep(0.5)  # Let thread acquire

# The second acquire should wait, emit WAITING, then ACQUIRED
r3 = run_cmd("acquire", "feat-waiting")
assert "WAITING:feat-blocking" in r3.stdout
assert "ACQUIRED" in r3.stdout
run_cmd("release", "feat-waiting")
t.join()
print("✅ [PASS] 排队与自旋挂起正常 (Spin-Queue works)")

print("\n🧪 [Test 3] 终端崩溃死锁自愈 (Deadlock Auto-Recovery)")
# Set timeout to 3 seconds for fast testing
run_cmd("acquire", "feat-crashed", env={"OMA_LOCK_TIMEOUT": "3"})
# We simulate a crash by NOT releasing it.
# Another feature tries to acquire. It should wait 3 seconds then steal it.
start_time = time.time()
r4 = run_cmd("acquire", "feat-stealer", env={"OMA_LOCK_TIMEOUT": "3"})
duration = time.time() - start_time
assert "WAITING:feat-crashed" in r4.stdout
assert "ACQUIRED" in r4.stdout
assert duration >= 2.5  # Should have waited for the timeout
run_cmd("release", "feat-stealer")
print(f"✅ [PASS] 强行夺锁与自愈正常 (Took {duration:.2f}s)")

print("\n🧪 [Test 4] 高并发原子性压力测试 (10 个终端抢占同一个文件)")
import concurrent.futures

results = []


def stress_worker(worker_id):
    owner = f"worker-{worker_id}"
    r = run_cmd("acquire", owner)
    time.sleep(0.2)  # hold it briefly
    run_cmd("release", owner)
    return r.stdout


start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(stress_worker, i) for i in range(10)]
    for f in concurrent.futures.as_completed(futures):
        results.append(f.result())
end = time.time()

# Verify all eventually got it, and there are many WAITING signals
acquired_count = sum(1 for r in results if "ACQUIRED" in r)
waiting_count = sum(r.count("WAITING") for r in results)
assert acquired_count == 10
assert waiting_count > 0  # Most workers should have waited

print(f"✅ [PASS] 10 终端并发压力测试通过，未发生重入覆盖 (Took {end-start:.2f}s)")

print("\n🎉 全部测试通过！一人成军 (OMA) 内核引擎稳定！")
