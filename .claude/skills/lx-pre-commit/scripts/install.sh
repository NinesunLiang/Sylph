#!/usr/bin/env bash
# install.sh — lx-pre-commit 安装脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_NAME="lx-pre-commit"
COPY_PATH=""

# ── 检测目标路径 ─────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
  COPY_PATH="${HOME}/.local/bin"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  COPY_PATH="${HOME}/.local/bin"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  COPY_PATH="${HOME}/bin"
else
  COPY_PATH="/usr/local/bin"
fi

mkdir -p "$COPY_PATH"

# ── 复制脚本 ─────────────────────────────────
cp "${SCRIPT_DIR}/lx-pre-commit.sh" "${COPY_PATH}/${BIN_NAME}"
chmod +x "${COPY_PATH}/${BIN_NAME}"
echo "✅ 已安装到 ${COPY_PATH}/${BIN_NAME}"

# ── 依赖检查 ─────────────────────────────────
echo ""
echo "==> 依赖检查"
for dep in bash timeout; do
  if command -v "$dep" &>/dev/null; then
    echo "  ✅ $dep"
  else
    echo "  ⚠️ $dep 未安装（脚本不会自动运行）"
  fi
done

# ── git hooks 安装（可选）───────────────────
if [ -d ".git/hooks" ]; then
  HOOK_FILE=".git/hooks/pre-commit"
  if [ -f "$HOOK_FILE" ]; then
    echo ""
    echo "⚠️ 已有 pre-commit hook: $HOOK_FILE"
    echo "   备份至 ${HOOK_FILE}.bak"
    cp "$HOOK_FILE" "${HOOK_FILE}.bak"
  fi

  cat > "$HOOK_FILE" << 'HOOKEOF'
#!/bin/sh
# lx-pre-commit hook — 自动安装
if command -v lx-pre-commit &>/dev/null; then
  exec lx-pre-commit
fi
HOOKEOF
  chmod +x "$HOOK_FILE"
  echo "✅ git hook 已安装到 ${HOOK_FILE}"
else
  echo ""
  echo "⚠️ 未检测到 .git/hooks/，跳过 git hook 安装"
  echo "   进入项目目录后手动运行: ${COPY_PATH}/${BIN_NAME}"
fi

echo ""
echo "==> 安装完成"
echo "   手动运行: ${BIN_NAME}"
echo "   或 git commit 时自动触发"
