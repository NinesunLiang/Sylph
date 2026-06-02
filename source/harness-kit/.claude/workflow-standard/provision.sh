#!/usr/bin/env bash
# workflow-standard/provision.sh — 一键部署到 Claude Code / OpenCode 项目
# 用法: bash .claude/workflow-standard/provision.sh
#
# 将五阶段工作流行为标准注入到当前项目的 settings.json
# 可重复运行——已存在的 hook 条目不重复添加

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETTINGS="$PROJECT_ROOT/.claude/settings.json"
STATE_DIR="$PROJECT_ROOT/.claude/state"

echo "=========================================="
echo " Workflow Standard v4.0 — 部署"
echo "=========================================="
echo " 项目: $PROJECT_ROOT"
echo ""

# 检查 settings.json
if [ ! -f "$SETTINGS" ]; then
    echo "❌ 未找到 .claude/settings.json — 请先初始化 Claude Code"
    exit 1
fi

# 检查 python3
if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 python3"
    exit 1
fi

# 创建 state 目录
mkdir -p "$STATE_DIR"

# 复制状态模板（如果不存在）
if [ ! -f "$STATE_DIR/workflow-state.json" ]; then
    cp "$SCRIPT_DIR/state/workflow-state.json.template" "$STATE_DIR/workflow-state.json"
    echo "✅ 状态模板已创建: .claude/state/workflow-state.json"
else
    echo "⏭️  状态文件已存在，跳过"
fi

# 注入 hooks 到 settings.json
echo ""
echo "正在注入 hooks..."

python3 -c "
import json, os, sys

settings_file = '''$SETTINGS'''
hooks_dir = '''$SCRIPT_DIR/hooks'''

with open(settings_file) as f:
    s = json.load(f)

hooks = s.setdefault('hooks', {})

# ─── PreToolUser:Edit|Write|Bash — workflow gate ───
pre = hooks.setdefault('PreToolUse', [])
edit_write_block = None
for block in pre:
    if block.get('matcher') == 'Edit|Write|Bash':
        edit_write_block = block
        break
if not edit_write_block:
    edit_write_block = {'matcher': 'Edit|Write|Bash', 'hooks': []}
    pre.append(edit_write_block)

existing_cmds = {h.get('command', '') for h in edit_write_block['hooks']}
gate_cmd = 'bash $PROJECT_ROOT/.claude/workflow-standard/hooks/pretool-workflow-gate'
if gate_cmd not in existing_cmds:
    edit_write_block['hooks'].append({
        'type': 'command',
        'command': gate_cmd,
        'timeout': 5000
    })
    print('  ✅ PreToolUse:Edit|Write|Bash → pretool-workflow-gate')

# ─── PostToolUse:TaskUpdate — checkpoint ───
post = hooks.setdefault('PostToolUse', [])
for block in post:
    if block.get('matcher') == 'TaskUpdate':
        existing_cmds = {h.get('command', '') for h in block['hooks']}
        cp_cmd = 'bash $PROJECT_ROOT/.claude/workflow-standard/hooks/checkpoint'
        if cp_cmd not in existing_cmds:
            block['hooks'].append({
                'type': 'command',
                'command': cp_cmd,
                'timeout': 5000
            })
            print('  ✅ PostToolUse:TaskUpdate → checkpoint')
        break

# ─── SessionStart — recovery + inject ───
ss = hooks.setdefault('SessionStart', [])
session_block = None
for block in ss:
    if 'hooks' in block and isinstance(block.get('hooks'), list):
        session_block = block
        break
if not session_block:
    session_block = {'hooks': []}
    ss.append(session_block)

existing_cmds = {h.get('command', '') for h in session_block['hooks']}
recov_cmd = 'bash $PROJECT_ROOT/.claude/workflow-standard/hooks/state-recovery'
inj_cmd = 'bash $PROJECT_ROOT/.claude/workflow-standard/hooks/session-inject'

for cmd, name in [(recov_cmd, 'state-recovery'), (inj_cmd, 'session-inject')]:
    if cmd not in existing_cmds:
        session_block['hooks'].append({
            'type': 'command',
            'command': cmd,
            'timeout': 5000
        })
        print(f'  ✅ SessionStart → {name}')

# 写回
os.rename(settings_file, settings_file + '.pre-workflow.bak')
with open(settings_file, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)
print(f'  📄 已备份原 settings.json → .claude/settings.json.pre-workflow.bak')
"

echo ""
echo "=========================================="
echo " ✅ 部署完成"
echo "=========================================="
echo ""
echo "下一步: 用 'workflow start <任务描述>' 启动工作流"
echo "卸载: bash .claude/workflow-standard/deprovision.sh"
echo ""
