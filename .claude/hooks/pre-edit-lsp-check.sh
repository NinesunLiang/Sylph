#!/usr/bin/env bash
# pre-edit-lsp-check.sh — PreToolUse:Edit — 编辑前诊断检查提醒
# Role: 编辑代码文件前提醒 AI 检查当前文件诊断错误
# 哲学 #3 (先守护): 改代码前先确认不会引入新错误
# 哲学 #6 (0信任): 不信任 AI 的"应该没问题"，诊断数据是客观事实
# 哲学 #1 (less is more): 零外部依赖，提醒即机制，不强制
# 永不阻断 (exit 0) — 仅提醒。改为阻断需 harness lsp_gate.block: true

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

# 只对代码文件提醒
EXT="${FILE_PATH##*.}"
case "$EXT" in
    py|pyi|ts|tsx|js|jsx|go|rs) ;;
    *) echo '{"continue": true}'; exit 0 ;;
esac

# 跨平台诊断工具名（hook 不调用，仅提醒 AI 使用其平台可用工具）
# Claude Code: mcp__ide__getDiagnostics
# OpenCode:    内置 LSP (lsp_diagnostics)
# Codex:       Serena MCP (serena_diagnostics)
echo "[lsp-gate] 🔍 编辑前诊断: $FILE_PATH ($EXT)" >&2
echo "[lsp-gate] 请先用你平台可用的诊断工具检查此文件错误，确认无误后再编辑" >&2

flywheel_event "pre_edit_lsp" "diagnostics_reminder" "L2" "ext=$EXT" || true
echo '{"continue": true}'
exit 0
