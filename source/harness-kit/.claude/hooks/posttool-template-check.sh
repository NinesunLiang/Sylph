#!/usr/bin/env bash
source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "posttool_template_check" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)
FP=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[[ "$FP" == *.claude/task_sys/templates/* ]] || { echo '{"continue": true}'; exit 0; }
flywheel_event "posttool_template_check" "checked" "P2" || true
printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"[task_sys] Template written: %s. Required fields: goal, acceptance_criteria, steps, verification. See .claude/task_sys/unified_delivery_schema.md"}}\n' "$FP"
exit 0
