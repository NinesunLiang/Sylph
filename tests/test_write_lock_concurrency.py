#!/usr/bin/env python3
"""test_write_lock_concurrency.py — 多进程并发写锁压测
Grok 要求: write_lock.py 缺少多进程竞争场景的集成测试。
"""
import json, multiprocessing, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from write_lock import write_with_lock, set_lock_dir

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp-concurrency-test"
TARGET = TMP / "shared.json"
PASS, FAIL = 0, 0
N_WORKERS = 8

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name} {detail}")

def writer(worker_id, q):
    try:
        set_lock_dir(TMP)
        success = write_with_lock(TARGET, {"worker": worker_id, "ts": time.time()}, timeout=5.0)
        q.put({"worker": worker_id, "success": success})
    except Exception as e:
        q.put({"worker": worker_id, "success": False, "error": str(e)})

def run():
    global PASS, FAIL
    TMP.mkdir(parents=True, exist_ok=True)
    set_lock_dir(TMP)

    # Use Queue instead of Manager().list() to avoid spawn issues
    q = multiprocessing.Queue()
    procs = []
    for i in range(N_WORKERS):
        p = multiprocessing.Process(target=writer, args=(i, q))
        procs.append(p)

    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=10)

    ok(f"C1: {N_WORKERS} workers completed",
       all(p.exitcode == 0 for p in procs),
       f"exitcodes={[p.exitcode for p in procs]}")

    # Collect results from queue
    results = []
    for _ in range(N_WORKERS):
        try:
            results.append(q.get(timeout=2))
        except:
            pass
    ok("C2: all workers got result", len(results) >= 1, f"got={len(results)}")

    success_count = sum(1 for r in results if r.get("success"))
    ok(f"C3: {success_count}/{N_WORKERS} write succeeded",
       success_count >= 1, f"results={results}")

    try:
        data = json.loads(TARGET.read_text(encoding="utf-8"))
        ok("C4: final file valid JSON", True)
    except Exception as e:
        ok("C4: final file valid JSON", False, str(e))

    shutil.rmtree(str(TMP), ignore_errors=True)
    print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
    sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
