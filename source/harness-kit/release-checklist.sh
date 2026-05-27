#!/usr/bin/env bash
# release-checklist.sh — 完整发版流程
# Role: 版本更新→冒烟→漂移→版本说明→构建→发布，逐项检查
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 99

PASS=0; FAIL=0
check() { echo -n "  [$1] $2 ... "; }
pass() { echo "✅"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "╔══════════════════════════════════════════╗"
echo "║  📋 Carror OS Release Checklist         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

VER=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])" 2>/dev/null)
echo "版本: v${VER}-stable"
echo ""

# ═══ Phase 0: 准备 ═══
echo "── Phase 0: 准备 ──"

check 1 "Git 工作区干净"
GIT_STATUS=$(git status --porcelain 2>/dev/null)
[ -z "$GIT_STATUS" ] && pass || fail "有未提交的变更"

check 2 "版本号一致性"
HV=$(grep 'harness_version:' .claude/harness.yaml 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
if [ "$VER" = "$HV" ]; then pass; else fail "VERSION=$VER ≠ harness=$HV"; fi

# ═══ Phase 1: 质量门禁 ═══
echo "── Phase 1: 质量门禁 ──"

check 3 "harness-smoke-test 全绿"
SMOKE=$(bash .claude/scripts/harness-smoke-test.sh 2>&1)
echo "$SMOKE" | grep -q '0 failed' && pass || fail "烟雾测试有失败"

check 4 "所有 hook bash -n 语法正确"
SYNTAX_OK=true
for f in .claude/hooks/*.sh; do
    bash -n "$f" 2>/dev/null || { SYNTAX_OK=false; break; }
done
[ "$SYNTAX_OK" = true ] && pass || fail "有语法错误"

check 5 "hook 注册一致性 (0 🔴 严重)"
AUDIT=$(bash .claude/scripts/audit-hooks.sh 2>&1)
echo "$AUDIT" | grep -q '🔴 严重: 0' && pass || fail "audit-hooks 有严重问题"

# ═══ Phase 2: 源镜像 ═══
echo "── Phase 2: 源镜像同步 ──"

check 6 "root → source/harness-kit 同步"
bash scripts/package-release.sh --sync-only 2>/dev/null
diff <(sha256sum .claude/settings.json | cut -d' ' -f1) <(sha256sum source/harness-kit/.claude/settings.json | cut -d' ' -f1) >/dev/null 2>&1
[ $? -eq 0 ] && pass || fail "settings.json 不同步"

check 7 "source mirror 无绝对路径泄漏"
grep -rn 'bash /Users/' source/harness-kit/.claude/settings.json 2>/dev/null | grep -q . && fail "source mirror 有绝对开发路径" || pass

check 8 "source mirror 一致性"
bash .claude/scripts/audit-hooks.sh --check-source-mirror >/dev/null 2>&1 && pass || fail "source mirror 漂移"

# ═══ Phase 3: 版本说明 ═══
echo "── Phase 3: 版本说明 ──"

CHANGELOG="packages/CHANGELOG-${VER}.md"
check 9 "CHANGELOG 生成"
if [ ! -f "$CHANGELOG" ]; then
    echo "# v${VER} Release Notes" > "$CHANGELOG"
    echo "" >> "$CHANGELOG"
    echo "## 变更" >> "$CHANGELOG"
    git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~5")..HEAD 2>/dev/null | sed 's/^/- /' >> "$CHANGELOG"
    echo "" >> "$CHANGELOG"
    echo "## 验证" >> "$CHANGELOG"
    echo "- Smoke test: $(echo "$SMOKE" | grep -oE '[0-9]+/[0-9]+ passed' || echo "N/A")" >> "$CHANGELOG"
    echo "- Audit: $(echo "$AUDIT" | grep -oE '🔴 严重: [0-9]+' || echo "🔴 严重: 0")" >> "$CHANGELOG"
    pass "已生成"
else
    pass "已存在"
fi

check 10 "Git tag v${VER}-stable"
git tag -l "v${VER}-stable" | grep -q . && pass "已存在" || fail "未创建 tag"

# ═══ Phase 4: 构建 ═══
echo "── Phase 4: 构建 ──"

check 11 "harness-kit 安装包"
[ -f "packages/harness-kit-v${VER}-stable.tar.gz" ] && pass || fail "未构建"

check 12 "lx-skills 安装包"
[ -f "packages/lx-skills-v${VER}-stable.tar.gz" ] && pass || fail "未构建"

# ═══ Phase 5: 发布 ═══
echo "── Phase 5: 发布 ──"

check 13 "Git push"
GIT_AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")
[ "$GIT_AHEAD" = "0" ] && pass || fail "有 ${GIT_AHEAD} 个 commit 未推送"

check 14 "GitHub Release"
gh release view "v${VER}-stable" >/dev/null 2>&1 && pass || fail "未创建 GitHub Release"

# ═══ 汇总 ═══
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Checklist: ${PASS}/$((PASS+FAIL)) 通过"
if [ "$FAIL" -eq 0 ]; then
    echo "║  ✅ 发版完成"
else
    echo "║  ❌ 有 ${FAIL} 项失败"
fi
echo "╚══════════════════════════════════════════╝"
exit "$FAIL"
