#!/usr/bin/env bash
# rollback-last-refactor.sh — 回滚本次大改动，恢复安全状态
# 用法: bash .claude/scripts/rollback-last-refactor.sh [--hard|--soft]
#   --soft: 仅关闭harness开关，保留代码 (默认)
#   --hard: git reset 到备份分支

set -e
cd "$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== Carror OS 回滚工具 ==="
MODE="${1:---soft}"

if [ "$MODE" = "--hard" ]; then
    BACKUP_BRANCH="backup/dev-big-refactor-20260531-1059"
    if git rev-parse --verify "$BACKUP_BRANCH" >/dev/null 2>&1; then
        echo "🔴 硬回滚到: $BACKUP_BRANCH"
        git reset --hard "$BACKUP_BRANCH"
        echo "✅ 已回滚"
    else
        echo "❌ 备份分支不存在: $BACKUP_BRANCH"
        exit 1
    fi
else
    echo "🟡 软回滚: 关闭新激活的4个hook开关"
    
    # 关闭知识管道
    sed -i '' 's/knowledge_condenser: true/knowledge_condenser: false/' .claude/harness.yaml
    sed -i '' 's/pretool_plan_gate: true/pretool_plan_gate: false/' .claude/harness.yaml
    sed -i '' 's/build_validator: true/build_validator: false/' .claude/harness.yaml
    sed -i '' 's/error_dna_auto_fix: true/error_dna_auto_fix: false/' .claude/harness.yaml
    
    echo "  knowledge_condenser: false"
    echo "  pretool_plan_gate: false"
    echo "  build_validator: false"
    echo "  error_dna_auto_fix: false"
    echo "✅ 软回滚完成，代码保留"
fi
