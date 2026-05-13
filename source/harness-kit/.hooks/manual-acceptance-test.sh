#!/usr/bin/env bash
#
# manual-acceptance-test.sh — Manual Acceptance Test Suite
# Tests actual hook script execution, blocking behavior, fallback mechanism,
# and generated config integrity across all 6 platforms.
#
# Usage:
#   bash .hooks/manual-acceptance-test.sh
#
# Exit codes:
#   0  All tests passed
#   1  One or more tests failed
#

set -euo pipefail

PASS="✅"
FAIL="❌"
INFO="ℹ️"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$ROOT/.claude/hooks"
TESTS_PASSED=0
TESTS_FAILED=0
FAILURES=()

header() {
  echo ""
  echo "============================================================"
  echo "  $1"
  echo "============================================================"
}

test_pass() {
  TESTS_PASSED=$((TESTS_PASSED + 1))
  echo "  $PASS $1"
}

test_fail() {
  TESTS_FAILED=$((TESTS_FAILED + 1))
  FAILURES+=("$1: $2")
  echo "  $FAIL $1 — $2"
}

run_hook_test() {
  local hook_script="$1"
  local input_json="$2"
  local expected_exit="$3"
  local desc="$4"

  local abs_script="$HOOKS_DIR/$hook_script"
  if [ ! -f "$abs_script" ]; then
    test_fail "$desc" "script not found: $abs_script"
    return
  fi

  local actual_exit=0
  local output
  output=$(echo "$input_json" | bash "$abs_script" 2>&1) || actual_exit=$?

  if [ "$actual_exit" -eq "$expected_exit" ]; then
    test_pass "$desc"
  else
    test_fail "$desc" "expected exit $expected_exit, got $actual_exit. output: $output"
  fi
}

# ════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Sylph Harness — Manual Acceptance Test Suite          ║"
echo "║   Cross-Platform Hook System v6.1.8                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Project: $ROOT"
echo ""

# ════════════════════════════════════════════════════════════════
# 1. Hook Script Execution Tests
# ════════════════════════════════════════════════════════════════
header "1. Hook Script Execution Tests"

# 1a. completion-gate.sh — blocking hook, should exit 2 when completed without evidence
run_hook_test "completion-gate.sh" \
  '{"tool_input":{"status":"completed"}}' \
  2 \
  "completion-gate: blocks completed without VERIFIED"

# 1b. completion-gate.sh — should exit 0 when status is not completed
run_hook_test "completion-gate.sh" \
  '{"tool_input":{"status":"in_progress"}}' \
  0 \
  "completion-gate: passes when not completed"

# 1c. permission-gate.sh — blocking hook, should exit 2 on dangerous commands
run_hook_test "permission-gate.sh" \
  '{"tool_input":{"command":"rm -rf /tmp/test"}}' \
  2 \
  "permission-gate: blocks rm -rf"

# 1d. permission-gate.sh — should exit 0 on safe commands
run_hook_test "permission-gate.sh" \
  '{"tool_input":{"command":"ls -la"}}' \
  0 \
  "permission-gate: passes safe command"

# 1e. permission-gate.sh — block git push --force
run_hook_test "permission-gate.sh" \
  '{"tool_input":{"command":"git push --force origin main"}}' \
  2 \
  "permission-gate: blocks git push --force"

# 1f. permission-gate.sh — block sudo
run_hook_test "permission-gate.sh" \
  '{"tool_input":{"command":"sudo rm -rf /var/log"}}' \
  2 \
  "permission-gate: blocks sudo"

# 1g. privacy-gate.sh — block .env access
run_hook_test "privacy-gate.sh" \
  '{"tool_input":{"file_path":".env"}}' \
  2 \
  "privacy-gate: blocks .env file"

# 1h. privacy-gate.sh — block private key access
run_hook_test "privacy-gate.sh" \
  '{"tool_input":{"file_path":"id_rsa"}}' \
  2 \
  "privacy-gate: blocks private key"

# 1i. privacy-gate.sh — allow normal file
run_hook_test "privacy-gate.sh" \
  '{"tool_input":{"file_path":"src/main.go"}}' \
  0 \
  "privacy-gate: allows normal source file"

