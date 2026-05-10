#!/usr/bin/env bash
# error-dna.sh — PostToolUse:Bash / PostToolUseFailure:Bash — 捕获结构化错误 DNA 写入跨会话错误记忆
# Role: 捕获结构化错误 DNA 写入跨会话错误记忆

source "$(dirname "$0")/harness_config.sh"
hc_enabled "error_dna" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 从 stdin JSON 读 tool_name（兼容 settings.json 无位置参数场景）
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$TOOL_NAME" ] && TOOL_NAME=$(echo "$INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi
# fallback 到位置参数（保留给手动调用/测试场景）
[ -z "$TOOL_NAME" ] && TOOL_NAME="$1"
TOOL_NAME=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')

# Only capture bash tool errors
if [ "$TOOL_NAME" != "bash" ]; then
    echo '{"continue": true}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
TS=$(date +%s)

mkdir -p "$STATE_DIR" 2>/dev/null

# Write INPUT to temp file for python processing (avoids heredoc/stdin conflicts)
TMP_FILE="${STATE_DIR}/.error-dna-input-$$.json"
echo "$INPUT" > "$TMP_FILE"

ERROR_DNA_ROTATION_SIZE=$(hc_get "error_dna.rotation_size_bytes" "1048576")
export ERROR_DNA_ROTATION_SIZE
ERROR_DNA_ARCHIVE_COUNT=$(hc_get "error_dna.archive_count" "3")
export ERROR_DNA_ARCHIVE_COUNT
export SCRIPT_DIR
PY_OUTPUT=$(python3 - "$STATE_DIR" "$TS" "$TMP_FILE" <<'PYEOF'
import json, os, sys, hashlib, re

state_dir = sys.argv[1]
ts = int(sys.argv[2])
tmp_path = sys.argv[3]
script_dir = os.environ.get('SCRIPT_DIR', '')

try:
    with open(tmp_path) as f:
        data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
    sys.exit(0)

try:
    os.unlink(tmp_path)
except Exception:
    pass

tool_response = data.get('tool_response', {})
tool_input = data.get('tool_input', {})

exit_code = tool_response.get('exit_code', 0)
command = tool_input.get('command', '') or ''
stderr = tool_response.get('stderr', '') or ''
stdout = tool_response.get('stdout', '') or ''

# === Total-ops counter: increment on every Bash call ===
ops_path = os.path.join(state_dir, 'total-ops.txt')
try:
    current = int(open(ops_path).read().strip())
except (FileNotFoundError, ValueError):
    current = 0
with open(ops_path, 'w') as f:
    f.write(str(current + 1))

# PostToolUseFailure schema: top-level `error` field (no exit_code/stderr under tool_response)
# Treat presence of top-level error OR hook_event_name=PostToolUseFailure as definite failure.
top_error = data.get('error', '') or ''
event_name = data.get('hook_event_name', '') or ''
if event_name == 'PostToolUseFailure' or top_error:
    if exit_code == 0:
        exit_code = 1  # synthetic non-zero to keep downstream invariants
    if not stderr:
        stderr = top_error

# === AC-1.4: Credential sanitization (early for repair tracking) ===
cmd_clean = re.sub(r'--password\s+\S+', '--password ***', command)
cmd_clean = re.sub(r'--token\s+\S+', '--token ***', cmd_clean)
cmd_clean = re.sub(r'--secret\s+\S+', '--secret ***', cmd_clean)
cmd_clean = re.sub(r'--key\s+\S+', '--key ***', cmd_clean)

# === repair_success detection: previous failure now succeeds (exit_code non-zero → zero) ===
_rs_json_path = os.path.join(state_dir, 'error-dna.json')
_rs_aggregated = {}
if exit_code == 0 and command:
    try:
        with open(_rs_json_path) as f:
            _rs_aggregated = json.load(f).get('error_signatures', {})
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    _rs_sig = hashlib.md5(cmd_clean.encode()).hexdigest()[:16]
    _rs_entry = _rs_aggregated.get(_rs_sig, {})
    if _rs_entry and _rs_entry.get('count', 0) > 0 and not _rs_entry.get('repair_success'):
        _rs_entry['repair_success'] = True
        _rs_entry['status'] = 'fixed'
        with open(_rs_json_path, 'w') as f:
            json.dump({'error_signatures': _rs_aggregated}, f, indent=2, ensure_ascii=False)
        print(f"[error-dna repair_success] 签名 {_rs_sig[:12]} — 之前失败 ({_rs_entry.get('count', 0)} 次)，现已修复")

# Skip success and empty commands
if exit_code == 0 or not command:
    sys.exit(0)

# === AC-1.2 / AC-1.6: Shared library classifier + signature (with local fallback) ===
_ec_path = os.path.abspath(os.path.join(script_dir, '..', 'scripts', 'error_classifier.py'))
_ec_available = False
if os.path.exists(_ec_path):
    try:
        sys.path.insert(0, os.path.dirname(_ec_path))
        from error_classifier import classify_by_command, generate_signature as _gs_lib
        error_type = classify_by_command(cmd_clean)
        signature = _gs_lib(cmd_clean, exit_code, error_type)
        _ec_available = True
    except Exception:
        pass

if not _ec_available:
    # === Fallback: inline signature (cmd-only) + local classifier ===
    signature = hashlib.md5(cmd_clean.encode()).hexdigest()[:16]

    cmd_lower = cmd_clean.lower()
    if any(x in cmd_lower for x in ['go build', 'go test', 'npm run build', 'npm build', 'cargo build', 'tsc']):
        error_type = 'build'
    elif any(x in cmd_lower for x in ['go test', 'npm test', 'pytest', 'jest']):
        error_type = 'test'
    elif any(x in cmd_lower for x in ['git']):
        error_type = 'git'
    elif any(x in cmd_lower for x in ['npm install', 'go get', 'pip install']):
        error_type = 'dependency'
    elif any(x in cmd_lower for x in ['lint', 'eslint', 'golangci-lint']):
        error_type = 'lint'
    elif any(x in cmd_lower for x in ['docker']):
        error_type = 'docker'
    elif any(x in cmd_lower for x in ['curl', 'wget', 'http']):
        error_type = 'network'
    elif any(x in cmd_lower for x in ['find', 'grep', 'sed', 'awk']):
        error_type = 'file_ops'
    else:
        error_type = 'runtime'

# Build output snippet and message
output_snippet = (stderr or stdout)[:500]
message = output_snippet[:200].replace('\n', ' ').replace('\r', ' ').strip()

session_id = os.environ.get('SESSION_ID', 'unknown') or 'unknown'

# === AC-1.1: JSONL record ===
record = {
    'ts': ts,
    'signature': signature,
    'cmd': cmd_clean,
    'exit_code': exit_code,
    'error_type': error_type,
    'message': message,
    'output_snippet': output_snippet,
    'session_id': session_id
}

jsonl_path = os.path.join(state_dir, 'error-dna.jsonl')
json_path = os.path.join(state_dir, 'error-dna.json')

# Append to jsonl
os.makedirs(state_dir, exist_ok=True)
with open(jsonl_path, 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

# === AC-1.1: Merge into json state (rebuild from jsonl, preserve persistent metadata) ===
# Step 1: Load persistent state from error-dna.json (preserves fix_count, repair_success, etc.)
_persistent_agg = {}
try:
    with open(json_path) as f:
        _persistent_agg = json.load(f).get('error_signatures', {})
except (FileNotFoundError, json.JSONDecodeError):
    pass

# Step 2: Rebuild from jsonl source-of-truth
aggregated = {}
try:
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                sig = rec.get('signature', 'unknown')
                if sig not in aggregated:
                    aggregated[sig] = {
                        'count': 0,
                        'fix_count': 0,
                        'status': 'active',
                        'last_seen': 0,
                        'message': ''
                    }
                aggregated[sig]['count'] += 1
                aggregated[sig]['last_seen'] = max(aggregated[sig]['last_seen'], rec.get('ts', 0))
                if not aggregated[sig]['message']:
                    aggregated[sig]['message'] = rec.get('message', '')[:200]
            except json.JSONDecodeError:
                continue
except FileNotFoundError:
    pass

# Step 3: Merge persistent metadata (fix_count, repair_success, repair_command) from error-dna.json
for sig in aggregated:
    if sig in _persistent_agg:
        p = _persistent_agg[sig]
        aggregated[sig]['fix_count'] = p.get('fix_count', aggregated[sig]['fix_count'])
        aggregated[sig]['status'] = p.get('status', aggregated[sig]['status'])
        if p.get('repair_success'):
            aggregated[sig]['repair_success'] = True
        if p.get('repair_command'):
            aggregated[sig]['repair_command'] = p['repair_command']

merged = {'error_signatures': aggregated}
with open(json_path, 'w') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

# === Auto-fix: generate fix strategy for known error types ===
# Track fix_attempts in the aggregated state (incremented per suggestion emission)
_fix_suggestions = []
_error_entry = aggregated.get(signature, {})
_fix_count = _error_entry.get('fix_count', 0)
_repair_command = ''

if error_type == 'build':
    cmd_lower_fix = cmd_clean.lower()
    if 'go build' in cmd_lower_fix or 'go test' in cmd_lower_fix:
        _fix_suggestions.append("运行 `go mod tidy` 后重试")
        _fix_suggestions.append("检查是否有未使用的 import 或未定义的变量")
        _repair_command = 'go mod tidy && go build ./...'
    elif 'tsc' in cmd_lower_fix or 'npm run build' in cmd_lower_fix or 'npm build' in cmd_lower_fix:
        _fix_suggestions.append("运行 `npm install` 确保依赖完整")
        _fix_suggestions.append("检查 `npx tsc --noEmit` 的完整错误列表")
        _repair_command = 'npm install && npx tsc --noEmit'
elif error_type == 'dependency':
    cmd_lower_fix = cmd_clean.lower()
    if 'npm' in cmd_lower_fix or 'node' in cmd_lower_fix:
        _fix_suggestions.append("运行 `npm install` 或检查 package.json 中的版本约束")
        _repair_command = 'npm install'
    elif 'go' in cmd_lower_fix:
        _fix_suggestions.append("运行 `go mod tidy` 后重试")
        _repair_command = 'go mod tidy'
elif error_type == 'git':
    _fix_suggestions.append("检查 .git/index.lock 是否存在并清理")
    _fix_suggestions.append("确认 git HEAD 未 detached 且分支名正确")
    _repair_command = 'rm -f .git/index.lock && git status'
elif error_type == 'lint':
    _fix_suggestions.append("运行 `git diff` 查看最近的改动区域")
    _fix_suggestions.append("检查是否有格式或命名规范违规")

if _fix_suggestions and _fix_count < 3:
    # Track fix_attempt (increment fix_count)
    if signature in aggregated:
        aggregated[signature]['fix_count'] = _fix_count + 1
        if _repair_command:
            aggregated[signature]['repair_command'] = _repair_command

    _fix_lines = [f"[error-dna auto-fix] 签名 {signature[:12]} 类型 {error_type} — 建议修复策略:"]
    for suggestion in _fix_suggestions:
        _fix_lines.append(f"  · {suggestion}")
    if _repair_command:
        _fix_lines.append(f"  ▶ 可执行修复: `{_repair_command}`")
    if _fix_count >= 2:
        _fix_lines.append(f"  ⚠️ 已尝试 {_fix_count + 1}/3 次，超过 3 次将不再自动建议")
    print('|'.join(_fix_lines))

# Re-write with updated fix_count and repair metadata
if _fix_suggestions and _fix_count < 3:
    with open(json_path, 'w') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

# === AC-1.5: auto-rotation, configurable size & archive count ===
try:
    size = os.path.getsize(jsonl_path)
    rotation_size = int(os.environ.get('ERROR_DNA_ROTATION_SIZE', '1048576'))
    archive_count = int(os.environ.get('ERROR_DNA_ARCHIVE_COUNT', '3'))
    if size > rotation_size:
        rotate_dir = state_dir
        for i in range(archive_count, 0, -1):
            old_path = os.path.join(rotate_dir, 'error-dna.jsonl.{}'.format(i - 1))
            new_path = os.path.join(rotate_dir, 'error-dna.jsonl.{}'.format(i))
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
        os.rename(jsonl_path, os.path.join(rotate_dir, 'error-dna.jsonl.0'))
        # Create fresh empty file
        open(jsonl_path, 'w').close()
except Exception:
    pass

# === Oracle Q2-A: additionalContext for high-frequency errors (>=2 occurrences) ===
frequent = [(sig, info['count'], info.get('message', '')[:120])
            for sig, info in aggregated.items()
            if info['count'] >= 2 and info.get('status') != 'fixed']
if frequent:
    frequent.sort(key=lambda x: -x[1])
    lines = ["[高频错误模式检测] 以下签名已出现 >=2 次:"]
    for sig, count, msg in frequent:
        lines.append(f'  · {sig[:20]} ×{count} — {msg}')
    print('|'.join(lines))
PYEOF
)

if [ -n "$PY_OUTPUT" ]; then
    ESCAPED=$(echo "$PY_OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
    echo "{\"continue\": true, \"hookSpecificOutput\": {\"hookEventName\": \"PostToolUse\", \"additionalContext\": ${ESCAPED}}}"
else
    echo '{"continue": true}'
fi
exit 0
