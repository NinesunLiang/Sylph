#!/usr/bin/env bash
# workflow-standard/deprovision.sh — 一键卸载
# 用法: bash .claude/workflow-standard/deprovision.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETTINGS="$PROJECT_ROOT/.claude/settings.json"

echo "=========================================="
echo " Workflow Standard — 卸载"
echo "=========================================="

if [ ! -f "$SETTINGS" ]; then
    echo "无 settings.json，无需卸载"
    exit 0
fi

if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 python3"
    exit 1
fi

python3 -c "
import json, os

settings_file = '''$SETTINGS'''
with open(settings_file) as f:
    s = json.load(f)

# 过滤掉所有 workflow-standard 的 hook 条目
pre = s.get('hooks', {}).get('PreToolUse', [])
for block in pre:
    block['hooks'] = [h for h in block.get('hooks', []) if 'workflow-standard/hooks/' not in h.get('command', '')]

post = s.get('hooks', {}).get('PostToolUse', [])
for block in post:
    block['hooks'] = [h for h in block.get('hooks', []) if 'workflow-standard/hooks/' not in h.get('command', '')]

ss = s.get('hooks', {}).get('SessionStart', [])
for block in ss:
    block['hooks'] = [h for h in block.get('hooks', []) if 'workflow-standard/hooks/' not in h.get('command', '')]

# 清理空 block
s['hooks']['PreToolUse'] = [b for b in pre if b.get('hooks')]
s['hooks']['PostToolUse'] = [b for b in post if b.get('hooks')]
s['hooks']['SessionStart'] = [b for b in ss if b.get('hooks')]

os.rename(settings_file, settings_file + '.pre-uninstall.bak')
with open(settings_file, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)
"

echo "✅ 已移除所有 workflow-standard hooks"
echo "📄 备份: .claude/settings.json.pre-uninstall.bak"
echo "📁 状态文件保留: .claude/state/workflow-state.json (手动删除如需清理)"
