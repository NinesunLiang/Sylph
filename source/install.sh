#!/bin/bash

# Carror OS 完整安装脚本
# 版本：v6.1.8-stable | 日期：2026-05-04
# 用法：bash install.sh [base|enhanced|harness|skills]

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION="v6.1.8-stable"
GITHUB_REPO="NinesunLiang/Sylph"
GITHUB_RELEASE_URL="https://github.com/$GITHUB_REPO/releases/download/$VERSION"

# 兼容两种运行方式：bash packages/install.sh（本地包）和 curl ... | bash（远程下载）
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "bash" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)"
fi

# Agentic UI: CLI flags 驱动，零交互提示
UPGRADE_MODE="auto"  # auto | skip | force
LANG_SPEC=""
POSITIONAL=()

for arg in "$@"; do
    case "$arg" in
        --yes|-y) UPGRADE_MODE="force" ;;
        --no-upgrade) UPGRADE_MODE="skip" ;;
        --lang=*) LANG_SPEC="${arg#*=}" ;;
        --lang) SKIP_NEXT=1 ;;
        go|node|python|rust|generic)
            [ "${SKIP_NEXT:-0}" -eq 1 ] && { LANG_SPEC="$arg"; SKIP_NEXT=0; continue; }
            POSITIONAL+=("$arg") ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
INSTALL_MODE="${POSITIONAL[0]:-base}"

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

# ─── 无损热更新机制 (Safe In-Place Upgrade) ──────────────────
BACKUP_DIR=$(mktemp -d)
# 注意：不使用 trap EXIT 删除备份。中途失败时保留备份文件由用户手动清理。
HAS_BACKUP=false

# 备份已有根目录治理文件，无论是否为升级安装
for file in CLAUDE.md AGENTS.md; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        log_info "已安全备份 $file（用户项目配置）"
        HAS_BACKUP=true
    fi
done

if [ -d ".claude" ]; then
    log_warn "检测到已安装 Carror OS (.claude/ 目录已存在)。"
    if [ "$UPGRADE_MODE" = "skip" ]; then
        log_info "跳过升级（--no-upgrade），保留现有安装。"
    else
        log_step "正在自动执行无损升级 — 保留配置与记忆资产，仅更新内核与技能引擎。"
        log_info "（跳过升级请使用 --no-upgrade 参数）"
        for file in harness.yaml claude-next.md anti-patterns.md kernel.md; do
            if [ -f ".claude/$file" ]; then
                cp ".claude/$file" "$BACKUP_DIR/"
                log_info "已安全备份 .claude/$file"
                HAS_BACKUP=true
            fi
        done
    fi
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
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（32 hooks）"
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（自动化审查总控）"
        log_step "应用基础版限制..."
        for s in lx-rpe lx-todo lx-task-spec lx-tdd-spec lx-debug-spec lx-root-cause-analysis lx-prd lx-browser-verify lx-golang-test lx-frontend-test lx-varlock lx-status lx-validate-skill lx-race; do
            rm -rf .claude/skills/$s
        done
        log_info "已精简为 10 个静默门禁 Skill。"
        ;;
    enhanced)
        log_step "安装 Carror OS 增强版 (Enhanced Edition: 高阶武器库)..."
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（32 hooks）"
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（全特性 24 个 Skills）"
        ;;
    harness)
        extract_tar "harness-kit-$VERSION.tar.gz" "治理层（32 hooks）"
        ;;
    skills)
        extract_tar "lx-skills-$VERSION.tar.gz" "能力层（全特性 24 个 Skills）"
        ;;
esac

