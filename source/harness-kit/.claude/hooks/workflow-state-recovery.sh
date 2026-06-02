#!/usr/bin/env bash
# workflow-state-recovery.sh — 工作流状态腐蚀恢复
# 注册: SessionStart（在 sessionstart-workflow-inject.sh 之前运行）
#
# 检测 workflow-state.json 是否可解析。
# 若损坏: 备份损坏文件 + 重置为 inactive。
# 若 Gate 超时: 转入 PAUSED 状态。

set -u

STATE_FILE="$HOME/Desktop/Sylph/Carror_OS/.claude/state/workflow-state.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

# ──────── 腐蚀检测 ────────
if ! python3 -c "import json; json.load(open('$STATE_FILE'))" 2>/dev/null; then
  TIMESTAMP=$(date +%Y%m%d-%H%M%S)
  CORRUPTED_BACKUP="$HOME/Desktop/Sylph/Carror_OS/.claude/state/workflow-state.corrupted.$TIMESTAMP.json"

  cp "$STATE_FILE" "$CORRUPTED_BACKUP" 2>/dev/null

  # 重置为 inactive
  python3 -c "
import json, os
reset = {
  'active': False,
  'task_id': None,
  'task_level': None,
  'stage': 'idle',
  'stages': {},
  'constraint_matrix': {'allowed_files': [], 'forbidden_patterns': [], 'max_files': 20},
  'checkpoints': [],
  'blocked_items': [],
  'roi_estimate': {},
  'roi_actual': {},
  'audit_log': [{
    'event': 'corruption_recovery',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'backup': '$CORRUPTED_BACKUP',
    'detail': 'workflow-state.json was corrupted. Reset to inactive. Corrupted backup saved.'
  }]
}
with open('$STATE_FILE', 'w') as f:
  json.dump(reset, f, indent=2, ensure_ascii=False)
"

  cat >&2 <<EOF
========================================
[WORKFLOW RECOVERY] State file corrupted
========================================
已备份损坏文件: $CORRUPTED_BACKUP
已重置 workflow-state.json 为 inactive。

原因: JSON 解析失败。
影响: 活跃工作流已丢失。需 Boss 重新启动工作流。
========================================
EOF
  exit 0
fi

# ──────── Gate 超时检测 ────────
if ! command -v python3 &>/dev/null; then
  exit 0
fi

python3 -c "
import json, os, sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
state_file = '$STATE_FILE'

with open(state_file) as f:
    s = json.load(f)

if not s.get('active'):
    sys.exit(0)

stage = s.get('stage', 'idle')
if stage not in ('gate1', 'gate2', 'gate3'):
    sys.exit(0)

# 获取最后一条 audit log
audit = s.get('audit_log', [])
if not audit:
    sys.exit(0)

last_event = audit[-1]
last_ts = last_event.get('timestamp', '')
if not last_ts:
    sys.exit(0)

try:
    last_time = datetime.fromisoformat(last_ts)
except:
    sys.exit(0)

elapsed_minutes = (datetime.now(CST) - last_time).total_seconds() / 60

# Gate 超时阈值: 60 分钟
timeout_map = s.get('gate_timeouts', {})
threshold = timeout_map.get(f'{stage}_timeout_minutes', 60)

if elapsed_minutes > threshold:
    s['active'] = False
    s['stage'] = 'idle'
    s['audit_log'].append({
        'event': 'gate_timeout',
        'stage': stage,
        'elapsed_minutes': round(elapsed_minutes, 1),
        'threshold_minutes': threshold,
        'detail': f'Gate {stage[-1]} timed out after {elapsed_minutes:.0f}min. Workflow deactivated.',
        'timestamp': datetime.now(CST).isoformat()
    })
    
    os.rename(state_file, state_file + '.bak')
    with open(state_file, 'w') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    
    print(f'GATE_TIMEOUT:{stage}:{elapsed_minutes:.0f}min', file=sys.stderr)
" 2>/dev/null

exit 0
