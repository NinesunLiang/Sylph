#!/usr/bin/env bash
# error-dna.sh — PostToolUse:Bash / PostToolUseFailure:Bash — 轻量错误捕获（Oracle 瘦身后 v2）
# Role: 捕获 Bash 错误写入 error-dna.jsonl + governance-audit.jsonl + total-ops 计数器 + 高频告警
# E5 修复: error-dna.jsonl 是主捕获文件（所有错误 + 逃逸），不再仅限于 E2 逃逸
# 瘦身说明: 移除 JSON 全量重建(~200行)、噪声分类(~100行)、repair_success 检测
#           保留: 捕获管道、total-ops、retry-budget、归档轮转(R41)、高频告警
# Oracle 裁决: 哲学#3+#6 保留基础设施 > 哲学#1+#2 去噪 — 保留捕获点，去除非必要计算

source "$(dirname "$0")/harness_config.sh"
set -f
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

# DG-87: ensure error-dna.jsonl exists after rotation or accidental deletion.
# Rotation re-creates it via open().write().close(), but external deletion between
# rotations leaves a gap until the next escape event. Touch here guarantees existence.
touch "$STATE_DIR/error-dna.jsonl" 2>/dev/null || true

# DG-90: flywheel telemetry — error-dna is the error capture pipeline itself,
# must emit runtime evidence that it's firing (Source III for C5/C9/E5 scoring).
flywheel_event "error_dna" "capture" "P2" || true

	# Heartbeat: timestamp file to distinguish "zero errors" from "collection broken"
	touch "$STATE_DIR/error-dna-heartbeat.txt" 2>/dev/null || true

TMP_FILE="${STATE_DIR}/.error-dna-input-$$.json"

# 启动时清理超过 1 小时的孤儿临时文件（防积压，DG-17 同类静默失败模式）
find "$STATE_DIR" -maxdepth 1 -name '.error-dna-input-*.json' -mmin +60 -delete 2>/dev/null

# trap 确保任何退出路径都清理临时文件（防 Python crash 导致孤儿文件）
trap "rm -f '$TMP_FILE'" EXIT

echo "$INPUT" > "$TMP_FILE"

ERROR_DNA_ROTATION_SIZE=$(hc_get "error_dna.rotation_size_bytes" "1048576")
export ERROR_DNA_ROTATION_SIZE
ERROR_DNA_ARCHIVE_COUNT=$(hc_get "error_dna.archive_count" "3")
export ERROR_DNA_ARCHIVE_COUNT

