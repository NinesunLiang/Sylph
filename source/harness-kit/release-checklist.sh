#!/usr/bin/env bash
# release-checklist.sh — 发版前完整检查清单
# Role: package-release.sh 前置门禁，逐项检查，任何失败阻断发版
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 99

PASS=0; FAIL=0
check() { echo -n "  [$1] $2 ... "; }
pass() { echo "✅"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "=== Release Checklist ==="
echo ""

# 1. Git clean
check 1 "Git 工作区干净"
[ -z "$(git status --porcelain 2>/dev/null)" ] && pass || fail "有未提交的变更"

# 2. Smoke test
check 2 "harness-smoke-test 全绿"
SMOKE=$(bash .claude/scripts/harness-smoke-test.sh 2>&1)
echo "$SMOKE" | grep -q '0 failed' && pass || fail "烟雾测试有失败"

# 3. Source mirror
check 3 "source mirror 一致性"
bash .claude/scripts/audit-hooks.sh --check-source-mirror >/dev/null 2>&1 && pass || fail "source mirror 漂移"

# 4. __PROJECT_ROOT__ placeholder
check 4 "source mirror 无绝对路径泄漏"
if grep -rn '/Users/' source/harness-kit/.claude/settings.json 2>/dev/null | grep -q 'bash /Users'; then
    fail "source mirror 有绝对开发路径"
else
    pass
fi

# 5. VERSION.json consistency
check 5 "VERSION.json 一致性"
VER=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])" 2>/dev/null)
HV=$(grep 'harness_version:' .claude/harness.yaml 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
if [ "$VER" = "$HV" ]; then pass; else fail "VERSION=$VER ≠ harness=$HV"; fi

# 6. Hook registration consistency
check 6 "hook 注册一致性 (0 🔴 严重)"
AUDIT=$(bash .claude/scripts/audit-hooks.sh 2>&1)
echo "$AUDIT" | grep -q '🔴 严重: 0' && pass || fail "audit-hooks 有严重问题"

# 7. bash syntax on all hooks
check 7 "所有 hook 语法正确"
SYNTAX_OK=true
for f in .claude/hooks/*.sh; do
    bash -n "$f" 2>/dev/null || { SYNTAX_OK=false; break; }
done
[ "$SYNTAX_OK" = true ] && pass || fail "有语法错误的 hook"

echo ""
echo "=== Checklist: ${PASS}/$((PASS+FAIL)) 通过 ==="
[ "$FAIL" -eq 0 ] && echo "✅ 可以发版" || echo "❌ 有 ${FAIL} 项失败，修复后重试"
exit "$FAIL"
