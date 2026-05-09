#!/bin/bash
# auto-snapshot.sh — Stop / PostToolUse:Edit|Write — 会话结束时自动保存状态快照（分支/轮次/未提交文件）
# Role: 会话结束时自动保存状态快照（分支/轮次/未提交文件）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "auto_snapshot" || exit 0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

# 读取轮次计数（与 turn-counter.sh 共享状态文件）
TURNS=0
TURNS_FILE="$STATE_DIR/session-turns.json"
if [ -f "$TURNS_FILE" ]; then
    if command -v jq &>/dev/null; then
        TURNS=$(jq -r '.count // 0' "$TURNS_FILE" 2>/dev/null || echo 0)
    else
        TURNS=$(grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' "$TURNS_FILE" 2>/dev/null | sed 's/.*:[[:space:]]*//' | head -1)
        [ -z "$TURNS" ] && TURNS=0
    fi
fi

# 获取当前分支
BRANCH=$(cd "$PROJECT_ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# 获取未提交修改文件列表
MODIFIED_JSON="[]"
MODIFIED_RAW=$(cd "$PROJECT_ROOT" && git diff --name-only 2>/dev/null)
if [ -n "$MODIFIED_RAW" ]; then
    MODIFIED_JSON=$(echo "$MODIFIED_RAW" | python3 -c "
import sys, json
lines = [l.rstrip() for l in sys.stdin if l.rstrip()]
print(json.dumps(lines))" 2>/dev/null || echo "[]")
fi

# 获取已暂存文件列表
STAGED_JSON="[]"
STAGED_RAW=$(cd "$PROJECT_ROOT" && git diff --cached --name-only 2>/dev/null)
if [ -n "$STAGED_RAW" ]; then
    STAGED_JSON=$(echo "$STAGED_RAW" | python3 -c "
import sys, json
lines = [l.rstrip() for l in sys.stdin if l.rstrip()]
print(json.dumps(lines))" 2>/dev/null || echo "[]")
fi

# 生成时间戳
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 写入快照文件
SNAPSHOT_FILE="$STATE_DIR/session-snapshot.json"
python3 - <<PYEOF
import json
snapshot = {
    "timestamp": "$TIMESTAMP",
    "turns": int("$TURNS") if "$TURNS".isdigit() else 0,
    "branch": "$BRANCH",
    "modified_files": $MODIFIED_JSON,
    "staged_files": $STAGED_JSON
}
with open("$SNAPSHOT_FILE", "w") as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)
PYEOF

# SHA256 防篡改摘要
SHA256_FILE="$STATE_DIR/session-snapshot.json.sha256"
if command -v shasum &>/dev/null; then
    shasum -a 256 "$SNAPSHOT_FILE" | awk '{print $1}' > "$SHA256_FILE"
elif command -v sha256sum &>/dev/null; then
    sha256sum "$SNAPSHOT_FILE" | awk '{print $1}' > "$SHA256_FILE"
fi

echo "Session snapshot saved: turns=$TURNS branch=$BRANCH"

# 文档同步检查：本次修改的源文件是否有对应的 executor.md 更新
SOURCE_EXT=$(hc_get "project.source_extensions" "*.go")
EXT_SUFFIX="${SOURCE_EXT#\*}"
MODIFIED_GO_FILES=$(cd "$PROJECT_ROOT" && git diff --name-only 2>/dev/null | grep "\\${EXT_SUFFIX}$" || true)
STAGED_GO_FILES=$(cd "$PROJECT_ROOT" && git diff --cached --name-only 2>/dev/null | grep "\\${EXT_SUFFIX}$" || true)
ALL_GO_FILES=$(echo -e "${MODIFIED_GO_FILES}\n${STAGED_GO_FILES}" | sort -u | grep -v '^$' || true)

if [ -n "$ALL_GO_FILES" ]; then
    GO_COUNT=$(echo "$ALL_GO_FILES" | wc -l | tr -d ' ')
    # 检查 executor.md 是否在本次修改范围内
    EXEC_DOC=$(hc_get "workflow.executor_doc" "executor.md")
    DOC_ROOT=$(hc_get "workflow.doc_root" "rpe")
    PLAN_DOC=$(hc_get "workflow.plan_doc" "plan.md")
    HAS_EXECUTOR_UPDATE=false
    if echo "$MODIFIED_RAW$STAGED_RAW" | grep -q "${EXEC_DOC}"; then
        HAS_EXECUTOR_UPDATE=true
    fi
    if [ "$HAS_EXECUTOR_UPDATE" = false ]; then
        echo ""
        echo "⚠️ 文档同步提醒: 本次修改了 ${GO_COUNT} 个 ${EXT_SUFFIX} 文件但未更新 ${EXEC_DOC}。"
        echo "若涉及状态/接口/行为变更，请同步更新 ${DOC_ROOT}/{feature}/${EXEC_DOC} 和 ${PLAN_DOC}。"
        echo "涉及文件: $(echo "$ALL_GO_FILES" | tr '\n' ', ' | sed 's/,$//')"
    fi
fi

# ─── 生成交接备忘录 ───
HANDOFF_FILE="$STATE_DIR/session-handoff.md"
DOC_ROOT=$(hc_get "workflow.doc_root" "rpe")
EXEC_DOC=$(hc_get "workflow.executor_doc" "executor.md")
HANDOFF_ENABLED=$(hc_get "session_handoff.enabled" "true")
MAX_ADR=$(hc_get "session_handoff.max_adr_lines" "10")
MAX_TODO=$(hc_get "session_handoff.max_todo_lines" "10")
MAX_LESSONS=$(hc_get "session_handoff.max_lessons" "3")

if [ "$HANDOFF_ENABLED" = "true" ]; then
    python3 - "$PROJECT_ROOT" "$DOC_ROOT" "$EXEC_DOC" "$HANDOFF_FILE" "$MAX_ADR" "$MAX_TODO" "$MAX_LESSONS" "$BRANCH" "$TURNS" <<'PYEOF'
import sys, os, re, json
from datetime import datetime

project_root = sys.argv[1]
doc_root = sys.argv[2]
exec_doc = sys.argv[3]
handoff_path = sys.argv[4]
max_adr = int(sys.argv[5])
max_todo = int(sys.argv[6])
max_lessons = int(sys.argv[7])
branch = sys.argv[8]
turns = sys.argv[9]

sections = []
now = datetime.now().strftime("%Y-%m-%d %H:%M")
sections.append(f"# 会话交接备忘录\n> 生成时间: {now} | 分支: {branch} | 轮次: {turns}\n")

# 查找活跃的 executor.md
executor_files = []
rpe_dir = os.path.join(project_root, doc_root)
if os.path.isdir(rpe_dir):
    for feature in os.listdir(rpe_dir):
        epath = os.path.join(rpe_dir, feature, exec_doc)
        if os.path.isfile(epath):
            executor_files.append((feature, epath))

for feature, epath in executor_files:
    try:
        with open(epath) as f:
            content = f.read()
    except:
        continue

    # 正在做什么：grep 🔄 行
    active_steps = re.findall(r'.*🔄.*', content)
    completed_steps = re.findall(r'.*✅.*', content)
    blocked_steps = re.findall(r'.*⛔.*', content)

    if active_steps or completed_steps or blocked_steps:
        sections.append(f"## Feature: {feature}\n")

    if active_steps:
        sections.append("### 🔄 进行中")
        for s in active_steps[:5]:
            sections.append(f"- {s.strip()}")
    if completed_steps or blocked_steps:
        sections.append(f"\n### 进度: ✅ {len(completed_steps)} 完成, 🔄 {len(active_steps)} 进行中, ⛔ {len(blocked_steps)} 阻塞")

    # 关键决策: ADR
    adr_lines = [l.strip() for l in content.split('\n') if 'ADR-' in l]
    if adr_lines:
        sections.append("\n### 关键决策")
        for l in adr_lines[:max_adr]:
            sections.append(f"- {l}")

    # 未完成项: TODO
    todo_lines = [l.strip() for l in content.split('\n') if re.match(r'\s*-\s*\[', l)]
    if todo_lines:
        sections.append("\n### 未完成项")
        for l in todo_lines[:max_todo]:
            sections.append(f"- {l}")

    # 关键决策: 从 executor.md 和 plan.md 扫描决策关键词
    decision_pattern = re.compile(r'决定|选择|确认|方案[A-Ca-c]|采用|用户.*同意|放弃.*改用', re.IGNORECASE)
    decision_lines = [l.strip() for l in content.split('\n') if decision_pattern.search(l) and l.strip()]

    # 同时扫描 plan.md（若存在）
    plan_path = os.path.join(os.path.dirname(epath), 'plan.md')
    if os.path.isfile(plan_path):
        try:
            with open(plan_path) as pf:
                plan_content = pf.read()
            decision_lines += [l.strip() for l in plan_content.split('\n') if decision_pattern.search(l) and l.strip()]
        except:
            pass

    # 去重并截断
    seen = set()
    unique_decisions = []
    for l in decision_lines:
        if l not in seen:
            seen.add(l)
            unique_decisions.append(l)

    if unique_decisions:
        sections.append("\n### 关键决策 (本轮)")
        for l in unique_decisions[:5]:
            sections.append(f"- {l}")

    # 踩坑记录: 从 executor.md 扫描问题关键词
    pitfall_pattern = re.compile(r'踩坑|注意|坑:|问题:|bug|⚠️|BLOCKED|失败.*因为|原因.*是', re.IGNORECASE)
    pitfall_lines = [l.strip() for l in content.split('\n') if pitfall_pattern.search(l) and l.strip()]
    if pitfall_lines:
        sections.append("\n### 踩坑记录")
        seen_p = set()
        for l in pitfall_lines:
            if l not in seen_p:
                seen_p.add(l)
                sections.append(f"- {l}")
            if len(seen_p) >= 5:
                break

# 未解决的错误: 从 error-dna.json 读取
error_dna_path = os.path.join(project_root, '.omc', 'state', 'error-dna.json')
if os.path.isfile(error_dna_path):
    try:
        with open(error_dna_path) as ef:
            error_data = json.load(ef)
        unfixed = [e for e in error_data if e.get('status') != 'fixed']
        if unfixed:
            sections.append("\n## 未解决的错误")
            for e in unfixed[:3]:
                sig = e.get('signature', '(unknown)')
                count = e.get('count', 1)
                last_seen = e.get('last_seen', '')
                sections.append(f"- {sig} (出现{count}次, 最后: {last_seen})")
    except:
        pass

# 当前 Todo 队列: 从 todo-queue.md 读取
todo_path = os.path.join(project_root, '.omc', 'state', 'todo-queue.md')
if os.path.isfile(todo_path):
    try:
        with open(todo_path) as tf:
            todo_content = tf.read().strip()
        if todo_content:
            active = [l for l in todo_content.split('\n') if '[·]' in l]
            pending = [l for l in todo_content.split('\n') if re.match(r'\s*-\s*\[', l)]
            if active or pending:
                sections.append("\n## 当前 Todo")
                for l in active[:5]:
                    sections.append(f" {l.strip()}")
                for l in pending[:5]:
                    sections.append(f" {l.strip()}")
    except:
        pass

# 本次涉及文件: 从 session-edit-log.txt 读取
edit_log_path = os.path.join(project_root, '.omc', 'state', 'session-edit-log.txt')
if os.path.isfile(edit_log_path):
    try:
        with open(edit_log_path) as lf:
            raw_files = [l.strip() for l in lf if l.strip()]
        unique_files = sorted(set(raw_files))
        if unique_files:
            sections.append(f"\n## 本次涉及文件 ({len(unique_files)}个)")
            for f in unique_files[:10]:
                sections.append(f"- {f}")
    except:
        pass

# 修改的文件
try:
    import subprocess
    modified = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True, cwd=project_root).stdout.strip()
    staged = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True, cwd=project_root).stdout.strip()
    all_files = set(filter(None, (modified + '\n' + staged).split('\n')))
    if all_files:
        sections.append("\n## 修改的文件")
        for f in sorted(all_files)[:15]:
            sections.append(f"- {f}")
except:
    pass

# ─── non-rpe fallback：无 executor.md 时注入 git log 摘要 ───────────
# 让第一天/第一周的用户也能获得有意义的交接内容
if not executor_files:
    try:
        import subprocess
        log_result = subprocess.run(
            ['git', 'log', '--oneline', '--no-merges', '-10'],
            capture_output=True, text=True, cwd=project_root
        )
        if log_result.returncode == 0 and log_result.stdout.strip():
            sections.append("\n## 最近提交（rpe 工作流未启用时的替代摘要）")
            for line in log_result.stdout.strip().split('\n')[:10]:
                sections.append(f"- `{line.strip()}`")
            sections.append("\n> 💡 启用 rpe 工作流后（`mkdir rpe && mkdir rpe/{feature}`），交接内容将更丰富")
    except:
        pass

# 踩过的坑: claude-next.md 最近条目
claude_next = os.path.join(project_root, '.claude', 'claude-next.md')
if os.path.isfile(claude_next):
    try:
        with open(claude_next) as f:
            cn_content = f.read()
        lesson_titles = re.findall(r'^## \[.+?\] (.+)', cn_content, re.MULTILINE)
        if lesson_titles:
            sections.append("\n## 近期教训")
            for t in lesson_titles[-max_lessons:]:
                sections.append(f"- {t}")
    except:
        pass

# 写入
with open(handoff_path, 'w') as f:
    f.write('\n'.join(sections) + '\n')

print(f"Session handoff saved: {len(sections)} sections")
PYEOF
fi

# 注意：不在 Stop hook 中重置计数器
# Stop 事件每次 AI 回复结束都会触发，不是只在会话结束时
# 计数器重置移至 SessionStart hook（inject-project-knowledge.sh）
exit 0
