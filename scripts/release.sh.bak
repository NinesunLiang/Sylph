#!/usr/bin/env bash
# release.sh — Carror OS 一键发版脚本
# 用法: bash scripts/release.sh <patch|minor|major> ["Release notes"] [--yes]
# 示例: bash scripts/release.sh patch "python3 auto-install + Windows兼容" --yes
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

BUMP="${1:-patch}"
NOTES="${2:-"Carror OS release"}"
AUTO_YES=false
for arg in "$@"; do [[ "$arg" == --yes* ]] && AUTO_YES=true; done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ─── 预检 ───
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    log_error "非 git 仓库，无法发版"; exit 1
fi
if ! command -v gh &>/dev/null; then
    log_error "gh CLI 未安装"; exit 1
fi

# ═══════════════════════════════════════════════════════════════
log_step "1/7 版本号递增..."
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
log_info "  $OLD_VER → $NEW_VER ($RELEASE_DATE)"

# ═══════════════════════════════════════════════════════════════
log_step "2/7 同步版本号到所有文件..."

# VERSION.json
python3 -c "
import json
v=json.load(open('VERSION.json'))
v.update({'version':'$NEW_VER','release_date':'$RELEASE_DATE'})
json.dump(v,open('VERSION.json','w'),indent=2)
" && log_info "  VERSION.json"

# 4 个 VERSION 文件
for vf in source/harness-kit/VERSION source/lx-skills-v5/VERSION \
          .claude/skills/VERSION source/lx-skills-v5/.claude/skills/VERSION; do
    [ -f "$vf" ] && echo "$NEW_VER" > "$vf" && log_info "  $vf"
done

# install.sh (4 处版本引用)
for f in install.sh source/harness-kit/install.sh source/install.sh; do
    [ -f "$f" ] || continue
    sed -i '' "s/DEFAULT_VERSION=\"v[0-9.]*-stable\"/DEFAULT_VERSION=\"v${NEW_VER}-stable\"/" "$f" 2>/dev/null || \
    sed -i "s/DEFAULT_VERSION=\"v[0-9.]*-stable\"/DEFAULT_VERSION=\"v${NEW_VER}-stable\"/" "$f"
    sed -i '' "s/# 版本：v[0-9.]* |/# 版本：v${NEW_VER} |/" "$f" 2>/dev/null || \
    sed -i "s/# 版本：v[0-9.]* |/# 版本：v${NEW_VER} |/" "$f"
    log_info "  $f"
done

# AGENTS.md
sed -i '' "s/Base 版本 v[0-9.]*/Base 版本 v${NEW_VER}/" source/harness-kit/AGENTS.md 2>/dev/null || \
sed -i "s/Base 版本 v[0-9.]*/Base 版本 v${NEW_VER}/" source/harness-kit/AGENTS.md
log_info "  source/harness-kit/AGENTS.md"

# kernel.md
for kf in source/harness-kit/.claude/kernel.md; do
    [ -f "$kf" ] || continue
    sed -i '' "s/始终 \`[0-9.]*\` 格式/始终 \`${NEW_VER}\` 格式/" "$kf" 2>/dev/null || \
    sed -i "s/始终 \`[0-9.]*\` 格式/始终 \`${NEW_VER}\` 格式/" "$kf"
    sed -i '' "s/无前缀 \`[0-9.]*\`/无前缀 \`${NEW_VER}\`/" "$kf" 2>/dev/null || \
    sed -i "s/无前缀 \`[0-9.]*\`/无前缀 \`${NEW_VER}\`/" "$kf"
    log_info "  $kf"
done

# kernel-compact.md
sed -i '' "s/版本=[0-9.]*/版本=${NEW_VER}/" source/harness-kit/.claude/kernel-compact.md 2>/dev/null || \
sed -i "s/版本=[0-9.]*/版本=${NEW_VER}/" source/harness-kit/.claude/kernel-compact.md
log_info "  source/harness-kit/.claude/kernel-compact.md"

# ═══════════════════════════════════════════════════════════════
log_step "3/7 同步 install.sh 到所有副本..."
cp source/harness-kit/install.sh install.sh
cp source/harness-kit/install.sh source/install.sh
log_info "  root/install.sh + source/install.sh ← source/harness-kit/install.sh"

