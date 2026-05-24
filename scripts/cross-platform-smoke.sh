#!/usr/bin/env bash
# cross-platform-smoke.sh — 跨平台/跨IDE 兼容性冒烟测试
# #37: 验证所有 hook/脚本在当前平台可执行
set -f

# Cross-platform Python resolution (DG-105)
[ -f ".claude/hooks/harness_config.sh" ] && source ".claude/hooks/harness_config.sh" 2>/dev/null || true

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

ok() { echo -e "  ${GREEN}✅${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}❌${NC} $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; WARN=$((WARN+1)); }

echo "============================================"
echo " Carror OS 跨平台兼容性冒烟测试"
echo " Platform: $(uname -s) | $(uname -m)"
echo " Shell: $SHELL | $(bash --version | head -1)"
echo "============================================"
echo ""

# ─── 基础运行时 ──────────────────────────────────────────
echo "=== 基础运行时 ==="
command -v bash &>/dev/null && ok "bash" || fail "bash — required"
command -v "${PYTHON_BIN:-python3}" &>/dev/null && ok "python3 ($(${PYTHON_BIN:-python3} --version 2>&1))" || fail "python3 — required"
command -v jq &>/dev/null && ok "jq" || warn "jq — optional, python3 fallback works"

# ─── 平台检测 ─────────────────────────────────────────────
echo ""
echo "=== 平台检测 ==="
case "$(uname -s)" in
    Darwin)  PLATFORM="macOS"; ok "macOS detected" ;;
    Linux)   PLATFORM="Linux"; ok "Linux detected" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="Windows"; ok "Windows (Git Bash/MSYS2)" ;;
    *)       PLATFORM="Unknown"; warn "Unknown platform: $(uname -s)" ;;
esac

# macOS specifics
if [ "$PLATFORM" = "macOS" ]; then
    # sed -i compatibility
    _CROSS_SED_TEST="$(mktemp "${TMPDIR:-/tmp}/_cross_sed_test.XXXXXX")"
echo "test" > "$_CROSS_SED_TEST"
    sed -i '' 's/test/ok/' "$_CROSS_SED_TEST" 2>/dev/null && ok "sed -i '' (BSD)" || warn "sed -i '' failed"
    rm -f "$_CROSS_SED_TEST" "$_CROSS_SED_TEST.bak"

    # COPYFILE_DISABLE for tar
    [ -n "${COPYFILE_DISABLE:-}" ] && ok "COPYFILE_DISABLE set" || warn "COPYFILE_DISABLE not set (tar may leak ._* files)"
fi

# Windows specifics
if [ "$PLATFORM" = "Windows" ]; then
    command -v winget &>/dev/null && ok "winget" || warn "winget — recommended for python3"
    command -v choco &>/dev/null && ok "choco" || warn "choco — alternative package manager"
fi

# ─── IDE/CLI 检测 ──────────────────────────────────────────
echo ""
echo "=== IDE/CLI 检测 ==="
command -v codex &>/dev/null && ok "Codex CLI" || warn "Codex CLI — not installed"
[ -d ".opencode" ] && ok "OpenCode config (.opencode/)" || warn "OpenCode config — not present"
[ -f ".cursor/hooks.json" ] || [ -d ".cursor" ] && ok "Cursor config" || true
command -v code &>/dev/null && ok "VS Code CLI" || true

# ─── Hook 语法检查 ────────────────────────────────────────
echo ""
echo "=== Hook 语法检查 ==="
HOOK_DIR=".claude/hooks"
if [ -d "$HOOK_DIR" ]; then
    set +f  # enable glob for hook enumeration
    for hook in "$HOOK_DIR"/*.sh; do
        set -f
        name=$(basename "$hook")
        if bash -n "$hook" 2>/dev/null; then
            ok "$name"
        else
            fail "$name — syntax error"
        fi
    done
else
    fail "Hook directory not found: $HOOK_DIR"
fi

# ─── 关键脚本语法检查 ─────────────────────────────────────
echo ""
echo "=== 关键脚本语法 ==="
for script in \
    .claude/skills/lx-goal/scripts/lx-goal.sh \
    .claude/skills/lx-ghost/scripts/lx-ghost.sh \
    scripts/release.sh \
    source/harness-kit/install.sh; do
    if [ -f "$script" ]; then
        bash -n "$script" 2>/dev/null && ok "$(basename $script)" || fail "$script — syntax error"
    else
        warn "$script — not found"
    fi
done

# ─── Python 模块检查 ───────────────────────────────────────
echo ""
echo "=== Python 模块 ==="
for mod in json os sys datetime; do
    ${PYTHON_BIN:-python3} -c "import $mod" 2>/dev/null && ok "$mod" || fail "$mod — missing (critical)"
done
${PYTHON_BIN:-python3} -c "import secrets" 2>/dev/null && ok "secrets" || warn "secrets — permission-gate fallback"

# ─── Git 环境 ──────────────────────────────────────────────
echo ""
echo "=== Git 环境 ==="
command -v git &>/dev/null && ok "git ($(git --version 2>&1 | head -1))" || warn "git — not found"
[ -d ".git" ] && ok ".git directory" || warn "Not in git repo"

# ─── 信号文件 ─────────────────────────────────────────────
echo ""
echo "=== 信号文件 ==="
for f in .omc/state/lx-goal.json .omc/state/lx-ghost.json .omc/state/autonomous.active; do
    if [ -f "$f" ]; then
        warn "$f exists — mode may be active"
    fi
done

# ─── 结果 ──────────────────────────────────────────────────
echo ""
echo "============================================"
echo " 结果: ${GREEN}${PASS} PASS${NC} / ${RED}${FAIL} FAIL${NC} / ${YELLOW}${WARN} WARN${NC}"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo "❌ 发现 ${FAIL} 个失败项，需修复"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "⚠️  ${WARN} 个警告 (非阻塞，功能降级)"
    exit 0
else
    echo "✅ 全部通过"
    exit 0
fi
