#!/usr/bin/env bash
# release.sh — Carror OS 一键发布脚本
# 用法: bash scripts/release.sh [patch|minor|major] ["Release notes"]
# 示例: bash scripts/release.sh patch "fix: Windows兼容 + Rust诊断修复"
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

BUMP="${1:-patch}"
NOTES="${2:-"Carror OS release"}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ═══ Step 1: 版本号 +1 ═══
log_info "Step 1/6: 版本号递增..."
OLD_VER=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])")
IFS='.' read -r MAJ MIN PAT <<< "$OLD_VER"
case "$BUMP" in
    major) MAJ=$((MAJ+1)); MIN=0; PAT=0 ;;
    minor) MIN=$((MIN+1)); PAT=0 ;;
    patch) PAT=$((PAT+1)) ;;
    *) log_error "未知 bump 类型: $BUMP (patch|minor|major)"; exit 1 ;;
esac
NEW_VER="$MAJ.$MIN.$PAT"
RELEASE_DATE=$(date +%Y-%m-%d)
python3 -c "
import json
v=json.load(open('VERSION.json'))
v.update({'version':'$NEW_VER','release_date':'$RELEASE_DATE'})
json.dump(v,open('VERSION.json','w'),indent=2)
"
log_info "  版本: $OLD_VER → $NEW_VER ($RELEASE_DATE)"

# ═══ Step 2: install.sh DEFAULT_VERSION 同步 ═══
log_info "Step 2/6: install.sh 版本同步..."
for f in install.sh source/harness-kit/install.sh source/install.sh; do
    [ -f "$f" ] || continue
    # DEFAULT_VERSION
    sed -i '' "s/DEFAULT_VERSION=\"v[0-9.]*-stable\"/DEFAULT_VERSION=\"v${NEW_VER}-stable\"/" "$f" 2>/dev/null || \
    sed -i "s/DEFAULT_VERSION=\"v[0-9.]*-stable\"/DEFAULT_VERSION=\"v${NEW_VER}-stable\"/" "$f"
    # Header comment
    sed -i '' "s/# 版本：v[0-9.]* |/# 版本：v${NEW_VER} |/" "$f" 2>/dev/null || \
    sed -i "s/# 版本：v[0-9.]* |/# 版本：v${NEW_VER} |/" "$f"
    log_info "  $f → v${NEW_VER}-stable"
done

# ═══ Step 3: 打包 ═══
log_info "Step 3/6: 构建安装包..."
if ! bash scripts/package-release.sh --skip-smoke --force 2>&1 | grep -E "版本|完成|越界|✅"; then
    log_error "打包失败 — 检查 source mirror 漂移后重试"
    exit 1
fi

# ═══ Step 4: Git 提交 ═══
log_info "Step 4/6: Git 提交 (需手动确认)..."
git add VERSION.json install.sh source/harness-kit/install.sh source/install.sh \
    packages/harness-kit-v${NEW_VER}-stable.tar.gz \
    packages/lx-skills-v${NEW_VER}-stable.tar.gz
echo ""
echo "  即将提交以下文件:"
git status -s
echo ""
echo "  Commit message: chore: release v${NEW_VER} — $NOTES"
echo ""
read -p "  确认提交? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    log_warn "  跳过 commit"
    exit 0
fi
git commit -m "chore: release v${NEW_VER} — $NOTES"
git push
log_info "  ✅ 已推送"

# ═══ Step 5: GitHub Release ═══
log_info "Step 5/6: 创建 GitHub Release..."
if command -v gh &>/dev/null; then
    TAG="v${NEW_VER}-stable"
    gh release create "$TAG" \
        "packages/harness-kit-${TAG}.tar.gz" \
        "packages/lx-skills-${TAG}.tar.gz" \
        --title "Carror OS v${NEW_VER}" \
        --notes "$NOTES" 2>&1 && \
        log_info "  ✅ Release $TAG 已创建" || \
        log_error "  Release 创建失败，手动: gh release create $TAG packages/"
else
    log_warn "  gh CLI 未安装，跳过 Release 创建"
fi

# ═══ Step 6: 验证 ═══
log_info "Step 6/6: 验证..."
bash .claude/scripts/audit-hooks.sh --check-source-mirror 2>&1 | grep -E "✅|🔴" | head -3
log_info "  版本: $(cat VERSION.json)"
log_info "  包: $(ls -la packages/harness-kit-v${NEW_VER}-stable.tar.gz 2>/dev/null | awk '{print $NF, $5}')"

echo ""
log_info "🎉 Release v${NEW_VER} 完成！"
