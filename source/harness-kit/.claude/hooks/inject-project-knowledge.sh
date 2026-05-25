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

# R39: 注入预算强制 (~120 行 / ~3KB)，超限时硬截断（C2 fix: 从 stderr 警告升级为硬约束）
R39_BUDGET_LINES=120
r39_used=0
R39_EXCEEDED=false

set -f
for entry in $INJECT_FILES; do
    # R39 硬截断: 预算已超 → 剩余 full 模式降级为 summary 行引用
    if [ "$R39_EXCEEDED" = true ]; then
        FILE_NAME="${entry%%:*}"
        MODE="${entry##*:}"
        FILE_PATH="$CLAUDE_DIR/$FILE_NAME"
        [ ! -f "$FILE_PATH" ] && continue
        echo "[.claude/$FILE_NAME] ⏭ R39 预算已满，请 Read 查看"
        continue
    fi

    # 解析 filename:mode 格式
    FILE_NAME="${entry%%:*}"
    MODE="${entry##*:}"
    FILE_PATH="$CLAUDE_DIR/$FILE_NAME"

    [ ! -f "$FILE_PATH" ] && continue

    if [ "$MODE" = "full" ]; then
        FILE_LINES=$(wc -l < "$FILE_PATH" | tr -d ' ')
        # DG-96 C2 fix: 先检查是否会超预算，再决定全量/部分/跳过
        if [ $((r39_used + FILE_LINES + 2)) -gt $R39_BUDGET_LINES ]; then
            REMAINING=$((R39_BUDGET_LINES - r39_used - 2))
            if [ "$REMAINING" -gt 10 ]; then
                # 部分注入: 预算有剩余空间，注入前 N 行
                r39_used=$((r39_used + REMAINING + 2))
                echo "[.claude/$FILE_NAME 前${REMAINING}/${FILE_LINES}行]"
                head -"$REMAINING" "$FILE_PATH" | hc_sanitize_utf8
                echo "--- ⏭ R39 预算限制，剩余 $(($FILE_LINES - REMAINING)) 行请 Read"
                echo ""
                R39_EXCEEDED=true
                flywheel_event "inject_project_knowledge" "triggered" "P2" || true
                echo "⚠️ [R39 注入预算] 已超 ${R39_BUDGET_LINES} 行上限，后续文件仅摘要。" >&2
            else
                # 预算几乎耗尽 (<10行)，跳过此文件
                R39_EXCEEDED=true
                echo "[.claude/$FILE_NAME] ⏭ R39 预算已满 (剩余 ${REMAINING} 行)，请 Read 查看"
                flywheel_event "inject_project_knowledge" "triggered" "P2" || true
            fi
            continue
        fi
        r39_used=$((r39_used + FILE_LINES + 2))
        echo "[.claude/$FILE_NAME]"
        cat "$FILE_PATH" | hc_sanitize_utf8
        echo ""
    elif [ "$MODE" = "summary" ]; then
        # summary 模式固定 ~35 行，若预算不足则跳过
        if [ $((r39_used + 35)) -gt $R39_BUDGET_LINES ]; then
            R39_EXCEEDED=true
            echo "[.claude/$FILE_NAME] ⏭ R39 预算已满，请 Read 查看"
            continue
        fi
        r39_used=$((r39_used + 35))
        LINES=$(wc -l < "$FILE_PATH" | tr -d ' ')
        echo "[.claude/$FILE_NAME ${LINES}行] 章节:"
        grep "^##" "$FILE_PATH" | head -30
        echo "--- 完整内容请Read .claude/$FILE_NAME"
        echo ""
    fi
done
set +f

# 注入 skill 关联图谱（C7 关联编排）
SKILL_GRAPH="$PROJECT_ROOT/.claude/reference/skill-graph.md"
if [ -f "$SKILL_GRAPH" ]; then
    echo "[.claude/reference/skill-graph.md 线上]"
    grep -E '^\|' "$SKILL_GRAPH" 2>/dev/null | head -16 | hc_sanitize_utf8
    echo "--- 完整图谱请Read .claude/reference/skill-graph.md"
    echo ""
fi

