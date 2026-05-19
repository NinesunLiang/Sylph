#!/usr/bin/env bash
# posttool-completion-audit.sh — PostToolUse — 独立验证 evidence 质量（E3/E7 防御纵深）
# Role: PostToolUse 独立验证证据文件质量，不依赖 completion-gate 的门禁逻辑
#
# 原理：
#   completion-gate.sh 是 PreToolUse 门禁（阻断无证据的完成声明）。
#   本 hook 是 PostToolUse 兜底扫描 — 即使门禁被绕过（如 ghost mode 降级），
#   本 hook 仍会检查 evidence 文件质量并记录异常，形成 E3/E7 双层防御。

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_completion_audit" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 提取 tool 和 status 字段
TOOL=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool', ''))
except:
    pass" 2>/dev/null)

# 只检查 TaskUpdate completed
if [ "$TOOL" != "TaskUpdate" ]; then
    echo '{"continue": true}'
    exit 0
fi

STATUS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('status', ''))
except:
    pass" 2>/dev/null)

[ "$STATUS" != "completed" ] && { echo '{"continue": true}'; exit 0; }

# 独立检查 evidence 文件质量
EVIDENCE_FILE="$STATE_DIR/.completion-evidence-$(date +%Y%m%d)"

if [ ! -f "$EVIDENCE_FILE" ]; then
    echo "[completion-audit] ⚠️ TaskUpdate completed 但无证据文件" >&2
    echo '{"continue": true}'
    exit 0
fi

# 检查证据质量（独立于 completion-gate 的逻辑）
python3 -c "
import os, re, json

ef = '$EVIDENCE_FILE'

try:
    with open(ef) as f:
        content = f.read()
except:
    print('[completion-audit] ⚠️ 无法读取证据文件', file=__import__('sys').stderr)
    exit(0)

issues = []

# 1. 长度检查
MIN_CHARS = 20
if len(content) < MIN_CHARS:
    issues.append('证据过短(%d字符<%d)' % (len(content), MIN_CHARS))

# 2. VERIFIED 关键字检查
if 'VERIFIED' not in content:
    issues.append('缺少 VERIFIED 关键字')

# 3. file:line 引用检查
fl_count = len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
if fl_count == 0:
    issues.append('无 file:line 引用')

# 4. 软完成语检查
soft_words = ['应该没问题', '基本完成', '大部分完成', '差不多', '理论上可行',
              '看起来正常', '之前验证过', 'should be fine', 'basically done',
              'mostly complete', 'seems to work', 'should work', 'looks good']
for w in soft_words:
    if w in content:
        issues.append('含软完成语: %s' % w)
        break

# 5. B1: 结构完整性 — 证据中是否有完成标记和结构化引用
ac_count = len(re.findall(r'AC\s*[#:]\s*\d+|收条件|C\d+', content))
check_count = len(re.findall(r'\[[xX]\]\s', content))
verified_count = content.count('VERIFIED')
step_count = len(re.findall(r'步骤\s*\d+|Step\s*\d+', content))
if ac_count == 0 and check_count == 0 and verified_count <= 1 and step_count == 0:
    issues.append('证据缺少结构化完成标记(AC#/checkbox/VERIFIED)')

# 6. B1: 命令输出存在性 — 证据不能只有断言，必须有执行痕迹
has_cmd_output = bool(re.search(
    r'✅|❌|⚠️|PASS|FAIL|ERROR|OK|WARN|'
    r'\d+\s*passed|\d+\s*failed|'
    r'error:|Error:|ERROR:|'
    r'[a-z]+\.[a-z]+:\d+:\d+|'
    r'compilation|build.succeeded|BUILD',
    content))
has_shell = bool(re.search(r'(?m)^[\$>]\s', content))
has_paths = len(re.findall(r'/[\w/-]+\.[a-z]+', content)) > 3
if not has_cmd_output and not has_shell and not has_paths:
    issues.append('证据无实际命令输出(仅有断言，缺少执行痕迹)')

if issues:
    audit_log = os.path.join('$STATE_DIR', 'completion-audit.jsonl')
    record = {
        'ts': int(__import__('time').time()),
        'type': 'evidence_quality',
        'issues': issues,
        'file': ef,
        'content_len': len(content),
        'fl_count': fl_count,
    }
    with open(audit_log, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print('[completion-audit] ⚠️ 证据质量缺陷:', '; '.join(issues), file=__import__('sys').stderr)
else:
    print('[completion-audit] ✅ 证据质量通过', file=__import__('sys').stderr)

# 留痕到 flywheel（P1 级别）
if issues:
    flywheel_log = os.path.expanduser('~/.claude/flywheel.log')
    with open(flywheel_log, 'a') as f:
        f.write('%s,completion_audit_defect,P1,carror-os\n' %
                __import__('datetime').datetime.now().strftime('%Y-%m-%d'))
" 2>/dev/null || true

echo '{"continue": true}'
flywheel_event "posttool_completion_audit" "evidence_audited" "P2" "audited"
exit 0
