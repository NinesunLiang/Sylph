"""CarrorOS Benchmark — 主入口

编排整个测试流程：加载任务 → 构建环境 → 运行 → 收集 → 报告。
"""

from __future__ import annotations
import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import (
    ExperimentRun, Budget, Routing, Context, Recovery, Verification,
    AblationGroup, Stack, FailureClass, TaskDefinition,
)
from ablation import iter_groups, get_config
from task_loader import load_all_tasks, validate_task, summary
from reporter import Reporter


BENCHMARK_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BENCHMARK_DIR / "reports"
RUNS_DIR = BENCHMARK_DIR / "runs"
ENVS_DIR = BENCHMARK_DIR / "envs"

# Phase 1: 20 tasks × 4 groups × 3 seeds = 240 runs
PHASE1_GROUPS = [
    AblationGroup.A_BARE,
    AblationGroup.B_ENTRY_PROMPT,
    AblationGroup.C_ROUTING_KERNEL,
    AblationGroup.E_FULL,
]
PHASE1_TASK_COUNT = 20

# Phase 2: 80 tasks × 6 groups × 3 seeds = 1440 runs
PHASE2_GROUPS = [
    AblationGroup.A_BARE,
    AblationGroup.B_ENTRY_PROMPT,
    AblationGroup.C_ROUTING_KERNEL,
    AblationGroup.D_WITHOUT_HARNESS,
    AblationGroup.E_FULL,
    AblationGroup.G_FULL_TEST_TIME_SCALING,
]
PHASE2_TASK_COUNT = 80


def _print_banner():
    print("""
╔══════════════════════════════════════════════╗
║        CarrorOS Benchmark Framework          ║
║  组件消融 A/B · 配对多 seed · 隐藏验收        ║
╚══════════════════════════════════════════════╝
""")


def _create_run_record(
    task: TaskDefinition,
    group: AblationGroup,
    seed: int,
) -> ExperimentRun:
    """Create an empty experiment run record."""
    from uuid import uuid4
    return ExperimentRun(
        run_id=str(uuid4())[:12],
        task_id=task.task_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        stack=Stack.CLAUDE_CODE,
        model="deepseek-v4-flash",
        provider="deepseek",
        group=group,
        seed=seed,
        repository_commit=task.repo_commit,
        budget=Budget(
            max_tool_calls=task.max_tool_calls,
        ),
        routing=Routing(
            expected_workflow="L1" if task.difficulty.value in ("easy", "medium") else "L2",
        ),
    )


