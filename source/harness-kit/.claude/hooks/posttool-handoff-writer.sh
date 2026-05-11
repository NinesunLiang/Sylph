#!/usr/bin/env bash
# posttool-handoff-writer.sh — PostToolUse:TaskUpdate — 每次 Task 完成后写 handoff
# Role: 每次 Task 完成后写 handoff（E8 上下文遗忘防御）
source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_handoff_writer" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

# 解析 TaskUpdate 的 status 字段
STATUS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {})
    print(ti.get('status', ''))
except:
    pass
" 2>/dev/null)

# 仅对 "completed" status 响应
[ "$STATUS" != "completed" ] && { echo '{"continue": true}'; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

HANDOFF_FILE="$STATE_DIR/session-handoff.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 收集当前状态
BRANCH=$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo "unknown")
MODIFIED=$(git -C "$PROJECT_ROOT" diff --name-only 2>/dev/null | head -15 | tr '\n' ';')
DIFF_STAT=$(git -C "$PROJECT_ROOT" diff --stat 2>/dev/null | tail -1)

# 活跃 RPE 上下文
ACTIVE_FEATURE=""
ACTIVE_TASK=""
LATEST_EXEC=$(find "$PROJECT_ROOT/rpe" -name "executor.md" -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
if [ -n "$LATEST_EXEC" ]; then
    FEATURE_NAME=$(echo "$LATEST_EXEC" | sed "s|.*/rpe/||;s|/executor.md||")
    ACTIVE_FEATURE="$FEATURE_NAME"
    ACTIVE_TASK=$(grep -E "^##.*🔄|^## Step.*进行中|当前任务" "$LATEST_EXEC" 2>/dev/null | head -1 | sed 's/^## //')
fi

# error-dna 摘要
ERROR_SUMMARY=""
DNA_FILE="$STATE_DIR/error-dna.json"
if [ -f "$DNA_FILE" ]; then
    ERROR_SUMMARY=$(python3 -c "
import json, sys
try:
    with open('$DNA_FILE') as f:
        dna = json.load(f)
    sigs = dna.get('error_signatures', {})
    active = [(k, v) for k, v in sigs.items() if v.get('status') != 'fixed']
    if active:
        print(f'{len(active)} active errors')
    else:
        print('0 active errors')
except:
    print('(unreadable)')
" 2>/dev/null)
fi

# 顺手更新 token tracking 信息
CTX_INFO=""
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
if [ -f "$INDEX_FILE" ]; then
    CTX_INFO=$(python3 -c "
import json
try:
    d = json.load(open('$INDEX_FILE'))
    usage = d.get('usage', 0)
    limit = d.get('limit', 200000)
    pct = int(usage * 100 / limit) if limit > 0 else 0
    print(f'context: {pct}% ({usage}/{limit})')
except:
    print('')
" 2>/dev/null)
fi

# 写 handoff（覆盖式 — 始终最新状态）
cat > "$HANDOFF_FILE" <<EOF
# Session Handoff — ${TIMESTAMP}

## Context
- Branch: ${BRANCH}
- Active Feature: ${ACTIVE_FEATURE:-none}
- Last completion: $(date)

## State
- Modified files: ${MODIFIED:-none}
- Git diff: ${DIFF_STAT:-clean}
- Active task: ${ACTIVE_TASK:-none}

## Errors
- ${ERROR_SUMMARY:-not available}

## Token
- ${CTX_INFO:-not available}

## Next Steps
(handoff auto-generated after TaskUpdate completed — \`inject-project-knowledge.sh\` auto-loads this on next SessionStart)
EOF

# 同步 pipeline.yaml 状态（若有活跃 feature）
if [ -n "$ACTIVE_FEATURE" ]; then
    PIPELINE_FILE="$PROJECT_ROOT/.claude/skills/lx-orch/state/pipeline.yaml"
    if [ -f "$PIPELINE_FILE" ]; then
        if grep -q "feat-${ACTIVE_FEATURE}" "$PIPELINE_FILE" 2>/dev/null; then
            : # 已存在
        fi
    fi
fi

echo '{"continue": true}'
exit 0
