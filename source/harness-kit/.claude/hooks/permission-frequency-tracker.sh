#!/usr/bin/env bash
# permission-frequency-tracker.sh — PostToolUse:* — 统计当前会话中 permission-required* 文件的创建次数
# Role: 统计当前会话中 permission-required* 文件的创建次数，写入 .omc/state/permission-frequency.json
# 哲学 #6 (0信任): 量化权限请求频率，辅助审计
# 永不阻断

source "$(dirname "$0")/harness_config.sh"
hc_enabled "permission_frequency_tracker" || { echo '{"continue":true}'; exit 0; }
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

PERM_FILE="$STATE_DIR/permission-frequency.json"

# 提取 file_path 字段（适用于 Edit/Write/Bash 等工具）
FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    fp = ti.get('file_path', '') or ''
    if not fp:
        fp = d.get('args', {}).get('filePath', '') or ''
    print(fp)
except:
    pass" 2>/dev/null)

# 提取 tool_use_id 用于去重
TOOL_USE_ID=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_use_id', d.get('id', '')) or '')
except:
    pass" 2>/dev/null)

# 只关注门禁标记文件路径
case "$(basename "$FILE_PATH")" in
    permission-req*|permission-app*|permission-mar*)
        ;;
    *)
        echo '{"continue": true}'
        exit 0
        ;;
esac

# 基于 tool_use_id 去重写入
${PYTHON_BIN:-python3} - "$PERM_FILE" "$FILE_PATH" "$TOOL_USE_ID" <<'PYEOF'
import sys, json, os, time

perm_file = sys.argv[1]
file_path = sys.argv[2]
tool_id = sys.argv[3]

now = int(time.time())
basename = os.path.basename(file_path)

# 读取现有记录
data = {"total_count": 0, "files": {}, "tool_ids": [], "session_start": now, "last_updated": now}
if os.path.isfile(perm_file):
    try:
        with open(perm_file, "r") as f:
            existing = json.load(f)
            data["total_count"] = existing.get("total_count", 0)
            data["files"] = existing.get("files", {})
            data["tool_ids"] = existing.get("tool_ids", [])
            data["session_start"] = existing.get("session_start", now)
    except (json.JSONDecodeError, IOError):
        pass

# 去重：同一 tool_use_id 不重复计数
if tool_id and tool_id in data["tool_ids"]:
    # 更新 last_updated 但不变计数
    data["last_updated"] = now
    with open(perm_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    sys.exit(0)

# 更新计数
data["total_count"] += 1
if tool_id:
    data["tool_ids"].append(tool_id)

# 按文件名聚合
if basename not in data["files"]:
    data["files"][basename] = {"count": 0, "paths": []}
data["files"][basename]["count"] += 1
if file_path not in data["files"][basename]["paths"]:
    data["files"][basename]["paths"].append(file_path)

data["last_updated"] = now

with open(perm_file, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
PYEOF

flywheel_event "permission_frequency_tracker" "counted_$(basename "$FILE_PATH")" "P3" || true
echo '{"continue": true}'
