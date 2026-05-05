#!/usr/bin/env bash

# harness-kit:managed v1.0.0

# context-guard.sh — PreToolUse:Edit/Write/Bash Hook

# 功能：真实 Context Token 百分比硬阻断 (Hard Gate)

# - 读取 OMC 状态并结合 OPENCODE_CONFIG_CONTENT 算出精准 ctx%

# - 如果大于等于 DANGER_THRESHOLD (如 80%)，立即强制掐断任何实质性修改或执行操作

# 退出码 2 = 阻断（防止幻觉/代码毁坏）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_guard" || exit 0

# R26: 产品定位"冷酷无情 AI 管理员"要求 95% 上下文时任何工具都应受门禁。
# 原白名单 (edit/write/bash) 与 R19 settings.json matcher=.* 形成漂移：
#   matcher 派发所有事件 → 脚本又主动放行 Read/Grep → 真实 hook 行为与产品承诺不符。
# 现在不再在脚本层过滤工具名，全工具统一走阈值判断。
INPUT=$(cat)

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
        cat >&2 <<EOF

🚫 [Context Guard 硬阻断] 当前会话上下文占比已达 ${PCT}%（危险阈值: ${DANGER_PCT}%，警告阈值: ${WARN_PCT}%）！

为了防止灾难性的幻觉、指令遗忘或代码损毁，已强制拦截了你的写/执行操作。

请选择：
  1. 运行 /compact 压缩会话
  2. 开启新分支对话
  3. 强制覆盖（风险自负）

输入数字 (1-3):
EOF
        exit 2
    fi
fi

exit 0
