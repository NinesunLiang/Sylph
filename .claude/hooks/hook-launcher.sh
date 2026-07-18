#!/usr/bin/env bash
# CarrorOS Hook Launcher
# 用 $0 定位自身，切到项目根目录，再跑对应 hook
# settings.json 里写: .claude/hooks/hook-launcher.sh <hook_name>.py

set -euo pipefail

# 从 launcher 自身路径定位项目根
LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$LAUNCHER_DIR/../.." && pwd)"

HOOK_NAME="${1:-}"
if [ -z "$HOOK_NAME" ]; then
  echo "{\"continue\":true,\"message\":\"hook-launcher: missing hook name\"}"
  exit 0
fi

HOOK_PATH="$LAUNCHER_DIR/$HOOK_NAME"
if [ ! -f "$HOOK_PATH" ]; then
  echo "{\"continue\":true,\"message\":\"hook-launcher: hook not found: $HOOK_NAME\"}"
  exit 0
fi

cd "$PROJECT_ROOT"

# Sol 复审 P1-SOL-2 锁紧：生产路径显式清除 night-deny 的测试覆写变量，
# 保证 marker 根只能由 hook 文件 __file__ 锚定（模型/会话环境无法拐根）。
unset NIGHT_DENY_ROOT

case "$HOOK_NAME" in
  *.sh)
    exec bash "$HOOK_PATH"
    ;;
  *)
    exec python3 "$HOOK_PATH"
    ;;
esac
