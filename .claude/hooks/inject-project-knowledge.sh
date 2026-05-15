#!/usr/bin/env bash
# inject-project-knowledge.sh — SessionStart — 注入 .claude/ 核心知识到 AI context
# Role: 注入 .claude/ 核心知识到 AI context

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

# R39: 注入预算强制 (~120 行 / ~3KB)，超出时 stderr 告警
R39_BUDGET_LINES=120
r39_used=0

set -f
for entry in $INJECT_FILES; do
    # 解析 filename:mode 格式
    FILE_NAME="${entry%%:*}"
    MODE="${entry##*:}"
    FILE_PATH="$CLAUDE_DIR/$FILE_NAME"

    [ ! -f "$FILE_PATH" ] && continue

    if [ "$MODE" = "full" ]; then
        FILE_LINES=$(wc -l < "$FILE_PATH" | tr -d ' ')
        r39_used=$((r39_used + FILE_LINES + 2))
        echo "[.claude/$FILE_NAME]"
        cat "$FILE_PATH"
        echo ""
    elif [ "$MODE" = "summary" ]; then
        r39_used=$((r39_used + 35))
        LINES=$(wc -l < "$FILE_PATH" | tr -d ' ')
        echo "[.claude/$FILE_NAME ${LINES}行] 章节:"
        grep "^##" "$FILE_PATH" | head -30
        echo "--- 完整内容请Read .claude/$FILE_NAME"
        echo ""
    fi
done
set +f

# R39: 预算超限告警（不阻断，仅 stderr 通知）
if [ $r39_used -gt $R39_BUDGET_LINES ]; then
    echo "⚠️ [R39 注入预算] 预估 ~${r39_used} 行 > ${R39_BUDGET_LINES} 行上限。建议归档不常用内容到 reference/ 或降级为 summary 模式。" >&2
fi

# 注入 skill 关联图谱（C7 关联编排）
SKILL_GRAPH="$PROJECT_ROOT/.claude/reference/skill-graph.md"
if [ -f "$SKILL_GRAPH" ]; then
    echo "[.claude/reference/skill-graph.md 线上]"
    grep -E '^\|' "$SKILL_GRAPH" 2>/dev/null | head -16
    echo "--- 完整图谱请Read .claude/reference/skill-graph.md"
    echo ""
fi

# 注入当前 Pipeline Step（C3 流程结构化）
PIPELINE_STEP_SCRIPT="$PROJECT_ROOT/.claude/scripts/pipeline-step.sh"
if [ -f "$PIPELINE_STEP_SCRIPT" ]; then
    PIPELINE_CTX=$(bash "$PIPELINE_STEP_SCRIPT" inject 2>/dev/null)
    if [ -n "$PIPELINE_CTX" ]; then
        echo "$PIPELINE_CTX"
    fi
fi

# 注入会话健康检查（抗衰减）
HEALTH_SCRIPT="$PROJECT_ROOT/.claude/scripts/session-health-check.sh"
if [ -f "$HEALTH_SCRIPT" ]; then
    HEALTH_CTX=$(bash "$HEALTH_SCRIPT" inject 2>/dev/null)
    if [ -n "$HEALTH_CTX" ]; then
        echo "$HEALTH_CTX"
    fi
fi

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
        m = re.match(r'^### \[(.+?)\] (.+)', line)
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
rm -f "$PROJECT_ROOT/.omc/state/read-tracker.txt" "$PROJECT_ROOT/.omc/state/read-tracker.txt.lock"

# 注上次 knowledge-condenser 报告（Stop hook 写入）
KC_REPORT="$PROJECT_ROOT/.omc/state/knowledge-condenser-report.txt"
if [ -f "$KC_REPORT" ]; then
    echo "[knowledge-condenser 待处理建议]"
    cat "$KC_REPORT"
    echo "---"
    rm -f "$KC_REPORT"
fi

# error-dna-retrospective.txt: REMOVED — file never created in production (ED-01)

