#!/usr/bin/env python3
"""
验证 race-tool.py 的完整可用性。

考察：
1. 全部 CLI 命令功能
2. 状态机边界（非法转换）
3. 异常路径（重复 dispatch、空 batch、不存在的任务）
4. 并发安全（多 subagent 同时 update）
5. 集成：race-tool.py → delegate_task → subagent 读取 task.md 和写入 result.md
"""

import json
import subprocess
import sys
import os
import pathlib
import tempfile
import threading

TOOL = "packages/carroros-gov/src/scripts/race-tool.py"
ROOT = os.path.expanduser("~/Desktop/Sylph/Carror_OS")
TOOL_ABS = os.path.join(ROOT, TOOL)
PASS = 0
FAIL = 0


def run(*args, expect_pass=True) -> dict:
    global PASS, FAIL
    r = subprocess.run(
        [sys.executable, TOOL_ABS] + list(args),
        capture_output=True, text=True, timeout=15
    )
    if expect_pass:
        if r.returncode == 0:
            PASS += 1
        else:
            FAIL += 1
            print(f"  ❌ FAIL (exit={r.returncode}): {' '.join(args)}")
            print(f"     stderr: {r.stderr[:200]}")
    else:
        if r.returncode != 0:
            PASS += 1
        else:
            FAIL += 1
            print(f"  ❌ FAIL (expected error but passed): {' '.join(args)}")
    try:
        return json.loads(r.stdout) if r.stdout else {"_raw": r.stdout}
    except json.JSONDecodeError:
        return {"_raw": r.stdout, "_stderr": r.stderr}


def test_help():
    print("\n[test_help]")
    r = subprocess.run([sys.executable, TOOL_ABS, "help"], capture_output=True, text=True)
    if r.returncode == 0 and "Race Tool" in r.stdout:
        print("  ✅ PASS")
        return True
    print(f"  ❌ FAIL: {r.stdout[:200]}")
    return False


def test_init_dispatch():
    """基础 E2E: init → dispatch → status → update → collect → report"""
    global PASS, FAIL
    print("\n[test_init_dispatch]")

    # init
    data = run("init", "验证测试", "--parallel", "3", "--desc", "验证race-tool的完整功能")
    bid = data.get("batch_id")
    if not bid:
        FAIL += 1
        print("  ❌ FAIL: no batch_id from init")
        return
    print(f"  batch_id: {bid}")

    # dispatch
    tasks = json.dumps([
        {"id": "code-review", "goal": "审查模块A", "context": "src/module_a.py", "criteria": ["无安全漏洞", "命名规范"]},
        {"id": "test-check", "goal": "审查测试覆盖", "context": "tests/", "criteria": ["覆盖率>80%"]},
    ])
    data = run("dispatch", bid, "--tasks", tasks)
    assert data.get("created") == 2, f"Expected 2 created, got {data}"
    print("  ✅ dispatch 2 tasks")

    # status
    data = run("status", bid)
    assert data["state_counts"].get("pending") == 2, f"Expected 2 pending, got {data['state_counts']}"
    print("  ✅ status: 2 pending")

    # update t1: pending → running
    t1_path = data["tasks"][0]["path"]
    t2_path = data["tasks"][1]["path"]
    run("update", t1_path, "running")

    # status after t1 running
    data = run("status", bid)
    assert data["state_counts"].get("running") == 1, f"Expected 1 running, got {data}"
    print("  ✅ status: 1 running after update")

    # t1: write result + done
    pathlib.Path(t1_path, "result.md").write_text("# code-review 结果\n\n全部通过。\n")
    run("update", t1_path, "done", "完成")

    # t2: pending → running → done (direct)
    pathlib.Path(t2_path, "result.md").write_text("# test-check 结果\n\n覆盖率92%。\n")
    run("update", t2_path, "running")
    run("update", t2_path, "done")

    # collect
    data = run("collect", bid)
    assert data["total"] == 2, f"Expected 2 total, got {data}"
    states = {r["id"]: r["state"] for r in data["results"]}
    assert states == {"code-review": "done", "test-check": "done"}, f"Unexpected states: {states}"
    print("  ✅ collect: 2/2 done")

    # report
    data = run("report", bid)
    assert data["summary"]["completion"] == "100.0%"
    print(f"  ✅ report: completion={data['summary']['completion']}")

    # list
    data = run("list", "--limit", "5")
    assert len(data["batches"]) >= 1
    print("  ✅ list OK")

    # Cleanup
    import shutil
    shutil.rmtree(os.path.dirname(t1_path.rstrip("/").rsplit("/", 1)[0]), ignore_errors=True)
    print("  ✅ cleanup ok")


