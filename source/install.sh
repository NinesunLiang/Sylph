#!/usr/bin/env bash

# Carror OS 完整安装脚本
# 版本：v6.3.0 | 日期：2026-05-26
# 用法：bash install.sh [base|enhanced|harness|skills]

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 默认版本（本地包或 API 失败时的降级）
DEFAULT_VERSION="v6.3.0-stable"
VERSION="$DEFAULT_VERSION"
GITHUB_REPO="NinesunLiang/Sylph"

# 远程安装时动态解析最新版本（curl ... | bash 场景）
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "bash" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)"
fi
if [ -z "$SCRIPT_DIR" ] || [ ! -d "$SCRIPT_DIR/../packages" ]; then
    LATEST_VERSION=$(curl -sSL --connect-timeout 5 "https://api.github.com/repos/$GITHUB_REPO/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    if [ -n "$LATEST_VERSION" ]; then
        VERSION="$LATEST_VERSION"
        log_info "已检测到最新版本：$VERSION"
    fi
fi

GITHUB_RELEASE_URL="https://github.com/$GITHUB_REPO/releases/download/$VERSION"

# 跨平台兼容检测
# D1-1: sed -i 语法差异（macOS BSD sed vs Linux GNU sed）
if sed -i 's/hello/hello/' /dev/null 2>/dev/null; then
    SED_INPLACE=("sed" "-i")
else
    SED_INPLACE=("sed" "-i" "")
fi

# D1-2: sha256sum 兼容（macOS 用 shasum -a 256）
if command -v sha256sum &>/dev/null; then
    SHA256_CMD="sha256sum"
elif command -v shasum &>/dev/null; then
    SHA256_CMD="shasum -a 256"
else
    SHA256_CMD=""  # 后续用到时 exit 99
fi

# Agentic UI: CLI flags 驱动，零交互提示
UPGRADE_MODE="auto"  # auto | skip | force
LANG_SPEC=""
LSP_MODE="install"  # install(默认自动安装) | skip(跳过) | "" (仅检测建议)
POSITIONAL=()

for arg in "$@"; do
    case "$arg" in
        --yes|-y) UPGRADE_MODE="force" ;;
        --no-upgrade) UPGRADE_MODE="skip" ;;
        --lang=*) LANG_SPEC="${arg#*=}" ;;
        --lang) SKIP_NEXT=1 ;;
        --lsp) LSP_MODE="install" ;;
        --no-lsp) LSP_MODE="skip" ;;
        go|node|python|rust|generic)
            [ "${SKIP_NEXT:-0}" -eq 1 ] && { LANG_SPEC="$arg"; SKIP_NEXT=0; continue; }
            POSITIONAL+=("$arg") ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
INSTALL_MODE="${POSITIONAL[0]:-base}"

# ─── 平台检测 + Windows 引导 ─────────────────────────────────
PLATFORM_OS="unknown"
case "$(uname -s 2>/dev/null)" in
    Darwin)  PLATFORM_OS="macOS" ;;
    Linux)   PLATFORM_OS="Linux" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM_OS="Windows-GitBash" ;;
esac

# Windows CMD/PowerShell 检测: 没有 uname = 原生 Windows
if [ "$PLATFORM_OS" = "unknown" ]; then
    echo "============================================"
    echo " Carror OS 安装向导"
    echo "============================================"
    echo ""
    echo -e "${RED}⚠️  检测到原生 Windows 终端 (CMD/PowerShell)${NC}"
    echo ""
    echo "   Carror OS 需要 Bash 环境。请选择以下方式之一:"
    echo ""
    echo "   推荐: 安装 Git for Windows (自带 Git Bash)"
    echo "     https://git-scm.com/download/win"
    echo "     安装后右键项目目录 → 'Git Bash Here'"
    echo "     然后在 Git Bash 中运行: bash install.sh"
    echo ""
    echo "   最佳: 安装 WSL2 + Ubuntu"
    echo "     wsl --install -d Ubuntu"
    echo "     然后在 WSL 中运行: bash install.sh"
    echo ""
    echo "   💡 Git Bash 零配置，WSL2 兼容性最佳"
    exit 1
fi

echo "============================================"
echo " Carror OS 安装向导"
echo " 版本：$VERSION 模式：$INSTALL_MODE"
echo " 平台：$PLATFORM_OS"
echo " Carror OS — AI Native Developer Operating System"
echo "============================================"
echo ""

case "$INSTALL_MODE" in
    base|enhanced|full|harness|skills) ;;
    *) log_error "未知模式：${INSTALL_MODE}（用法：$0 [base|enhanced|harness|skills]）"; exit 1 ;;
esac

[ "$INSTALL_MODE" = "full" ] && INSTALL_MODE="enhanced"

# ─── 预检：运行时依赖检测 ──────────────────────────────────────
echo ""
log_step "正在检测运行时依赖..."

MISSING_DEPS=0

# ─── python3 查找/修复辅助函数 ───
resolve_python() {
    # 优先级: python3 > python (Windows) > 常见路径扫描
    if command -v python3 &>/dev/null; then
        echo "python3"; return
    fi
    if command -v python &>/dev/null; then
        local pver; pver=$(python --version 2>&1)
        if [[ "$pver" == *"Python 3"* ]]; then
            echo "python"; return
        fi
    fi
    # Windows: 扫描常见安装路径
    for p in /c/Python3*/python.exe /c/Program\ Files/Python3*/python.exe \
             /c/Users/*/AppData/Local/Programs/Python/Python3*/python.exe \
             /c/ProgramData/chocolatey/bin/python3.exe \
             /mingw64/bin/python3.exe /usr/bin/python3.exe; do
        for found in $p; do
            if [ -x "$found" ]; then
                echo "$found"; return
            fi
        done
    done
    echo ""
}

