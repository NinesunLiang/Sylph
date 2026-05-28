#!/usr/bin/env bash
# pre-completion-gate.sh — PreToolUse:TaskUpdate — 前置完成门禁，阻止无证据的 completed 调用
# Role: 前置完成门禁，在 AI 调用 TaskUpdate(completed) 前阻止，减少浪费轮次

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pre_completion_gate" || { echo '{"continue": true}'; exit 0; }
set -f
INPUT=$(cat)

# 提取 status 字段
STATUS=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('status', ''))
except:
    pass" 2>/dev/null)

# 非 completed 状态放行
if [ "$STATUS" != "completed" ]; then
    echo '{"continue": true}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 自主/无人值守模式降级
if [ -f "$PROJECT_ROOT/.omc/state/tokens/autonomous.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/ghost-mode.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/tokens/lx-ghost.json" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/tokens/lx-goal.json" ]; then
    echo "[pre-completion-gate] 自主模式: 允许 completed（门禁降级）" >&2
    echo '{"continue": true}'
    exit 0
fi

# 检查证据文件 + completion-blocked 状态 (DG-131: 最小范围阻断)
EVIDENCE_FILE="$PROJECT_ROOT/.omc/state/.completion-evidence-$(date +%Y%m%d)"
BLOCKED_FILE="$PROJECT_ROOT/.omc/state/completion-blocked"
EVIDENCE_OK=false
if [ -f "$EVIDENCE_FILE" ]; then
    FRESH=$(${PYTHON_BIN:-python3} -c "
import os, time
try:
    age = time.time() - os.path.getmtime('$EVIDENCE_FILE')
    print('yes' if age < 300 else 'no')
except:
    print('no')" 2>/dev/null)
    [ "$FRESH" = "yes" ] && EVIDENCE_OK=true
fi

if [ "$EVIDENCE_OK" != true ]; then
    flywheel_event "pre_completion_gate" "no_evidence" "P2" || true
    # DG-131: 写入 completion-blocked 状态 — 触发后续 Edit/Write 最小范围阻断
    mkdir -p "$(dirname "$BLOCKED_FILE")" 2>/dev/null || true
    ${PYTHON_BIN:-python3} -c "
import json, time
with open('$BLOCKED_FILE', 'w') as f:
    json.dump({'blocked_at': time.time(), 'block_count': 0, 'reason': 'no_evidence'}, f)" 2>/dev/null || true
    printf '{"continue": false, "additionalContext": "⚠️ [pre-completion-gate] TaskUpdate(completed) BLOCKED: no VERIFIED evidence.\\nTo unblock: (1) run a verification command (2) cite output with VERIFIED: tag (3) retry.\\nEdit/Write will be reminded for 2 turns (warning only, continue:true)."}'
    exit 0
fi

# 有证据 → 清除 completion-blocked 状态，放行
rm -f "$BLOCKED_FILE" 2>/dev/null || true
echo '{"continue": true}'
exit 0
