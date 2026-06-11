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

VERSION=$(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('VERSION.json'))['version'])")
TAG="v${VERSION}"
log_info "版本：$TAG"
PKG_DIR="$PROJECT_DIR/packages"
HARNESS_SRC="source/harness-kit"
LX_SRC="source/lx-skills-v5"

# ─── G4 Meta-Oracle Release 门禁（打包前最后守门）───
log_step "G4 Meta-Oracle Release 门禁检查..."
META_ORACLE_SCRIPT="$PROJECT_DIR/.claude/scripts/meta-oracle-review.py"
META_ORACLE_OVERRIDE="$PROJECT_DIR/.omc/state/meta-oracle-overrides.md"
META_ORACLE_G4_CHECK="$PROJECT_DIR/.claude/scripts/g4-precheck.py"

# 用 Python 执行 G4 预检（避免 set -eo pipefail + bash 的陷阱）
if [ -f "$META_ORACLE_G4_CHECK" ]; then
    log_info "G4 预检脚本: $META_ORACLE_G4_CHECK"
    G4_PRECHECK_OUTPUT=$(python3 "$META_ORACLE_G4_CHECK" 2>&1) || true
    G4_PRECHECK_EXIT=$?
    echo "$G4_PRECHECK_OUTPUT"

    # 从输出中提取检查结果文件路径
    EVIDENCE_FILE=$(echo "$G4_PRECHECK_OUTPUT" | grep -o '/tmp/g4-evidence-[^ ]*\.txt' | tail -1)

    # 提取裁决
    MO_VERDICT=$(echo "$G4_PRECHECK_OUTPUT" | grep -E '\[Meta-Oracle: (ACCEPT|ADVISORY|REJECT)\]' | tail -1)
    echo ""

    if echo "$MO_VERDICT" | grep -q 'REJECT'; then
        if [ -f "$META_ORACLE_OVERRIDE" ] && grep -q "v${VERSION}" "$META_ORACLE_OVERRIDE" 2>/dev/null; then
            log_warn "G4 Meta-Oracle: ⚠️  ${MO_VERDICT} — 已人工覆写 ($META_ORACLE_OVERRIDE)，继续打包"
        else
            log_warn "🔴 G4 Meta-Oracle: ${MO_VERDICT} — 硬门禁阻断打包！"
            log_warn "  修复问题后重试，或创建覆写文件 $META_ORACLE_OVERRIDE 记录理由"
            rm -f "$EVIDENCE_FILE" 2>/dev/null || true
            exit 1
        fi
    elif echo "$MO_VERDICT" | grep -q 'ADVISORY'; then
        log_warn "G4 Meta-Oracle: ⚠️  ${MO_VERDICT} — 建议修正但不阻断"
    else
        log_info "G4 Meta-Oracle: ✅ ${MO_VERDICT}"
    fi
    rm -f "$EVIDENCE_FILE" 2>/dev/null || true

elif [ -f "$META_ORACLE_SCRIPT" ]; then
    # Fallback: 直接调用老版（无预检注入，可能假阳性）
    log_warn "g4-precheck.py 不存在，降级到直接调用 meta-oracle-review.py（不推荐）"
    python3 "$META_ORACLE_SCRIPT" G4 2>&1
    echo ""
    log_warn "G4 Meta-Oracle: ⚠️  无预检注入，降级模式 — 继续打包"
else
    log_warn "Meta-Oracle 审查脚本不存在，跳过 G4 门禁"
fi
echo ""

# ═══ DG-100 三源安全门禁 (2026-05-22) ═══
# DG-118 修复 (2026-05-31): 三源预检从 Step 0 移至 Step 1 之后
# 原因: Step 0 时 root 已修改但 source/ 尚未 rsync → 假阳性漂移阻断
# Step 1 rsync 后 root→source 已同步 → 预检通过 → 仅 Step 5 兜底
log_step "0/4 三源安全门禁 (预检延迟至 Step 1.5)..."