# ═══════════════════════════════════════════════════════════════
log_step "4/7 构建安装包..."
bash scripts/package-release.sh --skip-smoke --force 2>&1 | grep -E "版本|完成|越界|✅|❌" || {
    log_error "打包失败"; exit 1
}
log_info "  packages/harness-kit-v${NEW_VER}-stable.tar.gz"
log_info "  packages/lx-skills-v${NEW_VER}-stable.tar.gz"

# ═══════════════════════════════════════════════════════════════
log_step "5/7 三源一致性审计..."
AUDIT_OUT=$(bash .claude/scripts/audit-hooks.sh --check-source-mirror 2>&1) || true
RED_COUNT=$(echo "$AUDIT_OUT" | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
RED_COUNT="${RED_COUNT:-0}"
if [ "$RED_COUNT" -gt 0 ]; then
    log_warn "  ⚠️  三源漂移: ${RED_COUNT} 项 — 建议修复后再发版"
    echo "$AUDIT_OUT" | grep '🔴' | head -5
else
    log_info "  ✅ 三源一致"
fi

# ═══════════════════════════════════════════════════════════════
log_step "6/7 Git 提交 + 推送..."

echo ""
echo "  即将提交以下文件:"
git status -s | head -30
echo ""

TAG="v${NEW_VER}-stable"
COMMIT_MSG="chore: release v${NEW_VER} — $NOTES"

if [ "$AUTO_YES" = true ]; then
    CONFIRM="y"
    log_info "  --yes: 跳过确认，自动提交"
else
    read -p "  确认提交并推送? [y/N] " CONFIRM
fi

if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
    if [ "$AUTO_YES" = true ]; then
        # --yes模式: 提交所有改动(排除临时文件), 不漏新脚本
        git add -A
        git reset -- packages/harness-kit-v*.tar.gz packages/lx-skills-v*.tar.gz 2>/dev/null || true
        git add packages/harness-kit-v${NEW_VER}-stable.tar.gz packages/lx-skills-v${NEW_VER}-stable.tar.gz
    else
        # 交互模式: 只提交版本文件
        git add VERSION.json \
            source/harness-kit/VERSION source/lx-skills-v5/VERSION \
            .claude/skills/VERSION source/lx-skills-v5/.claude/skills/VERSION \
            source/harness-kit/AGENTS.md \
            source/harness-kit/.claude/kernel.md \
            source/harness-kit/.claude/kernel-compact.md \
            install.sh source/install.sh source/harness-kit/install.sh \
            packages/harness-kit-v${NEW_VER}-stable.tar.gz \
            packages/lx-skills-v${NEW_VER}-stable.tar.gz
    fi

    git commit -m "$COMMIT_MSG"
    git push
    log_info "  ✅ 已提交并推送: $COMMIT_MSG"
else
    log_warn "  跳过提交 — 手动: git commit -m \"$COMMIT_MSG\" && git push"
fi

# ═══════════════════════════════════════════════════════════════
log_step "7/7 GitHub Release..."

# 删除旧 release（同大版本号的前一个 patch）
OLD_TAG="v${MAJ}.${MIN}.$((PAT-1))-stable"
if gh release view -R NinesunLiang/Sylph "$OLD_TAG" &>/dev/null; then
    gh release delete -R NinesunLiang/Sylph "$OLD_TAG" -y 2>/dev/null && \
        log_info "  已清理旧 release: $OLD_TAG" || true
fi

gh release create "$TAG" \
    "packages/harness-kit-${TAG}.tar.gz" \
    "packages/lx-skills-${TAG}.tar.gz" \
    --title "Carror OS v${NEW_VER}" \
    --notes "$NOTES" 2>&1 && \
    log_info "  ✅ Release $TAG 已创建" || \
    log_error "  Release 创建失败"

# ─── 验证下载链路 ───
DOWNLOAD_URL="https://github.com/NinesunLiang/Sylph/releases/download/${TAG}/harness-kit-${TAG}.tar.gz"
HTTP_CODE=$(curl -sI "$DOWNLOAD_URL" 2>/dev/null | head -1 | awk '{print $2}')
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    log_info "  ✅ 下载链路验证通过 (HTTP $HTTP_CODE)"
else
    log_warn "  ⚠️  下载链路 HTTP $HTTP_CODE"
fi

echo ""
echo "════════════════════════════════════════"
echo "  🎉 Release v${NEW_VER} 完成！"
echo "  📦 $TAG"
echo "  🔗 https://github.com/NinesunLiang/Sylph/releases/tag/$TAG"
echo "════════════════════════════════════════"
