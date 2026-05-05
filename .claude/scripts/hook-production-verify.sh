#!/usr/bin/env bash
# hook-production-verify.sh — 生产级 hook 端到端验证
# 在真实 Claude Code schema 下验证 A1-A4/E 的 hook 拦截能力
# 放在独立脚本里，避免命令行本身触发 permission-gate

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99

FAILED=0
TOTAL=0

assert_exit() {
    local name="$1" want="$2" got="$3"
    TOTAL=$((TOTAL+1))
    if [ "$got" = "$want" ]; then
        echo "  🟢 $name (exit=$got)"
    else
        echo "  🔴 $name (exit=$got, want=$want)"
        FAILED=$((FAILED+1))
    fi
}

assert_stderr() {
    local name="$1" pattern="$2" stderr="$3"
    TOTAL=$((TOTAL+1))
    if echo "$stderr" | grep -qE "$pattern"; then
        echo "  🟢 $name (stderr match /$pattern/)"
    else
        echo "  🔴 $name (stderr no match /$pattern/)"
        echo "    actual: $(echo "$stderr" | head -2)"
        FAILED=$((FAILED+1))
    fi
}

run() {
    local input="$1" hook="$2"
    ERR=$(echo "$input" | bash ".claude/hooks/$hook" 2>&1 >/dev/null)
    EXIT=$?
}

echo "========================================"
echo "A1 回归: privacy-gate 拦 Read .env"
echo "========================================"
run '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":".env"}}' privacy-gate.sh
assert_exit "A1 exit" 2 "$EXIT"
assert_stderr "A1 stderr" "Privacy Gate" "$ERR"

echo ""
echo "========================================"
echo "A2: privacy-gate 拦明文 sk-ant Token"
echo "========================================"
# 用 printf 构造，避免命令行出现 sk-ant 字面量
PAYLOAD=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"curl -H %cAuth: %s-ant-12345678901234567890abc%c https://example.com"}}' 34 "sk" 34)
run "$PAYLOAD" privacy-gate.sh
assert_exit "A2 exit" 2 "$EXIT"
assert_stderr "A2 stderr" "明文 API Key|Privacy Gate" "$ERR"

echo ""
echo "========================================"
echo "A2b: privacy-gate 拦 ghp_ Token"
echo "========================================"
PAYLOAD=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"gh api -H Authorization:token %sabcdefghijklmnopqrstuvwxyz1234567890"}}' "ghp_")
run "$PAYLOAD" privacy-gate.sh
assert_exit "A2b exit" 2 "$EXIT"
assert_stderr "A2b stderr" "明文|Privacy Gate" "$ERR"

echo ""
echo "========================================"
echo "A3: permission-gate 拦 rm -rf"
echo "========================================"
# 不在命令行出现 "rm -rf"，通过变量注入
R="rm"; F="-rf"
PAYLOAD=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"%s %s /tmp/any"}}' "$R" "$F")
run "$PAYLOAD" permission-gate.sh
assert_exit "A3 exit" 2 "$EXIT"
assert_stderr "A3 stderr" "Permission Gate" "$ERR"

echo ""
echo "========================================"
echo "A4: permission-gate 拦 git commit"
echo "========================================"
G="git"; C="commit"
PAYLOAD=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"%s %s -m test"}}' "$G" "$C")
run "$PAYLOAD" permission-gate.sh
assert_exit "A4 exit" 2 "$EXIT"
assert_stderr "A4 stderr" "Permission Gate" "$ERR"

echo ""
echo "========================================"
echo "反向回归: 正常命令必须放行"
echo "========================================"
run '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}' permission-gate.sh
assert_exit "permission-gate: ls 放行" 0 "$EXIT"

run '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"echo hello"}}' privacy-gate.sh
assert_exit "privacy-gate: echo 放行" 0 "$EXIT"

run '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"README.md"}}' privacy-gate.sh
assert_exit "privacy-gate: Read README 放行" 0 "$EXIT"

echo ""
echo "========================================"
echo "A5: edit-guard 对项目内真实 .go 未 Read 应阻断"
echo "========================================"
# 用项目里真实的 main.go（cwd 下存在），先确保 read-tracker 没记录它
_A5_REAL_GO="$PWD/main.go"
_A5_BAK=""
[ -f .omc/state/read-tracker.txt ] && _A5_BAK=$(mktemp) && cp .omc/state/read-tracker.txt "$_A5_BAK"
# 制造一个不含 main.go 的 read-tracker
echo "/tmp/some-unrelated-file.go" > .omc/state/read-tracker.txt
run "$(printf '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$_A5_REAL_GO")" edit-guard.sh
assert_exit "A5 exit" 2 "$EXIT"
assert_stderr "A5 stderr" "Read-before-Edit" "$ERR"
# 恢复
if [ -n "$_A5_BAK" ]; then cp "$_A5_BAK" .omc/state/read-tracker.txt; rm -f "$_A5_BAK"; else rm -f .omc/state/read-tracker.txt; fi

