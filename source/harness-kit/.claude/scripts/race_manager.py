#!/usr/bin/env python3
"""
race_manager.py — Race 蜂群协调引擎
Python 移植版，完全等价 race_manager.sh v1.0

跨平台: Claude Code / OpenCode / Codex CLI / Gemini CLI / Qwen Code / Cursor
所有平台均支持: bash + 文件 I/O → race_manager 全平台通用
Claude Code 额外支持: Task()/TeamCreate 子 Agent 派发 (由 lx-race SKILL.md 处理)

Race = 蜂群协调层 (Swarm Coordination)
  - register:   注册子任务到 Race 状态树 (全平台)
  - dispatch:   派发策略因平台而异 (由 lx-race SKILL.md 定义)
  - collect:    轮询 result.json 收集结果 (全平台)
  - report:     聚合报告 (全平台)

与 OMA Lock 协同: race 不建写锁, worker 写文件时 pretool-write-lock.sh 自动加锁

Usage:
  python3 race_manager.py init <id> [task_description]
  python3 race_manager.py start <id>
  python3 race_manager.py register <parent> --subtasks A,B,C [--desc "parent task"]
  python3 race_manager.py status <id> [--all] [--json]
  python3 race_manager.py complete <id> <status> [output]
  python3 race_manager.py report <id>
  python3 race_manager.py list [--json]
  python3 race_manager.py clean [id]
"""

import atexit
import glob
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Per-invocation temp dir (auto-cleaned on exit) ───
_RACE_TMPDIR = None  # type: Path | None


def _cleanup():
    if _RACE_TMPDIR and _RACE_TMPDIR.exists():
        shutil.rmtree(_RACE_TMPDIR, ignore_errors=True)


atexit.register(_cleanup)


def _mktmp() -> str:
    global _RACE_TMPDIR
    if _RACE_TMPDIR is None:
        _RACE_TMPDIR = Path(tempfile.mkdtemp())
    fd, path = tempfile.mkstemp(dir=str(_RACE_TMPDIR))
    os.close(fd)
    return path


def _use_tmpfile() -> str:
    """Return a tmpfile path for content staging."""
    return _mktmp()


# ─── Path initialization ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
RACE_DIR = PROJECT_ROOT / ".omc" / "race"

PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)


# ─── Utility functions ───
def _py_json_write(filepath: str, data: dict):
    """Write JSON to file atomically via temp + rename."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp." + str(os.getpid()))
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.rename(tmp, filepath)


def _py_read_json(filepath: str) -> dict:  # type: ignore[return]  # returns None when missing
    """Read JSON from file."""
    p = Path(filepath)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _py_read_json_key(filepath: str, key: str) -> str:
    """Read a specific key from JSON file."""
    data = _py_read_json(filepath)
    if data:
        return str(data.get(key, ""))
    return ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_id(raw: str) -> str:
    """Sanitize race id (plain, no slash)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', raw)


def _sanitize_path_id(raw: str) -> str:
    """Sanitize race id allowing / for subtask paths."""
    if not raw:
        return ""
    parts = raw.split("/")
    safe_parts = []
    for part in parts:
        safe = re.sub(r'[^a-zA-Z0-9_-]', '', part)
        if not safe:
            return ""
        safe_parts.append(safe)
    return "/".join(safe_parts)


# ─── Usage ───
def usage():
    print("""Race Manager — 蜂群协调引擎

Commands:
  init      race_manager.py init <id> [task_description]
            Create a flat race workspace at .omc/race/<id>/

  start     race_manager.py start <id>
            Mark a race as running

  register  race_manager.py register <parent> --subtasks A,B,C [--desc "..."]
            Create hierarchical race with subtask tracking
            → .omc/race/<parent>/manifest.json + subtasks/*/owner.json

  status    race_manager.py status <id> [--all] [--json]
            Check race status. --all aggregates subtask progress

  complete  race_manager.py complete <id> <status> [output]
            Write result.json. status: completed | failed

  report    race_manager.py report <id>
            Full aggregated report of all subtasks

  list      race_manager.py list [--json]
            List all races

  clean     race_manager.py clean [id]
            Remove a specific race or all completed races

Platform dispatch (handled by lx-race SKILL.md, not this script):
  Claude Code:  Task()/TeamCreate → sub-agents write result.json
  Other 5 CLI:  run_in_background / sequential → workers write result.json

OMA Lock: Workers writing shared files → pretool-write-lock.sh auto-locks""", file=sys.stderr)
    sys.exit(1)


