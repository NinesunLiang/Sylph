#!/bin/bash

# harness-kit:managed v1.0.2

# 项目级 SessionStart hook：注入 .claude/ 核心知识到 AI context

# 输出格式：纯文本（与 inject-instincts.sh 一致，已验证有效）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "inject_project_knowledge" || exit 0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

if [ ! -d "$CLAUDE_DIR" ]; then
    exit 0
fi

# 从配置读取注入文件列表
INJECT_FILES=$(hc_get_list "knowledge.inject_files" "index.md:full kernel.md:full claude-next.md:summary style-guide.md:summary")

for entry in $INJECT_FILES; do
    # 解析 filename:mode 格式
    FILE_NAME="${entry%%:*}"
    MODE="${entry##*:}"
    FILE_PATH="$CLAUDE_DIR/$FILE_NAME"

    [ ! -f "$FILE_PATH" ] && continue

    if [ "$MODE" = "full" ]; then
        echo "[.claude/$FILE_NAME]"
        cat "$FILE_PATH"
        echo ""
    elif [ "$MODE" = "summary" ]; then
        LINES=$(wc -l < "$FILE_PATH" | tr -d ' ')
        echo "[.claude/$FILE_NAME ${LINES}行] 章节:"
        grep "^##" "$FILE_PATH" | head -30
        echo "--- 完整内容请Read .claude/$FILE_NAME"
        echo ""
    fi
done

# LSP 提醒（从配置读取）
LSP_HINT=$(hc_get "knowledge.lsp_hint" "")
if [ -n "$LSP_HINT" ]; then
    echo "[LSP 提醒] ${LSP_HINT}:"
    echo " lsp_workspace_symbols(query=符号名) / lsp_goto_definition / lsp_find_references"
fi

# ─── 升华检测（claude-next.md 成熟度检查）───
CLAUDE_NEXT="$CLAUDE_DIR/claude-next.md"
if [ -f "$CLAUDE_NEXT" ]; then
    SUB_COUNT=$(hc_get "sublimation.count_threshold" "20")
    SUB_DAYS=$(hc_get "sublimation.age_days" "10")
    SUB_HITS=$(hc_get "sublimation.hit_threshold" "5")
    python3 - "$CLAUDE_NEXT" "$SUB_COUNT" "$SUB_DAYS" "$SUB_HITS" <<'PYEOF'
import re, sys
from datetime import datetime, date

try:
    file_path = sys.argv[1]
    threshold_count = int(sys.argv[2])
    threshold_days = int(sys.argv[3])
    threshold_hits = int(sys.argv[4])

    with open(file_path) as f:
        lines = f.read().split('\n')

    entries = []
    for i, line in enumerate(lines):
        m = re.match(r'^## \[(.+?)\] (.+)', line)
        if m:
            title = m.group(2)
            entry_date = None
            hits = 1
            if i + 1 < len(lines):
                meta = re.match(r'<!-- @(\d{4}-\d{2}-\d{2}) hits:(\d+) -->', lines[i+1])
                if meta:
                    entry_date = datetime.strptime(meta.group(1), '%Y-%m-%d').date()
                    hits = int(meta.group(2))
            entries.append({
                'title': title,
                'date': entry_date,
                'hits': hits
            })

    if not entries:
        sys.exit(0)

    today = date.today()
    total = len(entries)
    age_candidates = []
    hit_candidates = []

    for e in entries:
        if e['date']:
            age_days = (today - e['date']).days
            if age_days >= threshold_days:
                age_candidates.append((e['title'], age_days))
        if e['hits'] >= threshold_hits:
            hit_candidates.append((e['title'], e['hits']))

    triggers = []
    if total >= threshold_count:
        triggers.append(f"数量触发(>={threshold_count}): 当前 {total} 条")
    if age_candidates:
        items = ', '.join(f'"{t}"({d}天)' for t, d in age_candidates[:5])
        triggers.append(f"年龄候选(>={threshold_days}天): {items}")
    if hit_candidates:
        items = ', '.join(f'"{t}"({h}次)' for t, h in hit_candidates[:5])
        triggers.append(f"高频候选(>={threshold_hits}次): {items}")

    if triggers:
        print(f"[升华提醒] claude-next.md 有 {total} 条教训，检测到升华信号:")
        for t in triggers:
            print(f" - {t}")
        print("请发起升华审查: 将成熟教训迁入 kernel.md 或 style-guide.md，已升华条目记入「升华归档记录」")
except Exception:
    pass
PYEOF
fi

# 重置轮次计数器（新会话从 0 开始）
TURNS_FILE="$PROJECT_ROOT/.omc/state/session-turns.json"
if [ -f "$TURNS_FILE" ]; then
    echo '{"count": 0, "updated": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"}' > "$TURNS_FILE"
