#!/usr/bin/env bash
# harness_config.sh — 共享库（非 Hook） — 共享配置库，提供 hc_get/hc_enabled 等 harness.yaml 读取函数
# Role: 共享配置库，提供 hc_get/hc_enabled 等 harness.yaml 读取函数

if [ -z "$_HC_PROJECT_ROOT" ]; then
    HC_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    _HC_PROJECT_ROOT="$(cd "$HC_SCRIPT_DIR/../.." && pwd)"
    _HC_YAML="$_HC_PROJECT_ROOT/.claude/harness.yaml"
    _HC_STATE_DIR="$_HC_PROJECT_ROOT/.omc/state"
    _HC_CACHE="$_HC_STATE_DIR/.harness-cache"
    _HC_CACHE_LOADED=""
fi

# 确保缓存存在且新鲜
_hc_ensure_cache() {
    # 已加载且非空 → 跳过
    [ "$_HC_CACHE_LOADED" = "ready" ] && return 0
    [ "$_HC_CACHE_LOADED" = "empty" ] && return 1

    mkdir -p "$_HC_STATE_DIR" 2>/dev/null

    # 第一步：缓存已存在且非空 → 尝试使用（带 sentinel 完整性检查，防 DG-17 静默失败）
    if [ -f "$_HC_CACHE" ] && [ -s "$_HC_CACHE" ]; then
        # Sentinel 完整性检查：缓存必须含 __parsed_count__ 行
        if grep -q '^__parsed_count__=' "$_HC_CACHE" 2>/dev/null; then
            if [ ! -f "$_HC_YAML" ]; then
                # 无 yaml 但有预先生成的缓存（跨平台 fallback 场景）
                _HC_CACHE_LOADED="ready"
                return 0
            fi
            # 有 yaml：比较修改时间，yaml 不比 cache 新 → 缓存有效
            if [ ! "$_HC_YAML" -nt "$_HC_CACHE" ]; then
                _HC_CACHE_LOADED="ready"
                return 0
            fi
        else
            # 缓存缺少 sentinel — 旧格式或损坏，强制重建
            rm -f "$_HC_CACHE"
        fi
    fi

    # 无 yaml → 标记空缓存（也无预生成缓存），所有 hc_get 返回默认值
    if [ ! -f "$_HC_YAML" ]; then
        _HC_CACHE_LOADED="empty"
        return 1
    fi

    # 需要重建缓存：python3 扁平化 yaml → key=value
    if ! command -v python3 &>/dev/null; then
        _HC_CACHE_LOADED="empty"
        return 1
    fi

    # 写入临时文件再 mv（原子替换，防并发）
    local tmp_cache="${_HC_CACHE}.tmp.$$"
    local min_keys="${HC_MIN_PARSED_KEYS:-50}"
    python3 - "$_HC_YAML" "$tmp_cache" "$min_keys" <<'PYEOF'
import sys, os

yaml_path = sys.argv[1]
min_keys = int(sys.argv[3]) if len(sys.argv) > 2 else 50
out_path = sys.argv[2]

def parse_yaml_simple(path):
    """简单 YAML 解析器：处理 2 层嵌套 + 简单列表（无需 PyYAML）"""
    result = {}
    current_section = ""
    current_list_key = ""
    current_list = []

    with open(path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n\r')
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith('#'):
                # 如果在列表收集中且遇到空行/注释，先结束列表
                if current_list_key and current_list:
                    result[current_list_key] = ' '.join(current_list)
                    current_list_key = ""
                    current_list = []
                continue

            # 检测缩进层级
            indent = len(line) - len(line.lstrip())

            # 列表项（- value）
            if stripped.startswith('- '):
                if current_list_key:
                    item = stripped[2:].strip().strip('"').strip("'")
                    current_list.append(item)
                continue

            # 如果之前在收集列表，现在遇到非列表行，结束列表
            if current_list_key and current_list:
                result[current_list_key] = ' '.join(current_list)
                current_list_key = ""
                current_list = []

            # key: value 对
            if ':' in stripped:
                colon_idx = stripped.index(':')
                key = stripped[:colon_idx].strip()
                value = stripped[colon_idx+1:].strip()

                # 去除引号
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]

                if indent == 0:
                    # 顶层 section
                    if value:
                        result[key] = value
                    else:
                        current_section = key
                elif indent > 0 and current_section:
                    flat_key = f"{current_section}.{key}"
                    if value:
                        result[flat_key] = value
                    else:
                        # 下一行可能是列表
                        current_list_key = flat_key
                        current_list = []

    # 文件末尾如果还在收集列表
    if current_list_key and current_list:
        result[current_list_key] = ' '.join(current_list)

    return result

try:
    data = parse_yaml_simple(yaml_path)
    n_keys = len(data)

    # 解析完整性门禁：key 数量必须 >= 最小阈值，防止 YAML 格式损坏导致静默空缓存
    if n_keys < min_keys:
        sys.stderr.write(f"[harness_config] YAML 解析疑似失败: {n_keys} keys < {min_keys} 阈值。"
                         f"请检查 {yaml_path} 是否为多行 YAML 格式。\n")
        sys.stderr.write(f"[harness_config] 当前缓存将标记为不可用，所有 hc_get 返回默认值。\n")
        with open(out_path, 'w') as f:
            f.write('')
        sys.exit(1)

    lines = [f"__parsed_count__={n_keys}"]
    for k, v in sorted(data.items()):
        v_escaped = str(v).replace('\n', '\\n')
        lines.append(f"{k}={v_escaped}")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
except Exception as e:
    sys.stderr.write(f"[harness_config] 解析异常: {e}\n")
    with open(out_path, 'w') as f:
        f.write('')
    sys.exit(0)
PYEOF

	    # 原子替换（带完整性验证：必须含 __parsed_count__ sentinel，防 DG-17 YAML 解析静默失败）
	    if [ -f "$tmp_cache" ] && [ -s "$tmp_cache" ]; then
	        if grep -q '^__parsed_count__=' "$tmp_cache" 2>/dev/null; then
	            mv -f "$tmp_cache" "$_HC_CACHE" 2>/dev/null
	            _HC_CACHE_LOADED="ready"
	            return 0
	        else
	            echo "[harness_config] 缓存完整性失败 — 缺少 __parsed_count__ sentinel，YAML 解析可能异常" >&2
	            rm -f "$tmp_cache"
	            _HC_CACHE_LOADED="empty"
	            return 1
	        fi
	    else
	        _HC_CACHE_LOADED="empty"
	        return 1
	    fi
}

