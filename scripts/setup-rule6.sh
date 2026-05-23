#!/bin/bash
# sync rule6 changes and release
set -e
cp .claude/rules/terminal-safety.md source/harness-kit/.claude/rules/ 2>/dev/null || true
cp .claude/hooks/pretool-terminal-safety.sh source/harness-kit/.claude/hooks/
bash scripts/release.sh patch "feat: terminal-safety Rule6 — 长命令(>120字符)必须写成脚本文件,防终端换行截断" --yes
