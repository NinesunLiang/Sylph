#!/usr/bin/env bash
# context-guard.sh — PreToolUse:Edit|Write — 基于真实 token 百分比阻断写操作，防止上下文溢出
# Role: 基于真实 token 百分比阻断写操作，防止上下文溢出

source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_guard" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
set -f

# R29: context-guard matcher 改为 Edit|Write, 开放诊断通道 (Read/Grep/Bash)。
# 原则: "读是诊断, 写是破坏" — 高上下文时封锁写操作，但保留 Read/Grep 供诊断。
# 逃生门: context-force-override 文件存在时跳过阻断 (配合 Bash 修复)。
# Ghost/Unattended mode: is_mode_active() 检测到非 normal 模式时，不阻断仅记录 flywheel
INPUT=$(cat)

# 逃生舱盖: 标记文件存在时跳过阻断 (供诊断恢复使用)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
OVERRIDE_FILE="$STATE_DIR/context-force-override"
if [ -f "$OVERRIDE_FILE" ]; then
    rm -f "$OVERRIDE_FILE"
    echo '{"continue": true}'
    exit 0
fi

# 统一模式检测: ghost / unattended / normal
# ghost mode: 不阻断写操作，仅记录 flywheel
# unattended mode: 不阻断写操作，仅记录 flywheel
# 自动过期通过 is_mode_active() 在 harness_config.sh 中处理
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    MODE_LABEL="[${MODE} mode]"
else
    MODE_LABEL=""
fi

