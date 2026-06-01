#!/usr/bin/env bash
# stop-drain.sh — Stop — Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）
# Role: Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）

source "$(dirname "$0")/harness_config.sh"
set -f
hc_enabled "stop_drain" || exit 0
flywheel_event "stop_drain" "active" "P2" || true

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

# B1: Ghost mode detection + flywheel P0 events (Stop hook兜底：检测幽灵模式异常退出)
_ghost_json="$STATE_DIR/tokens/lx-ghost.json"
_ghost_auto="$STATE_DIR/tokens/autonomous.active"
_exit_report="$STATE_DIR/ghost-exit-report.md"
_pending="$STATE_DIR/ghost-exit-pending"
_ghost_mode=false

# Meta-Oracle M1 fix: autonomous.active 在 goal/ghost 模式均被创建。
# ghost 特定检查 (exit-report/pending) 只在 lx-ghost.json 存在时触发，避免 goal mode 假阳性 P0。
if [ -f "$_ghost_json" ]; then
    _ghost_mode=true
    mkdir -p "$HOME/.claude" 2>/dev/null
    if [ ! -f "$_exit_report" ]; then
        echo "$(date +%Y-%m-%d),ghost_exit_report_missing,P0,$(basename "$PROJECT_ROOT" 2>/dev/null || echo unknown)" >> "$HOME/.claude/flywheel-buffer.jsonl"
    fi
    if [ -f "$_pending" ]; then
        echo "$(date +%Y-%m-%d),ghost_forced_close,P0,$(basename "$PROJECT_ROOT" 2>/dev/null || echo unknown)" >> "$HOME/.claude/flywheel-buffer.jsonl"
    fi
fi

export TRANSCRIPT SESSION_ID STATE_DIR _ghost_mode
${PYTHON_BIN:-python3} - <<'PYEOF'
import json, os, sys, hashlib, re

transcript = os.environ.get('TRANSCRIPT', '')
session_id = os.environ.get('SESSION_ID', 'unknown')
state_dir = os.environ.get('STATE_DIR', '')

# stop-drain 记录的是 transcript 恢复的错误（非逃逸），写入 error-signals.jsonl
jsonl_path = os.path.join(state_dir, 'error-signals.jsonl')

