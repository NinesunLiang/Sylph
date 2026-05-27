#!/usr/bin/env bash
source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "pretool_node_reference" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)
TOOL=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
[ "$TOOL" = "Agent" ] || { echo '{"continue": true}'; exit 0; }
NODES_DIR="$(cd "$(dirname "$0")/.." && pwd)/nodes"
NODE_LIST=$(ls "$NODES_DIR"/*.md 2>/dev/null | xargs -n1 basename | sed 's/\.md$//' | tr '\n' ' ')
flywheel_event "pretool_node_reference" "injected" "P2" || true
printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[nodes] Available: %s"}}\n' "$NODE_LIST"
exit 0
