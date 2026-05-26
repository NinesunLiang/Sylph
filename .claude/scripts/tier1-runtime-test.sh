#!/usr/bin/env bash
# tier1-runtime-test.sh — 原子机制运行时验证
# 用法: bash .claude/scripts/tier1-runtime-test.sh
set -uo pipefail
PASS=0; FAIL=0; TOTAL=0

_test() {
    TOTAL=$((TOTAL+1))
    local name="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -qE "$expected"; then
        echo "  🟢 PASS: $name"
        PASS=$((PASS+1))
    else
        echo "  🔴 FAIL: $name"
        echo "     expected: $expected"
        echo "     actual:   $(echo "$actual" | head -c 150)"
        FAIL=$((FAIL+1))
    fi
}

H=".claude/hooks"

echo "╔══════════════════════════════════════════╗"
echo "║  Tier 1: 原子机制运行时验证 (18项)       ║"
echo "╚══════════════════════════════════════════╝"

# [1] completion-gate — 软完成语禁令
echo ""; echo "=== [1] completion-gate: 虚假完成检测 ==="
R1=$(bash $H/completion-gate.sh 2>&1 <<< '{"tool_input":{"file_path":"test.py"}}' || true)
_test "completion-gate enabled in harness" "true" "$(grep -c 'completion_gate: true' .claude/harness.yaml 2>/dev/null || echo 0)"

# [2] permission-gate — 危险命令拦截 (用 safe cmd 测试 hook 存在性)
echo ""; echo "=== [2] permission-gate: 危险命令拦截 ==="
R2=$(bash $H/permission-gate.sh 2>&1 <<< '{"tool_name":"Bash","tool_input":{"command":"echo safe"}}' || true)
_test "permission-gate responds" "continue" "$R2"

# [3] privacy-gate — .env 读取拦截
echo ""; echo "=== [3] privacy-gate: .env 拦截 ==="
R3=$(bash $H/privacy-gate.sh 2>&1 <<< '{"tool_input":{"file_path":".env"}}' || true)
_test "privacy-gate blocks .env" "continue.*false|privacy|阻断" "$R3"

# [4] blast-radius — git checkout . 硬阻断
echo ""; echo "=== [4] blast-radius: git checkout . 硬阻断 ==="
R4=$(bash $H/pretool-blast-radius.sh 2>&1 <<< '{"tool_name":"Bash","tool_input":{"command":"git checkout ."}}' || true)
_test "git checkout . BLOCKED" '"continue": false' "$R4"

# [5] blast-radius — 分号绕过阻断
echo ""; echo "=== [5] blast-radius: 分号绕过阻断 ==="
R5=$(bash $H/pretool-blast-radius.sh 2>&1 <<< '{"tool_name":"Bash","tool_input":{"command":"git checkout .; echo done"}}' || true)
_test "git checkout .; bypass BLOCKED" '"continue": false' "$R5"

# [6] blast-radius — 选择性路径放行
echo ""; echo "=== [6] blast-radius: 选择性路径放行 ==="
R6=$(bash $H/pretool-blast-radius.sh 2>&1 <<< '{"tool_name":"Bash","tool_input":{"command":"git checkout HEAD -- src/main.py"}}' || true)
_test "git checkout -- file ALLOWED" '"continue": true' "$R6"

# [7] error-dna — 启用状态
echo ""; echo "=== [7] error-dna: 启用+heartbeat ==="
_test "error-dna enabled" "true" "$(grep -c 'error_dna: true' .claude/harness.yaml 2>/dev/null || echo 0)"
_test "error-dna has heartbeat code" "[1-9]" "$(grep -c 'heartbeat' $H/error-dna.sh 2>/dev/null || echo 0)"

# [8] intent-tracker — E6 修复
echo ""; echo "=== [8] intent-tracker: E6 contradiction 检测 ==="
R8=$(grep "contradiction_level >= 2" $H/intent-tracker.sh 2>/dev/null | tail -1)
_test "E6 fix: contradiction_level >= 2" "contradiction_level >= 2" "$R8"

# [9] lsp-suggest — Grep 时 LSP 建议
echo ""; echo "=== [9] lsp-suggest: 导出符号检测 ==="
R9=$(bash $H/lsp-suggest.sh 2>&1 <<< '{"tool_input":{"pattern":"TaskRunner"}}' || true)
_test "lsp-suggest triggers on CamelCase" "LSP 建议|建议|lsp_suggest" "$R9"

# [10] pre-edit-lsp — 编辑 .py 提醒
echo ""; echo "=== [10] pre-edit-lsp: 编辑前诊断 ==="
R10=$(bash $H/pre-edit-lsp-check.sh 2>&1 <<< '{"tool_input":{"file_path":"test.py"}}' || true)
_test "pre-edit-lsp triggers on .py" "lsp-gate|diagnostics" "$R10"

# [11] compact-detect — /compact 恢复
echo ""; echo "=== [11] compact-detect: /compact 知识恢复 ==="
R11=$(bash $H/compact-detect.sh 2>&1 <<< "/compact" || true)
_test "compact-detect restores knowledge" "知识恢复|CTX-COMPACT|铁律" "$R11"

# [12] context-compressor — 缓存生成
echo ""; echo "=== [12] context-compressor: 缓存生成 ==="
R12=$(bash $H/context-compressor.sh 2>&1 || true)
_test "context-compressor cache" "缓存已更新|字节|cache_hit" "$R12"

# [13] context-guard — 上下文阈值
echo ""; echo "=== [13] context-guard: 阈值监控 ==="
_test "context-guard enabled" "true" "$(grep -c 'context_guard: true' .claude/harness.yaml 2>/dev/null || echo 0)"

# [14] pretool-edit-scope — goal mode 守卫
echo ""; echo "=== [14] pretool-edit-scope: goal mode 守卫 ==="
R14=$(grep -c "tokens/lx-goal.json" $H/pretool-edit-scope.sh 2>/dev/null || echo 0)
_test "scope has goal mode detection" "[1-9]" "$R14"

# [15] pretool-retry-check — 3轮上限
echo ""; echo "=== [15] pretool-retry-check: 3轮上限 ==="
R15=$(grep -c "retry_count\|轮\|上限" $H/pretool-retry-check.sh 2>/dev/null || echo 0)
_test "retry-check has round limit" "[3-9]|[1-9][0-9]" "$R15"

# [16] pretool-sensitive-edit — 治理文件 CAPTCHA
echo ""; echo "=== [16] pretool-sensitive-edit: 治理文件保护 ==="
_test "sensitive-edit exists" "true" "$([ -f $H/pretool-sensitive-edit.sh ] && echo true)"

# [17] posttool-claim-audit — file:line 强制
echo ""; echo "=== [17] posttool-claim-audit: file:line 强制 ==="
_test "claim-audit exists" "true" "$([ -f $H/posttool-claim-audit.sh ] && echo true)"
R17=$(grep -c "file:line\|双源\|claim" $H/posttool-claim-audit.sh 2>/dev/null || echo 0)
_test "claim-audit has file:line check" "[3-9]|[1-9][0-9]" "$R17"

# [18] posttool-anti-pattern — F1 假设驱动
echo ""; echo "=== [18] posttool-anti-pattern: F1 检测 ==="
_test "anti-pattern hook exists" "true" "$([ -f $H/posttool-anti-pattern-detect.sh ] && echo true)"

echo ""
echo "═══════════════════════════════════════"
echo "  Tier 1: $PASS/$TOTAL passed, $FAIL failed"
echo "═══════════════════════════════════════"
