#!/bin/bash
# init-omc.sh — 初始化 .omc/ 任务系统
# 用法: bash .claude/scripts/init-omc.sh [project_root]

ROOT="${1:-$(pwd)}"
cd "$ROOT" || exit 1

mkdir -p .omc/tasks .omc/tokens .omc/state

python3 .claude/scripts/carros_base.py init --task-id "sess_$(date +%Y%m%d)_0001"

echo "=== .omc 任务系统已初始化 ==="
echo "   Run 'python3 .claude/scripts/carros_base.py help' to see available commands"
