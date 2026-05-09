#!/usr/bin/env bash
# pretool-edit-scope.sh — PreToolUse:Edit|Write — 范围冻结拦截，阻止越界编辑 + 核心文件警告
# Role: 范围冻结拦截，阻止越界编辑 + 核心文件警告

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_edit_scope" || exit 0
INPUT=$(cat)

# 解析 file_path
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

# 任何解析错误 → fail-open
[ -z "$FILE_PATH" ] && exit 0
BASENAME=$(basename "$FILE_PATH")

# 保护文件警告（仅 stderr，不阻断）
PROTECTED=$(hc_get "protected_files.warn_on_edit" "package.json go.mod Cargo.toml main.go pom.xml")
for f in $PROTECTED; do
    if [ "$BASENAME" = "$f" ]; then
        echo "⚠️ 正在编辑核心文件: ${BASENAME}。请确认已声明影响范围并获得用户确认(§6.2)。" >&2
        break
    fi
done

# 范围冻结检查
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCOPE_FILE="$PROJECT_ROOT/.omc/state/current-scope.txt"

# ─── 耦合提醒函数（定义在调用之前）───
coupling_remind() {
    local edit_file="$1"
    local proj_root="$2"
    local coupling_enabled
    coupling_enabled=$(hc_get "coupling.enabled" "true")
    [ "$coupling_enabled" != "true" ] && return

    local COUPLING_MAP="$proj_root/.omc/state/coupling-map.json"
    [ ! -f "$COUPLING_MAP" ] && return

    local COUPLED
    COUPLED=$(python3 - "$edit_file" "$COUPLING_MAP" <<'PYEOF'
import json, sys
edit_file = sys.argv[1]
coupling_path = sys.argv[2]
try:
    with open(coupling_path) as f:
        data = json.load(f)
    source = data.get("source", "git_co_change")
    file_coupling = data.get("file_coupling", {})
    coupled = file_coupling.get(edit_file, [])
    if not coupled:
        for key in file_coupling:
            if key.lstrip('./') == edit_file.lstrip('./'):
                coupled = file_coupling[key]
                break
    if coupled:
        if source == "static_import_analysis":
            lines = []
            for e in coupled[:5]:
                reason = e.get("reason", "")
                label = f"({reason})" if reason else ""
                lines.append(f" - {e['file']} {label}")
            print("\n".join(lines))
        else:
            files = [f"{e['file']}({e['count']}次)" for e in coupled[:5]]
            print(", ".join(files))
except:
    pass
PYEOF
    2>/dev/null)

    if [ -n "$COUPLED" ]; then
        if echo "$COUPLED" | grep -q "^ - "; then
            # static_import_analysis: multi-line format
            echo "[耦合提醒] 编辑 ${edit_file} 时，以下文件可能需要同步检查:" >&2
            echo "$COUPLED" >&2
        else
            # git_co_change: single-line format
            echo "[耦合提醒] ${edit_file} 历史上常与以下文件一起变更: ${COUPLED}" >&2
        fi
    fi
}

# 无范围文件 → 仅输出耦合提醒后放行
if [ ! -f "$SCOPE_FILE" ]; then
    REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"
    coupling_remind "$REL_PATH" "$PROJECT_ROOT" 2>&1
    exit 0
fi

# 转为相对路径
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# 逐行 glob 匹配
while IFS= read -r pattern || [ -n "$pattern" ]; do
    [ -z "$pattern" ] && continue
    [[ "$REL_PATH" == $pattern ]] && { coupling_remind "$REL_PATH" "$PROJECT_ROOT" 2>&1; exit 0; }
done < "$SCOPE_FILE"

# 全部不匹配 → 输出耦合提醒后阻断
coupling_remind "$REL_PATH" "$PROJECT_ROOT"
SCOPE_CONTENT=$(tr '\n' ' ' < "$SCOPE_FILE")
echo "echo '${REL_PATH}' >> ${SCOPE_FILE}    # Scope Gate: 需要你批准才能将 ${REL_PATH} 加入编辑允许范围" >&2
exit 2
