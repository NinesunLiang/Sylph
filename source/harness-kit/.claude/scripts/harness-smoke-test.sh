#!/usr/bin/env bash
# harness-smoke-test.sh — 真实 Claude Code JSON schema 下的 hook 冒烟测试
# R12-R17 验证套件。模拟 Claude Code 传给 hook 的真实 stdin JSON 格式。
#
# 使用：bash .claude/scripts/harness-smoke-test.sh
# 返回：0=全通过；非 0=失败项数
# 日志：.omc/state/harness-smoke-<timestamp>.log

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
TS=$(date -u +%Y%m%d-%H%M%S)
LOG=".omc/state/harness-smoke-$TS.log"
mkdir -p .omc/state
FAILED=0
TOTAL=0

log()  { echo "$@" | tee -a "$LOG"; }
pass() { log "  🟢 PASS: $1"; }
fail() { log "  🔴 FAIL: $1"; FAILED=$((FAILED+1)); }

run_case() {
    local name="$1" input="$2" hook="$3" expected_exit="$4" expected_stderr_regex="$5"
    TOTAL=$((TOTAL+1))
    log ""
    log "[$TOTAL] $name"
    local out_err="/tmp/smoke-$$-err"
    echo "$input" | bash ".claude/hooks/$hook" >/dev/null 2>"$out_err"
    local actual_exit=$?
    local actual_err
    actual_err=$(cat "$out_err")
    log "    hook=$hook  exit=$actual_exit  expected=$expected_exit"
    if [ "$actual_exit" != "$expected_exit" ]; then
        fail "exit mismatch: got $actual_exit, expected $expected_exit"
        log "    stderr: $actual_err"
    elif [ -n "$expected_stderr_regex" ] && ! echo "$actual_err" | grep -qE "$expected_stderr_regex"; then
        fail "stderr does not match /$expected_stderr_regex/"
        log "    stderr: $actual_err"
    else
        pass "$name"
    fi
    rm -f "$out_err"
}

log "========================================"
log "harness-smoke-test.sh @ $TS"
log "========================================"

# --- context-guard (R13 大小写 + R15 tool_name) ---
echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json
run_case "context-guard: Write @ 95% 应硬阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 2 "(Context Guard 硬阻断|9[0-9]\.)"

run_case "context-guard: Edit @ 95% 应硬阻断（大写）" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 2 "Context Guard"

run_case "context-guard: Bash @ 95% 应放行 (R29 诊断通道)" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' \
  "context-guard.sh" 0 ""

rm -f .omc/state/token-tracking-index.json
run_case "context-guard: 正常占比不应拦截 Write" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 0 ""

# R26: 正常占比下 Read 放行
run_case "context-guard: 正常占比 Read 应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 0 ""

# R29: 诊断通道（Read/Grep/Bash）在高上下文时放行，保留写工具 (Edit/Write) 的硬阻断
echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json
run_case "R29 context-guard: Read @ 95% 应放行 (诊断通道)" \
  '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 0 ""
rm -f .omc/state/token-tracking-index.json

# --- privacy-gate (R13 + R15 + R16) ---
run_case "privacy-gate: Read .env 应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":".env"}}' \
  "privacy-gate.sh" 2 "Privacy Gate"

run_case "privacy-gate: Read id_rsa 应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"/home/user/.ssh/id_rsa"}}' \
  "privacy-gate.sh" 2 "Privacy Gate"

run_case "privacy-gate: Bash 明文 sk-ant Token 应阻断（R16 跨平台正则修复）" \
  "$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"curl -H %cAuth: sk-ant-12345678901234567890abc%c"}}' 34 34)" \
  "privacy-gate.sh" 2 "明文 API Key"

run_case "privacy-gate: Bash 明文 ghp_ Token 应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"gh api -H Authorization:token ghp_abcdefghijklmnopqrstuvwxyz1234567890"}}' \
  "privacy-gate.sh" 2 "明文"

run_case "privacy-gate: 正常 Read 不拦" \
  '{"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{"file_path":"README.md"}}' \
  "privacy-gate.sh" 0 ""

# --- error-dna (R17 position args → stdin) ---
rm -f .omc/state/error-dna.jsonl
run_case "error-dna: PostToolUse Bash 失败应落盘（R17 无位置参数场景）" \
  '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"go build"},"tool_response":{"stderr":"undefined: X","exit_code":1}}' \
  "error-dna.sh" 0 ""
