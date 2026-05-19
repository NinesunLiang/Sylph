#!/usr/bin/env bash
# intent-tracker.sh — PostToolUse:Edit|Write — 跟踪文件级编辑统计 + revert 检测
# Role: 跟踪编辑次数、检测内容回退（revert）、标记高频编辑（churn）
#
# 原理：
#   PostToolUse 不暴露 AI 输出文本，无法直接检测语义矛盾（已知约束）。
#   替代方案（均为文件级统计，非语义分析）：
#   1. 跟踪每个文件在会话内的编辑次数，5+ 次编辑 = churn（标记"高频改动"）
#   2. 跟踪文件内容哈希序列，检测 revert 模式（内容回到前一个哈希的版本）
#   注意：churn ≠ 矛盾，revert ≠ 矛盾。本 hook 只做统计标记，不推断意图。

source "$(dirname "$0")/harness_config.sh"
hc_enabled "intent_tracker" || { echo '{"continue":true}'; exit 0; }
INPUT=$(cat)

# 提取 file_path 字段
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('file_path', '') or '')
except:
    pass" 2>/dev/null)

[ -z "$FILE_PATH" ] && { echo '{"continue": true}'; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

CONTRADICTION_LOG="$STATE_DIR/contradiction-log.jsonl"

# Python 内联处理逻辑：会话级编辑计数 + 内容哈希追踪 + revert 检测
python3 - "$FILE_PATH" "$CONTRADICTION_LOG" <<'PYEOF'
import sys, json, hashlib, os, time, fcntl

file_path = sys.argv[1]
log_path = sys.argv[2]
now = int(time.time())

# Generate content hash tracking key
content_hash_key = hashlib.md5(file_path.encode()).hexdigest()

# Read existing contradiction records + content history
previous = []
content_history = {}  # content_hash_key -> list of (ts, content_hash)
if os.path.isfile(log_path):
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        previous.append(rec)
                        # Rebuild content history
                        if rec.get('type') == 'edit' and rec.get('content_hash') and rec.get('content_hash_key'):
                            k = rec['content_hash_key']
                            if k not in content_history:
                                content_history[k] = []
                            content_history[k].append((rec.get('ts', 0), rec['content_hash']))
                    except:
                        pass
    except:
        pass

# Compute current content hash (read file after edit)
content_hash = ''
try:
    with open(file_path) as f:
        c = f.read()
    content_hash = hashlib.md5(c.encode()).hexdigest()[:16]
except:
    pass

# Build sig for this file path (used as fingerprint)
sig = content_hash_key[:16]

# Check for revert pattern: current hash matches a previous hash
revert_of_hash = None
if content_hash and content_hash_key in content_history:
    for prev_ts, prev_hash in content_history[content_hash_key]:
        if prev_hash == content_hash and prev_ts < now:
            revert_of_hash = prev_ts
            break

# Check for content churn: add-then-remove same keyword detection
# Look at recent edits to this same file for opposite-direction patterns
churn_keyword = None
if revert_of_hash is None and content_hash:
    for rec in reversed(previous):
        if rec.get('content_hash_key') == content_hash_key and rec.get('type') == 'edit':
            kw = rec.get('diagnostic_keyword', '')
            if kw and len(kw) > 4:  # Only meaningful keywords
                # Check if same keyword appeared and was then removed
                churn_keyword = kw
                break

# Compute edit count for this file
edit_count = sum(1 for r in previous if r.get('sig') == sig) + 1

# Determine contradiction level
# Level 0: first edit (normal)
# Level 1: second edit or revert detected (warning)
# Level 2: 3+ edits or churn + revert (strong contradiction)

message = ''
contradiction_level = 0
contradiction_type = 'first_edit'

if edit_count >= 5:
    # Dedup: skip if same file already has a churn entry within the last hour
    recent_churn = False
    for r in reversed(previous):
        if r.get('sig') == sig and r.get('type') == 'churn' and r.get('level') == 2:
            if now - r.get('ts', 0) < 3600:
                recent_churn = True
            break
    if recent_churn:
        contradiction_level = 0
        contradiction_type = 'dedup_churn'
    else:
        contradiction_level = 2
        contradiction_type = 'churn'
        message = (f"[intent-tracker] 编辑抖动: 文件 {file_path} "
                   f"本会话已被编辑 {edit_count} 次，高频改动。")
elif revert_of_hash is not None:
    contradiction_level = 2
    contradiction_type = 'revert'
    message = (f"[intent-tracker] revert 检测: 文件 {file_path} "
               f"内容回退到之前的状态（哈希 {content_hash}）。"
               f"本会话第 {edit_count} 次编辑" +
               (f"，注意内容方向变化。" if churn_keyword else "。"))
elif churn_keyword:
    contradiction_level = 1
    contradiction_type = 'churn_keyword'
    message = (f"[intent-tracker] 文件 {file_path} 第 {edit_count} 次编辑，"
               f"检测到关键词 '{churn_keyword}' 前后变动。")
elif edit_count >= 2:
    contradiction_level = 1
    contradiction_type = 'revisit'
    message = (f"[intent-tracker] 文件 {file_path} 本会话第 {edit_count} 次编辑。")

if message and contradiction_level >= 1:
    print(message, file=sys.stderr)

record = {
    'ts': now,
    'sig': sig,
    'content_hash_key': content_hash_key,
    'content_hash': content_hash or '',
    'revert_of': revert_of_hash,
    'file': file_path,
    'edit_count': edit_count,
    'contradiction': contradiction_level >= 2 and contradiction_type in ('revert',),
    'level': contradiction_level,
    'type': contradiction_type,
}

# Append to log (atomic flock to prevent concurrent write interleaving)
with open(log_path, 'a') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
    f.flush()
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# Output additionalContext for level 2+ (real contradiction)
if contradiction_level >= 2:
    # Build detailed context with actionable guidance
    history_summary = ""
    file_edits = [r for r in reversed(previous) if r.get('sig') == sig]
    if len(file_edits) > 1:
        prev_types = [r.get('type', '?') for r in file_edits[:3]]
        history_summary = f"。编辑历史: {', '.join(prev_types)}"
    resolution = ("建议: (1) 若内容回退, 确认目标版本正确后重新编辑; "
                  "(2) 若频繁 churn, 先固化设计再改; "
                  "(3) 检查前几次编辑是否被意外撤销。")
    ctx = (f"[intent-tracker] {'内容回退' if revert_of_hash else '编辑抖动'}"
           f": 文件 {file_path} "
           f"本会话第 {edit_count} 次编辑{'，内容回退到历史版本' if revert_of_hash else '，高频改动'}"
           f"{history_summary}。{resolution}")
    # DG-88-v2: strip surrogates before json.dumps
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({"continue": True, "hookSpecificOutput": {"additionalContext": ctx}}))
PYEOF

flywheel_event "intent_tracker" "recorded" "P2" || true

	# M2: contradiction-log rotation (>512KB → archive, keep 3)
_clog_size=$(wc -c < "$CONTRADICTION_LOG" 2>/dev/null | tr -d ' ')
if [ "$_clog_size" -gt 524288 ] 2>/dev/null; then
    _clog_ts=$(date +%s)
    mv "$CONTRADICTION_LOG" "${CONTRADICTION_LOG}.$_clog_ts"
    touch "$CONTRADICTION_LOG"
    ls -t "${CONTRADICTION_LOG}."* 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
fi

echo '{"continue": true}'
exit 0
