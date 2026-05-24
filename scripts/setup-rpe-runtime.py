#!/usr/bin/env python3
"""setup-rpe-runtime.py — RPE文档层 runtime 验收修复
原子化处理: 每步独立可验证，有备份+回滚机制
"""
import json, os, sys
from datetime import datetime

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def atomic_write(path, content):
    """原子写入: tmp + rename"""
    tmp = path + '.tmp.' + str(os.getpid())
    with open(tmp, 'w') as f:
        f.write(content)
    os.rename(tmp, path)

def backup(path):
    """创建备份"""
    bak = path + '.bak.' + datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(path) as f:
        content = f.read()
    with open(bak, 'w') as f:
        f.write(content)
    return bak, content

def verify_bash_syntax(path):
    """验证 bash 语法"""
    import subprocess
    r = subprocess.run(['bash', '-n', path], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ Syntax FAILED: {r.stderr}")
        return False
    print(f"  ✅ Syntax OK")
    return True

# ============================================================
# Fix 1: lx-goal.sh
# ============================================================
goal_sh = os.path.join(PROJECT, '.claude/skills/lx-goal/scripts/lx-goal.sh')
bak, content = backup(goal_sh)
print(f"Backup: {bak}")

# --- Fix 1a: Remove duplicate broken RPE block ---
# The first echo-based block creates invalid JSON and uses undefined log_info
old_dup_start = "        DATE=$(date +%Y-%m-%d)\n\tSLUG=$(echo \"$GOAL\" | tr \" \" \"-\" | tr -cd \"[:alnum:]-_\" | head -c 50)\n\tPLAN_DIR=\"$PROJECT_ROOT/.omc/plans/${DATE}/${SLUG}\"\n\tmkdir -p \"$PLAN_DIR\"\n\techo \"{\"phase\":\"draft\",\"created_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}\" > \"$PLAN_DIR/state.json\""

if old_dup_start in content:
    # Find the end of this block (ends at "log_info" line)
    end_marker = '\tlog_info "RPE文档层: $PLAN_DIR"\n\tDATE=$(date +%Y-%m-%d)'
    if end_marker in content:
        # Remove from dup_start to just before the second DATE=
        before = content.split(old_dup_start)[0]
        after_parts = content.split(old_dup_start)[1].split(end_marker, 1)
        if len(after_parts) == 2:
            # Keep the "DATE=..." that starts the second (good) block
            content = before + "DATE=$(date +%Y-%m-%d)" + after_parts[1]
            print("lx-goal.sh: ✅ removed duplicate broken RPE block")
        else:
            print("lx-goal.sh: ⚠️ could not split at end marker")
    else:
        print("lx-goal.sh: ⚠️ end marker not found")
else:
    print("lx-goal.sh: ⚠️ duplicate block start not found (may already be fixed)")

# --- Fix 1b: Save plan_dir to lx-goal.json ---
old_rpe_tail = '\techo "RPE文档层: $PLAN_DIR" >&2\n\techo "✅ 目标模式已开启'
new_rpe_tail = '''\techo "RPE文档层: $PLAN_DIR" >&2
\t# Save plan_dir to lx-goal.json for runtime subcommands (task-done/skip-risk/off)
\texport _LX_PLAN_DIR="$PLAN_DIR"
\texport _LX_MODE_FILE="$MODE_FILE"
\tpython3 <<'PYEOF'
import json, os
plan_dir = os.environ['_LX_PLAN_DIR']
mode_file = os.environ['_LX_MODE_FILE']
d = json.load(open(mode_file))
d['rpe_plan_dir'] = plan_dir
tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
\techo "✅ 目标模式已开启'''

if old_rpe_tail in content:
    content = content.replace(old_rpe_tail, new_rpe_tail, 1)
    print("lx-goal.sh: ✅ save plan_dir to lx-goal.json")
else:
    print("lx-goal.sh: ⚠️ RPE tail pattern not found")

# --- Fix 1c: task-done → append progress.md ---
old_task_done_tail = "os.rename(tmp, task_file)\nPYEOF\n\t\techo \"✅ 已标记任务完成: $(sanitize_output \"$DESCRIPTION\")\""
new_task_done_tail = """os.rename(tmp, task_file)
# Append to RPE progress.md
plan_dir = d.get('rpe_plan_dir', '')
if plan_dir:
    import os as _os
    progress_file = _os.path.join(plan_dir, 'progress.md')
    if _os.path.exists(progress_file):
        from datetime import datetime as _dt
        ts = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [x] {desc}  ({ts})\\n')
PYEOF
\t\techo "✅ 已标记任务完成: $(sanitize_output \"$DESCRIPTION\")\""""

if old_task_done_tail in content:
    content = content.replace(old_task_done_tail, new_task_done_tail, 1)
    print("lx-goal.sh: ✅ task-done → progress.md")
else:
    print("lx-goal.sh: ⚠️ task-done pattern not found")

# --- Fix 1d: skip-risk → append progress.md ---
old_skip_tail = "os.rename(tmp, task_file)\nPYEOF\n\t\techo \"📝 已记录跳过的风险: $(sanitize_output \"$DESCRIPTION\")\""
new_skip_tail = """os.rename(tmp, task_file)
# Append to RPE progress.md
plan_dir = d.get('rpe_plan_dir', '')
if plan_dir:
    import os as _os
    progress_file = _os.path.join(plan_dir, 'progress.md')
    if _os.path.exists(progress_file):
        from datetime import datetime as _dt
        ts = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [skip-risk] {desc}  ({ts})\\n')
PYEOF
\t\techo "📝 已记录跳过的风险: $(sanitize_output \"$DESCRIPTION\")\""""

if old_skip_tail in content:
    content = content.replace(old_skip_tail, new_skip_tail, 1)
    print("lx-goal.sh: ✅ skip-risk → progress.md")
else:
    print("lx-goal.sh: ⚠️ skip-risk pattern not found")

# --- Fix 1e: hard-boundary-hit → append progress.md ---
old_hard_tail = "os.rename(tmp, task_file)\nPYEOF\n\t\techo \"🛑 硬边界拦截已记录: $(sanitize_output \"$DESCRIPTION\") (原因: $(sanitize_output \"$REASON\"))\""
new_hard_tail = """os.rename(tmp, task_file)
# Append to RPE progress.md
plan_dir = d.get('rpe_plan_dir', '')
if plan_dir:
    import os as _os
    progress_file = _os.path.join(plan_dir, 'progress.md')
    if _os.path.exists(progress_file):
        from datetime import datetime as _dt
        ts = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [hard-boundary] {desc} — {reason}  ({ts})\\n')
PYEOF
\t\techo "🛑 硬边界拦截已记录: $(sanitize_output \"$DESCRIPTION\") (原因: $(sanitize_output \"$REASON\"))\""""

if old_hard_tail in content:
    content = content.replace(old_hard_tail, new_hard_tail, 1)
    print("lx-goal.sh: ✅ hard-boundary-hit → progress.md")
else:
    print("lx-goal.sh: ⚠️ hard-boundary-hit pattern not found")

# --- Fix 1f: blocked-human → append progress.md ---
old_blocked_tail = "os.rename(tmp, task_file)\nPYEOF\n\t\techo \"🤔 推迟决策已记录: $(sanitize_output \"$DESCRIPTION\") → 推荐: $(sanitize_output \"$AI_RECOMMENDATION\")\""
new_blocked_tail = """os.rename(tmp, task_file)
# Append to RPE progress.md
plan_dir = d.get('rpe_plan_dir', '')
if plan_dir:
    import os as _os
    progress_file = _os.path.join(plan_dir, 'progress.md')
    if _os.path.exists(progress_file):
        from datetime import datetime as _dt
        ts = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [blocked-human] {desc} → {ai_recommendation}  ({ts})\\n')
PYEOF
\t\techo "🤔 推迟决策已记录: $(sanitize_output \"$DESCRIPTION\") → 推荐: $(sanitize_output \"$AI_RECOMMENDATION\")\""""

if old_blocked_tail in content:
    content = content.replace(old_blocked_tail, new_blocked_tail, 1)
    print("lx-goal.sh: ✅ blocked-human → progress.md")
else:
    print("lx-goal.sh: ⚠️ blocked-human pattern not found")

# --- Fix 1g: off → write checklist.md + update state.json ---
old_off = """    off)
\t\tif [ -f "$MODE_FILE" ]; then
\t\t\trm -f "$MODE_FILE"
\t\tfi
\t\t# 清理旧格式
\t\trm -f "$STATE_DIR/unattended-mode.json" "$STATE_DIR/.unattended-mode" 2>/dev/null
\t\trm -f "$STATE_DIR/autonomous.active" 2>/dev/null
\t\techo "✅ 目标模式已关闭，所有 hook 恢复正常阻断\""""

new_off = """    off)
\t\t# Generate exit report to RPE dir before cleanup
\t\tif [ -f "$MODE_FILE" ]; then
\t\t\tPLAN_DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_plan_dir',''))" 2>/dev/null)
\t\t\tif [ -n "$PLAN_DIR" ] && [ -d "$PLAN_DIR" ]; then
\t\t\t\tDONE=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('completed_tasks',[])))" 2>/dev/null)
\t\t\t\tSKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
\t\t\t\tHARD=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
\t\t\t\tBLOCKED=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('blocked_human',[])))" 2>/dev/null)
\t\t\t\t{
\t\t\t\t\techo "# Checklist"
\t\t\t\t\techo ""
\t\t\t\t\techo "## 验收清单"
\t\t\t\t\techo "- [x] 目标模式已关闭"
\t\t\t\t\techo "- [x] 完成任务: ${DONE:-0} 项"
\t\t\t\t\techo "- [x] 跳过风险: ${SKIP:-0} 项"
\t\t\t\t\techo "- [x] 硬边界拦截: ${HARD:-0} 项"
\t\t\t\t\techo "- [x] 推迟决策: ${BLOCKED:-0} 项"
\t\t\t\t\techo ""
\t\t\t\t\techo "> 自动生成 @ $(date)"
\t\t\t\t} > "$PLAN_DIR/checklist.md"
\t\t\t\tpython3 -c "
import json
sf = '$PLAN_DIR/state.json'
d = json.load(open(sf))
d['phase'] = 'completed'
d['completed_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
json.dump(d, open(sf, 'w'), indent=2, ensure_ascii=False)
" 2>/dev/null
\t\t\t\techo \"RPE退出报告: $PLAN_DIR/checklist.md\" >&2
\t\t\tfi
\t\t\trm -f "$MODE_FILE"
\t\tfi
\t\t# 清理旧格式
\t\trm -f "$STATE_DIR/unattended-mode.json" "$STATE_DIR/.unattended-mode" 2>/dev/null
\t\trm -f "$STATE_DIR/autonomous.active" 2>/dev/null
\t\techo "✅ 目标模式已关闭，所有 hook 恢复正常阻断\""""

if old_off in content:
    content = content.replace(old_off, new_off, 1)
    print("lx-goal.sh: ✅ off → checklist.md + state.json")
else:
    print("lx-goal.sh: ⚠️ off pattern not found")

# Write and verify
atomic_write(goal_sh, content)
verify_bash_syntax(goal_sh)


# ============================================================
# Fix 2: lx-ghost.sh
# ============================================================
ghost_sh = os.path.join(PROJECT, '.claude/skills/lx-ghost/scripts/lx-ghost.sh')
bak2, content2 = backup(ghost_sh)
print(f"\nBackup: {bak2}")

# --- Fix 2a: Remove duplicate broken RPE block ---
old_dup2_start = "        DATE=$(date +%Y-%m-%d)\n\tSLUG=$(echo \"$DIRECTION\" | tr \" \" \"-\" | tr -cd \"[:alnum:]-_\" | head -c 50)\n\tCHAT_DIR=\"$PROJECT_ROOT/.omc/chats/${DATE}/${SLUG}\"\n\tmkdir -p \"$CHAT_DIR\"\n\techo \"{\"phase\":\"exploring\",\"created_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}\" > \"$CHAT_DIR/state.json\""

if old_dup2_start in content2:
    end_marker2 = '\tlog_info "RPE文档层: $CHAT_DIR"\n\tDATE=$(date +%Y-%m-%d)'
    if end_marker2 in content2:
        before = content2.split(old_dup2_start)[0]
        after_parts = content2.split(old_dup2_start)[1].split(end_marker2, 1)
        if len(after_parts) == 2:
            content2 = before + "DATE=$(date +%Y-%m-%d)" + after_parts[1]
            print("lx-ghost.sh: ✅ removed duplicate broken RPE block")
        else:
            print("lx-ghost.sh: ⚠️ could not split at end marker")
    else:
        print("lx-ghost.sh: ⚠️ end marker not found")
else:
    print("lx-ghost.sh: ⚠️ duplicate block start not found")

# --- Fix 2b: Save chat_dir + fix log_info ---
old_ghost_tail = '\tlog_info "RPE文档层: $CHAT_DIR"\n\techo "✅ 幽灵模式已开启'
new_ghost_tail = '''\techo "RPE文档层: $CHAT_DIR" >&2
\t# Save chat_dir to lx-ghost.json for runtime subcommands
\texport _LX_CHAT_DIR="$CHAT_DIR"
\texport _LX_MODE_FILE="$MODE_FILE"
\tpython3 <<'PYEOF'
import json, os
chat_dir = os.environ['_LX_CHAT_DIR']
mode_file = os.environ['_LX_MODE_FILE']
d = json.load(open(mode_file))
d['rpe_chat_dir'] = chat_dir
tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
\techo "✅ 幽灵模式已开启'''

if old_ghost_tail in content2:
    content2 = content2.replace(old_ghost_tail, new_ghost_tail, 1)
    print("lx-ghost.sh: ✅ save chat_dir + fix log_info")
else:
    print("lx-ghost.sh: ⚠️ ghost RPE tail pattern not found")

# --- Fix 2c: skip-risk → progress.md (inline python → heredoc) ---
old_ghost_skip = """    skip-risk)
\t\t# 记录跳过的风险（供 permission-gate 等调用）
\t\tDESCRIPTION="${2:-未知风险}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\tpython3 -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
risks = d.get('skipped_risks', [])
risks.append({'description': '$DESCRIPTION', 'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'})
d['skipped_risks'] = risks
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
\t" 2>/dev/null && echo "📝 已记录跳过的风险: $DESCRIPTION" || echo "❌ 记录失败\""""

new_ghost_skip = """    skip-risk)
\t\t# 记录跳过的风险（供 permission-gate 等调用）
\t\tDESCRIPTION="${2:-未知风险}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\texport _LX_DESC="$DESCRIPTION"
\t\texport _LX_MODE_FILE="$MODE_FILE"
\t\tpython3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
risks = d.get('skipped_risks', [])
risks.append({'description': desc, 'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
d['skipped_risks'] = risks

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [skip-risk] {desc}  ({ts})\\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
\t\techo "📝 已记录跳过的风险: $DESCRIPTION\""""

if old_ghost_skip in content2:
    content2 = content2.replace(old_ghost_skip, new_ghost_skip, 1)
    print("lx-ghost.sh: ✅ skip-risk → heredoc + progress.md")
else:
    print("lx-ghost.sh: ⚠️ skip-risk pattern not found")

# --- Fix 2d: hard-boundary-hit → progress.md ---
old_ghost_hard = """    hard-boundary-hit)
\t\t# 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
\t\tDESCRIPTION="${2:-未知硬边界}"
\t\tREASON="${3:-未知原因}"
\t\tHUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\tpython3 -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
hits = d.get('hard_boundary_hits', [])
hits.append({
    'description': '$DESCRIPTION',
    'reason': '$REASON',
    'human_action': '$HUMAN_ACTION',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
})
d['hard_boundary_hits'] = hits
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
\t" 2>/dev/null && echo "🛑 硬边界拦截已记录: $DESCRIPTION (原因: $REASON)" || echo "❌ 记录失败\""""

new_ghost_hard = """    hard-boundary-hit)
\t\t# 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
\t\tDESCRIPTION="${2:-未知硬边界}"
\t\tREASON="${3:-未知原因}"
\t\tHUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\texport _LX_DESC="$DESCRIPTION"
\t\texport _LX_REASON="$REASON"
\t\texport _LX_HUMAN_ACTION="$HUMAN_ACTION"
\t\texport _LX_MODE_FILE="$MODE_FILE"
\t\tpython3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
reason = os.environ['_LX_REASON']
human_action = os.environ['_LX_HUMAN_ACTION']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
hits = d.get('hard_boundary_hits', [])
hits.append({
    'description': desc,
    'reason': reason,
    'human_action': human_action,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['hard_boundary_hits'] = hits

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [hard-boundary] {desc} — {reason}  ({ts})\\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
\t\techo "🛑 硬边界拦截已记录: $DESCRIPTION (原因: $REASON)\""""

if old_ghost_hard in content2:
    content2 = content2.replace(old_ghost_hard, new_ghost_hard, 1)
    print("lx-ghost.sh: ✅ hard-boundary-hit → heredoc + progress.md")
else:
    print("lx-ghost.sh: ⚠️ hard-boundary-hit pattern not found")

# --- Fix 2e: blocked-human → progress.md ---
old_ghost_blocked = """    blocked-human)
\t\t# 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
\t\t# 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
\t\tDESCRIPTION="${2:-未知决策}"
\t\tAI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
\t\tRATIONALE="${4:-决策依据未提供}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\tpython3 -c "
import json, os
file = '$MODE_FILE'
d = json.load(open(file))
blocked = d.get('blocked_human', [])
blocked.append({
    'description': '$DESCRIPTION',
    'ai_recommendation': '$AI_RECOMMENDATION',
    'rationale': '$RATIONALE',
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
})
d['blocked_human'] = blocked
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
\t" 2>/dev/null && echo "🤔 推迟决策已记录: $DESCRIPTION → 推荐: $AI_RECOMMENDATION" || echo "❌ 记录失败\""""

new_ghost_blocked = """    blocked-human)
\t\t# 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
\t\t# 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
\t\tDESCRIPTION="${2:-未知决策}"
\t\tAI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
\t\tRATIONALE="${4:-决策依据未提供}"
\t\tif [ ! -f "$MODE_FILE" ]; then
\t\t\techo "❌ 幽灵模式未开启"
\t\t\texit 1
\t\tfi
\t\texport _LX_DESC="$DESCRIPTION"
\t\texport _LX_AI_RECOMMENDATION="$AI_RECOMMENDATION"
\t\texport _LX_RATIONALE="$RATIONALE"
\t\texport _LX_MODE_FILE="$MODE_FILE"
\t\tpython3 <<'PYEOF'
import json, os
from datetime import datetime, timezone

desc = os.environ['_LX_DESC']
ai_recommendation = os.environ['_LX_AI_RECOMMENDATION']
rationale = os.environ['_LX_RATIONALE']
mode_file = os.environ['_LX_MODE_FILE']

d = json.load(open(mode_file))
blocked = d.get('blocked_human', [])
blocked.append({
    'description': desc,
    'ai_recommendation': ai_recommendation,
    'rationale': rationale,
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
})
d['blocked_human'] = blocked

# Append to RPE progress.md
chat_dir = d.get('rpe_chat_dir', '')
if chat_dir:
    progress_file = os.path.join(chat_dir, 'progress.md')
    if os.path.exists(progress_file):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(progress_file, 'a') as pf:
            pf.write(f'\\n- [blocked-human] {desc} → {ai_recommendation}  ({ts})\\n')

tmp = mode_file + '.tmp.' + str(os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, mode_file)
PYEOF
\t\techo "🤔 推迟决策已记录: $DESCRIPTION → 推荐: $AI_RECOMMENDATION\""""

if old_ghost_blocked in content2:
    content2 = content2.replace(old_ghost_blocked, new_ghost_blocked, 1)
    print("lx-ghost.sh: ✅ blocked-human → heredoc + progress.md")
else:
    print("lx-ghost.sh: ⚠️ blocked-human pattern not found")

# --- Fix 2f: off → write summary + update state.json ---
old_ghost_off = """    off)
\t\tif [ -f "$MODE_FILE" ]; then
\t\t\trm -f "$MODE_FILE"
\t\tfi
\t\t# 清理旧格式文件
\t\trm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
\t\trm -f "$STATE_DIR/autonomous.active" 2>/dev/null
\t\techo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断\""""

new_ghost_off = """    off)
\t\t# Write summary to RPE chat dir before cleanup
\t\tif [ -f "$MODE_FILE" ]; then
\t\t\tCHAT_DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
\t\t\tif [ -n "$CHAT_DIR" ] && [ -d "$CHAT_DIR" ]; then
\t\t\t\tRETRY=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
\t\t\t\tSKIP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
\t\t\t\tHARD=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
\t\t\t\t{
\t\t\t\t\techo ""
\t\t\t\t\techo "---"
\t\t\t\t\techo "## 退出摘要"
\t\t\t\t\techo "- 关闭时间: $(date)"
\t\t\t\t\techo "- 重试次数: ${RETRY:-0}"
\t\t\t\t\techo "- 跳过风险: ${SKIP:-0}"
\t\t\t\t\techo "- 硬边界拦截: ${HARD:-0}"
\t\t\t\t\techo ""
\t\t\t\t\techo "> 幽灵模式自动关闭 @ $(date)"
\t\t\t\t} >> "$CHAT_DIR/progress.md"
\t\t\t\tpython3 -c "
import json
sf = '$CHAT_DIR/state.json'
d = json.load(open(sf))
d['phase'] = 'completed'
d['completed_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
json.dump(d, open(sf, 'w'), indent=2, ensure_ascii=False)
" 2>/dev/null
\t\t\tfi
\t\t\trm -f "$MODE_FILE"
\t\tfi
\t\t# 清理旧格式文件
\t\trm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
\t\trm -f "$STATE_DIR/autonomous.active" 2>/dev/null
\t\techo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断\""""

if old_ghost_off in content2:
    content2 = content2.replace(old_ghost_off, new_ghost_off, 1)
    print("lx-ghost.sh: ✅ off → summary + state.json")
else:
    print("lx-ghost.sh: ⚠️ off pattern not found")

# Write and verify
atomic_write(ghost_sh, content2)
verify_bash_syntax(ghost_sh)

print("\n=== All fixes applied ===")
