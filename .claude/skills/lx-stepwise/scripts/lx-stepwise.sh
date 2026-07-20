#!/usr/bin/env bash
# lx-stepwise.sh — [DEPRECATED] 兼容 wrapper，已不再需要。
# 直接调用 python3 lx-stepwise.py 替代。保留以兼容旧 settings.json/local.json 引用。
# 用法: lx-stepwise on|status|pass-card|fail-card|ask|resolve|off
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/lx-stepwise.py" "$@"
