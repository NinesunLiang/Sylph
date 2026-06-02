#!/usr/bin/env bash
# pretool-b1-detect.sh — PreToolUse:Edit|Write — 检测单次编辑是否过度（新文件创建数告警）
# Role: 统计本会话已创建的新文件数，超过5个时输出告警但不阻断。记录每次新文件创建到 new-files-log.jsonl
# 哲学 #1 (less is more): 提示而非阻断，避免干扰紧急修复
# 哲学 #3 (先守护): 预警过度编辑，保护文件系统不被无节制创建

source "$(dirname "$0")/harness_config.sh"
hc_enabled "b1_detect" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
LOG_FILE="$STATE_DIR/new-files-log.jsonl"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
THRESHOLD=$(hc_get "b1_detect.new_file_threshold" "5")

# 统一模式检测: ghost/goal/rpe 模式下仍记录但不阻断
MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")

# ─── 提取 file_path 字段 ──────────────────────────
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    fp = data.get('args', {}).get('filePath', '')
    if not fp:
        ti = data.get('tool_input', {})
        fp = ti.get('file_path', '')
    print(fp)
except:
    pass" 2>/dev/null)
    TOOL_NAME=""
fi

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

# ─── 仅检测 Write 操作（创建新文件） ──────────────
# Edit 操作不创建新文件，跳过
if [ "$TOOL_NAME" = "Edit" ]; then
    echo '{"continue": true}'
    exit 0
fi

# ─── 判断是否为新文件创建 ─────────────────────────
# 如果文件已存在，不算新文件创建
if [ -f "$FILE_PATH" ]; then
    echo '{"continue": true}'
    exit 0
fi

# ─── 记录新文件 ───────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_ENTRY=$(${PYTHON_BIN:-python3} -c "
import json
entry = {
    \"timestamp\": \"$TIMESTAMP\",
    \"session_id\": \"$SESSION_ID\",
    \"file_path\": \"$FILE_PATH\",
    \"tool\": \"$TOOL_NAME\",
    \"mode\": \"$MODE\"
}
print(json.dumps(entry))
" 2>/dev/null || echo "{\"timestamp\":\"$TIMESTAMP\",\"session_id\":\"$SESSION_ID\",\"file_path\":\"$FILE_PATH\",\"tool\":\"$TOOL_NAME\",\"mode\":\"$MODE\"}")

mkdir -p "$STATE_DIR"
echo "$LOG_ENTRY" >> "$LOG_FILE"

# ─── 统计本会话新文件数 ───────────────────────────
COUNT=$(${PYTHON_BIN:-python3} -c "
import json
count = 0
try:
    with open('$LOG_FILE') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('session_id') == '$SESSION_ID':
                    count += 1
            except json.JSONDecodeError:
                continue
except FileNotFoundError:
    pass
print(count)
" 2>/dev/null || echo "0")

# ─── 超过阈值输出告警 ─────────────────────────────
if [ "$COUNT" -gt "$THRESHOLD" ] 2>/dev/null; then
    cat >&2 <<WARN
⚠️  [B1 Detect] 本会话已创建 ${COUNT} 个新文件（阈值: ${THRESHOLD}）
   最新: ${FILE_PATH}
   哲学 #1 (less is more): 新文件过多，建议评估是否真正需要。

WARN
    flywheel_event "b1_detect" "warn_excessive" "P3" "count=${COUNT},file=${FILE_PATH}" || true
fi

echo '{"continue": true}'
exit 0
