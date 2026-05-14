#!/usr/bin/env bash
# error-dna.sh — PostToolUse:Bash / PostToolUseFailure:Bash — 轻量错误捕获（Oracle 瘦身后 v2）
# Role: 捕获 Bash 错误写入 jsonl + total-ops 计数器 + 高频告警
# 瘦身说明: 移除 JSON 全量重建(~200行)、噪声分类(~100行)、repair_success 检测
#           保留: 捕获管道、total-ops、retry-budget、归档轮转(R41)、高频告警
# Oracle 裁决: 哲学#3+#6 保留基础设施 > 哲学#1+#2 去噪 — 保留捕获点，去除非必要计算

source "$(dirname "$0")/harness_config.sh"
hc_enabled "error_dna" || { echo '{"continue": true}'; exit 0; }
_ed_val="$(hc_get 'escape_detection' 'true')"; _ed_val="${_ed_val%\\}"
[ "$_ed_val" = "true" ] || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 从 stdin JSON 读 tool_name
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$TOOL_NAME" ] && TOOL_NAME=$(echo "$INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi
[ -z "$TOOL_NAME" ] && TOOL_NAME="$1"
TOOL_NAME=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')

if [ "$TOOL_NAME" != "bash" ]; then
    echo '{"continue": true}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
TS=$(date +%s)

mkdir -p "$STATE_DIR" 2>/dev/null

TMP_FILE="${STATE_DIR}/.error-dna-input-$$.json"
echo "$INPUT" > "$TMP_FILE"

ERROR_DNA_ROTATION_SIZE=$(hc_get "error_dna.rotation_size_bytes" "1048576")
export ERROR_DNA_ROTATION_SIZE
ERROR_DNA_ARCHIVE_COUNT=$(hc_get "error_dna.archive_count" "3")
export ERROR_DNA_ARCHIVE_COUNT

