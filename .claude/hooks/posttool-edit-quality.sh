#!/usr/bin/env bash
# posttool-edit-quality.sh — PostToolUse:Edit|Write — 编辑后自查代码风格、文档同步、方案复用检测
# Role: 编辑后自查代码风格、文档同步、方案复用检测

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

# === AC-3: 工具响应异常检测 → claude-next.md 追加 ===
# 检测模式：超大编辑（>500 chars）、快速连续编辑同一文件
_CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
_ANOMALY_TRACKER="$STATE_DIR/edit-quality-anomalies.json"
mkdir -p "$(dirname "$_ANOMALY_TRACKER")"

_PY_ANOMALY=$(echo "$INPUT" | python3 - "$FILE_PATH" "$_ANOMALY_TRACKER" "$_CLAUDE_NEXT" "$EDIT_HISTORY" <<'PYEOF' 2>/dev/null
import json, os, sys, time

stdin_json = sys.stdin.read()
file_path = sys.argv[1]
tracker_path = sys.argv[2]
claude_next = sys.argv[3]
edit_history = sys.argv[4]

try:
    data = json.loads(stdin_json)
except json.JSONDecodeError:
    sys.exit(0)

tool_input = data.get('tool_input', {})
ti = tool_input or {}
old_size = len(ti.get('old_string', '') or '')
new_size = len(ti.get('new_string', '') or '')
content_size = len(ti.get('content', '') or '')
max_change = max(old_size, new_size, content_size)

anomalies = []
now = time.time()

if max_change > 500:
    anomalies.append(('large_edit', f'{file_path} ({max_change} chars)'))

if os.path.exists(edit_history):
    try:
        with open(edit_history) as f:
            recent = [l.strip().split() for l in f if l.strip()]
        same_file = [(int(ts), p) for ts, p in recent if p == file_path and now - int(ts) < 60]
        if len(same_file) >= 3:
            anomalies.append(('rapid_edit', f'{file_path} ({len(same_file)} edits/60s)'))
    except (ValueError, IndexError, OSError):
        pass

if not anomalies:
    sys.exit(0)

tracked = {}
if os.path.exists(tracker_path):
    try:
        with open(tracker_path) as f:
            tracked = json.load(f)
    except (json.JSONDecodeError, OSError):
        tracked = {}

new_entries = [a for a in anomalies if a[0] not in tracked]
if not new_entries:
    sys.exit(0)

for sig, _ in new_entries:
    tracked[sig] = {'ts': now, 'file': file_path}
with open(tracker_path, 'w') as f:
    json.dump(tracked, f, indent=2)

entry_date = time.strftime('%Y-%m-%d')
lines = [f'\n### [auto-detect:{entry_date}] Edit anomaly pattern\n']
lines.append(f'@{entry_date} hits:1\n')
anomaly_names = {'large_edit': '大编辑块', 'rapid_edit': '快速连续编辑'}
for sig, desc in new_entries:
    name = anomaly_names.get(sig, sig)
    lines.append(f'**模式**: {name} — {desc}')
    lines.append(f'触发条件：编辑工具调用中出现 {name} 模式')
    lines.append(f'建议：拆分大编辑为多个小编辑，或预先规划减少快速修正\n')

try:
    with open(claude_next) as f:
        existing = f.read()
    with open(claude_next, 'a') as f:
        for line in lines:
            if line not in existing:
                f.write(line + '\n')
except OSError:
    pass

print(f'anomaly_detected: {", ".join(a[0] for a in new_entries)}')
PYEOF
)

if [ -n "$_PY_ANOMALY" ]; then
    MSG="${MSG} | 编辑异常检测: ${_PY_ANOMALY}"
fi

echo "$MSG" | hc_emit_hook_json "PostToolUse" "true"
flywheel_event "posttool_edit_quality" "quality_checked" "P2" "checked"
exit 0
