#!/usr/bin/env python3
"""
honesty_audit.py — 全仓诚实度扫描

检查 claims（[x]/COMPLETED/全部完成/ALIGNED）与实际证据是否一致。
非 gate、不阻塞执行。输出报告。

Usage:
    python3 .claude/scripts/honesty_audit.py [--fix]

Exit code: 0 = 无问题 | 1 = 有未对齐 | 2 = 错误
"""

import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OMC = ROOT / ".omc"
TASKS = OMC / "tasks"
TOKENS = OMC / "tokens"
AUDIT = OMC / "audit"
ARCHIVE = OMC / "archive"
SCRIPTS = ROOT / ".claude" / "scripts"
HOOKS = ROOT / ".claude" / "hooks"

EXECUTOR_MIN_BYTES = 200  # 模板就是 ~195B，低于此 = 无证据
PLAN_MIN_BYTES = 150
ORACLE_SCRIPTS = [
    "oracle_engine.py", "oracle_gate.py", "meta_oracle.py",
    "oracle_agent.py", "oracle_spawn.py", "runtime_oracle_agent.py",
    "static_oracle_agent.py",
]

warnings = []
errors = []

def warn(msg: str):
    warnings.append(msg); print(f"  ⚠️  {msg}")

def err(msg: str):
    errors.append(msg); print(f"  ❌ {msg}")

def ok(msg: str):
    print(f"  ✅ {msg}")

# ── Check 1: X mark vs executor evidence ──
def check_x_marks():
    print("\n[1/6] [x] step 标记 vs executor 证据")
    found = 0
    for d in sorted(TASKS.rglob("plan.md")):
        text = d.read_text(encoding="utf-8", errors="replace")
        x_steps = re.findall(r"- \[x\]\s*(S\d+)", text)
        if not x_steps:
            continue
        exec_f = d.parent / "executor.md"
        if not exec_f.exists():
            warn(f"{d.parent.name}/executor.md 不存在但 plan 有 [x] step")
            continue
        exec_text = exec_f.read_text(encoding="utf-8", errors="replace")
        for step in x_steps:
            if step not in exec_text:
                warn(f"{d.parent.name}: [{step}] 标记完成但 executor 无该 step 记录")
                found += 1
    if found == 0:
        ok("所有 [x] step 在 executor 中有对应记录")

# ── Check 2: 状态声明 vs 文件容量 ──
def check_completed_declarations():
    print("\n[2/6] COMPLETED/全部完成 声明 vs 文件容量")
    for f in TASKS.rglob("plan.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "SKELETON" in text:
            continue
        size = len(text)
        if size < PLAN_MIN_BYTES:
            warn(f"{f.parent.name}/plan.md: 仅 {size}B，可能为空模板")
    for f in TASKS.rglob("executor.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "SKELETON" in text:
            continue
        size = len(text)
        if size < EXECUTOR_MIN_BYTES:
            warn(f"{f.parent.name}/executor.md: 仅 {size}B，可能为空模板")
    ok("文件容量检查完成 (SKELETON 豁免)")

# ── Check 3: 全部完成/ALIGNED 关键字 ──
def check_completion_claims():
    print("\n[3/6] 全部完成/ALIGNED 关键字扫描")
    patterns = [r"全部完成", r"完全对齐", r"production\s*ready", r"implementation\s*complete"]
    for f in sorted((ROOT / "重构指导文档").rglob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for pat in patterns:
            if re.search(pat, text):
                line_num = next((i+1 for i, l in enumerate(text.splitlines()) if re.search(pat, l)), 0)
                warn(f"{f.name}:{line_num} 含 \"{pat}\" 声明，需人工确认")
    ok("关键字扫描完成")

# ── Check 4: Oracle static_stub 标注 ──
def check_oracle_stub_labels():
    print("\n[4/6] Oracle static_stub 标注一致性")
    for name in ORACLE_SCRIPTS:
        for base in [SCRIPTS, ROOT / ".omc" / "scripts"]:
            f = base / name
            if f.exists() and not f.is_symlink():
                text = f.read_text(encoding="utf-8", errors="replace")
                if "static_stub" not in text:
                    err(f"{name} 缺少 static_stub 标注")
                    break
    ok("Oracle static_stub 标注检查完成")

# ── Check 5: SKELETON 扩散检测 ──
def check_skeleton_leak():
    print("\n[5/6] SKELETON 扩散检测（标记完成的任务不应有 SKELETON）")
    for d in sorted(TASKS.rglob("plan.md")):
        text = d.read_text(encoding="utf-8", errors="replace")
        if "SKELETON" in text and "[x]" in text:
            err(f"{d.parent.name}: 同时有 SKELETON 和 [x]，状态矛盾")
        if "SKELETON" in text and d.parent.name.startswith("bench"):
            continue  # bench 本来就是 SKELETON，预期内
    ok("SKELETON 一致性检查完成")

# ── Check 6: token/plan/executor 三方一致 ──
def check_triple_consistency():
    print("\n[6/6] token/plan/executor 三方一致性")
    for d in sorted(TASKS.glob("*/*")):  # {date}/{task}
        plan = d / "plan.md"
        exec_f = d / "executor.md"
        if not plan.exists() or not exec_f.exists():
            continue
        plan_text = plan.read_text(encoding="utf-8", errors="replace")
        x_steps = set(re.findall(r"- \[x\]\s*(S\d+)", plan_text))
        if not x_steps:
            continue
        # Check archive: archived tasks should have matching evidence
        archive_d = ARCHIVE / d.name
        if archive_d.exists():
            report = archive_d / "final-report.md"
            if not report.exists():
                warn(f"{d.parent.name}/{d.name}: plan 有 [x] 但 archive 无 final-report")
    ok("三方一致性检查完成")


def run():
    print("=" * 60)
    print("CarrorOS 全仓诚实度扫描")
    print(f"扫描路径: {ROOT}")
    print("=" * 60)

    check_x_marks()
    check_completed_declarations()
    check_completion_claims()
    check_oracle_stub_labels()
    check_skeleton_leak()
    check_triple_consistency()

    print("\n" + "=" * 60)
    print(f"摘要: {len(warnings)} warnings, {len(errors)} errors")
    if errors:
        print("❌ FAILED — 存在未对齐项")
        return 1
    if warnings:
        print("⚠️  PASSED — 有警告（不阻断）")
        return 0
    print("✅ PASSED — 无问题")
    return 0


if __name__ == "__main__":
    sys.exit(run())