# hc_get "section.key" "default" — 读标量
hc_get() {
    local key="$1"
    local default="$2"

    if ! _hc_ensure_cache; then
        echo "$default"
        return
    fi

    local value
    value=$(grep -m1 "^${key}=" "$_HC_CACHE" 2>/dev/null | cut -d'=' -f2-)
    if [ -n "$value" ]; then
        echo "$value"
    else
        echo "$default"
    fi
}

# hc_get_list "section.key" "default1 default2" — 读列表（空格分隔）
hc_get_list() {
    local key="$1"
    local default="$2"

    if ! _hc_ensure_cache; then
        echo "$default"
        return
    fi

    local value
    value=$(grep -m1 "^${key}=" "$_HC_CACHE" 2>/dev/null | cut -d'=' -f2-)
    if [ -n "$value" ]; then
        echo "$value"
    else
        echo "$default"
    fi
}

# hc_enabled "feature_name" — 检查 feature 是否启用（默认 true）
# 先查 hooks_enabled.{name}（自动 hyphen→underscore 转换），
# 再查 skills_enabled.{name}（原生名称），均不存在返回 true
hc_enabled() {
    local feature_name="$1"
    local val

    # 检查 hooks_enabled.{name}（harness.yaml 使用下划线，自动转换 hyphen→underscore）
    local hook_key="${feature_name//-/_}"
    val=$(hc_get "hooks_enabled.${hook_key}" "")
    if [ -n "$val" ]; then
        [ "$val" = "true" ]
        return $?
    fi

    # 检查 skills_enabled.{name}（skills 使用原生名称，无转换）
    val=$(hc_get "skills_enabled.${feature_name}" "")
    if [ -n "$val" ]; then
        [ "$val" = "true" ]
        return $?
    fi

    # 默认启用
    return 0
}

# hc_hook_enabled "hook_name" — 仅检查 hooks_enabled（默认 true，自动 hyphen→underscore）
hc_hook_enabled() {
    local hook_name="$1"
    local hook_key="${hook_name//-/_}"
    local val
    val=$(hc_get "hooks_enabled.${hook_key}" "true")
    [ "$val" = "true" ]
}

# hc_skill_enabled "skill_name" — 仅检查 skills_enabled（默认 true，原生名称）
hc_skill_enabled() {
    local skill_name="$1"
    local val
    val=$(hc_get "skills_enabled.${skill_name}" "true")
    [ "$val" = "true" ]
}

# hc_project_root — 返回项目根目录
hc_project_root() {
    echo "$_HC_PROJECT_ROOT"
}

