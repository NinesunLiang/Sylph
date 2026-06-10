#!/usr/bin/env python3
"""
race_swarm.py — Race 蜂群并行引擎 v2

角色: register → collect → report
dispatch 由 main agent 自行用 delegate_task(tasks=[...]) 派发。

为什么这样设计:
  - race_swarm.py 进程内无法调用 delegate_task (hermes_tools 仅 execute_code 可用)
  - delegate_task 是 Hermes 平台内置工具，只有 main agent 能调
  - race_swarm.py 做它擅长的: 状态管理 + 文件 I/O + 聚合

用法 Step 1: register + 生成 dispatch payload
  python3 .claude/scripts/race_swarm.py register <parent_id> \\
    --tasks 'N' \\
    [--max-concurrent 3] \\
    [--json]

  输出: JSON 含 subtask_ids 数组 + 每个任务的完成契约 path

用法 Step 2: main agent 根据输出调 delegate_task(tasks=[...])

用法 Step 3: collect + report
  python3 .claude/scripts/race_swarm.py report <parent_id> [--json]

防混款: 每个 subagent 写自己的 result.json (目录隔离)
  完成契约 path: .omc/race/<parent_id>/subtasks/<subtask_id>/result.json
  格式: {"status": "completed", "output": "..."}
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
RACE_DIR = PROJECT_ROOT / ".omc" / "race"
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
RACE_MANAGER = str(SCRIPT_DIR / "race_manager.sh")
SUBAGENT_STATE = STATE_DIR / "subagent-state.md"


# ── Utils ──────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_id(s: str) -> str:
    import re
    return re.sub(r'[^a-zA-Z0-9_\-/]', '', s)


def _run_manager(*args: str) -> tuple[str, int]:
    try:
        r = subprocess.run(
            [RACE_MANAGER] + list(args),
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", 1


def _write_state_entry(parent_id: str, total: int, completed: int,
                       batches: int, duration_s: float):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(SUBAGENT_STATE), "a", encoding="utf-8") as f:
            ts = int(time.time())
            f.write(f"\n## {ts} | race-swarm | {parent_id}\n")
            f.write(f"- 子任务数: {total}\n")
            f.write(f"- 分批: {batches} 批\n")
            f.write(f"- 成功: {completed}/{total}\n")
            f.write(f"- 总耗时: {duration_s:.1f}s\n")
    except OSError:
        pass


# ── Commands ───────────────────────────────────────────────────────────

def cmd_register(parent_id: str, n_tasks: int,
                 max_concurrent: int, json_output: bool) -> dict:
    """Register a parent race with N sub-task slots. Returns dispatch info."""
    parent_id = _sanitize_id(parent_id)
    safe_id = _sanitize_id(parent_id)
    if not safe_id:
        return {"status": "failed", "error": "invalid parent_id"}

    # Generate subtask IDs: sub_001, sub_002, ...
    subtask_ids = [f"sub_{i:03d}" for i in range(1, n_tasks + 1)]
    subtasks_csv = ",".join(subtask_ids)

    out, rc = _run_manager(
        "register", safe_id,
        "--subtasks", subtasks_csv,
        "--desc", f"RaceSwarm: {n_tasks} 个并行子任务"
    )

    # race_manager.sh may exit 1 even on success (shell bug)
    if "RACE_REGISTER" not in out and "RACE_REGISTERED" not in out:
        return {"status": "failed", "error": f"register failed: {out} (rc={rc})"}

    batches = (n_tasks + max_concurrent - 1) // max_concurrent

    result = {
        "status": "registered",
        "parent_id": safe_id,
        "total": n_tasks,
        "batches": batches,
        "max_concurrent": max_concurrent,
        "subtask_ids": subtask_ids,
        "contract": {
            "result_json_path": f".omc/race/{safe_id}/subtasks/<subtask_id>/result.json",
            "format": '{"status": "completed|failed", "output": "..."}'
        },
        "race_dir": str(RACE_DIR / safe_id),
        "register_cmd": f"bash {RACE_MANAGER} register {safe_id} --subtasks {subtasks_csv}",
    }

    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Race {safe_id} 注册成功: {n_tasks} 个子任务, "
              f"分 {batches} 批 (并发 {max_concurrent})")
        print(f"   目录: {result['race_dir']}")
        print(f"   子任务: {', '.join(subtask_ids)}")
        print(f"")
        print(f"   现在用 delegate_task 派发子任务。每个 subagent 完成后写:")
        print(f"     .omc/race/{safe_id}/subtasks/<subtask_id>/result.json")
        print(f"     格式: {{\"status\": \"completed\", \"output\": \"...\"}}")
        print(f"")
        print(f"   派发完后运行:")
        print(f"     python3 .claude/scripts/race_swarm.py report {safe_id}")

    return result


def cmd_report(parent_id: str, json_output: bool):
    """Collect all subtask results and produce aggregated report.
    Also writes to subagent-state.md for cross-session visibility.
    """
    parent_id = _sanitize_id(parent_id)
    race_dir = RACE_DIR / parent_id
    subtasks_dir = race_dir / "subtasks"
    manifest = race_dir / "manifest.json"

    if not manifest.exists():
        msg = f"Race '{parent_id}' 未注册或 manifest.json 不存在"
        if json_output:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"❌ {msg}")
        return

    start = time.time()

    # Read manifest
    with open(str(manifest), "r") as f:
        mf = json.load(f)

    total = mf.get("total_subtasks", 0)
    subtask_ids = mf.get("subtask_ids", [])

    subtask_results = []
    completed = 0
    failed = 0

    # Also check HOME-based paths (subagents may write there if CWD is ~)
    home_race = Path.home() / ".omc" / "race" / parent_id / "subtasks"

    for sid in subtask_ids:
        # Check project path first, then HOME path
        result_file = subtasks_dir / sid / "result.json"
        if not result_file.exists():
            alt = home_race / sid / "result.json"
            if alt.exists():
                result_file = alt

        entry = {"subtask_id": sid, "status": "registered", "output": None}
        if result_file.exists():
            try:
                with open(str(result_file), "r") as f:
                    data = json.load(f)
                st = data.get("status", "unknown")
                entry["status"] = st
                entry["output"] = data.get("output", "")
                if st == "completed":
                    completed += 1
                elif st == "failed":
                    failed += 1
            except (json.JSONDecodeError, OSError):
                entry["status"] = "parse_error"
        subtask_results.append(entry)

    duration = time.time() - start

    # Also fetch running/not-started counts
    running = 0
    pending = 0
    for r in subtask_results:
        if r["status"] == "running":
            running += 1
        elif r["status"] == "registered":
            pending += 1

    report = {
        "status": "completed" if failed == 0 and running == 0 else "partial",
        "parent_id": parent_id,
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "pending": pending,
        "duration_s": round(duration, 2),
        "subtasks": subtask_results,
        "race_dir": str(race_dir),
    }

    # Write to subagent-state.md
    batches = report.get("batches", 1)
    _write_state_entry(parent_id, total, completed, batches, duration)
    report["state_file"] = str(SUBAGENT_STATE)

    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status_icon = "✅" if report["status"] == "completed" else "⚠️"
        print(f"\n{status_icon} Race 报告: {parent_id}")
        print("=" * 45)
        print(f"  状态:    {report['status']}")
        print(f"  总计:    {total}")
        print(f"  成功:    {completed}")
        print(f"  失败:    {failed}")
        print(f"  运行中:  {running}")
        print(f"  待处理:  {pending}")
        print(f"  耗时:    {duration:.1f}s")
        print(f"  目录:    {race_dir}")
        print(f"")

        if subtask_results:
            for r in subtask_results:
                icon = {"completed": "✅", "failed": "❌",
                        "running": "🔄", "registered": "○",
                        "parse_error": "⚠️"}.get(r["status"], "?")
                out = (r.get("output") or "")[:80]
                print(f"    {icon} {r['subtask_id']} [{r['status']}]")
                if out:
                    print(f"       → {out}")

    return report


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Race Swarm — 并行 subagent 状态管理"
    )
    parser.add_argument("command", choices=["register", "report"],
                        help="register: 创建 race + 生成 dispatch 信息;\n"
                             "report: 收集 + 聚合结果")
    parser.add_argument("parent_id", help="Race parent ID")
    parser.add_argument("--tasks", type=int, default=0,
                        help="子任务数（仅 register 需要）")
    parser.add_argument("--max-concurrent", type=int, default=3,
                        help="每批并发数（默认 3, 配置文件可调 10）")
    parser.add_argument("--json", action="store_true",
                        help="JSON 输出")

    args = parser.parse_args()

    if args.command == "register":
        if args.tasks <= 0:
            print("❌ --tasks N 是必填的（子任务数）")
            sys.exit(1)
        cmd_register(args.parent_id, args.tasks,
                     args.max_concurrent, args.json)
    elif args.command == "report":
        cmd_report(args.parent_id, args.json)

    sys.exit(0)


if __name__ == "__main__":
    main()
