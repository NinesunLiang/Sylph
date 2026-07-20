#!/usr/bin/env bash
# lx-stepwise.sh — 兼容 wrapper,实际逻辑委托给 lx-stepwise.py
# 用法: lx-stepwise on|status|pass-card|fail-card|ask|resolve|off
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/lx-stepwise.py" "$@"
