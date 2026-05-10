#!/usr/bin/env python3
"""
flywheel_analytics.py — Compute per-skill usage analytics from flywheel.log
Detects skill deprecation (unused >30 days) for flywheel self-healing.
Output: JSON report to stdout and optional report_path.
"""
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
    print(summary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