if [ -s .omc/state/error-dna.jsonl ] && grep -q '"signature"' .omc/state/error-dna.jsonl; then
    pass "error-dna.jsonl 已落盘且含 signature"
else
    fail "error-dna.jsonl 未落盘或无 signature"
fi
TOTAL=$((TOTAL+1))
rm -f .omc/state/error-dna.jsonl

run_case "error-dna: Edit 工具不应触发" \
  '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{}}' \
  "error-dna.sh" 0 ""

# --- R22: PostToolUseFailure schema (顶层 error 字段，无 tool_response) ---
rm -f .omc/state/error-dna.jsonl
run_case "error-dna: PostToolUseFailure schema 应落盘（R22 顶层 error）" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"false"},"error":"Command failed with exit code 1","is_interrupt":false}' \
  "error-dna.sh" 0 ""
if [ -s .omc/state/error-dna.jsonl ] && grep -q '"signature"' .omc/state/error-dna.jsonl; then
    pass "R22 error-dna.jsonl 已落盘（PostToolUseFailure schema）"
else
    fail "R22 error-dna.jsonl 未落盘（PostToolUseFailure schema）"
fi
TOTAL=$((TOTAL+1))
rm -f .omc/state/error-dna.jsonl

# --- R22: stop-drain 扫 transcript 兜底重放 ---
TRANSCRIPT_FAKE="/tmp/smoke-transcript-$$.jsonl"
cat > "$TRANSCRIPT_FAKE" <<'TJSONL'
{"type":"user","timestamp":1700000000,"message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"toolu_fake_R22_drain","is_error":true,"content":"command not found: nonexistent_xyz"}]}}
TJSONL
rm -f .omc/state/error-dna.jsonl
run_case "stop-drain: 扫 transcript 补录失败 tool_use（R22）" \
  "$(printf '{"hook_event_name":"Stop","session_id":"smoke-R22","transcript_path":"%s"}' "$TRANSCRIPT_FAKE")" \
  "stop-drain.sh" 0 ""
if [ -s .omc/state/error-dna.jsonl ] && grep -q '"origin": "stop-drain"' .omc/state/error-dna.jsonl; then
    pass "R22 stop-drain 补录成功（origin=stop-drain）"
else
    fail "R22 stop-drain 未补录"
fi
TOTAL=$((TOTAL+1))
rm -f .omc/state/error-dna.jsonl "$TRANSCRIPT_FAKE"

# --- write-lock (R17) ---
# 用唯一虚拟路径避免与业务锁冲突
LOCK_PATH="/tmp/smoke-lock-$$-$TS.txt"
run_case "pretool-write-lock: Write 应成功获锁（R17 无位置参数场景）" \
  "$(printf '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"%s"}}' "$LOCK_PATH")" \
  "pretool-write-lock.sh" 0 ""

run_case "posttool-write-lock: 释放该锁" \
  "$(printf '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"%s"}}' "$LOCK_PATH")" \
  "posttool-write-lock.sh" 0 ""

# --- permission-gate ---
run_case "permission-gate: rm -rf 无 marker 应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' \
  "permission-gate.sh" 2 "Permission Gate"

run_case "permission-gate: git commit 无 marker 应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git commit -m foo"}}' \
  "permission-gate.sh" 2 "Permission Gate"

run_case "permission-gate: 普通 ls 不拦" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls -la"}}' \
  "permission-gate.sh" 0 ""

# --- edit-guard ---
# R18 已修复：case *.go 对 basename 匹配，生产全路径亦生效
mkdir -p .omc/state
echo "/tmp/some-other-file.go" > .omc/state/read-tracker.txt
run_case "edit-guard: 未 Read 就 Edit 应阻断（R18 全路径场景）" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/Users/demo/project/src/main.go"}}' \
  "edit-guard.sh" 2 "Read-before-Edit"

# R18 回归：非源文件应放行
run_case "edit-guard: 非 .go 文件应放行（R18）" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/notes.txt"}}' \
  "edit-guard.sh" 0 ""
rm -f .omc/state/read-tracker.txt

# --- pretool-edit-scope ---
rm -f .omc/state/current-scope.txt
run_case "pretool-edit-scope: 无 scope 文件应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/any.go"}}' \
  "pretool-edit-scope.sh" 0 ""

echo "auth.go" > .omc/state/current-scope.txt
run_case "pretool-edit-scope: 越界文件应阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/payment.go"}}' \
  "pretool-edit-scope.sh" 2 "Scope Gate"
