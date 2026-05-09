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

    # 第一步：缓存已存在且非空 → 尝试使用
    if [ -f "$_HC_CACHE" ] && [ -s "$_HC_CACHE" ]; then
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
    python3 - "$_HC_YAML" "$tmp_cache" <<'PYEOF'
import sys, os

yaml_path = sys.argv[1]
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
    lines = []
    for k, v in sorted(data.items()):
        v_escaped = str(v).replace('\n', '\\n')
        lines.append(f"{k}={v_escaped}")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
except Exception as e:
    with open(out_path, 'w') as f:
        f.write('')
    sys.exit(0)
PYEOF

    # 原子替换
    if [ -f "$tmp_cache" ]; then
        mv -f "$tmp_cache" "$_HC_CACHE" 2>/dev/null
        _HC_CACHE_LOADED="ready"
        return 0
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
