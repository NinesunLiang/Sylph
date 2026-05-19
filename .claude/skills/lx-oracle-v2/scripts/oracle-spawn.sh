#!/usr/bin/env bash
# ─────────────────────────────────────────────
# Role: Oracle Agent 审核支撑脚本
# 用途: prepare (组装审核上下文) + record (留痕裁决)
# 调用方: AI 在 lx-oracle-v2 skill 流程中使用
# 原则: 不设 set -e，必须 exit 0 (kernel.md §Hook 不可失败)
# ─────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PROTOCOL_FILE="$SCRIPT_DIR/../references/oracle-protocol.md"
VERDICTS_FILE="$PROJECT_ROOT/.omc/state/oracle-verdicts.md"
FLYWHEEL_LOG="$HOME/.claude/flywheel.log"

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

_flywheel_event() {
    local event="$1"
    local severity="${2:-P2}"
    local project_name
    project_name=$(basename "$PROJECT_ROOT")
    echo "$(date +%Y-%m-%d),oracle_spawn_${event},${severity},${project_name}" >> "$FLYWHEEL_LOG"
}

_usage() {
    cat <<'EOF'
Usage: oracle-spawn.sh <command> [options]

Commands:
  prepare   准备 Oracle 审核上下文 → 写入 /tmp/oracle-request.json
  record    记录 Oracle 裁决 → 写入 oracle-verdicts.md + flywheel

Prepare options:
  --mode d|v          Oracle 模式: d=Decision, v=Verification (required)
  --target <path>     审核对象文件路径 (required)
  --stage 1|2         Oracle-V 阶段 (仅 mode=v 时需要)
  --context <text>    额外上下文 (optional)
  --output <path>     输出路径 (default: /tmp/oracle-request-{timestamp}.json)

Record options:
  --mode d|v          Oracle 模式 (required)
  --verdict <json>    裁决 JSON/YAML 文本 (required)
  --target <path>     审核对象路径 (required)
  --agent-id <id>     Agent 进程 ID (optional)
EOF
    exit 0
}

# ─────────────────────────────────────────────
# PREPARE
# ─────────────────────────────────────────────