# ─── Command: init ───
def cmd_init(race_id: str, task_desc: str = ""):
    if not race_id:
        print("ERROR: race id is required", file=sys.stderr)
        sys.exit(1)

    safe_id = _sanitize_id(race_id)
    if safe_id != race_id:
        print("ERROR: race id contains invalid characters (use a-zA-Z0-9_-)", file=sys.stderr)
        sys.exit(1)

    race_workspace = RACE_DIR / safe_id
    if race_workspace.exists():
        print(f"ERROR: race '{safe_id}' already exists at {race_workspace}", file=sys.stderr)
        sys.exit(1)

    race_workspace.mkdir(parents=True, exist_ok=True)

    owner = os.environ.get("USER", "unknown")
    now_val = _now()

    data = {
        "race_id": safe_id,
        "owner": owner,
        "created_at": now_val,
        "status": "init",
        "task": task_desc if task_desc else None,
    }
    _py_json_write(str(race_workspace / "owner.json"), data)
    print(f"RACE_INIT:{safe_id}:{race_workspace}")


# ─── Command: start ───
def cmd_start(race_id: str):
    if not race_id:
        print("ERROR: race id is required", file=sys.stderr)
        sys.exit(1)

    safe_id = _sanitize_id(race_id)
    if safe_id != race_id or not safe_id:
        print("ERROR: race id contains invalid characters (use a-zA-Z0-9_-)", file=sys.stderr)
        sys.exit(1)
    race_id = safe_id
    race_workspace = RACE_DIR / race_id

    if not race_workspace.exists():
        print(f"ERROR: race '{race_id}' not found (run init first)", file=sys.stderr)
        sys.exit(1)

    ts = _now()

    result_data = {
        "race_id": race_id,
        "status": "running",
        "started_at": ts,
        "completed_at": None,
        "output": None,
    }
    _py_json_write(str(race_workspace / "result.json"), result_data)
    print(f"RACE_START:{race_id}")

    # Update owner.json
    owner_file = race_workspace / "owner.json"
    owner_data = _py_read_json(str(owner_file))
    if owner_data:
        owner_data["status"] = "running"
        _py_json_write(str(owner_file), owner_data)


# ─── Command: register (hierarchical) ───
def cmd_register(args: list[str]):
    parent_id = ""
    subtasks = ""
    desc = ""

    i = 0
    while i < len(args):
        if args[i] == "--subtasks":
            i += 1
            if i < len(args):
                subtasks = args[i]
        elif args[i] == "--desc":
            i += 1
            if i < len(args):
                desc = args[i]
        elif args[i].startswith("--"):
            print(f"ERROR: unknown flag {args[i]}", file=sys.stderr)
            sys.exit(1)
        else:
            parent_id = _sanitize_id(args[i])
        i += 1

    if not parent_id:
        print("ERROR: parent race id is required", file=sys.stderr)
        sys.exit(1)

    if not subtasks:
        print("ERROR: --subtasks is required (comma-separated, e.g. A,B,C)", file=sys.stderr)
        sys.exit(1)

    # Split subtasks
    sub_list = [s.strip() for s in subtasks.split(",") if s.strip()]
    if not sub_list:
        print("ERROR: at least one subtask required", file=sys.stderr)
        sys.exit(1)

    race_workspace = RACE_DIR / parent_id
    if race_workspace.exists():
        print(f"ERROR: race '{parent_id}' already exists", file=sys.stderr)
        sys.exit(1)

    race_workspace.mkdir(parents=True)
    now_val = _now()
    owner = os.environ.get("USER", "unknown")

    # Sanitize subtask IDs
    subtask_ids = []
    for raw_id in sub_list:
        safe_id = _sanitize_id(raw_id)
        if not safe_id:
            print(f"WARNING: skipping empty/invalid subtask id '{raw_id}'", file=sys.stderr)
            continue
        subtask_ids.append(safe_id)

    # Build manifest.json
    manifest_data = {
        "parent_id": parent_id,
        "owner": owner,
        "created_at": now_val,
        "status": "registered",
        "description": desc,
        "total_subtasks": len(subtask_ids),
        "completed_subtasks": 0,
        "failed_subtasks": 0,
        "subtask_ids": subtask_ids,
    }
    _py_json_write(str(race_workspace / "manifest.json"), manifest_data)
    print(f"RACE_REGISTER:{parent_id}:{len(subtask_ids)} subtasks")

    # Create subtask directories and owner.json files
    for subtask_id in subtask_ids:
        sub_workspace = race_workspace / "subtasks" / subtask_id
        sub_workspace.mkdir(parents=True, exist_ok=True)
        sub_data = {
            "race_id": f"{parent_id}/{subtask_id}",
            "parent": parent_id,
            "subtask_id": subtask_id,
            "owner": owner,
            "created_at": now_val,
            "status": "registered",
            "assigned_to": None,
        }
        _py_json_write(str(sub_workspace / "owner.json"), sub_data)

    print(f"RACE_REGISTERED:{parent_id} @ {race_workspace}")


