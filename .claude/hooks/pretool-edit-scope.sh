#!/usr/bin/env bash
# pretool-edit-scope.sh — PreToolUse:Edit|Write — 范围管理 + 规则锚定 + completion-blocked 提醒 (DG-131)
# Role: 范围文件匹配 + 自动加入 + 核心文件警告 + 长对话规则锚定 + 无证据完成提醒
# Known limit: DG-131 completion-blocked 仅覆盖 Edit|Write，Bash sed/echo 可绕过（设计取舍，误杀率过高）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_edit_scope" || { echo '{"continue": true}'; exit 0; }
INPUT=$(cat)

# ─── DG-131: completion-blocked 最小范围阻断 ───
# pre-completion-gate 拦截无证据完成声明后，写入 completion-blocked 状态文件
# 本段在后续 Edit/Write 时检测该状态，阻断 1-2 轮强制 AI 处理证据问题
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BLOCKED_FILE="$PROJECT_ROOT/.omc/state/completion-blocked"
if [ -f "$BLOCKED_FILE" ]; then
    BLOCK_INFO=$(${PYTHON_BIN:-python3} -c "
import json, time
try:
    with open('$BLOCKED_FILE') as f:
        data = json.load(f)
    age = time.time() - data.get('blocked_at', 0)
    count = data.get('block_count', 0)
    # >5min or >=2 blocks → auto-clear (anti-deadlock)
    if age > 300 or count >= 2:
        print('CLEAR')
    else:
        data['block_count'] = count + 1
        with open('$BLOCKED_FILE', 'w') as f:
            json.dump(data, f)
        print(f'BLOCK:{count+1}')
except:
    print('CLEAR')" 2>/dev/null || echo "CLEAR")
    case "$BLOCK_INFO" in
        CLEAR)
            rm -f "$BLOCKED_FILE" 2>/dev/null || true
            ;;
        BLOCK:*)
            BLOCK_COUNT="${BLOCK_INFO#BLOCK:}"
            flywheel_event "pretool_edit_scope" "completion_blocked_turn${BLOCK_COUNT}" "P2" || true
            printf '{"continue": true, "additionalContext": "⚠️ [completion-blocked·第%s轮] Reminder: you tried to mark TaskUpdate(completed) without VERIFIED evidence.\\nPlease: (1) run a verification command (2) cite output with VERIFIED: [已测试: ...] tag (3) retry TaskUpdate(completed).\\nNote: pre-completion-gate still hard-blocks TaskUpdate(completed). This Edit/Write warning stops after 2 rounds, but evidence is required to mark complete."}' "$BLOCK_COUNT"
            exit 0
            ;;
    esac
fi
# ─── end completion-blocked ───

# 解析 file_path
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('filePath', data.get('tool_input', {}).get('file_path', '')))
except:
    pass" 2>/dev/null)
fi

# 任何解析错误 → fail-open
[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }
BASENAME=$(basename "$FILE_PATH")

# 保护文件警告（仅 stderr，不阻断）
PROTECTED=$(hc_get "protected_files.warn_on_edit" "package.json go.mod Cargo.toml main.go pom.xml")
set -f
for f in $PROTECTED; do
    if [ "$BASENAME" = "$f" ]; then
flywheel_event "pretool_edit_scope" "protected_file_warn" "P2" || true
        echo "⚠️ 正在编辑核心文件: ${BASENAME}。请确认已声明影响范围并获得用户确认(§6.2)。" >&2
        break
    fi
done
set +f

# 范围冻结检查
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCOPE_FILE="$PROJECT_ROOT/.omc/state/current-scope.txt"