def test_state_machine_boundaries():
    """状态机边界：非法转换、重复 update、超限"""
    global PASS, FAIL
    print("\n[test_state_machine_boundaries]")

    b = run("init", "状态机边界测试")
    bid = b["batch_id"]
    tasks = json.dumps([{"id": "sm1", "goal": "test", "context": "x", "criteria": ["ok"]}])
    run("dispatch", bid, "--tasks", tasks)
    data = run("status", bid)
    tp = data["tasks"][0]["path"]

    # pending → done: should be rejected (must go through running)
    r = subprocess.run(
        [sys.executable, TOOL_ABS, "update", tp, "done"],
        capture_output=True, text=True
    )
    if r.returncode != 0 and "非法状态转换" in (r.stdout + r.stderr):
        PASS += 1
        print("  ✅ pending→done rejected (must go through running)")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: expected rejection, got exit={r.returncode} {r.stdout[:100]}")

    # pending → running (valid)
    run("update", tp, "running")

    # running → running (same state): should be rejected
    r = subprocess.run(
        [sys.executable, TOOL_ABS, "update", tp, "running"],
        capture_output=True, text=True
    )
    if r.returncode != 0 and "非法状态转换" in (r.stdout + r.stderr):
        PASS += 1
        print("  ✅ running→running rejected (no self-loop)")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: expected rejection for self-loop")

    # running → done (valid)
    pathlib.Path(tp, "result.md").write_text("# done\n")
    run("update", tp, "done")

    # done → anything: should be rejected (final state)
    r = subprocess.run(
        [sys.executable, TOOL_ABS, "update", tp, "running"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        PASS += 1
        print("  ✅ done→running rejected (done is terminal)")
    else:
        FAIL += 1
        print("  ❌ FAIL: expected rejection from terminal state")

    # Cleanup
    import shutil
    shutil.rmtree(os.path.dirname(tp.rstrip("/").rsplit("/", 1)[0]), ignore_errors=True)


def test_error_paths():
    """异常路径：不存在 batch、空 tasks、部分 task 失败"""
    global PASS, FAIL
    print("\n[test_error_paths]")

    # 不存在的 batch
    r = subprocess.run(
        [sys.executable, TOOL_ABS, "status", "nonexistent-batch"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        PASS += 1
        print("  ✅ nonexistent batch rejected")
    else:
        FAIL += 1
        print("  ❌ FAIL: should reject nonexistent batch")

    # 空 tasks
    b = run("init", "空tasks测试")
    bid = b["batch_id"]
    data = run("dispatch", bid, "--tasks", "[]")
    if data.get("created") == 0:
        PASS += 1
        print("  ✅ empty tasks: created=0")
    else:
        FAIL += 1
        print("  ❌ FAIL: expected 0 created for empty tasks")

    import shutil
    shutil.rmtree(os.path.expanduser(f"~/Desktop/Sylph/Carror_OS/.omc/plan/*/{bid}"), ignore_errors=True)

    # report 不存在 batch
    r = subprocess.run(
        [sys.executable, TOOL_ABS, "report", "invalid-batch"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        PASS += 1
        print("  ✅ report on nonexistent batch rejected")
    else:
        FAIL += 1
        print("  ❌ FAIL: should reject report on nonexistent batch")


def test_race_mode_characteristic():
    """验证 race 模式特性：同一个 batch 可以处理多个独立任务"""
    global PASS, FAIL
    print("\n[test_race_mode_characteristic]")

    b = run("init", "5任务并行测试", "--parallel", "10")
    bid = b["batch_id"]

    # Dispatch 5 tasks
    tasks = json.dumps([
        {"id": f"task-{i}", "goal": f"模拟任务{i}", "context": f"ctx_{i}", "criteria": [f"ac_{i}"]}
        for i in range(5)
    ])
    data = run("dispatch", bid, "--tasks", tasks)
    assert data["created"] == 5
    print("  ✅ dispatched 5 tasks")

    data = run("status", bid)
    assert data["state_counts"].get("pending") == 5
    print("  ✅ 5 pending")

    # Concurrent updates (simulating multi-subagent)
    tasks_data = data["tasks"]

    def update_subagent(t):
        tp = t["path"]
        t_id = t["id"]
        run("update", tp, "running")
        pathlib.Path(tp, "result.md").write_text(f"# {t_id} 完成\n")
        run("update", tp, "done", f"{t_id} complete")

    threads = [threading.Thread(target=update_subagent, args=(t,)) for t in tasks_data]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    data = run("report", bid)
    assert data["summary"]["done"] == 5
    print(f"  ✅ 5/5 done after concurrent updates: completion={data['summary']['completion']}")

    import shutil
    shutil.rmtree(os.path.dirname(tasks_data[0]["path"].rstrip("/").rsplit("/", 1)[0]), ignore_errors=True)
    print("  ✅ cleanup")


def test_integration_simulation():
    """模拟真实子树任务场景：main → delegate_task → subagent 读 task.md 写 result.md
    
    不实际调 delegate_task（本环境不支持），
    而是验证 task.md 的格式对 subagent 是可直接阅读的，
    以及 result.md 被正确读取。
    """
    global PASS, FAIL
    print("\n[test_integration_simulation]")

    b = run("init", "子树任务集成模拟")
    bid = b["batch_id"]

    tasks = json.dumps([{
        "id": "sub-agent-task",
        "goal": "分析项目结构并给出优化建议",
        "context": "项目目录: src/\n主要框架: React 19 + TypeScript 6",
        "criteria": ["至少3条建议", "每条建议带理由"],
    }])
    run("dispatch", bid, "--tasks", tasks)
    data = run("status", bid)
    tp = data["tasks"][0]["path"]

    # Verify task.md is subagent-readable
    task_md = pathlib.Path(tp, "task.md").read_text()
    assert "分析项目结构" in task_md
    assert "React 19" in task_md
    assert "至少3条建议" in task_md
    print("  ✅ task.md 对 subagent 可读 (goal + context + criteria present)")

    # Verify executor.md exists
    assert pathlib.Path(tp, "executor.md").exists()
    print("  ✅ executor.md 存在")

    # Simulate subagent: read task.md, write result.md
    run("update", tp, "running")
    pathlib.Path(tp, "result.md").write_text(
        "# 分析结果\n\n"
        "## 建议1: 使用React Compiler\n"
        "理由: 自动memo化减少re-render\n\n"
        "## 建议2: 统一类型导出\n"
        "理由: 避免循环依赖\n\n"
        "## 建议3: 添加Vitest配置\n"
        "理由: 测试覆盖率监控\n"
    )
    run("update", tp, "done")

    # Verify main agent can collect result
    data = run("collect", bid)
    result = data["results"][0]["result"]
    assert "建议1" in result and "建议2" in result and "建议3" in result
    print("  ✅ result.md 被 collect 正确读取 (3条建议)")

    import shutil
    shutil.rmtree(os.path.dirname(tp.rstrip("/").rsplit("/", 1)[0]), ignore_errors=True)
    print("  ✅ cleanup")


if __name__ == "__main__":
    os.chdir(ROOT)

    print("=" * 50)
    print("Race Tool 验证套件")
    print("=" * 50)

    test_help()
    test_init_dispatch()
    test_state_machine_boundaries()
    test_error_paths()
    test_race_mode_characteristic()
    test_integration_simulation()

    print()
    print("=" * 50)
    print(f"总计: PASS={PASS}  FAIL={FAIL}")
    if FAIL == 0:
        print("🎉 全部通过")
    else:
        print(f"❌ {FAIL} 个失败")
    print("=" * 50)

    sys.exit(0 if FAIL == 0 else 1)
