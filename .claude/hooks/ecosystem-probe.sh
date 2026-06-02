#!/usr/bin/env bash
# ecosystem-probe.sh — SessionStart — 生态探针
# Role: 检测运行平台（Claude Code / OpenCode）与 OMO 安装状态，输出软建议
# 永不阻断，exit 0。SessionStart 时注入平台能力信息，AI 据此调整行为策略。
# 有 OMO 时：hook 完整运行，gate/skill/context 全功能可用
# 无 OMO 时：无 hook 环境，AI 需要更保守、更自检

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "ecosystem_probe" || { echo '{"continue": true}'; exit 0; }

PLATFORM="unknown"
OMO=false; OMC=false; CODEX=false; GEMINI=false
OPENCODE=false
HOOK_LAYER="none"

# ── Layer 1: 从 stdin hook_source 检测（最可靠）──
INPUT=$(cat 2>/dev/null || echo "")
HOOK_SOURCE=""
if [ -n "$INPUT" ]; then
    if command -v jq &>/dev/null; then
        HOOK_SOURCE=$(echo "$INPUT" | jq -r '.hook_source // empty' 2>/dev/null)
    else
        HOOK_SOURCE=$(echo "$INPUT" | grep -o '"hook_source"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    fi
fi

# ── OMO 家族检测函数 ──
detect_omo_family() {
    # oh-my-claudecode (omc)
    if command -v omc &>/dev/null || npm list -g oh-my-claudecode &>/dev/null 2>&1; then
        OMC=true; OMO=true; HOOK_LAYER="full"
    fi
    # oh-my-opencode (omo)
    if command -v omo &>/dev/null || npm list -g oh-my-opencode &>/dev/null 2>&1; then
        OMO=true; HOOK_LAYER="full"
    fi
    # Codex CLI
    if command -v codex &>/dev/null || npm list -g @openai/codex &>/dev/null 2>&1 || [ -f "$HOME/.codex/config.json" ] 2>/dev/null; then
        CODEX=true
    fi
    # Gemini CLI
    if command -v gemini &>/dev/null || npm list -g @google/gemini-cli &>/dev/null 2>&1; then
        GEMINI=true
    fi
}

case "$HOOK_SOURCE" in
    "opencode-plugin")
        PLATFORM="opencode"; OPENCODE=true
        detect_omo_family
        ;;
    "claude-code-hook"|"claude_code_hook")
        PLATFORM="claude-code"
        HOOK_LAYER="full"
        command -v opencode &>/dev/null && OPENCODE=true
        detect_omo_family
        ;;
    *)
        # Layer 2: 环境检测（独立调用时）
        if command -v opencode &>/dev/null; then
            OPENCODE=true; PLATFORM="opencode"
            detect_omo_family
            [ "$OMO" = false ] && HOOK_LAYER="partial"
        fi
        if [ -d "$HOME/.claude/projects" ] 2>/dev/null; then
            PLATFORM="claude-code"
            HOOK_LAYER="full"
            detect_omo_family
        fi
        ;;
esac

# ── 运行时依赖检测 ──
PYTHON3_OK=false; PYTHON3_HAS_SECRETS=false
if command -v python3 &>/dev/null; then
    PYTHON3_OK=true
    if ${PYTHON_BIN:-python3} -c "import secrets" 2>/dev/null; then
        PYTHON3_HAS_SECRETS=true
    fi
fi
MISSING_DEPS=""
[ "$PYTHON3_OK" = false ] && MISSING_DEPS="${PYTHON_BIN:-python3} $MISSING_DEPS"
[ "$PYTHON3_HAS_SECRETS" = false ] && [ "$PYTHON3_OK" = true ] && MISSING_DEPS="${PYTHON_BIN:-python3}-secrets $MISSING_DEPS"

