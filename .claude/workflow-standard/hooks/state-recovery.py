#!/usr/bin/env python3
"""state-recovery.py — workflow-standard/hooks — 状态腐蚀恢复 + Gate 超时检测
注册: SessionStart（在 session-inject 之前运行）
"""
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'hooks'))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue

CST = timezone(timedelta(hours=8))


def _find_state_file():
    """Find workflow-state.json: prefer local .claude/state/, fallback ~/.claude/state/"""
    local = Path(".claude/state/workflow-state.json")
    if local.is_file():
        return str(local.resolve())
    home = Path.home() / ".claude" / "state" / "workflow-state.json"
    if home.is_file():
        return str(home)
    return None


def main():
    if not hc_enabled("state_recovery"):
        sys.exit(0)

    state_file = _find_state_file()
    if state_file is None:
        sys.exit(0)

    # ─── 腐蚀检测 ───
    try:
        with open(state_file, 'r') as f:
            s = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        # JSON corrupted — backup and reset
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{state_file}.corrupted.{timestamp}"
        try:
            shutil.copy2(state_file, backup_path)
        except OSError:
            pass

        reset_state = {
            'active': False,
            'task_id': None,
            'task_level': None,
            'stage': 'idle',
            'stages': {},
            'constraint_matrix': {
                'allowed_files': [],
                'forbidden_patterns': [],
                'max_files': 20
            },
            'checkpoints': [],
            'blocked_items': [],
            'roi_estimate': {},
            'roi_actual': {},
            'audit_log': [{
                'event': 'corruption_recovery',
                'backup': backup_path,
                'detail': 'JSON corrupted — reset to inactive'
            }]
        }

        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(reset_state, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

        print(f"[WORKFLOW RECOVERY] 状态文件已损坏 — 已备份至 {backup_path} — 已重置为 inactive",
              file=sys.stderr, flush=True)
        flywheel_event("workflow_recovery", "corruption", "P0", "reset")
        sys.exit(0)

    # ─── Gate 超时检测 ───
    if not s.get('active'):
        sys.exit(0)

    stage = s.get('stage', 'idle')
    if stage not in ('gate1', 'gate2', 'gate3'):
        sys.exit(0)

    audit = s.get('audit_log', [])
    if not audit:
        sys.exit(0)

    last_ts = audit[-1].get('timestamp', '')
    if not last_ts:
        sys.exit(0)

    try:
        last_time = datetime.fromisoformat(last_ts)
    except (ValueError, TypeError):
        sys.exit(0)

    elapsed_min = (datetime.now(CST) - last_time).total_seconds() / 60
    threshold = s.get('gate_timeouts', {}).get(f'{stage}_timeout_minutes', 60)

    if elapsed_min > threshold:
        s['active'] = False
        s['stage'] = 'idle'
        s.setdefault('audit_log', []).append({
            'event': 'gate_timeout',
            'stage': stage,
            'elapsed_minutes': round(elapsed_min, 1),
            'detail': f'Gate timed out after {elapsed_min:.0f}min'
        })

        # Atomic write: backup then write
        try:
            os.rename(state_file, state_file + '.bak')
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

        print(f"GATE_TIMEOUT:{stage}:{elapsed_min:.0f}min", file=sys.stderr, flush=True)

    flywheel_event("workflow_recovery", "gate_timeout_check", "L1", "checked")
    sys.exit(0)


if __name__ == '__main__':
    main()
