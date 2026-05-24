#!/usr/bin/env bash
# feature-probe.sh — 工具脚本（非 Hook） — 手动诊断工具，检查 feature 的 L1-L4 证据链完整性
# Role: 手动诊断工具，检查 feature 的 L1-L4 证据链完整性

HC_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$HC_SCRIPT_DIR/../.." && pwd)"
FEATURE_REGISTRY="$PROJECT_ROOT/.claude/feature-registry.yaml"

# 导入 harness_config.sh
source "$HC_SCRIPT_DIR/harness_config.sh"
set -f

usage() {
    echo "Usage: $0 <feature_name> [--json]"
    echo "Probe a registered feature (hook or skill) and output L1-L4 evidence."
    exit 1
}

# 解析参数
FEATURE_NAME="$1"
OUTPUT_JSON=false
[ "$2" = "--json" ] && OUTPUT_JSON=true

[ -z "$FEATURE_NAME" ] && usage

# -----------------------------------------------
# 探针检查函数
# -----------------------------------------------

# 检查 hook 脚本是否存在
_hook_scripts() {
    local name="$1"
    # 转换横线：completion_gate → completion-gate
    local dashed="${name//_/-}"
    # 同时支持横线名和下划线名
    local scripts
    scripts=$(ls "$HC_SCRIPT_DIR/${dashed}.sh" "$HC_SCRIPT_DIR/${name}.sh" 2>/dev/null | head -1)
    echo "$scripts"
}

# 检查 skill 目录是否存在
_skill_dir() {
    local name="$1"
    local dir="$PROJECT_ROOT/.claude/skills/$name"
    [ -d "$dir" ] && echo "$dir" && return 0
    echo ""
}

# 检查 SKILL.md 是否存在
_skill_skillmd() {
    local name="$1"
    local file="$PROJECT_ROOT/.claude/skills/$name/SKILL.md"
    [ -f "$file" ] && echo "$file" && return 0
    echo ""
}

