#!/bin/bash

# harness-kit:managed v1.0.2

# PostToolUse:Edit 代码风格自查 + 文档同步提醒 + 方案复用检测

# 仅对源代码文件生效，提示开发者执行自查清单


source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_edit_quality" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    pass" 2>/dev/null)
fi

# 非源代码文件直接放行
# R18 修复：case 的 * glob 不跨 /，先 basename 再匹配
# R24-S3 修复：set -f 禁用 pathname expansion，避免 cwd 有 *.go 时 $SOURCE_EXT 被展开为具体文件名
SOURCE_EXT=$(hc_get "project.source_extensions" "*.go")
_EQ_BASE=$(basename "$FILE_PATH")
_EQ_MATCH=false
set -f
for ext in $SOURCE_EXT; do
    # shellcheck disable=SC2254  # glob ${ext} is intentional (matches "*.go" as pattern)
    case "$_EQ_BASE" in
        ${ext}) _EQ_MATCH=true; break ;;
    esac
done
set +f
if [ "$_EQ_MATCH" = false ]; then
    echo '{"continue": true}'
    exit 0
fi

FILENAME=$(basename "$FILE_PATH")
QUALITY_CHECKLIST=$(hc_get "architecture.quality_checklist" "命名§4.2 | 导入三段式§4.3 | 错误处理§4.4 | 函数长度§4.5 | 日志纯英文§G-7")
MSG="代码已修改(${FILENAME})。自查: ${QUALITY_CHECKLIST}"

# 核心业务层追加文档同步提醒
# R24-S3 修复：set -f 禁用 pathname expansion，避免配置中的 glob 被 cwd 实际文件匹配展开
BUSINESS_LAYERS=$(hc_get "architecture.business_layers" "*/logic/* */model/* */executor/* */ai/*")
DOC_SYNC_TARGET=$(hc_get "architecture.doc_sync_target" "executor.md")
set -f
for layer in $BUSINESS_LAYERS; do
    # shellcheck disable=SC2254  # glob ${layer} is intentional (matches "*/logic/*" as pattern)
    case "$FILE_PATH" in
        ${layer}) MSG="${MSG} | 文档同步: 若涉及状态/接口变更，更新${DOC_SYNC_TARGET}" ; break ;;
    esac
done
set +f

# Handler 层追加架构约束提醒
HANDLER_LAYERS=$(hc_get "architecture.handler_layers" "*/handler/*")
HANDLER_CONSTRAINT=$(hc_get "architecture.handler_constraint" "Handler禁止直接调用Model(§4.1)")
set -f
for layer in $HANDLER_LAYERS; do
    # shellcheck disable=SC2254  # glob ${layer} is intentional (matches "*/handler/*" as pattern)
    case "$FILE_PATH" in
        ${layer}) MSG="${MSG} | 注意: ${HANDLER_CONSTRAINT}" ; break ;;
    esac
done
set +f

# 方案复用检测：当 Edit 涉及 ≥3 个文件且与最近修改文件集重合度 >60%
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
EDIT_HISTORY="$STATE_DIR/edit-history.log"
mkdir -p "$STATE_DIR"

# 记录本次编辑文件
REAL_PATH=$(realpath "$FILE_PATH" 2>/dev/null || echo "$FILE_PATH")
echo "$(date +%s) $REAL_PATH" >> "$EDIT_HISTORY"

# 清理超过 30 分钟的记录（视为同一次批量编辑）
CUTOFF=$(($(date +%s) - 1800))
TEMP_FILE="$STATE_DIR/edit-history.tmp"
while IFS= read -r line; do
    TS=$(echo "$line" | awk '{print $1}')
    if [ "$TS" -ge "$CUTOFF" ]; then
        echo "$line"
    fi
done < "$EDIT_HISTORY" > "$TEMP_FILE" 2>/dev/null
mv "$TEMP_FILE" "$EDIT_HISTORY"

# 统计本次批量编辑的文件数
CURRENT_FILES=$(awk '{print $2}' "$EDIT_HISTORY" | sort -u)
FILE_COUNT=$(echo "$CURRENT_FILES" | wc -l | tr -d ' ')

if [ "$FILE_COUNT" -ge 3 ]; then
    # 读取上一次批量编辑的文件集
    PREVIOUS_EDIT_FILE="$STATE_DIR/previous-edit-batch.log"

    if [ -f "$PREVIOUS_EDIT_FILE" ]; then
        # 计算重合度
        MATCH_COUNT=0
        while IFS= read -r f; do
            if echo "$CURRENT_FILES" | grep -qxF "$f" 2>/dev/null; then
                MATCH_COUNT=$((MATCH_COUNT + 1))
            fi
        done < "$PREVIOUS_EDIT_FILE"

        PREVIOUS_COUNT=$(wc -l < "$PREVIOUS_EDIT_FILE" | tr -d ' ')
        if [ "$PREVIOUS_COUNT" -gt 0 ]; then
            OVERLAP_PCT=$((MATCH_COUNT * 100 / PREVIOUS_COUNT))
            if [ "$OVERLAP_PCT" -gt 60 ]; then
                MSG="${MSG} | ⚠️ 方案复用检测: 本次编辑 ${FILE_COUNT} 个文件与上次(${PREVIOUS_COUNT} 个)重合度 ${OVERLAP_PCT}%。请执行复用自检(宪法第十条): [1]文件集重合≥80% [2]接口契约未变 [3]场景类型一致 [4]状态机未改。未通过自检禁止直接套用旧方案。"
            fi
        fi
    fi

    # 保存本次文件集供下次比较
    echo "$CURRENT_FILES" > "$PREVIOUS_EDIT_FILE"
fi

printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$MSG"
exit 0
