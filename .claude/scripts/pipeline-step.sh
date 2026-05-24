#!/usr/bin/env bash
# pipeline-step.sh — Lightweight pipeline step tracker for C3 流程结构化
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# Tracks current step in L3/L4 task pipeline across sessions.
# State file: .omc/state/pipeline-step.json
#
# Commands:
#   get       — Print current pipeline step
#   set N     — Set step to N (0-7)
#   advance   — Advance to next step
#   inject    — Inject pipeline context (for hooks)
#   status    — Full status with timestamp

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
STATE_FILE="$STATE_DIR/pipeline-step.json"
mkdir -p "$STATE_DIR"

STEPS=(
  "idle:当前无活跃任务"
  "列方案(澄清):澄清需求、列出候选方案"
  "细分最小可验证步骤:拆解为独立可验证子步骤"
  "实现:按 step 清单逐一实现，范围冻结"
  "Debug:收集错误按依赖排序修复，3 轮上限"
  "强证据验收:逐条核对完成标准"
  "Oracle专家复验:对抗性审查"
  "下一步(循环):全量回归→判断终止"
)

get_step() {
  if [ -f "$STATE_FILE" ]; then
    ${PYTHON_BIN:-python3} -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    print(d.get('step', 0))
except:
    print(0)
" 2>/dev/null || echo "0"
  else
    echo "0"
  fi
}

set_step() {
  local step="$1"
  ${PYTHON_BIN:-python3} -c "
import json, os, time
d = {'step': $step, 'updated': int(time.time())}
os.makedirs(os.path.dirname('$STATE_FILE'), exist_ok=True)
with open('$STATE_FILE', 'w') as f:
    json.dump(d, f)
" 2>/dev/null
}

case "${1:-get}" in
  get)
    step=$(get_step)
    echo "$step: ${STEPS[$step]%%:*}"
    ;;
  set)
    set_step "${2:-0}"
    echo "pipeline-step \u2192 ${2:-0}: ${STEPS[${2:-0}]%%:*}"
    ;;
  advance)
    cur=$(get_step)
    next=$((cur + 1))
    [ "$next" -gt 7 ] && next=7
    set_step "$next"
    echo "pipeline-step: ${STEPS[$cur]%%:*} \u2192 ${STEPS[$next]%%:*}"
    ;;
  inject)
    step=$(get_step)
    label="${STEPS[$step]%%:*}"
    desc="${STEPS[$step]#*:}"
    echo "[Pipeline Step ${step}/7] ${label} \u2014 ${desc}"
    ;;
  status)
    step=$(get_step)
    echo "Pipeline Step: ${step}/7"
    for i in "${!STEPS[@]}"; do
      marker=" "
      [ "$i" -eq "$step" ] && marker=">"
      echo "  $marker [$i] ${STEPS[$i]%%:*}"
    done
    if [ -f "$STATE_FILE" ]; then
      echo "Last updated: $(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$STATE_FILE')).get('updated','?'))" 2>/dev/null)"
    fi
    ;;
  *)
    echo "Usage: pipeline-step.sh {get|set N|advance|inject|status}"
    exit 1
    ;;
esac
