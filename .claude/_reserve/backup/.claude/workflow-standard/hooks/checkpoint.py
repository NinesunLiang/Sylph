#!/usr/bin/env python3
"""checkpoint.py — workflow-standard/hooks — 工作流 checkpoint 自动推进
注册: PostToolUse:TaskUpdate
依赖: workflow-state.json
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'hooks'))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue

# ── lx-plan 集成 ──
LX_PLAN = Path(__file__).resolve().parent.parent.parent / 'scripts' / 'lx-plan.py'

def _ensure_plan_system(state: dict, cp_name: str, description: str):
    """在 checkpoint 时自动初始化或更新任务文档体系"""
    try:
        task_name = state.get('task_name') or state.get('current_activity') or cp_name
        result = subprocess.run(
            [sys.executable, str(LX_PLAN), 'checkpoint', task_name, description],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            print(f"[plan] init warning: {result.stderr.strip()}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[plan] error: {e}", file=sys.stderr, flush=True)

CST = timezone(timedelta(hours=8))


def _find_state_file():
    """Find workflow-state.json: prefer local .claude/state/, fallback ~/.claude/state/"""
    # Local project state
    local = Path(".claude/state/workflow-state.json")
    if local.is_file():
        return str(local.resolve())
    # Home dir fallback
    home = Path.home() / ".claude" / "state" / "workflow-state.json"
    if home.is_file():
        return str(home)
    return None


def main():
    # hc_enabled check
    if not hc_enabled("checkpoint"):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    state_file = _find_state_file()
    if state_file is None:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # Read state
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    active = state.get('active', False)
    if not active:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    stage = state.get('stage', 'idle')
    if stage != 'executing':
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # Get description from first argument (matches bash ${1:-})
    description = sys.argv[1] if len(sys.argv) > 1 else ''

    if not description:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # Detect [CHECKPOINT: name]
    m = re.search(r'\[CHECKPOINT:\s*([^\]]+)\]', description)
    if not m:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    cp_name = m.group(1).strip()
    now_iso = datetime.now(CST).isoformat()

    # ── 自动创建/更新任务文档体系 ──
    _ensure_plan_system(state, cp_name, description)

    # Update checkpoints list
    checkpoints = state.setdefault('checkpoints', [])
    found = [c for c in checkpoints if c.get('name') == cp_name]
    if found:
        found[0]['updated_at'] = now_iso
    else:
        checkpoints.append({
            'name': cp_name,
            'status': 'completed',
            'completed_at': now_iso
        })

    # Atomic write: backup then write
    backup_path = state_file + '.bak'
    try:
        os.rename(state_file, backup_path)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[checkpoint] WARN: failed to write state file: {e}", file=sys.stderr, flush=True)

    flywheel_event("workflow_checkpoint", cp_name, "L1", "checkpointed")

    print(json.dumps({'continue': True}))
    sys.exit(0)


if __name__ == '__main__':
    main()
