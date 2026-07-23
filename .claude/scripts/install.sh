#!/usr/bin/env bash
# CarrorOS Base — 轻量跨平台安装脚本
# 版本: v1.0.0 | 日期: 2026-07-21
# 用法: bash install.sh [target_directory]

set -eo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v1.0.0"

# ─── 跨平台检测 ────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Darwin)                      echo "macos" ;;
    Linux)                       echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*)       echo "windows" ;;
    *)                           echo "unknown" ;;
  esac
}

# ─── 依赖检测 ──────────────────────────────────────
check_deps() {
  local missing=0
  command -v python3 &>/dev/null || { warn "python3 未安装"; missing=1; }
  command -v git &>/dev/null    || { warn "git 未安装"; missing=1; }
  [ "$missing" -eq 0 ] || { echo "请先安装缺失依赖"; exit 1; }
}

# ─── 安装包(本地 packages/ 目录优先) ──────────────
install_pkg() {
  local src
  src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/packages/carroros-base"
  if [ -d "$src" ]; then
    # macOS/Linux: dotglob 复制隐藏文件
    if [ "$(detect_os)" = "windows" ]; then
      cp -r "$src"/* "$TARGET/" 2>/dev/null || true
      cp -r "$src"/.* "$TARGET/" 2>/dev/null || true
    else
      shopt -s dotglob
      cp -r "$src"/* "$TARGET/"
      shopt -u dotglob
    fi
  else
    warn "本地包未找到: $src"
    echo "请先确保 packages/carroros-base/ 目录存在"
    exit 1
  fi
  echo "$VERSION" > "$TARGET/VERSION"
  echo "CarrorOS Base" > "$TARGET/.gitignore"
}

# ─── 主流程 ────────────────────────────────────────
OS=$(detect_os)
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd)" || { warn "目录不存在: $1"; exit 1; }

echo ""
echo "CarrorOS Base Installer $VERSION"
echo "  目标目录: $TARGET"
echo "  系统平台: $OS"
echo ""

check_deps
step "安装中..."
install_pkg
info "安装完成"
echo ""
echo "  位置: $TARGET | 版本: $VERSION"
echo "  快速开始: cd $TARGET && python3 .claude/scripts/carros_base.py init"
echo ""

