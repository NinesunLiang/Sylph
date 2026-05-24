#!/bin/bash
# setup-client-fallback.sh — 客户反馈吸收 (双法官修订后方案)
set -e
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
# Cross-platform Python resolution (DG-105)
[ -f "$PROJECT/.claude/hooks/harness_config.sh" ] && source "$PROJECT/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 1. COPYFILE_DISABLE=1 源头阻断 Apple Double
${PYTHON_BIN:-python3} -c "
path = '$PROJECT/scripts/package-release.sh'
with open(path) as f: content = f.read()
# Add COPYFILE_DISABLE before tar commands (line 219 and 231)
content = content.replace(
    'tar czf \"\$PKG_DIR/harness-kit-\${TAG}.tar.gz\"',
    'COPYFILE_DISABLE=1 tar czf \"\$PKG_DIR/harness-kit-\${TAG}.tar.gz\"')
content = content.replace(
    'tar czf \"\$PKG_DIR/lx-skills-\${TAG}.tar.gz\"',
    'COPYFILE_DISABLE=1 tar czf \"\$PKG_DIR/lx-skills-\${TAG}.tar.gz\"')
with open(path, 'w') as f: f.write(content)
print('package-release.sh: COPYFILE_DISABLE=1 added')
"

# 2. .gitignore 加 ._*
GITIGNORE="$PROJECT/.gitignore"
if ! grep -q '^\._\*' "$GITIGNORE" 2>/dev/null; then
    echo '._*' >> "$GITIGNORE"
    echo ".gitignore: ._* added"
fi

# 3. session-guardian.ts 覆盖 root + source (3 fixes from client)
CLIENT_TS="$PROJECT/client_fellback/session-guardian.ts"
ROOT_TS="$PROJECT/.opencode/plugins/session-guardian.ts"
SRC_TS="$PROJECT/source/harness-kit/.opencode/plugins/session-guardian.ts"

if [ -f "$CLIENT_TS" ]; then
    cp "$CLIENT_TS" "$ROOT_TS" && echo "root session-guardian.ts updated"
    [ -f "$SRC_TS" ] && cp "$CLIENT_TS" "$SRC_TS" && echo "source session-guardian.ts updated"
fi

# 4. 清理旧 setup 脚本
rm -f "$PROJECT/scripts/setup-apple-double-fix.sh" 2>/dev/null || true

echo "=== Done ==="
echo "Run: bash scripts/release.sh patch 'fix: DG-107 Apple Double源头阻断 + DG-108 session-guardian 3fix回传 + gitignore' --yes"
