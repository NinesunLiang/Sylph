#!/usr/bin/env python3
"""
CarrorOS A/B 对比测试 — 当前项目(有治理) vs 空项目(无治理)
同一个模型 DeepSeek 做同样的任务，对比耗时和完成质量。
"""

import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
EMPTY_DIR = Path("/tmp/carror-empty-project")

# 任务：创建一个 Python 文件并验证
PROMPT = """Create a Python file src/multiply.py with:
- multiply(a, b) function that returns a * b
- multiply_list(items) that multiplies all items together

Then create tests/test_multiply.py with:
- test_multiply_basic()
- test_multiply_list()
- test_multiply_zero()
- test_multiply_negative()

Run 'python3 -m pytest tests/ -x -q' to verify all tests pass.
Print the pytest output as evidence."""

def run_test(label, workdir):
    """在指定目录跑一次 CC -p 任务"""
    print(f"\n── {label} ──")
    print(f"  目录: {workdir}")
    print(f"  有 AGENTS.md: {(workdir/'AGENTS.md').exists()}")
    print(f"  有 .claude: {(workdir/'.claude').exists()}")

    # Step 1: 读结构
    start = time.time()
    r1 = subprocess.run(
        ["claude", "-p", "list all Python files in this project", "--output-format", "json"],
        cwd=str(workdir), capture_output=True, text=True, timeout=60,
    )
    read_s = round(time.time() - start, 1)
    read_ok = r1.returncode == 0

    # Step 2: 执行任务
    start = time.time()
    r2 = subprocess.run(
        ["claude", "-p", PROMPT, "--output-format", "json"],
        cwd=str(workdir), capture_output=True, text=True, timeout=120,
    )
    exec_s = round(time.time() - start, 1)
    exec_ok = r2.returncode == 0

    # Step 3: pytest 验证
    start = time.time()
    r3 = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-x", "-q"],
        cwd=str(workdir), capture_output=True, text=True, timeout=30,
    )
    verify_s = round(time.time() - start, 1)
    verify_pass = r3.returncode == 0
    verify_out = r3.stdout.strip()[:200] if r3.stdout else r3.stderr.strip()[:200]

    total = read_s + exec_s + verify_s

    return {
        "label": label,
        "read_s": read_s,
        "exec_s": exec_s,
        "verify_s": verify_s,
        "total_s": total,
        "read_ok": read_ok,
        "exec_ok": exec_ok,
        "verify_pass": verify_pass,
        "verify_output": verify_out,
    }

def main():
    print("="*70)
    print("🧪 CarrorOS A/B 对比测试 — 有治理 vs 无治理")
    print(f"模型: DeepSeek-v4-flash")
    print(f"任务: 创建 multiply.py + test_multiply.py，pytest 验证")
    print("="*70)

    # 空项目准备（已创建）
    if not (EMPTY_DIR / "src").exists():
        print(f"\n❌ 空项目不存在: {EMPTY_DIR}")
        print("请先运行空项目准备命令")
        return

    # 确认环境差异
    print(f"\n环境确认:")
    for name, path in [("CarrorOS(有治理)", ROOT), ("空项目(无治理)", EMPTY_DIR)]:
        agents = (path/"AGENTS.md").exists()
        claude = (path/".claude").exists()
        omc = (path/".omc").exists()
        print(f"  {name:25s}: AGENTS.md={'✅' if agents else '❌'} .claude={'✅' if claude else '❌'} .omc={'✅' if omc else '❌'}")

    # 跑两组测试
    results = []
    for label, workdir in [("CarrorOS(有治理)", ROOT), ("空项目(无治理)", EMPTY_DIR)]:
        r = run_test(label, workdir)
        results.append(r)

    # 输出对比
    print(f"\n{'='*70}")
    print("📊 对比结果")
    print(f"{'='*70}")

    a = results[0]  # CarrorOS
    b = results[1]  # 空项目

    metrics = [
        ("读项目耗时", f"{a['read_s']}s", f"{b['read_s']}s",
         f"{'快' if a['read_s'] < b['read_s'] else '慢'}{abs(a['read_s']-b['read_s']):.0f}s"),
        ("执行任务耗时", f"{a['exec_s']}s", f"{b['exec_s']}s",
         f"{'快' if a['exec_s'] < b['exec_s'] else '慢'}{abs(a['exec_s']-b['exec_s']):.0f}s"),
        ("验证耗时", f"{a['verify_s']}s", f"{b['verify_s']}s",
         f"{'快' if a['verify_s'] < b['verify_s'] else '慢'}{abs(a['verify_s']-b['verify_s']):.0f}s"),
        ("总耗时", f"{a['total_s']}s", f"{b['total_s']}s",
         f"{'快' if a['total_s'] < b['total_s'] else '慢'}{abs(a['total_s']-b['total_s']):.0f}s"),
        ("读项目成功", "✅" if a['read_ok'] else "❌", "✅" if b['read_ok'] else "❌", ""),
        ("执行成功", "✅" if a['exec_ok'] else "❌", "✅" if b['exec_ok'] else "❌", ""),
        ("测试通过", "✅" if a['verify_pass'] else "❌", "✅" if b['verify_pass'] else "❌",
         f"{a['verify_output'][:30]}" if not a['verify_pass'] or not b['verify_pass'] else ""),
    ]

    print(f"{'指标':20s} {'CarrorOS(有治理)':>20s} {'空项目(无治理)':>20s} {'差异':>15s}")
    print(f"{'-'*20} {'-'*20} {'-'*20} {'-'*15}")
    for name, va, vb, diff in metrics:
        print(f"{name:20s} {va:>20s} {vb:>20s} {diff:>15s}")

    # 如果验证输出有差别，额外打印
    if a['verify_output'] != b['verify_output']:
        print(f"\n  验证输出:")
        print(f"    CarrorOS: {a['verify_output']}")
        print(f"    空项目:   {b['verify_output']}")

    print(f"\n{'='*70}")
    if a['verify_pass'] and b['verify_pass']:
        print("结论: 两个环境都完成任务并通过测试。重点看耗时差异。")
    elif a['verify_pass'] and not b['verify_pass']:
        print("结论: 有治理的环境完成了任务，空项目失败了（治理有正向效果）")
    elif not a['verify_pass'] and b['verify_pass']:
        print("结论: 空项目反而通过了（异常情况，需要分析）")
    else:
        print("结论: 两个环境都失败（可能是任务本身的问题）")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
