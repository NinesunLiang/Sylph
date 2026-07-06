#!/bin/bash
# init-omc.sh — 初始化 round3-core 项目
# 用法: bash .omc/scripts/init-omc.sh [project_root]
set -e

ROOT="${1:-$(pwd)}"
echo "Initializing round3-core in: $ROOT"

# 创建目录
mkdir -p "$ROOT/.omc/state/audit"
mkdir -p "$ROOT/.omc/archive"
mkdir -p "$ROOT/.omc/reference"

# 初始化 token
python3 .omc/scripts/carros_base.py init --task-id "sess_$(date +%Y%m%d)_0001"

echo "✅ round3-core initialized"
echo "   Run 'python3 .omc/scripts/carros_base.py help' to see available commands"