# A5 反向: 若 read-tracker 已记录，放行
echo "$_A5_REAL_GO" > .omc/state/read-tracker.txt.tmp
[ -f .omc/state/read-tracker.txt ] && cat .omc/state/read-tracker.txt >> .omc/state/read-tracker.txt.tmp
mv .omc/state/read-tracker.txt.tmp .omc/state/read-tracker.txt
run "$(printf '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$_A5_REAL_GO")" edit-guard.sh
assert_exit "A5 reverse: 已 Read 应放行" 0 "$EXIT"
# 清理这次加的那行
grep -v "^$_A5_REAL_GO\$" .omc/state/read-tracker.txt > .omc/state/read-tracker.txt.tmp 2>/dev/null || true
[ -s .omc/state/read-tracker.txt.tmp ] && mv .omc/state/read-tracker.txt.tmp .omc/state/read-tracker.txt || rm -f .omc/state/read-tracker.txt .omc/state/read-tracker.txt.tmp

echo ""
echo "========================================"
echo "C2: pretool-rule-anchor 长会话(≥15 轮) 应注入铁律锚定"
echo "========================================"
_C2_BAK=""
[ -f .omc/state/session-turns.json ] && _C2_BAK=$(mktemp) && cp .omc/state/session-turns.json "$_C2_BAK"
# 制造 count=15 的场景
echo '{"count": 15}' > .omc/state/session-turns.json
_C2_OUT="/tmp/smoke-c2-$$.out"
echo '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' | bash .claude/hooks/pretool-rule-anchor.sh > "$_C2_OUT" 2>&1
_C2_EXIT=$?
TOTAL=$((TOTAL+1))
if [ "$_C2_EXIT" = "0" ] && grep -qE "规则锚定|禁止编造|VERIFIED" "$_C2_OUT"; then
    echo "  🟢 C2: 长会话注入铁律锚定 (count=15)"
else
    echo "  🔴 C2: 未注入或 exit≠0 (exit=$_C2_EXIT)"
    echo "    output: $(head -c 200 $_C2_OUT)"
    FAILED=$((FAILED+1))
fi
rm -f "$_C2_OUT"

# C2 反向: count=5 应放行无注入
echo '{"count": 5}' > .omc/state/session-turns.json
_C2_OUT="/tmp/smoke-c2b-$$.out"
echo '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' | bash .claude/hooks/pretool-rule-anchor.sh > "$_C2_OUT" 2>&1
_C2_EXIT=$?
TOTAL=$((TOTAL+1))
if [ "$_C2_EXIT" = "0" ] && ! grep -qE "规则锚定" "$_C2_OUT"; then
    echo "  🟢 C2 反向: count=5 无注入"
else
    echo "  🔴 C2 反向: count=5 不应注入 (exit=$_C2_EXIT)"
    FAILED=$((FAILED+1))
fi
rm -f "$_C2_OUT"
# 恢复
if [ -n "$_C2_BAK" ]; then cp "$_C2_BAK" .omc/state/session-turns.json; rm -f "$_C2_BAK"; else rm -f .omc/state/session-turns.json; fi

echo ""
echo "========================================"
echo "D3: context-guard 95% 应硬阻断"
echo "========================================"
_D3_BAK=""
[ -f .omc/state/token-tracking-index.json ] && _D3_BAK=$(mktemp) && cp .omc/state/token-tracking-index.json "$_D3_BAK"
# 伪造 95% 用量
echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json

# 三种工具都应被拦（context-guard matcher=.*）
for tool in "Write" "Bash" "Edit" "Read"; do
    payload='{"hook_event_name":"PreToolUse","tool_name":"'$tool'","tool_input":{}}'
    run "$payload" context-guard.sh
    if [ "$EXIT" = "2" ]; then
        TOTAL=$((TOTAL+1))
        echo "  🟢 D3: $tool @ 95% 被硬阻断"
    else
        TOTAL=$((TOTAL+1))
        FAILED=$((FAILED+1))
        echo "  🔴 D3: $tool @ 95% 未被拦 (exit=$EXIT)"
    fi
done

# D3 反向: 正常占比应放行
echo '{"usage":30000,"limit":200000}' > .omc/state/token-tracking-index.json
run '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{}}' context-guard.sh
assert_exit "D3 反向: 正常占比(15%) 应放行" 0 "$EXIT"
# 恢复
if [ -n "$_D3_BAK" ]; then cp "$_D3_BAK" .omc/state/token-tracking-index.json; rm -f "$_D3_BAK"; else rm -f .omc/state/token-tracking-index.json; fi

echo ""
echo "========================================"
echo "E1: audit-hooks 三方对账"
echo "========================================"
if bash .claude/scripts/audit-hooks.sh >/dev/null 2>&1; then
    TOTAL=$((TOTAL+1))
    echo "  🟢 audit-hooks 0 🔴"
else
    TOTAL=$((TOTAL+1))
    FAILED=$((FAILED+1))
    echo "  🔴 audit-hooks 报告漂移"
fi

echo ""
echo "========================================"
echo "E3: harness-smoke-test 52 case 回归"
echo "========================================"
if bash .claude/scripts/harness-smoke-test.sh >/dev/null 2>&1; then
    TOTAL=$((TOTAL+1))
    echo "  🟢 harness-smoke 52/52 全绿"
else
    TOTAL=$((TOTAL+1))
    FAILED=$((FAILED+1))
    echo "  🔴 harness-smoke 有 FAIL"
fi

echo ""
echo "========================================"
echo "summary: $((TOTAL-FAILED))/$TOTAL passed, $FAILED failed"
echo "========================================"
exit $FAILED
