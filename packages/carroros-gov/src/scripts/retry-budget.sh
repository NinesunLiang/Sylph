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
#
# C2 语义去重: record/clear 支持命令归一化（去除时间戳/UUID/临时路径等），
# 相似命令映射到同一签名。使用 --normalize 或 -n 开关激活。

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

# ─── C2: 命令归一化函数 ───
# normalize_command <raw_string>
# 去除时间戳、UUID、临时路径、session ID、版本号等可变部分，
# 使语义等价的命令映射到同一签名。
normalize_command() {
  local raw="$1"
  # 通过 Python 进行正则归一化（兼容 set -u）
  ${PYTHON_BIN:-python3} -c "
import re, sys
cmd = sys.argv[1] if len(sys.argv) > 1 else ''
# 1. 时间戳: YYYYMMDD_HHMMSS / YYYY-MM-DDTHH:MM:SS / epoch 秒(10位)
cmd = re.sub(r'\b\d{8}[-_]\d{6}\b', '<TS>', cmd)
cmd = re.sub(r'\b\d{4}[-_]\d{2}[-_]\d{2}[T ]\d{2}[-_:]\d{2}[-_:]\d{2}\b', '<TS>', cmd)
cmd = re.sub(r'\b1[3-9]\d{9}\b', '<TS>', cmd)  # epoch >= 1300000000
# 2. UUID/GUID
cmd = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '<UUID>', cmd)
cmd = re.sub(r'\b[0-9a-fA-F]{32}\b', '<UUID>', cmd)
# 3. 临时目录/文件路径
cmd = re.sub(r'/tmp/[^\s\"]+', '<TMP>', cmd)
cmd = re.sub(r'/private/tmp/[^\s\"]+', '<TMP>', cmd)
cmd = re.sub(r'/var/folders/[^\s\"]+', '<TMP>', cmd)
# 4. 常见的 --verbose/--debug/--quiet 等不影响语义的标志（保持签名聚焦错误模式）
cmd = re.sub(r'\s+(--verbose|-v|--debug|-d|--quiet|-q)(?:\s|$)', ' ', cmd)
# 5. 管道后的 head/tail/sort 等纯展示命令（不影响错误语义）
cmd = re.sub(r'\s*\|\s*(head|tail|sort|uniq|wc|grep -v|cat -n)\s*.*$', '', cmd)
# 6. 多个空格合并，去首尾空格
cmd = re.sub(r'\s+', ' ', cmd).strip()
sys.stdout.write(cmd)
" "$raw" 2>/dev/null || echo "$raw"
}

# ─── C2: 生成归一化签名 ───
# compute_signature <raw_string> [--normalize]
compute_signature() {
  local raw="$1"
  local do_norm="${2:-}"
  local normalized
  if [ "$do_norm" = "--normalize" ]; then
    normalized="$(normalize_command "$raw")"
  else
    normalized="$raw"
  fi
  echo "$normalized" | ${PYTHON_BIN:-python3} -c "import sys,hashlib; print(hashlib.md5(sys.stdin.read().strip().encode()).hexdigest()[:16])" 2>/dev/null
}

get_budget() {
  if [ -f "$BUDGET_FILE" ]; then
    ${PYTHON_BIN:-python3} -c "
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
    EXCEEDED=$(${PYTHON_BIN:-python3} -c "
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
except Exception:
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
  # 如果 label 以 --normalize 开头，对 sig 进行归一化
  local sig_key="$sig"
  if [ "${label:0:11}" = "--normalize" ]; then
    local raw_cmd="$sig"
    sig_key="$(compute_signature "$raw_cmd" "--normalize")"
    label="${label#--normalize }"
    [ -z "$label" ] && label="normalized: ${raw_cmd:0:60}"
  fi
  ${PYTHON_BIN:-python3} -c "
import json, os, time
bf = '$BUDGET_FILE'
d = json.load(open(bf))
sigs = d.get('signatures', {})
sig_key = '${sig_key}'
if sig_key not in sigs:
    sigs[sig_key] = {'retry_count': 0, 'label': '${label}', 'first_seen': int(time.time())}
entry = sigs[sig_key]
entry['retry_count'] = entry.get('retry_count', 0) + 1
entry['last_retry'] = int(time.time())
entry['label'] = '${label}'
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
  # 如果第二个参数是 --normalize, 对 sig 进行归一化后再查找
  local sig_key="$sig"
  if [ "${2:-}" = "--normalize" ]; then
    sig_key="$(compute_signature "$sig" "--normalize")"
  fi
  if [ ! -f "$BUDGET_FILE" ]; then
    echo "[Retry Budget] 无预算数据"
    return 0
  fi
  ${PYTHON_BIN:-python3} -c "
import json
bf = '$BUDGET_FILE'
d = json.load(open(bf))
sigs = d.get('signatures', {})
sig_key = '${sig_key}'
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
    clear_retry "${2:-}" "${3:-}"
    ;;
  norm)
    # norm <raw_cmd> — 输出归一化后的命令（测试/调试用）
    if [ -n "${2:-}" ]; then
      normalize_command "${2}"
    else
      echo "Usage: retry-budget.sh norm <raw_cmd>"
      exit 1
    fi
    ;;
  *)
    echo "Usage: retry-budget.sh {status|check|record <sig> [label|--normalize <label>]|clear <sig> [--normalize]|norm <raw_cmd>}"
    exit 1
    ;;
esac
