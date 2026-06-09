#!/usr/bin/env python3
"""
flywheel_analytics.py — Compute per-skill usage analytics from flywheel.log
Detects skill deprecation (unused >30 days) for flywheel self-healing.
Output: JSON report to stdout and optional report_path.
"""
import csv
import io
import json
import os
import sys
import time
from collections import defaultdict


def main():
    flywheel_log = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.expanduser('~/.claude/flywheel.log')
    report_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(flywheel_log):
        print(json.dumps({'error': 'flywheel.log not found', 'path': flywheel_log}))
        return 1

    skill_stats = defaultdict(lambda: {'count': 0, 'last_seen': 0, 'last_line': ''})
    current_ts = 0
    total_lines = 0

    with open(flywheel_log) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('# ts='):
                try:
                    for token in line.split():
                        if token.startswith('ts='):
                            current_ts = int(token.split('=')[1])
                except (IndexError, ValueError):
                    pass
            elif line.startswith('# '):
                pass  # other comment/metadata line
            else:
                total_lines += 1
                try:
                    entry = json.loads(line)
                    skill = entry.get('skill', entry.get('name', 'unknown'))
                    skill_stats[skill]['count'] += 1
                    if current_ts > skill_stats[skill]['last_seen']:
                        skill_stats[skill]['last_seen'] = current_ts
                        skill_stats[skill]['last_line'] = line[:200]
                except json.JSONDecodeError:
                    # CSV fallback: flywheel_event() writes "YYYY-MM-DD,event,severity,project"
                    # Parse CSV lines so hook events aren't silently dropped (DG-89: 92.9% were "parse errors")
                    try:
                        reader = csv.reader(io.StringIO(line))
                        row = next(reader)
                        if len(row) >= 2:
                            event_field = row[1]
                            # Extract category prefix (e.g. "posttool_claim_audit" from "posttool_claim_audit_blocked")
                            category = event_field.rsplit('_', 1)[0] if '_' in event_field else event_field
                            skill = 'hook:' + category
                            skill_stats[skill]['count'] += 1
                            if current_ts > skill_stats[skill]['last_seen']:
                                skill_stats[skill]['last_seen'] = current_ts
                                skill_stats[skill]['last_line'] = line[:200]
                    except Exception:
                        pass

    now = time.time()
    report = {
        'generated_ts': int(now),
        'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
        'total_log_lines': total_lines,
        'total_skill_events': sum(s['count'] for s in skill_stats.values()),
        'unique_skills': len(skill_stats),
        'skills': {},
    }

    for skill, stats in sorted(skill_stats.items(), key=lambda x: -x[1]['count']):
        days_since = ((now - stats['last_seen']) / 86400) if stats['last_seen'] > 0 else -1
        report['skills'][skill] = {
            'invocations': stats['count'],
            'last_seen_ts': stats['last_seen'],
            'days_since_last_use': round(days_since, 1),
            'deprecated': days_since > 30,
            'sample': stats['last_line'][:80],
        }

    deprecated = sorted(s for s, d in report['skills'].items() if d.get('deprecated'))
    report['deprecated_skills'] = deprecated

    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    # Short summary to stdout for hook logging
    summary = f'[flywheel] {report["total_skill_events"]} events across {report["unique_skills"]} skills'
    if deprecated:
        summary += f' | ⚠️ {len(deprecated)} unused: {deprecated}'

    # === I1 Mechanism Shadow Detection: 机制影壁 — hooks with flywheel_event but 0 events ===
    hooks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks')
    if os.path.isdir(hooks_dir):
        shadow_hooks = []
        for fname in sorted(os.listdir(hooks_dir)):
            if not fname.endswith('.sh'):
                continue
            fpath = os.path.join(hooks_dir, fname)
            with open(fpath) as hf:
                content = hf.read()
            if 'flywheel_event' not in content:
                continue
            # Derive event prefix from filename
            hook_key = fname.replace('.sh', '').replace('-', '_')
            # Check if any flywheel event matches this hook
            match_count = 0
            for skill, stats in skill_stats.items():
                if hook_key in skill or skill in hook_key:
                    match_count += stats['count']
            if match_count == 0:
                shadow_hooks.append(fname)

        if shadow_hooks:
            report['mechanism_shadows'] = shadow_hooks
            summary += f' | 🔍 {len(shadow_hooks)} shadows (flywheel code but 0 events)'
            print(f'[flywheel:shadow] Mechanism shadow detected: {", ".join(shadow_hooks)}', file=sys.stderr)

    print(summary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