# 注入当前 Pipeline Step（C3 流程结构化）
PIPELINE_STEP_SCRIPT="$PROJECT_ROOT/.claude/scripts/pipeline-step.sh"
if [ -f "$PIPELINE_STEP_SCRIPT" ]; then
    PIPELINE_CTX=$(bash "$PIPELINE_STEP_SCRIPT" inject 2>/dev/null)
    if [ -n "$PIPELINE_CTX" ]; then
        echo "$PIPELINE_CTX" | hc_sanitize_utf8
    fi
fi

# 注入会话健康检查（抗衰减）
HEALTH_SCRIPT="$PROJECT_ROOT/.claude/scripts/session-health-check.sh"
if [ -f "$HEALTH_SCRIPT" ]; then
    HEALTH_CTX=$(bash "$HEALTH_SCRIPT" inject 2>/dev/null)
    if [ -n "$HEALTH_CTX" ]; then
        echo "$HEALTH_CTX" | hc_sanitize_utf8
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
    ${PYTHON_BIN:-python3} - "$CLAUDE_NEXT" "$SUB_COUNT" "$SUB_DAYS" "$SUB_HITS" <<'PYEOF'
import re, sys
from datetime import datetime, date

try:
    file_path = sys.argv[1]
    threshold_count = int(sys.argv[2])
    threshold_days = int(sys.argv[3])
    threshold_hits = int(sys.argv[4])

    with open(file_path, encoding="utf-8") as f:
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
    cat "$KC_REPORT" | hc_sanitize_utf8
    echo "---"
    rm -f "$KC_REPORT"
fi

# error-dna-retrospective.txt: REMOVED — file never created in production (ED-01)

# 注入 Error-DNA 逃逸检测摘要（最近 24h）
DNA_JSONL="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
ESCAPE_ENABLED=$(hc_get "escape_detection.enabled" "true")
if [ "$ESCAPE_ENABLED" = "true" ] && [ -f "$DNA_JSONL" ]; then
    ESC_SUMMARY=$(${PYTHON_BIN:-python3} - "$DNA_JSONL" <<'ESCEOF'
import json, sys, time

jsonl_path = sys.argv[1]
now_ts = int(time.time())
window = 86400  # 24h
escapes = {'governance_bypass': [], 'captcha_forgery': []}

try:
    with open(jsonl_path, encoding="utf-8") as f:
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
            with open(_pp, encoding="utf-8") as _pf:
                _ap = json.load(_pf)
            _pend = sum(1 for p in _ap.values() if p.get('status') == 'pending')
            if _pend:
                print(f"  ⚠️ {_pend} 条补丁待审 → bash .claude/scripts/escape-patch-apply.sh status")
        except: pass
except: pass
ESCEOF
)
    if [ -n "$ESC_SUMMARY" ]; then
        echo "$ESC_SUMMARY" | hc_sanitize_utf8
        echo "---"
    fi
fi

# 注入飞轮废弃技能报告
FLYWHEEL_DEP="$PROJECT_ROOT/.omc/state/flywheel-deprecated-skills.txt"
if [ -f "$FLYWHEEL_DEP" ]; then
    echo "[flywheel 废弃技能]"
    cat "$FLYWHEEL_DEP" | hc_sanitize_utf8
    echo "---"
    rm -f "$FLYWHEEL_DEP"
fi

# 注入上次会话交接备忘录（优先于快照，内容更丰富）
HANDOFF_FILE="$PROJECT_ROOT/.omc/state/session-handoff.md"
HANDOFF_ENABLED=$(hc_get "session_handoff.enabled" "true")
SNAPSHOT_EXPIRY=$(hc_get "knowledge.snapshot_expiry_sec" "86400")

if [ "$HANDOFF_ENABLED" = "true" ] && [ -f "$HANDOFF_FILE" ]; then
    # 检查过期（与 snapshot 相同逻辑）
    ${PYTHON_BIN:-python3} - "$HANDOFF_FILE" "$SNAPSHOT_EXPIRY" <<'PYEOF' | hc_sanitize_utf8
import sys, os, re
from datetime import datetime, timezone

handoff_path = sys.argv[1]
expiry_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 86400

try:
    mtime = os.path.getmtime(handoff_path)
    age = datetime.now(timezone.utc).timestamp() - mtime
    if age > expiry_sec:
        sys.exit(0)
    with open(handoff_path, encoding="utf-8") as f:
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
    ${PYTHON_BIN:-python3} - "$DNA_FILE" <<'PYEOF' | hc_sanitize_utf8
