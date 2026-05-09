#!/usr/bin/env bash
# lx-oma-gov-resolve.sh — L3 冲突裁决命令
# 来源: HUMAN-IN-THE-LOOP-GATE.md §1 + governance-spec.md §4
# 用法: lx-oma-gov-resolve <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason "说明"]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
CONSOLIDATION_LOG="$PROJECT_ROOT/CONSOLIDATION-LOG.md"
PENDING_DECISIONS="$STATE_DIR/pending-decisions.md"
NOW_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ─── Help ───
if [ $# -lt 2 ]; then
    echo "用法: lx-oma-gov-resolve <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason \"说明\"]"
    echo ""
    echo "裁决选项:"
    echo "  accept          完整接受，进入 master"
    echo "  accept-partial  部分接受（需配合 --targets）"
    echo "  reject          驳回，不进入 master"
    echo "  defer           暂缓，保留在 pending"
    exit 1
fi

CONFLICT_ID="$1"
VERDICT="$2"
shift 2

# Parse options
REASON=""
TARGETS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --reason) REASON="$2"; shift 2 ;;
        --targets) TARGETS="$2"; shift 2 ;;
        *) echo "未知选项: $1"; exit 1 ;;
    esac
done

# Validate verdict
case "$VERDICT" in
    accept|reject|defer) ;;
    accept-partial)
        if [ -z "$TARGETS" ]; then
            echo "ERROR: accept-partial 需要 --targets 指定接受哪些对象"
            exit 1
        fi
        ;;
    *) echo "ERROR: 未知裁决 '$VERDICT'。可用: accept, accept-partial, reject, defer"; exit 1 ;;
esac

# ─── Check prerequisites ───
if [ ! -f "$PENDING_DECISIONS" ]; then
    echo "ERROR: 未找到 pending-decisions.md ($PENDING_DECISIONS)"
    echo "提示: 请先运行 reconcile 产生 L3 冲突"
    exit 1
fi

# ─── 1. 从 pending-decisions.md 读取冲突详情 ───
echo "📖 查找 $CONFLICT_ID..."
CONFLICT_BLOCK=$(grep -A10 "^## Open.*$CONFLICT_ID" "$PENDING_DECISIONS" 2>/dev/null || true)
if [ -z "$CONFLICT_BLOCK" ]; then
    echo "ERROR: $CONFLICT_ID 未在 $PENDING_DECISIONS 中找到"
    echo "提示: 运行 status 查看当前 open conflict 列表"
    exit 1
fi

echo "$CONFLICT_BLOCK"

# ─── 2. 更新 CONSOLIDATION-LOG.md ───
if [ -f "$CONSOLIDATION_LOG" ]; then
    # Find the CL entry matching this conflict and append adjudication
    CL_ENTRY=$(grep -B5 -A5 "$CONFLICT_ID" "$CONSOLIDATION_LOG" 2>/dev/null || true)
    if [ -n "$CL_ENTRY" ]; then
        cat >> "$CONSOLIDATION_LOG" <<EOF

### 裁决记录: ${CONFLICT_ID}
- Adjudicated At: ${NOW_UTC}
- Verdict: ${VERDICT}
- Reason: ${REASON:-无}
EOF
        if [ -n "$TARGETS" ]; then
            echo "- Accepted Targets: ${TARGETS}" >> "$CONSOLIDATION_LOG"
        fi
        # Update the entry status
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "/${CONFLICT_ID}/,/Status:/ s/Status:.*$/Status: ${VERDICT}/" "$CONSOLIDATION_LOG" 2>/dev/null || true
        else
            sed -i "/${CONFLICT_ID}/,/Status:/ s/Status:.*$/Status: ${VERDICT}/" "$CONSOLIDATION_LOG" 2>/dev/null || true
        fi
        echo "✅ CONSOLIDATION-LOG.md 已更新"
    fi
fi

# ─── 3. 更新 pending-decisions.md ───
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "/^## Open.*$CONFLICT_ID/,/^$/ s/^## Open.*$CONFLICT_ID/## Resolved: $CONFLICT_ID ($VERDICT)/" "$PENDING_DECISIONS" 2>/dev/null || true
else
    sed -i "/^## Open.*$CONFLICT_ID/,/^$/ s/^## Open.*$CONFLICT_ID/## Resolved: $CONFLICT_ID ($VERDICT)/" "$PENDING_DECISIONS" 2>/dev/null || true
fi

echo "✅ $PENDING_DECISIONS 已更新 ($CONFLICT_ID → $VERDICT)"

# ─── 4. Post-verdict actions ───
case "$VERDICT" in
    accept|accept-partial)
        echo ""
        echo "🔜 继续 reconcile 流程 — $CONFLICT_ID 的变更将归并到 master"
        echo "   运行 propagate --dry-run 预览传播内容"
        ;;
    reject)
        echo ""
        echo "❌ $CONFLICT_ID 已驳回，变更不归并到 master"
        ;;
    defer)
        echo ""
        echo "⏸️  $CONFLICT_ID 暂缓，保留 BLOCKED 状态"
        echo "   下次 reconcile 时重新评估"
        ;;
esac

echo ""
echo "📋 裁决摘要:"
echo "  CONFLICT-ID: $CONFLICT_ID"
echo "  Verdict: $VERDICT"
echo "  Time: $NOW_UTC"
echo "  Reason: ${REASON:-无}"

# ─── 方向指引 ───
echo ""
echo "─── 方向指引 ───"
case "$VERDICT" in
    accept|accept-partial)
        echo "  变更已接受，可继续以下流程:"
        echo "    1. lx-oma-gov propagate --dry-run"
        echo "       → 预览传播内容"
        echo "    2. lx-oma-gov propagate --execute"
        echo "       → dry-run确认后执行实际传播"
        echo "    3. lx-oma-gov status"
        echo "       → 查看治理全景（建议首选）"
        ;;
    reject)
        echo "  变更已驳回。建议下一步:"
        echo "    1. lx-oma-gov status"
        echo "       → 查看更新后治理状态"
        echo "    2. lx-oma-gov reconcile"
        echo "       → 如有新资料，重新reconcile"
        ;;
    defer)
        echo "  变更已暂缓。建议下一步:"
        echo "    1. lx-oma-gov status"
        echo "       → 查看待处理的 BLOCKED 项"
        echo "    2. 收集更多信息后重新裁决"
        echo "       → lx-oma-gov resolve $CONFLICT_ID accept|reject"
        ;;
esac
echo "    4. 自定义操作 — 输入你想要的命令"
echo "    ─── 或直接输入你想要的命令 ───"

exit 0