# ─── python3 检测 ───
PYTHON_BIN=$(resolve_python)
if [ -n "$PYTHON_BIN" ]; then
    PY_VER=$("$PYTHON_BIN" --version 2>&1 || echo "未知版本")
    log_info "python3 已安装: $PY_VER ($PYTHON_BIN)"
    if "$PYTHON_BIN" -c "import secrets" 2>/dev/null; then
        log_info "python3 secrets 模块可用 (Python >= 3.6)"
    else
        log_warn "python3 缺少 secrets 模块 (Python < 3.6)"
        log_warn "  permission-gate 随机验证码将使用降级方案 (od urandom / openssl / shell fallback)"
        MISSING_DEPS=$((MISSING_DEPS + 1))
    fi
    # DEPRECATED (2026-05-24): export -f does NOT survive process boundaries.
    # Hooks are invoked as independent bash processes by the CLI harness — the
    # alias created here has zero effect at runtime. The real fix is in
    # harness_config.sh: _resolve_python() + $PYTHON_BIN export at source time.
    # See: client_fellback/feedback.md S8 (Windows验收), DG-46 (手动touch教训)
    if [ "$PYTHON_BIN" != "python3" ] && ! command -v python3 &>/dev/null; then
        eval "python3() { $PYTHON_BIN \"\$@\"; }" 2>/dev/null || true
        export -f python3 2>/dev/null || true  # known ineffective, kept for install.sh internal use
        log_warn "已设置 python3 别名 → $PYTHON_BIN (仅本shell有效，hooks独立进程需靠 harness_config.sh)"
    fi
else
    echo -e "${RED}[DEPS]${NC} python3 未安装 — 正在自动安装..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            brew install python3 2>&1 | tail -3
        else
            log_error "macOS 需先安装 Homebrew: https://brew.sh"; exit 1
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin"* ]]; then
        if command -v winget &>/dev/null; then
            log_info "  通过 winget 安装 Python 3..."
            winget install -e --id Python.Python.3.11 --silent 2>&1 | tail -5 || \
            winget install -e --id Python.Python.3 --silent 2>&1 | tail -5 || true
        elif command -v choco &>/dev/null; then
            choco install python3 -y 2>&1 | tail -3
        elif command -v scoop &>/dev/null; then
            scoop install python3 2>&1 | tail -3
        else
            log_error "Windows 需安装 winget/choco/scoop 之一，或手动安装: https://python.org"; exit 1
        fi
        # Windows: winget 安装后 PATH 可能未刷新，重新扫描
        PYTHON_BIN=$(resolve_python)
    elif command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y python3 2>&1 | tail -3
    elif command -v yum &>/dev/null; then
        sudo yum install -y python3 2>&1 | tail -3
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 2>&1 | tail -3
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python3 2>&1 | tail -3
    elif command -v apk &>/dev/null; then
        apk add --no-cache python3 2>&1 | tail -3
    else
        log_error "无法识别包管理器，请手动安装 python3 后重试"; exit 1
    fi

    # 安装后验证
    if [ -z "$PYTHON_BIN" ]; then
        PYTHON_BIN=$(resolve_python)
    fi
    if [ -n "$PYTHON_BIN" ]; then
        log_info "python3 安装完成: $("$PYTHON_BIN" --version 2>&1)"
        # DEPRECATED: see note above (harness_config.sh is the real fix)
        if [ "$PYTHON_BIN" != "python3" ] && ! command -v python3 &>/dev/null; then
            eval "python3() { $PYTHON_BIN \"\$@\"; }" 2>/dev/null || true
            export -f python3 2>/dev/null || true
            log_info "已设置 python3 别名 → $PYTHON_BIN (仅本shell有效)"
        fi
    else
        log_warn "python3 自动安装未生效，请手动安装后重试: https://python.org/downloads/"
        MISSING_DEPS=$((MISSING_DEPS + 1))
    fi
fi



# 汇总
if [ "$MISSING_DEPS" -gt 0 ]; then
    echo -e "${YELLOW}[DEPS]${NC} ⚠️  检测到 $MISSING_DEPS 个依赖缺失"
    echo -e "${YELLOW}[DEPS]${NC} Carror OS 已为所有缺失依赖准备了降级方案，安装可继续。"
    echo -e "${YELLOW}[DEPS]${NC} 但为获得最佳体验和加密级随机验证码，建议安装后补全依赖。"
fi
echo ""

# ─── 无损热更新机制 (Safe In-Place Upgrade) ──────────────────
BACKUP_DIR=$(mktemp -d)
# 注意：不使用 trap EXIT 删除备份。中途失败时保留备份文件供 rollback 使用。
HAS_BACKUP=false

# 备份根目录治理文件
for file in CLAUDE.md AGENTS.md; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        log_info "已安全备份 ${file}（用户项目配置）"
        HAS_BACKUP=true
    fi
done

