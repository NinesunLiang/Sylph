#!/bin/bash
# pretool-python-bridge.sh — Python 桥接脚本
# 用途：hook 中调用 Python 脚本的入口点
# 跨平台：bash 3.2 (macOS stock) + bash 4+ (Windows Git Bash) 兼容
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 禁止 set -e（hook 铁则：永不阻断）
# 禁止 eval/rm -rf 等危险操作

main() {
    local cmd="$1"
    shift

    case "$cmd" in
        context-inject)
            python3 "$SCRIPT_DIR/context.py" "$@"
            ;;
        handoff-before)
            python3 "$SCRIPT_DIR/handoff.py" before-compact "$@"
            ;;
        handoff-after)
            python3 "$SCRIPT_DIR/handoff.py" after-compact "$@"
            ;;
        smoke)
            python3 "$SCRIPT_DIR/context.py" --smoke && \
            python3 "$SCRIPT_DIR/handoff.py" --smoke
            ;;
        *)
            echo "usage: pretool-python-bridge.sh <context-inject|handoff-before|handoff-after|smoke> [args]"
            return 0
            ;;
    esac
}

main "$@"
exit 0
