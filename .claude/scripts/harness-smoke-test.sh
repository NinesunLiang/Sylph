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
# 清理可能残留的无人值守/幽灵模式文件，防止干扰阻断测试
rm -f .omc/state/.unattended-mode .omc/state/autonomous.active .omc/state/ghost-mode.json
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

# --- ghost/unattended mode 降级测试（P0 改造验证）---
# 测试前清理任何残留
rm -f .omc/state/ghost-mode.json .omc/state/unattended-mode.json .omc/state/autonomous.active
# R40: Ghost mode 下所有门禁降级为"记录+跳过"

# ---- Setup: 创建活跃 ghost-mode.json ----
python3 -c "
import json
d = {'active': True, 'mode': 'ghost', 'direction': 'test', 'cycle_interval_seconds': 600,
     'expires_at': '2099-01-01T00:00:00', 'retry_count': 0, 'skipped_risks': []}
json.dump(d, open('.omc/state/ghost-mode.json', 'w'))
"
# R40-1: Ghost mode 下 context-guard Write @ 95% 不应阻断（仅记录）
echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json
run_case "R40 ghost mode: context-guard Write @ 95% 降级放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 0 ""
rm -f .omc/state/token-tracking-index.json

# R40-2: Ghost mode 下 permission-gate rm -rf 不应阻断
run_case "R40 ghost mode: permission-gate rm -rf 降级放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \
  "permission-gate.sh" 0 "\[ghost\]"

# R40-3: Ghost mode 下 edit-guard 未 Read 不应阻断
run_case "R40 ghost mode: edit-guard 未 Read 降级放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/test.go"}}' \
  "edit-guard.sh" 0 ""

# ---- Setup: 创建 inactive（已过期）ghost-mode.json ----
python3 -c "
import json
d = {'active': True, 'mode': 'ghost', 'direction': 'test', 'cycle_interval_seconds': 600,
     'expires_at': '2020-01-01T00:00:00', 'retry_count': 0, 'skipped_risks': []}
json.dump(d, open('.omc/state/ghost-mode.json', 'w'))
"
# R40-4: 过期 ghost mode 应恢复阻断（context-guard Write 恢复 hard block）
echo '{"usage":190000,"limit":200000}' > .omc/state/token-tracking-index.json
run_case "R40 ghost mode expired: context-guard Write 恢复阻断" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"x"}}' \
  "context-guard.sh" 2 "Context Guard"
rm -f .omc/state/token-tracking-index.json

# ---- Setup: 创建活跃 unattended-mode.json ----
python3 -c "
import json
d = {'active': True, 'mode': 'unattended', 'goal': 'test',
     'expires_at': '2099-01-01T00:00:00', 'retry_count': 0, 'skipped_risks': [], 'completed_tasks': []}
json.dump(d, open('.omc/state/unattended-mode.json', 'w'))
"
# R40-5: Unattended mode 下 permission-gate 应降级
run_case "R40 unattended mode: permission-gate rm -rf 降级放行" \
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \
  "permission-gate.sh" 0 "\[unattended\]"

# 测试完成后清理模式文件
rm -f .omc/state/ghost-mode.json .omc/state/unattended-mode.json .omc/state/autonomous.active

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
run_case "pretool-edit-scope: 越界文件应自动加入范围" \
  '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/payment.go"}}' \
  "pretool-edit-scope.sh" 0 "自动加入编辑范围"
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

# R38 posttool-claim-audit: 铁律 #1 强制校验回归 — 使用 bash ... hook.sh Edit 直调(传递$1)
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 posttool-claim-audit: 无 claim 时放行"
rm -f .omc/state/read-tracker.txt
echo '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/any.go"}}' | \
    bash .claude/hooks/posttool-claim-audit.sh Edit >/dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "R38 posttool-claim-audit 无 claim 放行"
else
    fail "R38 posttool-claim-audit 无 claim 不应阻断"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 posttool-claim-audit: 未读 claim 应阻断"
_CLAIM_OUT="/tmp/smoke-claim-$$.out"
echo '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"/tmp/claim-test.go","new_content":"Reference: ./src/nonexistent_claim_file_test.go:42"}}' | \
    bash .claude/hooks/posttool-claim-audit.sh Edit > "$_CLAIM_OUT" 2>&1
_CLAIM_EXIT=$?
if [ "$_CLAIM_EXIT" = "2" ] && grep -q "IRRELEVANT_CLAIM\|铁律\|编造" "$_CLAIM_OUT"; then
    pass "R38 posttool-claim-audit 正确阻断未读 claim (exit=$_CLAIM_EXIT)"
else
    fail "R38 posttool-claim-audit 未阻断未读 claim (exit=$_CLAIM_EXIT out=$(head -c200 $_CLAIM_OUT | tr '\n' ' '))"
