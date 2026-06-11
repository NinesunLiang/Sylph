#!/usr/bin/env python3
"""
posttool-checkpoint.py — PostToolUse:TaskUpdate + Stop — 工作流闭环：所有工作流结束时输出结构化 checkpoint

Role: TaskUpdate(completed) / Stop 时自动生成过程摘要 + 决策记录 + 待处理 + 方向指引
覆盖: RPE / TODO / Task-Spec (TaskUpdate) + Goal / Ghost (Stop)
哲学 #5(以人为本): 人类拿到清晰的收尾报告，不需要自行推断下一步
哲学 #4(验证): 每个结论附带证据来源
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    extract_event_name, extract_tool_input_status, output_continue,
    output_additional_context, sanitize_text,
    PROJECT_ROOT, STATE_DIR, HOME_DIR,
)


def main():
    if not hc_enabled("posttool_checkpoint"):
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    event = extract_event_name(input_str)

    trigger = ""
    task_desc = ""

    # Parse input data
    try:
        data = json.loads(input_str)
    except (json.JSONDecodeError, Exception):
        output_continue()
        return

    # TaskUpdate path: only completed status
    if event == "PostToolUse" or not event:
        status = extract_tool_input_status(input_str)
        if status != "completed":
            output_continue()
            return
        trigger = "TaskUpdate(completed)"
        ti = data.get("tool_input", {})
        task_desc = (ti.get("description") or ti.get("subject") or "")[:200]
    elif event == "Stop":
        trigger = "Stop"
    else:
        output_continue()
        return

    # Collect state data
    handoff_file = STATE_DIR / "session-handoff.md"
    todo_file = STATE_DIR / "todo-queue.md"
    signals_file = STATE_DIR / "error-signals.jsonl"
    budget_file = STATE_DIR / "retry-budget.json"

    # Recent decisions from handoff
    recent_decisions = ""
    if handoff_file.exists():
        try:
            lines = handoff_file.read_text(encoding="utf-8").split("\n")
            table_lines = [l for l in lines if re.match(r'^\|.*\|.*\|', l)]
            recent_decisions = "\n".join(table_lines[-3:])
        except OSError:
            pass

    # Open TODOs count
    open_todos = "0"
    if todo_file.exists():
        try:
            todos = todo_file.read_text(encoding="utf-8").split("\n")
            open_todos = str(sum(1 for l in todos if re.match(r'^\[ \]', l)))
        except OSError:
            pass

    # Error count
    error_count = "0"
    if signals_file.exists():
        try:
            with open(str(signals_file), encoding="utf-8") as f:
                error_count = str(sum(1 for _ in f))
        except OSError:
            pass

    # Retry stats
    retry_active = 0
    if budget_file.exists():
        try:
            with open(str(budget_file), encoding="utf-8") as f:
                budget_data = json.load(f)
            sigs = budget_data.get("signatures", {})
            retry_active = sum(1 for v in sigs.values() if v.get("retry_count", 0) >= 3)
        except (json.JSONDecodeError, OSError):
            pass

    # Gate blocks from flywheel log
    flywheel_log = HOME_DIR / ".claude" / "flywheel.log"
    gate_blocks = 0
    oracle_blocks = 0
    if flywheel_log.exists():
        try:
            content = flywheel_log.read_text(encoding="utf-8", errors="replace")
            gate_blocks = len(re.findall(r'oracle_gate.*blocked|permission_gate.*blocked', content))
            oracle_blocks = len(re.findall(r'oracle_gate.*blocked', content))
        except OSError:
            pass

    # Uncommitted files
    uncommitted = "0"
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        uncommitted = str(len([l for l in result.stdout.split("\n") if l.strip()]))
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Build checkpoint
    task_label = task_desc if task_desc else "未命名任务"
    checkpoint = (
        f"╔══════════════════════════════════════════╗\n"
        f"║  📋 Checkpoint — 工作流收尾              ║\n"
        f"╠══════════════════════════════════════════╣\n"
        f"║  任务: {task_label}\n"
        f"╠══════════════════════════════════════════╣\n"
        f"║  状态: ✅ 完成\n"
        f"║  错误: {error_count} 条信号 | 重试上限: {retry_active} 个签名\n"
        f"║  未提交: {uncommitted} 个文件 | 待办: {open_todos} 项\n"
        f"║  Gate阻断: oracle-gate ×{oracle_blocks} | 总计 ×{gate_blocks}\n"
        f"╠══════════════════════════════════════════╣\n"
        f"║  📌 下一步建议:\n"
        f"║  · 有未提交文件 → 确认后 git commit\n"
        f"║  · 有待办项 → /lx-todo 继续处理\n"
        f"║  · 有重试上限 → 检查是否需要人工介入\n"
        f"║  · 全清 → 开启新任务或结束会话\n"
        f"╚══════════════════════════════════════════╝\n"
    )

    # Human-visible summary (stderr)
    print(f"📋 [Checkpoint] {task_label} — ✅ 完成 | 未提交:{uncommitted} | 待办:{open_todos}", file=sys.stderr)
    print("   📌 下一步: 有未提交→commit | 有待办→/lx-todo | 全清→新任务", file=sys.stderr)

    # Stop: just output continue. PostToolUse: inject additionalContext
    if event == "Stop":
        output_continue()
    else:
        output_additional_context(checkpoint, "PostToolUse")

    flywheel_event("posttool_checkpoint", "generated", "P2")


if __name__ == "__main__":
    main()
