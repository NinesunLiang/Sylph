#!/usr/bin/env bash
# 安装 CarrorOS Git 硬闸到当前仓库的 .git/hooks。
# --check 只校验是否已安装且内容一致，不写文件。
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ]; then
  echo "ERROR: not inside a git repository; git hooks not installed" >&2
  exit 1
fi
SRC="$ROOT/.claude/scripts/git-hooks"
DST="$(git rev-parse --git-path hooks)"
case "$DST" in /*) ;; *) DST="$ROOT/$DST" ;; esac
mkdir -p "$DST"

mode="${1:-install}"
problems=0
for name in pre-commit pre-push; do
  src="$SRC/$name"
  dst="$DST/$name"
  if [ ! -f "$src" ]; then
    echo "ERROR: missing hook source: $src" >&2
    exit 1
  fi
  if [ "$mode" = "--check" ]; then
    if [ ! -x "$dst" ]; then
      echo "MISSING: $dst not installed" >&2
      problems=$((problems + 1))
    elif ! cmp -s "$src" "$dst"; then
      echo "STALE: $dst differs from $src" >&2
      problems=$((problems + 1))
    else
      echo "OK: $name installed"
    fi
    continue
  fi
  if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
    backup="$dst.bak.$(date +%Y%m%d%H%M%S)"
    cp -p "$dst" "$backup"
    echo "INFO: backed up existing $name -> $backup"
  fi
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "OK: installed $name"
done
if [ "$mode" = "--check" ] && [ "$problems" -gt 0 ]; then
  exit 1
fi
