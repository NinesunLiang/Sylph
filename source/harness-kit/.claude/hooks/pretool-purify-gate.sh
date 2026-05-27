#!/usr/bin/env bash
# pretool-purify-gate.sh — PreToolUse:Edit|Write — lx-purify runtime hook
# Role: 编辑治理文件时注入哲学纯度提醒到 AI 上下文 (不阻断)
source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "pretool_purify_gate" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('tool_input',{}).get('file_path',''))
except: pass
" 2>/dev/null)

# 治理文件列表
case "$FILE_PATH" in
    *.claude/*|*.opencode/*|*.cursor/*|AGENTS.md|CLAUDE.md|VERSION.json) ;;
    *) echo '{"continue": true}'; exit 0 ;;
esac

flywheel_event "pretool_purify_gate" "triggered" "P2" || true

printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[lx-purify] 编辑治理文件 %s. 哲学#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less). 确认改动不违反铁律且已通过 Oracle+Meta-Oracle 双审."}}\n' "$FILE_PATH"
exit 0
