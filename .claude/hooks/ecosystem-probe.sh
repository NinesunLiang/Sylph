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
OMO=false
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

case "$HOOK_SOURCE" in
    "opencode-plugin")
        PLATFORM="opencode"
        OMO=true; OPENCODE=true
        HOOK_LAYER="full"
        ;;
    "claude-code-hook"|"claude_code_hook")
        PLATFORM="claude-code"
        HOOK_LAYER="full"
        command -v opencode &>/dev/null && OPENCODE=true
        command -v omo &>/dev/null || npm list -g oh-my-opencode &>/dev/null 2>&1 && OMO=true
        ;;
    *)
        # Layer 2: 环境检测（独立调用时）
        if command -v opencode &>/dev/null; then
            OPENCODE=true; PLATFORM="opencode"
            if command -v omo &>/dev/null || npm list -g oh-my-opencode &>/dev/null 2>&1; then
                OMO=true; HOOK_LAYER="full"
            else
                HOOK_LAYER="partial"
            fi
        fi
        # Claude Code 检测
        if [ -d "$HOME/.claude/projects" ] 2>/dev/null; then
            PLATFORM="claude-code"
            HOOK_LAYER="full"
        fi
        ;;
esac

# ── 输出探针信息（AI 可见）──
cat <<PROBE

<ecosystem-probe>
platform:   $PLATFORM
omo:        $OMO
opencode:   $OPENCODE
hook_layer: $HOOK_LAYER
</ecosystem-probe>
PROBE

# ── 软建议 ──
if [ "$PLATFORM" = "opencode" ] && [ "$OMO" = false ]; then
    echo "[soft-suggest] OpenCode 已安装但未安装 OMO (oh-my-openagent)。"
    echo "[soft-suggest] Carror OS 的 hook 门禁/技能/skill 依赖 OMO 兼容层。无 OMO 时仅基础功能可用。"
    echo "[soft-suggest] 安装: npx oh-my-opencode install --no-tui --claude no --openai no --gemini no --skip-auth"
fi

echo '{"continue": true}'
exit 0
