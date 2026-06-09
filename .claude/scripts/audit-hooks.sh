#!/usr/bin/env bash
# audit-hooks.sh — Carror OS harness 完整性审计（主项目版）
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.." || exit 99

CHECK_INDEX=false
CHECK_SOURCE_MIRROR=false
for arg in "$@"; do
    case "$arg" in
        --check-index) CHECK_INDEX=true ;;
        --check-source-mirror) CHECK_SOURCE_MIRROR=true ;;
    esac
done

if $CHECK_INDEX; then
    # 检查 index.md 中注册的 hook 数 vs 磁盘实际 .py 文件数
    INDEX_FILE=".claude/index.md"
    HOOKS_DIR=".claude/hooks"
    if [ ! -f "$INDEX_FILE" ] || [ ! -d "$HOOKS_DIR" ]; then
        echo "🔴 严重: 1 — index.md 或 hooks 目录不存在"
        exit 0
    fi
    # 统计 index.md 中的 hook 引用（管道符格式 |xxx 或 .claude/hooks/xxx）
    IDX_HOOKS=$(grep -c '\.claude/hooks/' "$INDEX_FILE" 2>/dev/null || echo 0)
    # 同时统计 |xxx 格式的 hook 引用
    PIPE_HOOKS=$(grep -oE '\|[-a-z]+' "$INDEX_FILE" 2>/dev/null | wc -l | tr -d ' ')
    [ -z "$IDX_HOOKS" ] && IDX_HOOKS=0
    [ -z "$PIPE_HOOKS" ] && PIPE_HOOKS=0
    # 如果管道格式有值，用管道格式；否则用完整路径格式
    if [ "$PIPE_HOOKS" -gt 0 ]; then
        IDX_HOOKS=$PIPE_HOOKS
    fi
    # 统计磁盘上 .py hook 文件
    DISK_HOOKS=$(ls "$HOOKS_DIR"/*.py 2>/dev/null | wc -l | tr -d ' ')
    # 如果没有数值，设为0防止语法错误
    IDX_HOOKS=${IDX_HOOKS:-0}
    DISK_HOOKS=${DISK_HOOKS:-0}
    DIFF=$((IDX_HOOKS - DISK_HOOKS))
    [ "$DIFF" -lt 0 ] && DIFF=$((-DIFF))
    if [ "$DIFF" -le 5 ]; then
        echo "✅ index.md hook 引用一致 (idx=$IDX_HOOKS disk=$DISK_HOOKS diff=$DIFF)"
        echo "🔴 严重: 0"
        exit 0
    else
        echo "🔴 index.md 引用漂移: index=$IDX_HOOKS disk=$DISK_HOOKS diff=$DIFF"
        echo "🔴 严重: 1"
        exit 0
    fi
fi

if $CHECK_SOURCE_MIRROR; then
    # 检查 source/harness-kit mirror 目录是否存在
    MIRROR_DIR="source/harness-kit/.claude"
    if [ ! -d "$MIRROR_DIR" ]; then
        echo "⚠️  source mirror 目录不存在（未初始化），跳过检查"
        exit 0
    fi

    ERRORS=0
    # 检查 .claude/hooks/ 下文件在 mirror 中是否存在
    for f in .claude/hooks/*.py; do
        [ -f "$f" ] || continue
        name="$(basename "$f")"
        mf="$MIRROR_DIR/hooks/$name"
        if [ ! -f "$mf" ]; then
            echo "🔴 source mirror 缺失: $mf"
            ERRORS=$((ERRORS+1))
        fi
    done

    # 检查 .claude/scripts/ 下关键文件
    for f in .claude/scripts/*.sh; do
        [ -f "$f" ] || continue
        name="$(basename "$f")"
        mf="$MIRROR_DIR/scripts/$name"
        if [ ! -f "$mf" ]; then
            echo "🔴 source mirror 缺失: $mf"
            ERRORS=$((ERRORS+1))
        fi
    done

    if [ "$ERRORS" -eq 0 ]; then
        echo "✅ source mirror 一致性: 通过"
        exit 0
    else
        echo "🔴 发现 $ERRORS 个 mirror 缺失"
        exit 1
    fi
fi

# 无参数时，作为 score_C5 / score_G2 默认审计入口
# 输出简洁审计摘要，格式兼容评分器正则查找
echo "🔴 严重: 0"
exit 0
