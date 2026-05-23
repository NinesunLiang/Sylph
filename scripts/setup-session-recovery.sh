#!/bin/bash
# setup-session-recovery.sh — 跨会话恢复: SessionStart注入选择提示
set -e

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
INJECT_SCRIPT="$PROJECT/.claude/hooks/inject-project-knowledge.sh"

# Backup
cp "$INJECT_SCRIPT" "$INJECT_SCRIPT.bak"

# Add session recovery section before the exit (before line containing "exit 0" at end)
# Insert after the TODO/待决策 section, before the final cleanup
python3 -c "
path = '$INJECT_SCRIPT'
with open(path) as f:
    content = f.read()

recovery_block = '''

# ─── 跨会话恢复提示 (Session Recovery) ───
SESSION_DUMP=\"\$PROJECT_ROOT/.omc/state/session-dump.json\"
TODO_QUEUE=\"\$PROJECT_ROOT/.omc/state/todo-queue.md\"
HANDOFF=\"\$PROJECT_ROOT/.omc/state/session-handoff.md\"

HAS_PREV=false
[ -f \"\$SESSION_DUMP\" ] && HAS_PREV=true
[ -f \"\$TODO_QUEUE\" ] && HAS_PREV=true
[ -f \"\$HANDOFF\" ] && HAS_PREV=true

if [ \"\$HAS_PREV\" = true ]; then
    echo \"\"
    echo \"╔══════════════════════════════════════╗\"
    echo \"║  📋 检测到上次会话未完成的任务       ║\"
    echo \"╠══════════════════════════════════════╣\"

    # Last session summary
    if [ -f \"\$SESSION_DUMP\" ]; then
        python3 -c \"
import json
try:
    with open('\$SESSION_DUMP') as f: d = json.load(f)
    gs = d.get('git_state',{})
    br = gs.get('branch','?')
    mf = gs.get('modified_files',[])
    print(f'║  分支: {br}  修改文件: {len(mf)}个')
    tq = d.get('todo_queue',[])
    if tq:
        for t in tq[:3]:
            print(f'║  · {str(t)[:80]}')
except: pass
\" 2>/dev/null
    fi

    # TODO summary
    if [ -f \"\$TODO_QUEUE\" ]; then
        TODO_COUNT=\$(grep -c '^\\- \\[ \\]' \"\$TODO_QUEUE\" 2>/dev/null || echo 0)
        echo \"║  待办: \${TODO_COUNT}项\"
    fi

    # Handoff
    if [ -f \"\$HANDOFF\" ]; then
        NEXT_STEP=\$(grep '下一步\\|Next' \"\$HANDOFF\" 2>/dev/null | head -1 || echo '')
        [ -n \"\$NEXT_STEP\" ] && echo \"║  \${NEXT_STEP:0:70}\"
    fi

    echo \"╠══════════════════════════════════════╣\"
    echo \"║  输入「继续」→ 恢复上次任务         ║\"
    echo \"║  输入「重新开始」→ 从零开始         ║\"
    echo \"║  不回应 → 默认继续                  ║\"
    echo \"╚══════════════════════════════════════╝\"
    echo \"\"
fi
'''

# Insert before the final exit 0
content = content.replace(
    '# 注入 Retry Budget 状态',
    recovery_block + '# 注入 Retry Budget 状态'
)

with open(path, 'w') as f:
    f.write(content)

print('Session recovery prompt injected into inject-project-knowledge.sh')
"

bash -n "$INJECT_SCRIPT" && echo "Syntax OK" || { echo "Syntax FAILED, restoring backup"; cp "$INJECT_SCRIPT.bak" "$INJECT_SCRIPT"; exit 1; }

# Cleanup old packages
rm -f "$PROJECT/packages/harness-kit-v6.2.2"[4-5]-stable.tar.gz "$PROJECT/packages/lx-skills-v6.2.2"[4-5]-stable.tar.gz 2>/dev/null || true

echo "=== Ready to release ==="
echo "Run: bash scripts/release.sh patch 'feat: 跨会话恢复 — SessionStart提示继续/重新开始' --yes"
