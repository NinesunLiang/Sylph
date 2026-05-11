#!/usr/bin/env bash
# intent-tracker.sh — PostToolUse:Edit|Write — 检测同一会话中声明矛盾 + 模式级矛盾（E6 自我矛盾）
# Role: 检测同一会话中文件级编辑矛盾 + 模式级矛盾（先加后删等）
#
# 原理：
#   PostToolUse 不暴露 AI 输出文本，无法直接检测语义矛盾。
#   替代方案：
#   1. 跟踪每个文件在会话内的编辑次数，3+ 次编辑 = churn 矛盾
#   2. 跟踪文件内容哈希序列，检测 revert 模式（内容回到前一个哈希的版本）
#   3. 跨文件模式检测：同一会话中 A 写 X → B 写 Y（如果 X 和 Y 是同一个文件的互逆操作）

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
import sys, json, hashlib, os, time

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

if edit_count >= 3:
    contradiction_level = 2
    contradiction_type = 'churn'
    message = (f"[intent-tracker] 矛盾检测: 文件 {file_path} "
               f"本会话已被编辑 {edit_count} 次，前后矛盾风险。")
elif revert_of_hash is not None:
    contradiction_level = 2
    contradiction_type = 'revert'
    message = (f"[intent-tracker] revert 检测: 文件 {file_path} "
               f"内容回退到之前的状态（哈希 {content_hash}）。"
               f"本会话第 {edit_count} 次编辑" +
               (f"，注意冲突方向。" if churn_keyword else "。"))
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
    'contradiction': contradiction_level >= 2,
    'level': contradiction_level,
    'type': contradiction_type,
}

# Append to log
with open(log_path, 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

# Output additionalContext for level 2+ (real contradiction)
if contradiction_level >= 2:
    ctx = (f"[intent-tracker] {'revert 矛盾' if revert_of_hash else '编辑矛盾'}"
           f": 文件 {file_path} "
           f"本会话第 {edit_count} 次编辑{'，内容回退到历史版本' if revert_of_hash else '，频繁改动风险'}"
           f"。建议检查前几次编辑是否完整。")
    print(json.dumps({"continue": True, "hookSpecificOutput": {"additionalContext": ctx}}))
PYEOF

echo '{"continue": true}'
exit 0
