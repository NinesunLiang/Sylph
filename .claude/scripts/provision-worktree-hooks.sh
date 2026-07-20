#!/usr/bin/env bash
# provision-worktree-hooks.sh
#
# 用法:  bash .claude/scripts/provision-worktree-hooks.sh <worktree-path>
# 例子:  bash .claude/scripts/provision-worktree-hooks.sh .claude/worktrees/agent-xxx/
#
# 把主仓库的 .claude/hooks/ 安全同步到 worktree。
# 核心逻辑: 逐个文件 cp 覆盖，绝不 cp -R，杜绝嵌套。
# 只复制主仓库 hooks 目录里实际存在的文件（lite 套件），
# 不删除 worktree 已有的其他 hook 文件。

set -euo pipefail

MAIN_HOOKS="$(cd "$(dirname "$0")/../hooks" && pwd)"

WORKTREE_PATH="$1"
if [ -z "$WORKTREE_PATH" ]; then
  echo "ERROR: 用法: bash $0 <worktree-path>" >&2
  exit 1
fi

WT_REAL="$(cd "$WORKTREE_PATH" 2>/dev/null && pwd)" || {
  echo "ERROR: 目录不存在: $WORKTREE_PATH" >&2
  exit 1
}

WT_HOOKS="$WT_REAL/.claude/hooks"

if [ ! -d "$WT_HOOKS" ]; then
  echo "WARN: $WT_REAL 没有 .claude/hooks 目录，创建中..."
  mkdir -p "$WT_HOOKS"
fi

echo "syncing hooks into $WT_REAL"

errors=0
cd "$MAIN_HOOKS"
for entry in *; do
  case "$entry" in
    __pycache__|lib|tests)
      continue
      ;;
  esac
  src="$MAIN_HOOKS/$entry"
  dst="$WT_HOOKS/$entry"
  if [ -f "$src" ]; then
    rm -f "$dst"
    if cp "$src" "$dst"; then
      echo "  $entry"
    else
      echo "  FAIL: $entry" >&2
      errors=$((errors + 1))
    fi
  fi
done

if [ "$errors" -gt 0 ]; then
  echo "WARN: $errors 个文件复制失败" >&2
fi

echo "done: $(basename "$(cd "$(dirname "$0")/../.." && pwd)") hooks → $WT_REAL/.claude/hooks/"
echo ""
echo "验证: ls \"$WT_HOOKS/hook-launcher.py\""
