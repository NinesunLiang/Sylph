#!/usr/bin/env bash

# harness-kit:managed v1.0.0

# context-guard.sh — PreToolUse:.* Hook (R26: 全工具走阈值, see claude-next.md)

# 功能：真实 Context Token 百分比硬阻断 (Hard Gate)

# - 读取 OMC 状态并结合 OPENCODE_CONFIG_CONTENT 算出精准 ctx%

# - 如果大于等于 DANGER_THRESHOLD (如 80%)，立即强制掐断任何实质性修改或执行操作

# 退出码 2 = 阻断（防止幻觉/代码毁坏）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_guard" || exit 0

# R29: context-guard matcher 改为 Edit|Write, 开放诊断通道 (Read/Grep/Bash)。
# 原则: "读是诊断, 写是破坏" — 高上下文时封锁写操作，但保留 Read/Grep 供诊断。
# 逃生门: context-force-override 文件存在时跳过阻断 (配合 Bash 修复)。
# 保留 permission-gate 对危险 Bash (rm/git push) 的独立防护。
INPUT=$(cat)

# 逃生舱盖: 标记文件存在时跳过阻断 (供诊断恢复使用)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
OVERRIDE_FILE="$STATE_DIR/context-force-override"
if [ -f "$OVERRIDE_FILE" ]; then
    rm -f "$OVERRIDE_FILE"
    exit 0
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
        if [ "$BLOCK_WRITES" = "true" ]; then
            cat >&2 <<EOF

🚫 [Context Guard 硬阻断] 当前会话上下文占比已达 ${PCT}%（危险阈值: ${DANGER_PCT}%，警告阈值: ${WARN_PCT}%）！

为了防止灾难性的幻觉、指令遗忘或代码损毁，已强制拦截了写入操作。诊断工具 (Read/Grep/Bash) 可正常使用。请先诊断上下文状态，然后运行 '/compact' 压缩会话或手动重置 token 追踪。

EOF
            exit 2
        else
            # 非写工具: 仅输出告警, 不阻断 (保留诊断通道)
            printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"⚠️ 上下文占比 %s%%。超出危险阈值。请考虑 /compact。诊断操作未阻断。"}}\n' "$PCT"
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
