#!/bin/bash

# harness-kit 卸载脚本
# 版本：v6.2.0 | 日期：2026-05-17
# Agentic UI: CLI flags 驱动，默认 dry-run，--yes 执行
# --remove-skills: 同时卸载局部和全局 lx-* skills

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

DO_UNINSTALL=false
DRY_RUN=true
REMOVE_SKILLS=false

for arg in "$@"; do
    case "$arg" in
        --yes|-y) DO_UNINSTALL=true; DRY_RUN=false ;;
        --dry-run) DRY_RUN=true; DO_UNINSTALL=false ;;
        --remove-skills) REMOVE_SKILLS=true ;;
    esac
done

echo "============================================"
echo " harness-kit 卸载向导 v6.2.0"
echo "============================================"
echo ""

[ -d ".claude" ] || { log_warn ".claude/ 不存在，无需卸载"; exit 0; }

HOOK_COUNT=$(ls .claude/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
GLOBAL_SKILLS="$HOME/.claude/skills"
LOCAL_LX_COUNT=$(ls -d .claude/skills/lx-* 2>/dev/null | wc -l | tr -d ' ')
GLOBAL_LX_COUNT=$(ls -d "$GLOBAL_SKILLS"/lx-* 2>/dev/null | wc -l | tr -d ' ')

echo "以下文件将被删除："
echo " - CLAUDE.md | .claude/harness.yaml | .claude/kernel.md"
echo " - .claude/anti-patterns.md | .claude/claude-next.md | .claude/index.md"
echo " - .claude/hooks/（全部 ${HOOK_COUNT:-0} 个）"
echo ""
echo "以下将保留（除非 --remove-skills）："
echo " - nodes/ schemas/ profiles/ task_sys/ .omc/"
echo " - .claude/skills/（${LOCAL_LX_COUNT} 个 lx-* skill）"
echo " - ${GLOBAL_SKILLS}/（${GLOBAL_LX_COUNT} 个 lx-* skill）"
echo ""
if [ "$REMOVE_SKILLS" = true ]; then
    echo "⚠️  --remove-skills 已启用：将同时删除局部和全局 lx-* skills"
fi
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "这是 dry-run 预览模式。"
    echo "   --yes/-y           执行实际卸载"
    echo "   --remove-skills    同时删除局部和全局 lx-* skills"
    exit 0
fi

log_step "删除 harness-kit 文件..."
rm -f CLAUDE.md .claude/harness.yaml .claude/kernel.md \
    .claude/anti-patterns.md .claude/claude-next.md .claude/index.md \
    skill-atomization-guide.md
rm -rf .claude/hooks/
log_info "✅ harness-kit 卸载完成"

# ─── 全局 Skill 卸载 ───
# install.sh 将 lx-* 同步到全局目录，卸载时一并清理
if [ -d "$GLOBAL_SKILLS" ]; then
    GLOBAL_REMOVED=0
    for skill_dir in "$GLOBAL_SKILLS"/lx-*; do
        if [ -d "$skill_dir" ]; then
            rm -rf "$skill_dir"
            GLOBAL_REMOVED=$((GLOBAL_REMOVED + 1))
        fi
    done
    log_info "✅ 全局 Skill 卸载完成（${GLOBAL_REMOVED} 个）"
fi

# ─── 局部 Skill 卸载（仅 --remove-skills）───
if [ "$REMOVE_SKILLS" = true ]; then
    LOCAL_REMOVED=0
    for skill_dir in .claude/skills/lx-*; do
        if [ -d "$skill_dir" ]; then
            rm -rf "$skill_dir"
            LOCAL_REMOVED=$((LOCAL_REMOVED + 1))
        fi
    done
    log_info "✅ 局部 Skill 卸载完成（${LOCAL_REMOVED} 个）"
else
    log_warn "局部 skills/ 已保留（使用 --remove-skills 同时删除）"
fi