# ─── 规则锚定提醒函数（合并自 pretool-rule-anchor.sh）───
rule_anchor_check() {
    local turn_file="$PROJECT_ROOT/.omc/state/session-turns.json"
    [ ! -f "$turn_file" ] && return
    local current_turn=0
    if command -v jq &>/dev/null; then
        current_turn=$(jq -r '.count // 0' "$turn_file" 2>/dev/null || echo 0)
    else
        current_turn=$(grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' "$turn_file" 2>/dev/null | sed 's/.*:[[:space:]]*//' | head -1)
        [ -z "$current_turn" ] && current_turn=0
    fi
    [[ "$current_turn" =~ ^[0-9]+$ ]] || current_turn=0

    local threshold=$(hc_get "rule_anchor.turn_threshold" "15")
    local interval=$(hc_get "rule_anchor.interval" "5")
    [ "$current_turn" -lt "$threshold" ] && return
    local offset=$(( current_turn - threshold ))
    [ "$interval" -gt 0 ] && [ $(( offset % interval )) -ne 0 ] && return

    # 检测漂移信号词
    local last_prompt="$PROJECT_ROOT/.omc/state/.last-user-prompt"
    local drift_detected=false
    if [ -f "$last_prompt" ]; then
        for word in "顺手" "顺便" "另外也" "同时也" "顺带" "捎带"; do
            grep -qF "$word" "$last_prompt" 2>/dev/null && { drift_detected=true; break; }
        done
    fi

    if [ "$drift_detected" = true ]; then
        echo "⚠️ [第${current_turn}轮·漂移预警] 检测到范围扩展词。只改当前任务文件，额外问题记 TODO。" >&2
    else
        echo "📌 [第${current_turn}轮·规则锚定] 长会话提醒：①file:line ②VERIFIED证据 ③git批准 ④范围冻结 ⑤3轮上限 ⑥改动可追溯" >&2
    fi
}

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
    COUPLED=$(${PYTHON_BIN:-python3} - "$edit_file" "$COUPLING_MAP" <<'PYEOF'
import json, sys
edit_file = sys.argv[1]
coupling_path = sys.argv[2]
try:
    with open(coupling_path, encoding="utf-8") as f:
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

# 无范围文件 → 尝试自动推导（仅输出提醒，不创建 scope 文件）
# 原则：无 scope = 放行。auto-scope 不应本末倒置产生 scope 封锁。

# Goal/Ghost 模式检测 — 无人值守时范围自动扩展但有迹可查
MODE="normal"
if [ -f "$PROJECT_ROOT/.omc/state/tokens/lx-goal.json" ]; then MODE="goal"; fi
if [ -f "$PROJECT_ROOT/.omc/state/tokens/lx-ghost.json" ]; then MODE="ghost"; fi

if [ ! -f "$SCOPE_FILE" ]; then
    AUTO_SCOPE="$PROJECT_ROOT/.claude/scripts/auto-scope.sh"
    if [ -f "$AUTO_SCOPE" ]; then
        # 仅输出提醒，不创建 scope 文件
        AUTO_MSG=$(bash "$AUTO_SCOPE" 2>&1 || true)
        echo "ℹ️  auto-scope: $AUTO_MSG" >&2
    fi
    REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"
    coupling_remind "$REL_PATH" "$PROJECT_ROOT" 2>&1
    rule_anchor_check
    # session-edit-log：跳过 /tmp/ 临时文件
    case "$REL_PATH" in /tmp/*) ;; *)
		    echo "$REL_PATH" >> "$PROJECT_ROOT/.omc/state/session-edit-log.txt" 2>/dev/null || true
		;; esac
    echo '{"continue": true}'
    exit 0
fi

# 转为相对路径
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# 逐行 glob 匹配
while IFS= read -r pattern || [ -n "$pattern" ]; do
    [ -z "$pattern" ] && continue
    # 同时匹配 REL_PATH（全路径）和 BASENAME（文件名），解决 auto-scope 只生成 basename 的问题
    [[ "$REL_PATH" == $pattern || "$BASENAME" == $pattern ]] && {
        coupling_remind "$REL_PATH" "$PROJECT_ROOT" 2>&1
        rule_anchor_check
        # Record to session edit log
        # session-edit-log：跳过 /tmp/ 临时文件
    case "$REL_PATH" in /tmp/*) ;; *)
		    echo "$REL_PATH" >> "$PROJECT_ROOT/.omc/state/session-edit-log.txt" 2>/dev/null || true
		;; esac
        echo '{"continue": true}'
        exit 0
    }
done < "$SCOPE_FILE"

# 全部不匹配 → 自动加入 scope（非阻断）+ 耦合提醒
# R40: 从"硬阻断+复制粘贴"改为"自动添加+非阻断提醒"
# 用户预期是"AI 直接改文件"，不需要理解 scope 概念
coupling_remind "$REL_PATH" "$PROJECT_ROOT"
if [ "$MODE" != "normal" ]; then
    flywheel_event "pretool_edit_scope" "scope_autoexpand_${MODE}" "P3" "file=$REL_PATH" || true
    echo "ℹ️ [scope|${MODE}] ${REL_PATH} 自动加入编辑范围（无人值守模式，范围自动扩展）" >&2
else
    echo "ℹ️ [scope] ${REL_PATH} 自动加入编辑范围（之前未在 scope 中）" >&2
fi
echo "$REL_PATH" >> "$SCOPE_FILE" 2>/dev/null || true
# session-edit-log：跳过 /tmp/ 临时文件
case "$REL_PATH" in /tmp/*) ;; *)
    echo "$REL_PATH" >> "$PROJECT_ROOT/.omc/state/session-edit-log.txt" 2>/dev/null || true
;; esac
rule_anchor_check
echo '{"continue": true}'
exit 0