# R29: 只对写工具 (Edit/Write) 做硬阻断, 保留 Read/Grep/Bash 诊断通道
# 从 stdin JSON 中提取 tool_name
TOOL_NAME=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
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
CRITICAL_PCT=$(hc_get "context_guard.critical_threshold" "90")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../scripts/context_monitor.py"
if [ -x "$PYTHON_SCRIPT" ]; then
    RESULT=$(CONTEXT_WARN_THRESHOLD="$WARN_PCT" CONTEXT_DANGER_THRESHOLD="$DANGER_PCT" CONTEXT_CRITICAL_THRESHOLD="$CRITICAL_PCT" \
        ${PYTHON_BIN:-python3} "$PYTHON_SCRIPT" 2>/dev/null)
    SOURCE=$(echo "$RESULT" | ${PYTHON_BIN:-python3} -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('source', ''))" 2>/dev/null)
    IS_DANGER=$(echo "$RESULT" | ${PYTHON_BIN:-python3} -c "
import sys, json
d = json.load(sys.stdin)
print(str(d.get('is_danger', False)).lower())" 2>/dev/null)
    IS_CRITICAL=$(echo "$RESULT" | ${PYTHON_BIN:-python3} -c "
import sys, json
d = json.load(sys.stdin)
print(str(d.get('is_critical', False)).lower())" 2>/dev/null)
    PCT=$(echo "$RESULT" | ${PYTHON_BIN:-python3} -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('percentage', 0))" 2>/dev/null)

    # ── CRITICAL threshold (90%): hard-block in normal mode, log+pass in autonomous ──
    if [ "$IS_CRITICAL" = "true" ] && [ "$SOURCE" = "transcript (real)" ]; then
        if [ "$MODE" != "normal" ]; then
            echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | ${MODE} | context_guard | ${PCT}% | critical context but autonomous mode — skip hard block" >> "$STATE_DIR/skipped-errors.md"
            printf '⚠️ [%s mode] 上下文占比 %s%%。超出紧急阈值但自主模式不阻断。请考虑 /compact。' \
                "$MODE" "$PCT" | hc_emit_hook_json "PreToolUse" "true"
            exit 0
        fi
        flywheel_event "context_guard" "critical" "P0" || true
        agentic_status block \
            "Context Guard 紧急阻断 — 90% 临界" \
            "会话上下文占比已达 ${PCT}%（紧急阈值: ${CRITICAL_PCT}%）。AI 记忆已不可靠，继续操作将导致数据损毁。务必立即运行 /compact 压缩会话。所有写操作已被物理阻断。${MODE_LABEL}" 
        exit 2
    fi

    # Only trust real transcript data for blocking decisions.
    # Heuristic fallbacks (turns/cumulative) are unreliable for guard decisions
    # — prefer false negative (don't block) over false positive (wrong block).
    if [ "$IS_DANGER" = "true" ] && [ "$SOURCE" = "transcript (real)" ]; then
        flywheel_event "context_guard" "triggered" "P2" || true
        if [ "$BLOCK_WRITES" = "true" ]; then
            # DG-48 fix: in autonomous mode, context guard must NOT hard-block.
            # High context in goal/ghost mode is informational — log and continue.
            if [ "$MODE" != "normal" ]; then
                echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | ${MODE} | context_guard | ${PCT}% | context exceeds danger but autonomous mode — skip hard block" >> "$STATE_DIR/skipped-errors.md"
                printf '⚠️ [%s mode] 上下文占比 %s%%。超出危险阈值但自主模式不阻断。请考虑 /compact。' \
                    "$MODE" "$PCT" | hc_emit_hook_json "PreToolUse" "true"
                exit 0
            fi
            agentic_status block \
                "Context Guard 硬阻断" \
                "当前会话上下文占比已达 ${PCT}%（危险阈值: ${DANGER_PCT}%，警告阈值: ${WARN_PCT}%）！" \
                "为防止灾难性幻觉、指令遗忘或代码损毁，已强制拦截写入操作。诊断工具 (Read/Grep/Bash) 可正常使用。请运行 '/compact' 压缩会话或手动重置 token 追踪。${MODE_LABEL}"
            exit 2
        else
            # 非写工具 或 heuristic 数据: 告警到 stderr + 不阻断
            echo "⚠️ [Context Guard] 上下文占比 ${PCT}%${MODE_LABEL} — heuristic 源不触发硬阻断，已告警记录" >&2
            printf '⚠️ 上下文占比 %s%%。超出危险阈值。请考虑 /compact。诊断操作未阻断。' \
                "$PCT" | hc_emit_hook_json "PreToolUse" "true"
            exit 0
        fi
    fi
fi

# Heuristic danger warning: transcript unavailable but context estimated high
# Inform user without blocking (false negative > false positive for heuristic data)
if [ "$IS_DANGER" = "true" ] && [ "$SOURCE" != "transcript (real)" ]; then
    echo "⚠️ [Context Guard] 上下文占比 ${PCT}% (${SOURCE}) — heuristic 源告警不阻断" >&2
    printf '⚠️ 上下文估算占比 %s%%。来源: %s。无法读取 transcript，阻断已跳过。请检查 transcript 目录或手动 /compact。%s' \
        "$PCT" "$SOURCE" "$([ "$MODE" != "normal" ] && echo " [${MODE} mode]" || echo '')" | hc_emit_hook_json "PreToolUse" "true"
    exit 0
fi

# Sweet-spot / Hand-off Alert: inject into AI context via additionalContext
if [ -x "$PYTHON_SCRIPT" ]; then
    SWEET_WARNING=$(echo "$RESULT" | ${PYTHON_BIN:-python3} -c "import sys, json; d=json.load(sys.stdin); print(d.get('sweet_spot_warning',''))" 2>/dev/null)
    if [ -n "$SWEET_WARNING" ]; then
        SWEET_JSON=$(echo "$SWEET_WARNING" | ${PYTHON_BIN:-python3} -c "import sys,json; print(json.dumps(json.dumps(sys.stdin.buffer.read().decode('utf-8','replace').strip())))" 2>/dev/null)
        SWEET_JSON="${SWEET_JSON:-\"\"}"
        printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":%s}}\n' "$SWEET_JSON"
    fi
fi

echo '{"continue": true}'
exit 0
