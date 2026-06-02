#!/usr/bin/env bash
# pretool-workflow-gate.sh — 工作流阶段门禁
# 注册: PreToolUse:Edit|Write|Bash
# 阻断超越当前阶段的编辑/写入/执行操作
#
# 读取 workflow-state.json，根据当前 stage 决定是否放行。
# 铁律 #8: 过程性→直接执行，抉择性→哲学裁决。此 hook 是过程性阻断。

set -u

STATE_FILE="$HOME/Desktop/Sylph/Carror_OS/.claude/state/workflow-state.json"

# Gate: 状态文件不存在 → 无活跃工作流 → 放行
if [ ! -f "$STATE_FILE" ]; then
  echo "continue"
  exit 0
fi

# Gate: 解析状态
if ! command -v python3 &>/dev/null; then
  echo "continue"
  exit 0
fi

ACTIVE=$(python3 -c "
import json,sys
try:
  with open('$STATE_FILE') as f:
    s = json.load(f)
  print(s.get('active', False))
except:
  print(False)
" 2>/dev/null)

if [ "$ACTIVE" != "True" ]; then
  echo "continue"
  exit 0
fi

STAGE=$(python3 -c "
import json
with open('$STATE_FILE') as f:
  s = json.load(f)
print(s.get('stage', 'idle'))
" 2>/dev/null)

TASK_LEVEL=$(python3 -c "
import json
with open('$STATE_FILE') as f:
  s = json.load(f)
print(s.get('task_level', 'L1'))
" 2>/dev/null)

# L1: 跳过工作流约束
if [ "$TASK_LEVEL" = "L1" ]; then
  echo "continue"
  exit 0
fi

# 获取被操作的文件路径
FILE_PATH="${1:-}"
TOOL_NAME="${2:-}"

# ──────── Stage 依赖阻断 ────────

# Stage 0 (idle): 无约束——人类还在设定
if [ "$STAGE" = "idle" ]; then
  echo "continue"
  exit 0
fi

# Stage 1 (planning): 禁止 Edit/Write/Bash——方案阶段，不允许执行
# 例外: Read/Grep 不受此 hook 影响（此 hook 只注册在 Edit|Write|Bash)
if [ "$STAGE" = "planning" ] || [ "$STAGE" = "gate1" ]; then
  cat >&2 <<EOF
========================================
[WORKFLOW GATE] BLOCKED
========================================
当前阶段: $STAGE
操作: $TOOL_NAME → $FILE_PATH
原因: Gate 1 未通过。方案阶段不允许编辑/写入/执行。

下一步: 请 Boss 在 Gate 1 确认方案后，手动启动 Oracle 审查。
========================================
EOF
  exit 2
fi

# Stage 2 (executing): 允许执行，但受约束矩阵限制
if [ "$STAGE" = "executing" ]; then
  # 检查约束矩阵
  ALLOWED=$(python3 -c "
import json
with open('$STATE_FILE') as f:
  s = json.load(f)
allowed = s.get('constraint_matrix', {}).get('allowed_files', [])
for pattern in allowed:
  if '$FILE_PATH'.startswith(pattern.rstrip('/')):
    print('MATCH')
    break
" 2>/dev/null)

  if [ "$ALLOWED" != "MATCH" ] && [ -n "$FILE_PATH" ] && [ "${ALLOWED:-}" != "" ]; then
    cat >&2 <<EOF
========================================
[WORKFLOW GATE] BLOCKED
========================================
当前阶段: executing
文件: $FILE_PATH
原因: 不在约束矩阵范围内。

约束矩阵允许的文件范围:
$(python3 -c "import json; s=json.load(open('$STATE_FILE')); print('\n'.join('  - '+p for p in s.get('constraint_matrix',{}).get('allowed_files',[])))" 2>/dev/null)

说明: 如需扩展范围，请在 Gate 1 修改方案。
========================================
EOF
    exit 2
  fi

  echo "continue"
  exit 0
fi

# Stage gate2/gate3: 等待人类确认，禁止执行
if [ "$STAGE" = "gate2" ] || [ "$STAGE" = "gate3" ]; then
  cat >&2 <<EOF
========================================
[WORKFLOW GATE] BLOCKED
========================================
当前阶段: $STAGE
原因: 等待人类确认 Gate 审核结果。

下一步: 请 Boss 审执行报告后手动启动双法官验收。
========================================
EOF
  exit 2
fi

# Stage 3 (closed): 已闭环，禁止任何操作
if [ "$STAGE" = "closed" ]; then
  echo "continue"
  exit 0
fi

# 默认放行
echo "continue"
exit 0
