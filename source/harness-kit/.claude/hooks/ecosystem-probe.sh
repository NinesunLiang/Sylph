#!/usr/bin/env bash
# ecosystem-probe.sh — SessionStart — 生态探针
# Role: 检测运行平台（Claude Code / OpenCode）与 OMO 安装状态，输出软建议
# 永不阻断，exit 0。SessionStart 时注入平台能力信息，AI 据此调整行为策略。
# 有 OMO 时：hook 完整运行，gate/skill/context 全功能可用
# 无 OMO 时：无 hook 环境，AI 需要更保守、更自检

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
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
    if command -v codex &>/dev/null || npm list -g @anthropic-ai/codex &>/dev/null 2>&1 || [ -f "$HOME/.codex/config.json" ] 2>/dev/null; then
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
    if python3 -c "import secrets" 2>/dev/null; then
        PYTHON3_HAS_SECRETS=true
    fi
fi
MISSING_DEPS=""
[ "$PYTHON3_OK" = false ] && MISSING_DEPS="python3 $MISSING_DEPS"
[ "$PYTHON3_HAS_SECRETS" = false ] && [ "$PYTHON3_OK" = true ] && MISSING_DEPS="python3-secrets $MISSING_DEPS"

# ── 模型上下文窗口检测 ──
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
omo:        $OMO
omc:        $OMC
codex:      $CODEX
gemini:     $GEMINI
hook_layer: $HOOK_LAYER
python3:    $PYTHON3_OK
py_secrets: $PYTHON3_HAS_SECRETS
context_limit: ${CTX_LIMIT}
missing:    ${MISSING_DEPS:-none}
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
    echo "[soft-suggest] ⚠️ python3 未安装 — 38 个 hook（127 处调用）依赖它。"
    echo "[soft-suggest] macOS: brew install python3"
    echo "[soft-suggest] Linux: apt install python3"
elif [ "$PYTHON3_HAS_SECRETS" = false ]; then
    echo "[soft-suggest] ⚠️ python3 缺 secrets 模块（Python < 3.6），权限门禁降级。"
    echo "[soft-suggest] 升级: brew upgrade python3 或 apt upgrade python3"
fi

echo '{"continue": true}'
exit 0