SAFETY_BRANCH="_safe/package-${VERSION}-$(date +%Y%m%d-%H%M%S)"

# DG-100 M5: trap EXIT 自动清理安全分支（防无限积累）
trap 'git branch -D "$SAFETY_BRANCH" 2>/dev/null || true' EXIT

# 0.1 安全分支（全量快照）
if git rev-parse --git-dir >/dev/null 2>&1; then
    git branch "$SAFETY_BRANCH" 2>/dev/null && \
        log_info "  安全分支: $SAFETY_BRANCH" || \
        log_warn "  安全分支创建失败（继续）"
fi

# 0.2 关键文件存在性+非空验证 — 放宽检查：仅检查真正必要的文件
REQUIRED_FILES=".claude/harness.yaml"
# .sh 已迁移到 .py，不再强制检查 .sh 存在性
# .py 文件可选存在（已迁移）
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
# NOTE: AGENTS.md 根目录是通用分发模板（79行，仅哲学铁律+路由索引）
# source/harness-kit/AGENTS.md 可能是旧版元项目专属内容，必须覆盖
log_step "1/4 同步 root -> source/harness-kit..."
cp AGENTS.md    "$HARNESS_SRC/AGENTS.md"
cp CLAUDE.md    "$HARNESS_SRC/CLAUDE.md"
rsync -a --delete .claude/hooks/       "$HARNESS_SRC/.claude/hooks/"
rsync -a --delete .claude/scripts/     "$HARNESS_SRC/.claude/scripts/" --exclude='*.sh' --include='*.py' --include='*/'
rsync -a --delete .claude/reference/   "$HARNESS_SRC/.claude/reference/"
rsync -a --delete .claude/docs/        "$HARNESS_SRC/.claude/docs/"
rsync -a --delete .claude/workflow-standard/ "$HARNESS_SRC/.claude/workflow-standard/"
# 清理历史遗留的 references/ 目录（已合并到 reference/）
rm -rf "$HARNESS_SRC/.claude/references"
cp .claude/settings.json    "$HARNESS_SRC/.claude/settings.json"
# settings.json 全部使用相对路径，无需做任何路径替换
# 历史逻辑（__PROJECT_ROOT__ 占位符 → install.sh 还原）已废弃
cp .claude/harness.yaml     "$HARNESS_SRC/.claude/harness.yaml"
# kernel.md 不打包 — 用户在 Agent 上下文中已有（AGENTS.md @kernel.md），同时避免每次重复安装叠加副本
# cp .claude/kernel.md        "$HARNESS_SRC/.claude/kernel.md"
cp .claude/index.md         "$HARNESS_SRC/.claude/index.md"
cp .claude/anti-patterns.md "$HARNESS_SRC/.claude/anti-patterns.md"
cp .claude/claude-next.md   "$HARNESS_SRC/.claude/claude-next.md"
rsync -a --delete --exclude=node_modules .cursor/  "$HARNESS_SRC/.cursor/"
rsync -a --delete --exclude=node_modules .opencode/ "$HARNESS_SRC/.opencode/"
rsync -a --delete --exclude=node_modules .hooks/     "$HARNESS_SRC/.hooks/"
# 清理运行时状态、元项目专属内容、备份文件、缓存
rm -rf "$HARNESS_SRC/.omc" 2>/dev/null || true
rm -rf "$HARNESS_SRC/.claude/nodes" "$HARNESS_SRC/.claude/profiles" \
       "$HARNESS_SRC/.claude/schemas" "$HARNESS_SRC/.claude/skills" \
       "$HARNESS_SRC/.claude/task_sys" "$HARNESS_SRC/.claude/plans" \
       "$HARNESS_SRC/.claude/state" 2>/dev/null || true
rm -f "$HARNESS_SRC/.claude/settings.local.json" \
      "$HARNESS_SRC/.claude/scheduled_tasks.lock" 2>/dev/null || true
