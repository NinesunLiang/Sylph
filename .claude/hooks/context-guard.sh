#!/usr/bin/env bash
# context-guard.sh — PreToolUse:Edit|Write — 基于真实 token 百分比阻断写操作，防止上下文溢出
# Role: 基于真实 token 百分比阻断写操作，防止上下文溢出

source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_guard" || exit 0

# R29: context-guard matcher 改为 Edit|Write, 开放诊断通道 (Read/Grep/Bash)。
# 原则: "读是诊断, 写是破坏" — 高上下文时封锁写操作，但保留 Read/Grep 供诊断。
# 逃生门: context-force-override 文件存在时跳过阻断 (配合 Bash 修复)。
# 无人值守模式: .omc/state/.unattended-mode 存在时，不阻断仅记录 flywheel
INPUT=$(cat)

# 逃生舱盖: 标记文件存在时跳过阻断 (供诊断恢复使用)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
OVERRIDE_FILE="$STATE_DIR/context-force-override"
if [ -f "$OVERRIDE_FILE" ]; then
    rm -f "$OVERRIDE_FILE"
    exit 0
fi

# 无人值守模式: .omc/state/.unattended-mode 存在时，策略更松散
# - 写操作也不阻断(仅记录 flywheel)
# - 危险阈值提升到 95%，减少误报
# - 自动过期: 超过 UNATTENDED_MAX_AGE (默认30分钟) 视为过期，自动清理
UNATTENDED_FILE="$STATE_DIR/.unattended-mode"
UNATTENDED=false
if [ -f "$UNATTENDED_FILE" ]; then
    UNATTENDED_MAX_AGE=$(hc_get "context_guard.unattended_max_age_seconds" "1800")
    if [ -n "$UNATTENDED_MAX_AGE" ] && [ "$UNATTENDED_MAX_AGE" -gt 0 ]; then
        FILE_AGE=$(( $(date +%s) - $(stat -f %m "$UNATTENDED_FILE") ))
        if [ "$FILE_AGE" -gt "$UNATTENDED_MAX_AGE" ]; then
            rm -f "$UNATTENDED_FILE"
            echo "⚠️ [Context Guard] 无人值守模式文件已过期 (超过 ${UNATTENDED_MAX_AGE}s)，自动清理" >&2
        else
            UNATTENDED=true
        fi
    else
        UNATTENDED=true
    fi
fi

# R29: 只对写工具 (Edit/Write) 做硬阻断, 保留 Read/Grep/Bash 诊断通道
# 从 stdin JSON 中提取 tool_name
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_name', ''))
except:
    print('')
" 2>/dev/null)

case "$TOOL_NAME" in
    Edit|Write)
        BLOCK_WRITES=true
        ;;
    *)
        BLOCK_WRITES=false
        ;;
esac

# 从 harness config 读取可配置阈值，传递给 Python 探针
WARN_PCT=$(hc_get "context_guard.warn_threshold" "50")
DANGER_PCT=$(hc_get "context_guard.danger_threshold" "80")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../scripts/context_monitor.py"
if [ -x "$PYTHON_SCRIPT" ]; then
    RESULT=$(CONTEXT_WARN_THRESHOLD="$WARN_PCT" CONTEXT_DANGER_THRESHOLD="$DANGER_PCT" \
        python3 "$PYTHON_SCRIPT" 2>/dev/null)
    IS_DANGER=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(str(d.get('is_danger', False)).lower())" 2>/dev/null)
    PCT=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('percentage', 0))" 2>/dev/null)

    if [ "$IS_DANGER" = "true" ]; then
        echo "$(date +%Y-%m-%d),context_guard_triggered,P0,carror-os" >> "$HOME/.claude/flywheel.log"
        if [ "$BLOCK_WRITES" = "true" ] && [ "$UNATTENDED" = "false" ]; then
            cat >&2 <<EOF

🚫 [Context Guard 硬阻断] 当前会话上下文占比已达 ${PCT}%（危险阈值: ${DANGER_PCT}%，警告阈值: ${WARN_PCT}%）！

为了防止灾难性的幻觉、指令遗忘或代码损毁，已强制拦截了写入操作。诊断工具 (Read/Grep/Bash) 可正常使用。请先诊断上下文状态，然后运行 '/compact' 压缩会话或手动重置 token 追踪。

EOF
            exit 2
        else
            # 非写工具 或 无人值守模式: 仅记录 flywheel + 告警, 不阻断
            printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"⚠️ 上下文占比 %s%%。超出危险阈值。请考虑 /compact。诊断操作未阻断。%s"}}\n' \
                "$PCT" "$([ "$UNATTENDED" = "true" ] && echo ' [无人值守模式: 已记录，未阻断]' || echo '')"
            exit 0
        fi
    fi
fi

# Sweet-spot / Hand-off Alert: inject into AI context via additionalContext
if [ -x "$PYTHON_SCRIPT" ]; then
    SWEET_WARNING=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('sweet_spot_warning',''))" 2>/dev/null)
    if [ -n "$SWEET_WARNING" ]; then
        SWEET_JSON=$(echo "$SWEET_WARNING" | python3 -c "import sys,json; print(json.dumps(json.dumps(sys.stdin.read().strip())))" 2>/dev/null)
        printf '{"continue":true,"hookSpecificOutput":{"additionalContext":%s}}\n' "$SWEET_JSON"
    fi
fi

exit 0
