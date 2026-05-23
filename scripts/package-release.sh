#!/bin/bash
# Carror OS 打包脚本
# 用法：bash scripts/package-release.sh
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

VERSION=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])")
TAG="v${VERSION}-stable"
log_info "版本：$TAG"
PKG_DIR="$PROJECT_DIR/packages"
HARNESS_SRC="source/harness-kit"
LX_SRC="source/lx-skills-v5"

# ─── G4 Meta-Oracle Release 门禁（打包前最后守门）───
log_step "G4 Meta-Oracle Release 门禁检查..."
META_ORACLE_SCRIPT="$PROJECT_DIR/.claude/scripts/meta-oracle-review.sh"
G4_PASSED=true

if [ -x "$META_ORACLE_SCRIPT" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🔍 G4 Meta-Oracle — Release 最后守门员                    ║"
    echo "║  软门禁: 自动执行检查，发现问题报告但不阻断                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # 1. source mirror 一致性检查
    if [ -x "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" ]; then
        log_info "[G4.1] source mirror 一致性检查..."
        if bash "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" --check-source-mirror 2>&1; then
            log_info "  ✅ source mirror 一致"
        else
            log_warn "  ⚠️  source mirror 漂移检测到不一致项"
            G4_PASSED=false
        fi
    fi

    # 2. harness smoke test
    SMOKE_TEST="$PROJECT_DIR/.claude/scripts/harness-smoke-test.sh"
    if [ "${1:-}" = "--skip-smoke" ] || [ "${2:-}" = "--skip-smoke" ]; then
        log_warn "[G4.2] harness-smoke-test SKIPPED (--skip-smoke)"
    elif [ -x "$SMOKE_TEST" ]; then
        log_info "[G4.2] harness-smoke-test..."
        SMOKE_OUTPUT=$(bash "$SMOKE_TEST" 2>&1)
        SMOKE_EXIT=$?
        # DG-102: grep -c 双输出修复 — 用 wc -l 替代 grep -c || echo
        FAIL_COUNT=$(echo "$SMOKE_OUTPUT" | grep -E 'FAIL|🔴' 2>/dev/null | wc -l | tr -d ' ')
        FAIL_COUNT="${FAIL_COUNT:-0}"
        if [ "$SMOKE_EXIT" -eq 0 ] && [ "$FAIL_COUNT" = "0" ]; then
            log_info "  ✅ smoke test 全绿"
        else
            log_warn "  ⚠️  smoke test 有 ${FAIL_COUNT} 项失败"
            G4_PASSED=false
        fi
    fi

    # 3. VERSION.json 一致性
    if [ -f "$PROJECT_DIR/VERSION.json" ]; then
        log_info "[G4.3] VERSION.json 一致性..."
        VER=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/VERSION.json'))['version'])" 2>/dev/null)
        if [ -n "$VER" ] && [ "$VER" = "$VERSION" ]; then
            log_info "  ✅ VERSION.json 一致 ($VER)"
        else
            log_warn "  ⚠️  VERSION.json 不一致或读取失败"
            G4_PASSED=false
        fi
    fi

    # 4. 调用 meta-oracle-review.sh G4 输出审查方法论
    log_info "[G4.4] Meta-Oracle 审查方法注入..."
    bash "$META_ORACLE_SCRIPT" G4 2>&1

    # 汇总
    echo ""
    if [ "$G4_PASSED" = true ]; then
        log_info "G4 Meta-Oracle: ✅ 全部自动检查通过"
    else
        log_warn "G4 Meta-Oracle: ⚠️  有检查项未通过 — 软门禁不阻断，但强烈建议修复后再发布"
        log_warn "  覆写 REJECT 需记录理由到 .omc/state/meta-oracle-overrides.md"
    fi
else
    log_warn "Meta-Oracle 审查脚本不存在，跳过 G4 门禁"
fi
echo ""

# ═══ DG-100 三源安全门禁 (2026-05-22) ═══
log_step "0/4 三源安全门禁..."

SAFETY_BRANCH="_safe/package-${VERSION}-$(date +%Y%m%d-%H%M%S)"

# DG-100 M5: trap EXIT 自动清理安全分支（防无限积累）
trap 'git branch -D "$SAFETY_BRANCH" 2>/dev/null || true' EXIT

# 0.1 安全分支（全量快照）
if git rev-parse --git-dir >/dev/null 2>&1; then
    git branch "$SAFETY_BRANCH" 2>/dev/null && \
        log_info "  安全分支: $SAFETY_BRANCH" || \
        log_warn "  安全分支创建失败（继续）"
fi

# 0.2 三源一致性预检
if [ -x "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" ]; then
    log_info "  三源一致性预检..."
    set +e
    MIRROR_CHECK=$(bash "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" --check-source-mirror 2>&1)
    MIRROR_EXIT=$?
    set -e
    # macOS 兼容: POSIX sed 解析红字数
    RED_COUNT=$(echo "$MIRROR_CHECK" | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
    RED_COUNT="${RED_COUNT:-0}"

    FORCE_MODE=false
    for arg in "$@"; do [ "$arg" = "--force" ] && FORCE_MODE=true; done

    # Crash 检测: 脚本异常退出
    if [ "$MIRROR_EXIT" -ne 0 ] && [ "$RED_COUNT" -eq 0 ]; then
        log_warn "  🔴 三源验证脚本异常退出 (exit=$MIRROR_EXIT)，可能为假阴性"
        echo "$MIRROR_CHECK" | tail -5
        [ "$FORCE_MODE" != "true" ] && { log_warn "  打包已阻断。--force 可跳过。"; exit 1; }
    fi

    # 漂移检测: --force 跳过，否则阻断
    if [ "$RED_COUNT" -gt 0 ]; then
        log_warn "  ⚠️  三源一致性: ${RED_COUNT} 项 CRITICAL 漂移"
        echo "$MIRROR_CHECK" | grep '🔴' | head -10
        if [ "$FORCE_MODE" != "true" ]; then
            log_warn "  打包已阻断。--force 可跳过，或先修复漂移。"
            log_info "  安全分支 $SAFETY_BRANCH 已保存当前状态。"
            exit 1
        fi
        log_info "  --force: 跳过三源门禁（风险自负）"
    else
        log_info "  ✅ 三源一致性: 通过"
    fi
else
    log_warn "  audit-hooks.sh 不可用，跳过三源预检"
fi

# 0.3 关键文件存在性+非空验证
REQUIRED_FILES=".claude/hooks/error-dna.sh .claude/hooks/intent-tracker.sh .claude/hooks/context-compressor.sh .claude/hooks/pre-edit-lsp-check.sh .claude/settings.json .claude/harness.yaml"
MISSING_FILES=""
for rf in $REQUIRED_FILES; do
    [ ! -s "$PROJECT_DIR/$rf" ] && MISSING_FILES="$MISSING_FILES $rf"
done
if [ -n "$MISSING_FILES" ]; then
    log_warn "  🔴 关键文件缺失或为空: $MISSING_FILES"
    log_warn "  打包已阻断。恢复文件后再试。"
    exit 1
fi
log_info "  ✅ 关键文件存在性: 通过"

echo ""

# ─── Step 1: root -> source/harness-kit ───
# NOTE: AGENTS.md 有意不复制（根=元项目专属，source=通用分发模板）
log_step "1/4 同步 root -> source/harness-kit..."
cp CLAUDE.md "$HARNESS_SRC/CLAUDE.md"
rsync -a --delete .claude/hooks/       "$HARNESS_SRC/.claude/hooks/"
rsync -a --delete .claude/scripts/     "$HARNESS_SRC/.claude/scripts/"
rsync -a --delete .claude/reference/   "$HARNESS_SRC/.claude/reference/"
# 清理历史遗留的 references/ 目录（已合并到 reference/）
rm -rf "$HARNESS_SRC/.claude/references"
cp .claude/settings.json    "$HARNESS_SRC/.claude/settings.json"
# 将开发机绝对路径替换为占位符，install.sh 安装时还原为实际项目路径
sed -i '' "s|$PROJECT_DIR|__PROJECT_ROOT__|g" "$HARNESS_SRC/.claude/settings.json"
cp .claude/harness.yaml     "$HARNESS_SRC/.claude/harness.yaml"
cp .claude/kernel.md        "$HARNESS_SRC/.claude/kernel.md"
cp .claude/index.md         "$HARNESS_SRC/.claude/index.md"
cp .claude/anti-patterns.md "$HARNESS_SRC/.claude/anti-patterns.md"
cp .claude/claude-next.md   "$HARNESS_SRC/.claude/claude-next.md"
rsync -a --delete --exclude=node_modules .cursor/  "$HARNESS_SRC/.cursor/"
rsync -a --delete --exclude=node_modules .opencode/ "$HARNESS_SRC/.opencode/"
rsync -a --delete --exclude=node_modules .hooks/     "$HARNESS_SRC/.hooks/"
# 清理运行时状态 和 lx-skills 专属内容
rm -f "$HARNESS_SRC/.omc/state/"*.json "$HARNESS_SRC/.omc/state/"*.txt 2>/dev/null || true
rm -rf "$HARNESS_SRC/.claude/nodes" "$HARNESS_SRC/.claude/profiles" \
       "$HARNESS_SRC/.claude/schemas" "$HARNESS_SRC/.claude/skills" \
       "$HARNESS_SRC/.claude/task_sys" "$HARNESS_SRC/.claude/plans" \
       "$HARNESS_SRC/.claude/state" 2>/dev/null || true
rm -f "$HARNESS_SRC/.claude/settings.local.json" \
      "$HARNESS_SRC/.claude/scheduled_tasks.lock" 2>/dev/null || true
log_info "  harness-kit 同步完成"

# ─── Step 2: root -> source/lx-skills-v5 ───
log_step "2/4 同步 root -> source/lx-skills-v5..."
for dep in lx-frontend-test lx-perf-analysis lx-style-guide; do
  [ -d "$LX_SRC/.claude/skills/$dep" ] && rm -rf "$LX_SRC/.claude/skills/$dep"
done
rsync -a --delete --exclude=.omc   .claude/nodes/    "$LX_SRC/.claude/nodes/"
rsync -a --delete                  .claude/profiles/ "$LX_SRC/.claude/profiles/"
rsync -a --delete --exclude=__pycache__ .claude/schemas/ "$LX_SRC/.claude/schemas/"
rsync -a --delete --exclude=__pycache__ --exclude='.omc/state/hud-*' \
  .claude/skills/ "$LX_SRC/.claude/skills/"
rsync -a --delete .claude/task_sys/ "$LX_SRC/.claude/task_sys/"
# 清理治理层内容 和 运行时状态
rm -rf "$LX_SRC/.claude/hooks" "$LX_SRC/.claude/scripts" \
       "$LX_SRC/.claude/reference" "$LX_SRC/.claude/plans" \
       "$LX_SRC/.claude/state" "$LX_SRC/.claude/.omc" 2>/dev/null || true
rm -f "$LX_SRC/.claude/settings.json" "$LX_SRC/.claude/harness.yaml" \
      "$LX_SRC/.claude/kernel.md" "$LX_SRC/.claude/index.md" \
      "$LX_SRC/.claude/anti-patterns.md" "$LX_SRC/.claude/claude-next.md" \
      "$LX_SRC/.claude/settings.local.json" \
      "$LX_SRC/.claude/scheduled_tasks.lock" 2>/dev/null || true
find "$LX_SRC" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find "$LX_SRC" -name '*.pyc' -delete 2>/dev/null || true
log_info "  lx-skills 同步完成"

# ─── Step 3: package harness-kit ───
log_step "3/4 构建 harness-kit..."
cd "$HARNESS_SRC"
COPYFILE_DISABLE=1 tar czf "$PKG_DIR/harness-kit-${TAG}.tar.gz" \
  --exclude=.omc --exclude=node_modules --exclude='*.pyc' \
  AGENTS.md CLAUDE.md .claude/ .cursor/ .opencode/ .hooks/
cd "$PROJECT_DIR"
H_CONTAM=$(tar tzf "$PKG_DIR/harness-kit-${TAG}.tar.gz" \
  | grep -cE '\.claude/(nodes|profiles|schemas|skills|task_sys)/' || true)
[ "$H_CONTAM" -gt 0 ] && log_warn "  ⚠️ harness-kit: $H_CONTAM 越界文件"
log_info "  harness-kit-${TAG}.tar.gz ($(du -h "$PKG_DIR/harness-kit-${TAG}.tar.gz" | cut -f1))"

# ─── Step 4: package lx-skills ───
log_step "4/4 构建 lx-skills..."
cd "$LX_SRC"
COPYFILE_DISABLE=1 tar czf "$PKG_DIR/lx-skills-${TAG}.tar.gz" \
  --exclude=.omc --exclude=__pycache__ --exclude='*.pyc' \
  .claude/
cd "$PROJECT_DIR"
L_CONTAM=$(tar tzf "$PKG_DIR/lx-skills-${TAG}.tar.gz" \
  | grep -cE '\.claude/(hooks|scripts|references)/' || true)
[ "$L_CONTAM" -gt 0 ] && log_warn "  ⚠️ lx-skills: $L_CONTAM 越界文件"
log_info "  lx-skills-${TAG}.tar.gz ($(du -h "$PKG_DIR/lx-skills-${TAG}.tar.gz" | cut -f1))"

# ─── Step 5: 同步后三源验证 (DG-100) ───
log_step "5/5 同步后三源验证..."
if [ -x "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" ]; then
    set +e
    POST_CHECK=$(bash "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" --check-source-mirror 2>&1)
    POST_EXIT=$?
    set -e
    POST_RED=$(echo "$POST_CHECK" | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
    POST_RED="${POST_RED:-0}"

    if [ "$POST_RED" -gt 0 ]; then
        log_warn "  ⚠️  同步后三源漂移: ${POST_RED} 项"
        echo "$POST_CHECK" | grep '🔴' | head -5
        log_warn "  恢复方法:"
        log_warn "    1. git diff HEAD~1 -- source/  # git历史差异"
        log_warn "    2. git diff $SAFETY_BRANCH -- source/  # 对比安全分支"
        log_warn "    3. 或从上个tar包恢复"
    else
        log_info "  ✅ 同步后三源一致性: 通过"
        git tag "safe/${VERSION}-$(date +%Y%m%d-%H%M%S)" "$SAFETY_BRANCH" 2>/dev/null && \
            log_info "  安全标签已保存" || true
        git branch -D "$SAFETY_BRANCH" 2>/dev/null || true
    fi
fi

# ─── 验证 ───
log_info "打包完成！"
H_COUNT=$(tar tzf "$PKG_DIR/harness-kit-${TAG}.tar.gz" | wc -l)
L_COUNT=$(tar tzf "$PKG_DIR/lx-skills-${TAG}.tar.gz" | wc -l)
echo "  harness-kit: ${H_COUNT} 文件, 越界: ${H_CONTAM:-0}"
echo "  lx-skills:   ${L_COUNT} 文件, 越界: ${L_CONTAM:-0}"