# 注入 Error-DNA 逃逸检测摘要（最近 24h）
DNA_JSONL="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
ESCAPE_ENABLED=$(hc_get "escape_detection.enabled" "true")
if [ "$ESCAPE_ENABLED" = "true" ] && [ -f "$DNA_JSONL" ]; then
    ESC_SUMMARY=$(python3 - "$DNA_JSONL" <<'ESCEOF'
import json, sys, time

jsonl_path = sys.argv[1]
now_ts = int(time.time())
window = 86400  # 24h
escapes = {'governance_bypass': [], 'captcha_forgery': []}

try:
    with open(jsonl_path) as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                if not rec: continue
                et = rec.get('escape_type', '')
                if et in escapes:
                    if now_ts - rec.get('ts', 0) < window:
                        escapes[et].append(rec)
            except: pass

    total = sum(len(v) for v in escapes.values())
    if total == 0: sys.exit(0)

    print(f"[Error-DNA 逃逸检测] 最近 24h 检测到 {total} 次逃逸行为:")
    if escapes['governance_bypass']:
        print(f"  E1(治理绕过): {len(escapes['governance_bypass'])}次")
        for e in escapes['governance_bypass'][-3:]:
            print(f"    · {e.get('message', '')[:120]}")
    if escapes['captcha_forgery']:
        print(f"  E2(验证码伪造): {len(escapes['captcha_forgery'])}次")
        for e in escapes['captcha_forgery'][-3:]:
            print(f"    · {e.get('message', '')[:120]}")
    import os as _os
    _pp = _os.path.join(_os.path.dirname(jsonl_path), 'escape-patches.json')
    if _os.path.exists(_pp):
        try:
            with open(_pp) as _pf:
                _ap = json.load(_pf)
            _pend = sum(1 for p in _ap.values() if p.get('status') == 'pending')
            if _pend:
                print(f"  ⚠️ {_pend} 条补丁待审 → bash .claude/scripts/escape-patch-apply.sh status")
        except: pass
except: pass
ESCEOF
)
    if [ -n "$ESC_SUMMARY" ]; then
        echo "$ESC_SUMMARY"
        echo "---"
    fi
fi

# 注入飞轮废弃技能报告
FLYWHEEL_DEP="$PROJECT_ROOT/.omc/state/flywheel-deprecated-skills.txt"
if [ -f "$FLYWHEEL_DEP" ]; then
    echo "[flywheel 废弃技能]"
    cat "$FLYWHEEL_DEP"
    echo "---"
    rm -f "$FLYWHEEL_DEP"
fi

# 注入上次会话交接备忘录（优先于快照，内容更丰富）
HANDOFF_FILE="$PROJECT_ROOT/.omc/state/session-handoff.md"
HANDOFF_ENABLED=$(hc_get "session_handoff.enabled" "true")
SNAPSHOT_EXPIRY=$(hc_get "knowledge.snapshot_expiry_sec" "86400")

if [ "$HANDOFF_ENABLED" = "true" ] && [ -f "$HANDOFF_FILE" ]; then
    # 检查过期（与 snapshot 相同逻辑）
    python3 - "$HANDOFF_FILE" "$SNAPSHOT_EXPIRY" <<'PYEOF'
