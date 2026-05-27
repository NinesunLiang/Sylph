#!/usr/bin/env bash
for h in pretool-terminal-safety pretool-skill-version-guard pretool-blast-radius; do
  cp ".claude/hooks/${h}.sh" "source/harness-kit/.claude/hooks/"
done
rm -f scripts/sync-gate-pattern.sh
echo "synced"
