#!/usr/bin/env bash
# inject-project-knowledge.sh — SessionStart — 注入紧凑记忆恢复文件
# Role: 注入 todo-queue.md(最近询问+任务摘要) + session-handoff.md + session-dump.json
# 哲学 #4(验证): 压缩后记忆恢复; 哲学 #7(文档优先): 从文件恢复而非依赖记忆

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "inject_project_knowledge" || { echo '{"continue": true}'; exit 0; }

STATE_DIR="$PROJECT_ROOT/.omc/state"

# 1. Inject todo-queue.md (recent prompts + task summary)
TODO_FILE="$STATE_DIR/todo-queue.md"
if [ -f "$TODO_FILE" ]; then
    echo ""
    echo "--- 紧凑记忆恢复: 最近询问 + 任务摘要 ---"
    head -40 "$TODO_FILE"
    echo ""
fi

# 2. Inject session-handoff.md (feature progress + decisions)
HANDOFF_FILE="$STATE_DIR/session-handoff.md"
if [ -f "$HANDOFF_FILE" ]; then
    echo ""
    echo "--- 会话交接: 进度 + 决策 ---"
    head -30 "$HANDOFF_FILE"
    echo ""
fi

# 3. Inject session-dump.json summary (modified files + errors)
DUMP_FILE="$STATE_DIR/session-dump.json"
if [ -f "$DUMP_FILE" ]; then
    echo ""
    echo "--- 会话状态摘要 ---"
    ${PYTHON_BIN:-python3} -c "
import json, sys
try:
    d = json.load(open('$DUMP_FILE', encoding='utf-8'))
except:
    sys.exit(0)
gs = d.get('git_state', {})
mf = gs.get('modified_files', [])
if mf:
    print(f'修改文件 ({len(mf)}): ' + ', '.join(mf[:5]))
el = d.get('edit_log', [])
if el:
    print(f'编辑文件 ({len(el)}): ' + ', '.join(el[:5]))
es = d.get('error_summary', {})
if es.get('unfixed_count', 0) > 0:
    print(f'未修复错误: {es[\"unfixed_count\"]}')
af = d.get('active_features', [])
if af:
    names = [str(a.get('feature', '?')) if isinstance(a, dict) else str(a) for a in af]
    print(f'活跃特性: {\" | \".join(names[:3])}')
" 2>/dev/null || true
    echo ""
fi

# 4. Inject session-handoff-v2.json (跨平台 handoff, compact后恢复)
HANDOFF_V2="$STATE_DIR/session-handoff-v2.json"
if [ -f "$HANDOFF_V2" ]; then
    echo ""
    echo "--- 会话恢复 (handoff-v2) ---"
    ${PYTHON_BIN:-python3} -c "
import json
with open('$HANDOFF_V2', encoding='utf-8') as f:
    d = json.load(f)
print(f'任务: {d.get(\"task_summary\", \"无\")}')
print(f'已完成: {len(d.get(\"completed_tasks\", []))}')
print(f'待完成: {len(d.get(\"pending_tasks\", []))}')
print(f'分支: {d.get(\"working_branch\", \"\")}')
print(f'修改文件: {len(d.get(\"modified_files\", []))}')
print(f'最近询问: {len(d.get(\"queries\", []))} 条')
print(f'详情: {d.get(\"task_detail\", \"\")}')
print()
print('【必须遵守】禁止编造|用户裁定|证据门禁|Git门禁|范围冻结|隐私防线|断言真实|哲学先行')
" 2>/dev/null || true
    echo ""
fi

echo '{"continue": true}'
exit 0