PY_OUTPUT=$(python3 - "$STATE_DIR" "$TS" "$TMP_FILE" <<'PYEOF'
import json, os, sys, hashlib, re

state_dir = sys.argv[1]
ts = int(sys.argv[2])
tmp_path = sys.argv[3]

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

# === Total-ops counter ===
ops_path = os.path.join(state_dir, 'total-ops.txt')
try:
    current = int(open(ops_path).read().strip())
except (FileNotFoundError, ValueError):
    current = 0
with open(ops_path, 'w') as f:
    f.write(str(current + 1))

# PostToolUseFailure schema: top-level error field
top_error = data.get('error', '') or ''
event_name = data.get('hook_event_name', '') or ''
if event_name == 'PostToolUseFailure' or top_error:
    if exit_code == 0:
        exit_code = 1
    if not stderr:
        stderr = top_error

# Credential sanitization
cmd_clean = re.sub(r'--password\s+\S+', '--password ***', command)
cmd_clean = re.sub(r'--token\s+\S+', '--token ***', cmd_clean)
cmd_clean = re.sub(r'--secret\s+\S+', '--secret ***', cmd_clean)
cmd_clean = re.sub(r'--key\s+\S+', '--key ***', cmd_clean)

# === Escape Pattern E1: Governance file bypass via Bash ===
# AI uses Bash (sed -i / tee / > / >>) to modify governance files,
# bypassing pretool-sensitive-edit (which only hooks Edit|Write tools).
# These are HIGH-VALUE signals — successful gate bypass, not a gate failure.
GOVERNANCE_PATHS = [
    '.claude/harness.yaml', '.claude/settings.json',
    '.claude/kernel.md', '.claude/anti-patterns.md',
    '.claude/index.md', '.claude/claude-next.md',
    '.claude/feature-registry.yaml',
    'CLAUDE.md', 'AGENTS.md',
    '.cursor/hooks.json', '.opencode/opencode.json',
]
ESCAPE_E1 = False
ESCAPE_E1_TARGET = ''
for _gp in GOVERNANCE_PATHS:
    if _gp in cmd_clean:
        ESCAPE_E1 = True
        ESCAPE_E1_TARGET = _gp
        break

# Symlink resolution: check if command file args point to governance files via symlink
# Catches: AI creates /tmp/link -> .claude/settings.json then writes to /tmp/link
if not ESCAPE_E1:
    for _token in cmd_clean.split():
        _token = _token.strip("'\"")
        if _token.startswith('/') and os.path.exists(_token):
            _resolved = os.path.realpath(_token)
            if _resolved != _token:  # symbolic link resolves differently
                for _gp in GOVERNANCE_PATHS:
                    if _gp in _resolved:
                        ESCAPE_E1 = True
                        ESCAPE_E1_TARGET = _gp
                        break
        if ESCAPE_E1:
            break

# === Escape Pattern E2: CAPTCHA forgery ===
# AI directly writes to CAPTCHA approval files to self-approve gates.
# Per R42: AI must never self-approve — this is a critical escape attempt.
CAPTCHA_MARKERS = [
    'sensitive-approved', 'sensitive-required',
    'permission-approved', 'permission-required',
]
ESCAPE_E2 = False
ESCAPE_E2_TARGET = ''
for _cm in CAPTCHA_MARKERS:
    if _cm in cmd_clean:
        ESCAPE_E2 = True
        ESCAPE_E2_TARGET = _cm
        break

# Skip success and empty commands — EXCEPT when escape patterns detected
# Successful escapes (exit_code=0) are MORE valuable signals than failures
if (exit_code == 0 and not ESCAPE_E1 and not ESCAPE_E2) or not command:
    sys.exit(0)

# === Inline classifier (lightweight, no shared lib dependency) ===
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

output_snippet = (stderr or stdout)[:500]
message = output_snippet[:200].replace('\n', ' ').replace('\r', ' ').strip()
session_id = os.environ.get('SESSION_ID', 'unknown') or 'unknown'

# === Append to JSONL (capture only, no full rebuild) ===
record = {
    'ts': ts,
    'signature': signature,
    'cmd': cmd_clean,
    'exit_code': exit_code,
    'error_type': error_type,
    'message': message,
    'session_id': session_id,
    'escape_type': '',  # '' | 'governance_bypass' | 'captcha_forgery'
}

# Label escape records — these are HIGH-VALUE signals, not noise
if ESCAPE_E1:
    record['error_type'] = 'governance_bypass'
    record['escape_type'] = 'governance_bypass'
    record['message'] = f'E1: Bash bypass of governance file {ESCAPE_E1_TARGET} — cmd: {cmd_clean[:100]}'
elif ESCAPE_E2:
    record['error_type'] = 'captcha_forgery'
    record['escape_type'] = 'captcha_forgery'
    record['message'] = f'E2: CAPTCHA forgery targeting {ESCAPE_E2_TARGET} — cmd: {cmd_clean[:100]}' 

jsonl_path = os.path.join(state_dir, 'error-dna.jsonl')
os.makedirs(state_dir, exist_ok=True)
with open(jsonl_path, 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

# === Retry budget update (C9) ===
budget_path = os.path.join(state_dir, 'retry-budget.json')
budget = {'signatures': {}}
if os.path.isfile(budget_path):
    try:
        with open(budget_path) as _bf:
            budget = json.load(_bf)
    except Exception:
        pass
sigs = budget.get('signatures', {})
if signature not in sigs:
    sigs[signature] = {
        'retry_count': 0, 'label': message[:80],
        'first_seen': ts, 'error_type': error_type
    }
sigs[signature]['retry_count'] = sigs[signature].get('retry_count', 0) + 1
sigs[signature]['last_retry'] = ts
sigs[signature]['label'] = message[:80]
budget['signatures'] = sigs
_btmp = budget_path + '.tmp'
with open(_btmp, 'w') as _bf:
    json.dump(budget, _bf, indent=2, ensure_ascii=False)
os.rename(_btmp, budget_path)

# === Archive rotation (R41 fix: correct shift loop) ===
try:
    size = os.path.getsize(jsonl_path)
    rotation_size = int(os.environ.get('ERROR_DNA_ROTATION_SIZE', '1048576'))
    archive_count = int(os.environ.get('ERROR_DNA_ARCHIVE_COUNT', '3'))
    if size > rotation_size:
        rotate_dir = state_dir
        for i in range(archive_count - 1, 0, -1):
            old_path = os.path.join(rotate_dir, f'error-dna.jsonl.{i - 1}')
            new_path = os.path.join(rotate_dir, f'error-dna.jsonl.{i}')
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
        orphan = os.path.join(rotate_dir, f'error-dna.jsonl.{archive_count}')
        if os.path.exists(orphan):
            os.unlink(orphan)
        os.rename(jsonl_path, os.path.join(rotate_dir, 'error-dna.jsonl.0'))
        open(jsonl_path, 'w').close()
except Exception:
    pass



# === Write structured patch suggestion for Oracle/human review ===
_patch_file = os.path.join(state_dir, 'escape-patches.json')
_patches = {}
if os.path.isfile(_patch_file):
    try:
        with open(_patch_file) as _pf:
            _patches = json.load(_pf)
    except: pass

_patch_key = ''
_is_new_patch = False
if ESCAPE_E1:
    _patch_key = f'e1_{ESCAPE_E1_TARGET.replace("/","_").replace(".","_")}'
    if _patch_key not in _patches:
        _is_new_patch = True
        _patches[_patch_key] = {
            'type': 'governance_bypass',
            'target': ESCAPE_E1_TARGET,
            'command': cmd_clean[:200],
            'recommendation': '扩展 pretool-sensitive-edit matcher 到 Bash，或在 posttool-bash-audit 添加 governance_bypass 审计规则',
            'severity': 'high',
            'ts': ts,
            'status': 'pending'
        }
elif ESCAPE_E2:
    _patch_key = f'e2_{ESCAPE_E2_TARGET}'
    if _patch_key not in _patches:
        _is_new_patch = True
        _patches[_patch_key] = {
            'type': 'captcha_forgery',
            'target': ESCAPE_E2_TARGET,
            'command': cmd_clean[:200],
            'recommendation': '检查 permission-gate.sh / pretool-sensitive-edit.sh 的 CAPTCHA 文件保护机制，确保 Bash echo 到敏感文件被拦截',
            'severity': 'critical',
            'ts': ts,
            'status': 'pending'
        }

if _is_new_patch:
    _ptmp = _patch_file + '.tmp'
    with open(_ptmp, 'w') as _pf:
        json.dump(_patches, _pf, indent=2, ensure_ascii=False)
    os.rename(_ptmp, _patch_file)

# === Escape detection alert: immediate warning via additionalContext ===
if ESCAPE_E1:
    print(f"[E1] ⚠️ 治理文件绕过: {ESCAPE_E1_TARGET}")
    print(f"  Bash '{cmd_clean[:120]}' 绕过了 pretool-sensitive-edit 的 Edit|Write 门禁。")
    print(f"  escape_type=governance_bypass 已记录到 error-dna.jsonl。")
    print(f"  补丁建议: 扩展 pretool-sensitive-edit matcher 到 Bash，或在 posttool-bash-audit 添加审计。")
elif ESCAPE_E2:
    print(f"[E2] ⚠️ 验证码伪造: {ESCAPE_E2_TARGET}")
    print(f"  Bash '{cmd_clean[:120]}' 尝试自写批准标记绕过 CAPTCHA 门禁 (R42 禁止)。")
    print(f"  escape_type=captcha_forgery 已记录到 error-dna.jsonl。")
    print(f"  补丁建议: 检查 permission-gate.sh / pretool-sensitive-edit.sh 的验证码文件保护。")

# === High-frequency alert scan (scan recent jsonl, lightweight) ===
# Only scan current jsonl (not archives), max 100KB to keep it fast
_scanned = {}
try:
    _scan_size = min(os.path.getsize(jsonl_path) if os.path.exists(jsonl_path) else 0, 102400)
    with open(jsonl_path) as _sf:
        _sf.seek(max(0, os.path.getsize(jsonl_path) - _scan_size))
        for _line in _sf:
            _line = _line.strip()
            if not _line:
                continue
            try:
                _rec = json.loads(_line)
                _s = _rec.get('signature', '')
                if _s not in _scanned:
                    _scanned[_s] = {'count': 0, 'msg': _rec.get('message', '')[:120]}
                _scanned[_s]['count'] += 1
            except json.JSONDecodeError:
                pass
except Exception:
    pass

_frequent = [(sig, info['count'], info['msg'])
             for sig, info in _scanned.items()
             if info['count'] >= 3]  # threshold: 3+ in current jsonl
if _frequent:
    _frequent.sort(key=lambda x: -x[1])
    _lines = [f"[高频错误] 当前 jsonl 中 >=3 次的签名 ({len(_frequent)} 个):"]
    for sig, count, msg in _frequent[:5]:
        _lines.append(f'  · {sig[:16]} ×{count} — {msg[:100]}')
    print('|'.join(_lines))
PYEOF
)

if [ -n "$PY_OUTPUT" ]; then
    ESCAPED=$(echo "$PY_OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
    echo "{\"continue\": true, \"hookSpecificOutput\": {\"hookEventName\": \"PostToolUse\", \"additionalContext\": ${ESCAPED}}}"
else
    echo '{"continue": true}'
fi
exit 0