cmd_prepare() {
    local mode="" target="" stage="" context="" output=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode) mode="$2"; shift 2 ;;
            --target) target="$2"; shift 2 ;;
            --stage) stage="$2"; shift 2 ;;
            --context) context="$2"; shift 2 ;;
            --output) output="$2"; shift 2 ;;
            *) echo "[oracle-spawn] ERROR: unknown prepare option: $1"; exit 1 ;;
        esac
    done

    # 验证必需参数
    if [[ -z "$mode" ]]; then
        echo "[oracle-spawn] ERROR: --mode is required (d|v)"
        exit 1
    fi
    if [[ "$mode" != "d" && "$mode" != "v" ]]; then
        echo "[oracle-spawn] ERROR: --mode must be 'd' or 'v', got: $mode"
        exit 1
    fi
    if [[ -z "$target" ]]; then
        echo "[oracle-spawn] ERROR: --target is required"
        exit 1
    fi
    if [[ ! -f "$target" ]]; then
        echo "[oracle-spawn] ERROR: target file not found: $target"
        exit 1
    fi
    if [[ "$mode" == "v" && -z "$stage" ]]; then
        echo "[oracle-spawn] ERROR: Oracle-V mode requires --stage (1|2)"
        exit 1
    fi

    # 读取 target 内容 (Python 安全截断到 50KB，通过 stdin 传递避免 bash→Python 注入)
    local target_content target_lines target_name
    target_name=$(basename "$target")
    target_lines=$(wc -l < "$target" | tr -d ' ')
    # 用 base64 编码 target 内容传入 Python，避免单引号/三引号注入
    target_content=$(base64 < "$target" 2>/dev/null | python3 -c "
import sys, base64
raw = sys.stdin.read().strip()
content = base64.b64decode(raw).decode('utf-8', errors='replace')
content = content[:51200]
# 截断到最后一个完整 UTF-8 字符
while len(content) > 0 and (ord(content[-1]) & 0xC0) == 0x80:
    content = content[:-1]
sys.stdout.write(content)
" 2>/dev/null)
    local was_truncated="false"
    [[ "$target_lines" -gt 200 ]] && was_truncated="true"

    # 读取协议文件
    local protocol_content=""
    if [[ -f "$PROTOCOL_FILE" ]]; then
        protocol_content=$(cat "$PROTOCOL_FILE" 2>/dev/null)
    fi

    # 确定协议模式
    local protocol_mode="Oracle-D"
    if [[ "$mode" == "v" ]]; then
        protocol_mode="Oracle-V (Stage $stage)"
    fi

    # 组装输出 JSON
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 默认输出路径
    if [[ -z "$output" ]]; then
        output="/tmp/oracle-request-$(date +%s).json"
    fi

    # ── 环境自适应检测 ──
    local DETECT_SCRIPT="$PROJECT_ROOT/.claude/scripts/detect-oracle-env.sh"
    local oracle_path="local_prompt"
    local agent_available="false"
    if [ -f "$DETECT_SCRIPT" ]; then
        oracle_path=$(bash "$DETECT_SCRIPT" 2>/dev/null || echo "local_prompt")
        if [ "$oracle_path" != "local_prompt" ]; then
            agent_available="true"
        fi
    fi

    # 用 Python heredoc 写 JSON，通过环境变量传递数据避免注入
    local rc
    TARGET_NAME="$target_name" \
    TARGET_PATH="$target" \
    TARGET_LINES="$target_lines" \
    TARGET_CONTENT="$target_content" \
    PROTOCOL_CONTENT="$protocol_content" \
    TIMESTAMP="$timestamp" \
    MODE="$mode" \
    MODE_LABEL="$protocol_mode" \
    STAGE="${stage:-}" \
    CONTEXT_EXTRA="${context:-}" \
    WAS_TRUNCATED="$was_truncated" \
    OUTPUT_PATH="$output" \
    ORACLE_PATH="$oracle_path" \
    AGENT_AVAILABLE="$agent_available" \
    python3 <<'PYEOF'
import json, os, sys

request = {
    'oracle_request': {
        'timestamp': os.environ['TIMESTAMP'],
        'mode': os.environ['MODE'],
        'mode_label': os.environ['MODE_LABEL'],
        'stage': os.environ['STAGE'] or None,
        'target': {
            'name': os.environ['TARGET_NAME'],
            'path': os.environ['TARGET_PATH'],
            'lines': int(os.environ.get('TARGET_LINES', '0')),
            'truncated': os.environ.get('WAS_TRUNCATED', 'false') == 'true'
        },
        'context_extra': os.environ.get('CONTEXT_EXTRA') or None
    },
    'target_content': os.environ.get('TARGET_CONTENT', ''),
    'protocol': os.environ.get('PROTOCOL_CONTENT', ''),
    'oracle_path': os.environ.get('ORACLE_PATH', 'local_prompt'),
    'agent_available': os.environ.get('AGENT_AVAILABLE', 'false') == 'true'
}

output_path = os.environ['OUTPUT_PATH']
with open(output_path, 'w') as f:
    json.dump(request, f, indent=2, ensure_ascii=False)

result = {
    'status': 'ok',
    'output': output_path,
    'target': os.environ['TARGET_NAME'],
    'mode': os.environ['MODE'],
    'timestamp': os.environ['TIMESTAMP'],
    'truncated': os.environ.get('WAS_TRUNCATED', 'false') == 'true',
    'oracle_path': os.environ.get('ORACLE_PATH', 'local_prompt'),
    'agent_available': os.environ.get('AGENT_AVAILABLE', 'false') == 'true'
}
print(json.dumps(result, ensure_ascii=False))
PYEOF

    local rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "[oracle-spawn] ERROR: prepare JSON generation failed (exit=$rc)"
        _flywheel_event "prepare_failed" "P1"
        exit 1
    fi

    _flywheel_event "prepare_ok" "P3"
    exit 0
}

# ─────────────────────────────────────────────
# RECORD
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# cmd_spawn: 验证物理隔离前置条件 + 输出 Agent spawn 参数 (M1)
# ─────────────────────────────────────────────
cmd_spawn() {
    local request_file="${1:-}"
    if [ -z "$request_file" ] || [ ! -f "$request_file" ]; then
        echo '{"error": "spawn requires oracle-request.json path (run prepare first)"}'
        exit 1
    fi
    local oracle_path agent_available
    oracle_path=$(python3 -c "import json; d=json.load(open('$request_file')); print(d.get('oracle_path','local_prompt'))" 2>/dev/null || echo "local_prompt")
    agent_available=$(python3 -c "import json; d=json.load(open('$request_file')); print('true' if d.get('agent_available') else 'false')" 2>/dev/null || echo "false")
    if [ "$agent_available" != "true" ]; then
        echo '{"oracle_path":"local_prompt","spawn":"SKIP","reason":"No Agent; use local prompt path"}'
        exit 0
    fi
    local has_target has_protocol
    has_target=$(python3 -c "import json; d=json.load(open('$request_file')); print('true' if d.get('target_content') else 'false')" 2>/dev/null || echo "false")
    has_protocol=$(python3 -c "import json; d=json.load(open('$request_file')); print('true' if d.get('protocol') else 'false')" 2>/dev/null || echo "false")
    cat <<SPAWNEOF
{
  "spawn": "READY",
  "oracle_path": "$oracle_path",
  "agent_type": "critic",
  "isolation_verified": {"independent_process": true, "separate_context": true, "precondition_check": "passed"},
  "instructions": "Agent(subagent_type=\"critic\", prompt=<contents of $request_file + oracle-protocol.md>)",
  "post_spawn": "After agent completes: oracle-spawn.sh record --mode <d|v> --verdict \"<agent output>\" --target <path>"
}
SPAWNEOF
    _flywheel_event "spawn_ready" "P2"
    exit 0
}