# 检查 skill 是否有 scripts/ 目录
_skill_scripts() {
    local name="$1"
    local dir="$PROJECT_ROOT/.claude/skills/$name/scripts"
    [ -d "$dir" ] && ls "$dir"/*.py "$dir"/*.sh 2>/dev/null | head -3 || echo ""
}

# 检查 feature 是否在 registry 中注册
_registry_enabled() {
    local name="$1"
    if command -v python3 &>/dev/null && [ -f "$FEATURE_REGISTRY" ]; then
        ${PYTHON_BIN:-python3} -c "
import yaml, sys
with open('$FEATURE_REGISTRY') as f:
    data = yaml.safe_load(f)
name = '$name'
for hook in data.get('hooks', []):
    if hook.get('name') == name:
        print(hook.get('enabled_by_default', True))
        sys.exit(0)
for skill in data.get('skills', []):
    if skill.get('name') == name:
        print(skill.get('enabled_by_default', True))
        sys.exit(0)
print('True')
" 2>/dev/null || echo "True"
    else
        echo "True"
    fi
}

# 检查 harness 中是否启用
_harness_enabled() {
    hc_enabled "$1" && echo "true" || echo "false"
}

# bash 语法检查（仅 .sh 文件）
_bash_syntax() {
    local file="$1"
    [ -z "$file" ] && echo "N/A" && return
    bash -n "$file" 2>&1 | head -3
    echo "$?"
}

# -----------------------------------------------
# 主探针逻辑
# -----------------------------------------------

probe() {
    local name="$1"

    # ---- L4: 注册存在性 ----
    local l4=""
    if command -v python3 &>/dev/null && [ -f "$FEATURE_REGISTRY" ]; then
        if ${PYTHON_BIN:-python3} -c "
import yaml, sys
with open('$FEATURE_REGISTRY') as f:
    data = yaml.safe_load(f)
name = '$name'
found = False
for hook in data.get('hooks', []):
    if hook.get('name') == name:
        found = True
        break
for skill in data.get('skills', []):
    if skill.get('name') == name:
        found = True
        break
sys.exit(0 if found else 1)
" 2>/dev/null; then
            l4="PASS"
        else
            l4="NOT_REGISTERED (feature not found in registry)"
        fi
    else
        l4="NOT_TESTABLE (${PYTHON_BIN:-python3} or registry missing)"
    fi

    # ---- L3: 文件存在 + 语法 ----
    local hook_script
    hook_script=$(_hook_scripts "$name")
    local skill_dir
    skill_dir=$(_skill_dir "$name")
    local skill_md
    skill_md=$(_skill_skillmd "$name")

    local file_exists=false
    local syntax_check="N/A"
    local file_path=""

    if [ -n "$hook_script" ]; then
        file_exists=true
        file_path="$hook_script"
        syntax_check=$(_bash_syntax "$hook_script")
    elif [ -n "$skill_md" ]; then
        file_exists=true
        file_path="$skill_md"
        syntax_check="SKILL.md (text)"
    elif [ -n "$skill_dir" ]; then
        file_exists=true
        file_path="$skill_dir"
        syntax_check="SKILL.md not found in $skill_dir"
    else
        file_exists=false
        file_path=""
        syntax_check="NOT_FOUND"
    fi

    local l3=""
    if [ "$file_exists" = true ] && [ -z "$syntax_check" ]; then
        l3="PASS (${file_path})"
    elif [ "$file_exists" = true ] && [ "$syntax_check" = "SKILL.md (text)" ]; then
        l3="PASS (${file_path})"
    elif [ "$file_exists" = true ]; then
        l3="SYNTAX_ERROR (${syntax_check})"
    else
        l3="NOT_FOUND"
    fi

    # ---- L2: harness 中启用状态 ----
    local harness_val
    harness_val=$(_harness_enabled "$name")
    local l2=""
    if [ "$harness_val" = "true" ]; then
        l2="ENABLED in harness.yaml"
    else
        l2="DISABLED in harness.yaml"
    fi

    # ---- L1: 完整功能验证（仅对已知的可执行 feature 进行） ----
    local l1=""
    if [ -n "$hook_script" ] && [ -z "$syntax_check" ]; then
        # source 执行 hook 的 exit code（不带参数，预期 exit 0 或 exit 2）
        bash "$hook_script" 2>/dev/null
        local exit_code=$?
        if [ "$exit_code" -eq 0 ] || [ "$exit_code" -eq 2 ]; then
            l1="PASS (executable, exit=$exit_code)"
        else
            l1="UNEXPECTED_EXIT (exit=$exit_code)"
        fi
    elif [ -n "$skill_md" ]; then
        l1="MANUAL (SKILL.md requires AI context, not auto-testable)"
    else
        l1="NOT_TESTABLE"
    fi

    # ---- 汇总 ----
    cat <<RESULT
FEATURE: $name
  L1 (functional):   $l1
  L2 (config):       $l2
  L3 (file+compile): $l3
  L4 (registered):   $l4
RESULT
}

probe_json() {
    local name="$1"

    local hook_script
    hook_script=$(_hook_scripts "$name")
    local skill_dir
    skill_dir=$(_skill_dir "$name")
    local skill_md
    skill_md=$(_skill_skillmd "$name")
    local harness_val
    harness_val=$(_harness_enabled "$name")

    # L1
    local l1="NOT_TESTABLE"
    if [ -n "$hook_script" ]; then
        bash "$hook_script" 2>/dev/null
        local exit_code=$?
        if [ "$exit_code" -eq 0 ] || [ "$exit_code" -eq 2 ]; then
            l1="PASS"
        else
            l1="UNEXPECTED_EXIT"
        fi
    elif [ -n "$skill_md" ]; then
        l1="MANUAL"
    fi

    # L3 path
    local l3_path=""
    [ -n "$hook_script" ] && l3_path="$hook_script"
    [ -z "$l3_path" ] && [ -n "$skill_md" ] && l3_path="$skill_md"
    [ -z "$l3_path" ] && [ -n "$skill_dir" ] && l3_path="$skill_dir"

    ${PYTHON_BIN:-python3} -c "
import json

# L4 registry check
import yaml, sys
registered = False
try:
    with open('$FEATURE_REGISTRY') as f:
        data = yaml.safe_load(f)
    name = '$name'
    for hook in data.get('hooks', []):
        if hook.get('name') == name:
            registered = True
            break
    for skill in data.get('skills', []):
        if skill.get('name') == name:
            registered = True
            break
except:
    pass

result = {
    'feature': '$name',
    'evidence': {
        'L1': '$l1',
        'L2': '${harness_val}',
        'L3': '${l3_path}',
        'L4': 'REGISTERED' if registered else 'NOT_REGISTERED'
    }
}
json.dump(result, sys.stdout, indent=2)
print()
"
}

# 执行探针
if [ "$OUTPUT_JSON" = true ]; then
    probe_json "$FEATURE_NAME"
else
    probe "$FEATURE_NAME"
fi
