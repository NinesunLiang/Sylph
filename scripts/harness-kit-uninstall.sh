#!/bin/bash

# harness-kit 卸载脚本
# 版本：v5.2.3 | 日期：2026-04-24

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo "============================================"
echo " harness-kit 卸载向导 v5.2.3"
echo "============================================"
echo ""

[ -d ".claude" ] || { log_warn ".claude/ 不存在，无需卸载"; exit 0; }

log_warn "即将删除 harness-kit 文件："
echo " - CLAUDE.md | .claude/harness.yaml | .claude/kernel.md"
echo " - .claude/anti-patterns.md | .claude/claude-next.md | .claude/index.md"
echo " - .claude/hooks/（全部 $(ls .claude/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ') 个）"
echo ""
log_warn "以下将保留：nodes/ schemas/ skills/ profiles/ task_sys/ .omc/"
echo ""

read -p "确认卸载？(y/N) " -n 1 -r; echo ""
[[ $REPLY =~ ^[Yy]$ ]] || { log_info "卸载已取消"; exit 0; }

log_step "删除 harness-kit 文件..."
rm -f CLAUDE.md .claude/harness.yaml .claude/kernel.md \
    .claude/anti-patterns.md .claude/claude-next.md .claude/index.md \
    skill-atomization-guide.md
rm -rf .claude/hooks/
log_info "✅ harness-kit 卸载完成"
log_warn "个人资产（.omc/ nodes/ skills/ profiles/）已保留"
