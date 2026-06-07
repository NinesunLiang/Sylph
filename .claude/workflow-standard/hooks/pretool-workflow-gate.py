#!/usr/bin/env python3
"""pretool-workflow-gate.py — workflow-standard/hooks — 工作流阶段门禁
注册: PreToolUse:Edit|Write|Bash
阻断超越当前阶段的编辑/写入/执行操作
铁律 #8: 过程性阻断
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
    if not hc_enabled("pretool_workflow_gate"):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    state_file = _find_state_file()
    if state_file is None:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    try:
        with open(state_file, 'r') as f:
            s = json.load(f)
    except (json.JSONDecodeError, OSError):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    active = s.get('active', False)
    if not active:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    stage = s.get('stage', 'idle')
    level = s.get('task_level', 'L1')

    # L1: skip all gates
    if level == 'L1':
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # Extract file_path and tool_name from CLI args (matches bash ${1:-} and ${2:-})
    file_path = sys.argv[1] if len(sys.argv) > 1 else ''
    tool_name = sys.argv[2] if len(sys.argv) > 2 else ''

    # Planning / Gate 1: block all edits/writes/bash
    if stage in ('planning', 'gate1'):
        msg = (
            f"[WORKFLOW GATE] BLOCKED\n"
            f"当前阶段: {stage} → Gate 1 未通过\n"
            f"方案阶段不允许编辑/写入/执行。请 Boss 在 Gate 1 确认方案。\n"
        )
        print(msg, file=sys.stderr, flush=True)
        flywheel_event("workflow_gate", "blocked", "P1", stage)
        print(json.dumps({'continue': False, 'reason': f'Gate blocked: stage={stage}'}))
        sys.exit(2)

    # Executing: check file_path against constraint matrix
    if stage == 'executing' and file_path:
        allowed = s.get('constraint_matrix', {}).get('allowed_files', [])
        # If no allowed patterns defined (empty list), no restriction
        if allowed:
            is_allowed = False
            for pattern in allowed:
                pattern_clean = pattern.rstrip('/')
                if file_path.startswith(pattern_clean):
                    is_allowed = True
                    break
            if not is_allowed:
                allowed_list = '\n'.join(f'  - {p}' for p in allowed)
                msg = (
                    f"[WORKFLOW GATE] BLOCKED\n"
                    f"文件: {file_path} — 不在约束矩阵范围内\n"
                    f"{allowed_list}\n"
                )
                print(msg, file=sys.stderr, flush=True)
                flywheel_event("workflow_gate", "blocked", "P1", f"file_out_of_scope:{file_path}")
                print(json.dumps({'continue': False, 'reason': f'File {file_path} not in constraint matrix'}))
                sys.exit(2)

    # Gate 2 / Gate 3: paused
    if stage in ('gate2', 'gate3'):
        print(f"[WORKFLOW GATE] PAUSED: 等待 {stage} 人类确认", file=sys.stderr, flush=True)
        flywheel_event("workflow_gate", "paused", "P1", stage)
        print(json.dumps({'continue': False, 'reason': f'Paused at {stage}'}))
        sys.exit(2)

    # Pass
    print(json.dumps({'continue': True}))
    sys.exit(0)


if __name__ == '__main__':
    main()
