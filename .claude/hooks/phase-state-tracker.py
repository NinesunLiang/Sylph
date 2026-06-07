#!/usr/bin/env python3
"""
phase-state-tracker.py — PostToolUse hook — 追踪当前任务所处的五阶段状态

Role: 检查 oracle-verdicts.md 24h 内是否有 ACCEPT → phase2_approved
      检查 git diff 是否有未提交修改 → phase3_executing
      写入 .omc/state/current-phase.json
哲学 #4(验证): 每个状态判断附带证据来源
哲学 #6(0信任): 不依赖缓存，每次执行实时检查
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input, output_continue,
    output_additional_context, hc_init, sanitize_text,
    PROJECT_ROOT, STATE_DIR,
)


def check_accept_24h(verdicts_file: Path, now_epoch: int) -> tuple:
    """Check oracle-verdicts.md for ACCEPT within 24h (86400s)."""
    window_sec = 86400
    if not verdicts_file.exists():
        return False, "", ""

    try:
        content = verdicts_file.read_text(encoding="utf-8")
    except OSError:
        return False, "", ""

    # Pattern: "## <timestamp>Z — Oracle-<mode> — approved|accepted"
    pattern = r'##\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+—\s+Oracle-[^\s]+\s+—\s+(approved|accepted)'
    matches = re.findall(pattern, content)

    for ts_str, status in matches:
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_epoch = int(dt.timestamp())
            if now_epoch - ts_epoch <= window_sec:
                return True, ts_str, status
        except (ValueError, TypeError):
            continue

    return False, "", ""


def main():
    if not hc_enabled("phase_state_tracker"):
        output_continue()
        return

    hc_init()

    # ── Define five phases ──
    # phase1_research, phase2_approved, phase3_executing, phase4_approved, phase5_report

    verdicts_file = STATE_DIR / "oracle-verdicts.md"
    phase_file = STATE_DIR / "current-phase.json"
    now_epoch = int(time.time())

    # ── Phase 2: Check oracle-verdicts.md 24h ACCEPT ──
    has_accept_24h, accept_ts, accept_status = check_accept_24h(verdicts_file, now_epoch)
    accept_evidence = ""
    if has_accept_24h:
        accept_evidence = f"oracle-verdicts.md:{accept_ts} — {accept_status}"

    # ── Phase 3: Check git diff for uncommitted changes ──
    has_uncommitted = False
    uncommitted_count = 0
    uncommitted_files = ""

    try:
        diff_out = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        staged_out = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()

        all_uncommitted = set()
        for f in (diff_out + "\n" + staged_out).split("\n"):
            f = f.strip()
            if f:
                all_uncommitted.add(f)

        if all_uncommitted:
            has_uncommitted = True
            uncommitted_count = len(all_uncommitted)
            uncommitted_files = ",".join(sorted(all_uncommitted)[:10])
    except (OSError, subprocess.TimeoutExpired):
        pass

    # ── Phase 4: Reuse Phase 2 check for result dual-review ──
    has_accept_result_24h = has_accept_24h
    accept_result_evidence = accept_evidence

    # ── Determine current phase ──
    current_phase = "phase1_research"
    phase_label = "Phase 1: 调研"
    phase_description = "调研阶段：正在阅读源码、分析现状"
    transition_evidence = ""

    if has_uncommitted:
        current_phase = "phase3_executing"
        phase_label = "Phase 3: 执行"
        phase_description = "执行阶段：有未提交的代码修改"
        transition_evidence = f"git diff: {uncommitted_count} 个文件未提交 ({uncommitted_files})"
    elif has_accept_24h:
        current_phase = "phase2_approved"
        phase_label = "Phase 2: 方案双审通过"
        phase_description = "方案已通过 Oracle+Meta-Oracle 双审，等待执行"
        transition_evidence = accept_evidence

    # ── Write current-phase.json ──
    data = {
        "current_phase": current_phase,
        "phase_label": phase_label,
        "phase_description": phase_description,
        "transition_evidence": transition_evidence,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(phase_file) + ".tmp." + str(os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.rename(tmp, str(phase_file))
    except OSError:
        pass

    # ── Summary to stderr ──
    ev = transition_evidence if transition_evidence else "无转换证据"
    print(f"📊 [Phase-State] {phase_label} — {ev}", file=sys.stderr)

    # ── Inject additionalContext ──
    ctx = (
        f"[Phase-State Tracker] 当前阶段: {phase_label}\n"
        f"- 描述: {phase_description}\n"
        f"- 转换证据: {transition_evidence or '无'}\n"
        f"- 未提交文件: {uncommitted_count} 个\n"
        f"- 文件: {phase_file}\n"
    )
    output_additional_context(ctx, "PostToolUse")
    flywheel_event("phase_state_tracker", "tracked", "P3")


if __name__ == "__main__":
    main()