def _save_run(run: ExperimentRun) -> Path:
    """Save an experiment run to disk."""
    run_dir = RUNS_DIR / run.task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{run.group.value}_s{run.seed}.json"
    path.write_text(
        json.dumps(run.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _pick_tasks_for_phase(phase: int) -> list[TaskDefinition]:
    """Pick task subset for a given phase."""
    all_tasks = load_all_tasks()
    if phase == 1:
        # Phase 1: 20 tasks, balanced by difficulty
        import random
        random.seed(20260715)
        by_diff: dict[str, list[TaskDefinition]] = {}
        for t in all_tasks:
            by_diff.setdefault(t.difficulty.value, []).append(t)
        selected = []
        for diff, count in [("easy", 6), ("medium", 8), ("hard", 4), ("adversarial", 2)]:
            pool = by_diff.get(diff, [])
            random.shuffle(pool)
            selected.extend(pool[:count])
        # Fill remaining from any difficulty
        if len(selected) < 20:
            remaining = [t for t in all_tasks if t not in selected]
            random.shuffle(remaining)
            selected.extend(remaining[:20 - len(selected)])
        return selected[:20]
    else:
        return all_tasks[:PHASE2_TASK_COUNT]


def cmd_validate(args):
    """Validate all task definitions."""
    tasks = load_all_tasks()
    print(summary(tasks))
    print()
    issues_found = 0
    for t in tasks:
        issues = validate_task(t)
        if issues:
            print(f"  ❌ {t.task_id}: {'; '.join(issues)}")
            issues_found += 1
    if issues_found == 0:
        print("✅ 所有任务验证通过")


def cmd_report(args):
    """Generate benchmark reports."""
    reporter = Reporter(RUNS_DIR)

    cap_report = reporter.generate_capability_report(
        REPORTS_DIR / "capability-amplification.md"
    )
    print(cap_report)

    long_report = reporter.generate_long_running_report(
        REPORTS_DIR / "long-running-stability.md"
    )
    print("\n" + "=" * 60)
    print(long_report)


def cmd_plan(args):
    """Print what will be run."""
    tasks = load_all_tasks()
    phase = args.phase or 1
    selected = _pick_tasks_for_phase(phase)
    groups = PHASE1_GROUPS if phase == 1 else PHASE2_GROUPS

    print(f"\n📋 Phase {phase} 运行计划")
    print(f"   任务: {len(selected)}")
    print(f"   消融组: {len(groups)} ({', '.join(g.value for g in groups)})")
    print(f"   预估运行: {len(selected) * len(groups) * 3} runs")
    print()

    for i, t in enumerate(selected, 1):
        print(f"  {i:2d}. [{t.difficulty.value:10s}] {t.task_id} — {t.title}")


def run_task(
    task: TaskDefinition,
    group: AblationGroup,
    seed: int,
    dry_run: bool = False,
) -> ExperimentRun:
    """Run a single task for one ablation group and seed."""
    run = _create_run_record(task, group, seed)

    if dry_run:
        print(f"    [DRY RUN] Would run: {task.task_id} / {group.value} / s{seed}")
        return run

    print(f"\n  ▶ Running {task.task_id} / {group.value} / s{seed}")
    print(f"    Budget: {task.max_tool_calls} tool calls, {task.max_wall_time_seconds}s")
    print(f"    Description: {task.description[:100]}...")

    # Build environment
    from environment import build_task_env
    try:
        env_path = build_task_env(
            task_id=task.task_id,
            task_repo_url=task.repo_url,
            task_commit=task.repo_commit,
            group=group,
            seed=seed,
        )
        print(f"    Environment: {env_path}")
    except Exception as e:
        print(f"    ❌ Environment build failed: {e}")
        run.failure_class = FailureClass.CRITICAL_ERROR
        run.failure_detail = str(e)
        _save_run(run)
        return run

    # TODO: Launch Claude Code / OpenCode session
    # This part requires external automation (CI/CD pipeline)
    run.verified_success = False
    run.failure_class = FailureClass.OTHER
    run.failure_detail = "CC session execution not yet automated in this version"
    _save_run(run)

    return run


def cmd_run(args):
    """Run benchmark experiments."""
    _print_banner()
    phase = args.phase or 1
    tasks = _pick_tasks_for_phase(phase)
    groups = PHASE1_GROUPS if phase == 1 else PHASE2_GROUPS

    # Randomize run order
    all_runs = []
    for task in tasks:
        for group in groups:
            for seed in task.seeds[:3]:
                all_runs.append((task, group, seed))
    random.shuffle(all_runs)

    total = len(all_runs)
    print(f"📋 Phase {phase}: {total} runs ({len(tasks)} tasks × {len(groups)} groups × 3 seeds)")
    print()

    completed = 0
    for task, group, seed in all_runs:
        run_task(task, group, seed, dry_run=args.dry_run)
        completed += 1
        print(f"  Progress: {completed}/{total}")

    # Generate reports
    if not args.dry_run:
        print("\n" + "=" * 60)
        print("📊 Generating reports...")
        reporter = Reporter(RUNS_DIR)
        cap = reporter.generate_capability_report(REPORTS_DIR / "capability-amplification.md")
        long_r = reporter.generate_long_running_report(REPORTS_DIR / "long-running-stability.md")
        print("✅ Reports generated:")
        print(f"   {REPORTS_DIR / 'capability-amplification.md'}")
        print(f"   {REPORTS_DIR / 'long-running-stability.md'}")


def cmd_gen_tasks(args):
    """Generate task template YAML files."""
    import json
    output_dir = BENCHMARK_DIR / "tasks"
    categories = [
        ("01_repo_locate", "仓库定位与小修复", 10),
        ("02_multi_file", "多文件重构", 10),
        ("03_cross_module", "跨模块 Bug", 10),
        ("04_migration", "依赖升级/迁移", 8),
        ("05_fuzzy_req", "模糊需求实现", 8),
        ("06_test_fix", "测试修复", 8),
        ("07_perf_concur", "性能或并发问题", 8),
        ("08_long_recovery", "长期恢复任务", 8),
        ("09_high_risk", "高风险任务", 5),
        ("10_adversarial", "对抗性任务", 5),
    ]

    import random
    random.seed(20260715)
    difficulties = ["easy", "medium", "hard", "adversarial"]

    total = 0
    for cat_id, cat_label, count in categories:
        cat_dir = output_dir / cat_id
        cat_dir.mkdir(parents=True, exist_ok=True)

        for i in range(1, count + 1):
            task_id = f"{cat_id}_{i:03d}"
            diff = random.choice(difficulties)

            template = f"""# CarrorOS Benchmark Task: {task_id}
# Category: {cat_id} ({cat_label})
# Difficulty: {diff}
# Auto-generated template — replace with real task

task_id: "{task_id}"
category: "{cat_id}"
difficulty: "{diff}"
title: "TODO: Task title for {task_id}"
description: |
  TODO: Task description (must not leak solution)
  
  Context:
  - What the repo does
  - What needs to change
  - Constraints and requirements
  
  Deliverable:
  - What success looks like

repo_url: "https://github.com/NinesunLiang/Sylph.git"
repo_commit: "0000000000000000000000000000000000000000"  # TODO: set fixed commit
verify_script: ".benchmark/verify/{task_id}/verify.sh"   # TODO: create verification

allowed_files:
  - "**/*.py"    # TODO: restrict to relevant files
forbidden_files:
  - ".env"
  - "**/secret*"

build_command: "python3 -m py_compile src/main.py"      # TODO: set build command
lint_command: "python3 -m flake8 src/ --max-line-length=100"  # TODO: set lint
test_command: "python3 -m pytest tests/ -x -q"          # TODO: set test

max_tool_calls: 30
max_wall_time_seconds: 600
seeds: [20260701, 20260702, 20260703]
"""
            task_path = cat_dir / f"{task_id}.yaml"
            if not task_path.exists():
                task_path.write_text(template)
                total += 1

    print(f"✅ 已生成 {total} 个任务模板")


def main():
    parser = argparse.ArgumentParser(
        description="CarrorOS Benchmark Framework"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Validate task definitions")
    sub.add_parser("report", help="Generate reports from existing runs")
    sub.add_parser("plan", help="Show run plan").add_argument(
        "--phase", type=int, choices=[1, 2], default=1
    )
    run_p = sub.add_parser("run", help="Run benchmark experiments")
    run_p.add_argument("--phase", type=int, choices=[1, 2], default=1)
    run_p.add_argument("--dry-run", action="store_true", help="Print plan without running")
    run_p.add_argument("--model", default="deepseek-v4-flash")
    sub.add_parser("gen-tasks", help="Generate task templates")

    args = parser.parse_args()

    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "plan":
        cmd_plan(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "gen-tasks":
        cmd_gen_tasks(args)


if __name__ == "__main__":
    main()
