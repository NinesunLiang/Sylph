#!/usr/bin/env bash
# Wrapper: 调用 Hermes 门禁脚本
INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")
bash "$HOME/.hermes/scripts/hermes-error-dna.sh" "$CMD" 2>&1
exit $?
