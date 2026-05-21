#!/usr/bin/env bash
# pre-edit-lsp-check.sh — PreToolUse:Edit — 编辑前检查 LSP diagnostics
# Role: 确保 AI 修改代码前已检查 LSP 诊断结果。有错误时提醒 AI 先修复。
# 哲学 #3 (先守护后激发): 改代码前先确认不会引入新错误
# 哲学 #6 (0信任): LSP diagnostics 是客观事实，不信任 AI 的"应该没问题"
# 永不阻断 (exit 0) — 仅提醒，不强制。改为阻断需 harness lsp_gate: true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
hc_enabled "lsp_gate" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat 2>/dev/null || echo "")
FILE_PATH=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
fi

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

# 检测 LSP 可用性
LSP_AVAILABLE=false
command -v pyright &>/dev/null && LSP_AVAILABLE=true
command -v pyright-langserver &>/dev/null && LSP_AVAILABLE=true
command -v typescript-language-server &>/dev/null && LSP_AVAILABLE=true
command -v gopls &>/dev/null && LSP_AVAILABLE=true
command -v rust-analyzer &>/dev/null && LSP_AVAILABLE=true

# OpenCode 内置 LSP
if grep -q '"lsp".*true' "$PROJECT_ROOT/.opencode.json" 2>/dev/null; then
    LSP_AVAILABLE=true
fi

if [ "$LSP_AVAILABLE" = false ]; then
    echo "[lsp-gate] ⚠️ LSP 未配置 — 无法进行编辑前诊断检查" >&2
    echo "[lsp-gate] 安装指南: Read docs/guides/cn/lsp-setup.md" >&2
    echo '{"continue": true}'
    exit 0
fi

# 检查文件扩展名
EXT="${FILE_PATH##*.}"
LANG=""
case "$EXT" in
    py|pyi) LANG="python" ;;
    ts|tsx|js|jsx) LANG="typescript" ;;
    go) LANG="go" ;;
    rs) LANG="rust" ;;
    *) echo '{"continue": true}'; exit 0 ;;
esac

echo "[lsp-gate] 🔍 编辑前 LSP 检查: $FILE_PATH ($LANG)" >&2
echo "[lsp-gate] 提示: 请先用 LSP tools 检查 diagnostics，确认无错误后再编辑" >&2
echo "[lsp-gate] Claude Code: 使用 LSP 工具的 getDiagnostics" >&2
echo "[lsp-gate] OpenCode: 使用 lsp_diagnostics" >&2

echo '{"continue": true}'
exit 0
