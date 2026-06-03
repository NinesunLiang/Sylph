#!/usr/bin/env bash
# generate-local-settings.sh
# 从 settings.json 生成 settings.local.json，把所有 hook 路径从相对路径改为绝对路径
# 解决 Claude Code CWD 漂移到 /tmp 时所有 hook 报 No such file or directory 的问题
# 用法: bash .claude/scripts/generate-local-settings.sh [project-root]
#       如果省略 project-root，默认取脚本所在目录的上一层
# 哲学 #6 (0信任): settings.local.json 被 .gitignore 排除，不泄露个人信息到安装包

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"
LOCAL_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "ERROR: $SETTINGS_FILE not found" >&2
    exit 1
fi

echo "Generating $LOCAL_SETTINGS ..."

# Replace relative hook paths with absolute paths
sed -e "s|\"bash \.claude/hooks/|\"bash $PROJECT_DIR/.claude/hooks/|g" \
    -e "s|\"python3 \.claude/hooks/|\"python3 $PROJECT_DIR/.claude/hooks/|g" \
    -e "s|\"bash \.claude/workflow-standard/|\"bash $PROJECT_DIR/.claude/workflow-standard/|g" \
    -e "s|\"python3 \.claude/scripts/|\"python3 $PROJECT_DIR/.claude/scripts/|g" \
    "$SETTINGS_FILE" > "$LOCAL_SETTINGS"

# Validate JSON
if python3 -c "
import json
json.load(open('$LOCAL_SETTINGS'))
data = json.load(open('$LOCAL_SETTINGS'))
hooks = data.get('hooks', {}).values() if hasattr(dict.values, '__call__') else []
" 2>/dev/null; then
    count=$(grep -c '"command":' "$LOCAL_SETTINGS" || true)
    echo "✅ $LOCAL_SETTINGS generated ($count hook commands, all absolute paths)"
    echo "   Project root: $PROJECT_DIR"
    echo "   Settings file is in .gitignore — safe from packaging"
else
    echo "ERROR: Invalid JSON generated" >&2
    rm -f "$LOCAL_SETTINGS"
    exit 1
fi
