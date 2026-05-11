#!/usr/bin/env bash
# intent-tracker.sh — PostToolUse:Edit|Write — 检测同一会话中声明矛盾（E6 自我矛盾）
# Role: 检测同一会话中声明矛盾
#
# 原理：当 AI 对同一文件先声明"已修复"后又编辑该文件时，记录矛盾。
# 文件级签名 dedup，写入 .omc/state/contradiction-log.jsonl

source "$(dirname "$0")/harness_config.sh"
hc_enabled "intent_tracker" || { echo '{"continue":true}'; exit 0; }
INPUT=$(cat)

# 从 stdin JSON 提取关键字段
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('file_path', '') or '')
except:
    pass" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR"

CONTRADICTION_LOG="$STATE_DIR/contradiction-log.jsonl"

# 提取 tool_response 中可能含"完成/修复/验证"声明的文本
python3 - "$FILE_PATH" "$CONTRADICTION_LOG" "$INPUT" <<'PYEOF'
import sys, json, hashlib, os

file_path = sys.argv[1]
log_path = sys.argv[2]
input_raw = sys.argv[3]

try:
    data = json.loads(input_raw)
except:
    sys.exit(0)

tr = data.get('tool_response', {})
stdout = tr.get('stdout', '') or ''
stderr = tr.get('stderr', '') or ''

# 声明关键词
assertion_keywords = ['已完成', '已修复', '已验证', '已测试', 'fixed', 'completed', 'verified', 'done']
combined = (stdout + ' ' + stderr).lower()

# 检查是否含声明关键词
has_assertion = any(kw in combined for kw in assertion_keywords)
if not has_assertion:
    sys.exit(0)

# 生成文件级签名
sig = hashlib.md5(file_path.encode()).hexdigest()[:16]

# 读取已有矛盾记录
previous = []
if os.path.isfile(log_path):
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        previous.append(rec)
                    except:
                        pass
    except:
        pass

# 检查是否同一文件之前已有声明
is_contradiction = False
for rec in previous:
    if rec.get('sig') == sig:
        is_contradiction = True
        break

record = {
    'ts': int(__import__('time').time()),
    'sig': sig,
    'file': file_path,
    'assertion_found': True,
    'contradiction': is_contradiction,
}

if is_contradiction:
    record['type'] = 'contradiction'
    # Emit warning to stderr for visibility
    print(f"[intent-tracker 矛盾检测] 文件 {file_path} 在同一会话中已有声明记录，再次编辑存在前后矛盾风险", file=sys.stderr)

# Append
with open(log_path, 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')

# Output additionalContext on contradiction so AI sees its own past declarations
if is_contradiction:
    ctx = f"[intent-tracker] 矛盾检测: 文件 {file_path} 在同一会话中已有声明记录，再次编辑存在前后矛盾风险"
    print(json.dumps({"continue": True, "hookSpecificOutput": {"additionalContext": ctx}}))
PYEOF

exit 0