if [ -d ".claude" ]; then
    log_warn "检测到已安装 Carror OS (.claude/ 目录已存在)。"
    if [ "$UPGRADE_MODE" = "skip" ]; then
        log_info "跳过升级（--no-upgrade），保留现有安装。"
    else
        log_step "正在自动执行无损升级 — 保留全部资产，仅更新内核与技能引擎。"
        log_info "（跳过升级请使用 --no-upgrade 参数）"

        # ── 全量备份 .claude/ ──
        mkdir -p "$BACKUP_DIR/.claude"
        cp -r .claude/* "$BACKUP_DIR/.claude/" 2>/dev/null
        log_info "已备份 .claude/（全部资产：hooks/nodes/settings/skills/profiles/scripts 等）"

        # ── 备份 .omc/ 状态目录 ──
        if [ -d ".omc" ]; then
            mkdir -p "$BACKUP_DIR/.omc"
            cp -r .omc/* "$BACKUP_DIR/.omc/" 2>/dev/null
            log_info "已备份 .omc/（会话状态：todo/handoff/error-dna 等）"
        fi

        # ── 备份跨平台配置 ──
        for dir in .codex .cursor .gemini .opencode; do
            [ -d "$dir" ] && { cp -r "$dir" "$BACKUP_DIR/" 2>/dev/null; log_info "已备份 $dir/"; }
        done

        # ── hooks sha256 快照（后续对比用户是否修改过官方 hook） ──
        if [ -n "$SHA256_CMD" ]; then
            for f in .claude/hooks/*.sh; do
                [ -f "$f" ] && $SHA256_CMD "$f" >> "$BACKUP_DIR/hooks-sha256.txt" 2>/dev/null
            done
        else
            touch "$BACKUP_DIR/hooks-sha256.txt"  # 空文件，跳过 sha256 对比
            log_warn "sha256sum/shasum 不可用，跳过 hooks sha256 快照"
        fi

        # ── 用户 settings.json 副本（用于 3-way merge） ──
        [ -f ".claude/settings.json" ] && cp ".claude/settings.json" "$BACKUP_DIR/settings-user.json"

        HAS_BACKUP=true
    fi
fi

# ── 生成回滚脚本 ──
# 无论升级还是全新安装都生成，保证链路一致
cat > "$BACKUP_DIR/rollback.sh" << ROLLBACK
#!/bin/bash
# 由 Carror OS install.sh 自动生成 @ $(date)
# 用法：bash ${BACKUP_DIR}/rollback.sh
set -e
CWD="$(pwd)"
echo "正在回滚 Carror OS 升级..."
# 恢复根目录文件
[ -f "$BACKUP_DIR/AGENTS.md" ] && cp "$BACKUP_DIR/AGENTS.md" "\$CWD/AGENTS.md" 2>/dev/null || true
[ -f "$BACKUP_DIR/CLAUDE.md" ] && cp "$BACKUP_DIR/CLAUDE.md" "\$CWD/CLAUDE.md" 2>/dev/null || true
# 恢复 .claude/
if [ -d "$BACKUP_DIR/.claude" ]; then
    rm -rf "\$CWD/.claude" 2>/dev/null
    cp -r "$BACKUP_DIR/.claude" "\$CWD/.claude"
fi
# 恢复 .omc/
if [ -d "$BACKUP_DIR/.omc" ]; then
    rm -rf "\$CWD/.omc" 2>/dev/null
    cp -r "$BACKUP_DIR/.omc" "\$CWD/.omc"
fi
# 恢复跨平台配置
for dir in .codex .cursor .gemini .opencode; do
    [ -d "$BACKUP_DIR/\$dir" ] && { rm -rf "\$CWD/\$dir" 2>/dev/null; cp -r "$BACKUP_DIR/\$dir" "\$CWD/\$dir"; } || true
done
echo "✅ 回滚完成。备份保留在：$BACKUP_DIR"
ROLLBACK
chmod +x "$BACKUP_DIR/rollback.sh"
log_info "已生成回滚脚本 — 升级失败时运行：bash ${BACKUP_DIR}/rollback.sh"

log_step "创建目录结构..."
mkdir -p .claude/{hooks,nodes,schemas/{atomic,input,contract,output},task_sys/templates,skills,profiles/{base,go,node,python,rust},scripts}
mkdir -p .omc/state

extract_tar() {
    local tar_file="$1" desc="$2"
    if [ -f "$SCRIPT_DIR/$tar_file" ]; then
        log_info "发现本地包，解压 $desc ($tar_file)..."
        tar -xzf "$SCRIPT_DIR/$tar_file" 2>/dev/null || { log_error "解压 $tar_file 失败"; exit 1; }
    else
        log_warn "本地未找到 ${tar_file}，尝试从云端拉取 ${desc}..."
        local download_url="$GITHUB_RELEASE_URL/$tar_file"
        if command -v curl &>/dev/null; then
            curl -sSL --connect-timeout 15 --max-time 120 --retry 3 --retry-all-errors \
                -o "/tmp/$tar_file" "$download_url" || { log_error "云端下载失败。请检查网络或 GITHUB_REPO 配置"; exit 1; }
        elif command -v wget &>/dev/null; then
            wget -q --timeout=15 --tries=3 -O "/tmp/$tar_file" "$download_url" || { log_error "云端下载失败。请检查网络或 GITHUB_REPO 配置"; exit 1; }
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
        for s in lx-oma-orch lx-oma-hier lx-oma-split lx-oma-gov lx-task-spec lx-rpe lx-prd lx-debug-spec lx-tdd-spec lx-browser-verify lx-web-perf lx-stepwise lx-race lx-learner; do
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

# ═══ DG-97: 升级时自动清理已废弃 hook ═══
# 防止旧版安装残留的僵尸脚本污染新版本
DEPRECATED_HOOKS="pretool-rule-anchor|proactive-handoff|build-validator|error-dna-auto-fix|posttool-read-cite|plan-gate|knowledge-condenser|pretool-ask-guard"
CLEANED=0
if [ -d ".claude/hooks" ]; then
    for hook_file in .claude/hooks/*.sh; do
        hook_name=$(basename "$hook_file" .sh)
        if echo "$hook_name" | grep -qE "$DEPRECATED_HOOKS"; then
            rm -f "$hook_file"
            log_info "  🧹 清理废弃 hook: $hook_name.sh (v6.2+ 已移除)"
            CLEANED=$((CLEANED+1))
            # 同步清理 harness.yaml (hyphen→underscore)
            hook_name_under="${hook_name//-/_}"
            [ -f ".claude/harness.yaml" ] && \
                "${SED_INPLACE[@]}" "/^  ${hook_name_under}:.*$/d" ".claude/harness.yaml" 2>/dev/null || true
        fi
    done
fi
[ "$CLEANED" -gt 0 ] && log_info "✅ 已清理 $CLEANED 个废弃 hook + harness.yaml 配置 (DG-97)"

# DG-104: 生成上游 hook 基线（原始安装状态，用于下次升级 3-way merge）
# line 262 cp -r .claude/* → $BACKUP_DIR/.claude/ 会在下次安装前自动将此文件带入备份
# 恢复段(483-501)读取 BACKUP_DIR 中的旧 ORIG 与新安装版本做 3-way 对比
if [ -n "$SHA256_CMD" ]; then
    $SHA256_CMD .claude/hooks/*.sh > .claude/hooks-sha256-orig.txt 2>/dev/null
else
    touch .claude/hooks-sha256-orig.txt
    log_warn "sha256sum 不可用，hook 升级检测降级为 2-way 模式"
fi

# ─── 全局 Skill 安装（OpenCode 平台兼容）──────────────────────
# OpenCode 无法直接使用项目本地 .claude/skills/，需在全局目录创建符号链接
# 关键: 使用 ln -s 而非 cp -r — 技能内部有 ../../nodes/ 等相对路径引用，
#       直接复制到 ~/.claude/skills/ 会导致所有路径解析到 ~/.claude/ 而非项目根
#       符号链接保证文件仍在原位置，所有相对路径引用不受影响
if [ "$INSTALL_MODE" = "base" ] || [ "$INSTALL_MODE" = "enhanced" ] || [ "$INSTALL_MODE" = "skills" ]; then
    GLOBAL_SKILLS="$HOME/.claude/skills"
    mkdir -p "$GLOBAL_SKILLS"
    PROJECT_DIR="$(pwd)"
    log_info "链接 lx-* skills 到全局目录 ($GLOBAL_SKILLS)..."
    for skill_dir in .claude/skills/lx-*; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            rm -rf "$GLOBAL_SKILLS/$skill_name"
            ln -s "$PROJECT_DIR/$skill_dir" "$GLOBAL_SKILLS/$skill_name"
        fi
    done
    log_info "✅ 全局 Skill 符号链接完成（OpenCode 兼容）"
fi

# ─── 填充模板占位符 ──────────────────────────────────────────
# 自动替换 kernel.md 中的 {project_name} 和 {date}
PROJECT_NAME=$(basename "$(pwd)")
INSTALL_DATE=$(date +%Y-%m-%d)
if [ -f ".claude/kernel.md" ]; then
    if grep -q '{project_name}' ".claude/kernel.md" 2>/dev/null; then
        "${SED_INPLACE[@]}" "s/{project_name}/$PROJECT_NAME/g; s/{date}/$INSTALL_DATE/g" ".claude/kernel.md"
        log_info "已填充 kernel.md 模板占位符（project=${PROJECT_NAME}, date=${INSTALL_DATE}）"
    fi
fi

# ─── 路径重写：settings.json __PROJECT_ROOT__ → 实际项目路径 ───
# 跨平台 sed -i: macOS BSD 需 -i ''，Linux/Win GNU 只需 -i
if [ -f ".claude/settings.json" ]; then
    if grep -q '__PROJECT_ROOT__' ".claude/settings.json" 2>/dev/null; then
        USER_PROJECT_DIR="$(pwd)"
        if sed -i.backup "s@__PROJECT_ROOT__@$USER_PROJECT_DIR@g" ".claude/settings.json" 2>/dev/null; then
            rm -f ".claude/settings.json.backup"
        else
            sed -i "s@__PROJECT_ROOT__@$USER_PROJECT_DIR@g" ".claude/settings.json" 2>/dev/null
        fi
        log_info "已重写 settings.json 路径为实际项目目录（${USER_PROJECT_DIR}）"
    fi
fi

# ─── 恢复用户态资产 ──────────────────────────────────────────
if [ "$HAS_BACKUP" = true ]; then
    log_step "正在恢复用户配置与记忆资产..."

    # 恢复 .omc/ 状态目录（完全保留，不碰内容）
    if [ -d "$BACKUP_DIR/.omc" ]; then
        rm -rf .omc 2>/dev/null; cp -r "$BACKUP_DIR/.omc" .omc
        log_info "已恢复 .omc/ 会话状态"
    fi

    # 恢复跨平台配置
    for dir in .codex .cursor .gemini .opencode; do
        [ -d "$BACKUP_DIR/$dir" ] && { rm -rf "$dir" 2>/dev/null; cp -r "$BACKUP_DIR/$dir" .; log_info "已恢复 $dir/"; }
    done

    # 恢复官方配置类文件（用户可能定制了这些，以用户版为准）
    for file in harness.yaml claude-next.md anti-patterns.md; do
        if [ -f "$BACKUP_DIR/.claude/$file" ]; then
            cp "$BACKUP_DIR/.claude/$file" ".claude/$file"
            log_info "已恢复 .claude/${file}（用户配置）"
        fi
    done

    # 新安装: 使用集体智慧种子模板初始化 claude-next.md
    if [ ! -f ".claude/claude-next.md" ] && [ -f ".claude/claude-next.template.md" ]; then
        cp ".claude/claude-next.template.md" ".claude/claude-next.md"
        log_info "已初始化 claude-next.md（22 条通用教训种子）"
    fi

    # 恢复 kernel.md —— 但如果旧版是未填充的模板，使用新版
    if [ -f "$BACKUP_DIR/.claude/kernel.md" ]; then
        if grep -q '{project_name}' "$BACKUP_DIR/.claude/kernel.md" 2>/dev/null; then
            : # 旧版未填充，跳过恢复，保留新版已填充版本
        else
            cp "$BACKUP_DIR/.claude/kernel.md" ".claude/kernel.md"
            log_info "已恢复 .claude/kernel.md（用户已填充）"
        fi
    fi

    # hooks sha256 3-way merge — DG-104 修复
    # ORIG = 首次安装时的上游基线，USER = 用户备份版，NEW = 当前新版
    # 决策: ORIG=USER≠NEW → 上游升级 → 保留新版(不恢复)
    #       ORIG≠USER → 用户真改了 → 恢复用户版
    #       ORIG不存在 → 首次安装 → 保守恢复用户版
    if [ -f "$BACKUP_DIR/hooks-sha256.txt" ]; then
        log_step "正在检查 hooks 变更（3-way merge）..."
        HAVE_ORIG=false
        [ -f "$BACKUP_DIR/.claude/hooks-sha256-orig.txt" ] && HAVE_ORIG=true
        
        while IFS= read -r line; do
            user_sha=$(echo "$line" | awk '{print $1}')
            hook_rel=$(echo "$line" | awk '{print $2}')
            hook_name=$(basename "$hook_rel")
            user_hook="$BACKUP_DIR/.claude/hooks/$hook_name"
            new_hook=".claude/hooks/$hook_name"
            
            [ -f "$user_hook" ] && [ -f "$new_hook" ] && [ -n "$SHA256_CMD" ] || continue
            new_sha=$($SHA256_CMD "$new_hook" 2>/dev/null | awk '{print $1}')
            [ "$user_sha" = "$new_sha" ] && continue  # 相同 → 无需恢复
            
            if $HAVE_ORIG; then
                orig_sha=$(grep "$hook_rel" "$BACKUP_DIR/.claude/hooks-sha256-orig.txt" 2>/dev/null | awk '{print $1}')
                
                if [ -z "$orig_sha" ]; then
                    # ORIG 中无此 hook → 用户新增，保留用户版
                    cp "$user_hook" "$new_hook"
                    log_info "↩ $hook_name（用户新增 hook，已恢复）"
                elif [ "$orig_sha" = "$user_sha" ]; then
                    # 用户没改，上游升级了 → 保留新版（DG-104 核心修复）
                    log_info "↑ $hook_name（上游升级，保留新版）"
                else
                    # 用户确实修改过 → 恢复用户版
                    cp "$user_hook" "$new_hook"
                    log_info "↩ $hook_name（检测到用户修改，已恢复）"
                fi
            else
                # Fallback: 首次安装无 ORIG → 保守模式，恢复用户版
                cp "$user_hook" "$new_hook"
                log_info "↩ $hook_name（无基线，已恢复用户版）"
            fi
        done < "$BACKUP_DIR/hooks-sha256.txt"
    fi

    # 恢复用户自定义：节点、脚本、第三方 skill、profile、race、schemas、task templates
    for dir in nodes scripts profiles race schemas task_sys/templates; do
        [ -d "$BACKUP_DIR/.claude/$dir" ] || continue
        for f in "$BACKUP_DIR/.claude/$dir"/*; do
            [ -f "$f" ] || continue
            base=$(basename "$f")
            target=".claude/$dir/$base"
            # 官方 skills 以 lx- 开头 → 不恢复（优先新版）
            if [ "$dir" = "skills" ] && [[ "$base" == lx-* ]]; then continue; fi
            cp "$f" "$target" 2>/dev/null
        done
    done

    # 恢复第三方 skill（非 lx- 前缀）
    if [ -d "$BACKUP_DIR/.claude/skills" ]; then
        for f in "$BACKUP_DIR/.claude/skills"/*; do
            [ -d "$f" ] || continue
            base=$(basename "$f")
            [[ "$base" == lx-* ]] && continue
            cp -r "$f" ".claude/skills/$base" 2>/dev/null
            log_info "已恢复第三方 skill：$base"
        done
    fi

    # settings.json 3-way merge（python3 实现）
    # DG-102: 修复 pipefail 吞错 — 用临时文件替代管道，防止 Python 失败时 set -eo pipefail 静默杀脚本
    if [ -f "$BACKUP_DIR/settings-user.json" ] && [ -n "${PYTHON_BIN:-}" ] && command -v "${PYTHON_BIN:-python3}" &>/dev/null; then
        log_step "正在合并 settings.json（保留自定义 hook 注册）..."
        MERGE_LOG="/tmp/carror-settings-merge-$$.log"
        set +eo pipefail  # 允许捕获 Python 退出码
        ${PYTHON_BIN:-python3} -c "
import json, sys
try:
    with open('$BACKUP_DIR/settings-user.json') as f:
        old = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print('settings.json merge skipped — no user backup found')
    sys.exit(0)
try:
    with open('.claude/settings.json') as f:
        new = json.load(f)
except Exception as e:
    print(f'ERROR: 无法读取 .claude/settings.json: {e}', file=sys.stderr)
    sys.exit(2)
old_hooks = set(old.get('hooks', {}).keys())
new_hooks = set(new.get('hooks', {}).keys())
extra = {k: old['hooks'][k] for k in (old_hooks - new_hooks)}
if extra:
    new.setdefault('hooks', {}).update(extra)
old_skills = old.get('skills_enabled', {})
for k, v in old_skills.items():
    new.setdefault('skills_enabled', {})[k] = v
old_hooks_enabled = old.get('hooks_enabled', {})
for k, v in old_hooks_enabled.items():
    new.setdefault('hooks_enabled', {})[k] = v
try:
    with open('.claude/settings.json', 'w') as f:
        json.dump(new, f, indent=2)
except Exception as e:
    print(f'ERROR: 无法写入 .claude/settings.json: {e}', file=sys.stderr)
    sys.exit(3)
print(f'settings.json merge: {len(extra)} custom hooks, {len(old_skills)} skill toggles, {len(old_hooks_enabled)} hook toggles preserved')
" > "$MERGE_LOG" 2>&1
        MERGE_EXIT=$?
        set -eo pipefail  # 恢复严格模式
        while IFS= read -r line; do log_info "$line"; done < "$MERGE_LOG"
        rm -f "$MERGE_LOG"
        if [ "$MERGE_EXIT" -ne 0 ]; then
            log_warn "settings.json 合并失败 (exit=$MERGE_EXIT) — 继续安装，但旧自定义 hook 注册可能丢失"
        fi
    fi

    # 恢复 settings.local.json（用户自有文件，无冲突）
    [ -f "$BACKUP_DIR/.claude/settings.local.json" ] && cp "$BACKUP_DIR/.claude/settings.local.json" ".claude/settings.local.json"

    log_info "用户资产恢复完成"
fi

# ─── 跨平台 CLI 检测（后续多处引用）──────────────────────────
HAS_OPCODE=false; HAS_OMO=false; HAS_CODEX=false; HAS_CURSOR=false; HAS_CLAUDE=false; HAS_OMC=false
command -v opencode &>/dev/null && HAS_OPCODE=true
npm list -g oh-my-opencode &>/dev/null && HAS_OMO=true
command -v codex &>/dev/null && HAS_CODEX=true
[ -f ".cursor/hooks.json" ] || [ -d ".cursor" ] && HAS_CURSOR=true
command -v claude &>/dev/null && HAS_CLAUDE=true
npm list -g oh-my-claude &>/dev/null && HAS_OMC=true

if [ -d "$SCRIPT_DIR/opencode-plugins" ]; then
    mkdir -p .opencode/plugins
    cp -r "$SCRIPT_DIR/opencode-plugins/"* .opencode/plugins/
    log_info "OpenCode plugins 已安装（.opencode/plugins/）"
fi

# ─── 文档安装 ─────────────────────────────────────────────────
if [ -d "$SCRIPT_DIR/.claude/docs" ]; then
    mkdir -p .claude/docs
    cp -r "$SCRIPT_DIR/.claude/docs/"* .claude/docs/
    log_info "故事系列 + 教程系列已安装（.claude/docs/）"
fi

# ─── OpenCode + OMO 自动安装 ──────────────────────────────────
# OMO (oh-my-opencode) = OpenCode 的 hook 桥接层，是 Carror OS 安全网的硬依赖
if $HAS_OPCODE && ! $HAS_OMO; then
    log_step "检测到 OpenCode，正在自动安装 OMO (oh-my-opencode)..."
    if command -v npm &>/dev/null; then
        npm install -g oh-my-opencode 2>&1 | tail -3
        npm list -g oh-my-opencode &>/dev/null && HAS_OMO=true
        if $HAS_OMO; then
            log_info "OpenCode + OMO 已就绪 — hooks 全能力可用 (7/7)"
        else
            log_warn "OMO 自动安装失败，请手动执行: npm install -g oh-my-opencode"
        fi
    else
        log_warn "未检测到 npm，无法自动安装 OMO — 请先安装 Node.js: https://nodejs.org"
        log_warn "然后手动执行: npm install -g oh-my-opencode"
    fi
elif $HAS_OPCODE && $HAS_OMO; then
    log_info "OpenCode + oh-my-opencode 已就绪，hooks 全能力可用 (7/7)"
fi

# ─── Claude Code + OMC 自动安装 ──────────────────────────────────
# OMC (oh-my-claude) = Claude Code 的 agent/skill/hook 增强层
if $HAS_CLAUDE && ! $HAS_OMC; then
    log_step "检测到 Claude Code，正在自动安装 OMC (oh-my-claude)..."
    if command -v npm &>/dev/null; then
        npm install -g oh-my-claude 2>&1 | tail -3
        npm list -g oh-my-claude &>/dev/null && HAS_OMC=true
        if $HAS_OMC; then
            log_info "Claude Code + OMC 已就绪 — agent/skill/hook 增强可用"
        else
            log_warn "OMC 自动安装失败，请手动执行: npm install -g oh-my-claude"
        fi
    else
        log_warn "未检测到 npm，无法自动安装 OMC — 请先安装 Node.js: https://nodejs.org"
        log_warn "然后手动执行: npm install -g oh-my-claude"
    fi
elif $HAS_CLAUDE && $HAS_OMC; then
    log_info "Claude Code + oh-my-claude (OMC) 已就绪"
fi

# ─── Codex + OMX 自动安装 ────────────────────────────────────────
# Codex 原生缺少 PreToolUse/PostToolUse; OMX (oh-my-codex) 补充
if $HAS_CODEX; then
    HAS_OMX=false
    npm list -g oh-my-codex &>/dev/null 2>&1 && HAS_OMX=true

    if $HAS_OMX; then
        log_info "Codex + oh-my-codex (OMX) 已就绪 — 门禁可用"
    else
        log_step "检测到 Codex CLI，正在自动安装 OMX (oh-my-codex)..."
        npm install -g oh-my-codex 2>&1 | tail -3
        npm list -g oh-my-codex &>/dev/null 2>&1 && HAS_OMX=true
        if $HAS_OMX; then
            log_info "Codex + OMX 已就绪 — 门禁可用"
        else
            log_warn "OMX 自动安装失败，请手动执行: npm install -g oh-my-codex"
        fi
    fi
fi

# ─── Cursor 能力降级警告 ───────────────────────────────────────
if $HAS_CURSOR; then
    echo ""
    echo "   ⚠️  Cursor 仅支持 3/9 事件 (shell:before/after + file:write)"
    echo "      以下能力在 Cursor 下静默失效:"
    echo "        - SessionStart/Stop hook (知识注入、会话快照)"
    echo "        - PreToolUse:Edit hook (Read-before-Edit、范围冻结)"
    echo "        - PostToolUse hook (读写追踪、断言审计)"
    echo "        - PreCompact hook (上下文压缩保全)"
    echo "      仍生效: permission-gate、privacy-gate、context-guard"
    echo ""
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

    # 检测用户旧 AGENTS.md 是否已包含 Carror OS 内容（防重复叠加）
    # 注意：必须检查 BACKUP 中的用户旧内容，不能检查刚解压的新模板
    USER_HAD_CAROR=false
    if [ -n "$USER_CONTENT" ] && echo "$USER_CONTENT" | grep -q "Carror OS\|Harness 治理框架" 2>/dev/null; then
        USER_HAD_CAROR=true
    fi

    if [ "$USER_HAD_CAROR" = true ]; then
        # 用户已有 Carror OS → 智能替换：去掉旧 Carror OS 段，追加新版
        log_info "检测到用户 AGENTS.md 已含旧版 Carror OS，执行智能替换..."
        # 去掉旧 Carror OS 分隔线和之后的所有内容
        USER_ONLY=$(echo "$USER_CONTENT" | sed '/^## ═════════.*Carror OS\|^## Carror OS 治理框架\|^# Carror OS — AI 行为治理框架/,$ d')
        TEMPLATE=$(cat "AGENTS.md")
        DEMOTED=$(echo "$TEMPLATE" | sed 's/^# /## /g; s/^#$/##/')
        {
            echo "$USER_ONLY"
            echo ""
            echo "## ════════════════════════════════════════════"
            echo "## Carror OS 治理框架"
            echo "## ════════════════════════════════════════════"
            echo ""
            echo "$DEMOTED"
        } > AGENTS.md
        log_info "已合并 → AGENTS.md：旧 Carror OS 段已替换为新版，用户原创内容保留"
    elif [ -n "$USER_CONTENT" ]; then
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
[ "$ACTUAL" -ge "${MIN}" ] || { log_warn "文件数不足（${ACTUAL}/${MIN}）"; ERRORS=$((ERRORS+1)); }
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

# ─── LSP/AST 语言服务器检测与安装建议 ─────────────────────────
# #40: install.sh 安装时检测项目语言并提示安装对应 LSP
# 支持: pyright(python) / gopls(go) / tsserver(ts/js) / rust-analyzer(rust)
if [ "$LSP_MODE" != "skip" ]; then
	log_step "LSP 语言服务器检测..."
	LSP_STATUS=""
	LSP_INSTALL_CMD=""
	LSP_NAME=""

	_detect_pyright() {
		if command -v pyright &>/dev/null; then
			LSP_STATUS="ok"; LSP_NAME="pyright"
			log_info "pyright (Python) 已安装: $(pyright --version 2>&1 | head -1)"
		elif "$PYTHON_BIN" -c "import pyright" 2>/dev/null; then
			LSP_STATUS="ok"; LSP_NAME="pyright (pip)"
			log_info "pyright (Python) 已安装 (pip)"
		elif command -v npx &>/dev/null && npx -y pyright --version &>/dev/null 2>&1; then
			LSP_STATUS="ok"; LSP_NAME="pyright (npx)"
			log_info "pyright (Python) 可用 (npx)"
		else
			LSP_STATUS="missing"
			LSP_NAME="pyright"
			if [ -n "$PYTHON_BIN" ]; then
				LSP_INSTALL_CMD="pip install pyright"
			elif command -v npm &>/dev/null; then
				LSP_INSTALL_CMD="npm install -g pyright"
			else
				LSP_INSTALL_CMD="npm install -g pyright   # 需先安装 Node.js"
			fi
		fi
	}

	_detect_gopls() {
		if command -v gopls &>/dev/null; then
			LSP_STATUS="ok"; LSP_NAME="gopls"
			log_info "gopls (Go) 已安装: $(gopls version 2>&1 | head -1)"
		else
			LSP_STATUS="missing"
			LSP_NAME="gopls"
			LSP_INSTALL_CMD="go install golang.org/x/tools/gopls@latest"
		fi
	}

	_detect_tsserver() {
		if command -v typescript-language-server &>/dev/null; then
			LSP_STATUS="ok"; LSP_NAME="typescript-language-server"
			log_info "tsserver (TypeScript/JavaScript) 已安装"
		elif command -v tsc &>/dev/null; then
			LSP_STATUS="partial"
			LSP_NAME="tsserver"
			log_info "TypeScript 编译器已安装，建议安装 language server 获得完整诊断"
			LSP_INSTALL_CMD="npm install -g typescript-language-server typescript"
		elif command -v npm &>/dev/null && npm list -g typescript &>/dev/null 2>&1; then
			LSP_STATUS="partial"; LSP_NAME="tsserver (npm global)"
			log_info "TypeScript 全局已安装，建议追加 language server"
			LSP_INSTALL_CMD="npm install -g typescript-language-server"
		else
			LSP_STATUS="missing"
			LSP_NAME="tsserver"
			if command -v npm &>/dev/null; then
				LSP_INSTALL_CMD="npm install -g typescript-language-server typescript"
			else
				LSP_INSTALL_CMD="npm install -g typescript-language-server typescript   # 需先安装 Node.js"
			fi
		fi
	}

	_detect_rust_analyzer() {
		if command -v rust-analyzer &>/dev/null; then
			LSP_STATUS="ok"; LSP_NAME="rust-analyzer"
			log_info "rust-analyzer (Rust) 已安装: $(rust-analyzer --version 2>&1 | head -1)"
		elif rustup component list 2>/dev/null | grep -q 'rust-analyzer.*installed'; then
			LSP_STATUS="ok"; LSP_NAME="rust-analyzer (rustup)"
			log_info "rust-analyzer (Rust) 已安装 (rustup component)"
		else
			LSP_STATUS="missing"
			LSP_NAME="rust-analyzer"
			if command -v rustup &>/dev/null; then
				LSP_INSTALL_CMD="rustup component add rust-analyzer"
			else
				LSP_INSTALL_CMD="rustup component add rust-analyzer   # 需先安装 rustup: https://rustup.rs"
			fi
		fi
	}

	# 根据检测到的语言运行对应的 LSP 检测
	DETECTED_LANG="$LANG_SPEC"
	if [ -z "$DETECTED_LANG" ]; then
		if [ -f "go.mod" ]; then DETECTED_LANG="go"
		elif [ -f "package.json" ]; then DETECTED_LANG="node"
		elif ls *.py &>/dev/null 2>/dev/null || [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then DETECTED_LANG="python"
		elif [ -f "Cargo.toml" ]; then DETECTED_LANG="rust"
		fi
	fi

	case "$DETECTED_LANG" in
		python) _detect_pyright ;;
		go) _detect_gopls ;;
		node) _detect_tsserver ;;
		rust) _detect_rust_analyzer ;;
	esac

	# LSP 默认自动安装（失败不阻断安装流程 — LSP 是非必要增强资源）
	if [ "$LSP_MODE" = "install" ] && [ "$LSP_STATUS" = "missing" ] && [ -n "$LSP_INSTALL_CMD" ]; then
		log_step "LSP: 自动安装 $LSP_NAME..."
		set +e  # LSP 安装失败不阻断（保留 pipefail 以正确捕获 eval 退出码）
		if eval "$LSP_INSTALL_CMD" 2>&1 | tail -3; then
			LSP_STATUS="ok"
			log_info "$LSP_NAME 自动安装成功"
		else
			log_warn "$LSP_NAME 自动安装失败（非必要，Carror OS 核心功能不受影响）"
			log_warn "  手动安装: $LSP_INSTALL_CMD"
		fi
		set -eo pipefail
	fi

	# 存储 LSP 建议供后续 "下一步" 展示
	LSP_SUGGEST=""
	if [ "$LSP_STATUS" = "missing" ] && [ -n "$LSP_INSTALL_CMD" ]; then
		LSP_SUGGEST="  🔧 LSP ($LSP_NAME) 未安装，手动执行获得实时诊断:
      $LSP_INSTALL_CMD"
	elif [ "$LSP_STATUS" = "partial" ] && [ -n "$LSP_INSTALL_CMD" ]; then
		LSP_SUGGEST="  💡 LSP 增强 ($LSP_NAME):
      $LSP_INSTALL_CMD"
	fi

	# ─── AST 工具检测与安装 (ast-grep: 多语言通用 AST 解析) ───
	AST_STATUS=""
	AST_INSTALL_CMD=""
	AST_NAME="ast-grep"

	if command -v sg &>/dev/null; then
		AST_STATUS="ok"
		log_info "ast-grep (AST) 已安装: $(sg --version 2>&1 | head -1)"
	elif command -v ast-grep &>/dev/null; then
		AST_STATUS="ok"; AST_NAME="ast-grep"
		log_info "ast-grep (AST) 已安装"
	else
		AST_STATUS="missing"
		# 安装优先级: npm > cargo > brew > pip
		if command -v npm &>/dev/null; then
			AST_INSTALL_CMD="npm install -g @ast-grep/cli"
		elif command -v cargo &>/dev/null; then
			AST_INSTALL_CMD="cargo install ast-grep"
		elif command -v brew &>/dev/null; then
			AST_INSTALL_CMD="brew install ast-grep"
		elif [ -n "$PYTHON_BIN" ]; then
			AST_INSTALL_CMD="pip install ast-grep"
		else
			AST_INSTALL_CMD="npm install -g @ast-grep/cli   # 需先安装 Node.js"
		fi
	fi

	if [ "$AST_STATUS" = "missing" ] && [ -n "$AST_INSTALL_CMD" ]; then
		log_step "AST: 自动安装 $AST_NAME..."
		set +eo pipefail
		if eval "$AST_INSTALL_CMD" 2>&1 | tail -3; then
			AST_STATUS="ok"
			log_info "$AST_NAME 自动安装成功"
		else
			log_warn "$AST_NAME 自动安装失败（非必要，Carror OS 核心功能不受影响）"
			log_warn "  手动安装: $AST_INSTALL_CMD"
		fi
		set -eo pipefail
	fi

	AST_SUGGEST=""
	if [ "$AST_STATUS" = "missing" ] && [ -n "$AST_INSTALL_CMD" ]; then
		AST_SUGGEST="  🔧 AST ($AST_NAME) 未安装，手动执行获得结构化代码分析:
      $AST_INSTALL_CMD"
	fi
fi

# 跨平台 CLI 配置自动生成（Qwen Code / Codex / Gemini / Cursor / OpenCode）
if [ -n "${PYTHON_BIN:-}" ] && command -v "${PYTHON_BIN:-python3}" &>/dev/null && [ -f ".hooks/generate.py" ]; then
    # 保存用户自定义 sylph-hooks.ts（已从备份恢复，generate.py 会覆盖）
    # DG-105: generate.py install 在 .opencode/ 恢复之后执行，导致用户补丁丢失
    USER_SYLPH_SAVED=""
    if [ -f ".opencode/plugins/sylph-hooks.ts" ]; then
        cp ".opencode/plugins/sylph-hooks.ts" ".opencode/plugins/sylph-hooks.ts.user" 2>/dev/null
        USER_SYLPH_SAVED=".opencode/plugins/sylph-hooks.ts.user"
    fi

    # DG-124: 保存用户自定义 harness-smoke-test.sh（v6.2.39+ 支持.local扩展）
    USER_SMOKE_SAVED=""
    if [ -f ".claude/scripts/harness-smoke-test.sh" ]; then
        cp ".claude/scripts/harness-smoke-test.sh" ".claude/scripts/harness-smoke-test.sh.user" 2>/dev/null
        USER_SMOKE_SAVED=".claude/scripts/harness-smoke-test.sh.user"
    fi

    log_step "生成跨平台 CLI hooks 配置..."
    timeout 30 ${PYTHON_BIN:-python3} .hooks/generate.py install 2>/dev/null && log_info "跨平台 CLI hooks 已同步" || log_warn "跨平台 CLI hooks 生成跳过（超时或无可用平台）"

    # 恢复用户自定义 sylph-hooks.ts（DG-105）
    if [ -n "$USER_SYLPH_SAVED" ] && [ -f "$USER_SYLPH_SAVED" ]; then
        mv "$USER_SYLPH_SAVED" ".opencode/plugins/sylph-hooks.ts" 2>/dev/null
        log_info "已保留用户自定义 sylph-hooks.ts"
    fi

    # DG-124: 恢复用户自定义 harness-smoke-test.sh
    if [ -n "$USER_SMOKE_SAVED" ] && [ -f "$USER_SMOKE_SAVED" ]; then
        mv "$USER_SMOKE_SAVED" ".claude/scripts/harness-smoke-test.sh" 2>/dev/null
        log_info "已保留用户自定义 harness-smoke-test.sh"
    fi

    # ─── 后处理: 禁用跨平台生成的旧版 sylph-hooks.ts ──────────
    # carror-hooks-compat.ts 是 OMO 兼容策略的权威文件
    # sylph-hooks.ts 是旧版, 与 carror-hooks-compat 功能重叠
    if [ -f ".opencode/plugins/sylph-hooks.ts" ] && [ -f ".opencode/plugins/carror-hooks-compat.ts" ]; then
        mv ".opencode/plugins/sylph-hooks.ts" ".opencode/plugins/sylph-hooks.ts.disabled" 2>/dev/null
        log_info "旧版 sylph-hooks.ts 已禁用（.disabled），carror-hooks-compat.ts 优先"
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
    echo " - 参阅 .claude/index.md 获取完整武器库导航。"
fi
echo " 🔀 切换项目语言规范：bash .claude/profiles/merge-profile.sh <go|node|python|rust>"

# 平台特定指引
case "$PLATFORM_OS" in
    Windows-GitBash)
        echo ""
        echo " 🪟 Windows + Git Bash 用户:"
        echo "   - Claude Code: 推荐安装 WSL2 后在 WSL 内使用"
        echo "   - OpenCode: 原生 Windows 支持，直接安装 .exe 即可"
        echo "   - Codex CLI: npm install -g @openai/codex (需 Node.js 22+)"
        echo "   - 路径使用正斜杠 / 而非反斜杠 \\ (Git Bash 自动转换)"
        ;;
    macOS)
        echo ""
        echo " 🍎 macOS 用户:"
        echo "   - Claude Code: brew install claude-code 或 npm 安装"
        echo "   - OpenCode: 下载 .dmg 安装包"
        echo "   - Codex CLI: brew install --cask codex 或 npm 安装"
        echo "   - 所有 CLI 工具原生支持，体验最佳"
        ;;
    Linux)
        echo ""
        echo " 🐧 Linux 用户:"
        echo "   - Claude Code: curl 安装脚本一键安装"
        echo "   - OpenCode: .deb/.rpm 安装包"
        echo "   - Codex CLI: npm install -g @openai/codex"
        ;;
esac

# OMO/OMC 能力层状态
if $HAS_OPCODE; then
    if $HAS_OMO; then
        echo ""
        echo " ✅ OMO (oh-my-opencode) 已安装 — 安全门禁全开 (7/7)"
    else
        echo ""
        echo " ⚠️  OMO 未安装 — 安全门禁严重降级 (2/7)"
        echo "    npm install -g oh-my-opencode"
    fi
elif $HAS_CODEX; then
    echo ""
    echo " ⚠️  Codex CLI 需手动开启 hooks (config.toml: hooks=true)"
fi
if $HAS_OPCODE && ! $HAS_OMO; then
    echo " ⚡ OpenCode 用户：运行 npm install -g oh-my-opencode 解锁完整 7/7 hooks"
fi
if [ -n "$LSP_SUGGEST" ]; then
    echo ""
    echo "$LSP_SUGGEST"
fi
if [ -n "$AST_SUGGEST" ]; then
    echo ""
    echo "$AST_SUGGEST"
fi
echo "============================================"
log_info "Carror OS — AI Native Developer Operating System"
log_info "💡 运行 bash .claude/scripts/harness-smoke-test.sh 验证 hook 安装完整性"
log_info "✅ 安装完成。退出安装模式。"
exit 0
