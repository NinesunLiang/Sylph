#!/usr/bin/env bash
# build-pkg-b-source-zip.sh — 按 gpt-5.6Sol round1 首选方案生成源码压缩包
# 范围:git 追踪文件,排除运行产物(audit/artifacts/state/tokens/prompt-ring)、
#       benchmark/repos、__pycache__;.claude/settings.json 以脱敏版纳入。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

STAGE=$(mktemp -d /tmp/carroros-src-XXXXXX)
trap 'rm -rf "$STAGE"' EXIT

git ls-files -z -- \
  ':(exclude).claude/settings.json' \
  ':(exclude).claude/.prompt-ring*.json' \
  ':(exclude).omc/audit' \
  ':(exclude).omc/artifacts' \
  ':(exclude).omc/state' \
  ':(exclude).omc/tokens' \
  ':(exclude)state' \
  ':(exclude)benchmark/repos' \
  ':(exclude)**/__pycache__' \
  > "$STAGE/manifest"

while IFS= read -r -d '' f; do
  if [[ -f "$f" ]]; then
    mkdir -p "$STAGE/src/$(dirname "$f")"
    cp "$f" "$STAGE/src/$f"
  else
    printf '%s\n' "$f" >> "$STAGE/skipped.txt"
  fi
done < "$STAGE/manifest"

sed -E 's/sk-[A-Za-z0-9]{16,}/<REDACTED>/g' .claude/settings.json > "$STAGE/src/.claude/settings.json"

{
cat << EOF
CarrorOS source snapshot for PKG-B review
baseline: $(git rev-parse HEAD) + 工作区未提交改动(快照=工作树)
created:  2026-07-19
scope:    git tracked files MINUS runtime artifacts MINUS 工作区已删除文件
excluded: .claude/.prompt-ring*.json, .omc/audit, .omc/artifacts, .omc/state,
          .omc/tokens, state/, benchmark/repos, __pycache__
redacted: .claude/settings.json (API token -> <REDACTED>)
EOF
if [[ -f "$STAGE/skipped.txt" ]]; then
  echo "deleted-in-worktree (not included):"
  cat "$STAGE/skipped.txt"
fi
} > "$STAGE/src/PACKAGE-NOTE.txt"

OUT=carroros-src-pkg-b.zip
rm -f "$OUT"
( cd "$STAGE/src" && zip -q -r "$OLDPWD/$OUT" . )

echo "== 校验 =="
ls -la "$OUT"
unzip -l "$OUT" | tail -3
echo "-- 脱敏检查(应为 0) --"
unzip -p "$OUT" .claude/settings.json | grep -c "sk-Xrwon" || true
echo "-- REDACTED 在位(应为 1) --"
unzip -p "$OUT" .claude/settings.json | grep -c "<REDACTED>" || true
