#!/usr/bin/env python3
"""
task_state_tracker.py — 步骤执行状态追踪器（SubAgentManager 轻量版）

写入 task-task.json 到 task 的 state 目录（.omc/tasks/{date}/{id}/state/）。
每个步骤记录：开始时间 / 耗时 / 重试 / 文件变化（tick 前后 diff）。

文件规范：5.md#SubAgentManager 的 resolve_result 轻量实现。
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_state_file(task_dir: Path) -> Path:
    """task 的 state 目录下的 task-task.json"""
    state_dir = task_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "task-state.json"


def _load_state(task_dir: Path) -> dict[str, Any]:
    f = _get_state_file(task_dir)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"steps": {}}


def _save_state(task_dir: Path, state: dict[str, Any]) -> None:
    f = _get_state_file(task_dir)
    f.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _get_project_root(token_path: Path) -> Optional[Path]:
    """从 token 的 task_dir 推断项目根。"""
    try:
        token = json.loads(token_path.read_text())
        td = token.get("task_dir", "")
        if td:
            p = Path(td)
            for parent in [p] + list(p.parents):
                if (parent / ".git").exists() or (parent / "AGENTS.md").exists():
                    return parent
            return p.parent
    except Exception:
        pass
    return None


def _get_task_dir_from_token(token_path: Path) -> Optional[Path]:
    """从 token.json 提取 task_dir"""
    try:
        token = json.loads(token_path.read_text())
        td = token.get("task_dir", "")
        if td:
            return Path(td)
    except Exception:
        pass
    return None


def _detect_file_changes(project_root: Path) -> dict:
    """检测 git 工作区文件变化"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=project_root,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            return {
                "changed": True,
                "files": [l[2:].strip() for l in lines if len(l) > 3],
                "count": len(lines),
                "summary": "\n".join(lines) if len(lines) <= 10 else (
                    "\n".join(lines[:10]) + f"\n... and {len(lines)-10} more"
                ),
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return {"changed": False, "files": [], "count": 0, "summary": ""}


# ═════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════

def mark_step_started(token_path: Path, step_id: str) -> None:
    """记录 step 开始执行的时间。

    状态写入 token.json 同级的 state/task-state.json。

    参数:
        token_path: token.json 的路径
        step_id: 步骤 ID（S1, S2...）
    """
    task_dir = _get_task_dir_from_token(token_path)
    if not task_dir:
        return

    state = _load_state(task_dir)

    prev = state["steps"].get(step_id, {})
    retries = prev.get("retries", 0)
    if prev.get("completed_at"):
        retries += 1  # 之前完成过又跑 = 重试

    state["steps"][step_id] = {
        "status": "running",
        "started_at": _now_iso(),
        "completed_at": None,
        "duration": None,
        "retries": retries,
        "tick_before": None,
        "tick_after": None,
    }

    # 记录 tick 前的文件变化
    proj_root = _get_project_root(token_path)
    if proj_root:
        state["steps"][step_id]["tick_before"] = _detect_file_changes(proj_root)

    _save_state(task_dir, state)


def mark_step_completed(token_path: Path, step_id: str) -> None:
    """记录 step 完成。写完成时间 + 耗时 + tick 后文件变化"""
    task_dir = _get_task_dir_from_token(token_path)
    if not task_dir:
        return

    state = _load_state(task_dir)
    step = state["steps"].setdefault(step_id, {})
    step["status"] = "completed"
    step["completed_at"] = _now_iso()

    if step.get("started_at"):
        try:
            t_start = datetime.fromisoformat(step["started_at"])
            t_end = datetime.fromisoformat(step["completed_at"])
            step["duration"] = round((t_end - t_start).total_seconds(), 1)
        except Exception:
            pass

    # tick 后文件变化
    proj_root = _get_project_root(token_path)
    if proj_root:
        after = _detect_file_changes(proj_root)
        step["tick_after"] = after

    _save_state(task_dir, state)


def get_step_state(token_path: Path, step_id: str) -> Optional[dict]:
    """获取指定 step 的状态"""
    task_dir = _get_task_dir_from_token(token_path)
    if not task_dir:
        return None
    state = _load_state(task_dir)
    return state["steps"].get(step_id)


def get_all_states(token_path: Path) -> dict:
    """获取所有 step 的状态"""
    task_dir = _get_task_dir_from_token(token_path)
    if not task_dir:
        return {}
    return _load_state(task_dir)["steps"]


def format_status(token: dict, token_path: Path) -> str:
    """格式化 task-state 信息，用于 cmd_status 展示。"""
    all_states = get_all_states(token_path)
    if not all_states:
        return ""

    lines = []
    for step in token.get("steps", []):
        sid = step["id"]
        s = all_states.get(sid, {})
        status = step.get("status", "pending")

        icon = "✔" if status == "completed" else ("◷" if status == "running" else "○")

        parts = [f"   {icon} {sid}: {status}"]
        if s.get("started_at"):
            try:
                t = datetime.fromisoformat(s["started_at"])
                parts.append(f"started={t.strftime('%H:%M:%S')}")
            except Exception:
                pass
        if s.get("duration"):
            parts.append(f"took={s['duration']}s")
        if s.get("retries", 0) > 0:
            parts.append(f"retry={s['retries']}")
        ta = s.get("tick_after", {})
        if ta and ta.get("changed"):
            parts.append(f"Δ{ta['count']}")

        lines.append("  ".join(parts))

    return "\n".join(lines)


def format_tick_verdict(token_path: Path, step_id: str) -> str:
    """verify 完成后输出变化摘要"""
    all_states = get_all_states(token_path)
    s = all_states.get(step_id, {})
    before = s.get("tick_before", {})
    after = s.get("tick_after", {})

    lines = []
    b_count = before.get("count", 0)
    a_count = after.get("count", 0)

    if a_count > b_count:
        old_files = set(before.get("files", []))
        added = [f for f in after.get("files", []) if f not in old_files]
        if added:
            lines.append(f"   Δ files changed: {len(added)} new")
    elif a_count == 0 and b_count > 0:
        lines.append("   ✓ files cleaned")

    return "\n".join(lines)


# ═════════════════════════════════════════════════
# CLI entry point
# ═════════════════════════════════════════════════

def main():
    argv = sys.argv[1:]
    if not argv or argv[0] == "status":
        print("Usage: task_state_tracker.py <mark-started|mark-completed|get> <token_path> <step_id>")
        return 1

    action = argv[0]
    if action == "mark-started" and len(argv) >= 3:
        mark_step_started(Path(argv[1]), argv[2])
    elif action == "mark-completed" and len(argv) >= 3:
        mark_step_completed(Path(argv[1]), argv[2])
    elif action == "get" and len(argv) >= 3:
        s = get_step_state(Path(argv[1]), argv[2])
        print(json.dumps(s, ensure_ascii=False, indent=2) if s else "null")
    elif action == "status" and len(argv) >= 2:
        all_states = get_all_states(Path(argv[1]))
        print(json.dumps(all_states, ensure_ascii=False, indent=2))
    else:
        print(f"Unknown: {action}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