# 清理备份文件和缓存
find "$HARNESS_SRC" -name '*.bak*' -delete 2>/dev/null || true
find "$HARNESS_SRC" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$HARNESS_SRC" -name '*.pyc' -delete 2>/dev/null || true
# 清理 kernel.md — 已在开发源 AGENTS.md @kernel.md 注入，不打包进 harness-kit 避免重复
rm -f "$HARNESS_SRC/.claude/kernel.md" 2>/dev/null || true
# 清理测试/诊断脚本（含硬编码开发机路径）
rm -f "$HARNESS_SRC/.claude/scripts/task-verify-e1e2-fix.py" 2>/dev/null || true
# 替换 claude-next.md 中的 @lucas.liang 为通用署名
if [ -f "$HARNESS_SRC/.claude/claude-next.md" ]; then
    if sed --version 2>/dev/null | grep -q GNU; then
        sed -i 's/(@lucas\.liang)/(@dev)/g' "$HARNESS_SRC/.claude/claude-next.md" 2>/dev/null || true
    else
        sed -i '' 's/(@lucas\.liang)/(@dev)/g' "$HARNESS_SRC/.claude/claude-next.md" 2>/dev/null || true
    fi
fi
log_info "  harness-kit 同步完成"

# ─── Step 1.5: 三源一致性预检 (DG-118: 移至 rsync 之后，消除假阳性) ───
if [ -x "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" ]; then
    log_info "  三源一致性预检 (rsync 后)..."
    set +e
    MIRROR_CHECK=$(bash "$PROJECT_DIR/.claude/scripts/audit-hooks.sh" --check-source-mirror 2>&1)
    MIRROR_EXIT=$?
    set -e
    RED_COUNT=$(echo "$MIRROR_CHECK" | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
    RED_COUNT="${RED_COUNT:-0}"

    FORCE_MODE=false
    for arg in "$@"; do [ "$arg" = "--force" ] && FORCE_MODE=true; done

    if [ "$MIRROR_EXIT" -ne 0 ] && [ "$RED_COUNT" -eq 0 ]; then
        log_warn "  🔴 三源验证脚本异常退出 (exit=$MIRROR_EXIT)，可能为假阴性"
        echo "$MIRROR_CHECK" | tail -5
        [ "$FORCE_MODE" != "true" ] && { log_warn "  打包已阻断。--force 可跳过。"; exit 1; }
    fi

    if [ "$RED_COUNT" -gt 0 ]; then
        log_warn "  ⚠️  三源一致性: ${RED_COUNT} 项 CRITICAL 漂移 (rsync 后仍存在)"
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
  --exclude=.omc --exclude=node_modules --exclude='*.pyc' --exclude='__pycache__' --exclude='*.bak*' \
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

# ─── sha256 完整性校验（防打包退化，DG-105）───
log_step "sha256 完整性校验..."
verify_package() {
    local src_dir="$1" tar_file="$2"
    local fail=0
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        [[ "$f" == */ ]] && continue
        local tar_sha src_sha
        tar_sha=$(tar -xzf "$tar_file" -O "$f" 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
        src_sha=$(shasum -a 256 "$src_dir/$f" 2>/dev/null | cut -d' ' -f1)
        if [ "$tar_sha" != "$src_sha" ] || [ -z "$tar_sha" ]; then
            log_warn "  ⚠️  $f: tar=$tar_sha vs src=$src_sha"
            fail=1
        fi
    done < <(tar -tzf "$tar_file" 2>/dev/null)
    return $fail
}

PKG_FAIL=0
verify_package "source/harness-kit" "packages/harness-kit-${TAG}.tar.gz" || PKG_FAIL=1
verify_package "source/lx-skills-v5" "packages/lx-skills-${TAG}.tar.gz" || PKG_FAIL=1

if [ "$PKG_FAIL" -eq 1 ]; then
    log_warn "sha256 校验失败！打包内容与源文件不一致。"
    log_warn "建议重新执行 rsync 同步后重试。"
    exit 1
fi
log_info "✅ sha256 全部一致"

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
log_info "✅ 打包完成，文件统一使用 ${TAG} 命名"
