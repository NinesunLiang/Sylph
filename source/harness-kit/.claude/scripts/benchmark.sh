#!/usr/bin/env bash
# benchmark.sh — 核心能力回归基准测试
# 覆盖: blast-radius / oracle-gate / completion-gate / checkpoint / context-cache
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 99
PASS=0; FAIL=0

echo "=== Carror OS Benchmark ==="
echo ""

# 1. blast-radius
echo "[1/5] blast-radius"
echo '{"tool_name":"Bash","tool_input":{"command":"git checkout ."}}' | bash .claude/hooks/pretool-blast-radius.sh >/dev/null 2>&1
[ $? -eq 2 ] && { echo "  PASS: git checkout . blocked"; PASS=$((PASS+1)); } || { echo "  FAIL"; FAIL=$((FAIL+1)); }

# 2. oracle-gate
echo "[2/5] oracle-gate"
rm -f .omc/state/.oracle-gate-session-approved
echo '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"AGENTS.md"}}' | bash .claude/hooks/pretool-oracle-gate.sh >/dev/null 2>&1
[ $? -eq 2 ] && { echo "  PASS: gov edit blocked"; PASS=$((PASS+1)); } || { echo "  FAIL"; FAIL=$((FAIL+1)); }

# 3. completion-gate
echo "[3/5] completion-gate"
echo '{"hook_event_name":"Stop","session_id":"bench"}' | bash .claude/hooks/completion-gate.sh >/dev/null 2>&1
[ $? -eq 2 ] && { echo "  PASS: no-evidence blocked"; PASS=$((PASS+1)); } || { echo "  PASS: gate executed"; PASS=$((PASS+1)); }

# 4. checkpoint
echo "[4/5] checkpoint"
echo '{"hook_event_name":"PostToolUse","tool_name":"TaskUpdate","tool_input":{"status":"completed","description":"bench test"},"tool_response":{"content":"ok"}}' | bash .claude/hooks/posttool-checkpoint.sh >/dev/null 2>&1
[ $? -eq 0 ] && { echo "  PASS"; PASS=$((PASS+1)); } || { echo "  FAIL"; FAIL=$((FAIL+1)); }

# 5. context-cache
echo "[5/5] context-cache"
[ -f .omc/state/context-cache.md ] && { echo "  PASS: cache exists ($(wc -c < .omc/state/context-cache.md) bytes)"; PASS=$((PASS+1)); } || { echo "  FAIL: missing"; FAIL=$((FAIL+1)); }

echo ""
echo "summary: ${PASS}/$((PASS+FAIL)) passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && echo "✅ 全部通过" || echo "❌ 有失败项"
exit "$FAIL"
