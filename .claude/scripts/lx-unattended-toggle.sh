#!/usr/bin/env bash
# lx-unattended-toggle.sh — 切换无人值守模式
# 用法: lx-unattended on|off|status
# 无人值守模式: context-guard 更松散，不阻断写操作，仅记录 flywheel

FLAG_FILE="$(cd "$(dirname "$0")/../.." && pwd)/.omc/state/.unattended-mode"

case "${1:-status}" in
    on)
        touch "$FLAG_FILE"
        echo "✅ 无人值守模式已开启 — context-guard 仅记录，不阻断"
        ;;
    off)
        rm -f "$FLAG_FILE"
        echo "✅ 无人值守模式已关闭 — context-guard 恢复正常阻断"
        ;;
    status)
        if [ -f "$FLAG_FILE" ]; then
            echo "📋 无人值守模式: 🟢 开启中"
        else
            echo "📋 无人值守模式: ⚪ 已关闭"
        fi
        ;;
    *)
        echo "用法: lx-unattended on|off|status"
        exit 1
        ;;
esac
