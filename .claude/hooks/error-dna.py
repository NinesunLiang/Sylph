#!/usr/bin/env python3
"""error-dna.py — PostToolUse:Bash / PostToolUseFailure:Bash — 轻量错误捕获（Oracle 瘦身后 v2）
Role: 捕获 Bash 错误写入 error-dna.jsonl + governance-audit.jsonl + total-ops 计数器 + 高频告警

等效移植自 error-dna.sh (538行)
"""

import glob
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue


def main():
    # ─── hc_enabled 门禁 ───
    if not hc_enabled('error_dna'):
        output_continue()
        return

    # 读取 stdin
    INPUT = sys.stdin.read()

    # ─── 解析 JSON ───
    try:
        data = json.loads(INPUT)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    tool_name = data.get('tool_name', '') or ''
    if not tool_name:
        tool_name = data.get('tool', '') or ''
    if not tool_name:
        tool_name = data.get('args', {}).get('tool_name', '') or ''
    tool_name = tool_name.lower()

    if tool_name != 'bash':
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # ─── 路径初始化 ───
    SCRIPT_DIR = _HOOKS_DIR
    PROJECT_ROOT = (SCRIPT_DIR / '../..').resolve()
    STATE_DIR = PROJECT_ROOT / '.omc' / 'state'
    TS = int(time.time())

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # DG-87: ensure error-dna.jsonl exists
    open(STATE_DIR / 'error-dna.jsonl', 'a').close()

    # DG-90: flywheel telemetry
    flywheel_event('error_dna', 'capture', 'P2')

    # Heartbeat
    open(STATE_DIR / 'error-dna-heartbeat.txt', 'a').close()

    # ─── 清理孤儿临时文件 ───
    now_ts = TS
    for f in STATE_DIR.glob('.error-dna-input-*.json'):
        try:
            if now_ts - f.stat().st_mtime > 3600:
                f.unlink(missing_ok=True)
        except Exception:
            pass

    # ─── 提取字段 ───
    tool_response = data.get('tool_response', {})
    tool_input = data.get('tool_input', {})
    exit_code = tool_response.get('exit_code', 0)
    command = tool_input.get('command', '') or ''
    stderr = tool_response.get('stderr', '') or ''
    stdout = tool_response.get('stdout', '') or ''

    # === Total-ops counter ===
    ops_path = STATE_DIR / 'total-ops.txt'
    try:
        current = int(open(ops_path, encoding='utf-8').read().strip())
    except (FileNotFoundError, ValueError):
        current = 0
    with open(ops_path, 'w', encoding='utf-8') as f:
        f.write(str(current + 1))

    # PostToolUseFailure schema
    top_error = data.get('error', '') or ''
    event_name = data.get('hook_event_name', '') or ''
    if event_name == 'PostToolUseFailure' or top_error:
        if exit_code == 0:
            exit_code = 1
        if not stderr:
            stderr = top_error

    # ─── Credential sanitization ───
    cmd_clean = re.sub(r'--password\s+\S+', '--password ***', command)
    cmd_clean = re.sub(r'--token\s+\S+', '--token ***', cmd_clean)
    cmd_clean = re.sub(r'--secret\s+\S+', '--secret ***', cmd_clean)
    cmd_clean = re.sub(r'--key\s+\S+', '--key ***', cmd_clean)
    cmd_clean = re.sub(
        r'(ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY|DEEPSEEK_BRIDGE_API_KEY|OPENAI_API_KEY|CODECLI_API_KEY|GEMINI_API_KEY)=\S+',
        r'\1=***', cmd_clean
    )
    cmd_clean = re.sub(r'(Authorization:\s*Bearer\s+)[^\s"<>]+', r'\1***', cmd_clean)
    cmd_clean = re.sub(r'(?:sk-|ghp_|xoxb-|xapp-)[a-zA-Z0-9_\-]{20,}', '***REDACTED***', cmd_clean)
    cmd_clean = re.sub(r'(?:eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{10,})', '***JWT***', cmd_clean)
    # DG-008-v3: Sanitize lone surrogate escape sequences
    cmd_clean = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', cmd_clean)

    # === Escape Pattern E1: Governance file bypass via Bash ===
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

    # Symlink resolution
    if IS_WRITE_CMD and not ESCAPE_E1:
        for _token in cmd_clean.split():
            _token = _token.strip("'\"")
            if _token.startswith('/') and os.path.exists(_token):
                _resolved = os.path.realpath(_token)
                if _resolved != _token:
                    for _gp in GOVERNANCE_PATHS:
                        if _gp in _resolved:
                            ESCAPE_E1 = True
                            ESCAPE_E1_TARGET = _gp
                            break
            if ESCAPE_E1:
                break

    # === Escape Pattern E2: CAPTCHA forgery ===
    CAPTCHA_MARKERS = [
        'sensitive-approved', 'sensitive-required',
        'permission-approved', 'permission-required',
        'oracle-gate-approved', 'oracle-gate-required',
    ]
    ESCAPE_E2 = False
    ESCAPE_E2_TARGET = ''
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

    if not command:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # === Inline classifier ===
    cmd_normalized = re.sub(
        r'\b\d{8}[-_]\d{6}\b'
        r'|\b\d{4}[-_]\d{2}[-_]\d{2}[T ]\d{2}[-_:]\d{2}[-_:]\d{2}\b'
        r'|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
        r'|/tmp/[^\s]+|/private/tmp/[^\s]+',
        '<NORMALIZED>', cmd_clean
    )
    signature = hashlib.md5(cmd_normalized.encode()).hexdigest()[:16]
    cmd_lower = cmd_clean.lower()

    if any(x in cmd_lower for x in ['go build', 'go test', 'npm run build', 'npm build', 'cargo build', 'tsc',
                                     'python3 -c', 'python3 -', 'node ', 'deno ', 'make ', 'cmake ', 'mvn ', 'gradle ']):
        error_type = 'build'
    elif any(x in cmd_lower for x in ['go test', 'npm test', 'pytest', 'jest']):
        error_type = 'test'
    elif any(x in cmd_lower for x in ['git']):
        error_type = 'git'
    elif any(x in cmd_lower for x in ['npm install', 'go get', 'pip install', 'brew ', 'gem install', 'cargo install']):
        error_type = 'dependency'
    elif any(x in cmd_lower for x in ['lint', 'eslint', 'golangci-lint', 'shellcheck', 'bash -n']):
        error_type = 'lint'
    elif any(x in cmd_lower for x in ['docker']):
        error_type = 'docker'
    elif any(x in cmd_lower for x in ['curl', 'wget', 'http', 'ssh ', 'api.', 'fetch']):
        error_type = 'network'
    elif any(x in cmd_lower for x in ['find', 'grep', 'sed', 'awk']):
        error_type = 'file_ops'
    else:
        error_type = 'runtime'

    output_snippet = (stderr or stdout)[:500]
    message = output_snippet[:200].replace('\n', ' ').replace('\r', ' ').strip()
    message = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', message)
    session_id = os.environ.get('SESSION_ID', 'unknown') or 'unknown'

    # Strip lone surrogates from all string fields
    def _strip_surrogates(s):
        if not isinstance(s, str):
            return s
        return ''.join(c for c in s if not 0xD800 <= ord(c) <= 0xDFFF)

    cmd_clean = _strip_surrogates(cmd_clean)
    message = _strip_surrogates(message)
    stdout = _strip_surrogates(stdout)
    stderr = _strip_surrogates(stderr)

    # === Build record ===
    record = {
        'ts': TS,
        'signature': signature,
        'cmd': cmd_clean,
        'exit_code': exit_code,
        'error_type': error_type,
        'message': message,
        'session_id': session_id,
        'escape_type': '',
    }

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

    if is_escape:
        audit_path = STATE_DIR / 'governance-audit.jsonl'
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(audit_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        jsonl_path = STATE_DIR / 'error-dna.jsonl'
    elif error_type == 'gate_operation' or exit_code >= 128:
        jsonl_path = STATE_DIR / 'error-signals.jsonl'
    else:
        jsonl_path = STATE_DIR / 'error-dna.jsonl'

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # === Retry budget update (C9) ===
    budget_path = STATE_DIR / 'retry-budget.json'
    budget = {'signatures': {}}
    if budget_path.is_file():
        try:
            with open(budget_path, encoding='utf-8') as _bf:
                budget = json.load(_bf)
        except Exception:
            pass
    sigs = budget.get('signatures', {})
    if signature not in sigs:
        sigs[signature] = {
            'retry_count': 0, 'label': message[:80],
            'first_seen': TS, 'error_type': error_type
        }
    sigs[signature]['retry_count'] = sigs[signature].get('retry_count', 0) + 1
    sigs[signature]['last_retry'] = TS
    sigs[signature]['label'] = message[:80]
    budget['signatures'] = sigs
    _btmp = str(budget_path) + '.tmp'
    with open(_btmp, 'w', encoding='utf-8') as _bf:
        json.dump(budget, _bf, indent=2, ensure_ascii=False)
    os.rename(_btmp, budget_path)

    # === Archive rotation (error-dna.jsonl only) ===
    _dna_path = STATE_DIR / 'error-dna.jsonl'
    try:
        _dna_size = os.path.getsize(_dna_path) if _dna_path.exists() else 0
        rotation_size = int(os.environ.get('ERROR_DNA_ROTATION_SIZE', '1048576'))
        if _dna_size > rotation_size:
            _rotate_dir = STATE_DIR
            _archive_count = int(os.environ.get('ERROR_DNA_ARCHIVE_COUNT', '3'))
            for _i in range(_archive_count - 1, 0, -1):
                _old = _rotate_dir / f'error-dna.jsonl.{_i - 1}'
                _new = _rotate_dir / f'error-dna.jsonl.{_i}'
                if _old.exists():
                    os.rename(str(_old), str(_new))
            _orphan = _rotate_dir / f'error-dna.jsonl.{_archive_count}'
            if _orphan.exists():
                _orphan.unlink(missing_ok=True)
            os.rename(str(_dna_path), str(_rotate_dir / 'error-dna.jsonl.0'))
            open(_dna_path, 'w', encoding='utf-8').close()
    except Exception:
        pass

    # error-signals.jsonl: 7天自动清除
    _signals_path = STATE_DIR / 'error-signals.jsonl'
    try:
        _sig_size = os.path.getsize(_signals_path) if _signals_path.exists() else 0
        if _sig_size > 524288:
            _signals_path.unlink(missing_ok=True)
    except Exception:
        pass

    # === Write structured patch suggestion ===
    _patch_file = STATE_DIR / 'escape-patches.json'
    _patches = {}
    if _patch_file.is_file():
        try:
            with open(_patch_file, encoding='utf-8') as _pf:
                _patches = json.load(_pf)
        except Exception:
            pass

    _patch_key = ''
    _is_new_patch = False
    if ESCAPE_E1:
        _patch_key = 'e1_' + ESCAPE_E1_TARGET.replace('/', '_').replace('.', '_')
        if _patch_key not in _patches:
            _is_new_patch = True
            _patches[_patch_key] = {
                'type': 'governance_bypass',
                'target': ESCAPE_E1_TARGET,
                'command': cmd_clean[:200],
                'recommendation': '扩展 pretool-sensitive-edit matcher 到 Bash，或在 posttool-bash-audit 添加 governance_bypass 审计规则',
                'severity': 'high',
                'ts': TS,
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
                'ts': TS,
                'status': 'pending'
            }

    if _is_new_patch:
        _ptmp = str(_patch_file) + '.tmp'
        with open(_ptmp, 'w', encoding='utf-8') as _pf:
            json.dump(_patches, _pf, indent=2, ensure_ascii=False)
        os.rename(_ptmp, _patch_file)

    # Patch expiry: 30天 pending 自动过期
    _PATCH_EXPIRY_SEC = 30 * 86400
    _ARCHIVE_MAX_AGE_SEC = 7 * 86400
    _now = TS
    _patches_updated = False
    for _pk, _pv in list(_patches.items()):
        if _pv.get('status') == 'pending' and (_now - _pv.get('ts', 0)) > _PATCH_EXPIRY_SEC:
            _pv['status'] = 'expired'
            _patches_updated = True
    if _patches_updated:
        _ptmp = str(_patch_file) + '.tmp'
        with open(_ptmp, 'w', encoding='utf-8') as _pf:
            json.dump(_patches, _pf, indent=2, ensure_ascii=False)
        os.rename(_ptmp, _patch_file)

    # 7天 archive 清理
    for _af in STATE_DIR.glob('error-dna.jsonl.*'):
        try:
            _af_age = _now - os.path.getmtime(_af)
            if _af_age > _ARCHIVE_MAX_AGE_SEC:
                _af.unlink(missing_ok=True)
        except Exception:
            pass

    # === Escape detection alert: stderr output ===
    if ESCAPE_E1:
        print('[E1] ⚠️ 治理文件绕过: ' + ESCAPE_E1_TARGET, file=sys.stderr, flush=True)
        print("  Bash '" + cmd_clean[:120] + "' 绕过了 pretool-sensitive-edit 的 Edit|Write 门禁。", file=sys.stderr, flush=True)
        print("  escape_type=governance_bypass 已记录到 error-dna.jsonl + governance-audit.jsonl。", file=sys.stderr, flush=True)
        print("  补丁建议: 扩展 pretool-sensitive-edit matcher 到 Bash，或在 posttool-bash-audit 添加审计。", file=sys.stderr, flush=True)
    elif ESCAPE_E2:
        print('[E2] ⚠️ 验证码伪造: ' + ESCAPE_E2_TARGET, file=sys.stderr, flush=True)
        print("  Bash '" + cmd_clean[:120] + "' 尝试自写批准标记绕过 CAPTCHA 门禁 (R42 禁止)。", file=sys.stderr, flush=True)
        print("  escape_type=captcha_forgery 已记录到 error-dna.jsonl + governance-audit.jsonl。", file=sys.stderr, flush=True)
        print("  补丁建议: 检查 permission-gate.sh / pretool-sensitive-edit.sh 的验证码文件保护。", file=sys.stderr, flush=True)

    # === High-frequency alert scan ===
    _scanned = {}
    _scan_paths = [jsonl_path]
    if _signals_path.exists() and _signals_path != jsonl_path:
        _scan_paths.append(_signals_path)

    for _sp in _scan_paths:
        try:
            _sp_size = os.path.getsize(_sp) if _sp.exists() else 0
            _scan_size = min(_sp_size, 102400)
            if _scan_size > 0:
                with open(_sp, encoding='utf-8') as _sf:
                    _sf.seek(max(0, _sp_size - _scan_size))
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
                 if info['count'] >= 5]
    if _frequent:
        _frequent.sort(key=lambda x: -x[1])
        _lines = ['[高频错误] 当前 jsonl 中 >=5 次的签名 ({} 个):'.format(len(_frequent))]
        for sig, count, msg in _frequent[:5]:
            _lines.append('  · {} ×{} — {}'.format(sig[:16], count, msg[:100]))
        print('|'.join(_lines), file=sys.stderr, flush=True)

    # === Issue-triage integration ===
    TRIAGE_MSG = ''
    # Build the PY_OUTPUT string that the bash version would produce for triage logic
    py_output_lines = []
    if ESCAPE_E1 or ESCAPE_E2:
        py_output_lines.append('[E1]' if ESCAPE_E1 else '[E2]')
    if _frequent:
        py_output_lines.append('[高频错误]')
    PY_OUTPUT = '|'.join(py_output_lines) if py_output_lines else ''

    if PY_OUTPUT and ('[高频错误]' in PY_OUTPUT or '[E1]' in PY_OUTPUT or '[E2]' in PY_OUTPUT):
        triage_script = SCRIPT_DIR / '..' / 'scripts' / 'issue-triage.sh'
        if triage_script.exists():
            import subprocess
            try:
                result = subprocess.run(
                    ['bash', str(triage_script)],
                    input='', capture_output=True, text=True, timeout=10,
                    env={**os.environ, 'TRIAGE_HOOK': 'error-dna', 'TRIAGE_MESSAGE': '高频错误模式检测: ' + PY_OUTPUT[:200], 'TRIAGE_PRIORITY': 'P1'}
                )
                # The function triage_for_hook needs to be sourced, this is a simplified approach
                # We'll just skip triage if it fails
            except Exception:
                pass

    # === Output JSON ===
    combined = PY_OUTPUT
    if TRIAGE_MSG:
        combined += '\n' + TRIAGE_MSG if combined else TRIAGE_MSG

    if combined:
        combined = ''.join(c for c in combined if not (0xD800 <= ord(c) <= 0xDFFF))
        print(json.dumps({
            'continue': True,
            'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext': combined
            }
        }))
    else:
        print(json.dumps({'continue': True}))
    sys.exit(0)


if __name__ == '__main__':
    main()
