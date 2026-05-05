#!/usr/bin/env bash
# race_manager.sh — Race 蜂群协调引擎
#
# 跨平台: Claude Code / OpenCode / Codex CLI / Gemini CLI / Qwen Code / Cursor
# 所有平台均支持: bash + 文件 I/O → race_manager.sh 全平台通用
# Claude Code 额外支持: Task()/TeamCreate 子 Agent 派发 (由 lx-race SKILL.md 处理)
#
# Race = 蜂群协调层 (Swarm Coordination)
#   - register:   注册子任务到 Race 状态树 (全平台)
#   - dispatch:   派发策略因平台而异 (由 lx-race SKILL.md 定义)
#   - collect:    轮询 result.json 收集结果 (全平台)
#   - report:     聚合报告 (全平台)
#
# 与 OMA Lock 协同: race 不建写锁, worker 写文件时 pretool-write-lock.sh 自动加锁
#
# Usage:
#   bash race_manager.sh init <id> [task_description]
#   bash race_manager.sh start <id>
#   bash race_manager.sh register <parent> --subtasks A,B,C [--desc "parent task"]
#   bash race_manager.sh status <id> [--all] [--json]
#   bash race_manager.sh complete <id> <status> [output]
#   bash race_manager.sh report <id>
#   bash race_manager.sh list [--json]
#   bash race_manager.sh clean [id]

set -euo pipefail

# Per-invocation temp dir (auto-cleaned on exit)
_RACE_TMPDIR=""
_cleanup() {
    [ -n "$_RACE_TMPDIR" ] && [ -d "$_RACE_TMPDIR" ] && rm -rf "$_RACE_TMPDIR"
}
trap _cleanup EXIT
_mktmp() {
    [ -z "$_RACE_TMPDIR" ] && _RACE_TMPDIR="$(mktemp -d)"
    mktemp -p "$_RACE_TMPDIR"
}

