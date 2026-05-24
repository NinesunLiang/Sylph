#!/usr/bin/env bash
# task-workspace.sh — 日常复杂任务持久化工作区（哲学 #7 物化）
# 用法: task-workspace.sh init "任务标题"
#        task-workspace.sh progress "进度描述"
#        task-workspace.sh decision "决策描述"
#        task-workspace.sh done "完成摘要"
#        task-workspace.sh list
#        task-workspace.sh resume <workspace-id>
#
# 对标 RPE 四文件闭环，但更轻量：
#   .omc/state/tasks/{datetime-id}-{slug}/
#     progress.md   — 当前进度、卡点、决策记录
#     prd.md        — 需求/方案描述
#     executor.md   — 执行步骤和状态
#
# 哲学追溯:
#   #7(文档优先): 全流程持久化，调研→方案→执行→留痕
#   #5(以人为本): 人随时打开可看进度，跨会话可恢复
#   #4(没验证=没做): 完成时必须有强证据

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
TASKS_DIR="$STATE_DIR/tasks"
mkdir -p "$TASKS_DIR"

# slugify: Python for proper Unicode (BSD sed doesn't handle \u4e00-\u9fff)
# Fallback to ASCII-only if Python unavailable
slugify() {
    local raw="$1"
    local slug
    slug=$(${PYTHON_BIN:-python3} -c "
import re, sys
s = sys.argv[1].lower()
s = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', s)
s = s.strip('-')
print(s if s else 'task')
" "$raw" 2>/dev/null)
    if [ -z "$slug" ]; then
        slug=$(echo "$raw" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
        [ -z "$slug" ] && slug="task"
    fi
    echo "$slug"
}

# Portable sed -i (BSD vs GNU)
if sed --version 2>/dev/null | grep -q GNU; then
    SED_INPLACE=(sed -i)
else
    SED_INPLACE=(sed -i '')
fi

init() {
    local title="${1:-未命名任务}"
    local ts
    ts=$(date +%Y%m%d-%H%M%S)
    local slug
    slug=$(slugify "$title")
    local ws_id="${ts}-${slug}"
    local ws_dir="$TASKS_DIR/$ws_id"

    if [ -d "$ws_dir" ]; then
        echo "⚠️  工作区已存在: $ws_dir"
        echo "$ws_id"
        return 1
    fi

    mkdir -p "$ws_dir"

    # ─── prd.md ───
    cat > "$ws_dir/prd.md" <<PRDEOF
# $title

> 创建时间: $(date '+%Y-%m-%d %H:%M:%S')
> 工作区 ID: $ws_id
> 状态: 🟢 进行中

## 需求/方案描述

$title

## 边界

- 范围:
- 明确不在范围内:

## 验收条件

- [ ] AC1:
- [ ] AC2:

## 风险点

-
PRDEOF

    # ─── executor.md ───
    cat > "$ws_dir/executor.md" <<EXECEOF
# Executor — 执行步骤

> 工作区: $ws_id
> 当前 Step: 0
> 状态: 🟢 进行中

## 执行步骤

- [ ] Step 1:
- [ ] Step 2:

## 重试记录

(无)

## 跳过的风险

(无)

## 附带发现

(无)
EXECEOF

    # ─── progress.md ───
    cat > "$ws_dir/progress.md" <<PROGEOF
# Progress — 进度日志

> 工作区: $ws_id
> 最后更新: $(date '+%Y-%m-%d %H:%M:%S')

## $(date '+%Y-%m-%d %H:%M:%S') — 工作区创建

- 任务: $title
- 状态: 初始化

PROGEOF

    # 创建活跃工作区链接
    ln -sf "$ws_dir" "$TASKS_DIR/.active" 2>/dev/null

    echo "$ws_id"
    echo "✅ 工作区已创建: $ws_dir"
    echo ""
    echo "文件:"
    echo "  prd.md      — 需求/方案描述"
    echo "  executor.md — 执行步骤和状态"
    echo "  progress.md — 进度日志"
    echo ""
    echo "后续命令:"
    echo "  task-workspace.sh progress \"描述\"  — 记录进度"
    echo "  task-workspace.sh decision \"描述\"  — 记录决策"
    echo "  task-workspace.sh done \"摘要\"      — 标记完成"
}

progress() {
    local msg="${1:-进度更新}"
    local ws_dir
    ws_dir=$(readlink "$TASKS_DIR/.active" 2>/dev/null || echo "")
    if [ -z "$ws_dir" ] || [ ! -d "$ws_dir" ]; then
        echo "❌ 无活跃工作区。先用 task-workspace.sh init \"标题\" 创建。"
        return 1
    fi

    cat >> "$ws_dir/progress.md" <<PROGEOF

## $(date '+%Y-%m-%d %H:%M:%S') — 进度更新

- $msg
PROGEOF
    echo "✅ 进度已记录"
}

decision() {
    local msg="${1:-决策记录}"
    local ws_dir
    ws_dir=$(readlink "$TASKS_DIR/.active" 2>/dev/null || echo "")
    if [ -z "$ws_dir" ] || [ ! -d "$ws_dir" ]; then
        echo "❌ 无活跃工作区。"
        return 1
    fi

    cat >> "$ws_dir/progress.md" <<PROGEOF

## $(date '+%Y-%m-%d %H:%M:%S') — 🔵 决策

- $msg
- 依据: [哲学先行: 待补充]
PROGEOF
    echo "✅ 决策已记录"
}

complete_task() {
    local summary="${1:-任务完成}"
    local ws_dir
    ws_dir=$(readlink "$TASKS_DIR/.active" 2>/dev/null || echo "")
    if [ -z "$ws_dir" ] || [ ! -d "$ws_dir" ]; then
        echo "❌ 无活跃工作区。"
        return 1
    fi

    # 更新状态 (portable sed via SED_INPLACE array)
    "${SED_INPLACE[@]}" 's/🟢 进行中/✅ 已完成/g' "$ws_dir/prd.md" 2>/dev/null
    "${SED_INPLACE[@]}" 's/🟢 进行中/✅ 已完成/g' "$ws_dir/executor.md" 2>/dev/null

    cat >> "$ws_dir/progress.md" <<PROGEOF

## $(date '+%Y-%m-%d %H:%M:%S') — ✅ 任务完成

- $summary
PROGEOF

    rm -f "$TASKS_DIR/.active"
    echo "✅ 工作区已标记完成: $(basename "$ws_dir")"
    echo "   摘要: $summary"
}

list() {
    echo "=== 活跃工作区 ==="
    if [ -L "$TASKS_DIR/.active" ] && [ -d "$TASKS_DIR/.active" ]; then
        local active
        active=$(basename "$(readlink "$TASKS_DIR/.active")")
        echo "  🟢 活跃: $active"
    else
        echo "  (无活跃工作区)"
    fi
    echo ""
    echo "=== 历史工作区 ==="
    for ws in "$TASKS_DIR"/*/; do
        ws_name=$(basename "$ws")
        [ "$ws_name" = ".active" ] && continue
        local status="🟢"
        [ -f "$ws/prd.md" ] && grep -q '已完成' "$ws/prd.md" 2>/dev/null && status="✅"
        echo "  $status $ws_name"
    done | sort -r | head -15
}

resume() {
    local ws_id="$1"
    local ws_dir="$TASKS_DIR/$ws_id"
    if [ ! -d "$ws_dir" ]; then
        # Try partial match
        local matches
        matches=$(find "$TASKS_DIR" -maxdepth 1 -type d -name "${ws_id}*" 2>/dev/null | head -3)
        if [ -z "$matches" ]; then
            echo "❌ 工作区不存在: $ws_id"
            echo "   可用: task-workspace.sh list"
            return 1
        fi
        ws_dir=$(echo "$matches" | head -1)
    fi

    ln -sf "$ws_dir" "$TASKS_DIR/.active" 2>/dev/null
    echo "✅ 已恢复工作区: $(basename "$ws_dir")"
    echo ""
    echo "--- prd.md ---"
    head -20 "$ws_dir/prd.md" 2>/dev/null
    echo ""
    echo "--- executor.md (最后 3 步) ---"
    grep -E '\[.\] Step' "$ws_dir/executor.md" 2>/dev/null | tail -5
    echo ""
    echo "--- progress.md (最后 5 条) ---"
    grep '## 20' "$ws_dir/progress.md" 2>/dev/null | tail -5
}

case "${1:-list}" in
    init)    shift; init "$*" ;;
    progress) shift; progress "$*" ;;
    decision) shift; decision "$*" ;;
    done|complete|finish) shift; complete_task "$*" ;;
    list)    list ;;
    resume)  resume "$2" ;;
    *)
        echo "用法: task-workspace.sh init|progress|decision|done|list|resume [参数]"
        echo ""
        echo "  init \"标题\"        创建新工作区"
        echo "  progress \"描述\"     记录进度"
        echo "  decision \"描述\"     记录决策"
        echo "  done \"摘要\"         标记完成"
        echo "  list                 查看所有工作区"
        echo "  resume <id>          恢复工作区"
        echo ""
        echo "工作区位于: .omc/state/tasks/{datetime}-{slug}/"
        exit 1
        ;;
esac