fi
rm -f "$_CLAIM_OUT" .omc/state/read-tracker.txt

# R38 posttool-claim-audit: settings.json 注册
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 posttool-claim-audit: settings.json 注册"
if grep -q "posttool-claim-audit.sh" .claude/settings.json; then
    pass "R38 posttool-claim-audit 已注册 settings.json"
else
    fail "R38 posttool-claim-audit 未注册 settings.json"
fi

# R38 posttool-claim-audit: harness.yaml 开关
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 posttool-claim-audit: harness.yaml 开关"
if grep -q "posttool_claim_audit: true" .claude/harness.yaml; then
    pass "R38 posttool-claim-audit harness.yaml 已启用"
else
    fail "R38 posttool-claim-audit harness.yaml 未启用"
fi

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

# R30 source mirror: 一致性校验
TOTAL=$((TOTAL+1))
_SM_OUT="/tmp/smoke-source-mirror-$$.out"
log ""
log "[$TOTAL] R30 source mirror: 一致性应全绿"
bash .claude/scripts/audit-hooks.sh --check-source-mirror > "$_SM_OUT" 2>&1
if grep -q -e "全部一致" -e "已废弃" "$_SM_OUT"; then
    pass "R30 source mirror 一致性校验通过"
else
    fail "R30 source mirror 存在漂移"
    grep "🔴" "$_SM_OUT" | head -5
fi
rm -f "$_SM_OUT"

# --- R23: 新注册的 8 个 hook — 业务级验收（R24-S2 升级版） ---

# UX-1.3 lsp-suggest: 首次导出符号 Grep 应警告（exit 0，不再阻断）
rm -f .omc/state/lsp-suggested
run_case "UX-1.3 lsp-suggest: 首次 Grep 导出符号应提示 LSP（不阻断）" \
  '{"hook_event_name":"PreToolUse","tool_name":"Grep","tool_input":{"pattern":"SomeExportedSymbol"}}' \
  "lsp-suggest.sh" 0 "LSP 建议|lsp_workspace_symbols"
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

# R23/R24 pretool-rule-anchor → 已合并到 pretool-edit-scope.sh
# 在 scope 匹配 + 高轮次时应输出规则锚定
rm -f .omc/state/session-turns.json
echo "/tmp/x" > .omc/state/current-scope.txt
run_case "R23/R24 pretool-rule-anchor(合并): 低轮次无锚定" \
  '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' \
  "pretool-edit-scope.sh" 0 ""

# R24 pretool-rule-anchor(合并): 轮次 >=15 应输出规则锚定
echo '{"count": 20}' > .omc/state/session-turns.json
_ANCHOR_OUT="/tmp/smoke-anchor-$$.out"
echo '{"hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"/tmp/x"}}' | bash .claude/hooks/pretool-edit-scope.sh > "$_ANCHOR_OUT" 2>&1
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R24 pretool-rule-anchor(合并): 高轮次应输出锚定"
if grep -qE "规则锚定|禁止编造|VERIFIED|漂移" "$_ANCHOR_OUT"; then
    pass "R24 pretool-rule-anchor(合并) 已通过 pretool-edit-scope 输出锚定"
else
    fail "R24 pretool-rule-anchor(合并) 未输出锚定"
fi
rm -f "$_ANCHOR_OUT" .omc/state/session-turns.json .omc/state/current-scope.txt

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

