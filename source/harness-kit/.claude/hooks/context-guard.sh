#!/usr/bin/env bash

# harness-kit:managed v1.0.0

# context-guard.sh — PreToolUse:Edit/Write/Bash Hook

# 功能：真实 Context Token 百分比硬阻断 (Hard Gate)

# - 读取 OMC 状态并结合 OPENCODE_CONFIG_CONTENT 算出精准 ctx%

# - 如果大于等于 DANGER_THRESHOLD (如 80%)，立即强制掐断任何实质性修改或执行操作

# 退出码 2 = 阻断（防止幻觉/代码毁坏）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_guard" || exit 0

# 仅拦截变更操作，允许 Read、Grep 继续执行以便用户查看上下文
INPUT=$(cat)
if command -v jq &>/dev/null; then
    TOOL=$(echo "$INPUT" | jq -r '.tool // empty' 2>/dev/null)
else
    TOOL=$(echo "$INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi

if [ "$TOOL" != "edit" ] && [ "$TOOL" != "write" ] && [ "$TOOL" != "bash" ]; then
    exit 0
fi

# 执行探针脚本计算真实百分比
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../scripts/context_monitor.py"
if [ -x "$PYTHON_SCRIPT" ]; then
    RESULT=$(python3 "$PYTHON_SCRIPT" 2>/dev/null)
    IS_DANGER=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(str(d.get('is_danger', False)).lower())" 2>/dev/null)
    PCT=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('percentage', 0))" 2>/dev/null)

    if [ "$IS_DANGER" = "true" ]; then
        echo "🚫 [Context Guard 硬阻断] 当前会话上下文占比已达 ${PCT}%！" >&2
        echo "为了防止灾难性的幻觉、指令遗忘或代码损毁，已强制拦截了你的写/执行操作。" >&2
        echo "请立刻：运行 \`/compact\` 压缩会话，或开启一个新的分支对话。" >&2
        echo "👉 Re-insp-Kernel-Design:1.2-ContextGuard_OOMKill" >&2
        exit 2
    fi
fi

exit 0
