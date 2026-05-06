#!/bin/bash

# Carror OS 完整安装脚本
# 版本：v6.1.7-stable | 日期：2026-04-24
# 用法：bash install.sh [base|enhanced|harness|skills]

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v6.1.7-stable"
GITHUB_REPO="your-username/carror-os" # 请替换为真实的 GitHub 仓库路径
GITHUB_RELEASE_URL="https://github.com/$GITHUB_REPO/releases/download/$VERSION"
INSTALL_MODE="${1:-base}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo " Carror OS 安装向导"
echo " 版本：$VERSION 模式：$INSTALL_MODE"
echo " Carror OS — AI Native Developer Operating System"
echo "============================================"
echo ""

case "$INSTALL_MODE" in
    base|enhanced|full|harness|skills) ;;
    *) log_error "未知模式：$INSTALL_MODE（用法：$0 [base|enhanced|harness|skills]）"; exit 1 ;;
esac
[ "$INSTALL_MODE" = "full" ] && INSTALL_MODE="enhanced"

# ─── 无损热更新机制 (Safe In-Place Upgrade) ──────────────
BACKUP_DIR=$(mktemp -d)
# 注意：不要用 trap "rm -rf $BACKUP_DIR" EXIT，脚本中途失败时备份不会被删除。
# 备份文件在所有场景（包括成功）下保留，由用户手动清理或下次安装时覆盖。
HAS_BACKUP=false

if [ -d ".claude" ]; then
    log_warn "检测到当前项目已安装 Carror OS (.claude/ 目录已存在)。"
    read -p " 是否执行无损升级？系统将保留你的配置与记忆资产，仅更新内核与技能引擎。(y/N) " -n 1 -r; echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || { log_info "安装已取消"; exit 0; }
    log_step "正在备份用户态资产 (User Assets)..."
    for file in harness.yaml claude-next.md anti-patterns.md kernel.md; do
        if [ -f ".claude/$file" ]; then
            cp ".claude/$file" "$BACKUP_DIR/"
            log_info "已安全备份 .claude/$file"
            HAS_BACKUP=true
        fi
    done
fi

log_step "创建目录结构..."
mkdir -p .claude/{hooks,nodes,schemas/{atomic,input,contract,output},task_sys/templates,skills,profiles/{base,go,node,python,rust},scripts}
mkdir -p .omc/state

extract_tar() {
    local tar_file="$1" desc="$2"
    if [ -f "$SCRIPT_DIR/$tar_file" ]; then
        log_info "发现本地包，解压 $desc ($tar_file)..."
        tar -xzf "$SCRIPT_DIR/$tar_file" 2>/dev/null || { log_error "解压 $tar_file 失败"; exit 1; }
    else
        log_warn "本地未找到 $tar_file，尝试从云端拉取 $desc..."
        local download_url="$GITHUB_RELEASE_URL/$tar_file"
        if command -v curl &>/dev/null; then
            curl -sSL -o "/tmp/$tar_file" "$download_url" || { log_error "云端下载失败。请检查网络或 GITHUB_REPO 配置"; exit 1; }
        elif command -v wget &>/dev/null; then
            wget -qO "/tmp/$tar_file" "$download_url" || { log_error "云端下载失败。请检查网络或 GITHUB_REPO 配置"; exit 1; }
        else
            log_error "系统中未找到 curl 或 wget，无法从云端安装。"; exit 1
        fi
        log_info "云端下载完成，正在解压..."
        tar -xzf "/tmp/$tar_file" 2>/dev/null || { log_error "云端包损坏，解压 $tar_file 失败"; exit 1; }
        rm -f "/tmp/$tar_file"
    fi
}

case "$INSTALL_MODE" in
    base)
        log_step "安装 Carror OS 基础版 (Base Edition: 零学习成本的静默守护者)..."
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（24 hooks）"
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（自动化审查总控）"
        log_step "应用基础版限制..."
        for s in lx-rpe lx-todo lx-task-spec lx-tdd-spec lx-debug-spec lx-root-cause-analysis lx-prd lx-browser-verify lx-golang-test lx-frontend-test lx-varlock lx-status lx-validate-skill; do
            rm -rf .claude/skills/$s
        done
        log_info "已精简为 10 个静默门禁 Skill。"
        ;;
    enhanced)
        log_step "安装 Carror OS 增强版 (Enhanced Edition: 高阶武器库)..."
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（24 hooks）"
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（全特性 23 个 Skills）"
        ;;
    harness)
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（24 hooks）"
        ;;
    skills)
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（全特性 23 个 Skills）"
        ;;
esac

