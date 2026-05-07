#!/bin/bash

# harness-kit 卸载脚本
# 版本：v5.2.3 | 日期：2026-04-24
# Agentic UI: CLI flags 驱动，默认 dry-run，--yes 执行

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

DO_UNINSTALL=false
DRY_RUN=true

for arg in "$@"; do
    case "$arg" in
        --yes|-y) DO_UNINSTALL=true; DRY_RUN=false ;;
        --dry-run) DRY_RUN=true; DO_UNINSTALL=false ;;
    esac
done

echo "============================================"
echo " harness-kit 卸载向导 v5.2.3"
echo "============================================"
echo ""

[ -d ".claude" ] || { log_warn ".claude/ 不存在，无需卸载"; exit 0; }

HOOK_COUNT=$(ls .claude/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')

echo "以下文件将被删除："
echo " - CLAUDE.md | .claude/harness.yaml | .claude/kernel.md"
echo " - .claude/anti-patterns.md | .claude/claude-next.md | .claude/index.md"
echo " - .claude/hooks/（全部 ${HOOK_COUNT:-0} 个）"
echo ""
echo "以下将保留：nodes/ schemas/ skills/ profiles/ task_sys/ .omc/"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "这是 dry-run 预览模式。使用 --yes/-y 参数执行实际卸载。"
    exit 0
fi

log_step "删除 harness-kit 文件..."
rm -f CLAUDE.md .claude/harness.yaml .claude/kernel.md \
    .claude/anti-patterns.md .claude/claude-next.md .claude/index.md \
    skill-atomization-guide.md
rm -rf .claude/hooks/
log_info "✅ harness-kit 卸载完成"
log_warn "个人资产（.omc/ nodes/ skills/ profiles/）已保留"