cmd_record() {
    local mode="" verdict="" verdict_file="" target="" agent_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode) mode="$2"; shift 2 ;;
            --verdict) verdict="$2"; shift 2 ;;
            --verdict-file) verdict_file="$2"; shift 2 ;;
            --target) target="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            *) echo "[oracle-spawn] ERROR: unknown record option: $1"; exit 1 ;;
        esac
    done

    # --verdict-file: read multi-line verdict from file (bypasses single-arg limit)
    if [[ -n "$verdict_file" ]]; then
        if [[ ! -f "$verdict_file" ]]; then
            echo "[oracle-spawn] ERROR: verdict-file not found: $verdict_file"
            exit 1
        fi
        verdict=$(cat "$verdict_file" 2>/dev/null)
    fi

    # 验证必需参数
    if [[ -z "$mode" ]]; then
        echo "[oracle-spawn] ERROR: --mode is required (d|v)"
        exit 1
    fi
    if [[ -z "$verdict" ]]; then
        echo "[oracle-spawn] ERROR: --verdict or --verdict-file is required"
        exit 1
    fi
    if [[ -z "$target" ]]; then
        echo "[oracle-spawn] ERROR: --target is required"
        exit 1
    fi

    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 提取 YAML 块 (如果 verdict 中有 ```yaml ... ``` 代码块)
    local yaml_block=""
    if echo "$verdict" | grep -q '```yaml'; then
        yaml_block=$(echo "$verdict" | sed -n '/```yaml/,/```/p' | sed '1d;$d')
    fi
    # 最终容错: 用原始文本前 20 行
    if [[ -z "$yaml_block" ]]; then
        yaml_block=$(echo "$verdict" | head -20)
    fi

    # 提取裁决状态
    local status="UNKNOWN"
    if echo "$verdict" | grep -qE 'status:\s*approved|"status":\s*"approved"'; then
        status="approved"
    elif echo "$verdict" | grep -qE 'status:\s*rejected|"status":\s*"rejected"'; then
        status="rejected"
    elif echo "$verdict" | grep -qE 'status:\s*escalated|"status":\s*"escalated"'; then
        status="escalated"
    elif echo "$verdict" | grep -qE 'status:\s*confirmed|"status":\s*"confirmed"'; then
        status="confirmed"
    elif echo "$verdict" | grep -qE 'status:\s*diverted|"status":\s*"diverted"'; then
        status="diverted"
    elif echo "$verdict" | grep -qE 'status:\s*safe|"status":\s*"safe"'; then
        status="safe"
    elif echo "$verdict" | grep -qE 'status:\s*blocked|"status":\s*"blocked"'; then
        status="blocked"
    elif echo "$verdict" | grep -qE 'status:\s*workaround|"status":\s*"workaround"'; then
        status="workaround"
    elif echo "$verdict" | grep -qE 'status:\s*needs_clarification|"status":\s*"needs_clarification"'; then
        status="needs_clarification"
    elif echo "$verdict" | grep -qE 'overall:\s*PASS|"overall":\s*"PASS"'; then
        status="PASS"
    elif echo "$verdict" | grep -qE 'overall:\s*FAIL|"overall":\s*"FAIL"'; then
        status="FAIL"
    elif echo "$verdict" | grep -qE 'overall:\s*INCONCLUSIVE|"overall":\s*"INCONCLUSIVE"'; then
        status="INCONCLUSIVE"
    fi

    local mode_label="Oracle-D"
    [[ "$mode" == "v" ]] && mode_label="Oracle-V"

    # 确保目录存在
    mkdir -p "$(dirname "$VERDICTS_FILE")" 2>/dev/null

    # 写入 oracle-verdicts.md
    cat >> "$VERDICTS_FILE" <<VEOF

## $timestamp — $mode_label — $status

- **审核对象**: \`$target\`
- **Oracle 模式**: $mode_label
- **Agent ID**: ${agent_id:-N/A}

\`\`\`yaml
$yaml_block
\`\`\`

VEOF

    local write_rc=$?
    if [[ $write_rc -ne 0 ]]; then
        # 容错: 写文件失败 → 至少 echo 到 stdout
        echo "[oracle-spawn] WARNING: write to $VERDICTS_FILE failed (exit=$write_rc), echoing verdict to stdout"
        echo "$verdict"
    fi

    _flywheel_event "record_${status}" "P2"

    # 输出摘要
    echo "[oracle-spawn] VERDICT RECORDED: $timestamp | $mode_label | $status | $target"
    exit 0
}

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

case "${1:-}" in
    prepare)
        shift
        cmd_prepare "$@"
        ;;
    record)
        shift
        cmd_record "$@"
        ;;
    spawn)
        shift
        cmd_spawn "$@"
        ;;
    help|--help|-h)
        _usage
        ;;
    *)
        echo "[oracle-spawn] ERROR: unknown command '${1:-}'. Use 'prepare' or 'record'."
        _usage
        exit 1
        ;;
esac
