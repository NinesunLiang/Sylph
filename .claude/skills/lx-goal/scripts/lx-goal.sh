#!/usr/bin/env bash
# lx-goal.sh — 兼容 wrapper，实际逻辑委托给 lx-goal.py
# 用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/lx-goal.py" "$@"

