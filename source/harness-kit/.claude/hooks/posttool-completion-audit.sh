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
exit 0
