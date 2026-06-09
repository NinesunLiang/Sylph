#!/usr/bin/env python3
"""
flywheel-report.py — SessionStart — 读取飞轮日志，生成 30 天频率摘要注入会话

Role: 读取飞轮日志，生成 30 天频率摘要注入会话
"""

import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, hc_get, flywheel_event, output_continue,
    HOME_DIR,
)

REPORT_DIR = HOME_DIR / "flywheel-reports"


def main():
    if not hc_enabled("skill_flywheel"):
        output_continue()
        return

    flywheel_log = HOME_DIR / ".claude" / "flywheel.log"

    # AC-17.1: Empty log guard
    if not flywheel_log.exists() or flywheel_log.stat().st_size == 0:
        output_continue()
        return

    # AC-17.2: Ensure report directory exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Read configurable values from harness.yaml
    report_window = int(hc_get("flywheel_report.report_window_days", "30"))
    default_snooze = int(hc_get("flywheel_report.default_snooze_days", "7"))
    p0_threshold = int(hc_get("flywheel_report.p0_warning_threshold", "5"))

    today = date.today()
    today_str = today.isoformat()
    cutoff = (today - timedelta(days=report_window)).isoformat()

    # Parse flywheel.log: date,event,severity,project
    counts = defaultdict(int)
    severity_map = {}
    project_map = defaultdict(set)
    latest_date = {}
    total = 0

    try:
        with open(str(flywheel_log), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                d, evt = parts[0], parts[1]
                sev = parts[2] if len(parts) > 2 else ""
                proj = parts[3] if len(parts) > 3 else ""
                if d >= cutoff:
                    counts[evt] += 1
                    severity_map[evt] = sev
                    if proj:
                        project_map[evt].add(proj)
                if evt not in latest_date or d > latest_date[evt]:
                    latest_date[evt] = d
                total += 1
    except Exception:
        output_continue()
        return

    if total < 3:
        output_continue()
        return

    ranked = sorted(counts.items(), key=lambda x: -x[1])

    # Read ack log
    ack_log = HOME_DIR / ".claude" / "flywheel-ack.log"
    ack_resolved = {}
    ack_snooze = {}
    ack_ignore = set()

    if ack_log.exists():
        try:
            with open(str(ack_log), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) < 3:
                        continue
                    ack_d, ack_evt, action = parts[0], parts[1], parts[2]
                    if action == "resolved":
                        if ack_evt not in ack_resolved or ack_d > ack_resolved[ack_evt]:
                            ack_resolved[ack_evt] = ack_d
                    elif action.startswith("snooze"):
                        days = int(action[6:]) if action[6:].isdigit() else default_snooze
                        snooze_until = (date.fromisoformat(ack_d) + timedelta(days=days)).isoformat()
                        if ack_evt not in ack_snooze or snooze_until > ack_snooze[ack_evt]:
                            ack_snooze[ack_evt] = snooze_until
                    elif action == "ignore":
                        ack_ignore.add(ack_evt)
        except Exception:
            pass

    def is_suppressed(evt):
        if evt in ack_ignore:
            return True
        if evt in ack_snooze and today_str <= ack_snooze[evt]:
            return True
        if evt in ack_resolved:
            if latest_date.get(evt, "") <= ack_resolved[evt]:
                return True
        return False

    # Warnings: P0 events with count > threshold and not suppressed
    warnings = [
        (evt, cnt) for evt, cnt in ranked
        if severity_map.get(evt) == "P0" and cnt > p0_threshold and not is_suppressed(evt)
    ]

    if not warnings:
        output_continue()
        return

    # AC-17.2: Write date-stamped report
    report_path = REPORT_DIR / f"flywheel-report-{today_str}.md"
    try:
        report_lines = [
            "# Flywheel Report",
            f"**Date**: {today_str}",
            "",
            "## P0 Alerts",
        ]
        for evt, cnt in warnings[:5]:
            projs = ", ".join(sorted(project_map[evt]))[:50] if project_map[evt] else "-"
            report_lines.append(f"- **{evt}**: {cnt} occurrences (P0, projects: {projs})")
        report_lines.append("")
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
    except Exception:
        pass

    # AC-17.4: Desktop notification for P0 events
    p0_summary = "; ".join(f"{evt}x{cnt}" for evt, cnt in warnings[:3])
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{p0_summary}" with title "Flywheel P0 Alert"'],
            capture_output=True, timeout=5,
        )
    except Exception:
        try:
            subprocess.run(["notify-send", "Flywheel P0 Alert", p0_summary], capture_output=True, timeout=5)
        except Exception:
            pass

    # AI context injection (stdout)
    project_count = len(set(proj for _, _ in warnings for proj in project_map.get(_, [])))
    print(f"[Flywheel] P0 alerts this month: {len(warnings)} events across {project_count} projects")
    if warnings:
        print(f"  top: {warnings[0]}")
        if len(warnings) > 1:
            print(f"  also: {warnings[1]}")
    print("---")

    flywheel_event("flywheel_report", "report_generated", "P2", "30d_summary")
    output_continue()


if __name__ == "__main__":
    main()
