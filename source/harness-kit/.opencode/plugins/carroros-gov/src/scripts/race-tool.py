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
# 动态检测项目根（支持 packages 和 .claude 两种运行路径）
PROJECT_ROOT = None
for _p in _script_parents[:8]:
    if (_p / "AGENTS.md").exists() and (_p / ".claude").is_dir():
        PROJECT_ROOT = _p
        break
if PROJECT_ROOT is None:
    PROJECT_ROOT = _script_parents[0]
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

        # Build criteria + depends_on
        deps = task.get("depends_on", [])
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
        if deps:
            task_md.append("")
            task_md.append("## Depends On")
            for d in deps:
                task_md.append(f"- `{d}`")
        task_md.append("")
        _write_file(task_path(t_dir), "\n".join(task_md))

        # Write executor.md (with retry_count/step for checkpoint)
        executor_md = [
            f"# Executor — {t_id}",
            "",
            f"> batch: {batch_id}",
            f"> created: {_ts()}",
            f"> state: pending",
            f"> step: 0",
            f"> retry_count: 0",
            f"> last_checkpoint: {_ts()}",
            "",
            "## Steps",
            "",
        ]
        # Support custom steps from --steps N
        steps = task.get("steps", 5)
        default_steps = [
            "分析任务",
            "执行",
            "验证",
            "写入 result.md",
            "更新 task-state.md -> done",
        ]
        for i in range(steps):
            label = default_steps[i] if i < len(default_steps) else f"{i+1}: 执行步骤 {i+1}"
            no = i + 1
            executor_md.append(f"- [ ] Step {no}: {label}")
            executor_md.append(f"  - checkpoint: ckpt-{no}")
            executor_md.append(f"  - completed: (pending)")
            executor_md.append(f"  - summary: ")
        executor_md.append("")
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




# ─── 新命令: timeout-check / recover ───



def _read_executor_field(task_dir, field):
    """读取 executor.md 中 frontmatter 某字段的值"""
    content = _read_file(_executor_path(task_dir))
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(f"> {field}:"):
            return line.split(":", 1)[1].strip()
    return ""


def _now_ts():
    """当前时间戳（秒）"""
    return datetime.now().timestamp()


def _parse_updated(content):
    """解析 task-state.md 的 updated 字段为时间戳"""
    if not content:
        return 0.0
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("updated:"):
            val = line.split(":", 1)[1].strip()
            try:
                dt = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                return dt.timestamp()
            except ValueError:
                return 0.0
    return 0.0


def _check_elapsed(task_dir, timeout_seconds=600):
    """
    检查任务是否超时。
    返回 (is_timeout, elapsed)
    """
    content = _read_file(_state_path(task_dir))
    ts = _parse_updated(content)
    if ts == 0.0:
        return (False, 0.0)
    elapsed = _now_ts() - ts
    return (elapsed > timeout_seconds, elapsed)


def _dispatch_pending(batch_dir, batch_id, parallel):
    """扫描 pending 任务，在 parallel 上限内 dispatch。返回 dispatch 数量"""
    running = 0
    pending_tasks = []
    for td in sorted(batch_dir.iterdir()):
        if not td.is_dir():
            continue
        sp = _state_path(td)
        if not sp.exists():
            continue
        state = _read_state(td)
        if state == "pending":
            pending_tasks.append(td)
        elif state in ("running",):
            running += 1

    available = parallel - running
    if available <= 0 or not pending_tasks:
        return 0

    dispatched = 0
    for td in pending_tasks:
        if dispatched >= available:
            break
        # 检查 depends_on
        tm = _read_file(_task_path(td))
        deps = []
        in_depends = False
        for line in tm.splitlines():
            if line.strip() == "## Depends On":
                in_depends = True
                continue
            if line.startswith("## ") and line.strip() != "## Depends On":
                in_depends = False
            if in_depends:
                stripped = line.strip().strip("- ").strip("`")
                if stripped:
                    deps.append(stripped)
        if deps:
            all_met = True
            for dep in deps:
                dep_dir = batch_dir / dep
                if dep_dir.exists() and _state_path(dep_dir).exists():
                    dep_state = _read_state(dep_dir)
                    if dep_state != "done":
                        all_met = False
                        break
                else:
                    all_met = False
            if not all_met:
                continue

        _write_state(td, "running", td.name, "auto-dispatch by timeout-check")
        dispatched += 1

    return dispatched


