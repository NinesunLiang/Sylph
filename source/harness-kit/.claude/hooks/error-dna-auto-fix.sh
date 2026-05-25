#!/usr/bin/env bash
# error-dna-auto-fix.sh — Stop — 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
# Role: 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
# GS-001: 跨会话回顾聚合，只输出 fix_count > 1 的条目（避免与 PostToolUse 实时层重复）

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "error_dna_auto_fix" || exit 0
flywheel_event "error_dna_auto_fix" "active" "P2" || true

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DNA_FILE="$PROJECT_ROOT/.omc/state/error-dna.json"

[ -f "$DNA_FILE" ] || exit 0

PY_OUTPUT=$(${PYTHON_BIN:-python3} - "$DNA_FILE" <<'PYEOF'
import json, sys, time
from datetime import datetime

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        dna = json.load(f)
except (json.JSONDecodeError, FileNotFoundError, IndexError):
    sys.exit(0)

signatures = dna.get('error_signatures', {})
candidates = []

for sig, entry in signatures.items():
    count = entry.get('count', 0)
    fix_count = entry.get('fix_count', 0)
    status = entry.get('status', 'active')
    repair_cmd = entry.get('repair_command', '')
    message = entry.get('message', '')[:80]
    last_seen = entry.get('last_seen', 0)

    if count >= 3 and status == 'active':
        candidates.append((count, fix_count, sig, message, repair_cmd, last_seen))

if not candidates:
    sys.exit(0)

candidates.sort(key=lambda x: -x[0])
candidates = candidates[:5]

lines = [f"[error-dna retrospective] {len(candidates)} 个顽固错误 (≥3次出现，仍 active):"]
for count, fix_count, sig, message, repair_cmd, last_seen in candidates:
    last_str = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M') if last_seen else '未知'
    lines.append(f" · {sig[:16]} ×{count} (已尝试修复 {fix_count} 次) — {message}")
    if repair_cmd:
        lines.append(f"   ▶ 自动执行修复: `{repair_cmd}`")
    lines.append(f"   └ 上次失败: {last_str}")

print('|'.join(lines))
PYEOF
)

if [ -n "$PY_OUTPUT" ]; then
    # Stop hook 不支持 additionalContext，stderr 输出会导致 JSON 校验错误
    # 改为写入状态文件，由 inject-project-knowledge.sh 在下次 SessionStart 时读取
    echo "$PY_OUTPUT" > "$PROJECT_ROOT/.omc/state/error-dna-retrospective.txt"
fi
exit 0