rm -f .omc/state/current-scope.txt

# --- R24-S1: 8 个未覆盖 hook 的业务语义验收 ---

# R24 auto-snapshot: Stop 事件应写 session-snapshot.json
rm -f .omc/state/session-snapshot.json .omc/state/session-snapshot.json.sha256
run_case "R24 auto-snapshot: Stop 应写 session-snapshot.json" \
  '{"hook_event_name":"Stop","session_id":"smoke-R24"}' \
  "auto-snapshot.sh" 0 ""
if [ -s .omc/state/session-snapshot.json ] && grep -q '"turns"' .omc/state/session-snapshot.json; then
    pass "R24 auto-snapshot 已落盘 session-snapshot.json 且含 turns"
else
    fail "R24 auto-snapshot 未写 session-snapshot.json"
fi
TOTAL=$((TOTAL+1))

# R24 completion-gate: status=completed 且无证据应硬阻断
# 注意：证据文件可能被当前会话刷新过，先判断证据 freshness 是否生效
_EVID_PATH=".omc/state/.completion-evidence-$(date +%Y%m%d)"
_EVID_BAK=""
if [ -f "$_EVID_PATH" ]; then
    _EVID_BAK="${_EVID_PATH}.smoke-bak"
    mv "$_EVID_PATH" "$_EVID_BAK"
fi
run_case "R24 completion-gate: 无证据应硬阻断 completed" \
  '{"hook_event_name":"PreToolUse","tool_name":"TaskUpdate","tool_input":{"taskId":"X","status":"completed"}}' \
  "completion-gate.sh" 2 "Completion Gate|证据"
[ -n "$_EVID_BAK" ] && mv "$_EVID_BAK" "$_EVID_PATH"

# R24 completion-gate: pending/in_progress 应放行
run_case "R24 completion-gate: 非 completed 应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"TaskUpdate","tool_input":{"taskId":"X","status":"in_progress"}}' \
  "completion-gate.sh" 0 ""

# R24 inject-project-knowledge: SessionStart 应输出 .claude/index.md 内容
_INJECT_OUT="/tmp/smoke-inject-$$.out"
echo '{"hook_event_name":"SessionStart","session_id":"smoke-R24","source":"startup"}' | bash .claude/hooks/inject-project-knowledge.sh > "$_INJECT_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 inject-project-knowledge: SessionStart 应注入 index.md"
if grep -q "\[.claude/" "$_INJECT_OUT"; then
    pass "R24 inject-project-knowledge 已注入核心知识"
else
    fail "R24 inject-project-knowledge 未注入任何内容"
fi
rm -f "$_INJECT_OUT"

# R24 posttool-bash-audit: rm -rf 后应在 additionalContext 中提示
_BAUDIT_OUT="/tmp/smoke-baudit-$$.out"
echo '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/fake"},"tool_response":{"exit_code":0,"stdout":"","stderr":""}}' | bash .claude/hooks/posttool-bash-audit.sh > "$_BAUDIT_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 posttool-bash-audit: rm -rf 应提示递归删除"
if grep -q "递归删除\|additionalContext" "$_BAUDIT_OUT"; then
    pass "R24 posttool-bash-audit 检测到 rm -rf"
else
    fail "R24 posttool-bash-audit 未识别 rm -rf"
fi
rm -f "$_BAUDIT_OUT"

# R24 posttool-write-cite: 写 claude-next.md 格式不合规应有警告
_PCITE_OUT="/tmp/smoke-pcite-$$.out"
echo '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/claude-next.md","new_content":"## 随手写一条没格式"}}' | bash .claude/hooks/posttool-write-cite.sh > "$_PCITE_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 posttool-write-cite: 缺字段应提示"
if grep -qE "缺少字段|格式问题" "$_PCITE_OUT"; then
    pass "R24 posttool-write-cite 检出格式问题"
else
    fail "R24 posttool-write-cite 未检出"
fi
rm -f "$_PCITE_OUT"

# R24 read-tracker: Read 后应记到 read-tracker.txt
rm -f .omc/state/read-tracker.txt
run_case "R24 read-tracker: PostToolUse Read 应落盘" \
  '{"hook_event_name":"PostToolUse","tool_name":"Read","tool_input":{"file_path":"/tmp/smoke-read-target-xyz"}}' \
  "read-tracker.sh" 0 ""
if [ -s .omc/state/read-tracker.txt ] && grep -q "smoke-read-target-xyz" .omc/state/read-tracker.txt; then
    pass "R24 read-tracker.txt 已落盘记录"