chmod +x .claude/hooks/*.sh 2>/dev/null || true
chmod +x .claude/profiles/merge-profile.sh 2>/dev/null || true

# ─── 恢复用户态资产 ──────────────────────────────────────────
if [ "$HAS_BACKUP" = true ]; then
    log_step "正在恢复你的原始配置与项目记忆..."
    for file in harness.yaml claude-next.md anti-patterns.md kernel.md; do
        if [ -f "$BACKUP_DIR/$file" ]; then
            cp "$BACKUP_DIR/$file" ".claude/$file"
            log_info "已成功还原 .claude/$file"
        fi
    done
fi

if [ -d "$SCRIPT_DIR/opencode-plugins" ]; then
    mkdir -p .opencode/plugins
    cp -r "$SCRIPT_DIR/opencode-plugins/"* .opencode/plugins/
    log_info "OpenCode plugins 已安装（.opencode/plugins/）"
fi

if [ -f "AGENTS.md" ]; then
    log_info "AGENTS.md 已存在（主治理文件）"
else
    cp "CLAUDE.md" "AGENTS.md" 2>/dev/null && log_info "AGENTS.md 从 CLAUDE.md 生成" || true
fi

if ! grep -q "^@AGENTS.md" "CLAUDE.md" 2>/dev/null; then
    CLAUDE_CONTENT=$(cat CLAUDE.md 2>/dev/null)
    printf "@AGENTS.md\n\n%s\n" "$CLAUDE_CONTENT" > CLAUDE.md.tmp && mv CLAUDE.md.tmp CLAUDE.md
    log_info "CLAUDE.md 更新为 @-include 跳板格式"
fi

log_step "验证安装..."
ACTUAL=$(find .claude -type f 2>/dev/null | wc -l | tr -d ' ')
HOOKS=$(find .claude/hooks -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')

case "$INSTALL_MODE" in
    enhanced) MIN=70;;
    base) MIN=35;;
    harness) MIN=23;;
    skills) MIN=47;;
esac

ERRORS=0
chk() { [ -f "$1" ] || { log_warn "缺少：$1"; ERRORS=$((ERRORS+1)); }; }

case "$INSTALL_MODE" in
    enhanced|base|harness)
        chk "CLAUDE.md"; chk ".claude/harness.yaml"; chk ".claude/index.md"
        [ "$HOOKS" -ge 22 ] || { log_warn "hooks 不足（$HOOKS/22）"; ERRORS=$((ERRORS+1)); }
        ;;
esac

[ "$ACTUAL" -ge "$MIN" ] || { log_warn "文件数不足（$ACTUAL/$MIN）"; ERRORS=$((ERRORS+1)); }
echo ""
[ "$ERRORS" -eq 0 ] \
    && log_info "✅ 安装成功！共 $ACTUAL 个文件，$HOOKS 个 hooks" \
    || log_warn "⚠️ 安装完成，$ERRORS 个警告"

if [[ "$INSTALL_MODE" == "enhanced" || "$INSTALL_MODE" == "harness" || "$INSTALL_MODE" == "base" ]] \
    && [ -f ".claude/profiles/merge-profile.sh" ]; then
    echo ""
    echo "============================================"
    echo " 🌐 请选择项目主语言"
    echo "============================================"
    echo " 1) Go — *.go，三层架构，golangci-lint"
    echo " 2) Node.js/TS — *.ts/*.tsx，Controller-Service，tsc+eslint"
    echo " 3) Python — *.py，View-Service，pytest+ruff+mypy"
    echo " 4) Rust — *.rs，cargo build+test+clippy"
    echo " 5) Generic — 任意语言（base profile，已安装）"
    echo ""
    read -p " 请输入选项 [1-5]（回车=Generic）: " -n 1 -r LANG_CHOICE; echo ""

    case "$LANG_CHOICE" in
        1) LANG_NAME="go" ;;
        2) LANG_NAME="node" ;;
        3) LANG_NAME="python" ;;
        4) LANG_NAME="rust" ;;
        *) LANG_NAME="" ;;
    esac

    if [ -n "$LANG_NAME" ]; then
        CLAUDE_DIR=".claude" bash ".claude/profiles/merge-profile.sh" "$LANG_NAME" 2>/dev/null \
            && log_info "✅ 已合并 base + $LANG_NAME profile → .claude/harness.yaml" \
            || log_warn "merge 失败，保留 generic harness.yaml"
    else
        cp ".claude/profiles/base/harness.yaml" ".claude/harness.yaml" 2>/dev/null \
            && log_info "使用 Generic profile（base）→ .claude/harness.yaml"
    fi
fi

echo ""
echo "============================================"
echo " 下一步"
echo "============================================"
if [ "$INSTALL_MODE" = "base" ]; then
    echo " 🛡️ 基础版已就绪 (Base Edition)！"
    echo " - 内置 24 个底层物理拦截器 (防幻觉、防隐私泄露)。"
    echo " - 提交前输入 /lx-pre-commit 或 /lx-pre-push 即可自动进行门禁审查。"
    echo " - 若要解锁完整大任务流水线与看板，请运行 bash install.sh enhanced。"
else
    echo " ⚔️ 增强版已就绪 (Enhanced Edition)！"
    echo " - 使用 /lx-status 查看健康监控面板。"
    echo " - 使用 /lx-rpe 或 /lx-todo 开始任务驱动。"
    echo " - 参阅 .claude/CARROR-OS-FEATURES.md 获取完整武器库说明。"
fi
echo " 🔀 切换项目语言规范：bash .claude/profiles/merge-profile.sh <go|node|python|rust>"
echo "============================================"
log_info "Carror OS — AI Native Developer Operating System"
