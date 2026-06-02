#!/usr/bin/env bash
# posttool-workflow-checkpoint.sh — 工作流 checkpoint 状态推进
# 注册: PostToolUse:TaskUpdate
# 在 AI 报告子任务完成时自动更新 workflow-state.json 的 checkpoint 列表

set -u

STATE_FILE="$HOME/Desktop/Sylph/Carror_OS/.claude/state/workflow-state.json"

# Gate: 状态文件不存在 → 无活跃工作流 → 跳过
if [ ! -f "$STATE_FILE" ]; then
  echo "continue"
  exit 0
fi

if ! command -v python3 &>/dev/null; then
  echo "continue"
  exit 0
fi

ACTIVE=$(python3 -c "import json; s=json.load(open('$STATE_FILE')); print(s.get('active',False))" 2>/dev/null)

if [ "$ACTIVE" != "True" ]; then
  echo "continue"
  exit 0
fi

STAGE=$(python3 -c "import json; s=json.load(open('$STATE_FILE')); print(s.get('stage','idle'))" 2>/dev/null)

# 只在 executing 阶段推进 checkpoint
if [ "$STAGE" != "executing" ]; then
  echo "continue"
  exit 0
fi

# 从 stdin 或参数提取 checkpoint 信息
# TaskUpdate 的 description 中含有区域完成标记
DESCRIPTION="${1:-}"
if [ -z "$DESCRIPTION" ]; then
  echo "continue"
  exit 0
fi

# 检测 checkpoint 模式: "[CHECKPOINT: region-name]"
CHECKPOINT_NAME=$(echo "$DESCRIPTION" | grep -oP '\[CHECKPOINT:\s*\K[^\]]+' | head -1)

if [ -z "$CHECKPOINT_NAME" ]; then
  # 尝试检测 "完成" 模式
  CHECKPOINT_NAME=$(echo "$DESCRIPTION" | grep -oP '(?:完成|done|completed)\s*[：:]\s*\K\S+' | head -1)
fi

if [ -z "$CHECKPOINT_NAME" ]; then
  echo "continue"
  exit 0
fi

# 推进状态
python3 -c "
import json, sys, os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
state_file = '$STATE_FILE'
checkpoint_name = '''$CHECKPOINT_NAME'''

with open(state_file) as f:
    s = json.load(f)

# 检查是否已存在
existing = [c for c in s.get('checkpoints', []) if c.get('name') == checkpoint_name]
if existing:
    existing[0]['updated_at'] = datetime.now(CST).isoformat()
else:
    s.setdefault('checkpoints', []).append({
        'name': checkpoint_name,
        'status': 'completed',
        'completed_at': datetime.now(CST).isoformat()
    })

# 写回（保留格式，compact=False保证可读性）
os.rename(state_file, state_file + '.bak')
with open(state_file, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)
" 2>/dev/null

echo "continue"
exit 0