PY_OUTPUT=$(${PYTHON_BIN:-python3} - "$STATE_DIR" "$TS" "$TMP_FILE" <<'PYEOF'
import json, os, sys, hashlib, re, glob, time

state_dir = sys.argv[1]
ts = int(sys.argv[2])
tmp_path = sys.argv[3]

try:
    with open(tmp_path, encoding="utf-8") as f:
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
    current = int(open(ops_path, encoding="utf-8").read().strip())
except (FileNotFoundError, ValueError):
    current = 0
with open(ops_path, 'w', encoding="utf-8") as f:
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
# P0.2: Mask API key env vars
cmd_clean = re.sub(r'(ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY|DEEPSEEK_BRIDGE_API_KEY|OPENAI_API_KEY|CODECLI_API_KEY|GEMINI_API_KEY)=\S+', r'\1=***', cmd_clean)
# P0.2: Mask Authorization: Bearer tokens (stop at whitespace/quotes/angle brackets)
cmd_clean = re.sub(r'(Authorization:\s*Bearer\s+)[^\s"<>]+', r'\1***', cmd_clean)
# P0.2: Mask known token prefixes and JWT tokens
cmd_clean = re.sub(r'(?:sk-|ghp_|xoxb-|xapp-)[a-zA-Z0-9_\-]{20,}', '***REDACTED***', cmd_clean)
cmd_clean = re.sub(r'(?:eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{10,})', '***JWT***', cmd_clean)
# DG-008-v3: Sanitize lone surrogate escape sequences BEFORE writing to jsonl.
# U+D800 text in commands (e.g. Python code) → json.dumps → jsonl →
# inject-project-knowledge reads → AI context → API 400 lone surrogate error.
cmd_clean = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', cmd_clean)

# === Escape Pattern E1: Governance file bypass via Bash ===
# AI uses Bash (sed -i / tee / > / >>) to modify governance files,
# bypassing pretool-sensitive-edit (which only hooks Edit|Write tools).
# These are HIGH-VALUE signals — successful gate bypass, not a gate failure.
# NOTE: Only write operations trigger E1. Read-only ops (cat, grep, ls, find,
# python3 -m json.tool, etc.) are excluded to avoid false positives.
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
# Only detect write operations. Read-only ops are excluded.
E1_WRITE_PATTERN = re.compile(
    r'(?:^|\||;|&&)\s*(?:echo|printf)\s+.*?(?:>>?|\|tee)\s+'
    r'|(?:^|\||;|&&)\s*sed\s+(?:-i|--in-place)\s+'
    r'|(?:^|\||;|&&)\s*tee\s+'
    r'|(?:^|\||;|&&)\s*(?:cp|mv)\s+'
    r'|(?:^|\||;|&&)\s*cat\s+.*?(?:>|>>)\s+'
    r'|(?:^|\||;|&&)\s*python3?\s+.*?(?:open\(|\.write\(|\.writelines\()'
    r'|(?:^|\||;|&&)\s*install\s+'
    r'|>\s+\.claude/'
    r'|>>\s+\.claude/',
    re.IGNORECASE
)
IS_WRITE_CMD = bool(E1_WRITE_PATTERN.search(cmd_clean)) if cmd_clean else False
if IS_WRITE_CMD:
    for _gp in GOVERNANCE_PATHS:
        if _gp in cmd_clean:
            ESCAPE_E1 = True
            ESCAPE_E1_TARGET = _gp
            break

# Symlink resolution: check if command file args point to governance files via symlink
# Catches: AI creates /tmp/link -> .claude/settings.json then writes to /tmp/link
if IS_WRITE_CMD and not ESCAPE_E1:
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
# NOTE: Only write operations (echo >, > file, cp, mv, sed -i, tee)
# trigger E2. Read-only ops (ls, cat, grep, find) are excluded to
# avoid false positives when the AI inspects the state directory.
CAPTCHA_MARKERS = [
    'sensitive-approved', 'sensitive-required',
    'permission-approved', 'permission-required',
]
ESCAPE_E2 = False
ESCAPE_E2_TARGET = ''
# Only detect write operations (echo >/>>, cp, mv, sed, tee, cat >)
# Read-only ops (ls, cat without redirect, grep, find) are excluded.
E2_WRITE_PATTERN = re.compile(
    r'(?:echo|printf)\s+.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')'
    r'|(?:cp|mv|sed|tee)\s+.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')'
    r'|(?:>>?|>)\s*.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')',
    re.IGNORECASE
)
for _cm in CAPTCHA_MARKERS:
    if _cm in cmd_clean and E2_WRITE_PATTERN.search(cmd_clean):
        ESCAPE_E2 = True
        ESCAPE_E2_TARGET = _cm
        break

# E5 修复: 三 pipeline 消除症状混淆 — error-dna.jsonl 是主捕获文件（所有错误）
#               E1/E2 逃逸 → governance-audit.jsonl (审计追踪)
#               普通错误 → error-dna.jsonl (主捕获, 下游 C5/C9/E3 消费)
#               高频/低价值 gate 事件 → error-signals.jsonl (7天清除, 降噪)
# 哲学 #2(少量大增益): 逃逸和错误分轨，各取所需，互不污染
# 哲学 #4(验证): error-dna.jsonl 必须有数据，否则 Source III 无法评分
if not command:
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
# DG-008-v3: Sanitize lone surrogate escape sequences in message field too.
# stderr/stdout may contain \uDxxx text from tool output, separate path from cmd_clean.
message = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', message)
session_id = os.environ.get('SESSION_ID', 'unknown') or 'unknown'

# === Strip lone surrogates from all string fields before json.dumps ===
# DG-008-v4: json.dumps(ensure_ascii=False) serializes U+D800..U+DFFF chars
# as \uDxxx hex escapes in JSON output. DeepSeek JSON parser rejects these.
# Existing regex at lines 115/200 only handles literal \uDxxx text, not actual
# surrogate codepoints. Strip them here before JSON serialization.
def _strip_surrogates(s):
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not 0xD800 <= ord(c) <= 0xDFFF)

cmd_clean = _strip_surrogates(cmd_clean)
message = _strip_surrogates(message)
stdout = _strip_surrogates(stdout)
stderr = _strip_surrogates(stderr)

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
is_escape = False
if ESCAPE_E1:
    record['error_type'] = 'governance_bypass'
    record['escape_type'] = 'governance_bypass'
    record['message'] = f'E1: Bash bypass of governance file {ESCAPE_E1_TARGET} — cmd: {cmd_clean[:100]}'
    is_escape = True
elif ESCAPE_E2:
    record['error_type'] = 'captcha_forgery'
    record['escape_type'] = 'captcha_forgery'
    record['message'] = f'E2: CAPTCHA forgery targeting {ESCAPE_E2_TARGET} — cmd: {cmd_clean[:100]}'
    is_escape = True