else
    fail "R24 read-tracker.txt 未记录"
fi
TOTAL=$((TOTAL+1))
rm -f .omc/state/read-tracker.txt

# R24 turn-counter: UserPromptSubmit 应递增 session-turns.json
rm -f .omc/state/session-turns.json
echo "test prompt" | bash .claude/hooks/turn-counter.sh >/dev/null 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 turn-counter: UserPromptSubmit 应递增 turns"
if [ -s .omc/state/session-turns.json ] && grep -q '"count": 1' .omc/state/session-turns.json; then
    pass "R24 session-turns.json count=1"
else
    fail "R24 session-turns.json 未递增"
fi
rm -f .omc/state/session-turns.json

# R24 pretool-user-correction: 纠正词应注入提示
_CORR_OUT="/tmp/smoke-corr-$$.out"
echo "你错了，这个不对" | bash .claude/hooks/pretool-user-correction.sh > "$_CORR_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 pretool-user-correction: 纠正词应触发提示"
if grep -q "纠正检测" "$_CORR_OUT"; then
    pass "R24 pretool-user-correction 检测到纠正信号"
else
    fail "R24 pretool-user-correction 未触发"
fi
rm -f "$_CORR_OUT"

# --- R23: 新注册的 8 个 hook — 业务级验收（R24-S2 升级版） ---

# R23/R24 lsp-suggest: 首次导出符号 Grep 应阻断（exit 2）+ 提示 LSP
rm -f .omc/state/lsp-suggested
run_case "R23/R24 lsp-suggest: 首次 Grep 导出符号应阻断并提示 LSP" \
  '{"hook_event_name":"PreToolUse","tool_name":"Grep","tool_input":{"pattern":"SomeExportedSymbol"}}' \
  "lsp-suggest.sh" 2 "LSP 建议|lsp_workspace_symbols"
if [ -f .omc/state/lsp-suggested ]; then
    pass "R24 lsp-suggest 写入会话标记（首次后不再重提）"
else
    fail "R24 lsp-suggest 未写标记"
fi
TOTAL=$((TOTAL+1))
run_case "R23/R24 lsp-suggest: 会话内第二次应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Grep","tool_input":{"pattern":"AnotherSymbol"}}' \
  "lsp-suggest.sh" 0 ""
rm -f .omc/state/lsp-suggested

run_case "R23/R24 lsp-suggest: 非符号模式（含正则元字符）应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Grep","tool_input":{"pattern":"func.*Foo"}}' \
  "lsp-suggest.sh" 0 ""

# R23/R24 pretool-rule-anchor: 轮次 <15 应放行
rm -f .omc/state/session-turns.json
run_case "R23/R24 pretool-rule-anchor: 轮次低应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' \
  "pretool-rule-anchor.sh" 0 ""

# R24 pretool-rule-anchor: 轮次 >=15 应注入 additionalContext（规则锚定）
echo '{"count": 15}' > .omc/state/session-turns.json
_ANCHOR_OUT="/tmp/smoke-anchor-$$.out"
echo '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' | bash .claude/hooks/pretool-rule-anchor.sh > "$_ANCHOR_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 pretool-rule-anchor: 长会话应注入 additionalContext"
if grep -qE "规则锚定|禁止编造|VERIFIED" "$_ANCHOR_OUT"; then
    pass "R24 pretool-rule-anchor 注入铁律提醒"
else
    fail "R24 pretool-rule-anchor 未注入"
fi
rm -f "$_ANCHOR_OUT" .omc/state/session-turns.json

# R23/R24/R25 subagent-guard: 危险 agent 无 max_turns → 默认放行 + additionalContext 提示
_SG_OUT="/tmp/smoke-sg-$$.out"
echo '{"hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"subagent_type":"executor","description":"x"}}' | bash .claude/hooks/subagent-guard.sh > "$_SG_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R25 subagent-guard: 无 max_turns 应走默认值放行 + 提示"
if grep -qE "默认上限 20|additionalContext" "$_SG_OUT"; then
    pass "R25 subagent-guard: 默认 max_turns=20 放行并提示"
else
    fail "R25 subagent-guard 未按预期放行: $(cat $_SG_OUT | head -2)"
fi
rm -f "$_SG_OUT"

# R23/R24/R25 subagent-guard: prompt 声明 max_turns=N 应放行（无提示）
run_case "R25 subagent-guard: prompt 含 max_turns=30 应放行（explicit）" \
  '{"hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"subagent_type":"executor","description":"max_turns=30 x"}}' \
  "subagent-guard.sh" 0 ""