# ─── Command: status ───
def cmd_status(args: list[str]):
    all_mode = False
    json_output = False
    race_id = ""

    for arg in args:
        if arg == "--all":
            all_mode = True
        elif arg == "--json":
            json_output = True
        elif arg.startswith("--"):
            print(f"ERROR: unknown flag {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            if not race_id:
                race_id = arg

    if not race_id:
        print("ERROR: race id is required", file=sys.stderr)
        sys.exit(1)

    safe_id = _sanitize_path_id(race_id)
    if not safe_id:
        print("ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)", file=sys.stderr)
        sys.exit(1)
    race_id = safe_id

    race_workspace = RACE_DIR / race_id
    if not race_workspace.exists():
        print(f"ERROR: race '{race_id}' not found", file=sys.stderr)
        sys.exit(1)

    # --all mode: aggregate subtask statuses
    if all_mode:
        _status_all(race_id, race_workspace, json_output)
        return

    # Single race status
    result_file = race_workspace / "result.json"
    owner_file = race_workspace / "owner.json"

    if json_output:
        result_data = _py_read_json(str(result_file))
        owner_data = _py_read_json(str(owner_file))
        output = {
            "race_id": race_id,
            "workspace": str(race_workspace),
            "owner": owner_data,
            "result": result_data,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        status = "init"
        output = ""
        if result_file.exists():
            status = _py_read_json_key(str(result_file), "status")
            output = _py_read_json_key(str(result_file), "output")

        print(f"RACE:{race_id}")
        print(f"  status:    {status}")
        print(f"  workspace: {race_workspace}")
        if output:
            print(f"  output:    {output[:200]}")
        if owner_file.exists():
            task_desc = _py_read_json_key(str(owner_file), "task")
            if task_desc:
                print(f"  task:      {task_desc}")


# ─── Internal: status --all ───
def _status_all(race_id: str, race_workspace: Path, json_output: bool):
    subtasks_dir = race_workspace / "subtasks"
    manifest_file = race_workspace / "manifest.json"

    if not manifest_file.exists():
        print(f"ERROR: race '{race_id}' has no manifest (not a parent race)", file=sys.stderr)
        sys.exit(1)

    total = 0
    completed = 0
    failed = 0
    running = 0
    registered = 0

    subdata = []

    if subtasks_dir.exists():
        for sub_dir in sorted(subtasks_dir.iterdir()):
            if not sub_dir.is_dir():
                continue
            sub_id = sub_dir.name
            total += 1

            result_file = sub_dir / "result.json"
            st = "registered"
            sub_output = ""
            if result_file.exists():
                st = _py_read_json_key(str(result_file), "status") or "registered"
                sub_output = _py_read_json_key(str(result_file), "output") or ""

            if st == "completed":
                completed += 1
            elif st == "failed":
                failed += 1
            elif st == "running":
                running += 1
            else:
                registered += 1

            subdata.append({"id": sub_id, "status": st, "output": sub_output})

    if json_output:
        output = {
            "race_id": race_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "registered": registered,
            "subtasks": subdata,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"RACE:{race_id} (swarm)")
        print(f"  progress:  {completed}/{total} completed, {running} running, {failed} failed, {registered} registered")
        print(f"  workspace: {race_workspace}")
        print(f"  subtasks:")
        icons = {"completed": "✅", "failed": "❌", "running": "🔄"}
        for sd in subdata:
            icon = icons.get(sd["status"], "○")
            print(f"    {icon} {sd['id']} [{sd['status']}]")
            if sd["output"]:
                print(f"      output: {sd['output'][:60]}")


# ─── Command: complete ───
def cmd_complete(raw_id: str, status: str, output: str = ""):
    if status not in ("completed", "failed"):
        print(f"ERROR: status must be 'completed' or 'failed', got '{status}'", file=sys.stderr)
        sys.exit(1)

    race_id = _sanitize_path_id(raw_id)
    if not race_id:
        print("ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)", file=sys.stderr)
        sys.exit(1)

    # Resolve workspace path:
    #   parent/subtask → .omc/race/parent/subtasks/subtask/
    #   parent         → .omc/race/parent/
    if "/" in race_id:
        pp, ss = race_id.rsplit("/", 1)
        race_workspace = RACE_DIR / pp / "subtasks" / ss
    else:
        race_workspace = RACE_DIR / race_id

    if not race_workspace.exists():
        print(f"ERROR: race '{race_id}' not found", file=sys.stderr)
        sys.exit(1)

    result_file = race_workspace / "result.json"
    owner_file = race_workspace / "owner.json"
    ts = _now()

    # Write result.json
    result_data = {
        "race_id": race_id,
        "status": status,
        "started_at": None,
        "completed_at": ts,
        "output": output if output else None,
    }
    _py_json_write(str(result_file), result_data)

    # Update owner.json
    owner_data = _py_read_json(str(owner_file))
    if owner_data:
        owner_data["status"] = status
        _py_json_write(str(owner_file), owner_data)

    # Update parent manifest
    if "/" in race_id:
        pp, ss = race_id.rsplit("/", 1)
        manifest_file = RACE_DIR / pp / "manifest.json"
        if manifest_file.exists():
            manifest_data = _py_read_json(str(manifest_file))
            if manifest_data:
                if status == "completed":
                    manifest_data["completed_subtasks"] = manifest_data.get("completed_subtasks", 0) + 1
                elif status == "failed":
                    manifest_data["failed_subtasks"] = manifest_data.get("failed_subtasks", 0) + 1
                _py_json_write(str(manifest_file), manifest_data)

    print(f"RACE_COMPLETE:{race_id}:{status}")


# ─── Command: report ───
def cmd_report(raw_id: str):
    race_id = _sanitize_path_id(raw_id)
    if not race_id:
        print("ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)", file=sys.stderr)
        sys.exit(1)

    race_workspace = RACE_DIR / race_id
    manifest_file = race_workspace / "manifest.json"
    subtasks_dir = race_workspace / "subtasks"

    if not manifest_file.exists():
        print(f"ERROR: race '{race_id}' has no manifest (not a parent race)", file=sys.stderr)
        sys.exit(1)

    # Read parent info
    manifest_data = _py_read_json(str(manifest_file)) or {}
    parent_desc = manifest_data.get("description", "")
    total = manifest_data.get("total_subtasks", 0)
    comp = manifest_data.get("completed_subtasks", 0)
    failed = manifest_data.get("failed_subtasks", 0)

    print("==========================================")
    print(f"  Race Report: {race_id}")
    print("==========================================")
    if parent_desc:
        print(f"  Description: {parent_desc}")
    print(f"  Progress:    {comp}/{total} completed, {failed} failed")
    print("")

    if subtasks_dir.exists():
        for sub_dir in sorted(subtasks_dir.iterdir()):
            if not sub_dir.is_dir():
                continue
            sub_id = sub_dir.name
            result_file = sub_dir / "result.json"
            owner_file = sub_dir / "owner.json"

            st = "registered"
            sub_output = ""
            if result_file.exists():
                st = _py_read_json_key(str(result_file), "status") or "registered"
                sub_output = _py_read_json_key(str(result_file), "output") or ""

            assigned = ""
            if owner_file.exists():
                assigned = _py_read_json_key(str(owner_file), "assigned_to") or ""

            print(f"  --- subtask: {sub_id} [{st}] ---")
            if assigned:
                print(f"    assigned_to: {assigned}")
            if sub_output:
                print("    output:")
                for line in sub_output.splitlines():
                    print(f"      {line}")
            print("")

    print("==========================================")


# ─── Command: list ───
def cmd_list(json_output: bool = False):
    if not RACE_DIR.exists():
        if json_output:
            print('{"races": []}')
        else:
            print("No races found.")
        sys.exit(0)

    if json_output:
        races = []
        for d in sorted(RACE_DIR.iterdir()):
            if not d.is_dir():
                continue
            owner = _py_read_json(str(d / "owner.json")) or {}
            result = _py_read_json(str(d / "result.json")) or {}
            races.append({"id": d.name, "owner": owner, "result": result})
        print(json.dumps({"races": races}, indent=2, ensure_ascii=False))
    else:
        races = sorted([d.name for d in RACE_DIR.iterdir() if d.is_dir()])
        if not races:
            print("No races found.")
            sys.exit(0)
        print(f"Races in {RACE_DIR}:")
        for rid in races:
            ws = RACE_DIR / rid
            st = "init"
            if (ws / "result.json").exists():
                st = _py_read_json_key(str(ws / "result.json"), "status") or "init"
            if (ws / "manifest.json").exists():
                comp = _py_read_json_key(str(ws / "manifest.json"), "completed_subtasks") or "0"
                total = _py_read_json_key(str(ws / "manifest.json"), "total_subtasks") or "0"
                print(f"  - {rid} [swarm {comp}/{total}]")
            else:
                print(f"  - {rid} [{st}]")


# ─── Command: clean ───
def cmd_clean(raw_target: str = ""):
    if raw_target:
        target_id = _sanitize_id(raw_target)
        if target_id != raw_target or not target_id:
            print(f"ERROR: invalid race id '{raw_target}' (use a-zA-Z0-9_-)", file=sys.stderr)
            sys.exit(1)
        race_workspace = RACE_DIR / target_id
        if not race_workspace.exists():
            print(f"ERROR: race '{target_id}' not found", file=sys.stderr)
            sys.exit(1)
        shutil.rmtree(race_workspace)
        print(f"CLEANED:{target_id}")
    else:
        if not RACE_DIR.exists():
            print("No races to clean.")
            sys.exit(0)
        cleaned = 0
        for d in sorted(RACE_DIR.iterdir()):
            if not d.is_dir():
                continue
            rid = d.name
            result_file = d / "result.json"
            if result_file.exists():
                st = _py_read_json_key(str(result_file), "status") or ""
                if st in ("completed", "failed"):
                    shutil.rmtree(d)
                    print(f"CLEANED:{rid}")
                    cleaned += 1
        if cleaned == 0:
            print("No completed races to clean.")
        else:
            print(f"Cleaned {cleaned} race(s).")


# ─── Main ───
def main():
    if len(sys.argv) < 2:
        usage()

    action = sys.argv[1]
    args = sys.argv[2:]

    if action == "init":
        if len(args) < 1:
            print("ERROR: init requires <id> [task_description]", file=sys.stderr)
            sys.exit(1)
        cmd_init(args[0], " ".join(args[1:]))
    elif action == "start":
        if len(args) < 1:
            print("ERROR: start requires <id>", file=sys.stderr)
            sys.exit(1)
        cmd_start(args[0])
    elif action == "register":
        cmd_register(args)
    elif action == "status":
        cmd_status(args)
    elif action == "complete":
        if len(args) < 2:
            print("ERROR: complete requires <id> <status> [output]", file=sys.stderr)
            sys.exit(1)
        output = " ".join(args[2:]) if len(args) > 2 else ""
        cmd_complete(args[0], args[1], output)
    elif action == "report":
        if len(args) < 1:
            print("ERROR: report requires <id>", file=sys.stderr)
            sys.exit(1)
        cmd_report(args[0])
    elif action == "list":
        json_output = "--json" in args
        cmd_list(json_output)
    elif action == "clean":
        cmd_clean(args[0] if args else "")
    else:
        usage()


if __name__ == "__main__":
    main()
