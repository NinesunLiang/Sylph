#!/usr/bin/env python3
"""
pretool-compact-writer.py — PreCompact — 在 /compact 前保存任务状态+最后20条用户query

Role: /compact 前收集当前会话状态、活跃任务、最近用户询问
      写入 session-handoff.md 和 todo-queue.md，
      确保 compact 后 inject-project-knowledge 能恢复完整上下文。
"""

import json
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    extract_tool_input_status, output_continue,
    PROJECT_ROOT, STATE_DIR,
)


def collect_query_history(state_dir: Path, max_queries: int = 20) -> list:
    """从 .last-user-prompts 收集最近 N 条用户 query（环形队列）。"""
    prompt_log = state_dir / ".last-user-prompts"
    queries = []
    if prompt_log.exists():
        try:
            lines = prompt_log.read_text(encoding="utf-8", errors="replace").splitlines()
            # 格式: "YYYY-MM-DDTHH:MM:SSZ||query"
            for line in lines[-max_queries:]:
                line = line.strip()
                if not line:
                    continue
                if "||" in line:
                    ts, q = line.split("||", 1)
                    queries.append(f"- [{ts}] {q.strip()[:120]}")
                else:
                    queries.append(f"- {line[:120]}")
        except OSError:
            pass
    return queries


def collect_session_state(project_root: Path, state_dir: Path) -> dict:
    """收集当前会话状态。"""
    state = {
        "branch": "unknown",
        "modified_files": [],
        "diff_stat": "",
        "turn_count": 0,
        "active_feature": "",
        "active_task": "",
        "error_summary": "not available",
        "errors_active": 0,
        "context_usage": "",
        "is_autonomous": False,
    }

    # Git branch
    try:
        r = subprocess.run(
            ["git", "-C", str(project_root), "branch", "--show-current"],
            capture_output=True, text=True, timeout=10,
        )
        state["branch"] = r.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Modified files
    try:
        r = subprocess.run(
            ["git", "-C", str(project_root), "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        files = [f for f in r.stdout.strip().split("\n") if f]
        state["modified_files"] = files[:15]
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Diff stat
    try:
        r = subprocess.run(
            ["git", "-C", str(project_root), "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
        state["diff_stat"] = lines[-1] if lines else ""
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Turn count
    turns_file = state_dir / "session-turns.json"
    if turns_file.exists():
        try:
            d = json.loads(turns_file.read_text(encoding="utf-8"))
            state["turn_count"] = int(d.get("count", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # Active RPE feature + task
    rpe_dir = project_root / "rpe"
    if rpe_dir.exists():
        try:
            r = subprocess.run(
                ["find", str(rpe_dir), "-name", "executor.md", "-type", "f"],
                capture_output=True, text=True, timeout=10,
            )
            files = [f for f in r.stdout.strip().split("\n") if f]
            if files:
                files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
                latest = files[0]
                rel = latest.replace(str(rpe_dir) + "/", "").replace("/executor.md", "")
                state["active_feature"] = rel
                try:
                    with open(latest, encoding="utf-8") as f:
                        for line in f:
                            m = re.search(r"\b(🔄|in.progress|进行中)\b.*", line)
                            if m:
                                state["active_task"] = m.group(0).strip()
                                break
                except OSError:
                    pass
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Error DNA summary
    dna_file = state_dir / "error-dna.json"
    if dna_file.exists():
        try:
            dna = json.loads(dna_file.read_text(encoding="utf-8"))
            sigs = dna.get("error_signatures", {})
            if isinstance(sigs, dict):
                active = [k for k, v in sigs.items() if isinstance(v, dict) and v.get("status") == "active"]
                state["errors_active"] = len(active)
                state["error_summary"] = f"{len(active)} active errors" if active else "0 active errors"
        except (json.JSONDecodeError, OSError):
            pass

    # Context usage
    idx_file = state_dir / "token-tracking-index.json"
    if idx_file.exists():
        try:
            d = json.loads(idx_file.read_text(encoding="utf-8"))
            usage = int(d.get("usage", 0))
            limit = int(d.get("limit", 200000))
            pct = int(usage * 100 / limit) if limit > 0 else 0
            state["context_usage"] = f"{pct}% ({usage}/{limit})"
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # Autonomous mode markers
    for marker in ["tokens/autonomous.active", "tokens/lx-ghost.json", "tokens/lx-goal.json"]:
        if (state_dir / marker).exists():
            state["is_autonomous"] = True
            break

    return state


def write_handoff(state: dict, queries: list, state_dir: Path):
    """写 session-handoff.md。"""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    auto_note = "_mode: autonomous_  \n" if state["is_autonomous"] else ""

    modified = ";".join(state["modified_files"][:10]) if state["modified_files"] else "none"
    query_block = "\n".join(queries) if queries else "- (none recorded)"

    content = (
        f"# Compact Savepoint — {ts}\n"
        f"## Session State\n"
        f"- Branch: {state['branch']}\n"
        f"- Turn: {state['turn_count']}\n"
        f"- Context: {state['context_usage']}\n"
        f"- Active Feature: {state['active_feature'] or 'none'}\n"
        f"- Active Task: {state['active_task'] or 'none'}\n"
        f"{auto_note}"
        f"\n"
        f"## Modified Files\n"
        f"- Modified: {modified}\n"
        f"- Diff stat: {state['diff_stat'] or 'clean'}\n"
        f"\n"
        f"## Errors\n"
        f"- Active errors: {state['errors_active']}\n"
        f"- Summary: {state['error_summary']}\n"
        f"\n"
        f"## Last {len(queries)} User Queries\n"
        f"{query_block}\n"
    )

    try:
        (state_dir / "session-handoff.md").write_text(content, encoding="utf-8")
    except OSError:
        pass


def write_todo_queue(queries: list, state_dir: Path):
    """写 todo-queue.md（供 inject-project-knowledge 读取）。"""
    query_block = "\n".join(queries[-20:]) if queries else "- (none)"
    content = (
        f"# Todo Queue — Compact 记忆恢复\n"
        f"\n"
        f"## 最近用户询问\n"
        f"{query_block}\n"
        f"\n"
        f"## 已完成任务\n"
        f"- (see session-handoff.md)\n"
        f"\n"
        f"## 待完成任务\n"
        f"- (see session-handoff.md)\n"
    )

    try:
        (state_dir / "todo-queue.md").write_text(content, encoding="utf-8")
    except OSError:
        pass


def main():
    if not hc_enabled("pretool_compact_writer"):
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Parse input for PreCompact context
    # CC sends PreCompact hook input with current tool call info
    # We detect compact trigger via stdin
    is_compact_triggered = False
    if input_str:
        try:
            data = json.loads(input_str)
            # PreCompact hook gets the tool call data
            # If it's a UserPromptSubmit with /compact, that's our signal
            tool_name = data.get("tool", "") or data.get("name", "")
            tool_input = data.get("input", {}) or data.get("arguments", {})
            prompt = ""
            if isinstance(tool_input, dict):
                prompt = tool_input.get("prompt", "") or tool_input.get("text", "")
            if isinstance(tool_input, str):
                prompt = tool_input
            if "/compact" in prompt.lower() or "compact" == tool_name.lower():
                is_compact_triggered = True
        except (json.JSONDecodeError, AttributeError):
            prompt = str(input_str)
            if "/compact" in prompt.lower():
                is_compact_triggered = True

    if not is_compact_triggered:
        output_continue()
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    queries = collect_query_history(STATE_DIR, max_queries=20)
    state = collect_session_state(PROJECT_ROOT, STATE_DIR)

    write_handoff(state, queries, STATE_DIR)
    write_todo_queue(queries, STATE_DIR)

    output_continue()
    flywheel_event("pretool_compact_writer", "compact_handoff_written", "P2")


if __name__ == "__main__":
    main()