# ---------------------------------------------------------------------------
# Path initialization
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RACE_DIR="$PROJECT_ROOT/.omc/race"

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
usage() {
    cat <<USAGE
Race Manager — 蜂群协调引擎

Commands:
  init      race_manager.sh init <id> [task_description]
            Create a flat race workspace at .omc/race/<id>/

  start     race_manager.sh start <id>
            Mark a race as running

  register  race_manager.sh register <parent> --subtasks A,B,C [--desc "..."]
            Create hierarchical race with subtask tracking
            → .omc/race/<parent>/manifest.json + subtasks/*/owner.json

  status    race_manager.sh status <id> [--all] [--json]
            Check race status. --all aggregates subtask progress

  complete  race_manager.sh complete <id> <status> [output]
            Write result.json. status: completed | failed

  report    race_manager.sh report <id>
            Full aggregated report of all subtasks

  list      race_manager.sh list [--json]
            List all races

  clean     race_manager.sh clean [id]
            Remove a specific race or all completed races

Platform dispatch (handled by lx-race SKILL.md, not this script):
  Claude Code:  Task()/TeamCreate → sub-agents write result.json
  Other 5 CLI:  run_in_background / sequential → workers write result.json

OMA Lock: Workers writing shared files → pretool-write-lock.sh auto-locks
USAGE
    exit 1
}

[ $# -lt 1 ] && usage

ACTION="$1"
shift

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

# Write JSON to file using python3 (reliable, no shell escaping issues)
_py_json() {
    local file="$1"
    mkdir -p "$(dirname "$file")"
    python3 -c "
import json, sys, os
data = json.loads(sys.stdin.read())
with open(os.path.expanduser('$file'), 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null || {
    echo "ERROR: failed to write $file" >&2
    return 1
}
}

# Read JSON value from file
_py_read_json() {
    local file="$1"
    local key="$2"
    python3 -c "
import json, sys
with open('$file') as f:
    data = json.load(f)
print(data.get('$key', ''))
" 2>/dev/null || echo ""
}

# Get ISO timestamp
_now() {
    python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))" 2>/dev/null || echo ""
}

# Sanitize race id (plain, no slash)
_sanitize_id() {
    echo "$1" | tr -dc 'a-zA-Z0-9_-'
}

# Sanitize race id allowing / for subtask paths (e.g. parent/subtask)
_sanitize_path_id() {
    local id="$1"
    local result=""
    # Handle empty input
    [ -z "$id" ] && { echo ""; return 0; }
    # Split on / and sanitize each segment
    local parts
    IFS='/' read -ra parts <<< "$id"
    for part in "${parts[@]}"; do
        local safe
        safe="$(echo "$part" | tr -dc 'a-zA-Z0-9_-')"
        [ -z "$safe" ] && { echo ""; return 0; }
        result="${result:+$result/}$safe"
    done
    echo "$result"
    return 0
}

# ---------------------------------------------------------------------------
# Command: init (flat race — original, unchanged)
# ---------------------------------------------------------------------------
cmd_init() {
    local race_id="$1"
    local task_desc="${2:-}"

    if [ -z "$race_id" ]; then
        echo "ERROR: race id is required" >&2
        exit 1
    fi

    local safe_id
    safe_id="$(_sanitize_id "$race_id")"
    if [ "$safe_id" != "$race_id" ]; then
        echo "ERROR: race id contains invalid characters (use a-zA-Z0-9_-)" >&2
        exit 1
    fi

    local race_workspace="$RACE_DIR/$safe_id"
    if [ -d "$race_workspace" ]; then
        echo "ERROR: race '$safe_id' already exists at $race_workspace" >&2
        exit 1
    fi

    mkdir -p "$race_workspace"

    local tmpfile
    tmpfile="$(_mktmp)"
    echo "$task_desc" > "$tmpfile"

    local owner_file="$race_workspace/owner.json"
    local owner="${USER:-unknown}"
    local now_val
    now_val="$(_now)"

    python3 -c "
import json, os
with open(os.path.expanduser('$tmpfile')) as f:
    task = f.read().strip()
data = {
    'race_id': '$safe_id',
    'owner': '$owner',
    'created_at': '$now_val',
    'status': 'init',
    'task': task if task else None
}
with open('$owner_file', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('RACE_INIT:$safe_id:$race_workspace')
"
    rm -f "$tmpfile"
}

# ---------------------------------------------------------------------------
# Command: start
# ---------------------------------------------------------------------------
cmd_start() {
    local race_id="$1"
    local safe_id
    safe_id="$(_sanitize_id "$race_id")"
    if [ "$safe_id" != "$race_id" ] || [ -z "$safe_id" ]; then
        echo "ERROR: race id contains invalid characters (use a-zA-Z0-9_-)" >&2
        exit 1
    fi
    race_id="$safe_id"
    local race_workspace="$RACE_DIR/$race_id"

    if [ ! -d "$race_workspace" ]; then
        echo "ERROR: race '$race_id' not found (run init first)" >&2
        exit 1
    fi

    local ts
    ts="$(_now)"

    # Write result.json via temp+rename for atomicity
    local result_file="$race_workspace/result.json"
    local result_tmp
    result_tmp="$(_mktmp)"
    python3 -c "
import json
data = {
    'race_id': '$race_id',
    'status': 'running',
    'started_at': '$ts',
    'completed_at': None,
    'output': None
}
with open('$result_tmp', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('RACE_START:$race_id')
"
    mv "$result_tmp" "$result_file"

    # Update owner.json via temp+rename
    local owner_file="$race_workspace/owner.json"
    if [ -f "$owner_file" ]; then
        local owner_tmp
        owner_tmp="$(_mktmp)"
        python3 -c "
import json
with open('$owner_file') as f:
    data = json.load(f)
data['status'] = 'running'
with open('$owner_tmp', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
        mv "$owner_tmp" "$owner_file"
    fi
}

# ---------------------------------------------------------------------------
# Command: register (hierarchical — NEW)
# Creates .omc/race/<parent>/
#   ├── manifest.json  — parent metadata + subtask list
#   └── subtasks/
#       ├── A/owner.json
#       ├── B/owner.json
#       └── C/owner.json
# ---------------------------------------------------------------------------
cmd_register() {
    local parent_id=""
    local subtasks=""
    local desc=""

    # Parse args
    while [ $# -gt 0 ]; do
        case "$1" in
            --subtasks) shift; subtasks="$1" ;;
            --desc) shift; desc="$1" ;;
            --*) echo "ERROR: unknown flag $1" >&2; exit 1 ;;
            *) parent_id="$(_sanitize_id "$1")" ;;
        esac
        shift
    done

    if [ -z "$parent_id" ]; then
        echo "ERROR: parent race id is required" >&2
        exit 1
    fi

    if [ -z "$subtasks" ]; then
        echo "ERROR: --subtasks is required (comma-separated, e.g. A,B,C)" >&2
        exit 1
    fi

    # Split subtasks
    IFS=',' read -ra SUB_LIST <<< "$subtasks"
    if [ ${#SUB_LIST[@]} -eq 0 ]; then
        echo "ERROR: at least one subtask required" >&2
        exit 1
    fi

    local race_workspace="$RACE_DIR/$parent_id"
    if [ -d "$race_workspace" ]; then
        echo "ERROR: race '$parent_id' already exists" >&2
        exit 1
    fi

    mkdir -p "$race_workspace"
    local now_val
    now_val="$(_now)"
    local owner="${USER:-unknown}"

    # Sanitize subtask IDs
    local subtask_ids=()
    for raw_id in "${SUB_LIST[@]}"; do
        local safe_id
        safe_id="$(_sanitize_id "$raw_id")"
        if [ -z "$safe_id" ]; then
            echo "WARNING: skipping empty/invalid subtask id '$raw_id'" >&2
            continue
        fi
        subtask_ids+=("$safe_id")
    done

    # Build manifest.json via temp files (zero bash interpolation in Python code)
    local manifest_file="$race_workspace/manifest.json"
    local tmp_ids
    tmp_ids="$(_mktmp)"
    local tmp_desc
    tmp_desc="$(_mktmp)"
    printf '%s\n' "${subtask_ids[@]}" > "$tmp_ids"
    echo "$desc" > "$tmp_desc"

    python3 -c "
import json, os

with open('$tmp_ids') as f:
    subtask_ids = [line.strip() for line in f if line.strip()]
with open('$tmp_desc') as f:
    desc = f.read().strip()

data = {
    'parent_id': '$parent_id',
    'owner': '$owner',
    'created_at': '$now_val',
    'status': 'registered',
    'description': desc,
    'total_subtasks': len(subtask_ids),
    'completed_subtasks': 0,
    'failed_subtasks': 0,
    'subtask_ids': subtask_ids,
}
os.makedirs(os.path.dirname('$manifest_file'), exist_ok=True)
with open('$manifest_file', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print('RACE_REGISTER:$parent_id:{} subtasks'.format(len(subtask_ids)))
"
    rm -f "$tmp_ids" "$tmp_desc"

    # Create subtask directories and owner.json files
    for subtask_id in "${subtask_ids[@]}"; do
        local sub_workspace="$race_workspace/subtasks/$subtask_id"
        mkdir -p "$sub_workspace"
        local owner_file="$sub_workspace/owner.json"
        python3 -c "
import json
data = {
    'race_id': '$parent_id/$subtask_id',
    'parent': '$parent_id',
    'subtask_id': '$subtask_id',
    'owner': '$owner',
    'created_at': '$now_val',
    'status': 'registered',
    'assigned_to': None
}
with open('$owner_file', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null || {
            echo "WARNING: failed to create subtask '$subtask_id'" >&2
        }
    done

    echo "RACE_REGISTERED:$parent_id @ $race_workspace"
}

# ---------------------------------------------------------------------------
# Command: status
# ---------------------------------------------------------------------------
cmd_status() {
    local all_mode=false
    local json_output=false
    local race_id=""

    for arg in "$@"; do
        case "$arg" in
            --all) all_mode=true ;;
            --json) json_output=true ;;
            --*) echo "ERROR: unknown flag $arg" >&2; exit 1 ;;
            *)
                if [ -z "$race_id" ]; then
                    race_id="$arg"
                fi
                ;;
        esac
    done

    if [ -z "$race_id" ]; then
        echo "ERROR: race id is required" >&2
        exit 1
    fi

    # Sanitize: allow / for subtask paths
    local safe_id
    safe_id="$(_sanitize_path_id "$race_id")"
    if [ -z "$safe_id" ]; then
        echo "ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)" >&2
        exit 1
    fi
    race_id="$safe_id"

    local race_workspace="$RACE_DIR/$race_id"

    if [ ! -d "$race_workspace" ]; then
        echo "ERROR: race '$race_id' not found" >&2
        exit 1
    fi

    # --all mode: aggregate subtask statuses
    if [ "$all_mode" = true ]; then
        _status_all "$race_id" "$race_workspace" "$json_output"
        return
    fi

    # Original single-race status
    local result_file="$race_workspace/result.json"
    local owner_file="$race_workspace/owner.json"

    if [ "$json_output" = true ]; then
        local rid_tmp ws_tmp
        rid_tmp="$(_mktmp)"
        ws_tmp="$(_mktmp)"
        printf '%s' "$race_id" > "$rid_tmp"
        printf '%s' "$race_workspace" > "$ws_tmp"
        python3 -c "
import json, sys
with open('$rid_tmp') as f:
    race_id = f.read().strip()
with open('$ws_tmp') as f:
    race_workspace = f.read().strip()
result = {'race_id': race_id, 'workspace': race_workspace}
try:
    with open('$owner_file') as f:
        result['owner'] = json.load(f)
except:
    result['owner'] = None
try:
    with open('$result_file') as f:
        result['result'] = json.load(f)
except:
    result['result'] = None
json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
print()
"
        rm -f "$rid_tmp" "$ws_tmp"
    else
        local status="init"
        local output=""

        if [ -f "$result_file" ]; then
            status=$(_py_read_json "$result_file" "status") || status="init"
            output=$(_py_read_json "$result_file" "output") || output=""
        fi

        echo "RACE:$race_id"
        echo "  status:    $status"
        echo "  workspace: $race_workspace"
        if [ -n "$output" ]; then
            echo "  output:    ${output:0:200}"
        fi
        if [ -f "$owner_file" ]; then
            local task_desc
            task_desc=$(_py_read_json "$owner_file" "task") || true
            if [ -n "$task_desc" ]; then
                echo "  task:      $task_desc"
            fi
        fi
    fi
}

# ---------------------------------------------------------------------------
# Internal: status --all (aggregate subtasks)
# ---------------------------------------------------------------------------
_status_all() {
    local race_id="$1"
    local race_workspace="$2"
    local json_output="$3"

    local subtasks_dir="$race_workspace/subtasks"
    local manifest_file="$race_workspace/manifest.json"

    if [ ! -f "$manifest_file" ]; then
        echo "ERROR: race '$race_id' has no manifest (not a parent race)" >&2
        exit 1
    fi

    local total=0
    local completed=0
    local failed=0
    local running=0
    local registered=0

    # Collect subtask statuses as JSON objects via temp file
    local subdata_file
    subdata_file="$(_mktmp)"
    if [ -d "$subtasks_dir" ]; then
        for sub_dir in "$subtasks_dir"/*/; do
            [ -d "$sub_dir" ] || continue
            local sub_id
            sub_id="$(basename "$sub_dir")"
            total=$((total + 1))

            local result_file="$sub_dir/result.json"
            local st="registered"
            local sub_output=""

            if [ -f "$result_file" ]; then
                st=$(_py_read_json "$result_file" "status") || st="registered"
                sub_output=$(_py_read_json "$result_file" "output") || sub_output=""
            fi

            case "$st" in
                completed) completed=$((completed + 1)) ;;
                failed) failed=$((failed + 1)) ;;
                running) running=$((running + 1)) ;;
                *) registered=$((registered + 1)) ;;
            esac

            # Write each subtask as JSON object line (avoids pipe/multiline corruption)
            local sub_entry_tmp
            sub_entry_tmp="$(_mktmp)"
            printf '%s' "$sub_output" > "$sub_entry_tmp"
            python3 -c "
