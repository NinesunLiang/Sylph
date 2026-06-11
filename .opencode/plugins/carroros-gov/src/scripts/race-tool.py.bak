#!/usr/bin/env python3
# race-tool.py — Document-driven race swarm engine
# 用法: race-tool.py init|dispatch|status|collect|report [参数]
# 哲学 #7(文档优先) + #4(验收) + #2(最小改动)
# Python 3.10 strict (no str|None, no match/case)

"""
Race Swarm 文档驱动引擎。

三域边界:
  race    — N 并行同构子任务，每个 = 1 个 task.md
  stepwise — 串行依赖分析，完整文档系统 (RPE-like)
  RPE     — 深度单线正式评审

工作目录: .omc/plan/{date}/{taskid}_{time}/
  子任务目录:
    task.md       — main agent 写的任务描述 (goal, context, criteria)
    executor.md   — subagent 执行步骤 + 状态
    result.md     — subagent 产出物
    task-state.md — state machine 状态文件

  task-state.md state machine:
    pending  → running → done
                      → failed → retry(≤3) → running
                                    → blocked(>3)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 常量 ───

# 从脚本路径 .py → scripts/ → carroros-gov/src/ → packages/ → Carror_OS/
# 实际：.../packages/carroros-gov/src/scripts/race-tool.py
# 需要升4级回到仓库根
_script_path = Path(__file__).resolve()
_script_parents = list(_script_path.parents)
# _script_parents[0] = scripts/, [1] = src/, [2] = carroros-gov/, [3] = packages/, [4] = Carror_OS/
PROJECT_ROOT = _script_parents[4] if len(_script_parents) > 4 else _script_parents[0]
PLAN_BASE = PROJECT_ROOT / ".omc" / "plan"
DATE_FMT = "%Y%m%d"
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"
MAX_RETRY = 3
POLL_INTERVAL = 2  # seconds

# ─── 工具函数 ───

def _now() -> str:
    """返回 CST 时间戳字符串"""
    # 用 UTC+8 模拟 CST
    now = datetime.now(timezone.utc)
    # Python 3.10: no tz offset formatting
    return now.strftime(DATE_FMT)


def _ts() -> str:
    """返回带时间的时间戳"""
    # Use local time for timestamps
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _taskid() -> str:
    """生成 task ID: {TIMESTAMP}"""
    return datetime.now().strftime(TIMESTAMP_FMT)


def _plan_date_dir(date_str: str = "") -> Path:
    """获取 .omc/plan/{date}/ 目录"""
    if not date_str:
        date_str = _now()
    d = PLAN_BASE / date_str
    d.mkdir(parents=True, exist_ok=True)
    return d


def _task_dir(task_id: str, date_str: str = "") -> Path:
    """创建并返回子任务目录 .omc/plan/{date}/{task_id}/"""
    parent = _plan_date_dir(date_str)
    td = parent / task_id
    td.mkdir(parents=True, exist_ok=True)
    return td


def _read_file(path: Path) -> str:
    """安全读文件，不存在返回空字符串"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _write_file(path: Path, content: str) -> None:
    """安全写文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _state_path(task_dir: Path) -> Path:
    return task_dir / "task-state.md"


def _task_path(task_dir: Path) -> Path:
    return task_dir / "task.md"


def _executor_path(task_dir: Path) -> Path:
    return task_dir / "executor.md"


def _result_path(task_dir: Path) -> Path:
    return task_dir / "result.md"


# ─── 状态机 ───

def _read_state(task_dir: Path) -> str:
    """读取 task-state.md 中的状态行"""
    content = _read_file(_state_path(task_dir))
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("state:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _write_state(task_dir: Path, state: str, task_id: str, message: str = "") -> None:
    """写入 task-state.md 状态文件"""
    content = [
        "# Task State\n",
        f"task_id: {task_id}",
        f"state: {state}",
        f"updated: {_ts()}",
    ]
    if message:
        content.append(f"message: {message}")
    content.append("")
    content.append("## State Machine")
    content.append("pending  -> running -> done")
    content.append("                   -> failed -> retry(<=3) -> running")
    content.append("                                    -> blocked(>3)")
    _write_file(_state_path(task_dir), "\n".join(content))


def _validate_state_transition(current: str, target: str) -> tuple:
    """
    验证状态转换是否合法。
    返回 (is_valid: bool, error_msg: str)
    """
    transitions = {
        "pending":  ["running"],
        "running":  ["done", "failed"],
        "failed":   ["retry", "blocked"],
        "retry":    ["running", "blocked"],
        "done":     [],
        "blocked":  [],
    }
    allowed = transitions.get(current, [])
    if target not in allowed:
        return (False, f"非法状态转换: {current} -> {target} (允许: {', '.join(allowed) if allowed else '无'})")
    return (True, "")


def _update_state(task_dir: Path, target: str, task_id: str, message: str = "") -> tuple:
    """
    更新状态，验证合法性。
    返回 (success: bool, msg: str)
    """
    current = _read_state(task_dir)
    valid, err = _validate_state_transition(current, target)
    if not valid:
        return (False, err)
    _write_state(task_dir, target, task_id, message)
    return (True, f"状态更新: {current} -> {target}")


# ─── 核心操作 ───

def cmd_init(args: list) -> None:
    """
    race-tool.py init <title> [--parallel N] [--desc "<description>"]
    创建 race 批次，返回批次 ID。
    """
    if not args:
        print("用法: race-tool.py init <title> [--parallel N] [--desc \"<description>\"]", file=sys.stderr)
        sys.exit(1)

    title = args[0]
    parallel = 5  # default
    description = ""

    i = 1
    while i < len(args):
        if args[i] == "--parallel" and i + 1 < len(args):
            parallel = int(args[i + 1])
            i += 2
        elif args[i] == "--desc" and i + 1 < len(args):
            description = args[i + 1]
            i += 2
        else:
            i += 1

    batch_id = _taskid()
    date_str = _now()
    batch_dir = _task_dir(batch_id, date_str)

    # Write manifest.md
    manifest = [
        f"# Race Batch: {title}",
        f"",
        f"> batch_id: {batch_id}",
        f"> date: {date_str}",
        f"> created: {_ts()}",
        f"> parallel: {parallel}",
        f"> status: initialized",
        f"",
    ]
    if description:
        manifest.append(f"> description: {description}")
        manifest.append("")
    manifest.append("## Sub-tasks")
    manifest.append("")
    manifest.append("(pending)")
    manifest.append("")

    _write_file(batch_dir / "manifest.md", "\n".join(manifest))

    output = {
        "batch_id": batch_id,
        "date": date_str,
        "path": str(batch_dir),
        "parallel": parallel,
        "title": title,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_dispatch(args: list) -> None:
    """
    race-tool.py dispatch <batch_id> --tasks <json_array>
    向批次中添加子任务。
    每个任务: {"id": "task-1", "goal": "...", "context": "...", "criteria": ["...",]}
    """
    if len(args) < 3 or args[1] != "--tasks":
        print("用法: race-tool.py dispatch <batch_id> --tasks <json_array>", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    tasks_input = " ".join(args[2:])
    try:
        tasks = json.loads(tasks_input)
    except (IndexError, json.JSONDecodeError):
        print("❌ --tasks 需要有效的 JSON 数组", file=sys.stderr)
        sys.exit(1)

    if not isinstance(tasks, list):
        print("❌ tasks 必须是 JSON 数组", file=sys.stderr)
        sys.exit(1)

    # Find batch directory
    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    created = []
    for task in tasks:
        t_id = task.get("id", _taskid())
        t_dir = batch_dir / t_id
        t_dir.mkdir(parents=True, exist_ok=True)

        # Write task.md
        task_md = [
            f"# {t_id}",
            "",
            f"## Goal",
            f"{task.get('goal', '(未指定)')}",
            "",
            f"## Context",
            f"{task.get('context', '(未指定)')}",
            "",
            "## Completion Criteria",
        ]
        for c in task.get("criteria", []):
            task_md.append(f"- [ ] {c}")
        task_md.append("")
        _write_file(task_path(t_dir), "\n".join(task_md))

        # Write executor.md (placeholder for subagent)
        executor_md = [
            f"# Executor — {t_id}",
            "",
            f"> batch: {batch_id}",
            f"> created: {_ts()}",
            f"> state: pending",
            "",
            "## Steps",
            "",
            "- [ ] Step 1: 分析任务",
            "- [ ] Step 2: 执行",
            "- [ ] Step 3: 验证",
            "- [ ] Step 4: 写入 result.md",
            "- [ ] Step 5: 更新 task-state.md -> done",
            "",
        ]
        _write_file(executor_path(t_dir), "\n".join(executor_md))

        # Write task-state.md
        task_state = [
            "# Task State",
            f"task_id: {t_id}",
            "state: pending",
            f"updated: {_ts()}",
            "",
            "## State Machine",
            "pending  -> running -> done",
            "                   -> failed -> retry(<=3) -> running",
            "                                    -> blocked(>3)",
        ]
        _write_file(state_path(t_dir), "\n".join(task_state))

        created.append({
            "id": t_id,
            "path": str(t_dir),
            "state": "pending",
        })

    # Update manifest
    manifest_path = batch_dir / "manifest.md"
    manifest_content = []
    if manifest_path.exists():
        manifest_content = manifest_path.read_text(encoding="utf-8").splitlines()
    # Add task list to manifest
    task_lines = []
    for t in created:
        task_lines.append(f"- [{t['id']}]({t['id']}/) — pending")
    manifest_lines = []
    added = False
    for line in manifest_content:
        if line.strip() == "(pending)" and not added:
            manifest_lines.extend(task_lines)
            added = True
        else:
            manifest_lines.append(line)
    if not added:
        manifest_lines.extend(task_lines)
    manifest_lines.append("")
    _write_file(manifest_path, "\n".join(manifest_lines))

    output = {
        "batch_id": batch_id,
        "created": len(created),
        "tasks": created,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def task_path(task_dir: Path) -> Path:
    return task_dir / "task.md"


def executor_path(task_dir: Path) -> Path:
    return task_dir / "executor.md"


def result_path(task_dir: Path) -> Path:
    return task_dir / "result.md"


def state_path(task_dir: Path) -> Path:
    return task_dir / "task-state.md"


def _find_batch(batch_id: str, date_str: str = "") -> Path:
    """查找 batch 目录。可以部分匹配 batch_id。"""
    if not date_str:
        date_str = _now()
    # Try exact match first
    exact = _plan_date_dir(date_str) / batch_id
    if exact.exists():
        return exact
    # Try partial match in all date dirs
    if PLAN_BASE.exists():
        for d in sorted(PLAN_BASE.iterdir()):
            if d.is_dir():
                    # Skip non-date dirs
                if len(d.name) != 8 or not d.name.isdigit():
                    continue
                for bd in d.iterdir():
                    if bd.is_dir() and bd.name.startswith(batch_id):
                        return bd
    print(f"❌ 未找到 batch: {batch_id} (在 .omc/plan/ 中搜索)", file=sys.stderr)
    return None


def cmd_status(args: list) -> None:
    """
    race-tool.py status <batch_id>
    查看 batch 中所有子任务的状态。
    """
    if not args:
        print("用法: race-tool.py status <batch_id>", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    tasks = []
    for td in sorted(batch_dir.iterdir()):
        if td.is_dir() and (td / "task-state.md").exists():
            state = _read_state(td)
            tasks.append({
                "id": td.name,
                "state": state,
                "path": str(td),
            })

    # Count by state
    state_counts = {}
    for t in tasks:
        s = t["state"]
        state_counts[s] = state_counts.get(s, 0) + 1

    output = {
        "batch_id": batch_id,
        "path": str(batch_dir),
        "total": len(tasks),
        "state_counts": state_counts,
        "tasks": tasks,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_collect(args: list) -> None:
    """
    race-tool.py collect <batch_id>
    收集所有已完成/失败的子任务结果。
    """
    if not args:
        print("用法: race-tool.py collect <batch_id>", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    results = []
    for td in sorted(batch_dir.iterdir()):
        if td.is_dir() and (td / "task-state.md").exists():
            state = _read_state(td)
            task_result = {
                "id": td.name,
                "state": state,
                "result": _read_file(result_path(td)),
                "task": _read_file(task_path(td)),
            }
            results.append(task_result)

    output = {
        "batch_id": batch_id,
        "total": len(results),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_report(args: list) -> None:
    """
    race-tool.py report <batch_id>
    汇总报告，带状态统计和结果摘要。
    """
    if not args:
        print("用法: race-tool.py report <batch_id>", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    tasks = []
    done_count = 0
    fail_count = 0
    pending_count = 0

    for td in sorted(batch_dir.iterdir()):
        if td.is_dir() and (td / "task-state.md").exists():
            state = _read_state(td)
            if state == "done":
                done_count += 1
            elif state in ("failed", "blocked"):
                fail_count += 1
            else:
                pending_count += 1

            tasks.append({
                "id": td.name,
                "state": state,
                "result_summary": _read_file(result_path(td))[:200] if result_path(td).exists() else "",
            })

    output = {
        "batch_id": batch_id,
        "path": str(batch_dir),
        "summary": {
            "total": len(tasks),
            "done": done_count,
            "failed": fail_count,
            "pending": pending_count,
            "completion": f"{done_count / max(len(tasks), 1) * 100:.1f}%" if tasks else "N/A",
        },
        "tasks": tasks,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_update(args: list) -> None:
    """
    race-tool.py update <task_dir> <target_state> [message]
    更新子任务状态（由 subagent 调用）。
    """
    if len(args) < 2:
        print("用法: race-tool.py update <task_dir> <target_state> [message]", file=sys.stderr)
        sys.exit(1)

    task_dir = Path(args[0])
    target = args[1]
    message = args[2] if len(args) > 2 else ""

    if not task_dir.exists():
        # Try relative from .omc/plan/{date}/
        for d in PLAN_BASE.glob("**/" + args[0]):
            task_dir = d
            break
        else:
            print(f"❌ 目录不存在: {task_dir}", file=sys.stderr)
            sys.exit(1)

    task_id = task_dir.name
    success, msg = _update_state(task_dir, target, task_id, message)
    if not success:
        print(f"❌ {msg}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ {msg}")


def cmd_list(args: list) -> None:
    """
    race-tool.py list [--limit N]
    列出所有 race batch。
    """
    limit = 10
    if args and args[0] == "--limit" and len(args) > 1:
        limit = int(args[1])

    batches = []
    if PLAN_BASE.exists():
        for d in sorted(PLAN_BASE.iterdir(), reverse=True):
            if d.is_dir() and len(d.name) == 8 and d.name.isdigit():
                for bd in sorted(d.iterdir(), reverse=True):
                    if bd.is_dir() and (bd / "manifest.md").exists():
                        manifest = _read_file(bd / "manifest.md")
                        title = manifest.splitlines()[0].lstrip("# ") if manifest else bd.name
                        state_counts = {}
                        for td in bd.iterdir():
                            if td.is_dir() and (td / "task-state.md").exists():
                                s = _read_state(td)
                                state_counts[s] = state_counts.get(s, 0) + 1
                        batches.append({
                            "batch_id": bd.name,
                            "date": d.name,
                            "title": title,
                            "path": str(bd),
                            "state_counts": state_counts,
                        })
                        if len(batches) >= limit:
                            break
            if len(batches) >= limit:
                break

    output = {"batches": batches, "count": len(batches)}
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_help() -> None:
    """打印帮助信息"""
    print("Race Tool — 文档驱动并行 Swarm 引擎")
    print("")
    print("用法: race-tool.py <command> [args]")
    print("")
    print("Commands:")
    print("  init <title> [--parallel N] [--desc \"...\"]   创建 race 批次")
    print("  dispatch <batch_id> --tasks <json>         派发子任务")
    print("  status <batch_id>                          查询状态")
    print("  collect <batch_id>                         收集结果")
    print("  report <batch_id>                          生成汇总报告")
    print("  update <task_dir> <state> [msg]            更新子任务状态")
    print("  list [--limit N]                           列出所有批次")
    print("")
    print("Examples:")
    print("  race-tool.py init \"代码审查\" --parallel 5")
    print("  race-tool.py dispatch <id> --tasks '[{\"id\":\"t1\",\"goal\":\"...\"}]'")
    print("  race-tool.py report <batch_id>")


def main() -> None:
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": cmd_init,
        "dispatch": cmd_dispatch,
        "status": cmd_status,
        "collect": cmd_collect,
        "report": cmd_report,
        "update": cmd_update,
        "list": cmd_list,
        "help": lambda a: cmd_help(),  # ignore args
    }

    if command not in commands:
        print(f"❌ 未知命令: {command}", file=sys.stderr)
        cmd_help()
        sys.exit(1)

    commands[command](args)


if __name__ == "__main__":
    main()
