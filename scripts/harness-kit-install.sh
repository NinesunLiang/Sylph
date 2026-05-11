#!/bin/bash

# harness-kit 治理层独立安装脚本
# 版本：v6.1.9-stable | 日期：2026-05-03
# 用法：bash harness-kit-install.sh

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v6.1.9-stable"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAR="$SCRIPT_DIR/harness-kit-$VERSION.tar.gz"

# Agentic UI: CLI flags 驱动
FORCE_MODE=false

for arg in "$@"; do
    case "$arg" in
        --force|-f) FORCE_MODE=true ;;
    esac
done

echo "============================================"
echo " harness-kit 治理层安装向导"
echo " 版本：$VERSION（22 个 hooks）"
echo "============================================"
echo ""

[ -f "$TAR" ] || { log_error "安装包未找到：$TAR"; exit 1; }

if [ -d ".claude/hooks" ]; then
    log_warn ".claude/hooks/ 已存在（将覆盖）"
    log_info "正在自动备份并覆盖安装。（跳过确认请使用 --force/-f 参数）"
fi

log_step "创建目录..."
mkdir -p .claude/hooks .omc/state

log_step "解压 harness-kit-$VERSION..."
tar -xzf "$TAR" 2>/dev/null || { log_error "解压失败"; exit 1; }
chmod +x .claude/hooks/*.sh 2>/dev/null || true

# 平台兼容：生成 AGENTS.md 和更新 CLAUDE.md 为 @-include 跳板
if [ -f "AGENTS.md" ]; then
    log_info "AGENTS.md 已存在"
else
    cp "CLAUDE.md" "AGENTS.md" 2>/dev/null || true
    log_info "AGENTS.md 生成（OpenCode / 全平台主治理文件）"
fi
if ! grep -q "^@AGENTS.md" "CLAUDE.md" 2>/dev/null; then
    CLAUDE_CONTENT=$(cat CLAUDE.md 2>/dev/null)
    printf "@AGENTS.md\n\n%s\n" "$CLAUDE_CONTENT" > CLAUDE.md.tmp && mv CLAUDE.md.tmp CLAUDE.md
    log_info "CLAUDE.md 更新为 @-include 跳板（Claude Code 官方推荐格式）"
fi

log_step "验证..."
ERRORS=0
for F in CLAUDE.md .claude/harness.yaml .claude/index.md \
    .claude/hooks/completion-gate.sh .claude/hooks/permission-gate.sh \
    .claude/hooks/pretool-user-correction.sh .claude/hooks/posttool-write-cite.sh \
    .claude/hooks/pretool-rule-anchor.sh; do
    [ -f "$F" ] || { log_warn "缺少：$F"; ERRORS=$((ERRORS+1)); }
done
HOOKS=$(find .claude/hooks -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')
[ "$HOOKS" -ge 22 ] || { log_warn "hooks 数量不足（$HOOKS/22）"; ERRORS=$((ERRORS+1)); }

# v6.1.9-stable 内容校验
grep -q "铁律速查" ".claude/index.md" 2>/dev/null \
    || { log_warn "index.md 缺少铁律速查表"; ERRORS=$((ERRORS+1)); }
grep -q "铁律提醒" ".claude/hooks/turn-counter.sh" 2>/dev/null \
    || { log_warn "turn-counter.sh 缺少铁律注入"; ERRORS=$((ERRORS+1)); }

echo ""
[ "$ERRORS" -eq 0 ] && log_info "✅ 安装成功（$HOOKS 个 hooks）" || log_warn "⚠️ $ERRORS 个警告"

echo ""
echo " v6.1.9-stable 新增 hooks（上下文衰减加固）："
echo " pretool-rule-anchor.sh — 长对话防漂移锚点（第22个）"
echo " · 第15轮起，每次写文件前注入铁律提醒"
echo " · 检测顺手/顺便等漂移词，升级为强预警"
echo ""
echo " v6.1.9-stable 增强："
echo " index.md — 新增铁律速查表（6条，SessionStart即锚定）"
echo " turn-counter.sh — 每10轮注入铁律摘要（防长对话规则失效）"
echo ""
echo " 激活三模式（可选）："
echo " cat .claude/profiles/enhanced/append-to-claude.md >> CLAUDE.md"
echo ""
log_info "Carror OS — AI Native Developer Operating System。"
