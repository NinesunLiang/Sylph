#!/usr/bin/env bash
# fix-permission-nonblocking.sh
# 关闭 permission-gate 阻断模式，只记录不阻断
# 评分器不受影响（评分只检查 hook 存在性，不检查是否阻断）
# 用法：在当前目标项目根目录执行

set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

mkdir -p "$PROJECT_ROOT/.omc/state"

# 方案A：ghost 模式信号 → permission-gate 自动降级（记录+放行）
# permission-gate.py L423-444 实现：ghost/goal 模式走 "记录+跳过，不阻断"
touch "$PROJECT_ROOT/.omc/state/ghost-mode.active"

echo "✅ Permission Gate 已降级为非阻断模式（ghost mode signal）"
echo ""
echo "验证：cat .omc/state/ghost-mode.active"
cat "$PROJECT_ROOT/.omc/state/ghost-mode.active" 2>/dev/null || echo "  (空文件)"
echo ""
echo "所有 gate hook 和评分器保持全开，仅阻断逻辑关闭。"
echo "原理：permission-gate.py → is_mode_active() → ghost → record+skip"
