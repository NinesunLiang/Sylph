#!/usr/bin/env bash
# detect-oracle-env.sh — Oracle 环境自适应检测
# Role: 检测运行平台能力, 输出 Oracle 最佳执行路径
# 输出格式: {"oracle_path":"agent_omc"|"agent_omo"|"local_prompt","agent_available":true|false}

# 默认: 本地 prompt
ORACLE_PATH="local_prompt"
AGENT_AVAILABLE=false
PLATFORM="unknown"

# ── Detection ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 1. OMC (oh-my-claude): Agent 工具是 Claude Code 原生能力
#    .omc/ 目录存在 = OMC 已安装
if [ -d "$PROJECT_ROOT/.omc" ]; then
    ORACLE_PATH="agent_omc"
    AGENT_AVAILABLE=true
    PLATFORM="claude-code-omc"
# 2. OMO (oh-my-opencode): .opencode/plugins/ 存在 OMO 配置
elif [ -d "$PROJECT_ROOT/.opencode/plugins" ] && [ -f "$PROJECT_ROOT/.opencode/oh-my-openagent.json" ]; then
    ORACLE_PATH="agent_omo"
    AGENT_AVAILABLE=true
    PLATFORM="opencode-omo"
# 3. Claude Code 原生 (无 OMC): Agent 工具仍然可用
elif [ -f "$PROJECT_ROOT/.claude/settings.json" ]; then
    ORACLE_PATH="agent_omc"
    AGENT_AVAILABLE=true
    PLATFORM="claude-code-native"
fi

# ── Output ──────────────────────────────────────────────────────
if [ "${1:-}" = "--json" ]; then
    cat <<JSON
{"oracle_path":"$ORACLE_PATH","agent_available":$AGENT_AVAILABLE,"platform":"$PLATFORM"}
JSON
else
    echo "$ORACLE_PATH"
fi

exit 0