fi

# 清除 LSP 首次提醒标记（新会话重新首次提醒）
rm -f "$PROJECT_ROOT/.omc/state/lsp-suggested"

# 清除 Read 追踪日志（新会话重新追踪）
rm -f "$PROJECT_ROOT/.omc/state/read-files.log" "$PROJECT_ROOT/.omc/state/read-files.log.lock"

# 注入上次会话交接备忘录（优先于快照，内容更丰富）
HANDOFF_FILE="$PROJECT_ROOT/.omc/state/session-handoff.md"
HANDOFF_ENABLED=$(hc_get "session_handoff.enabled" "true")
SNAPSHOT_EXPIRY=$(hc_get "knowledge.snapshot_expiry_sec" "86400")

if [ "$HANDOFF_ENABLED" = "true" ] && [ -f "$HANDOFF_FILE" ]; then
    # 检查过期（与 snapshot 相同逻辑）
    python3 - "$HANDOFF_FILE" "$SNAPSHOT_EXPIRY" <<'PYEOF'
import sys, os
from datetime import datetime, timezone

handoff_path = sys.argv[1]
expiry_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 86400

try:
    mtime = os.path.getmtime(handoff_path)
    age = datetime.now(timezone.utc).timestamp() - mtime
    if age > expiry_sec:
        sys.exit(0)
    with open(handoff_path) as f:
        content = f.read().strip()
    if content:
        print("[上次会话交接]")
        print(content)
        print("---")
except Exception:
    pass
PYEOF
fi

# 注入未解决的错误记忆（从 error-dna.json 直接读取）
DNA_FILE="$PROJECT_ROOT/.omc/state/error-dna.json"
DNA_ENABLED=$(hc_get "error_dna" "true")

if [ "$DNA_ENABLED" = "true" ] && [ -f "$DNA_FILE" ]; then
    python3 - "$DNA_FILE" <<'PYEOF'
import json, sys

try:
    with open(sys.argv[1]) as f:
        dna = json.load(f)

    unfixed = [e for e in dna if e.get('status') != 'fixed']
    reopened = [e for e in dna if e.get('status') == 'reopened']

    if unfixed or reopened:
        print("[错误记忆]")
        if reopened:
            print("⚠️ 反复出现的错误:")
            for e in reopened[:3]:
                sig = e.get('signature', '(unknown)')[:80]
                count = e.get('count', 1)
                fix_count = e.get('fix_count', 0)
                print(f" - [{count}次, 修过{fix_count}次] {sig}")
                if e.get('fix_context'):
                    print(f" 上次修复相关文件: {', '.join(e['fix_context'])}")
        if unfixed:
            new_errors = [e for e in unfixed if e.get('status') != 'reopened']
            if new_errors:
                print("未解决的错误:")
                for e in new_errors[:3]:
                    sig = e.get('signature', '(unknown)')[:80]
                    count = e.get('count', 1)
                    print(f" - [{count}次] {sig}")
        print("---")
except Exception:
    pass
PYEOF
fi

# 注入上次会话快照（仅当快照在配置的过期时间内时输出）
SNAPSHOT_FILE="$PROJECT_ROOT/.omc/state/session-snapshot.json"
SNAPSHOT_EXPIRY=$(hc_get "knowledge.snapshot_expiry_sec" "86400")
if [ -f "$SNAPSHOT_FILE" ]; then
    python3 - "$SNAPSHOT_FILE" "$SNAPSHOT_EXPIRY" <<'PYEOF'
import json, sys
from datetime import datetime, timezone

try:
    with open(sys.argv[1]) as f:
        snap = json.load(f)

    expiry_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 86400
    ts_str = snap.get("timestamp", "")
    if not ts_str:
        sys.exit(0)

    snap_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_seconds = (now - snap_time).total_seconds()

    if age_seconds > expiry_sec:
        sys.exit(0)

    branch = snap.get("branch", "(unknown)")
    turns = snap.get("turns", 0)
    modified = snap.get("modified_files", [])
    staged = snap.get("staged_files", [])

    modified_str = ", ".join(modified[:10]) if modified else "(none)"
    staged_str = ", ".join(staged[:10]) if staged else "(none)"

    if len(modified) > 10:
        modified_str += f" ... and {len(modified)-10} more"

    print("[上次会话快照]")
    print(f"分支: {branch}")
    print(f"轮次: {turns}")
    print(f"未提交修改: {modified_str}")
    print(f"已暂存: {staged_str}")
    print("---")
except Exception:
    pass
PYEOF
fi