# ── LSP 服务器探测 ──
LSP_PYRIGHT=false; LSP_TSSERVER=false; LSP_GO=false; LSP_RUST=false
LSP_SERENA=false; LSP_TOTAL=0
command -v pyright &>/dev/null || pip show pyright &>/dev/null 2>&1 && { LSP_PYRIGHT=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
command -v pyright-langserver &>/dev/null && { LSP_PYRIGHT=true; }
command -v typescript-language-server &>/dev/null && { LSP_TSSERVER=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
command -v gopls &>/dev/null && { LSP_GO=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
command -v rust-analyzer &>/dev/null && { LSP_RUST=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
command -v serena &>/dev/null || pip show serena-agent &>/dev/null 2>&1 && { LSP_SERENA=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
# uvx 检查加超时和缓存——避免每次 SessionStart 触发下载
SERENA_CACHE="$PROJECT_ROOT/.omc/state/.serena-checked"
if [ "$LSP_SERENA" = false ] && command -v uvx &>/dev/null; then
    CACHE_MTIME=$({ stat -c "%Y" "$SERENA_CACHE" 2>/dev/null || stat -f "%m" "$SERENA_CACHE" 2>/dev/null || python3 -c "import os; print(int(os.path.getmtime('$SERENA_CACHE')))" 2>/dev/null || echo "0"; })
    if [ -f "$SERENA_CACHE" ] && [ $(($(date +%s) - CACHE_MTIME)) -lt 86400 ]; then
        LSP_SERENA=$(cat "$SERENA_CACHE")
    else
        timeout 5 uvx --from serena-agent serena --help &>/dev/null 2>&1 && { LSP_SERENA=true; LSP_TOTAL=$((LSP_TOTAL+1)); }
        echo "$LSP_SERENA" > "$SERENA_CACHE" 2>/dev/null
    fi
fi

# ── LSP 能力等级 ──
LSP_LEVEL="none"
if [ "$PLATFORM" = "opencode" ] && [ "$OPENCODE" = true ]; then
    LSP_LEVEL="full"  # OpenCode 40+ 内置 LSP
elif [ "$PLATFORM" = "claude-code" ]; then
    [ "$LSP_TOTAL" -ge 1 ] && LSP_LEVEL="partial" || LSP_LEVEL="none"
elif [ "$CODEX" = true ]; then
    [ "$LSP_SERENA" = true ] && LSP_LEVEL="bridge" || LSP_LEVEL="none"
fi
CTX_LIMIT_FILE="$PROJECT_ROOT/.omc/state/model-context-limit"
if [ -f "$CTX_LIMIT_FILE" ]; then
    CTX_LIMIT=$(cat "$CTX_LIMIT_FILE" 2>/dev/null)
    CTX_LIMIT="${CTX_LIMIT:-unset}"
else
    CTX_LIMIT="unset"
fi

# ── 输出探针信息（AI 可见）──
cat <<PROBE

<ecosystem-probe>
platform:   $PLATFORM
opencode:   $OPENCODE
omo:        $OMO
omc:        $OMC
codex:      $CODEX
gemini:     $GEMINI
hook_layer: $HOOK_LAYER
${PYTHON_BIN:-python3}:    $PYTHON3_OK
py_secrets: $PYTHON3_HAS_SECRETS
context_limit: ${CTX_LIMIT}
missing:    ${MISSING_DEPS:-none}
lsp_level:  $LSP_LEVEL
lsp_pyright: $LSP_PYRIGHT
lsp_typescript: $LSP_TSSERVER
lsp_go:     $LSP_GO
lsp_rust:   $LSP_RUST
lsp_serena: $LSP_SERENA
lsp_servers: $LSP_TOTAL
</ecosystem-probe>
PROBE

# ── 软建议 ──
if [ "$PLATFORM" = "opencode" ] && [ "$OMO" = false ]; then
    echo "[soft-suggest] OpenCode 已安装但未安装 OMO (oh-my-openagent)。"
    echo "[soft-suggest] Carror OS 的 hook 门禁/技能/skill 依赖 OMO 兼容层。无 OMO 时仅基础功能可用。"
    echo "[soft-suggest] 安装: npx oh-my-opencode install --no-tui --claude no --openai no --gemini no --skip-auth"
fi
if [ "$PLATFORM" = "claude-code" ] && [ "$OMC" = false ]; then
    echo "[soft-suggest] Claude Code 平台建议安装 OMC (oh-my-claudecode) 获得完整 hook 门禁。"
    echo "[soft-suggest] 安装: npx oh-my-claudecode install"
fi
if [ "$PYTHON3_OK" = false ]; then
    echo "[soft-suggest] ⚠️ ${PYTHON_BIN:-python3} 未安装 — 38 个 hook（127 处调用）依赖它。"
    echo "[soft-suggest] macOS: brew install python3"
    echo "[soft-suggest] Linux: apt install python3"
elif [ "$PYTHON3_HAS_SECRETS" = false ]; then
    echo "[soft-suggest] ⚠️ ${PYTHON_BIN:-python3} 缺 secrets 模块（Python < 3.6），权限门禁降级。"
    echo "[soft-suggest] 升级: brew upgrade ${PYTHON_BIN:-python3} 或 apt upgrade python3"
fi

# ── LSP 安装建议（按平台差异化）──
if [ "$LSP_LEVEL" = "none" ] && [ "$PLATFORM" != "unknown" ]; then
    echo ""
    echo "[lsp-suggest] 🔍 LSP 语义引擎未配置 — AI 将只能用 grep 理解代码（低效且容易出错）"
    echo "[lsp-suggest] LSP 可让 AI 获得 IDE 级别的代码理解：跳转定义、查找引用、实时诊断"
    echo "[lsp-suggest] 安装指南: Read docs/guides/cn/lsp-setup.md"
fi
if [ "$PLATFORM" = "claude-code" ] && [ "$LSP_LEVEL" = "none" ]; then
    echo "[lsp-suggest] Claude Code: /plugin install pyright-lsp@claude-plugins-official"
    echo "[lsp-suggest] 前置依赖: pip install pyright"
elif [ "$PLATFORM" = "claude-code" ] && [ "$LSP_LEVEL" = "partial" ]; then
    echo "[lsp-suggest] LSP 部分就绪 ($LSP_TOTAL 服务器)，建议安装更多语言服务器以覆盖本项目"
fi
if [ "$CODEX" = true ] && [ "$LSP_SERENA" = false ]; then
    echo "[lsp-suggest] Codex CLI 无原生 LSP，建议通过 Serena MCP 桥接"
    echo "[lsp-suggest] 安装: pip install serena-agent && serena start --context codex"
    echo "[lsp-suggest] 然后在 ~/.codex/config.toml 中配置 MCP 服务器"
fi
if [ "$PLATFORM" = "opencode" ]; then
    echo "[lsp-suggest] OpenCode LSP 已内置 (40+ 服务器)，设置 lsp:true 即可启用"
    if ! grep -q '"lsp".*true' "$PROJECT_ROOT/.opencode.json" 2>/dev/null && ! grep -q '"lsp".*true' "$HOME/.opencode.json" 2>/dev/null; then
        echo "[lsp-suggest] ⚠️ 当前项目未启用 LSP — 在 .opencode.json 中设置 \"lsp\": true"
    fi
fi

echo '{"continue": true}'
flywheel_event "ecosystem_probe" "probe_complete" "P2" "${PLATFORM:-detected}"
exit 0