chmod +x .claude/hooks/*.sh 2>/dev/null || true
chmod +x .claude/scripts/*.py .claude/scripts/*.sh 2>/dev/null || true
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

# ─── 用户治理文件合并迁移 ──────────────────────────────────────
if [ "$HAS_BACKUP" = true ] && [ -f "AGENTS.md" ]; then
    USER_CONTENT=""
    if [ -f "$BACKUP_DIR/AGENTS.md" ]; then
        USER_CONTENT=$(cat "$BACKUP_DIR/AGENTS.md")
        log_info "从备份恢复用户 AGENTS.md 内容"
    elif [ -f "$BACKUP_DIR/CLAUDE.md" ]; then
        if ! grep -q "^@AGENTS.md" "$BACKUP_DIR/CLAUDE.md" 2>/dev/null; then
            USER_CONTENT=$(cat "$BACKUP_DIR/CLAUDE.md")
            log_info "从备份 CLAUDE.md 提取用户项目配置（无 @AGENTS.md 引用）"
        fi
    fi

    if [ -n "$USER_CONTENT" ]; then
        TEMPLATE=$(cat "AGENTS.md")
        # 降级 Carror OS 标题层级：# → ##，保留用户原始 # 的原创性
        DEMOTED=$(echo "$TEMPLATE" | sed 's/^# /## /g; s/^#$/##/')
        {
            echo "$USER_CONTENT"
            echo ""
            echo "## ════════════════════════════════════════════"
            echo "## Carror OS 治理框架"
            echo "## ════════════════════════════════════════════"
            echo ""
            echo "$DEMOTED"
        } > AGENTS.md
        log_info "已合并 → AGENTS.md：用户项目配置在前（#），Carror OS 治理模板在后（##）"
    fi
fi

# 确保 CLAUDE.md 为 @-include 跳板格式
if ! grep -q "^@AGENTS.md" "CLAUDE.md" 2>/dev/null; then
    CLAUDE_CONTENT=$(cat CLAUDE.md 2>/dev/null || echo "")
    printf '@AGENTS.md\n\n%s\n' "$CLAUDE_CONTENT" > CLAUDE.md
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
        chk "CLAUDE.md"; chk ".claude/settings.json"; chk ".claude/harness.yaml"; chk ".claude/index.md"
        [ "$HOOKS" -ge 30 ] || { log_warn "hooks 不足（$HOOKS/30）"; ERRORS=$((ERRORS+1)); }
        ;;
esac
[ "$ACTUAL" -ge "$MIN" ] || { log_warn "文件数不足（$ACTUAL/$MIN）"; ERRORS=$((ERRORS+1)); }
echo ""
[ "$ERRORS" -eq 0 ] \
    && log_info "✅ 安装成功！共 $ACTUAL 个文件，$HOOKS 个 hooks" \
    || log_warn "⚠️ 安装完成，$ERRORS 个警告"

if [[ "$INSTALL_MODE" == "enhanced" || "$INSTALL_MODE" == "harness" || "$INSTALL_MODE" == "base" ]] \
    && [ -f ".claude/profiles/merge-profile.sh" ]; then

    # Agentic UI: --lang flag > 自动检测 > 兜底 generic
    if [ -z "$LANG_SPEC" ]; then
        if [ -f "go.mod" ]; then
            LANG_SPEC="go"
            log_info "检测到 go.mod → 自动选择 Go profile（可通过 --lang <name> 覆盖）"
        elif [ -f "package.json" ]; then
            LANG_SPEC="node"
            log_info "检测到 package.json → 自动选择 Node.js profile（可通过 --lang <name> 覆盖）"
        elif ls *.py &>/dev/null 2>/dev/null || [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
            LANG_SPEC="python"
            log_info "检测到 Python 项目 → 自动选择 Python profile（可通过 --lang <name> 覆盖）"
        elif [ -f "Cargo.toml" ]; then
            LANG_SPEC="rust"
            log_info "检测到 Cargo.toml → 自动选择 Rust profile（可通过 --lang <name> 覆盖）"
        else
            LANG_SPEC=""
        fi
    fi

    if [ -n "$LANG_SPEC" ]; then
        log_info "使用 $LANG_SPEC profile"
        case "$LANG_SPEC" in
            go|node|python|rust) CLAUDE_DIR=".claude" bash ".claude/profiles/merge-profile.sh" "$LANG_SPEC" 2>/dev/null \
                && log_info "✅ 已合并 base + $LANG_SPEC profile → .claude/harness.yaml" \
                || log_warn "merge 失败，保留 generic harness.yaml" ;;
            generic|*) cp ".claude/profiles/base/harness.yaml" ".claude/harness.yaml" 2>/dev/null \
                && log_info "使用 Generic profile（base）→ .claude/harness.yaml" ;;
        esac
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
    echo " - 内置 27+ 个底层物理拦截器 (防幻觉、防隐私泄露)。"
    echo " - 提交前输入 /lx-pre-commit 或 /lx-pre-push 即可自动进行门禁审查。"
    echo " - 若要解锁完整大任务流水线与看板，请运行 \`bash install.sh enhanced\`。"
else
    echo " ⚔️ 增强版已就绪 (Enhanced Edition)！"
    echo " - 使用 /lx-status 查看健康监控面板。"
    echo " - 使用 /lx-rpe 或 /lx-todo 开始任务驱动。"
    echo " - 参阅 .claude/CARROR-OS-FEATURES.md 获取完整武器库说明。"
fi
echo " 🔀 切换项目语言规范：bash .claude/profiles/merge-profile.sh <go|node|python|rust>"
echo "============================================"
log_info "Carror OS — AI Native Developer Operating System"
