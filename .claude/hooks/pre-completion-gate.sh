#!/usr/bin/env bash
# pre-completion-gate.sh — PreToolUse:TaskUpdate — 前置完成门禁，阻止无证据的 completed 调用
# Role: 前置完成门禁，在 AI 调用 TaskUpdate(completed) 前阻止，减少浪费轮次

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pre_completion_gate" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 提取 status 字段
STATUS=$(echo "$INPUT" | python3 -c "
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
if [ -f "$PROJECT_ROOT/.omc/state/autonomous.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/ghost-mode.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/lx-ghost.json" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/lx-goal.json" ]; then
    echo "[pre-completion-gate] 自主模式: 允许 completed（门禁降级）" >&2
    echo '{"continue": true}'
    exit 0
fi

# 检查证据文件
EVIDENCE_FILE="$PROJECT_ROOT/.omc/state/.completion-evidence-$(date +%Y%m%d)"
if [ ! -f "$EVIDENCE_FILE" ]; then
    echo "⛔ 前置门禁阻断: 调用 TaskUpdate(completed) 但无证据文件。" >&2
    echo "要求: 必须先运行验证并向 ${EVIDENCE_FILE} 写入结构化证据。" >&2
    echo "格式示例:" >&2
    echo '  echo "VERIFIED: go build ./... → exit 0, all tests PASS" > '"$EVIDENCE_FILE" >&2
    exit 2
fi

# 检查证据文件新鲜度
FRESH=$(python3 -c "
import os, time
try:
    age = time.time() - os.path.getmtime('$EVIDENCE_FILE')
    print('yes' if age < 300 else 'no')
except:
    print('no')" 2>/dev/null)

if [ "$FRESH" != "yes" ]; then
    echo "⛔ 前置门禁阻断: 证据文件已过期（超过 5 分钟）。请重新运行验证。" >&2
    rm -f "$EVIDENCE_FILE"
    exit 2
fi

echo '{"continue": true}'
exit 0