import json
with open('$sub_entry_tmp') as f:
    out_text = f.read()
entry = {'id': '$sub_id', 'status': '$st', 'output': out_text}
print(json.dumps(entry, ensure_ascii=False))
" >> "$subdata_file"
            rm -f "$sub_entry_tmp"
        done
    fi

    if [ "$json_output" = true ]; then
        # JSON output from collected JSON-lines file
        python3 -c "
import json, sys

subtasks = []
with open('$subdata_file') as f:
    for line in f:
        line = line.strip()
        if line:
            subtasks.append(json.loads(line))

data = {
    'race_id': '$race_id',
    'total': $total,
    'completed': $completed,
    'failed': $failed,
    'running': $running,
    'registered': $registered,
    'subtasks': subtasks,
}
json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
print()
"
        rm -f "$subdata_file"
    else
        echo "RACE:$race_id (swarm)"
        echo "  progress:  $completed/$total completed, $running running, $failed failed, $registered registered"
        echo "  workspace: $race_workspace"
        echo "  subtasks:"
        if [ -f "$subdata_file" ]; then
            # Single Python invocation to format all subtask output
            python3 -c "
import json, sys
icons = {'completed': '✅', 'failed': '❌', 'running': '🔄'}
with open('$subdata_file') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        sid = d.get('id', '')
        sts = d.get('status', '')
        out = (d.get('output') or '')[:60]
        icon = icons.get(sts, '○')
        print(f'    {icon} {sid} [{sts}]')
        if out:
            print(f'      output: {out}')