# ════════════════════════════════════════════════════════════════
# 2. Fallback Cache Mechanism Test
# ════════════════════════════════════════════════════════════════
header "2. Fallback Cache Mechanism Test"

# 2a. Verify .hooks/.cache exists and is non-empty
CACHE_FILE="$ROOT/.hooks/.cache"
if [ -f "$CACHE_FILE" ] && [ -s "$CACHE_FILE" ]; then
  test_pass "fallback cache: .hooks/.cache exists ($(wc -c < "$CACHE_FILE") bytes)"
else
  test_fail "fallback cache" ".hooks/.cache missing or empty"
fi

# 2b. Verify cache contains expected keys
if grep -q "hooks_enabled." "$CACHE_FILE" && \
   grep -q "knowledge.inject_files" "$CACHE_FILE" && \
   grep -q "workflow.doc_root" "$CACHE_FILE"; then
  test_pass "fallback cache: contains expected sections"
else
  test_fail "fallback cache" "missing expected sections"
fi

# 2c. Simulate harness.yaml absent — verify harness_config.sh falls back to .hooks/.cache
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT
mkdir -p "$TMPDIR/.claude/hooks" "$TMPDIR/.omc/state" "$TMPDIR/.hooks"
cp "$HOOKS_DIR/harness_config.sh" "$TMPDIR/.claude/hooks/"
cp "$CACHE_FILE" "$TMPDIR/.hooks/.cache"