# R23/R24 subagent-guard: tool_input.max_turns（未来 schema 支持）应放行
run_case "R23/R24 subagent-guard: 带 max_turns 应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"subagent_type":"executor","max_turns":20,"description":"x"}}' \
  "subagent-guard.sh" 0 ""

# R23/R24 subagent-guard: 安全 agent 应放行
run_case "R23/R24 subagent-guard: 安全 agent 应放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"subagent_type":"general-purpose","description":"x"}}' \
  "subagent-guard.sh" 0 ""

# R23/R24 posttool-edit-quality: Edit .go 文件应输出 hookSpecificOutput 自查清单
_EQ_OUT="/tmp/smoke-eq-$$.out"
echo '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/smoke-eq-test.go"},"tool_response":{}}' | bash .claude/hooks/posttool-edit-quality.sh > "$_EQ_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 posttool-edit-quality: Edit .go 应产出自查清单"
if grep -qE "命名|自查|additionalContext" "$_EQ_OUT"; then
    pass "R24 posttool-edit-quality 产出自查清单"
else
    fail "R24 posttool-edit-quality 未产出"
fi
rm -f "$_EQ_OUT"

# R23/R24 flywheel-report: SessionStart 不崩（业务上无副作用/日志为空时静默）
run_case "R23/R24 flywheel-report: SessionStart 不崩" \
  '{"hook_event_name":"SessionStart","session_id":"smoke-R24","source":"startup"}' \
  "flywheel-report.sh" 0 ""

# R23/R24 skill-flywheel: Stop 无 buffer 应静默退出（语法修复后）
rm -f "$HOME/.claude/flywheel-buffer.jsonl"
run_case "R23/R24 skill-flywheel: 无 buffer 应静默退出 (语法修复验证)" \
  '{"hook_event_name":"Stop","session_id":"smoke-R24"}' \
  "skill-flywheel.sh" 0 ""

# R24 skill-flywheel: 有 buffer 应刷入 flywheel.log
mkdir -p "$HOME/.claude"
echo '{"test":"smoke-R24-flush"}' > "$HOME/.claude/flywheel-buffer.jsonl"
_BEFORE=$(wc -l < "$HOME/.claude/flywheel.log" 2>/dev/null || echo 0)
bash .claude/hooks/skill-flywheel.sh < <(echo '{"hook_event_name":"Stop","session_id":"smoke-R24"}') >/dev/null 2>&1
_AFTER=$(wc -l < "$HOME/.claude/flywheel.log" 2>/dev/null || echo 0)
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 skill-flywheel: buffer 应被刷入 flywheel.log"
if [ "$_AFTER" -gt "$_BEFORE" ] && [ ! -f "$HOME/.claude/flywheel-buffer.jsonl" ]; then
    pass "R24 skill-flywheel flushed buffer → flywheel.log (before=$_BEFORE after=$_AFTER)"
else
    fail "R24 skill-flywheel 未 flush（before=$_BEFORE after=$_AFTER, buffer still exists=$([ -f "$HOME/.claude/flywheel-buffer.jsonl" ] && echo yes || echo no)）"
fi

# R23/R24 build-validator: PostToolUseFailure schema 不崩（顶层 error）
run_case "R23/R24 build-validator: PostToolUseFailure 顶层 error 兼容" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"go build"},"error":"undefined symbol"}' \
  "build-validator.sh" 0 ""

# R23 audit-hooks: 三方对账应 0 🔴
if bash .claude/scripts/audit-hooks.sh >/dev/null 2>&1; then
    pass "R23 audit-hooks: 三方对账 0 🔴"
else
    fail "R23 audit-hooks: 发现 🔴 级漂移"
fi
TOTAL=$((TOTAL+1))

# P1-1 R26 audit-hooks --scan-internal-filter: 脚本内白名单 vs matcher 漂移扫描应 0 🟡
# 注：3 个 🟡 为预期设计（plan-gate / posttool-read-cite / proactive-handoff
# 已注册但禁用，Base 版可用但默认不激活），允许 ≤3 个预期 🟡
SCAN_OUT=$(bash .claude/scripts/audit-hooks.sh --scan-internal-filter 2>&1)
YELLOW_COUNT=$(echo "$SCAN_OUT" | grep -E '🟡 次要:' | grep -oE '[0-9]+' | head -1)
RED_COUNT=$(echo "$SCAN_OUT" | grep -E '🔴 严重:' | grep -oE '[0-9]+' | head -1)
if [ "${RED_COUNT:-0}" -eq 0 ] && [ "${YELLOW_COUNT:-99}" -le 3 ]; then
    pass "P1-1 audit-hooks --scan-internal-filter: R26 回归 clean (🟡 $YELLOW_COUNT, 预期 ≤3)"
