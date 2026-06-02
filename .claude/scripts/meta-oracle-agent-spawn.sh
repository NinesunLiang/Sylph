#!/usr/bin/env bash
# meta-oracle-agent-spawn.sh — Meta-Oracle Agent spawn 入口
# Role: 用和 Oracle 相同的 Agent spawn 机制启动 Meta-Oracle 独立审查
# 只是 prompt 不同（Meta-Oracle 方法论 vs Oracle 方法论）
#
# 使用方式: AI 在收到 Meta-Oracle trigger 后调用此脚本
# 流程:
#   1. prepare: 组装审核上下文 → /tmp/meta-oracle-request.json
#   2. spawn:   Agent(subagent_type="critic", prompt=<request.json + meta-oracle-protocol.md>)
#   3. record:  记录裁决到 meta-oracle-verdicts.md

source "$(dirname "$0")/../hooks/harness_config.sh"
set -f

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
# 用法: meta-oracle-agent-spawn.sh [G1|G2|G3|G4] prepare|record
# 第一个参数是触发类型(可选,默认G3)，第二个是子命令
TRIGGER_TYPE="G3"
CMD=""
for arg in "$@"; do
    case "$arg" in
        prepare|record|help) CMD="$arg" ;;
        G1|G2|G3|G4) TRIGGER_TYPE="$arg" ;;
    esac
done

# Meta-Oracle 审查协议
META_PROTOCOL="$PROJECT_ROOT/.claude/reference/meta-oracle.md"
VERDICTS_FILE="$STATE_DIR/meta-oracle-verdicts.md"

# ─────────────────────────────────────────────
# Step 1: Prepare — 组装审核上下文
# ─────────────────────────────────────────────
cmd_prepare() {
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 读取审查协议
    local protocol_content=""
    if [ -f "$META_PROTOCOL" ]; then
        protocol_content=$(cat "$META_PROTOCOL" 2>/dev/null)
    fi

    # 读取最新 smoke test 结果
    local smoke_result=""
    local latest_smoke
    latest_smoke=$(ls -t "$STATE_DIR"/harness-smoke-*.log 2>/dev/null | head -1)
    if [ -f "$latest_smoke" ]; then
        smoke_result=$(grep 'summary:' "$latest_smoke" 2>/dev/null || echo "无 smoke test 数据")
    fi

    # 读取最新 Oracle 裁决
    local oracle_verdicts=""
    if [ -f "$STATE_DIR/oracle-verdicts.md" ]; then
        oracle_verdicts=$(tail -30 "$STATE_DIR/oracle-verdicts.md" 2>/dev/null)
    fi

    # 输出 JSON 到 stdout（AI 读取后用 Agent 调用）
    cat << JSONEOF
{
  "meta_oracle_request": {
    "timestamp": "$timestamp",
    "trigger_type": "${TRIGGER_TYPE#G}",
    "project_root": "$PROJECT_ROOT"
  },
  "protocol": $(echo "$protocol_content" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "smoke_test": $(echo "$smoke_result" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "oracle_verdicts": $(echo "$oracle_verdicts" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "spawn": "READY",
  "agent_type": "critic",
  "instructions": "使用 Agent(subagent_type='critic') 拉起独立上下文，prompt = protocol + smoke_test + oracle_verdicts",
  "post_spawn": "将 agent 输出写入 $VERDICTS_FILE"
}
JSONEOF

    flywheel_event "meta_oracle_spawn" "prepare_ok" "P2" || true
    exit 0
}

# ─────────────────────────────────────────────
# Step 2: Record — 记录裁决
# ─────────────────────────────────────────────
cmd_record() {
    local verdict="${1:-}"
    if [ -z "$verdict" ]; then
        echo "[meta-oracle-spawn] ERROR: --verdict is required"
        exit 1
    fi

    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 提取裁决状态
    local status="UNKNOWN"
    if echo "$verdict" | grep -qE '\[Meta-Oracle:\s*ACCEPT\]'; then
        status="ACCEPT"
    elif echo "$verdict" | grep -qE '\[Meta-Oracle:\s*ADVISORY\]'; then
        status="ADVISORY"
    elif echo "$verdict" | grep -qE '\[Meta-Oracle:\s*REJECT\]'; then
        status="REJECT"
    fi

    # 写入 meta-oracle-verdicts.md
    mkdir -p "$(dirname "$VERDICTS_FILE")" 2>/dev/null
    cat >> "$VERDICTS_FILE" << VEOF

## [$timestamp] [$TRIGGER_TYPE] [Meta-Oracle: $status]

**审查类型**: G${TRIGGER_TYPE} — Meta-Oracle Agent 独立审查
**Agent**: critic (独立上下文, 物理隔离)
**路径**: Agent spawn

\`\`\`
$(echo "$verdict" | head -30)
\`\`\`

VEOF

    flywheel_event "meta_oracle_spawn" "record_${status}" "P2" || true
    echo "[meta-oracle-spawn] ✅ 裁决已记录: $timestamp | ${TRIGGER_TYPE} | $status"
    exit 0
}

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

case "$CMD" in
    prepare)
        cmd_prepare
        ;;
    record)
        cmd_record "$@"
        ;;
    help|--help|-h)
        echo "Usage: meta-oracle-agent-spawn.sh [G1|G2|G3|G4] prepare|record"
        echo "  prepare             组装审核上下文 → stdout JSON"
        echo "  record --verdict    记录裁决到 meta-oracle-verdicts.md"
        echo "  G1|G2|G3|G4        触发类型(可选,默认G3)"
        exit 0
        ;;
    *)
        echo "[meta-oracle-spawn] Usage: $0 [G1|G2|G3|G4] <prepare|record>"
        exit 1
        ;;
esac
