#!/bin/bash
# Carror OS 打包脚本
# 用法：bash scripts/package-release.sh
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
cd "$PROJECT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])")
TAG="v${VERSION}-stable"
log_info "版本：$TAG"
PKG_DIR="$PROJECT_DIR/packages"
HARNESS_SRC="source/harness-kit"
LX_SRC="source/lx-skills-v5"

# ─── Step 1: root -> source/harness-kit ───
# NOTE: AGENTS.md 有意不复制（根=元项目专属，source=通用分发模板）
log_step "1/4 同步 root -> source/harness-kit..."
cp CLAUDE.md "$HARNESS_SRC/CLAUDE.md"
rsync -a --delete .claude/hooks/       "$HARNESS_SRC/.claude/hooks/"
rsync -a --delete .claude/scripts/     "$HARNESS_SRC/.claude/scripts/"
rsync -a --delete .claude/references/  "$HARNESS_SRC/.claude/references/"
cp .claude/settings.json    "$HARNESS_SRC/.claude/settings.json"
cp .claude/harness.yaml     "$HARNESS_SRC/.claude/harness.yaml"
cp .claude/kernel.md        "$HARNESS_SRC/.claude/kernel.md"
cp .claude/index.md         "$HARNESS_SRC/.claude/index.md"
cp .claude/anti-patterns.md "$HARNESS_SRC/.claude/anti-patterns.md"
cp .claude/claude-next.md   "$HARNESS_SRC/.claude/claude-next.md"
rsync -a --delete --exclude=node_modules .cursor/  "$HARNESS_SRC/.cursor/"
rsync -a --delete --exclude=node_modules .opencode/ "$HARNESS_SRC/.opencode/"
rsync -a --delete --exclude=node_modules .hooks/     "$HARNESS_SRC/.hooks/"
# 清理运行时状态 和 lx-skills 专属内容
rm -f "$HARNESS_SRC/.omc/state/"*.json "$HARNESS_SRC/.omc/state/"*.txt 2>/dev/null || true
rm -rf "$HARNESS_SRC/.claude/nodes" "$HARNESS_SRC/.claude/profiles" \
       "$HARNESS_SRC/.claude/schemas" "$HARNESS_SRC/.claude/skills" \
       "$HARNESS_SRC/.claude/task_sys" "$HARNESS_SRC/.claude/plans" \
       "$HARNESS_SRC/.claude/state" 2>/dev/null || true
rm -f "$HARNESS_SRC/.claude/settings.local.json" \
      "$HARNESS_SRC/.claude/scheduled_tasks.lock" 2>/dev/null || true
log_info "  harness-kit 同步完成"

# ─── Step 2: root -> source/lx-skills-v5 ───
log_step "2/4 同步 root -> source/lx-skills-v5..."
for dep in lx-frontend-test lx-perf-analysis lx-style-guide; do
  [ -d "$LX_SRC/.claude/skills/$dep" ] && rm -rf "$LX_SRC/.claude/skills/$dep"
done
rsync -a --delete --exclude=.omc   .claude/nodes/    "$LX_SRC/.claude/nodes/"
rsync -a --delete                  .claude/profiles/ "$LX_SRC/.claude/profiles/"
rsync -a --delete --exclude=__pycache__ .claude/schemas/ "$LX_SRC/.claude/schemas/"
rsync -a --delete --exclude=__pycache__ --exclude='.omc/state/hud-*' \
  .claude/skills/ "$LX_SRC/.claude/skills/"
rsync -a --delete .claude/task_sys/ "$LX_SRC/.claude/task_sys/"
# 清理治理层内容 和 运行时状态
rm -rf "$LX_SRC/.claude/hooks" "$LX_SRC/.claude/scripts" \
       "$LX_SRC/.claude/references" "$LX_SRC/.claude/plans" \
       "$LX_SRC/.claude/state" "$LX_SRC/.claude/.omc" 2>/dev/null || true
rm -f "$LX_SRC/.claude/settings.json" "$LX_SRC/.claude/harness.yaml" \
      "$LX_SRC/.claude/kernel.md" "$LX_SRC/.claude/index.md" \
      "$LX_SRC/.claude/anti-patterns.md" "$LX_SRC/.claude/claude-next.md" \
      "$LX_SRC/.claude/settings.local.json" \
      "$LX_SRC/.claude/scheduled_tasks.lock" 2>/dev/null || true
find "$LX_SRC" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find "$LX_SRC" -name '*.pyc' -delete 2>/dev/null || true
log_info "  lx-skills 同步完成"

# ─── Step 3: package harness-kit ───
log_step "3/4 构建 harness-kit..."
cd "$HARNESS_SRC"
tar czf "$PKG_DIR/harness-kit-${TAG}.tar.gz" \
  --exclude=.omc --exclude=node_modules --exclude='*.pyc' \
  AGENTS.md CLAUDE.md .claude/ .cursor/ .opencode/ .hooks/
cd "$PROJECT_DIR"
H_CONTAM=$(tar tzf "$PKG_DIR/harness-kit-${TAG}.tar.gz" \
  | grep -cE '\.claude/(nodes|profiles|schemas|skills|task_sys)/' || true)
[ "$H_CONTAM" -gt 0 ] && log_warn "  ⚠️ harness-kit: $H_CONTAM 越界文件"
log_info "  harness-kit-${TAG}.tar.gz ($(du -h "$PKG_DIR/harness-kit-${TAG}.tar.gz" | cut -f1))"

# ─── Step 4: package lx-skills ───
log_step "4/4 构建 lx-skills..."
cd "$LX_SRC"
tar czf "$PKG_DIR/lx-skills-${TAG}.tar.gz" \
  --exclude=.omc --exclude=__pycache__ --exclude='*.pyc' \
  .claude/
cd "$PROJECT_DIR"
L_CONTAM=$(tar tzf "$PKG_DIR/lx-skills-${TAG}.tar.gz" \
  | grep -cE '\.claude/(hooks|scripts|references)/' || true)
[ "$L_CONTAM" -gt 0 ] && log_warn "  ⚠️ lx-skills: $L_CONTAM 越界文件"
log_info "  lx-skills-${TAG}.tar.gz ($(du -h "$PKG_DIR/lx-skills-${TAG}.tar.gz" | cut -f1))"

# ─── 验证 ───
log_info "打包完成！"
H_COUNT=$(tar tzf "$PKG_DIR/harness-kit-${TAG}.tar.gz" | wc -l)
L_COUNT=$(tar tzf "$PKG_DIR/lx-skills-${TAG}.tar.gz" | wc -l)
echo "  harness-kit: ${H_COUNT} 文件, 越界: ${H_CONTAM:-0}"
echo "  lx-skills:   ${L_COUNT} 文件, 越界: ${L_CONTAM:-0}"
