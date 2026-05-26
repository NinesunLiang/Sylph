#!/usr/bin/env bash
# session-resume.sh — SessionStart — 跨会话恢复: 注入进行中的 goal/ghost 任务上下文
# #36: 新会话启动时检测活跃自主模式，注入进度摘要 + 恢复指令
# 哲学 #7(文档优先): 从 RPE progress.md 重建上下文，而非依赖记忆

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f

STATE_DIR="$PROJECT_ROOT/.omc/state"
GOAL_FILE="$STATE_DIR/tokens/lx-goal.json"
GHOST_FILE="$STATE_DIR/tokens/lx-ghost.json"

RESUME_CTX=""

# ─── Goal 模式恢复 ──────────────────────────────────────────
if [ -f "$GOAL_FILE" ]; then
    GOAL_DATA=$(${PYTHON_BIN:-python3} -c "
import json, sys
try:
    d = json.load(open('$GOAL_FILE', encoding="utf-8"))
    goal = d.get('goal', '?')
    activated = d.get('activated_at', '?')
    expires = d.get('expires_at', '?')
    done = len(d.get('completed_tasks', []))
    skip = len(d.get('skipped_risks', []))
    hard = len(d.get('hard_boundary_hits', []))
    blocked = len(d.get('blocked_human', []))
    plan_dir = d.get('rpe_plan_dir', '')
    phase0 = d.get('phase0_passed_at', '')
    print(json.dumps({
        'goal': goal, 'activated': activated, 'expires': expires,
        'done': done, 'skip': skip, 'hard': hard, 'blocked': blocked,
        'plan_dir': plan_dir, 'phase0': phase0
    }))
except: print('{}')
" 2>/dev/null)

    if [ -n "$GOAL_DATA" ] && [ "$GOAL_DATA" != "{}" ]; then
        GOAL=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('goal','?'))" 2>/dev/null)
        DONE=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('done',0))" 2>/dev/null)
        PLAN_DIR=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('plan_dir',''))" 2>/dev/null)
        PHASE0=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('phase0',''))" 2>/dev/null)
        EXPIRES=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('expires','?'))" 2>/dev/null)
        BLOCKED=$(echo "$GOAL_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('blocked',0))" 2>/dev/null)

        # 检查过期
        EXPIRED=$(${PYTHON_BIN:-python3} -c "
from datetime import datetime
try:
    exp = datetime.fromisoformat('$EXPIRES')
    print('yes' if datetime.now() > exp else 'no')
except: print('no')" 2>/dev/null)

        if [ "$EXPIRED" = "yes" ]; then
            RESUME_CTX="${RESUME_CTX}
⏰ [session-resume] 目标模式已过期 ($EXPIRES)，请运行 lx-goal off 清理。
"
        else
            PHASE_LABEL="Phase 0 (draft)"
            [ -n "$PHASE0" ] && PHASE_LABEL="Phase 1 (executing, 已通过 phase0-done)"

            RESUME_CTX="${RESUME_CTX}
🔄 [session-resume·跨会话恢复] 目标模式活跃中 — ${PHASE_LABEL}

   📋 目标: ${GOAL}
   📊 进度: ${DONE} 完成 | ${BLOCKED} 推迟决策
   📁 RPE: ${PLAN_DIR}

   🔧 恢复指令:
   1. 读取进度: cat ${PLAN_DIR}/progress.md
   2. 读取计划: cat ${PLAN_DIR}/prd.md
   3. 继续执行未完成任务 (使用 task-done/skip-risk/hard-boundary-hit/blocked-human)
   4. 完成后: lx-goal off && lx-goal report
"

            # 追加 progress.md 最后 5 条记录
            if [ -n "$PLAN_DIR" ] && [ -f "$PLAN_DIR/progress.md" ]; then
                RECENT=$(tail -5 "$PLAN_DIR/progress.md" 2>/dev/null | sed 's/^/     /')
                [ -n "$RECENT" ] && RESUME_CTX="${RESUME_CTX}
   📝 最近进度:
${RECENT}
"
            fi
        fi
    fi
fi

# ─── Ghost 模式恢复 ─────────────────────────────────────────
if [ -f "$GHOST_FILE" ]; then
    GHOST_DATA=$(${PYTHON_BIN:-python3} -c "
import json, sys
try:
    d = json.load(open('$GHOST_FILE', encoding="utf-8"))
    direction = d.get('direction', '?')
    activated = d.get('activated_at', '?')
    expires = d.get('expires_at', '?')
    retry = d.get('retry_count', 0)
    skip = len(d.get('skipped_risks', []))
    hard = len(d.get('hard_boundary_hits', []))
    chat_dir = d.get('rpe_chat_dir', '')
    print(json.dumps({
        'direction': direction, 'activated': activated, 'expires': expires,
        'retry': retry, 'skip': skip, 'hard': hard, 'chat_dir': chat_dir
    }))
except: print('{}')
" 2>/dev/null)

    if [ -n "$GHOST_DATA" ] && [ "$GHOST_DATA" != "{}" ]; then
        DIRECTION=$(echo "$GHOST_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('direction','?'))" 2>/dev/null)
        RETRY=$(echo "$GHOST_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('retry',0))" 2>/dev/null)
        CHAT_DIR=$(echo "$GHOST_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('chat_dir',''))" 2>/dev/null)
        EXPIRES=$(echo "$GHOST_DATA" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('expires','?'))" 2>/dev/null)

        EXPIRED=$(${PYTHON_BIN:-python3} -c "
from datetime import datetime
try:
    exp = datetime.fromisoformat('$EXPIRES')
    print('yes' if datetime.now() > exp else 'no')
except: print('no')" 2>/dev/null)

        if [ "$EXPIRED" = "yes" ]; then
            RESUME_CTX="${RESUME_CTX}
⏰ [session-resume] 幽灵模式已过期 — 请运行 lx-ghost off 清理。
"
        else
            RESUME_CTX="${RESUME_CTX}
👻 [session-resume] 幽灵模式活跃中

   🧭 方向: ${DIRECTION}
   🔄 轮次: ${RETRY}
   📁 Chat: ${CHAT_DIR}

   🔧 恢复指令:
   1. 读取探索进度: cat ${CHAT_DIR}/progress.md
   2. 继续围绕方向探索
   3. 记录发现: 追加到 ${CHAT_DIR}/progress.md
   4. 如有风险: lx-ghost skip-risk '描述'
   5. 如方向完成: lx-ghost off
"
        fi
    fi
fi

# ─── 输出 ──────────────────────────────────────────────────
if [ -n "$RESUME_CTX" ]; then
    echo "$RESUME_CTX"
    flywheel_event "session_resume" "inject_active_mode" "P1" || true
fi

# 始终放行 (SessionStart 不应阻断)
echo '{"continue": true}'
exit 0