import json, sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
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

# C5: Tool-level health summary (双 pipeline — escape + signals)
TOTAL_OPS_FILE="$PROJECT_ROOT/.omc/state/total-ops.txt"
DNA_JSONL="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
SIGNALS_JSONL="$PROJECT_ROOT/.omc/state/error-signals.jsonl"
if [ -f "$TOTAL_OPS_FILE" ]; then
    ${PYTHON_BIN:-python3} - "$DNA_JSONL" "$SIGNALS_JSONL" "$TOTAL_OPS_FILE" <<'PYEOF' | hc_sanitize_utf8
import json, sys, os
try:
    dna_path, signals_path, ops_path = sys.argv[1], sys.argv[2], sys.argv[3]
    total_ops = int(open(ops_path, encoding="utf-8").read().strip())
    tool_types = {}
    for jp in [dna_path, signals_path]:
        if os.path.exists(jp):
            with open(jp, encoding="utf-8") as f:
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
    ${PYTHON_BIN:-python3} - "$SNAPSHOT_FILE" "$SNAPSHOT_EXPIRY" <<'PYEOF' | hc_sanitize_utf8
import json, sys
from datetime import datetime, timezone

try:
    with open(sys.argv[1], encoding="utf-8") as f:
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
    GOV_OUTPUT=$(bash "$GOV_AUDIT_SCRIPT" --json 2>/dev/null | ${PYTHON_BIN:-python3} -c "
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
        echo "$GOV_OUTPUT" | hc_sanitize_utf8
    fi
fi



# ─── 跨会话恢复提示 (Session Recovery) ───
SESSION_DUMP="$PROJECT_ROOT/.omc/state/session-dump.json"
TODO_QUEUE="$PROJECT_ROOT/.omc/state/todo-queue.md"
HANDOFF="$PROJECT_ROOT/.omc/state/session-handoff.md"

HAS_PREV=false
[ -f "$SESSION_DUMP" ] && HAS_PREV=true
[ -f "$TODO_QUEUE" ] && HAS_PREV=true
[ -f "$HANDOFF" ] && HAS_PREV=true

if [ "$HAS_PREV" = true ]; then
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║  📋 检测到上次会话未完成的任务       ║"
    echo "╠══════════════════════════════════════╣"

    # Last session summary
    if [ -f "$SESSION_DUMP" ]; then
        ${PYTHON_BIN:-python3} -c "
import json
try:
    with open('$SESSION_DUMP', encoding="utf-8") as f: d = json.load(f)
    gs = d.get('git_state',{})
    br = gs.get('branch','?')
    mf = gs.get('modified_files',[])
    print(f'║  分支: {br}  修改文件: {len(mf)}个')
    tq = d.get('todo_queue',[])
    if tq:
        for t in tq[:3]:
            print(f'║  · {str(t)[:80]}')
except: pass
" 2>/dev/null
    fi

    # TODO summary
    if [ -f "$TODO_QUEUE" ]; then
        TODO_COUNT=$(grep -c '^\- \[ \]' "$TODO_QUEUE" 2>/dev/null || echo 0)
        echo "║  待办: ${TODO_COUNT}项"
    fi

    # Handoff
    if [ -f "$HANDOFF" ]; then
        NEXT_STEP=$(grep '下一步\|Next' "$HANDOFF" 2>/dev/null | head -1 || echo '')
        [ -n "$NEXT_STEP" ] && echo "║  ${NEXT_STEP:0:70}"
    fi

    echo "╠══════════════════════════════════════╣"
    echo "║  输入「继续」→ 恢复上次任务         ║"
    echo "║  输入「重新开始」→ 从零开始         ║"
    echo "║  不回应 → 默认继续                  ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
fi

# 注入 Retry Budget 状态（C9 修复上限追踪）
RETRY_SCRIPT="$PROJECT_ROOT/.claude/scripts/retry-budget.sh"
if [ -f "$RETRY_SCRIPT" ]; then
    RETRY_CTX=$(bash "$RETRY_SCRIPT" check 2>&1)
    RETRY_EXIT=$?
    if [ $RETRY_EXIT -eq 2 ] && [ -n "$RETRY_CTX" ]; then
        echo "$RETRY_CTX" | hc_sanitize_utf8
    fi
fi

# 注入 Session Dump 恢复上下文（E8 跨会话恢复）
SESSION_DUMP="$PROJECT_ROOT/.omc/state/session-dump.json"
if [ -f "$SESSION_DUMP" ]; then
    ${PYTHON_BIN:-python3} -c "
import json, os
try:
    with open('$SESSION_DUMP', encoding="utf-8") as f:
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
" | hc_sanitize_utf8 2>/dev/null || true
fi

# ─── 自主模式决策链注入 ───
# 当 goal/ghost 模式激活时，将决策链注入 AI 上下文
# 哲学 #3(先守护): 决策链提供硬边界保护 
# 哲学 #4(没验证=没做): 决策链强制 Oracle/Meta-Oracle 验证
# 哲学 #5(以人为本): 减少心智负担 — AI 自主决策，人仅在最后审核
# 哲学 #6(0信任): 决策链物理注入上下文，不依赖 AI 记忆
STATE_DIR="$PROJECT_ROOT/.omc/state"
CURRENT_MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")
if [ "$CURRENT_MODE" != "normal" ]; then
    DECISION_CHAIN="$PROJECT_ROOT/.claude/reference/autonomous-decision-chain.md"
    if [ -f "$DECISION_CHAIN" ]; then
        echo "[.claude/reference/autonomous-decision-chain.md]"
        cat "$DECISION_CHAIN" | hc_sanitize_utf8
        echo ""
    else
        echo "⚠️ [自主模式] 决策链文件缺失: $DECISION_CHAIN" >&2
    fi
fi

# ─── 日常任务工作区注入（哲学 #7 物化） ───
# 活跃/最近的任务工作区让 AI 知道"之前做了什么"，人无需重复解释
# .omc/state/tasks/{datetime}-{slug}/ 目录通过时间戳天然索引行为
TASKS_DIR="$STATE_DIR/tasks"
if [ -d "$TASKS_DIR" ]; then
    CURRENT_TASK=$(readlink "$TASKS_DIR/.active" 2>/dev/null || echo "")
    if [ -n "$CURRENT_TASK" ] && [ -d "$CURRENT_TASK" ]; then
        TASK_NAME=$(basename "$CURRENT_TASK")
        echo "[任务工作区] 🟢 活跃: $TASK_NAME"
        head -1 "$CURRENT_TASK/prd.md" 2>/dev/null
        echo "  .omc/state/tasks/$TASK_NAME/"
        echo ""
    fi
    # 最近 3 天的工作区（按时间倒序，最多 5 个）
    RECENT_TASKS=$(ls -dt "$TASKS_DIR"/*/ 2>/dev/null | grep -v '.active' | head -5)
    if [ -n "$RECENT_TASKS" ]; then
        echo "[任务工作区] 📋 最近:"
        for _td in $RECENT_TASKS; do
            _tn=$(basename "$_td")
            _status="✅"
            grep -q '🟢 进行中' "$_td/prd.md" 2>/dev/null && _status="🟢"
            echo "  $_status $_tn"
        done
        echo "  人提及'刚才/上次/那个任务'时 → 按时间找对应目录 → task-workspace.sh resume <id>"
        echo ""
    fi
fi

# ─── 待决策清单注入（b-mode 问题分流） ───
# 哲学 #5(以人为本): 非自主模式下发现的问题结构化记录，SessionStart 时提醒用户决策
# issue-triage.sh → pending-triage.md → 此处注入
# 使用 pending-triage.md 独立文件，避免与 lx-oma-gov 的 pending-decisions.md 冲突
PENDING_TRIAGE="$STATE_DIR/pending-triage.md"
if [ -f "$PENDING_TRIAGE" ]; then
    # 统计待决策项（按优先级）— DG-36 fix: grep -c 输出 "0" 时 exit 1, 不可用 || echo 0
    P0_COUNT=$(grep -c '^\### .*\[P0\]' "$PENDING_TRIAGE" 2>/dev/null); P0_COUNT="${P0_COUNT:-0}"
    P1_COUNT=$(grep -c '^\### .*\[P1\]' "$PENDING_TRIAGE" 2>/dev/null); P1_COUNT="${P1_COUNT:-0}"
    P2_COUNT=$(grep -c '^\### .*\[P2\]' "$PENDING_TRIAGE" 2>/dev/null); P2_COUNT="${P2_COUNT:-0}"
    P3_COUNT=$(grep -c '^\### .*\[P3\]' "$PENDING_TRIAGE" 2>/dev/null); P3_COUNT="${P3_COUNT:-0}"
    TOTAL=$(( P0_COUNT + P1_COUNT + P2_COUNT + P3_COUNT ))
    if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
        echo ""
        echo "📋 [待决策清单] ${TOTAL} 项待用户决策（P0:${P0_COUNT} P1:${P1_COUNT} P2:${P2_COUNT} P3:${P3_COUNT}）"
        echo "   → Read .omc/state/pending-triage.md 查看详情"
        echo "   → 决策后删除对应条目，或 rm -f .omc/state/pending-triage.md 清除全部"
        if [ "$P0_COUNT" -gt 0 ] 2>/dev/null; then
            echo "   ⚠️ 含 ${P0_COUNT} 项 P0 安全问题，建议优先处理！"
        fi
        echo ""
    fi
fi

# ─── 自动优化追踪注入（a-mode 问题分流消费者） ───
# 哲学 #2(少量大增益): a-mode 自主优化历史 → 此处注入 AI 上下文
# issue-triage.sh → auto-optimizations.jsonl → 此处消费
AUTO_OPT="$STATE_DIR/auto-optimizations.jsonl"
if [ -f "$AUTO_OPT" ] && [ -s "$AUTO_OPT" ]; then
    # 统计最近的自动优化记录（24h 内）
    OPT_COUNT=$(${PYTHON_BIN:-python3} -c "
import json, os, time
count = 0
cutoff = time.time() - 86400
try:
    with open('$AUTO_OPT', encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                if rec and rec.get('ts', 0) > cutoff:
                    count += 1
            except:
                pass
except:
    pass
print(count)
" 2>/dev/null || echo 0)
    if [ "$OPT_COUNT" -gt 0 ] 2>/dev/null; then
        echo ""
        echo "🔧 [自动优化] a-mode 最近 24h 自主优化了 ${OPT_COUNT} 项问题"
        echo "   → Read .omc/state/auto-optimizations.jsonl 查看详情"
        echo ""
    fi
fi

# ─── Ghost 退出报告追补检查（L3 事后追补门禁） ───
# 哲学 #4(没验证=没做): ghost --force 关闭时留下 pending 桩，此处检测并提醒补交
# Meta-Oracle C1: 原 L3 完全缺失，此行修复
GHOST_EXIT_PENDING="$STATE_DIR/ghost-exit-pending"
if [ -f "$GHOST_EXIT_PENDING" ]; then
    EXIT_REPORT="$STATE_DIR/ghost-exit-report.md"
    echo ""
    echo "⚠️ [Ghost 退出报告缺失] 上次幽灵模式强制关闭（--force）后未提交退出报告。"
    if [ -f "$EXIT_REPORT" ]; then
        echo "   但已检测到退出报告文件: $EXIT_REPORT"
        echo "   请审阅报告内容，确认无误后 rm -f $GHOST_EXIT_PENDING 清除此提醒。"
    else
        echo "   退出报告文件 ($EXIT_REPORT) 不存在。"
        echo "   建议: 根据上次探索方向补交报告（lx-ghost report '内容'），或 rm -f $GHOST_EXIT_PENDING 清除提醒。"
    fi
    echo ""
fi

# ─── Ghost 会话异常中断检测（B5: 粘性标记） ───
# ghost-session-active-at 在 lx-ghost on 时创建，off 时清理。
# 如果标记存在但 lx-ghost.json 不存在 → 会话异常中断（崩溃/强杀）
GHOST_STICKY="$STATE_DIR/ghost-session-active-at"
if [ -f "$GHOST_STICKY" ] && [ ! -f "$STATE_DIR/lx-ghost.json" ] && [ ! -f "$STATE_DIR/ghost-exit-report.md" ] && [ ! -f "$GHOST_EXIT_PENDING" ]; then
    echo ""
    echo "⚠️ [Ghost 会话异常中断] 上次幽灵模式会话异常结束（会话中断或进程崩溃），未生成退出报告。"
    echo "   请检查探索状态，确认是否需要补交报告。"
    echo "   确认无误后执行: rm -f $GHOST_STICKY"
    echo ""
fi
