#!/usr/bin/env bash
# phase-state-tracker.sh — PostToolUse hook — 追踪当前任务所处的五阶段状态
# Role: 检查 oracle-verdicts.md 24h 内是否有 ACCEPT → phase2_approved
#       检查 git diff 是否有未提交修改 → phase3_executing
#       写入 .omc/state/current-phase.json
# 哲学 #4(验证): 每个状态判断附带证据来源
# 哲学 #6(0信任): 不依赖缓存，每次执行实时检查

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "phase_state_tracker" || { echo '{"continue": true}'; exit 0; }

hc_init

# ─── 定义五阶段 ───
# phase1_research     — 调研阶段：正在阅读源码、分析现状
# phase2_approved     — 方案已通过 Oracle+Meta-Oracle 双审
# phase3_executing    — 执行阶段：有未提交的代码修改
# phase4_approved     — 结果已通过 Oracle+Meta-Oracle 双审
# phase5_report       — 验收报告阶段：等待人类确认

VERDICTS_FILE="$PROJECT_ROOT/.omc/state/oracle-verdicts.md"
PHASE_FILE="$STATE_DIR/current-phase.json"
NOW_EPOCH=$(date +%s 2>/dev/null || echo 0)

# ─── Phase 2: 检查 oracle-verdicts.md 24h 内是否有 ACCEPT ───
HAS_ACCEPT_24H="false"
ACCEPT_EVIDENCE=""
if [ -f "$VERDICTS_FILE" ]; then
    ACCEPT_DATA=$($PYTHON_BIN - "$VERDICTS_FILE" "$NOW_EPOCH" <<'PYEOF'
import sys, re, os
from datetime import datetime, timezone

file_path = sys.argv[1]
now_epoch = int(sys.argv[2])
window_sec = 86400  # 24 hours

try:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
except:
    print("false||")
    sys.exit(0)

# Match verdict blocks: "## <timestamp>Z — Oracle-<mode> — approved|accepted"
# Timestamp format: 2026-05-19T03:34:20Z
pattern = r'##\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+—\s+Oracle-[^\s]+\s+—\s+(approved|accepted)'
matches = re.findall(pattern, content)

for ts_str, status in matches:
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        ts_epoch = int(dt.timestamp())
        if now_epoch - ts_epoch <= window_sec:
            print(f"true|{ts_str}|{status}")
            sys.exit(0)
    except:
        continue

print("false||")
PYEOF
    )
    IFS='|' read -r HAS_ACCEPT_24H ACCEPT_TS ACCEPT_STATUS <<< "$ACCEPT_DATA"
    if [ "$HAS_ACCEPT_24H" = "true" ]; then
        ACCEPT_EVIDENCE="oracle-verdicts.md:${ACCEPT_TS} — ${ACCEPT_STATUS}"
    fi
fi

# ─── Phase 3: 检查 git diff 是否有未提交修改 ───
HAS_UNCOMMITTED="false"
UNCOMMITTED_COUNT=0
UNCOMMITTED_FILES=""
if git -C "$PROJECT_ROOT" rev-parse --git-dir &>/dev/null; then
    _diff_out=$(git -C "$PROJECT_ROOT" diff --name-only 2>/dev/null)
    _staged_out=$(git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null)
    _all_uncommitted=$(echo -e "${_diff_out}\n${_staged_out}" | sort -u | grep -v '^$' || true)
    if [ -n "$_all_uncommitted" ]; then
        HAS_UNCOMMITTED="true"
        UNCOMMITTED_COUNT=$(echo "$_all_uncommitted" | wc -l | tr -d ' ')
        UNCOMMITTED_FILES=$(echo "$_all_uncommitted" | head -10 | tr '\n' ',' | sed 's/,$//')
    fi
fi

# ─── Phase 4: 检查 oracle-verdicts.md 24h 内是否有 ACCEPT（结果双审） ───
# 复用 Phase 2 的检查结果，但标注为 phase4
HAS_ACCEPT_RESULT_24H="$HAS_ACCEPT_24H"
ACCEPT_RESULT_EVIDENCE="$ACCEPT_EVIDENCE"

# ─── 确定当前阶段 ───
CURRENT_PHASE="phase1_research"
PHASE_LABEL="Phase 1: 调研"
PHASE_DESCRIPTION="调研阶段：正在阅读源码、分析现状"
TRANSITION_EVIDENCE=""

if [ "$HAS_UNCOMMITTED" = "true" ]; then
    CURRENT_PHASE="phase3_executing"
    PHASE_LABEL="Phase 3: 执行"
    PHASE_DESCRIPTION="执行阶段：有未提交的代码修改"
    TRANSITION_EVIDENCE="git diff: ${UNCOMMITTED_COUNT} 个文件未提交 (${UNCOMMITTED_FILES})"
elif [ "$HAS_ACCEPT_24H" = "true" ]; then
    # 有 ACCEPT 但无未提交修改 → Phase 2 (方案双审通过) 或 Phase 4 (结果双审通过)
    # 简单判断：如果存在已修改文件的历史记录，则可能是 Phase 4
    # 此处保守标记为 phase2_approved
    CURRENT_PHASE="phase2_approved"
    PHASE_LABEL="Phase 2: 方案双审通过"
    PHASE_DESCRIPTION="方案已通过 Oracle+Meta-Oracle 双审，等待执行"
    TRANSITION_EVIDENCE="$ACCEPT_EVIDENCE"
fi

# ─── 写入 current-phase.json ───
mkdir -p "$STATE_DIR"
$PYTHON_BIN - "$PHASE_FILE" "$CURRENT_PHASE" "$PHASE_LABEL" "$PHASE_DESCRIPTION" "$TRANSITION_EVIDENCE" <<'PYEOF'
import json, sys, os

phase_file = sys.argv[1]
current_phase = sys.argv[2]
phase_label = sys.argv[3]
phase_description = sys.argv[4]
transition_evidence = sys.argv[5]

data = {
    "current_phase": current_phase,
    "phase_label": phase_label,
    "phase_description": phase_description,
    "transition_evidence": transition_evidence,
    "updated_at": None  # filled below
}
try:
    from datetime import datetime, timezone
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
except:
    data["updated_at"] = "unknown"

# Atomic write via tmp + rename
tmp = phase_file + ".tmp." + str(os.getpid())
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
os.rename(tmp, phase_file)
PYEOF

# ─── 输出摘要到 stderr（人类可见） ───
echo "📊 [Phase-State] ${PHASE_LABEL} — ${TRANSITION_EVIDENCE:-无转换证据}" >&2

# ─── 注入 additionalContext（AI 可见） ───
CTX=$(cat <<CTX
[Phase-State Tracker] 当前阶段: ${PHASE_LABEL}
- 描述: ${PHASE_DESCRIPTION}
- 转换证据: ${TRANSITION_EVIDENCE:-无}
- 未提交文件: ${UNCOMMITTED_COUNT} 个
- 文件: ${PHASE_FILE}
CTX
)

echo "$CTX" | ${PYTHON_BIN:-python3} -c '
import json, sys
ctx = sys.stdin.read()
ctx = "".join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({"continue": True, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}}, ensure_ascii=False))
'

flywheel_event "phase_state_tracker" "tracked" "P3" || true
exit 0
