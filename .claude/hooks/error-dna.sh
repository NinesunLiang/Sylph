#!/bin/bash
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

# Skip success and empty commands
if exit_code == 0 or not command:
    sys.exit(0)

# === AC-1.4: Credential sanitization ===
cmd_clean = re.sub(r'--password\s+\S+', '--password ***', command)
cmd_clean = re.sub(r'--token\s+\S+', '--token ***', cmd_clean)
cmd_clean = re.sub(r'--secret\s+\S+', '--secret ***', cmd_clean)
cmd_clean = re.sub(r'--key\s+\S+', '--key ***', cmd_clean)

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

# === AC-1.1: Merge into json state (rebuild from jsonl source-of-truth) ===
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

merged = {'error_signatures': aggregated}
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
