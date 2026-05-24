#!/bin/bash
# setup-rpe-task-layer.sh — goal/ghost 自动创建 RPE 文档目录
set -e
# Cross-platform Python resolution (DG-105)
[ -f ".claude/hooks/harness_config.sh" ] && source ".claude/hooks/harness_config.sh" 2>/dev/null || true
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

# Fix 1: lx-goal.sh (skill copy) — add mkdir on activation
GOAL_SH="$PROJECT/.claude/skills/lx-goal/scripts/lx-goal.sh"
if [ -f "$GOAL_SH" ]; then
    cp "$GOAL_SH" "$GOAL_SH.bak"
    ${PYTHON_BIN:-python3} -c "
path = '$GOAL_SH'
with open(path) as f: c = f.read()
# Insert mkdir before the exit line in 'on' subcommand
old = 'echo \"✅ 目标模式已开启 — 目标: \$(sanitize_output \"\$GOAL\"), \${EXPIRY_HOURS}h 过期\"'
new = '''DATE=\$(date +%Y-%m-%d)
SLUG=\$(echo \"\$GOAL\" | tr \" \" \"-\" | tr -cd \"[:alnum:]-_\" | head -c 50)
PLAN_DIR=\"\$PROJECT_ROOT/.omc/plans/\${DATE}/\${SLUG}\"
mkdir -p \"\$PLAN_DIR\"
${PYTHON_BIN:-python3} -c \"import json; json.dump({'phase':'draft','created_at':'\$(date -u +%Y-%m-%dT%H:%M:%SZ)'},open('\$PLAN_DIR/state.json','w'))\"
echo \"# \$GOAL\n\n> goal模式自动创建 @ \$(date)\" > \"\$PLAN_DIR/prd.md\"
echo \"# Progress\n\n\" > \"\$PLAN_DIR/progress.md\"
echo \"# Checklist\n\n\" > \"\$PLAN_DIR/checklist.md\"
echo \"RPE文档层: \$PLAN_DIR\" >&2
echo \"✅ 目标模式已开启 — 目标: \$(sanitize_output \"\$GOAL\"), \${EXPIRY_HOURS}h 过期\"'''
c = c.replace(old, new)
with open(path, 'w') as f: f.write(c)
print('lx-goal.sh: mkdir added')
"
    bash -n "$GOAL_SH" && echo "  Syntax OK" || { echo "  Syntax FAILED"; cp "$GOAL_SH.bak" "$GOAL_SH"; exit 1; }
fi

# Fix 2: lx-ghost.sh (skill copy) — add mkdir on activation
GHOST_SH="$PROJECT/.claude/skills/lx-ghost/scripts/lx-ghost.sh"
if [ -f "$GHOST_SH" ]; then
    cp "$GHOST_SH" "$GHOST_SH.bak"
    ${PYTHON_BIN:-python3} -c "
path = '$GHOST_SH'
with open(path) as f: c = f.read()
old = 'echo \"✅ 幽灵模式已开启 — 方向: \$DIRECTION, 每 \${INTERVAL}s 轮询, \${EXPIRY_HOURS}h 过期\"'
new = '''DATE=\$(date +%Y-%m-%d)
SLUG=\$(echo \"\$DIRECTION\" | tr \" \" \"-\" | tr -cd \"[:alnum:]-_\" | head -c 50)
CHAT_DIR=\"\$PROJECT_ROOT/.omc/chats/\${DATE}/\${SLUG}\"
mkdir -p \"\$CHAT_DIR\"
echo \"{\\\"phase\\\":\\\"exploring\\\",\\\"created_at\\\":\\\"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"}\" > \"\$CHAT_DIR/state.json\"
echo \"# \$DIRECTION\n\n> ghost模式自动创建 @ \$(date)\" > \"\$CHAT_DIR/progress.md\"
log_info \"RPE文档层: \$CHAT_DIR\"
echo \"✅ 幽灵模式已开启 — 方向: \$DIRECTION, 每 \${INTERVAL}s 轮询, \${EXPIRY_HOURS}h 过期\"'''
c = c.replace(old, new)
with open(path, 'w') as f: f.write(c)
print('lx-ghost.sh: mkdir added')
"
    bash -n "$GHOST_SH" && echo "  Syntax OK" || { echo "  Syntax FAILED"; cp "$GHOST_SH.bak" "$GHOST_SH"; exit 1; }
fi

# State
STATE_DIR="$PROJECT/.omc/plans/2026-05-23/rpe-task-layer"
mkdir -p "$STATE_DIR"
${PYTHON_BIN:-python3} -c "import json; json.dump({'phase':'approved','approved_by':'LuangSir','created_at':'2026-05-23T20:00:00Z'},open('$STATE_DIR/state.json','w'))"
echo "state.json: approved"

echo "=== Done ==="
echo "Run: bash scripts/release.sh patch 'feat: RPE任务文档层 — goal/ghost激活时自动创建prd+progress+checklist+state' --yes"
