#!/usr/bin/env bash
# sessionstart-workflow-inject.sh — 工作流上下文注入
# 注册: SessionStart
# 在每次会话开始时检测活跃工作流，注入当前阶段+约束到 AI 上下文
#
# 输出: 若存在活跃工作流，通过 additionalContext 注入结构化摘要

set -u

STATE_FILE="$HOME/Desktop/Sylph/Carror_OS/.claude/state/workflow-state.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

if ! command -v python3 &>/dev/null; then
  exit 0
fi

ACTIVE=$(python3 -c "import json; s=json.load(open('$STATE_FILE')); print(s.get('active',False))" 2>/dev/null)

if [ "$ACTIVE" != "True" ]; then
  exit 0
fi

# 生成上下文注入摘要
python3 -c "
import json
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

with open('$STATE_FILE') as f:
    s = json.load(f)

task_id = s.get('task_id', 'unknown')
task_level = s.get('task_level', 'L1')
stage = s.get('stage', 'idle')
stages = s.get('stages', {})

checkpoints = s.get('checkpoints', [])
completed_cps = [c['name'] for c in checkpoints if c.get('status') == 'completed']
blocked_items = s.get('blocked_items', [])

constraint = s.get('constraint_matrix', {})
allowed = constraint.get('allowed_files', [])

roi = s.get('roi_estimate', {})
roi_actual = s.get('roi_actual', {})

# 构建结构化上下文
lines = []
lines.append('')
lines.append('══════════════════════════════════════════════')
lines.append('ACTIVE WORKFLOW STATE')
lines.append('══════════════════════════════════════════════')
lines.append(f'Task: {task_id} (Level: {task_level})')
lines.append(f'Current Stage: {stage}')
lines.append('')

# 阶段状态
stage_map = {
    'stage0_completed': 'Stage 0 - Human Setup',
    'stage1_completed': 'Stage 1 - Plan Generated',
    'gate1_passed': 'Gate 1 - Human+Oracle+Meta-Oracle',
    'stage2_completed': 'Stage 2 - Execution',
    'gate2_passed': 'Gate 2 - Human+Acceptance',
    'stage3_completed': 'Stage 3 - Final Report',
    'gate3_passed': 'Gate 3 - Closed',
}
lines.append('Stage Progress:')
for key, label in stage_map.items():
    done = '✅' if stages.get(key) else '⬜'
    lines.append(f'  {done} {label}')
lines.append('')

# Checkpoints
if completed_cps:
    lines.append(f'Completed Checkpoints ({len(completed_cps)}):')
    for cp in completed_cps:
        lines.append(f'  ✅ {cp}')
    lines.append('')

# Blocked
if blocked_items:
    lines.append(f'BLOCKED Items ({len(blocked_items)}):')
    for bi in blocked_items:
        lines.append(f'  ❌ {bi}')
    lines.append('')

# Constraint Matrix
if allowed:
    lines.append('Constraint Matrix (allowed file patterns):')
    for pattern in allowed:
        lines.append(f'  📁 {pattern}')
    lines.append('')

# ROI
lines.append(f'ROI Estimate: {roi.get(\"time_minutes\",\"?\")}min / {roi.get(\"files_count\",\"?\")} files')
if roi_actual.get('time_minutes'):
    lines.append(f'ROI Actual:   {roi_actual[\"time_minutes\"]}min / {roi_actual.get(\"files_count\",\"?\")} files')
    est = roi.get('time_minutes', 1)
    act = roi_actual.get('time_minutes', 1)
    if est > 0:
        dev = abs(act - est) / est
        if dev > 0.7:
            lines.append(f'⚠️  ROI Deviation: {dev*100:.0f}% — EXCEEDS 70% THRESHOLD')
lines.append('')

lines.append('Current Stage Protocol:')
if stage in ('idle', 'planning', 'gate1'):
    lines.append('  → READ ONLY. Do NOT edit/write/execute. Gate 1 must pass first.')
elif stage == 'executing':
    lines.append('  → Execute within constraint matrix. Respect checkpoint protocol.')
    lines.append('  → Each completed region must be checkpointed.')
    lines.append('  → 3 failures max per issue → BLOCKED.')
elif stage in ('gate2', 'gate3'):
    lines.append('  → PAUSED. Awaiting human gate review.')
lines.append('══════════════════════════════════════════════')
lines.append('')

print('\\n'.join(lines))
" 2>/dev/null

exit 0