else
    fail "P1-1 audit-hooks --scan-internal-filter: 发现内部白名单漂移 (R=$RED_COUNT Y=$YELLOW_COUNT)"
fi
TOTAL=$((TOTAL+1))

# R25 posttool-subagent-audit: 危险 agent 正常返回应落盘 usage log，非 Task 应放行
rm -f .omc/state/subagent-usage.jsonl
run_case "R25 posttool-subagent-audit: 危险 agent 应记 usage" \
  '{"hook_event_name":"PostToolUse","tool_name":"Task","tool_input":{"subagent_type":"executor"},"tool_response":{"content":"small result"}}' \
  "posttool-subagent-audit.sh" 0 ""
if [ -s .omc/state/subagent-usage.jsonl ] && grep -q '"agent":"executor"' .omc/state/subagent-usage.jsonl; then
    pass "R25 subagent-usage.jsonl 已记录"
else
    fail "R25 subagent-usage.jsonl 未记录"
fi
TOTAL=$((TOTAL+1))
rm -f .omc/state/subagent-usage.jsonl

run_case "R25 posttool-subagent-audit: 非 Task 工具应放行" \
  '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' \
  "posttool-subagent-audit.sh" 0 ""

# --- R29: compact-detect (UserPromptSubmit /compact detection) ---
TOTAL=$((TOTAL+1))
run_case "R29 compact-detect: /compact 应写 compact-state" \
  '/compact' \
  "compact-detect.sh" 0 ""
if [ -f .omc/state/token-compact-state.json ] && grep -q '"pre_compact_usage"' .omc/state/token-compact-state.json; then
    pass "R29 compact-detect 已写 compact-state"
else
    fail "R29 compact-detect 未写 compact-state"
fi
rm -f .omc/state/token-compact-state.json

TOTAL=$((TOTAL+1))
run_case "R29 compact-detect: 普通输入应静默退出" \
  'ls' \
  "compact-detect.sh" 0 ""
if [ ! -f .omc/state/token-compact-state.json ]; then
    pass "R29 compact-detect 非 compact 正确放行"
else
    fail "R29 compact-detect 非 compact 错误触发了写入"
fi
rm -f .omc/state/token-compact-state.json

# --- R29: token_writer (PostToolUse/PostToolUseFailure token tracking) ---
TOTAL=$((TOTAL+1))
rm -f .omc/state/token-tracking-index.json
run_case "R29 token_writer: --reset 应设 usage=0" \
  '' \
  "token_writer.sh" 0 ""
# token_writer without args is a no-op for default values; use --reset
bash .claude/hooks/token_writer.sh --reset 2>/dev/null
if [ -f .omc/state/token-tracking-index.json ]; then
    USAGE=$(python3 -c "import json; print(json.load(open('.omc/state/token-tracking-index.json')).get('usage', -1))" 2>/dev/null)
    if [ "$USAGE" = "0" ]; then
        pass "R29 token_writer --reset usage=0"
    else
        fail "R29 token_writer --reset usage=$USAGE 应为 0"
    fi
else
    fail "R29 token_writer --reset 未写 index"
fi

TOTAL=$((TOTAL+1))
run_case "R29 token_writer: --increment 应递增 usage" \
  '' \
  "token_writer.sh" 0 ""
bash .claude/hooks/token_writer.sh --increment 2>/dev/null
if [ -f .omc/state/token-tracking-index.json ]; then
    USAGE=$(python3 -c "import json; print(json.load(open('.omc/state/token-tracking-index.json')).get('usage', 0))" 2>/dev/null)
    if [ "$USAGE" -gt 0 ]; then
        pass "R29 token_writer --increment usage=$USAGE"
    else
        fail "R29 token_writer --increment usage=$USAGE 应 >0"
    fi
else
    fail "R29 token_writer --increment 未写 index"
fi

log ""
log "========================================"
log "summary: $((TOTAL-FAILED))/$TOTAL passed, $FAILED failed"
log "log file: $LOG"
log "========================================"
exit $FAILED
