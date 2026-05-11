#!/bin/bash

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

log_info(){ echo -e "${GREEN}[INFO]${NC} $1"; }

log_step(){ echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v6.1.9-stable"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/source"
PACKAGES_DIR="$SCRIPT_DIR/packages"
rm -rf "$PACKAGES_DIR" && mkdir -p "$PACKAGES_DIR"
TEMP_DIR=$(mktemp -d); trap "rm -rf $TEMP_DIR" EXIT
# harness-kit
HK_SRC="$SOURCE_DIR/harness-kit"
HK_TMP="$TEMP_DIR/harness"
mkdir -p "$HK_TMP/.claude/hooks" "$HK_TMP/.claude/scripts" "$HK_TMP/.opencode/plugins"
cp -f "$HK_SRC/CLAUDE.md" "$HK_TMP/"
cp -f "$HK_SRC/AGENTS.md" "$HK_TMP/"
cp -f "$HK_SRC/.claude/kernel.md" "$HK_TMP/.claude/"
cp -f "$HK_SRC/.claude/anti-patterns.md" "$HK_TMP/.claude/"
cp -f "$HK_SRC/.claude/claude-next.md" "$HK_TMP/.claude/"
cp -f "$HK_SRC/.claude/harness.yaml" "$HK_TMP/.claude/"
cp -f "$HK_SRC/.claude/index.md" "$HK_TMP/.claude/"
cp -f "$HK_SRC/.claude/hooks/"*.sh "$HK_TMP/.claude/hooks/"
cp -f "$HK_SRC/.claude/scripts/"* "$HK_TMP/.claude/scripts/"
chmod +x "$HK_TMP/.claude/hooks/"*.sh
cp -f "$HK_SRC/.opencode/plugins/"*.ts "$HK_TMP/.opencode/plugins/" 2>/dev/null || true
cp -f "$HK_SRC/.opencode/plugins/package.json" "$HK_TMP/.opencode/plugins/" 2>/dev/null || true
# lx-skills
LX_SRC="$SOURCE_DIR/lx-skills"
LX_TMP="$TEMP_DIR/skills"
mkdir -p "$LX_TMP/.claude"
cp -rf "$LX_SRC/.claude/nodes" "$LX_TMP/.claude/"
cp -rf "$LX_SRC/.claude/schemas" "$LX_TMP/.claude/"
cp -rf "$LX_SRC/.claude/task_sys" "$LX_TMP/.claude/"
cp -rf "$LX_SRC/.claude/skills" "$LX_TMP/.claude/"
cp -rf "$LX_SRC/.claude/profiles" "$LX_TMP/.claude/"
cd "$HK_TMP" && tar -czf "$PACKAGES_DIR/harness-kit-$VERSION.tar.gz" . 2>/dev/null
cd "$LX_TMP" && tar -czf "$PACKAGES_DIR/lx-skills-$VERSION.tar.gz" . 2>/dev/null
log_step "复制辅助文件..."

for F in install.sh harness-kit-install.sh harness-kit-uninstall.sh final-exam.md CHANGELOG.md;
do [ -f "$SCRIPT_DIR/$F" ] && cp -f "$SCRIPT_DIR/$F" "$PACKAGES_DIR/"
done
[ -d "$SCRIPT_DIR/docs" ] && cp -r "$SCRIPT_DIR/docs" "$PACKAGES_DIR/"

log_info "✅ 打包完成！v6.1.9-stable is fully loaded."
