#!/usr/bin/env python3
"""
30次随机 bench 巡检 — 随机场景 + 随机 seed 参数化
用法: python3 randomized_bench.py [--iterations N]
"""
import random, subprocess, sys, json, os
from datetime import datetime

BASE_DIR = os.path.expanduser("~/Desktop/CarrorOS")
os.chdir(BASE_DIR)

SCENES = [
    "01_doc_update",
    "02_single_file_fix",
    "03_multi_file_test",
    "04_failure_then_repair",
    "05_compact_resume",
    "06_fallback_downgrade",
    "07_archive",
]

iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 30

results = []
pass_count = 0
fail_count = 0

print(f"═══ 30 次随机 bench 巡检 ═══")
print(f"场景: {', '.join(SCENES)}")
print(f"开始时间: {datetime.now().isoformat()}")
print("=" * 60)

for i in range(1, iterations + 1):
    scene = random.choice(SCENES)
    seed = random.randint(1, 2**31)

    print(f"\n[{i:2d}/{iterations}] 场景: {scene}  seed: {seed}")

    # run bench with seed
    cmd = f"python3 .omc/scripts/carros_base.py bench {scene} --seed {seed} 2>&1"
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = proc.stdout + proc.stderr
    exit_code = proc.returncode

    # sometimes bench returns 2 for lint fail — check output for PASS
    passed = "passed" in output.lower() and "0 failed" in output.lower() and exit_code == 0

    # 更严谨: 检查场景名 + PASS
    scene_pass = f"{scene}: PASS" in output
    all_pass = "7 passed" in output or scene_pass

    final_pass = all_pass and exit_code == 0

    if final_pass:
        status = "✅ PASS"
        pass_count += 1
    else:
        status = "❌ FAIL"
        fail_count += 1

    # 提取关键行做摘要
    # 找 bench results 块
    summary = ""
    for line in output.split("\n"):
        if any(k in line for k in ["PASS", "FAIL", "Error", "Traceback", "exit code"]):
            summary += line.strip() + " | "
        if "failed" in line.lower() and "0 failed" not in line.lower():
            summary += f"[FAIL] {line.strip()} | "

    print(f"  → {status}  exit={exit_code}")
    if not final_pass:
        # 打印前 20 行关键错误
        err_lines = [l for l in output.split("\n") if "Error" in l or "Traceback" in l or "FAIL" in l or "failed" in l]
        for e in err_lines[:5]:
            print(f"    {e.strip()}")
        # 最后 15 行
        tail = "\n".join(output.split("\n")[-15:])
        print(f"    tail:\n{tail}")

    results.append({
        "iteration": i,
        "scene": scene,
        "seed": seed,
        "exit_code": exit_code,
        "passed": final_pass,
        "status": status,
        "summary": summary[:200],
        "timestamp": datetime.now().isoformat(),
    })

    # 清理残留任务目录/归档
    subprocess.run(
        "rm -rf .omc/tasks/* .omc/archive/* .omc/tokens/* 2>/dev/null",
        shell=True, timeout=10,
    )

# report
print(f"\n{'='*60}")
print(f"═══ 30 次随机 bench 巡检结果 ═══")
print(f"{'='*60}")
print(f"  总次数: {iterations}")
print(f"  ✅ 通过: {pass_count}")
print(f"  ❌ 失败: {fail_count}")
print(f"  通过率: {100 * pass_count // iterations}%")

if fail_count > 0:
    print(f"\n  失败明细:")
    for r in results:
        if not r["passed"]:
            print(f"  [{r['iteration']:2d}] {r['scene']} seed={r['seed']} → {r['summary'][:120]}")

# save report
report = {
    "timestamp": datetime.now().isoformat(),
    "total": iterations,
    "pass": pass_count,
    "fail": fail_count,
    "rate": f"{100 * pass_count // iterations}%",
    "results": results,
}

report_path = os.path.join(BASE_DIR, ".omc", "scripts", "randomized_bench_report.json")
with open(report_path, "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n报告已保存: {report_path}")
print(f"═══ 巡检结束 ═══")

sys.exit(0 if fail_count == 0 else 1)
