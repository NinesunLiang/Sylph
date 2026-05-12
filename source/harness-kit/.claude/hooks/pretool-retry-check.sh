#!/usr/bin/env bash
# pretool-retry-check.sh — PreToolUse — 阻断超过重试上限的 Bash 命令
# Role: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令
#
# 原理：
#   retry-budget.json 记录每个错误签名的重试次数。
#   当某个签名超过 MAX_RETRIES（默认 3），后续 Bash 调用被阻断。
#   避免 AI 在同一个错误上无限重试（C9 错误恢复）。
#
# 注意：直接读取 retry-budget.json，不调用 retry-budget.sh check
# （retry-budget.sh 存在 bash 退出码传播 bug）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "retry_budget_check" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

# 仅检查 Bash 命令（重试只发生在命令执行失败时）
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // ""' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool', ''))
except:
    pass" 2>/dev/null)
fi
[ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "bash" ] && { echo '{"continue": true}'; exit 0; }

# 直接读取 retry-budget.json 检查是否超过上限
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUDGET_FILE="$PROJECT_ROOT/.omc/state/retry-budget.json"

if [ -f "$BUDGET_FILE" ]; then
    EXCEEDED=$(python3 -c "
import json, sys
try:
    with open('$BUDGET_FILE') as f:
        d = json.load(f)
    sigs = d.get('signatures', {})
    max_r = 3
    exceeded = [(k, v.get('retry_count', 0)) for k, v in sigs.items() if v.get('retry_count', 0) >= max_r]
    if exceeded:
        for sig, cnt in exceeded:
            label = sigs[sig].get('label', sig)[:80]
            print(f'{sig[:40]} ({cnt} retries): {label}')
        sys.exit(2)
    else:
        sys.exit(0)
except Exception:
    sys.exit(0)
")
    PY_EXIT=$?
    if [ $PY_EXIT -eq 2 ] && [ -n "$EXCEEDED" ]; then
        echo "[Retry Budget] BLOCKED — 存在超过重试上限的错误:" >&2
        echo "$EXCEEDED" >&2
        exit 2
    fi
fi

echo '{"continue": true}'
exit 0