# hc_state_dir — 返回状态目录
hc_state_dir() {
    echo "$_HC_STATE_DIR"
}

# ══════════════════════════════════════════════════════════════════
# 模式检测: Ghost Mode / Goal Mode 统一入口
# ══════════════════════════════════════════════════════════════════
# 返回值:
#   "ghost"      — ghost mode 激活未过期（lx-ghost 方向驱动探索）
#   "goal"       — goal mode 激活未过期（lx-goal 目标驱动执行）
#   "normal"     — 无激活模式
#
# 优先级: ghost > goal > normal
# 新文件格式: lx-ghost.json / lx-goal.json
# 旧文件兼容: ghost-mode.json / ghost-mode.active / unattended-mode.json / .unattended-mode
# lx-ghost vs lx-goal: ghost = 方向驱动（开放探索）, goal = 目标驱动（具体任务）

is_mode_active() {
    local state_dir="$1"
    [ -z "$state_dir" ] && state_dir="${_HC_STATE_DIR:-.omc/state}"
    mkdir -p "$state_dir" 2>/dev/null
    local now_epoch
    now_epoch=$(date +%s 2>/dev/null || echo 0)

    # ── 检查 lx-ghost mode（新格式）──
    local ghost_new="$state_dir/lx-ghost.json"
    if [ -f "$ghost_new" ]; then
        local expired
        expired=$(python3 -c "
import json, sys
try:
    d = json.load(open('$ghost_new'))
    expires = d.get('expires_at', '')
    if not expires:
        print('active')
    else:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < exp:
            print('active')
        else:
            print('expired')
except Exception:
    print('invalid')" 2>/dev/null || echo 'invalid')
        case "$expired" in
            active) echo "ghost"; return ;;
            expired) rm -f "$ghost_new" 2>/dev/null ;;
        esac
    fi

    # ── 检查旧格式 ghost-mode.json（后向兼容）──
    local ghost_old="$state_dir/ghost-mode.json"
    if [ -f "$ghost_old" ]; then
        local expired
        expired=$(python3 -c "
import json, sys
try:
    d = json.load(open('$ghost_old'))
    expires = d.get('expires_at', '')
    if not expires:
        print('active')
    else:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < exp:
            print('active')
        else:
            print('expired')
except Exception:
    print('invalid')" 2>/dev/null || echo 'invalid')
        case "$expired" in
            active) echo "ghost"; return ;;
            expired) rm -f "$ghost_old" 2>/dev/null ;;
        esac
    fi

    # ── 兼容旧 ghost-mode.active（纯文件标记）──
    if [ -f "$state_dir/ghost-mode.active" ]; then
        echo "ghost"
        return
    fi

    # ── 检查 lx-goal mode（新格式）──
    local goal_new="$state_dir/lx-goal.json"
    if [ -f "$goal_new" ]; then
        local expired
        expired=$(python3 -c "
import json, sys
try:
    d = json.load(open('$goal_new'))
    expires = d.get('expires_at', '')
    if not expires:
        print('active')
    else:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < exp:
            print('active')
        else:
            print('expired')
except Exception:
    print('invalid')" 2>/dev/null || echo 'invalid')
        case "$expired" in
            active) echo "goal"; return ;;
            expired) rm -f "$goal_new" 2>/dev/null ;;
        esac
    fi

    # ── 检查旧格式 unattended-mode.json（后向兼容）──
    local goal_old="$state_dir/unattended-mode.json"
    if [ -f "$goal_old" ]; then
        local expired
        expired=$(python3 -c "
import json, sys
try:
    d = json.load(open('$goal_old'))
    expires = d.get('expires_at', '')
    if not expires:
        print('active')
    else:
        from datetime import datetime
        exp = datetime.fromisoformat(expires)
        if datetime.now() < exp:
            print('active')
        else:
            print('expired')
except Exception:
    print('invalid')" 2>/dev/null || echo 'invalid')
        case "$expired" in
            active) echo "goal"; return ;;
            expired) rm -f "$goal_old" 2>/dev/null ;;
        esac
    fi

    # ── 兼容旧 .unattended-mode（纯文件标记）──
    if [ -f "$state_dir/.unattended-mode" ]; then
        echo "goal"
        return
    fi

    echo "normal"
}

# ══════════════════════════════════════════════════════════════════
# 模式状态更新: lx-ghost.json / lx-goal.json 原子写入
# ══════════════════════════════════════════════════════════════════

