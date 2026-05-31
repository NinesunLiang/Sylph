#!/usr/bin/env bash
# lsp-gate.sh — SessionStart — 检测项目语言对应的 LSP 是否可用
# 哲学 #3 (先守护后激发): 确保基础设施就绪再开始工作
# 基于 ecosystem_probe.sh 已有的 LSP 检测逻辑

source "$(dirname "$0")/harness_config.sh"
hc_enabled "lsp_gate" || { echo '{"continue": true}'; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 检测项目语言（通过文件存在性）
HAS_GO=false; HAS_PY=false; HAS_TS=false; HAS_RS=false
[ -f "$PROJECT_ROOT/go.mod" ] || ls "$PROJECT_ROOT"/*.go >/dev/null 2>&1 && HAS_GO=true
[ -f "$PROJECT_ROOT/requirements.txt" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ] || ls "$PROJECT_ROOT"/*.py >/dev/null 2>&1 && HAS_PY=true
[ -f "$PROJECT_ROOT/package.json" ] && grep -q '"typescript"' "$PROJECT_ROOT/package.json" 2>/dev/null && HAS_TS=true
[ -f "$PROJECT_ROOT/Cargo.toml" ] && HAS_RS=true

# 检测 LSP 可用性
MISSING=""
if $HAS_GO && ! command -v gopls &>/dev/null; then MISSING="$MISSING gopls (Go)"; fi
if $HAS_PY && ! command -v pyright &>/dev/null && ! pip show pyright &>/dev/null 2>&1; then MISSING="$MISSING pyright (Python)"; fi
if $HAS_TS && ! command -v typescript-language-server &>/dev/null; then MISSING="$MISSING typescript-language-server (TS)"; fi
if $HAS_RS && ! command -v rust-analyzer &>/dev/null; then MISSING="$MISSING rust-analyzer (Rust)"; fi

if [ -n "$MISSING" ]; then
    printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[lsp-gate] 项目语言缺少LSP: %s。Run: brew install gopls pyright typescript-language-server rust-analyzer"}}\n' "$MISSING"
else
    echo '{"continue": true}'
fi
exit 0
