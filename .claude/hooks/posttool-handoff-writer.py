#!/usr/bin/env python3
"""
posttool-handoff-writer.py — PostToolUse:TaskUpdate — 每次 Task 完成后写 handoff

Role: 每次 Task 完成后写 handoff（E8 上下文遗忘防御）
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    extract_tool_input_status, output_continue,
    PROJECT_ROOT, STATE_DIR,
)


def main():
    if not hc_enabled("posttool_handoff_writer"):
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Only respond to TaskUpdate completed
    status = extract_tool_input_status(input_str)
    if status != "completed":
        output_continue()
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handoff_file = STATE_DIR / "session-handoff.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Collect state
    branch = "unknown"
    modified = ""
    diff_stat = ""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "branch", "--show-current"],
            capture_output=True, text=True, timeout=10,
        )
        branch = result.stdout.strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        modified = ";".join(result.stdout.strip().split("\n")[:15])
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
        )
        diff_stat = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Active RPE context
    active_feature = ""
    active_task = ""
    rpe_dir = PROJECT_ROOT / "rpe"
    if rpe_dir.exists():
        try:
            result = subprocess.run(
                ["find", str(rpe_dir), "-name", "executor.md", "-type", "f"],
                capture_output=True, text=True, timeout=10,
            )
            files = [f for f in result.stdout.strip().split("\n") if f]
            if files:
                # Get latest by sorting
                files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
                latest = files[0]
                rel_part = latest.replace(str(rpe_dir) + "/", "").replace("/executor.md", "")
                active_feature = rel_part
                try:
                    with open(latest, encoding="utf-8") as f:
                        for line in f:
                            m = re.search(r'##.*🔄|## Step.*进行中|当前任务', line)
                            if m:
                                active_task = line.strip().lstrip("#").strip()
                                break
                except OSError:
                    pass
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Error DNA summary
    error_summary = "not available"
    dna_file = STATE_DIR / "error-dna.json"
    if dna_file.exists():
        try:
            with open(str(dna_file), encoding="utf-8") as f:
                dna = json.load(f)
            sigs = dna.get("error_signatures", {})
            active = [(k, v) for k, v in sigs.items() if v.get("status") != "fixed"]
            error_summary = f"{len(active)} active errors" if active else "0 active errors"
        except (json.JSONDecodeError, OSError):
            pass

    # Token tracking info
    ctx_info = "not available"
    index_file = STATE_DIR / "token-tracking-index.json"
    if index_file.exists():
        try:
            with open(str(index_file), encoding="utf-8") as f:
                d = json.load(f)
            usage = d.get("usage", 0)
            limit = d.get("limit", 200000)
            pct = int(usage * 100 / limit) if limit > 0 else 0
            ctx_info = f"context: {pct}% ({usage}/{limit})"
        except (json.JSONDecodeError, OSError):
            pass

    # Lessons from claude-next.md
    lessons = ""
    claude_next = PROJECT_ROOT / ".claude" / "claude-next.md"
    if claude_next.exists():
        try:
            content = claude_next.read_text(encoding="utf-8")
            today_entries = re.findall(r'^### \[(.+?)\] (.+)', content, re.MULTILINE)
            for t in today_entries[:5]:
                lessons += f"- [{t[0]}] {t[1]}\n"
        except OSError:
            pass

    # Contradictions
    contradictions = ""
    contradiction_log = STATE_DIR / "edit-churn-log.jsonl"
    if contradiction_log.exists():
        try:
            with open(str(contradiction_log), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("type") == "revert":
                            contradictions += f"- revert: {rec.get('file', '')[:60]}\n"
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass

    # Check autonomous mode
    is_autonomous = False
    for marker in ["tokens/autonomous.active", "tokens/lx-ghost.json", "tokens/lx-goal.json"]:
        if (STATE_DIR / marker).exists():
            is_autonomous = True
            break

    # Write structured handoff
    auto_note = "_mode: autonomous (ghost/goal exit report already shown)_\n" if is_autonomous else ""
    lessons_block = lessons if lessons else "- Lessons: (none)\n"
    contradictions_block = f"- Contradictions:\n{contradictions}" if contradictions else ""

    handoff_content = (
        f"# Session Exit Report — {timestamp}\n"
        f"{auto_note}"
        f"\n"
        f"## 会话摘要\n"
        f"- Branch: {branch}\n"
        f"- Active Feature: {active_feature or 'none'}\n"
        f"- Active Task: {active_task or 'none'}\n"
        f"- Token: {ctx_info}\n"
        f"\n"
        f"## 修改文件\n"
        f"- Modified: {modified or 'none'}\n"
        f"- Git diff: {diff_stat or 'clean'}\n"
        f"\n"
        f"## 待办项\n"
        f"- Errors: {error_summary}\n"
        f"{lessons_block}"
        f"{contradictions_block}"
    )

    try:
        handoff_file.write_text(handoff_content, encoding="utf-8")
    except OSError:
        pass

    output_continue()
    flywheel_event("posttool_handoff_writer", "handoff_written", "P2")


if __name__ == "__main__":
    main()
