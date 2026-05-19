#!/usr/bin/env bash
# flywheel-report.sh — SessionStart — 读取飞轮日志，生成 30 天频率摘要注入会话
# Role: 读取飞轮日志，生成 30 天频率摘要注入会话

source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_flywheel" || exit 0

FLYWHEEL="$HOME/.claude/flywheel.log"
REPORT_DIR="$HOME/.claude/flywheel-reports"

# AC-17.1: Explicit empty log guard (file missing or empty -> silent exit)
[ -s "$FLYWHEEL" ] || exit 0

# AC-17.2: Ensure persistent report directory exists
mkdir -p "$REPORT_DIR"

# Read configurable values from harness.yaml
FLYWHEEL_REPORT_WINDOW_DAYS=$(hc_get "flywheel_report.report_window_days" "30")
export FLYWHEEL_REPORT_WINDOW_DAYS
FLYWHEEL_DEFAULT_SNOOZE_DAYS=$(hc_get "flywheel_report.default_snooze_days" "7")
export FLYWHEEL_DEFAULT_SNOOZE_DAYS
FLYWHEEL_P0_WARNING_THRESHOLD=$(hc_get "flywheel_report.p0_warning_threshold" "5")
export FLYWHEEL_P0_WARNING_THRESHOLD

python3 - "$FLYWHEEL" "$REPORT_DIR" <<'PYEOF'
import sys, os, subprocess
from datetime import date, timedelta
from collections import defaultdict

log_path = sys.argv[1]
report_dir = sys.argv[2]
today = date.today()
today_str = today.isoformat()
report_window = int(os.environ.get('FLYWHEEL_REPORT_WINDOW_DAYS', '30'))
cutoff = (today - timedelta(days=report_window)).isoformat()

# Parse flywheel.log: date,event,severity,project
counts = defaultdict(int)
severity_map = {}
project_map = defaultdict(set)
latest_date = {}
total = 0

try:
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 3:
                continue
            d, evt = parts[0], parts[1]
            sev = parts[2] if len(parts) > 2 else ''
            proj = parts[3] if len(parts) > 3 else ''
            if d >= cutoff:
                counts[evt] += 1
                severity_map[evt] = sev
                if proj:
                    project_map[evt].add(proj)
            if evt not in latest_date or d > latest_date[evt]:
                latest_date[evt] = d
            total += 1
except Exception:
    sys.exit(0)

if total < 3:
    sys.exit(0)

ranked = sorted(counts.items(), key=lambda x: -x[1])

# Read ack log for resolved/snoozed/ignored events
ack_log = os.path.expanduser('~/.claude/flywheel-ack.log')
ack_resolved = {}
ack_snooze = {}
ack_ignore = set()
if os.path.exists(ack_log):
    try:
        with open(ack_log) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) < 3:
                    continue
                ack_d, ack_evt, action = parts[0], parts[1], parts[2]
                if action == 'resolved':
                    if ack_evt not in ack_resolved or ack_d > ack_resolved[ack_evt]:
                        ack_resolved[ack_evt] = ack_d
                elif action.startswith('snooze'):
                    default_snooze = int(os.environ.get('FLYWHEEL_DEFAULT_SNOOZE_DAYS', '7'))
                    days = int(action[6:]) if action[6:].isdigit() else default_snooze
                    snooze_until = (date.fromisoformat(ack_d) + timedelta(days=days)).isoformat()
                    if ack_evt not in ack_snooze or snooze_until > ack_snooze[ack_evt]:
                        ack_snooze[ack_evt] = snooze_until
                elif action == 'ignore':
                    ack_ignore.add(ack_evt)
    except Exception:
        pass

def is_suppressed(evt):
    if evt in ack_ignore:
        return True
    if evt in ack_snooze and today_str <= ack_snooze[evt]:
        return True
    if evt in ack_resolved:
        if latest_date.get(evt, '') <= ack_resolved[evt]:
            return True
    return False

# Warnings: P0 events with count > 5 and not suppressed
p0_threshold = int(os.environ.get('FLYWHEEL_P0_WARNING_THRESHOLD', '5'))
warnings = [(evt, cnt) for evt, cnt in ranked
            if severity_map.get(evt) == 'P0' and cnt > p0_threshold and not is_suppressed(evt)]

if not warnings:
    sys.exit(0)

# AC-17.2: Write date-stamped report to persistent directory
report_path = os.path.join(report_dir, f"flywheel-report-{today_str}.md")
try:
    report_lines = [
        "# Flywheel Report",
        f"**Date**: {today_str}",
        "",
        "## P0 Alerts",
    ]
    for evt, cnt in warnings[:5]:
        projs = ', '.join(sorted(project_map[evt]))[:50] if project_map[evt] else '-'
        report_lines.append(f"- **{evt}**: {cnt} occurrences (P0, projects: {projs})")
    report_lines.append("")
    with open(report_path, 'w') as f:
        f.write("\n".join(report_lines))
except Exception:
    pass

# AC-17.4: Desktop notification for P0 events
p0_summary = "; ".join(f"{evt}x{cnt}" for evt, cnt in warnings[:3])
try:
    subprocess.run(['osascript', '-e', 'display notification "' + p0_summary + '" with title "Flywheel P0 Alert"'], capture_output=True)
except Exception:
    try:
        subprocess.run(['notify-send', 'Flywheel P0 Alert', p0_summary], capture_output=True)
    except Exception:
        pass

# AI context injection (stdout) — flywheel alerts
project_count = len(set(proj for evt, cnt in warnings for proj in project_map.get(evt, [])))
print(f"[Flywheel] P0 alerts this month: {len(warnings)} events across {project_count} projects")
if warnings:
    print(f"  top: {warnings[0]}")
    if len(warnings) > 1:
        print(f"  also: {warnings[1]}")
print("---")
PYEOF
flywheel_event "flywheel_report" "report_generated" "P2" "30d_summary"
exit 0