"
        fi
        rm -f "$subdata_file"
    fi
}

# ---------------------------------------------------------------------------
# Command: complete
# ---------------------------------------------------------------------------
cmd_complete() {
    local raw_id="$1"
    local status="$2"
    local output="${3:-}"

    if [ "$status" != "completed" ] && [ "$status" != "failed" ]; then
        echo "ERROR: status must be 'completed' or 'failed', got '$status'" >&2
        exit 1
    fi

    local race_id
    race_id="$(_sanitize_path_id "$raw_id")"
    if [ -z "$race_id" ]; then
        echo "ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)" >&2
        exit 1
    fi

    # Resolve workspace path:
    #   parent/subtask → .omc/race/parent/subtasks/subtask/
    #   parent         → .omc/race/parent/
    local race_workspace="$RACE_DIR/$race_id"
    if [[ "$race_id" == */* ]]; then
        local pp="${race_id%/*}"
        local ss="${race_id##*/}"
        race_workspace="$RACE_DIR/$pp/subtasks/$ss"
    fi

    if [ ! -d "$race_workspace" ]; then
        echo "ERROR: race '$race_id' not found" >&2
        exit 1
    fi

    local tmpfile
    tmpfile="$(_mktmp)"
    echo "$output" > "$tmpfile"

    local result_file="$race_workspace/result.json"
    local owner_file="$race_workspace/owner.json"
    local ts
    ts="$(_now)"

    # Write result.json via temp+rename for atomicity
    local result_tmp
    result_tmp="$(_mktmp)"
    python3 -c "
import json
with open('$tmpfile') as f:
    out_text = f.read().strip()
data = {
    'race_id': '$race_id',
    'status': '$status',
    'started_at': None,
    'completed_at': '$ts',
    'output': out_text if out_text else None
}
with open('$result_tmp', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
"
    mv "$result_tmp" "$result_file"
    rm -f "$tmpfile"

    # Update owner.json status via temp+rename
    if [ -f "$owner_file" ]; then
        local owner_tmp
        owner_tmp="$(_mktmp)"
        python3 -c "
import json
with open('$owner_file') as f:
    data = json.load(f)
data['status'] = '$status'
with open('$owner_tmp', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
        mv "$owner_tmp" "$owner_file"
    fi

    # Update parent manifest via temp+rename (TOCTOU fix)
    if [[ "$race_id" == */* ]]; then
        local pp="${race_id%/*}"
        local ss="${race_id##*/}"
        local manifest_file="$RACE_DIR/$pp/manifest.json"
        if [ -f "$manifest_file" ]; then
            local mf_tmp
            mf_tmp="$(_mktmp)"
            python3 -c "
import json
with open('$manifest_file') as f:
    data = json.load(f)
if '$status' == 'completed':
    data['completed_subtasks'] = data.get('completed_subtasks', 0) + 1
elif '$status' == 'failed':
    data['failed_subtasks'] = data.get('failed_subtasks', 0) + 1
with open('$mf_tmp', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
            mv "$mf_tmp" "$manifest_file"
        fi
    fi

    echo "RACE_COMPLETE:$race_id:$status"
}

# ---------------------------------------------------------------------------
# Command: report (aggregated — NEW)
# ---------------------------------------------------------------------------
cmd_report() {
    local raw_id="$1"
    local race_id
    race_id="$(_sanitize_path_id "$raw_id")"
    if [ -z "$race_id" ]; then
        echo "ERROR: race id contains invalid characters (use a-zA-Z0-9_-/)" >&2
        exit 1
    fi
    local race_workspace="$RACE_DIR/$race_id"
    local manifest_file="$race_workspace/manifest.json"
    local subtasks_dir="$race_workspace/subtasks"

    if [ ! -f "$manifest_file" ]; then
        echo "ERROR: race '$race_id' has no manifest (not a parent race)" >&2
        exit 1
    fi

    # Read parent info
    local parent_desc=""
    parent_desc=$(_py_read_json "$manifest_file" "description") || parent_desc=""

    echo "=========================================="
    echo "  Race Report: $race_id"
    echo "=========================================="
    if [ -n "$parent_desc" ]; then
        echo "  Description: $parent_desc"
    fi

    local total
    total=$(_py_read_json "$manifest_file" "total_subtasks") || total=0
    local comp
    comp=$(_py_read_json "$manifest_file" "completed_subtasks") || comp=0
    local failed
    failed=$(_py_read_json "$manifest_file" "failed_subtasks") || failed=0

    echo "  Progress:    $comp/$total completed, $failed failed"
    echo ""

    if [ -d "$subtasks_dir" ]; then
        for sub_dir in "$subtasks_dir"/*/; do
            [ -d "$sub_dir" ] || continue
            local sub_id
            sub_id="$(basename "$sub_dir")"
            local result_file="$sub_dir/result.json"
            local owner_file="$sub_dir/owner.json"

            local st="registered"
            local sub_output=""
            [ -f "$result_file" ] && st=$(_py_read_json "$result_file" "status") || st="registered"
            [ -f "$result_file" ] && sub_output=$(_py_read_json "$result_file" "output") || sub_output=""

            local assigned=""
            [ -f "$owner_file" ] && assigned=$(_py_read_json "$owner_file" "assigned_to") || assigned=""

            echo "  --- subtask: $sub_id [$st] ---"
            if [ -n "$assigned" ]; then
                echo "    assigned_to: $assigned"
            fi
            if [ -n "$sub_output" ]; then
                echo "    output:"
                echo "$sub_output" | sed 's/^/      /'
            fi
            echo ""
        done
    fi
    echo "=========================================="
}

# ---------------------------------------------------------------------------
# Command: list
# ---------------------------------------------------------------------------
cmd_list() {
    local json_output=false
    [ "${1:-}" = "--json" ] && json_output=true

    if [ ! -d "$RACE_DIR" ]; then
        if [ "$json_output" = true ]; then
            echo '{"races": []}'
        else
            echo "No races found."
        fi
        exit 0
    fi

    local races=()
    for d in "$RACE_DIR"/*/; do
        [ -d "$d" ] || continue
        local id
        id="$(basename "$d")"
        races+=("$id")
    done

    if [ ${#races[@]} -eq 0 ]; then
        if [ "$json_output" = true ]; then
            echo '{"races": []}'
        else
            echo "No races found."
        fi
        exit 0
    fi

    if [ "$json_output" = true ]; then
        local list_dir_tmp
        list_dir_tmp="$(_mktmp)"
        printf '%s' "$RACE_DIR" > "$list_dir_tmp"
        python3 -c "
import json, os
with open('$list_dir_tmp') as f:
    base = f.read().strip()
races = []
if os.path.isdir(base):
    for entry in sorted(os.listdir(base)):
        d = os.path.join(base, entry)
        if not os.path.isdir(d): continue
        owner = {}; result = {}
        owner_file = os.path.join(d, 'owner.json')
        result_file = os.path.join(d, 'result.json')
        if os.path.isfile(owner_file):
            try:
                with open(owner_file) as f: owner = json.load(f)
            except: pass
        if os.path.isfile(result_file):
            try:
                with open(result_file) as f: result = json.load(f)
            except: pass
        races.append({'id': entry, 'owner': owner, 'result': result})
json.dump({'races': races}, sys.stdout, indent=2, ensure_ascii=False)
print()
"
        rm -f "$list_dir_tmp"
    else
        echo "Races in $RACE_DIR:"
        for id in "${races[@]}"; do
            local ws="$RACE_DIR/$id"
            local st="init"
            if [ -f "$ws/result.json" ]; then
                st=$(_py_read_json "$ws/result.json" "status") || st="init"
            fi
            # Check if it's a parent race with subtasks
            if [ -f "$ws/manifest.json" ]; then
                local comp
                comp=$(_py_read_json "$ws/manifest.json" "completed_subtasks") || comp=0
                local total
                total=$(_py_read_json "$ws/manifest.json" "total_subtasks") || total=0
                echo "  - $id [swarm $comp/$total]"
            else
                echo "  - $id [$st]"
            fi
        done
    fi
}

# ---------------------------------------------------------------------------
# Command: clean
# ---------------------------------------------------------------------------
cmd_clean() {
    local raw_target="${1:-}"

    if [ -n "$raw_target" ]; then
        local target_id
        target_id="$(_sanitize_id "$raw_target")"
        if [ "$target_id" != "$raw_target" ] || [ -z "$target_id" ]; then
            echo "ERROR: invalid race id '$raw_target' (use a-zA-Z0-9_-)" >&2
            exit 1
        fi
        local race_workspace="$RACE_DIR/$target_id"
        if [ ! -d "$race_workspace" ]; then
            echo "ERROR: race '$target_id' not found" >&2
            exit 1
        fi
        rm -rf "$race_workspace"
        echo "CLEANED:$target_id"
    else
        if [ ! -d "$RACE_DIR" ]; then
            echo "No races to clean."
            exit 0
        fi

        local cleaned=0
        for d in "$RACE_DIR"/*/; do
            [ -d "$d" ] || continue
            local id
            id="$(basename "$d")"
            local result_file="$d/result.json"
            if [ -f "$result_file" ]; then
                local st
                st=$(_py_read_json "$result_file" "status") || st=""
                if [ "$st" = "completed" ] || [ "$st" = "failed" ]; then
                    rm -rf "$d"
                    echo "CLEANED:$id"
                    cleaned=$((cleaned + 1))
                fi
            fi
        done
        if [ "$cleaned" -eq 0 ]; then
            echo "No completed races to clean."
        else
            echo "Cleaned $cleaned race(s)."
        fi
    fi
}

# ---------------------------------------------------------------------------
# Route commands
# ---------------------------------------------------------------------------
case "$ACTION" in
    init)
        cmd_init "$@"
        ;;
    start)
        cmd_start "$@"
        ;;
    register)
        cmd_register "$@"
        ;;
    status)
        cmd_status "$@"
        ;;
    complete)
        cmd_complete "$@"
        ;;
    report)
        cmd_report "$@"
        ;;
    list)
        cmd_list "$@"
        ;;
    clean)
        cmd_clean "$@"
        ;;
    *)
        usage
        ;;
esac
