#!/usr/bin/env bash
# pretool-python-bridge.sh — 桥接 CC hooks → Python 脚本
# 确保跨平台 python3 可用
# 用法: pretool-python-bridge.sh <script_name> [args...]
# 示例: pretool-python-bridge.sh handoff.py before-compact

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON=$(command -v python3 || command -v python)

if [ -z "$PYTHON" ]; then
    echo '{"error": "python3 not found"}'
    exit 1
fi

SCRIPT_NAME="$1"
shift

"$PYTHON" "$PROJECT_ROOT/scripts/$SCRIPT_NAME" "$@"
