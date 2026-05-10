#!/usr/bin/env bash
# skill-flywheel.sh — Stop — 停止时更新 skill 使用频率，驱动飞轮优化（含时间戳追踪）
# Role: 停止时更新 skill 使用频率，驱动飞轮优化（含时间戳追踪）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "skill_flywheel" || exit 0

BUFFER="$HOME/.claude/flywheel-buffer.jsonl"
FLYWHEEL="$HOME/.claude/flywheel.log"

# buffer 不存在或为空则静默退出
[ -f "$BUFFER" ] && [ -s "$BUFFER" ] || exit 0

# 确保 flywheel.log 目录存在
mkdir -p "$(dirname "$FLYWHEEL")"

# flush：将 buffer 内容追加到 flywheel.log，附带时间戳标记
# 时间戳格式: # ts=<epoch> iso=<ISO-8601>
BUFFER_CONTENT=$(cat "$BUFFER")
if [ -z "$BUFFER_CONTENT" ]; then
    rm -f "$BUFFER"
    exit 0
fi

# 写入时间戳标记 + buffer 内容
TS=$(date +%s)
TS_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
{
    echo "# ts=${TS} iso=${TS_ISO}"
    echo "$BUFFER_CONTENT"
} >> "$FLYWHEEL"

# 消费 buffer
rm -f "$BUFFER"

LINES=$(echo "$BUFFER_CONTENT" | wc -l | tr -d ' ')
echo "Flywheel flushed: ${LINES} entries → flywheel.log (${TS_ISO})"

# === Analytics: compute per-skill frequency and deprecation detection ===
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ANALYTICS_SCRIPT="$PROJECT_ROOT/.claude/scripts/flywheel_analytics.py"
if [ -f "$ANALYTICS_SCRIPT" ]; then
    python3 "$ANALYTICS_SCRIPT" "$FLYWHEEL" "$PROJECT_ROOT/.omc/state/flywheel-report.json" 2>/dev/null || true
fi

# === GS-002: Deprecated skill notification ===
REPORT="$PROJECT_ROOT/.omc/state/flywheel-report.json"
if [ -f "$REPORT" ]; then
    DEP_OUTPUT=$(python3 - "$REPORT" <<'PYEOF'
import json, sys
try:
    with open(sys.argv[1]) as f:
        report = json.load(f)
    dep = report.get('deprecated_skills', [])
    if not dep:
        sys.exit(0)
    lines = ["[flywheel] ⚠️ {} 个技能已废弃 (>30天未使用):".format(len(dep))]
    skills = report.get('skills', {})
    for name in dep:
        info = skills.get(name, {})
        days = info.get('days_since_last_use', '?')
        lines.append(" · {} — 上次使用: {} 天前".format(name, days))
    print('|'.join(lines))
except Exception:
    sys.exit(0)
PYEOF
)
    if [ -n "$DEP_OUTPUT" ]; then
        ESCAPED=$(echo "$DEP_OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
        echo "{\"continue\": true, \"hookSpecificOutput\": {\"hookEventName\": \"Stop\", \"additionalContext\": ${ESCAPED}}}"
    fi
fi

exit 0
