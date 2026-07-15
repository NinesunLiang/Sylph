#!/usr/bin/env bash
# CarrorOS Base — 安装脚本
# 版本：v1.0.0 | 日期：2026-07-15
# 用法：bash install.sh [target_directory]
# 默认安装到当前目录

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v1.0.0"
GITHUB_REPO="NinesunLiang/Sylph"
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd)" || { echo "目录不存在: $1"; exit 1; }

# 检测安装源：本地包还是远程下载
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)"
fi

# 远程包 URL 模板
REMOTE_BASE="https://github.com/$GITHUB_REPO/releases/download/$VERSION"

banner() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║         CarrorOS Base Installer             ║"
    echo "║         ${VERSION}                           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
}

detect_platform() {
    info "检测系统环境..."
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "     系统: macOS $(sw_vers -productVersion 2>/dev/null || echo '?')"
        if command -v brew &>/dev/null; then
            echo "     Homebrew: ✅"
        fi
    elif [[ "$(uname)" == "Linux" ]]; then
        echo "     系统: Linux"
    fi
    echo "     Python: $(python3 --version 2>/dev/null || echo '未安装')"
    echo "     Git: $(git --version 2>/dev/null || echo '未安装')"
    echo ""
}

check_prereqs() {
    local missing=0
    command -v python3 &>/dev/null || { warn "需要 python3"; missing=1; }
    command -v git &>/dev/null || { warn "需要 git"; missing=1; }
    if [ $missing -eq 1 ]; then
        echo "请先安装依赖"
        exit 1
    fi
}

get_package() {
    local pkg_dir="$SCRIPT_DIR/packages/carroros-base"
    
    if [ -d "$pkg_dir" ]; then
        step "从本地包安装..."
        # 复制所有文件，包括 .claude/ 等点开头目录
        shopt -s dotglob
        cp -r "$pkg_dir"/* "$TARGET/"
        shopt -u dotglob
        return 0
    fi
    
    # 尝试远程下载
    step "从 GitHub Releases 下载..."
    local tarball="$TARGET/carroros-base.tar.gz"
    local url="$REMOTE_BASE/carroros-base.tar.gz"
    
    if command -v curl &>/dev/null; then
        curl -sSL --connect-timeout 10 "$url" -o "$tarball"
    elif command -v wget &>/dev/null; then
        wget -q "$url" -O "$tarball"
    else
        warn "无法下载，请手动下载后重试："
        echo "  $url"
        exit 1
    fi
    
    if [ -f "$tarball" ] && [ -s "$tarball" ]; then
        tar xzf "$tarball" -C "$TARGET"
        rm "$tarball"
        info "下载完成"
    else
        warn "下载失败或文件为空"
        exit 1
    fi
}

setup_version() {
    echo "$VERSION" > "$TARGET/VERSION"
}

setup_gitignore() {
    cat > "$TARGET/.gitignore" << 'EOF'
# CarrorOS 运行时数据
.omc/
__pycache__/
*.pyc
.env
benchmark/repos/bench-test-app/
benchmark/envs/
benchmark/runs/
benchmark/repos/
EOF
}

summary() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║         CarrorOS Base 安装完成 ✅            ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "  位置: $TARGET"
    echo "  版本: $VERSION"
    echo ""
    echo "  目录结构:"
    echo "    AGENTS.md      — 行为治理路由"
    echo "    CLAUDE.md       — 操作守则"
    echo "    .claude/"
    echo "      ├── hooks/   — 治理 hooks（5个）"
    echo "      ├── scripts/ — 核心引擎"
    echo "      ├── settings.json"
    echo "      ├── kernel.md"
    echo "      └── harness.yaml"
    echo "    benchmark/     — 评测框架（80 任务）"
    echo ""
    echo "  快速开始:"
    echo "    cd $TARGET"
    echo "    python3 .claude/scripts/carros_base.py init"
    echo ""
    echo "  评测:"
    echo "    python3 benchmark/runner.py validate"
    echo "    python3 benchmark/runner.py plan --phase 1"
    echo ""
}

# ─── 主流程 ──────────────────────────────────────────

banner
detect_platform
check_prereqs

step "安装 CarrorOS Base 到: $TARGET"
get_package
setup_version
setup_gitignore
summary