def cmd_timeout_check(args: list) -> None:
    """
    race-tool.py timeout-check <batch_id> [--timeout <seconds>] [--watch <interval>] [--once]
    检查批次中超时的任务，超时则自动 update 为 failed。
    """
    if not args:
        print("用法: race-tool.py timeout-check <batch_id> [--timeout <seconds>] [--watch <interval>] [--once]", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    timeout_sec = 600
    watch_sec = 0
    once = False

    i = 1
    while i < len(args):
        if args[i] == '--timeout' and i + 1 < len(args):
            timeout_sec = int(args[i + 1])
            i += 2
        elif args[i] == '--watch' and i + 1 < len(args):
            watch_sec = int(args[i + 1])
            i += 2
        elif args[i] == '--once':
            once = True
            i += 1
        else:
            i += 1

    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    # Read parallel from manifest
    parallel = 5
    manifest_content = _read_file(batch_dir / 'manifest.md')
    for line in manifest_content.splitlines():
        if line.strip().startswith('> parallel:'):
            try:
                parallel = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
            break

    import time as _time

    while True:
        timed_out = 0
        for td in sorted(batch_dir.iterdir()):
            if not td.is_dir():
                continue
            sp = _state_path(td)
            if not sp.exists():
                continue
            state = _read_state(td)
            if state != 'running':
                continue
            is_timeout, elapsed = _check_elapsed(td, timeout_sec)
            if is_timeout:
                task_id = td.name
                _write_state(td, 'failed', task_id, f'超时 (elapsed={int(elapsed)}s)')
                print(f'  ⏰ {task_id}: 超时 (elapsed={int(elapsed)}s, timeout={timeout_sec}s) → failed')
                timed_out += 1

        # Auto-dispatch pending tasks after timeout check
        dispatched = _dispatch_pending(batch_dir, batch_id, parallel)
        if dispatched > 0:
            print(f'  📦 auto-dispatched {dispatched} pending tasks')

        if once or timed_out == 0 and dispatched == 0:
            print(f'✅ timeout-check complete: {timed_out} timed out, {dispatched} dispatched')
            return

        if watch_sec > 0:
            print(f'  ⏳ waiting {watch_sec}s...')
            _time.sleep(watch_sec)
        else:
            break


def cmd_recover(args: list) -> None:
    """
    race-tool.py recover <batch_id> [--timeout <seconds>]
    main agent 死亡恢复：扫描批次目录，恢复所有任务状态。
    """
    if not args:
        print("用法: race-tool.py recover <batch_id> [--timeout <seconds>]", file=sys.stderr)
        sys.exit(1)

    batch_id = args[0]
    timeout_sec = 600
    if len(args) > 1 and args[1] == '--timeout' and len(args) > 2:
        timeout_sec = int(args[2])

    batch_dir = _find_batch(batch_id)
    if batch_dir is None:
        sys.exit(1)

    print(f'🔍 Recovering batch: {batch_id}')
    print(f'   Path: {batch_dir}')
    print()

    states = {'done': 0, 'failed': 0, 'pending': 0, 'running': 0, 'blocked': 0, 'recovered': 0}
    for td in sorted(batch_dir.iterdir()):
        if not td.is_dir():
            continue
        sp = _state_path(td)
        if not sp.exists():
            continue
        state = _read_state(td)
        task_id = td.name

        if state == 'done':
            print(f'  ✅ {task_id}: done (跳过)')
            states['done'] += 1
        elif state == 'failed':
            # Check retry_count from executor.md
            retry_count = _read_executor_field(td, 'retry_count')
            try:
                rc = int(retry_count) if retry_count else 0
            except ValueError:
                rc = 0
            if rc >= 3:
                _write_state(td, 'blocked', task_id, f'recover: retry次数已达上限({rc})')
                print(f'  🔴 {task_id}: failed (retry={rc}) → blocked (已达上限)')
                states['blocked'] += 1
            else:
                _write_state(td, 'retry', task_id, 'recover: 自动重试')
                _write_state(td, 'running', task_id, 'recover: 重试中')
                print(f'  🟡 {task_id}: failed (retry={rc}) → running (第{rc+1}次重试)')
                states['recovered'] += 1
        elif state == 'pending':
            print(f'  📋 {task_id}: pending (待dispatch)')
            states['pending'] += 1
        elif state == 'running':
            is_timeout, elapsed = _check_elapsed(td, timeout_sec)
            if is_timeout:
                _write_state(td, 'failed', task_id, f'recover: 超时 (elapsed={int(elapsed)}s)')
                retry_count = _read_executor_field(td, 'retry_count')
                try:
                    rc = int(retry_count) if retry_count else 0
                except ValueError:
                    rc = 0
                if rc >= 3:
                    _write_state(td, 'blocked', task_id, f'recover: 超时+retry上限')
                    print(f'  🔴 {task_id}: running (超时, retry={rc}) → blocked')
                    states['blocked'] += 1
                else:
                    _write_state(td, 'retry', task_id, 'recover: 超时自动重试')
                    _write_state(td, 'running', task_id, 'recover: 重试中')
                    print(f'  🟡 {task_id}: running (超时, elapsed={int(elapsed)}s) → running (第{rc+1}次重试)')
                    states['recovered'] += 1
            else:
                print(f'  🔄 {task_id}: running (未超时, elapsed={int(elapsed)}s, 保留)')
                states['running'] += 1
        elif state in ('blocked', 'retry'):
            print(f'  ⚪ {task_id}: {state} (保留)')
            states[state] = states.get(state, 0) + 1

    # Update manifest.md recovery info
    print()
    print(f'📊 Recovery Summary:')
    for k, v in states.items():
        if v > 0:
            print(f'    {k}: {v}')

    manifest_path = batch_dir / 'manifest.md'
    if manifest_path.exists():
        manifest_content = _read_file(manifest_path)
        recovery_block = [
            '',
            '---',
            '## Recovery Info',
            f'- status: recovered',
            f'- total_tasks: {sum(states.values())}',
            f'- recovered: {states["recovered"]}',
            f'- blocked: {states["blocked"]}',
            f'- done: {states["done"]}',
            f'- last_updated: {_ts()}',
        ]
        manifest_content = manifest_content.rstrip() + '\n' + '\n'.join(recovery_block) + '\n'
        _write_file(manifest_path, manifest_content)
        print(f'  📝 manifest.md 已更新 Recovery Info')

    print(f'✅ Recover complete')

    # Auto-dispatch pending tasks after recovery
    parallel = 5
    manifest_content = _read_file(batch_dir / 'manifest.md')
    for line in manifest_content.splitlines():
        if line.strip().startswith('> parallel:'):
            try:
                parallel = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
            break
    dispatched = _dispatch_pending(batch_dir, batch_id, parallel)
    if dispatched > 0:
        print(f'  📦 auto-dispatched {dispatched} pending tasks')


def cmd_help() -> None:
    """打印帮助信息"""
    print("Race Tool — 文档驱动并行 Swarm 引擎 (v3.0)")
    print("")
    print("用法: race-tool.py <command> [args]")
    print("")
    print("Commands:")
    print("  init <title> [--parallel N] [--desc \"...\"]   创建 race 批次")
    print("  dispatch <batch_id> --tasks <json>         派发子任务")
    print("  status <batch_id>                          查询状态")
    print("  collect <batch_id>                         收集结果")
    print("  report <batch_id>                          生成汇总报告")
    print("  timeout-check <batch_id> [opts]            超时检测 [--timeout N] [--watch N] [--once]")
    print("  recover <batch_id> [--timeout N]           死亡恢复扫描")
    print("  update <task_dir> <state> [msg]            更新子任务状态")
    print("  list [--limit N]                           列出所有批次")
    print("")
    print("Examples:")
    print("  race-tool.py init \"代码审查\" --parallel 5")
    print("  race-tool.py dispatch <id> --tasks '[{\"id\":\"t1\",\"goal\":\"...\"}]'")
    print("  race-tool.py timeout-check <batch_id> --watch 30")
    print("  race-tool.py recover <batch_id>")
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
        "timeout-check": cmd_timeout_check,
        "recover": cmd_recover,
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