# Load existing signatures to dedupe
seen = set()
if os.path.exists(jsonl_path):
    try:
        with open(jsonl_path, encoding="utf-8") as f:
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
    if not isinstance(cmd, str):
        cmd = str(cmd) if cmd else ''
    cmd = re.sub(r'--password\s+\S+', '--password ***', cmd)
    cmd = re.sub(r'--token\s+\S+', '--token ***', cmd)
    cmd = re.sub(r'--secret\s+\S+', '--secret ***', cmd)
    cmd = re.sub(r'--key\s+\S+', '--key ***', cmd)
    # P0.1: Mask API key env vars (ANTHROPIC_AUTH_TOKEN, DEEPSEEK_API_KEY, OPENAI_API_KEY, etc.)
    cmd = re.sub(r'(ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY|DEEPSEEK_BRIDGE_API_KEY|OPENAI_API_KEY|CODECLI_API_KEY|GEMINI_API_KEY)=\S+', r'\1=***', cmd)
    # P0.1: Mask Authorization: Bearer tokens
    cmd = re.sub(r"(Authorization:\s*Bearer\s+)[^\s\"'<>]+", r'\1***', cmd)
    # P0.1: Mask long base64 tokens (32+ chars from secrets.token_urlsafe)
    cmd = re.sub(r'(?:sk-|ghp_|xoxb-|xapp-)[a-zA-Z0-9_\-]{20,}', '***REDACTED***', cmd)
    cmd = re.sub(r'(?:eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{10,})', '***JWT***', cmd)
    # DG-008-v3: Sanitize lone surrogate escape sequences before writing to jsonl
    cmd = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', cmd)
    # DG-008-v4: Strip actual lone surrogate codepoints (json.dumps escapes them as \uDxxx)
    cmd = ''.join(c for c in cmd if not 0xD800 <= ord(c) <= 0xDFFF)
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
    with open(transcript, encoding="utf-8") as tf:
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
                cmd_clean = sanitize(f'[tool_use_id:{tool_use_id}]')
                signature = hashlib.md5(cmd_clean.encode()).hexdigest()[:16]

                # P1-7: Fix ts=0 — transcript entries often lack top-level timestamp.
                # Fallback chain: entry.timestamp > transcript mtime > current time.
                ts = int(entry.get('timestamp', 0)) if isinstance(entry.get('timestamp'), (int, float)) else 0
                if ts == 0:
                    try:
                        ts = int(os.path.getmtime(os.environ.get('TRANSCRIPT', '')))
                    except (OSError, ValueError):
                        ts = int(__import__('time').time())

                key = (session_id, signature, ts)
                if key in seen:
                    continue
                seen.add(key)

                # P0.1: Sanitize result_content before storing (may contain API keys from printenv/cmd output)
                result_content_clean = sanitize(result_content)
                record = {
                    'ts': ts,
                    'signature': signature,
                    'cmd': cmd_clean,
                    'exit_code': -1,  # marker for drain-origin (transcript doesn't expose exit_code)
                    'error_type': classify(cmd_clean),
                    'message': result_content_clean[:200].replace('\n', ' ').strip(),
                    'output_snippet': result_content_clean,
                    'session_id': session_id,
                    'session_start': ts - 3600,  # estimate: drain runs at session end
                    'session_end': ts,
                    'origin': 'stop-drain',
                    'mode': 'ghost' if os.environ.get('_ghost_mode') == 'true' else 'normal',
                }
                with open(jsonl_path, 'a', encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                recovered += 1
except FileNotFoundError:
    pass
except Exception:
    pass

# Silent: don't noise stdout in Stop flow
PYEOF

# Layer 3: Write token-tracking-real.json from transcript or DB (multi-platform)
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
    # Claude Code: direct transcript path via Stop event
    ${PYTHON_BIN:-python3} "$PROJECT_ROOT/.claude/scripts/token_transcript_parser.py" \
        --parser claude_code --transcript "$TRANSCRIPT" --write 2>/dev/null || true
else
    # Other platforms (OpenCode, etc.): auto-detect data source
    ${PYTHON_BIN:-python3} "$PROJECT_ROOT/.claude/scripts/token_transcript_parser.py" \
        --write 2>/dev/null || true
fi

# Layer 5: Write compact recovery memory (todo-queue.md with recent prompts + task summary)
# Runs on every Stop, so after /compact the next SessionStart can restore context
if [ -f "$TRANSCRIPT" ]; then
    ${PYTHON_BIN:-python3} "$PROJECT_ROOT/.claude/scripts/extract-compact-memory.py" \
        --transcript "$TRANSCRIPT" \
        --handoff "$STATE_DIR/session-handoff.md" \
        --dump "$STATE_DIR/session-dump.json" \
        --output "$STATE_DIR/todo-queue.md" 2>/dev/null || true
fi

# Layer 4: State directory hygiene — 1-day shelf life for all files
# Keep: last 3 harness-smoke logs, last 5 snapshots, last 3 completion evidence
# Remove: any file older than 1 day
if [ -d "$STATE_DIR" ]; then
    # Clean .tmp files (leftover from crashed processes)
    find "$STATE_DIR" -name "*.tmp.*" -mtime +0 -delete 2>/dev/null || true
    # Clean harness-smoke logs older than 1 day
    find "$STATE_DIR" -name "harness-smoke-*.log" -mtime +0 -delete 2>/dev/null || true
    # Clean snapshot files older than 1 day
    find "$STATE_DIR" -name "snapshot-*.txt" -mtime +0 -delete 2>/dev/null || true
    # Keep only last N of each type
    for pattern in "harness-smoke-*.log" "snapshot-*.txt" ".completion-evidence-*"; do
        count=3
        [[ "$pattern" == "snapshot-*.txt" ]] && count=5
        ls -t "$STATE_DIR"/$pattern 2>/dev/null | tail -n +$((count+1)) | while read -r f; do
            rm -f "$f" 2>/dev/null || true
        done
    done
fi

exit 0