# E5 修复: 三 pipeline 消除症状混淆
#   error-dna.jsonl = 主捕获文件（所有错误 + 逃逸），确保 Source III 评分有数据
#   governance-audit.jsonl = E1/E2 逃逸审计追踪（独立文件供安全审计）
#   error-signals.jsonl = 高频/低价值 gate 事件（7天清除，降噪）
# 旧逻辑: E2 → error-dna.jsonl（导致 0 输出症状混淆），E1 → governance-audit.jsonl，普通 → error-signals.jsonl
# 新逻辑: 全量 → error-dna.jsonl（主捕获），E1/E2 额外写入 governance-audit.jsonl（审计追踪）
#         gate 事件（exit_code >= 128 或 gate_operation）→ error-signals.jsonl（降噪）
if is_escape:
    # E1/E2 逃逸: 写 governance-audit.jsonl (审计追踪) + error-dna.jsonl (主捕获)
    audit_path = os.path.join(state_dir, 'governance-audit.jsonl')
    os.makedirs(state_dir, exist_ok=True)
    with open(audit_path, 'a', encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    jsonl_path = os.path.join(state_dir, 'error-dna.jsonl')
elif error_type == 'gate_operation' or exit_code >= 128:
    # Gate/high-exit events: 写 error-signals.jsonl (降噪)
    jsonl_path = os.path.join(state_dir, 'error-signals.jsonl')
else:
    # 普通错误: 写 error-dna.jsonl (主捕获)
    jsonl_path = os.path.join(state_dir, 'error-dna.jsonl')

os.makedirs(state_dir, exist_ok=True)
with open(jsonl_path, 'a', encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

# === Retry budget update (C9) — 所有记录，恢复完整追踪 ===
budget_path = os.path.join(state_dir, 'retry-budget.json')
budget = {'signatures': {}}
if os.path.isfile(budget_path):
    try:
        with open(budget_path, encoding="utf-8") as _bf:
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
with open(_btmp, 'w', encoding="utf-8") as _bf:
    json.dump(budget, _bf, indent=2, ensure_ascii=False)
os.rename(_btmp, budget_path)

# === Archive rotation (error-dna.jsonl only, R41 fix) ===
# E5 修复: 轮转适用于 error-dna.jsonl（主捕获文件），不再仅限于 E2 逃逸
_dna_path = os.path.join(state_dir, 'error-dna.jsonl')
try:
    _dna_size = os.path.getsize(_dna_path) if os.path.exists(_dna_path) else 0
    if _dna_size > int(os.environ.get('ERROR_DNA_ROTATION_SIZE', '1048576')):
        _rotate_dir = state_dir
        _archive_count = int(os.environ.get('ERROR_DNA_ARCHIVE_COUNT', '3'))
        for _i in range(_archive_count - 1, 0, -1):
            _old = os.path.join(_rotate_dir, f'error-dna.jsonl.{_i - 1}')
            _new = os.path.join(_rotate_dir, f'error-dna.jsonl.{_i}')
            if os.path.exists(_old):
                os.rename(_old, _new)
        _orphan = os.path.join(_rotate_dir, f'error-dna.jsonl.{_archive_count}')
        if os.path.exists(_orphan):
            os.unlink(_orphan)
        os.rename(_dna_path, os.path.join(_rotate_dir, 'error-dna.jsonl.0'))
        open(_dna_path, 'w', encoding="utf-8").close()
except Exception:
    pass

# error-signals.jsonl: 7天自动清除（轻量，无需轮转）
_signals_path = os.path.join(state_dir, 'error-signals.jsonl')
try:
    _sig_size = os.path.getsize(_signals_path) if os.path.exists(_signals_path) else 0
    if _sig_size > 524288:  # >512KB → 清空重启
        os.unlink(_signals_path)
except Exception:
    pass



# === Write structured patch suggestion for Oracle/human review ===
_patch_file = os.path.join(state_dir, 'escape-patches.json')
_patches = {}
if os.path.isfile(_patch_file):
    try:
        with open(_patch_file, encoding="utf-8") as _pf:
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
    with open(_ptmp, 'w', encoding="utf-8") as _pf:
        json.dump(_patches, _pf, indent=2, ensure_ascii=False)
    os.rename(_ptmp, _patch_file)

# B方案: 30天 pending 补丁自动过期 + 7天 archive 清理
_PATCH_EXPIRY_SEC = 30 * 86400
_ARCHIVE_MAX_AGE_SEC = 7 * 86400
_now = int(ts)
_patches_updated = False
for _pk, _pv in list(_patches.items()):
    if _pv.get('status') == 'pending' and (_now - _pv.get('ts', 0)) > _PATCH_EXPIRY_SEC:
        _pv['status'] = 'expired'
        _patches_updated = True
if _patches_updated:
    _ptmp = _patch_file + '.tmp'
    with open(_ptmp, 'w', encoding="utf-8") as _pf:
        json.dump(_patches, _pf, indent=2, ensure_ascii=False)
    os.rename(_ptmp, _patch_file)

# 7天 archive 清理
import glob as _glob
for _af in _glob.glob(os.path.join(state_dir, 'error-dna.jsonl.*')):
    try:
        _af_age = _now - os.path.getmtime(_af)
        if _af_age > _ARCHIVE_MAX_AGE_SEC:
            os.unlink(_af)
    except Exception:
        pass

# === Escape detection alert: immediate warning via additionalContext ===
if ESCAPE_E1:
    print(f"[E1] ⚠️ 治理文件绕过: {ESCAPE_E1_TARGET}")
    print(f"  Bash '{cmd_clean[:120]}' 绕过了 pretool-sensitive-edit 的 Edit|Write 门禁。")
    print(f"  escape_type=governance_bypass 已记录到 error-dna.jsonl + governance-audit.jsonl。")
    print(f"  补丁建议: 扩展 pretool-sensitive-edit matcher 到 Bash，或在 posttool-bash-audit 添加审计。")
elif ESCAPE_E2:
    print(f"[E2] ⚠️ 验证码伪造: {ESCAPE_E2_TARGET}")
    print(f"  Bash '{cmd_clean[:120]}' 尝试自写批准标记绕过 CAPTCHA 门禁 (R42 禁止)。")
    print(f"  escape_type=captcha_forgery 已记录到 error-dna.jsonl + governance-audit.jsonl。")
    print(f"  补丁建议: 检查 permission-gate.sh / pretool-sensitive-edit.sh 的验证码文件保护。")

# === High-frequency alert scan (scan both pipelines, lightweight) ===
_scanned = {}
_signals_path = os.path.join(state_dir, 'error-signals.jsonl')
_scan_paths = [jsonl_path]  # current record's pipeline
if os.path.exists(_signals_path) and _signals_path != jsonl_path:
    _scan_paths.append(_signals_path)

for _sp in _scan_paths:
    try:
        _scan_size = min(os.path.getsize(_sp) if os.path.exists(_sp) else 0, 102400)
        with open(_sp, encoding="utf-8") as _sf:
            _sf.seek(max(0, os.path.getsize(_sp) - _scan_size))
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

# 高频扫描: 信号文件中的 gate 操作是 E3/C5 的正常输入，不过滤
# 逃逸文件已天然过滤（只有 E1/E2），无需额外 gate 排除
_frequent = [(sig, info['count'], info['msg'])
             for sig, info in _scanned.items()
             if info['count'] >= 5]  # M3: raised from 3 to reduce toolchain noise
if _frequent:
    _frequent.sort(key=lambda x: -x[1])
    _lines = [f"[高频错误] 当前 jsonl 中 >=5 次的签名 ({len(_frequent)} 个):"]
    for sig, count, msg in _frequent[:5]:
        _lines.append(f'  · {sig[:16]} ×{count} — {msg[:100]}')
    print('|'.join(_lines))
PYEOF
)

# ── issue-triage 集成: 高频错误/新模式 → 分流 ──
# 使用临时文件传递数据给 python3 做安全的 JSON 合并（防 shell 注入 + JSON 协议损坏）
TRIAGE_MSG=""
# Meta-Oracle ADVISORY: 扩展 triage 覆盖 E1/E2 安全逃逸信号
if [ -n "$PY_OUTPUT" ] && (echo "$PY_OUTPUT" | grep -q "\[高频错误\]" || echo "$PY_OUTPUT" | grep -qE '\[E[12]\]'); then
    if [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
        TRIAGE_MSG=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook "error-dna" "高频错误模式检测: $(echo "$PY_OUTPUT" | head -3 | tr '\n' ' ')" "P1" "{}" 2>/dev/null || echo "")
    fi
fi

if [ -n "$PY_OUTPUT" ]; then
    if [ -n "$TRIAGE_MSG" ]; then
        # 安全合并: 通过 env var 传 triage_msg, python3 构造合法 JSON
        export TRIAGE_MSG
        echo "$PY_OUTPUT" | ${PYTHON_BIN:-python3} -c "
import json, sys, os
py_output = sys.stdin.read()
triage = os.environ.get('TRIAGE_MSG', '')
combined = py_output
if triage:
    combined += '\n' + triage
# DG-88-v2: strip surrogates before json.dumps to prevent lone surrogate API 400 errors
combined = ''.join(c for c in combined if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': combined}}))
"
    else
        echo "$PY_OUTPUT" | ${PYTHON_BIN:-python3} -c "
import json, sys
text = sys.stdin.read()
text = ''.join(c for c in text if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': text}}))
"
    fi
else
    echo '{"continue": true}'
fi
exit 0
