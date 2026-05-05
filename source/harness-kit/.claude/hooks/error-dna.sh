#!/usr/bin/env bash

TOOL_NAME="$1"

if [ "$TOOL_NAME" != "
bash" ]; then exit 0; fi


EXIT_CODE=$(jq -r '.exitCode // 0' < /dev/stdin 2>/dev/null)
if [ "$EXIT_CODE" -ne 0 ]; then mkdir -p .omc/state echo "{\"
ts\":$(date +%s),\"
error_code\":$EXIT_CODE}" >> "$DNA_FILE"
fi
exit 0
