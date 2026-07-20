#!/usr/bin/env bash
# lx-goal.sh — [DEPRECATED] 兼容 wrapper，已不再需要。
# 直接调用 python3 lx-goal.py 替代。保留以兼容旧 settings.json/local.json 引用。
# 用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/lx-goal.py" "$@"

