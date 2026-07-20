#!/usr/bin/env python3
"""session-inject.py — workflow-standard/hooks — 会话启动时注入工作流上下文
注册: SessionStart
抗 compact: 每次 SessionStart（含 compact 后重启）自动重新注入
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'hooks'))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue


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
    if not hc_enabled("session_inject"):
        sys.exit(0)

    state_file = _find_state_file()
    if state_file is None:
        sys.exit(0)

    try:
        with open(state_file, 'r') as f:
            s = json.load(f)
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    active = s.get('active', False)
    if not active:
        sys.exit(0)

    task = s.get('task_id', '?')
    level = s.get('task_level', '?')
    stage = s.get('stage', '?')
    st = s.get('stages', {})

    # Stage map
    stage_names = {
        'stage0_completed': 'S0-Setup',
        'stage1_completed': 'S1-Plan',
        'gate1_passed': 'G1-OK',
        'gate2_passed': 'G2-OK',
        'gate3_passed': 'G3-Close'
    }
    done = [v for k, v in stage_names.items() if st.get(k)]

    cps = [c['name'] for c in s.get('checkpoints', []) if c.get('status') == 'completed']
    blocked = s.get('blocked_items', [])
    allowed = s.get('constraint_matrix', {}).get('allowed_files', [])
    roi = s.get('roi_estimate', {})

    # Build output lines
    lines = []
    lines.append('══════════════════════ ACTIVE WORKFLOW ══════════════════════')
    lines.append(f'Task: {task}  |  Level: {level}  |  Stage: {stage}')
    lines.append(f'Progress: {" → ".join(done) if done else "none"}')
    if cps:
        lines.append(f'Done: {", ".join(cps)}')
    if blocked:
        lines.append(f'BLOCKED: {", ".join(blocked)}')
    if allowed:
        lines.append(f'Scope: {len(allowed)} file patterns')
    lines.append(f'ROI est: {roi.get("time_minutes", "?")}min / {roi.get("files_count", "?")} files')

    # Stage-specific protocol
    if stage in ('planning', 'gate1'):
        lines.append('⚠️  READ ONLY — Gate 1 not yet passed')
    elif stage == 'executing':
        lines.append('▶️  Execute freely within constraint matrix')
    elif stage in ('gate2', 'gate3'):
        lines.append('⏸️  PAUSED — awaiting human review')
    lines.append('═══════════════════════════════════════════════════════════════')

    for l in lines:
        print(l, file=sys.stderr, flush=True)

    flywheel_event("workflow_session", "injected", "L0", f"stage={stage}")
    sys.exit(0)


if __name__ == '__main__':
    main()
