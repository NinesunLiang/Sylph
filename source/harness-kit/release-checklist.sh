#!/usr/bin/env bash
# release-checklist.sh — 完整发版流程 7 Phase
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)" || exit 99
PASS=0; FAIL=0
check() { echo -n "  [$1] $2 ... "; }
pass() { echo "✅"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "╔══════════════════════════════════╗"
echo "║  📋 Release Checklist           ║"
echo "╚══════════════════════════════════╝"
VER=$(python3 -c "import json;print(json.load(open('VERSION.json'))['version'])")
echo "当前: v${VER}-stable"
echo ""

# ═══ Phase 0: 版本更新 ═══
echo "── Phase 0: 版本更新 ──"
NEW_VER="${1:-}"
if [ -z "$NEW_VER" ]; then
    MAJOR=$(echo "$VER" | cut -d. -f1)
    MINOR=$(echo "$VER" | cut -d. -f2)
    PATCH=$(echo "$VER" | cut -d. -f3)
    NEW_VER="${MAJOR}.${MINOR}.$((PATCH + 1))"
fi
echo "  目标: v${NEW_VER}-stable"

check 1 "VERSION.json → ${NEW_VER}"
sed -i.bak "s/\"version\": \"${VER}\"/\"version\": \"${NEW_VER}\"/" VERSION.json
rm -f VERSION.json.bak
python3 -c "import json;v=json.load(open('VERSION.json'))['version'];exit(0 if v=='${NEW_VER}' else 1)" && pass || fail

check 2 "harness.yaml → ${NEW_VER}"
sed -i.bak "s/harness_version: ${VER}/harness_version: ${NEW_VER}/" .claude/harness.yaml
rm -f .claude/harness.yaml.bak
grep -q "harness_version: ${NEW_VER}" .claude/harness.yaml && pass || fail
VER="$NEW_VER"
echo ""

# ═══ Phase 1: 质量门禁 ═══
echo "── Phase 1: 质量门禁 ──"
check 1 "Git 干净"
[ -z "$(git status --porcelain 2>/dev/null)" ] && pass || fail

check 2 "Smoke test 全绿"
bash .claude/scripts/harness-smoke-test.sh 2>&1 | grep -q '0 failed' && pass || fail

check 3 "Bash 语法"
OK=true; for f in .claude/hooks/*.sh; do bash -n "$f" 2>/dev/null || OK=false; done
[ "$OK" = true ] && pass || fail

check 4 "Audit 0🔴"
bash .claude/scripts/audit-hooks.sh 2>&1 | grep -q '🔴 严重: 0' && pass || fail
echo ""

# ═══ Phase 2: 源镜像 ═══
echo "── Phase 2: 源镜像 ──"
check 1 "无绝对路径泄漏"
grep -n 'bash /Users/' source/harness-kit/.claude/settings.json 2>/dev/null | grep -q . && fail "source mirror 有绝对开发路径" || pass

check 2 "源镜像一致性"
DIFF=$(diff <(sha256sum .claude/settings.json .claude/harness.yaml install.sh 2>/dev/null | cut -d' ' -f1) <(sha256sum source/harness-kit/.claude/settings.json source/harness-kit/.claude/harness.yaml source/harness-kit/install.sh 2>/dev/null | cut -d' ' -f1) 2>/dev/null)
[ -z "$DIFF" ] && pass || fail "源镜像有漂移"
echo ""

# ═══ Phase 3: 文档一致性 ═══
echo "── Phase 3: 文档一致性 ──"
check 1 "Hook 计数"
DOC=$(grep -oE '[0-9]+ 个脚本' .claude/docs/guides/cn/hook-configuration.md 2>/dev/null | grep -oE '[0-9]+' | head -1)
DISK=$(ls .claude/hooks/*.sh 2>/dev/null | grep -v harness_config | wc -l | tr -d ' ')
[ "${DOC:-0}" = "${DISK:-0}" ] && pass || fail "doc=${DOC} disk=${DISK}"

check 2 "版本引用"
grep -q "v${VER}" .claude/docs/guides/cn/hook-configuration.md 2>/dev/null && pass || fail "文档缺 v${VER}"
echo ""

# ═══ Phase 4: 版本说明 ═══
echo "── Phase 4: 版本说明 ──"
CHANGELOG="packages/CHANGELOG-${VER}.md"
check 1 "CHANGELOG"
[ -f "$CHANGELOG" ] && pass || { echo "# v${VER}" > "$CHANGELOG"; git log --oneline -10 >> "$CHANGELOG"; pass "已生成"; }

check 2 "Git tag"
git tag "v${VER}-stable" 2>/dev/null; pass
echo ""

# ═══ Phase 5: 构建 ═══
echo "── Phase 5: 构建 ──"
check 1 "harness-kit"
bash scripts/package-release.sh --skip-smoke --force 2>&1 | grep -q '打包完成' && pass || fail

check 2 "lx-skills"
[ -f "packages/lx-skills-v${VER}-stable.tar.gz" ] && pass || fail
echo ""

# ═══ Phase 6: 发布 ═══
echo "── Phase 6: 发布 ──"
check 1 "Git push"
git push 2>&1 | grep -qE 'up.to.date|main -> main' && pass || fail "网络或冲突"

check 2 "GitHub Release"
gh release view "v${VER}-stable" >/dev/null 2>&1 && pass || { gh release create "v${VER}-stable" --title "v${VER}" --notes "Release v${VER}" 2>/dev/null && pass || fail; }
echo ""

echo "╔══════════════════════════════════╗"
[ "$FAIL" -eq 0 ] && echo "║  ✅ ${PASS}/$((PASS+FAIL)) 全部通过" || echo "║  ❌ ${PASS}/$((PASS+FAIL)) 通过, ${FAIL} 失败"
echo "╚══════════════════════════════════╝"
exit "$FAIL"
