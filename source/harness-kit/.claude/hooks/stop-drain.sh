#!/usr/bin/env bash
# stop-drain.sh — Stop hook 兜底重放
# 防御纵深第二层：扫 transcript.jsonl 抓 PostToolUse 派发之外的 Bash 失败，补写 error-dna.jsonl
# 触发时机：Claude Code 会话结束（Stop event）
# 幂等：基于 session_id + ts + signature 去重
# 与实时层（PostToolUseFailure → error-dna.sh）互不冲突，重复事件会被去重丢弃

source "$(dirname "$0")/harness_config.sh"
hc_enabled "stop_drain" || exit 0

INPUT=$(cat)

if command -v jq &>/dev/null; then
    TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
    SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
else
    TRANSCRIPT=$(echo "$INPUT" | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi

[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

export TRANSCRIPT SESSION_ID STATE_DIR
python3 - <<'PYEOF'
import json, os, sys, hashlib, re

transcript = os.environ.get('TRANSCRIPT', '')
session_id = os.environ.get('SESSION_ID', 'unknown')
state_dir = os.environ.get('STATE_DIR', '')

jsonl_path = os.path.join(state_dir, 'error-dna.jsonl')

# Load existing signatures to dedupe
seen = set()
if os.path.exists(jsonl_path):
    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    # Dedup key: session + signature + ts (same failure within same session)
                    seen.add((r.get('session_id', ''), r.get('signature', ''), r.get('ts', 0)))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

def sanitize(cmd):
    cmd = re.sub(r'--password\s+\S+', '--password ***', cmd)
    cmd = re.sub(r'--token\s+\S+', '--token ***', cmd)
    cmd = re.sub(r'--secret\s+\S+', '--secret ***', cmd)
    cmd = re.sub(r'--key\s+\S+', '--key ***', cmd)
    return cmd

def classify(cmd):
    c = cmd.lower()
    if any(x in c for x in ['go build', 'npm run build', 'cargo build', 'tsc']): return 'build'
    if any(x in c for x in ['go test', 'npm test', 'pytest', 'jest']): return 'test'
    if 'git' in c: return 'git'
    if any(x in c for x in ['npm install', 'go get', 'pip install']): return 'dependency'
    if any(x in c for x in ['lint', 'eslint', 'golangci-lint']): return 'lint'
    if 'docker' in c: return 'docker'
    if any(x in c for x in ['curl', 'wget', 'http']): return 'network'
    if any(x in c for x in ['find', 'grep', 'sed', 'awk']): return 'file_ops'
    return 'runtime'

recovered = 0
try:
    with open(transcript) as tf:
        for line in tf:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Transcript entries have varied shape; look for tool_use_result with is_error
            # or message.content items with type == 'tool_result' having exit indicators
            content = None
            if entry.get('type') == 'user' and isinstance(entry.get('message', {}), dict):
                content = entry['message'].get('content')

            if not isinstance(content, list):
                continue

            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get('type') != 'tool_result':
                    continue
                is_error = item.get('is_error', False)
                if not is_error:
                    continue

                # Find the matching tool_use in previous entries by tool_use_id - skipped for simplicity;
                # we only care about the error message here.
                result_content = item.get('content', '')
                if isinstance(result_content, list):
                    result_content = ' '.join(
                        c.get('text', '') for c in result_content if isinstance(c, dict)
                    )
                result_content = str(result_content)[:500]

                # Use tool_use_id as pseudo-command key if nothing else
                tool_use_id = item.get('tool_use_id', '')
                # We don't have the command here; look back-index the original tool_use
                # (skipped: simple approach — record by tool_use_id hash)
                cmd_clean = sanitize(f'[tool_use_id:{tool_use_id}]')
                signature = hashlib.md5(cmd_clean.encode()).hexdigest()[:16]
                ts = int(entry.get('timestamp', 0)) if isinstance(entry.get('timestamp'), (int, float)) else 0

                key = (session_id, signature, ts)
                if key in seen:
                    continue
                seen.add(key)

                record = {
                    'ts': ts,
                    'signature': signature,
                    'cmd': cmd_clean,
                    'exit_code': -1,  # unknown from transcript, marker for drain-origin
                    'error_type': classify(cmd_clean),
                    'message': result_content[:200].replace('\n', ' ').strip(),
                    'output_snippet': result_content,
                    'session_id': session_id,
                    'origin': 'stop-drain',
                }
                with open(jsonl_path, 'a') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                recovered += 1
except FileNotFoundError:
    pass
except Exception:
    pass

# Silent: don't noise stdout in Stop flow
PYEOF

# Layer 3: Write token-tracking-real.json from transcript (real token data)
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
    python3 "$PROJECT_ROOT/.claude/scripts/token-transcript-parser.py" \
        --transcript "$TRANSCRIPT" --write 2>/dev/null || true
fi

exit 0