import sys, os, re
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
        # 提取 Next Steps 区块并高亮显示
        next_section = re.search(r'## Next Steps\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if next_section:
            next_text = next_section.group(1).strip()
            print(f"> 下一步: {next_text[:200]}")
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

    signatures = dna.get('error_signatures', {})

    reopened_errors = {}
    unfixed_errors = {}

    for sig, entry in signatures.items():
        status = entry.get('status', 'active')
        if status == 'reopened':
            reopened_errors[sig] = entry
        elif status != 'fixed':
            unfixed_errors[sig] = entry

    # Separate actionable vs historical (older than 7 days without new hits)
    import time
    now_ts = int(time.time())
    seven_days = 7 * 86400
    actionable = {}
    historical = {}
    for sig, e in (unfixed_errors | reopened_errors).items():
        last_seen = e.get('last_seen', 0)
        count = e.get('count', 1)
        # entries with last_seen >7d and count>100 are historical artifacts
        if last_seen > 0 and (now_ts - last_seen) > seven_days and count >= 10:
            historical[sig] = e
        else:
            actionable[sig] = e

    if actionable or historical:
        print("[错误记忆]")
        print(f"  总计 {len(signatures)} 条签名, {len(actionable)} 活跃可操作, {len(historical)} 历史归档")
        if actionable:
            for sig, e in list(actionable.items())[:3]:
                count = e.get('count', 1)
                fix_count = e.get('fix_count', 0)
                message = e.get('message', '(unknown)')[:80]
                print(f" - [×{count}, 修过{fix_count}次] {message}")
                if e.get('fix_context'):
                    print(f"   修复相关文件: {', '.join(e['fix_context'])}")
        if historical:
            print(f"  ({len(historical)} 条为 >7天历史记录，不影响当前会话)")
        print("---")
except Exception:
    pass
PYEOF
fi

# C5: Tool-level health summary (error rate by type)
TOTAL_OPS_FILE="$PROJECT_ROOT/.omc/state/total-ops.txt"
DNA_JSONL="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
if [ -f "$DNA_JSONL" ] && [ -f "$TOTAL_OPS_FILE" ]; then
    python3 - "$DNA_JSONL" "$TOTAL_OPS_FILE" <<'PYEOF'
import json, sys
try:
    jsonl_path, ops_path = sys.argv[1], sys.argv[2]
    total_ops = int(open(ops_path).read().strip())
    tool_types = {}
    with open(jsonl_path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                t = rec.get('error_type', 'unknown')
                tool_types[t] = tool_types.get(t, 0) + 1
            except: pass
    if tool_types:
        total_err = sum(tool_types.values())
        rate = total_err * 100 // total_ops if total_ops > 0 else 0
        print(f"[工具健康] 总操作: {total_ops}, 总错误: {total_err} ({rate}%)")
        for t, c in sorted(tool_types.items(), key=lambda x: -x[1])[:5]:
            print(f"  [{t}] ×{c}")
except: pass
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

# === GS-004 5.2: 治理一致性告警 ===
GOV_AUDIT_SCRIPT="$PROJECT_ROOT/.claude/scripts/audit-hooks.sh"
if [ -f "$GOV_AUDIT_SCRIPT" ]; then
    GOV_OUTPUT=$(bash "$GOV_AUDIT_SCRIPT" --json 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    red = d.get('issue_count_red', 0)
    yellow = d.get('issue_count_yellow', 0)
    if red == 0 and yellow == 0:
        sys.exit(0)
    print('[governance-drift] {} 🔴, {} 🟡 治理漂移 — 运行 audit-hooks.sh 查看详情'.format(red, yellow))
    issues = d.get('issues', [])
    for iss in issues[:3]:
        print(' · [{}] {}: {}'.format(iss['level'], iss['script'], iss['message'][:120]))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$GOV_OUTPUT" ]; then
        echo "$GOV_OUTPUT"
    fi
fi

# 注入 Retry Budget 状态（C9 修复上限追踪）
RETRY_SCRIPT="$PROJECT_ROOT/.claude/scripts/retry-budget.sh"
if [ -f "$RETRY_SCRIPT" ]; then
    RETRY_CTX=$(bash "$RETRY_SCRIPT" check 2>&1)
    RETRY_EXIT=$?
    if [ $RETRY_EXIT -eq 2 ] && [ -n "$RETRY_CTX" ]; then
        echo "$RETRY_CTX"
    fi
fi

# 注入 Session Dump 恢复上下文（E8 跨会话恢复）
SESSION_DUMP="$PROJECT_ROOT/.omc/state/session-dump.json"
if [ -f "$SESSION_DUMP" ]; then
    python3 -c "
import json, os
try:
    with open('$SESSION_DUMP') as f:
        d = json.load(f)
except:
    exit(0)

parts = []

gs = d.get('git_state', {})
mf = gs.get('modified_files', [])
if mf:
    parts.append('[session-dump] 上次会话状态: 分支=%s | 轮次=%s | 修改文件=%d' % (gs.get('branch','?'), gs.get('turns',0), len(mf)))
    for f in mf[:6]:
        parts.append('  * %s' % f)
    if len(mf) > 6:
        parts.append('  * ... 共 %d 个文件' % len(mf))

af = d.get('active_features', [])
if af:
    feat_names = []
    for a in af:
        if isinstance(a, dict):
            feat_names.append(str(a.get('name', a.get('feature', ''))))
        else:
            feat_names.append(str(a))
    parts.append('活跃特性: %s' % ' | '.join(feat_names[:4]))

es = d.get('error_summary', {})
unfixed = es.get('unfixed_count', 0)
if unfixed > 0 and unfixed < 50:
    parts.append('未修复错误: %d 个' % unfixed)
elif unfixed >= 50:
    parts.append('未修复错误: %d 个（大量噪音）' % unfixed)

tq = d.get('todo_queue', [])
if tq:
    parts.append('待办 (%d): 见 todo-queue.md' % len(tq))

cn = d.get('claude_next_hits', [])
if cn:
    parts.append('近期教训 (%d):' % len(cn))
    for h in cn[:3]:
        label = h[:120] if isinstance(h, str) else str(h.get('title', ''))[:120]
        parts.append('  * %s' % label)

el = d.get('edit_log', [])
if el:
    parts.append('上次会话编辑: %d 个文件' % len(el))

if parts:
    print('[session-recovery]')
    for p in parts:
        print(p)
    print('--- 完整 dump: Read .omc/state/session-dump.json')
" 2>/dev/null || true
fi