# _mode_file_for <state_dir> <mode>
# 返回模式状态文件路径，兼容新旧命名。
# 新格式: ghost → lx-ghost.json, goal → lx-goal.json
# 旧格式: ghost → ghost-mode.json, unattended → unattended-mode.json（回退）
_mode_file_for() {
    local state_dir="$1" mode="$2"
    case "$mode" in
        ghost) echo "$state_dir/lx-ghost.json" ;;
        goal)  echo "$state_dir/lx-goal.json" ;;
        unattended) echo "$state_dir/unattended-mode.json" ;;
        *)     echo "$state_dir/${mode}-mode.json" ;;
    esac
}

# _mode_append_to_list <state_dir> <mode> <field> <json_value>
# 原子追加 JSON 值到模式状态文件的列表字段。使用 tmp+rename 防止并发读取不一致。
# 示例: _mode_append_to_list "$STATE_DIR" "ghost" "skipped_risks" '{"type":"rm -rf","command":"rm -rf /tmp","timestamp":"2026-05-11T12:00:00"}'
_mode_append_to_list() {
    local state_dir="$1" mode="$2" field="$3" json_value="$4"
    local file="$(_mode_file_for "$state_dir" "$mode")"
    [ ! -f "$file" ] && return 1
    python3 -c "
import json, os
file = '$file'
field = '$field'
try:
    value = json.loads('$json_value')
except:
    value = '$json_value'
try:
    d = json.load(open(file))
except:
    d = {}
lst = d.get(field, [])
lst.append(value)
d[field] = lst
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null || true
}

# _mode_increment_field <state_dir> <mode> <field>
# 原子递增模式状态文件的数字字段。
_mode_increment_field() {
    local state_dir="$1" mode="$2" field="$3"
    local file="$(_mode_file_for "$state_dir" "$mode")"
    [ ! -f "$file" ] && return 1
    python3 -c "
import json, os
file = '$file'
field = '$field'
try:
    d = json.load(open(file))
except:
    d = {}
d[field] = d.get(field, 0) + 1
tmp = file + '.tmp.' + str(os.getpid())
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.rename(tmp, file)
" 2>/dev/null || true
}

# ── Safe JSON hook response construction ──
# Usage: echo "$message" | hc_emit_hook_json ["hookEventName"] ["true|false"]
# Reads message from stdin (binary-safe), outputs complete JSON hook response.
# Uses python3 json.dumps for proper escaping — handles quotes, backslashes,
# control chars, and invalid UTF-8 (replaced with U+FFFD).
# Pattern proven at context-guard.sh:120 and error-dna.sh:432.
hc_emit_hook_json() {
    export _HC_EVENT_NAME="${1:-PostToolUse}"
    export _HC_CONTINUE_VAL="${2:-true}"
    python3 -c "
import os, sys, json
event = os.environ.get('_HC_EVENT_NAME', 'PostToolUse')
continue_val = os.environ.get('_HC_CONTINUE_VAL', 'true')
text = sys.stdin.buffer.read().decode('utf-8', errors='replace')
result = {
    'continue': continue_val == 'true',
    'hookSpecificOutput': {
        'hookEventName': event,
        'additionalContext': text.strip()
    }
}
print(json.dumps(result, ensure_ascii=False))
"
}

# ── UTF-8 sanitization pipe ──
# Usage: cat "$file" | hc_sanitize_utf8
# Replaces invalid UTF-8 bytes with U+FFFD, strips lone surrogates.
hc_sanitize_utf8() {
    python3 -c "
import sys
text = sys.stdin.buffer.read().decode('utf-8', errors='replace')
# Strip lone surrogates (U+D800..U+DFFF) — they are valid Unicode code
# points but NOT valid characters.  Python's UTF-8 decoder rejects their
# byte encoding (W3C spec), but they can appear after intermediate steps
# that roundtrip through text, and they break json.dumps / API JSON parsers.
text = ''.join(c for c in text if not 0xD800 <= ord(c) <= 0xDFFF)
sys.stdout.write(text)
"
}

# ── Flywheel event logging (for ROI measurement) ──
# Usage: flywheel_event "hook_name" "event_type" ["severity" ["project"]]
# Logs structured event to ~/.claude/flywheel.log when a hook takes MEANINGFUL action.
# Call on blocks / warnings / detections — NOT on every passive invocation.
flywheel_event() {
    local hook_name="${1:-unknown}"
    local event_type="${2:-triggered}"
    local severity="${3:-P2}"
    local project="${4:-carror-os}"
    local flywheel_log="${HOME}/.claude/flywheel.log"
    echo "$(date +%Y-%m-%d),${hook_name}_${event_type},${severity},${project}" >> "$flywheel_log" 2>/dev/null || true
}
