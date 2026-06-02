#!/usr/bin/env bash
# pretool-scope-gate.sh — PreToolUse:Edit|Write — 检测 Edit/Write 是否超出 current-scope.txt 声明的文件范围
# 哲学 #5(范围冻结): 一次一 Step，非核心 → TODO，越界 → 撤销
# 无 current-scope.txt 时透传。支持 glob 模式匹配。自主模式降级为记录。

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_scope_gate" || { echo '{"continue": true}'; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
SCOPE_FILE="$STATE_DIR/current-scope.txt"

# ─── 无范围文件 → 透传 ───
if [ ! -f "$SCOPE_FILE" ]; then
    echo '{"continue": true}'
    exit 0
fi

INPUT=$(cat)
TOOL_NAME=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
fi
[ -z "$TOOL_NAME" ] && { echo '{"continue": true}'; exit 0; }

# 只拦截 Edit/Write
[[ "$TOOL_NAME" =~ ^(Edit|Write)$ ]] || { echo '{"continue": true}'; exit 0; }

# ─── 提取目标文件路径 ───
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    fp = data.get('file_path', data.get('tool_input', {}).get('file_path', ''))
    print(fp)
except:
    pass
" 2>/dev/null)

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

# ─── 读取 scope 模式列表（跳过注释行和空行） ───
SCOPE_PATTERNS=()
while IFS= read -r line || [ -n "$line" ]; do
    trimmed="${line#"${line%%[! ]*}"}"  # 去前导空格
    # 跳过注释行（#开头）和空行
    case "$trimmed" in
        \#*|'') continue ;;
        *) SCOPE_PATTERNS+=("$trimmed") ;;
    esac
done < "$SCOPE_FILE"

# ─── glob 匹配检测 ───
# 计算相对路径: 以 PROJECT_ROOT 为基准
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"
REL_PATH="${REL_PATH#$PROJECT_ROOT}"

IN_SCOPE=false
for pattern in "${SCOPE_PATTERNS[@]}"; do
    # 支持 * 和 ** glob
    # 用 python3 fnmatch 做跨平台 glob 匹配
    MATCH_RESULT=$(${PYTHON_BIN:-python3} -c "
import sys, fnmatch
pattern = '$pattern'
path = '$REL_PATH'
if fnmatch.fnmatch(path, pattern):
    sys.stdout.write('1')
elif fnmatch.fnmatch(path, '*' + pattern):
    sys.stdout.write('1')
elif '/' not in pattern and fnmatch.fnmatch(path.split('/')[-1], pattern):
    sys.stdout.write('1')
else:
    sys.stdout.write('0')
" 2>/dev/null)

    if [ "$MATCH_RESULT" = "1" ]; then
        IN_SCOPE=true
        break
    fi
done

if [ "$IN_SCOPE" = true ]; then
    echo '{"continue": true}'
    exit 0
fi

# ─── 模式检测: 自主模式降级为记录 ───
MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")
if [ "$MODE" != "normal" ]; then
    echo "⚠️ [Scope Gate] ${MODE} mode — 文件 ${FILE_PATH} 超出 current-scope.txt 范围，已记录（模式降级，不阻断）" >&2
    flywheel_event "pretool_scope_gate" "mode_downgrade_${MODE}" "P2" "path=${FILE_PATH}" || true
    echo '{"continue": true}'
    exit 0
fi

# ─── 阻断：超出范围 ───
cat >&2 <<BLOCK
⛔ [Scope Gate] 文件超出 current-scope.txt 声明的范围！

  目标文件: ${FILE_PATH}
  范围文件: ${SCOPE_FILE}

  当前声明的范围模式:
$(for p in "${SCOPE_PATTERNS[@]}"; do echo "    - ${p}"; done)

  哲学 #5(范围冻结): 一次一 Step，非核心 → TODO，越界 → 撤销。

  AI 应:
  1. 将 ${FILE_PATH} 的变更记录到 TODO（如果是当前任务的非核心补充）
  2. 或更新 current-scope.txt 扩展范围（如果确实需要修改此文件）
  3. 或撤销本次操作，专注于 scope 内的文件

BLOCK

flywheel_event "pretool_scope_gate" "blocked_out_of_scope" "P1" "path=${FILE_PATH}" || true
exit 2