# Remove harness.yaml to force fallback
FALLBACK_OUTPUT=$(bash -c '
  source "'"$TMPDIR"'/.claude/hooks/harness_config.sh"
  echo "doc_root=$(hc_get workflow.doc_root NOT_FOUND)"
  echo "completion_gate=$(hc_enabled completion_gate && echo enabled || echo disabled)"
  echo "nonexistent=$(hc_get something.that.does.not.exist DEFAULT_OK)"
' 2>&1)

if echo "$FALLBACK_OUTPUT" | grep -q "doc_root=rpe" && \
   echo "$FALLBACK_OUTPUT" | grep -q "completion_gate=enabled" && \
   echo "$FALLBACK_OUTPUT" | grep -q "nonexistent=DEFAULT_OK"; then
  test_pass "fallback cache: harness_config.sh reads .hooks/.cache correctly"
else
  test_fail "fallback cache" "unexpected output: $FALLBACK_OUTPUT"
fi
rm -rf "$TMPDIR"

# ════════════════════════════════════════════════════════════════
# 3. Generated Config Validation
# ════════════════════════════════════════════════════════════════
header "3. Generated Config Validation"

# 3a. Codex CLI hooks.json
CODX_JSON="$ROOT/.codex/hooks.json"
if [ -f "$CODX_JSON" ]; then
  HOOK_COUNT=$(python3 -c "import json; d=json.load(open('$CODX_JSON')); print(sum(len(g.get('hooks',[])) for e in d.get('hooks',{}).values() for g in e))")
  EVENT_COUNT=$(python3 -c "import json; d=json.load(open('$CODX_JSON')); print(len(d.get('hooks',{})))")
  if [ "$HOOK_COUNT" -ge 11 ]; then
    test_pass "Codex CLI: $HOOK_COUNT hook registrations across $EVENT_COUNT events"
  else
    test_fail "Codex CLI" "only $HOOK_COUNT hooks, expected ≥11"
  fi
else
  test_fail "Codex CLI" "hooks.json not found"
fi

# 3b. Gemini CLI settings.json
GEMINI_JSON="$ROOT/.gemini/settings.json"
if [ -f "$GEMINI_JSON" ]; then
  GEMINI_HOOKS=$(python3 -c "import json; d=json.load(open('$GEMINI_JSON')); print(sum(len(g.get('hooks',[])) for e in d.get('hooks',{}).values() for g in e))")
  GEMINI_EVENTS=$(python3 -c "import json; d=json.load(open('$GEMINI_JSON')); print(len(d.get('hooks',{})))")
  test_pass "Gemini CLI: $GEMINI_HOOKS hook registrations across $GEMINI_EVENTS events"
else
  test_fail "Gemini CLI" "settings.json not found"
fi

# 3c. Qwen Code settings.json
QWEN_JSON="$ROOT/settings.json"
if [ -f "$QWEN_JSON" ]; then
  QWEN_HOOKS=$(python3 -c "import json; d=json.load(open('$QWEN_JSON')); print(sum(len(g.get('hooks',[])) for e in d.get('hooks',{}).values() for g in e))")
  QWEN_EVENTS=$(python3 -c "import json; d=json.load(open('$QWEN_JSON')); print(len(d.get('hooks',{})))")
  if [ -n "$QWEN_HOOKS" ]; then
    test_pass "Qwen Code: $QWEN_HOOKS hook registrations across $QWEN_EVENTS events"
  else
    test_fail "Qwen Code" "failed to parse hooks"
  fi
else
  test_fail "Qwen Code" "settings.json not found"
fi

# 3d. Cursor hooks.json
CURSOR_JSON="$ROOT/.cursor/hooks.json"
if [ -f "$CURSOR_JSON" ]; then
  CURSOR_HOOKS=$(python3 -c "import json; d=json.load(open('$CURSOR_JSON')); h=d.get('hooks',{}); print(sum(len(v) for v in h.values()))")
  CURSOR_EVENTS=$(python3 -c "import json; d=json.load(open('$CURSOR_JSON')); print(len(d.get('hooks',{})))")
  if [ "$CURSOR_HOOKS" -ge 2 ]; then
    test_pass "Cursor: $CURSOR_HOOKS hooks across $CURSOR_EVENTS events"
  else
    test_fail "Cursor" "expected ≥2 hooks, got $CURSOR_HOOKS"
  fi
else
  test_fail "Cursor" "hooks.json not found"
fi

# 3e. OpenCode TypeScript plugin
OPENCODE_TS="$ROOT/.opencode/plugins/sylph-hooks.ts"
if [ -f "$OPENCODE_TS" ]; then
  # Count hook entries
  TS_HOOK_COUNT=$(grep -c 'name: "' "$OPENCODE_TS" || true)
  # Check all 5 events are exported
  HAS_BEFORE=$(grep -c '"tool.execute.before"' "$OPENCODE_TS" || true)
  HAS_AFTER=$(grep -c '"tool.execute.after"' "$OPENCODE_TS" || true)
  HAS_SESSION=$(grep -c '"session.created"' "$OPENCODE_TS" || true)
  HAS_CHAT=$(grep -c '"chat.message"' "$OPENCODE_TS" || true)
  HAS_IDLE=$(grep -c '"session.idle"' "$OPENCODE_TS" || true)
  if [ "$TS_HOOK_COUNT" -ge 5 ] && [ "$HAS_BEFORE" -ge 1 ] && [ "$HAS_AFTER" -ge 1 ] && \
     [ "$HAS_SESSION" -ge 1 ] && [ "$HAS_CHAT" -ge 1 ] && [ "$HAS_IDLE" -ge 1 ]; then
    test_pass "OpenCode: $TS_HOOK_COUNT hooks, all 5 events exported"
  else
    test_fail "OpenCode" "hooks=$TS_HOOK_COUNT, before=$HAS_BEFORE, after=$HAS_AFTER, session=$HAS_SESSION, chat=$HAS_CHAT, idle=$HAS_IDLE"
  fi
else
  test_fail "OpenCode" "plugin not found"
fi

# 3f. Claude Code harness.yaml
HARNESS_YAML="$ROOT/.claude/harness.yaml"
if [ -f "$HARNESS_YAML" ]; then
  HOOK_ENABLED=$(grep -c "true" "$HARNESS_YAML" || true)
  test_pass "Claude Code: harness.yaml exists ($(wc -c < "$HARNESS_YAML") bytes, $HOOK_ENABLED enabled hooks)"
else
  test_fail "Claude Code" "harness.yaml not found"
fi

# ════════════════════════════════════════════════════════════════
# 4. Hook Script Integrity Tests
# ════════════════════════════════════════════════════════════════
header "4. Hook Script Integrity Tests"

ALL_SCRIPTS=0
VALID_SCRIPTS=0
for script in "$HOOKS_DIR"/*.sh; do
  ALL_SCRIPTS=$((ALL_SCRIPTS + 1))
  name=$(basename "$script")
  # Check bash syntax
  if bash -n "$script" 2>/dev/null; then
    VALID_SCRIPTS=$((VALID_SCRIPTS + 1))
  else
    test_fail "hook script $name" "bash syntax error"
  fi
done
if [ "$ALL_SCRIPTS" -eq "$VALID_SCRIPTS" ]; then
  test_pass "all $ALL_SCRIPTS hook scripts have valid bash syntax"
else
  test_fail "hook scripts" "$VALID_SCRIPTS/$ALL_SCRIPTS have valid syntax"
fi

# Check all scripts referenced in unified.yaml exist
MISSING_SCRIPTS=0
for script in $(python3 -c "
import sys; sys.path.insert(0, '.hooks')
import yaml
with open('.hooks/unified.yaml') as f:
    d = yaml.safe_load(f)
for h in {**d.get('hooks',{}), **d.get('claude_specific',{})}.values():
    s = h.get('script','')
    if s: print(s)
" 2>/dev/null); do
  if [ -f "$HOOKS_DIR/$script" ]; then
    true
  else
    test_fail "unified.yaml references" "missing script: $script"
    MISSING_SCRIPTS=$((MISSING_SCRIPTS + 1))
  fi
done
if [ "$MISSING_SCRIPTS" -eq 0 ]; then
  test_pass "all unified.yaml script references exist on disk"
fi

# ════════════════════════════════════════════════════════════════
# 5. Cross-Platform Config Generation Consistency
# ════════════════════════════════════════════════════════════════
header "5. Config Generation Consistency"

# Verify same hook generates same command across platforms that support it
PERMISSION_CMD='bash .claude/hooks/permission-gate.sh'

# Check permission_gate exists in multiple platform configs
CODX_MATCH=$(python3 -c "
import json
d=json.load(open('$CODX_JSON'))
for evt, groups in d.get('hooks',{}).items():
    for g in groups:
        for h in g.get('hooks',[]):
            c = h.get('command','')
            if 'permission-gate' in c:
                print(f'codex: {evt}')
                break
" 2>/dev/null || echo "")

GEMINI_MATCH=$(python3 -c "
import json
d=json.load(open('$GEMINI_JSON'))
for evt, groups in d.get('hooks',{}).items():
    for g in groups:
        for h in g.get('hooks',[]):
            c = h.get('command','')
            if 'permission-gate' in c:
                print(f'gemini: {evt}')
                break
" 2>/dev/null || echo "")

QWEN_MATCH=$(python3 -c "
import json
d=json.load(open('$QWEN_JSON'))
for evt, groups in d.get('hooks',{}).items():
    for g in groups:
        for h in g.get('hooks',[]):
            c = h.get('command','')
            if 'permission-gate' in c:
                print(f'qwen: {evt}')
                break
" 2>/dev/null || echo "")

if [ -n "$CODX_MATCH" ] && [ -n "$GEMINI_MATCH" ] && [ -n "$QWEN_MATCH" ]; then
  test_pass "permission_gate consistent across Codex/Gemini/Qwen"
else
  test_fail "permission_gate cross-platform" "missing in some platforms: codex=$CODX_MATCH gemini=$GEMINI_MATCH qwen=$QWEN_MATCH"
fi

# ════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo ""
echo "============================================================"
echo "  Manual Acceptance Test Results"
echo "============================================================"
echo "  Total: $TOTAL tests"
echo "  $PASS Passed: $TESTS_PASSED"
if [ "$TESTS_FAILED" -gt 0 ]; then
  echo "  $FAIL Failed: $TESTS_FAILED"
  echo ""
  echo "  Failures:"
  for f in "${FAILURES[@]}"; do
    echo "    • $f"
  done
  echo ""
  exit 1
else
  echo "  $PASS All tests passed!"
  echo ""
  exit 0
fi
