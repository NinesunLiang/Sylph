#!/usr/bin/env bash
# pre-edit-lsp-check.sh — PreToolUse:Edit — 编辑前强制诊断检查 (v2)
# Role: 编辑代码文件前主动获取诊断结果，注入 AI 上下文
# 哲学 #3 (先守护): 改代码前先拿到错误清单
# 哲学 #6 (0信任): 诊断数据是客观事实，不信任 AI 的"应该没问题"
# 永不阻断 (exit 0) — 诊断注入不阻断编辑

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

EXT="${FILE_PATH##*.}"
FULL_PATH="$PROJECT_ROOT/$FILE_PATH"
[ -f "$FULL_PATH" ] || FULL_PATH="$FILE_PATH"
DIAG_OUTPUT=""

case "$EXT" in
    py|pyi)
        # Python: try pyright > py_compile > flake8 > pylint
        if command -v pyright &>/dev/null; then
            DIAG_OUTPUT=$(pyright "$FULL_PATH" --outputjson 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    errs=d.get('generalDiagnostics',[])
    if errs:
        for e in errs[:5]:
            print(f\"  L{e.get('severity','?')} line {e.get('range',{}).get('start',{}).get('line','?')}: {e.get('message','')[:100]}\")
    else:
        print('  ✅ pyright: no errors')
except: print('  (pyright parse failed)')
" 2>/dev/null)
        elif command -v python3 &>/dev/null; then
            DIAG_OUTPUT=$(python3 -m py_compile "$FULL_PATH" 2>&1 && echo "  ✅ py_compile: syntax OK" || echo "  ❌ compile failed")
        fi
        ;;
    ts|tsx|js|jsx)
        if command -v tsc &>/dev/null; then
            DIAG_OUTPUT=$(tsc --noEmit --pretty false "$FULL_PATH" 2>&1 | head -5)
        elif command -v node &>/dev/null; then
            DIAG_OUTPUT=$(node --check "$FULL_PATH" 2>&1 && echo "  ✅ node --check: syntax OK" || echo "  ❌ syntax error")
        fi
        ;;
    go)
        if command -v go &>/dev/null; then
            DIAG_OUTPUT=$(go vet "$FULL_PATH" 2>&1 | head -5)
            [ -z "$DIAG_OUTPUT" ] && DIAG_OUTPUT="  ✅ go vet: no issues"
        fi
        ;;
    rs)
        if command -v rustc &>/dev/null; then
            DIAG_OUTPUT=$(rustc --edition 2021 --parse-only "$FULL_PATH" 2>&1 | head -5)
        fi
        ;;
    sh|bash)
        DIAG_OUTPUT=$(bash -n "$FULL_PATH" 2>&1 && echo "  ✅ bash -n: syntax OK" || echo "  ❌ bash syntax error")
        ;;
    *) echo '{"continue": true}'; exit 0 ;;
esac

# Build additionalContext with actual diagnostics
if [ -n "$DIAG_OUTPUT" ]; then
    CTX="[lsp-gate] 编辑前诊断: $FILE_PATH
${DIAG_OUTPUT}"
    echo "$CTX" >&2
    flywheel_event "pre_edit_lsp" "diagnostics_checked" "L2" "ext=$EXT" || true
else
    echo "[lsp-gate] 🔍 编辑 $FILE_PATH — 无本地诊断工具，请用 IDE getDiagnostics" >&2
    flywheel_event "pre_edit_lsp" "diagnostics_reminder" "L2" "ext=$EXT" || true
fi

# Inject diagnostics into AI context via additionalContext
python3 -c "
import json, sys
ctx = sys.stdin.read()
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': ctx}}))
" <<< "[lsp-gate] 编辑前诊断: $FILE_PATH
${DIAG_OUTPUT:-⚠️ 无本地LSP服务器，请用平台 getDiagnostics 工具检查}"

exit 0