# --- R31: session-dump.json 结构完整性 ---
TOTAL=$((TOTAL+1))
_DUMP_FILE=".omc/state/session-dump.json"
log ""
log "[$TOTAL] R31 session-dump: auto-snapshot 应写入结构化 dump"
echo '{"hook_event_name":"Stop"}' | bash .claude/hooks/auto-snapshot.sh > /dev/null 2>&1
if [ -f "$_DUMP_FILE" ]; then
    _DUMP_OK=$(python3 -c "
import json
d = json.load(open('$_DUMP_FILE'))
fields = ['git_state', 'error_summary', 'todo_queue', 'active_features', 'token_usage', 'claude_next_hits', 'edit_log']
present = [f for f in fields if f in d]
print(f'{len(present)}/{len(fields)} fields: {present}')
" 2>/dev/null)
    if echo "$_DUMP_OK" | grep -q "7/7"; then
        pass "R31 session-dump 结构完整 ($_DUMP_OK)"
    else
        fail "R31 session-dump 字段不完整 ($_DUMP_OK)"
    fi
else
    fail "R31 session-dump 未生成"
fi
rm -f "$_DUMP_FILE"

# --- R32: intent-tracker 注册与基本功能 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R32 intent-tracker: 注册检查"
if grep -q "intent-tracker.sh" .claude/settings.json; then
    pass "R32 intent-tracker 已注册 settings.json"
else
    fail "R32 intent-tracker 未注册"
fi
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R32 intent-tracker: harness.yaml 开关"
if grep -q "intent_tracker: true" .claude/harness.yaml; then
    pass "R32 intent-tracker harness.yaml 已启用"
else
    fail "R32 intent-tracker harness.yaml 未启用"
fi
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R32 intent-tracker: 非 Edit 应静默退出"
echo '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' | \
    bash .claude/hooks/intent-tracker.sh > /dev/null 2>&1
_EXIT=$?
if [ "$_EXIT" = "0" ]; then
    pass "R32 intent-tracker 非 Edit 放行 (exit=0)"
else
    fail "R32 intent-tracker 非 Edit 不应阻断 (exit=$_EXIT)"
fi

# --- R33: validate_skill_refs.py skill 引用校验 ---
TOTAL=$((TOTAL+1))
_SKILL_REF_OUT="/tmp/smoke-skill-ref-$$.out"
python3 .claude/scripts/validate_skill_refs.py > "$_SKILL_REF_OUT" 2>&1
_SKILL_REF_EXIT=$?
log ""
log "[$TOTAL] R33 validate_skill_refs: 所有 skill 引用应有效"
if [ "$_SKILL_REF_EXIT" = "0" ] && grep -q "PASS" "$_SKILL_REF_OUT"; then
    SKILL_COUNT=$(grep -oE 'All [0-9]+ skills have valid references' "$_SKILL_REF_OUT" | grep -oE '[0-9]+')
    pass "R33 validate_skill_refs 全部有效 ($SKILL_COUNT skills, exit=$_SKILL_REF_EXIT)"
else
    fail "R33 validate_skill_refs 发现破损引用 (exit=$_SKILL_REF_EXIT)"
    grep -E "broken|FAIL|missing" "$_SKILL_REF_OUT" | head -5
fi
rm -f "$_SKILL_REF_OUT"

# --- R34: audit-hooks --check-source-mirror 扩展: settings.json + harness.yaml 三方对账 ---
TOTAL=$((TOTAL+1))
_SM_EXT_OUT="/tmp/smoke-mirror-ext-$$.out"
bash .claude/scripts/audit-hooks.sh --check-source-mirror > "$_SM_EXT_OUT" 2>&1
log ""
log "[$TOTAL] R34 source mirror 扩展: settings.json + harness.yaml 注册一致性"
if grep -q "已废弃" "$_SM_EXT_OUT"; then
    pass "R34 source mirror 已废弃，跳过"
elif grep -q "config mirror" "$_SM_EXT_OUT"; then
    fail "R34 source mirror config 存在漂移"
    grep "🔴" "$_SM_EXT_OUT" | head -5
else
    pass "R34 source mirror config 校验通过 (settings.json + harness.yaml)"
fi
rm -f "$_SM_EXT_OUT"

# --- R35: error-dna-auto-fix.sh 回归 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R35 error-dna-auto-fix: 语法检查"
bash -n .claude/hooks/error-dna-auto-fix.sh
if [ $? -eq 0 ]; then
    pass "R35 error-dna-auto-fix 语法通过"
else
    fail "R35 error-dna-auto-fix 语法错误"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R35 error-dna-auto-fix: 无 error-dna.json 时静默退出"
echo '{"hook_event_name":"Stop"}' | bash .claude/hooks/error-dna-auto-fix.sh > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "R35 error-dna-auto-fix 无文件静默退出"
else
    fail "R35 error-dna-auto-fix 无文件不应阻断 (exit=$?)"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R35 error-dna-auto-fix: 只读不写验证"
_READ_ONLY=$(grep -cE '\bwrite\b|json\.dump\(' .claude/hooks/error-dna-auto-fix.sh 2>/dev/null; true)
if [ "$_READ_ONLY" = "0" ] 2>/dev/null; then
    pass "R35 error-dna-auto-fix 只读不写 (0 write calls)"
else
    fail "R35 error-dna-auto-fix 发现写操作 (grep-count=$_READ_ONLY)"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R35 error-dna-auto-fix: settings.json 注册"
if grep -q "error-dna-auto-fix.sh" .claude/settings.json; then
    pass "R35 error-dna-auto-fix 已注册 settings.json"
else
    fail "R35 error-dna-auto-fix 未注册 settings.json"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R35 error-dna-auto-fix: harness.yaml 开关"
if grep -q "error_dna_auto_fix: true" .claude/harness.yaml; then
    pass "R35 error-dna-auto-fix harness.yaml 已启用"
else
    fail "R35 error-dna-auto-fix harness.yaml 未启用"
fi

# --- R36: knowledge-condenser.sh 回归 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R36 knowledge-condenser: 语法检查"
bash -n .claude/hooks/knowledge-condenser.sh
if [ $? -eq 0 ]; then
    pass "R36 knowledge-condenser 语法通过"
else
    fail "R36 knowledge-condenser 语法错误"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R36 knowledge-condenser: 无 claude-next.md 时静默退出"
_OLD_NEXT=""
[ -f ".claude/claude-next.md" ] && _OLD_NEXT=$(cat .claude/claude-next.md) && mv .claude/claude-next.md /tmp/smoke-next-$$.bak
echo '{"hook_event_name":"Stop"}' | bash .claude/hooks/knowledge-condenser.sh > /dev/null 2>&1
_RC=$?
if [ -f "/tmp/smoke-next-$$.bak" ]; then
    mv /tmp/smoke-next-$$.bak .claude/claude-next.md
fi
if [ "$_RC" = "0" ]; then
    pass "R36 knowledge-condenser 无文件静默退出"
else
    fail "R36 knowledge-condenser 无文件不应阻断 (exit=$_RC)"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R36 knowledge-condenser: 双格式解析验证"
_NEXT_EXISTS="no"
[ -f ".claude/claude-next.md" ] && _NEXT_EXISTS="yes"
_NEXT_HITS=$(python3 -c "
import re
try:
    c = open('.claude/claude-next.md').read()
    # [seed:*] format
    m1 = re.findall(r'hits:(\d+)', c)
    print(','.join(m1) if m1 else '0')
except: print('err')
" 2>/dev/null)
if [ "$_NEXT_EXISTS" = "yes" ] && [ -n "$_NEXT_HITS" ] && [ "$_NEXT_HITS" != "err" ]; then
    pass "R36 knowledge-condenser 双格式解析正常 (hits: $_NEXT_HITS)"
else
    fail "R36 knowledge-condenser 解析失败"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R36 knowledge-condenser: settings.json 注册"
if grep -q "knowledge-condenser.sh" .claude/settings.json; then
    pass "R36 knowledge-condenser 已注册 settings.json"
else
    fail "R36 knowledge-condenser 未注册 settings.json"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R36 knowledge-condenser: harness.yaml 开关"
if grep -q "knowledge_condenser: true" .claude/harness.yaml; then
    pass "R36 knowledge-condenser harness.yaml 已启用"
else
    fail "R36 knowledge-condenser harness.yaml 未启用"
fi

# --- R37: posttool-handoff-writer.sh 回归 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R37 posttool-handoff-writer: 语法检查"
bash -n .claude/hooks/posttool-handoff-writer.sh
if [ $? -eq 0 ]; then
    pass "R37 posttool-handoff-writer 语法通过"
else
    fail "R37 posttool-handoff-writer 语法错误"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R37 posttool-handoff-writer: 非 completed 静默退出"
echo '{"tool":"TaskUpdate","tool_input":{"status":"in_progress"}}' | bash .claude/hooks/posttool-handoff-writer.sh > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "R37 posttool-handoff-writer 非 completed 静默退出"
else
    fail "R37 posttool-handoff-writer 非 completed 不应阻断"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R37 posttool-handoff-writer: settings.json 注册"
if grep -q "posttool-handoff-writer.sh" .claude/settings.json; then
    pass "R37 posttool-handoff-writer 已注册 settings.json"
else
    fail "R37 posttool-handoff-writer 未注册 settings.json"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R37 posttool-handoff-writer: harness.yaml 开关"
if grep -q "posttool_handoff_writer: true" .claude/harness.yaml; then
    pass "R37 posttool-handoff-writer harness.yaml 已启用"
else
    fail "R37 posttool-handoff-writer harness.yaml 未启用"
fi

# --- R38: auto-scope.sh 回归 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 auto-scope: 语法检查"
bash -n .claude/scripts/auto-scope.sh
if [ $? -eq 0 ]; then
    pass "R38 auto-scope 语法通过"
else
    fail "R38 auto-scope 语法错误"
fi

TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R38 auto-scope: 静默执行（无 plan.md fallback）"
bash .claude/scripts/auto-scope.sh > /dev/null 2>&1
_RC=$?
if [ "$_RC" = "0" ]; then
    pass "R38 auto-scope 静默执行 (exit=$_RC)"
else
    fail "R38 auto-scope 不应阻断 (exit=$_RC)"
fi

# --- R39: completion-gate 证据质量评分回归 ---
TOTAL=$((TOTAL+1))
log ""
log "[$TOTAL] R39 completion-gate quality: harness.yaml 配置检查"
if grep -q "quality_threshold" .claude/harness.yaml || grep -q "quality_threshold" .claude/profiles/base/harness.yaml 2>/dev/null; then
    pass "R39 completion-gate quality 配置存在"
else
    fail "R39 completion-gate quality 无 quality_threshold 配置"
fi

log ""
log "========================================"
log "summary: $((TOTAL-FAILED))/$TOTAL passed, $FAILED failed"
log "log file: $LOG"
log "========================================"
exit $FAILED
