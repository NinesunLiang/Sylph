#!/usr/bin/env bash

# harness-kit:managed v1.0.0

# proactive-handoff.sh — PostToolUse Hook [INACTIVE: 未注册, 反向漂移]
# 注意：此脚本存在于磁盘但未注册到 settings.json（R23 移除反向漂移）。
# 恢复激活请：settings.json PostToolUse 添加 + harness.yaml hooks_enabled.proactive_handoff=true
#
# 功能：Enhanced 专属。当 step 执行完毕且上下文 >50% 时，
#       触发主动交接警告，提醒用户运行 /compact 压缩会话。
#
# 触发条件（全部满足）：
#   1. Enhanced 模式已激活（profiles/enhanced/ 存在）
#   2. 真实上下文百分比 >= 50%
#   3. 最近 5 分钟内 executor.md 被修改且包含完成标记
#   4. 本会话中尚未触发过（防重复）
#
# 退出码：0（仅警告，不阻断操作）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"

# ─── 1. Enhanced 门禁 ──────────────────────────────────────────────
[ -f "$PROJECT_ROOT/.claude/profiles/enhanced/append-to-claude.md" ] || exit 0
hc_enabled "proactive_handoff" || exit 0

# ─── 2. 获取可配置阈值 ────────────────────────────────────────────
CONTEXT_THRESHOLD=$(hc_get "proactive_handoff.context_threshold" "50")
EXECUTOR_FRESHNESS=$(hc_get "proactive_handoff.executor_freshness_sec" "300")

# ─── 3. 获取上下文百分比 ──────────────────────────────────────────
PYTHON_SCRIPT="$SCRIPT_DIR/../scripts/context_monitor.py"
if [ ! -x "$PYTHON_SCRIPT" ]; then
    # degraded 状态：context_monitor.py 不可用，输出警告
    echo "[degraded] proactive-handoff.sh: context_monitor.py not found at $PYTHON_SCRIPT" >> "$PROJECT_ROOT/.omc/state/harness-degraded.log" 2>/dev/null
    exit 0
fi

RESULT=$(python3 "$PYTHON_SCRIPT" 2>/dev/null) || exit 0
PCT=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('percentage', 0))
except:
    print('0')
" 2>/dev/null)

# 浮点数比较：< {阈值} 不触发
PCT_INT=${PCT%.*}
[ -z "$PCT_INT" ] && exit 0
[ "$PCT_INT" -lt "$CONTEXT_THRESHOLD" ] 2>/dev/null && exit 0

# ─── 3. 防重复触发（单会话仅一次） ───────────────────────────────
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"
HANDOFF_FIRED="$STATE_DIR/.proactive-handoff-fired"
[ -f "$HANDOFF_FIRED" ] && exit 0

# ─── 4. 检测 Step 完成 ─────────────────────────────────────────────
DOC_ROOT=$(hc_get "workflow.doc_root" "rpe")
EXEC_DOC=$(hc_get "workflow.executor_doc" "executor.md")

LATEST_EXEC=""
STEP_COMPLETED=false

# 4a. 在 DOC_ROOT (rpe/) 下查找最近修改的 executor.md
MATCHED=$(find "$PROJECT_ROOT/$DOC_ROOT" -name "$EXEC_DOC" -type f 2>/dev/null | \
    xargs ls -t 2>/dev/null | head -1)
[ -n "$MATCHED" ] && LATEST_EXEC="$MATCHED"

# 4b. 在 .omc/state/ 下也查找（用于 lx-task-spec / lx-todo 场景）
if [ -z "$LATEST_EXEC" ]; then
    MATCHED=$(find "$PROJECT_ROOT/.omc/state" -name "$EXEC_DOC" -type f 2>/dev/null | \
        xargs ls -t 2>/dev/null | head -1)
    [ -n "$MATCHED" ] && LATEST_EXEC="$MATCHED"
fi

if [ -n "$LATEST_EXEC" ] && [ -f "$LATEST_EXEC" ]; then
    # 检查是否最近 5 分钟内修改
    RECENT=$(python3 -c "
import os, time
try:
    age = time.time() - os.path.getmtime('$LATEST_EXEC')
    freshness = $EXECUTOR_FRESHNESS
    print('true' if age < freshness else 'false')
except:
    print('false')
" 2>/dev/null)
    if [ "$RECENT" = "true" ]; then
        # 检查包含完成标记
        HAS_DONE=$(grep -cE '\[x\]|✅|\[done\]|Status.*[Dd]one|✅' "$LATEST_EXEC" 2>/dev/null || echo 0)
        [ "$HAS_DONE" -gt 0 ] && STEP_COMPLETED=true
    fi
fi

[ "$STEP_COMPLETED" = false ] && exit 0

# ─── 5. 触发主动交接 ───────────────────────────────────────────────
touch "$HANDOFF_FIRED"

PCT_DISPLAY=$(echo "$PCT" | python3 -c "import sys; v=float(sys.stdin.read()); print(f'{v:.0f}%')" 2>/dev/null || echo "${PCT_INT}%")

cat >&2 <<HANDOFF_MSG

═══════════════════════════════════════════════════════════════
  🔄 [主动交接] 上下文已达上限（${PCT_DISPLAY}），当前 Step 已完成

  建议立即运行 /compact 压缩会话，
  保持大模型在最高智商区间接力。

  恢复后系统将自动加载当前 executor.md 和 plan.md，
  从下一个未完成的 Step 继续执行。
═══════════════════════════════════════════════════════════════
👉 Re-insp-Kernel-Design:1.2-ContextGuard_ProactiveHandoff
HANDOFF_MSG

exit 0
