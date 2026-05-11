#!/usr/bin/env bash
# retry-budget.sh — C9 错误修复预算追踪
# Reads error-dna.json and flags signatures exceeding retry budget.
# Prevents infinite retry loops by blocking before 3rd failed attempt.
#
# Commands:
#   status   — Print retry budget status for all active errors
#   check    — Exit 2 if any error exceeds budget (for hooks)
#   record   — Increment retry count for a given error signature
#   clear    — Clear/reset retry count for a given error signature

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
DNA_FILE="$STATE_DIR/error-dna.json"
BUDGET_FILE="$STATE_DIR/retry-budget.json"
mkdir -p "$STATE_DIR"

# 从 harness.yaml 读取 max_retries（通过缓存文件，不 source harness_config.sh 以兼容 set -u）
MAX_RETRIES=3
RETRY_CACHE="$STATE_DIR/.harness-cache"
if [ -f "$RETRY_CACHE" ]; then
    HC_MAX=$(grep -m1 "^retry_budget.max_retries=" "$RETRY_CACHE" 2>/dev/null | cut -d'=' -f2-)
    [ -n "$HC_MAX" ] && MAX_RETRIES=$HC_MAX
fi

init_budget() {
  if [ ! -f "$BUDGET_FILE" ]; then
    echo '{"signatures":{}}' > "$BUDGET_FILE"
  fi
}

get_budget() {
  if [ -f "$BUDGET_FILE" ]; then
    python3 -c "
import json, sys
try:
    d = json.load(open('$BUDGET_FILE'))
    sigs = d.get('signatures', {})
    max_r = $MAX_RETRIES
    for sig, entry in sorted(sigs.items()):
        count = entry.get('retry_count', 0)
        label = entry.get('label', sig)[:80]
        blocked = 'BLOCKED' if count >= max_r else 'ok'
        print(f'{sig[:40]} | {count}/{max_r} | {blocked} | {label}')
except:
    pass
" 2>/dev/null
  else
    echo "(no retry data)"
  fi
}

check_budget() {
  if [ -f "$BUDGET_FILE" ]; then
    EXCEEDED=$(python3 -c "
import json, sys
try:
    d = json.load(open('$BUDGET_FILE'))
    sigs = d.get('signatures', {})
    max_r = $MAX_RETRIES
    exceeded = [(k, v.get('retry_count', 0)) for k, v in sigs.items() if v.get('retry_count', 0) >= max_r]
    if exceeded:
        for sig, cnt in exceeded:
            label = sigs[sig].get('label', sig)[:80]
            print(f'{sig[:40]} ({cnt} retries): {label}')
        sys.exit(2)
    else:
        sys.exit(0)
except:
    sys.exit(0)
" 2>/dev/null)
    EXIT_CODE=$?
    if [ -n "$EXCEEDED" ]; then
      echo "[Retry Budget] BLOCKED — 以下错误超过 ${MAX_RETRIES} 次重试上限:"
      echo "$EXCEEDED"
    fi
    return $EXIT_CODE
  fi
  return 0
}

record_retry() {
  local sig="$1"
  local label="${2:-unknown}"
  init_budget
  python3 -c "
import json, os, time
bf = '$BUDGET_FILE'
d = json.load(open(bf))
sigs = d.get('signatures', {})
sig_key = '$sig'
if sig_key not in sigs:
    sigs[sig_key] = {'retry_count': 0, 'label': '$label', 'first_seen': int(time.time())}
entry = sigs[sig_key]
entry['retry_count'] = entry.get('retry_count', 0) + 1
entry['last_retry'] = int(time.time())
entry['label'] = '$label'
d['signatures'] = sigs
with open(bf, 'w') as f:
    json.dump(d, f, indent=2)
cnt = entry['retry_count']
print(f'[Retry Budget] {sig_key[:40]}: retry {cnt}/${MAX_RETRIES}')
if cnt >= $MAX_RETRIES:
    print(f'[Retry Budget] BLOCKED — 已达 {cnt} 次上限，需人工干预')
" 2>/dev/null
}

clear_retry() {
  local sig="$1"
  if [ ! -f "$BUDGET_FILE" ]; then
    echo "[Retry Budget] 无预算数据"
    return 0
  fi
  python3 -c "
import json
bf = '$BUDGET_FILE'
d = json.load(open(bf))
sigs = d.get('signatures', {})
sig_key = '$sig'
if sig_key in sigs:
    del sigs[sig_key]
    print(f'[Retry Budget] cleared: {sig_key[:40]}')
else:
    print(f'[Retry Budget] not found: {sig_key[:40]}')
d['signatures'] = sigs
with open(bf, 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null
}

case "${1:-status}" in
  status)
    get_budget
    ;;
  check)
    check_budget
    ;;
  record)
    record_retry "${2:-}" "${3:-}"
    ;;
  clear)
    clear_retry "${2:-}"
    ;;
  *)
    echo "Usage: retry-budget.sh {status|check|record <sig> [label]|clear <sig>}"
    exit 1
    ;;
esac
