#!/bin/bash

# harness-kit:managed v1.3.0

# flywheel-report.sh — SessionStart Hook (RPE-017 enhanced)
# Reads ~/.claude/flywheel.log, generates 30-day frequency summary
# AC-17.1: Explicit empty log guard
# AC-17.2: Persistent .claude/flywheel-reports/ with date-stamped reports
# AC-17.3: Monthly trend comparison (printed to /dev/tty, not injected)
# AC-17.4: Desktop notification for P0 events (osascript/notify-send)

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
import sys, os
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

# /dev/tty terminal summary (visible to user, not injected into AI context)
compact = " | ".join(f"{evt}x{cnt}" for evt, cnt in warnings[:3])
try:
    with open('/dev/tty', 'w') as tty:
        tty.write(f"\r[Flywheel] {compact}\n")
except Exception:
    pass

# AC-17.3: Monthly trend comparison (printed to /dev/tty only)
this_month_cutoff = cutoff
prev_month_cutoff = (today - timedelta(days=60)).isoformat()
this_month_counts = defaultdict(int)
prev_month_counts = defaultdict(int)

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
            if sev != 'P0':
                continue
            if d >= this_month_cutoff:
                this_month_counts[evt] += 1
            elif d >= prev_month_cutoff:
                prev_month_counts[evt] += 1
except Exception:
    pass

trend_lines = []
all_events = set(list(this_month_counts.keys()) + list(prev_month_counts.keys()))
for evt in sorted(all_events):
    this_c = this_month_counts.get(evt, 0)
    prev_c = prev_month_counts.get(evt, 0)
    diff = this_c - prev_c
    if diff > 0:
        trend_lines.append(f"{evt}: {prev_c} -> {this_c} (+{diff})")
    elif diff < 0:
        trend_lines.append(f"{evt}: {prev_c} -> {this_c} ({diff})")
    elif this_c > 0:
        trend_lines.append(f"{evt}: {this_c} (no change)")

if trend_lines:
    try:
        with open('/dev/tty', 'w') as tty:
            tty.write("\n[Flywheel Trend] (this month vs last month)\n")
            for line in trend_lines[:5]:
                tty.write(f"  {line}\n")
    except Exception:
        pass

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
    if trend_lines:
        report_lines.append("")
        report_lines.append("## Monthly Trend (this vs last month)")
        for line in trend_lines[:5]:
            report_lines.append(f"- {line}")
    report_lines.append("")
    with open(report_path, 'w') as f:
        f.write("\n".join(report_lines))
except Exception:
    pass

# AC-17.4: Desktop notification for P0 events
p0_summary = "; ".join(f"{evt}x{cnt}" for evt, cnt in warnings[:3])
try:
    os.system('osascript -e \'display notification "' + p0_summary + '" with title "Flywheel P0 Alert"\'')
except Exception:
    try:
        os.system('notify-send "Flywheel P0 Alert" "' + p0_summary + '"')
    except Exception:
        pass

# AI context injection (stdout) — keep original format for AI parsing
print("[Flywheel 警报] 请用 Markdown 表格向用户展示以下高频 P0 问题，并询问处理方式：")
print("| 事件 | 本月次数 | 等级 | 项目 |")
print("|------|---------|------|------|")
for evt, cnt in warnings[:3]:
    projs = ', '.join(sorted(project_map[evt]))[:30] if project_map[evt] else '-'
    print(f"| {evt} | {cnt} 次 | P0 | {projs} |")
print("")
print("用户选择后 AI 执行（替换 EVENT/PROJECT 为实际值，DATE 为今日）：")
print(" 已解决 → Bash: echo 'DATE,EVENT,resolved,PROJECT' >> ~/.claude/flywheel-ack.log")
print(" 稍后7天 → Bash: echo 'DATE,EVENT,snooze7,PROJECT' >> ~/.claude/flywheel-ack.log")
print(" 永久静默 → Bash: echo 'DATE,EVENT,ignore,PROJECT' >> ~/.claude/flywheel-ack.log")
print("---")
PYEOF
