#!/usr/bin/env bash
# pretool-cruise-check.sh — SessionStart / PreToolUse — 巡航模式基础设施自检
# 检测 ghost/goal mode 激活但 feature/ 未初始化 → 提醒 AI 创建

source "$(dirname "$0")/harness_config.sh"
hc_enabled "cruise_check" || { echo '{"continue": true}'; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 检测模式
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" = "normal" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 检查 .cruising 文件
CRUISING_FILE="$PROJECT_ROOT/.cruising"
FEATURE_DIR="$PROJECT_ROOT/feature"

if [ ! -f "$CRUISING_FILE" ]; then
    # 巡航模式激活但信号文件不存在 → 提醒创建
    FEATURE_HINT=""
    if [ -f "$STATE_DIR/goal-mode.json" ]; then
        FEATURE_HINT=$(${PYTHON_BIN:-python3} -c "import json;d=json.load(open('$STATE_DIR/goal-mode.json'));print(d.get('feature','unknown'))" 2>/dev/null) && [ -n "$FEATURE_HINT" ] || FEATURE_HINT="unknown"
    elif [ -f "$STATE_DIR/ghost-mode.json" ]; then
        FEATURE_HINT=$(${PYTHON_BIN:-python3} -c "import json;d=json.load(open('$STATE_DIR/ghost-mode.json'));print(d.get('directive','unknown'))" 2>/dev/null) && [ -n "$FEATURE_HINT" ] || FEATURE_HINT="unknown"
    fi
    
    printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[cruise-check] %s mode 已激活但巡航基础设施未初始化。请运行: bash .claude/scripts/cruise-bootstrap.sh %s"}}\n' \
        "$MODE" "$FEATURE_HINT"
    exit 0
fi

# 信号文件存在但 feature/ 目录缺失
if [ ! -d "$FEATURE_DIR" ]; then
    echo "[cruise-check] .cruising 存在但 feature/ 目录缺失 — 创建中..."
    mkdir -p "$FEATURE_DIR"
fi

echo '{"continue": true}'
exit 0
