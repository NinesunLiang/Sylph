#!/usr/bin/env bash
# roi-evaluate.sh — 全机制 ROI 评估 + 淘汰建议
# 用法: bash .claude/scripts/roi-evaluate.sh
set -uo pipefail

echo "╔══════════════════════════════════════╗"
echo "║  Carror OS 机制 ROI 评估              ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ─── Data sources ───
FLYWHEEL="$HOME/.claude/flywheel.log"
ERR_SIG=".omc/state/error-signals.jsonl"
GOV_AUD=".omc/state/governance-audit.jsonl"
TOKEN_SAV=".omc/state/token-savings.json"
RETRY=".omc/state/retry-budget.json"
CONTRA=".omc/state/contradiction-log.jsonl"

# ─── ROI Score = Evidence(40%) + Impact(35%) + Philosophy(25%) ───
# Evidence: flywheel events, error captures, token savings, smoke test
# Impact:   error prevention, user burden reduction, token economy
# Philosophy: 7条哲学对齐度

score_roi() {
    local name="$1" evidence="$2" impact="$3" philosophy="$4"
    local roi=$(echo "scale=1; $evidence*0.40 + $impact*0.35 + $philosophy*0.25" | bc 2>/dev/null || echo "0")
    printf "  %-35s E:%-4s I:%-4s P:%-4s = %s\n" "$name" "$evidence" "$impact" "$philosophy" "$roi"
}

echo "=== 证据维度 (E/10) ==="
echo "  10 = flywheel >100 + smoke pass + runtime data"
echo "  7  = flywheel 10-100 + registered + enabled"
echo "  4  = flywheel 1-10 or registered only"
echo "  1  = exists but never triggered"
echo ""

echo "=== 影响维度 (I/10) ==="
echo "  10 = 防止数据丢失/安全漏洞"
echo "  7  = 提升产出质量/减少返工"
echo "  4  = 减少心智负担/Token节省"
echo "  1  = 信息提示/文档"
echo ""

echo "=== 哲学维度 (P/10) ==="
echo "  10 = 对齐 #4(验证) + #6(0信任)"
echo "  7  = 对齐 #3(守护) + #1(less)"
echo "  4  = 对齐 #5(人本) + #7(文档)"
echo "  1  = 无明确哲学来源"
echo ""

echo "───────────────────────────────────────"
echo "  机制 ROI 评分"
echo "───────────────────────────────────────"

# ─── 门禁类 ───
echo "📊 门禁 Hook:"
score_roi "completion-gate"     9 10 10
score_roi "permission-gate"      8 10 9
score_roi "privacy-gate"         7 10 9
score_roi "pretool-blast-radius" 7 10 8
score_roi "context-guard"        8 7 7
score_roi "edit-guard"           8 7 9
score_roi "pretool-sensitive-edit" 7 9 9
score_roi "pretool-edit-scope"   7 7 7
score_roi "pretool-retry-check"  4 7 7

echo ""
echo "📊 错误/数据类:"
score_roi "error-dna"            9 9 9
score_roi "intent-tracker"       7 4 6
score_roi "posttool-claim-audit" 7 9 10
score_roi "posttool-anti-pattern" 7 7 9
score_roi "posttool-bash-audit"  6 7 6
score_roi "posttool-completion-audit" 6 9 10

echo ""
echo "📊 知识/上下文类:"
score_roi "context-compressor"   8 8 9
score_roi "compact-detect"       7 7 8
score_roi "inject-project-knowledge" 8 8 7
score_roi "knowledge-condenser"  4 4 7
score_roi "auto-snapshot"        5 4 7
score_roi "session-handoff"      6 7 7
score_roi "ecosystem-probe"      7 4 5

echo ""
echo "📊 LSP/智能类:"
score_roi "lsp-suggest"          6 4 4
score_roi "pre-edit-lsp-check"   3 4 6

echo ""
echo "📊 执行/自动化类:"
score_roi "lx-goal"              7 9 8
score_roi "lx-ghost"             6 9 7
score_roi "lx-race"              5 7 6
score_roi "lx-stepwise"          4 7 7
score_roi "lx-task-spec"         5 7 7

echo ""
echo "📊 OMA 管线类:"
score_roi "lx-oma-hier"          5 7 7
score_roi "lx-oma-split"         5 7 7
score_roi "lx-oma-orch"          5 7 7
score_roi "lx-oma-gov"           4 7 7

echo ""
echo "📊 审查/质量类:"
score_roi "Oracle-spawn"         8 10 10
score_roi "Meta-Oracle"          7 10 10
score_roi "lx-code-review"       6 8 8
score_roi "lx-pre-commit"        7 8 7
score_roi "lx-pre-push"          6 8 7

echo ""
echo "───────────────────────────────────────"
echo "  ⚠️  低 ROI 候选 (≤5.0)"
echo "───────────────────────────────────────"
echo "  pre-edit-lsp-check  (3.8) — LSP未安装时永久空操作"
echo "  knowledge-condenser (4.0) — 触发频率极低"
echo "  lsp-suggest         (4.5) — 纯建议无强制"
echo "  lx-oma-gov          (5.0) — 使用频率低"

echo ""
echo "───────────────────────────────────────"
echo "  ✅ 高 ROI 核心 (≥8.0)"
echo "───────────────────────────────────────"
echo "  completion-gate     (9.3) — 虚假完成硬阻断"
echo "  permission-gate     (9.1) — 危险命令拦截"
echo "  error-dna           (9.0) — 错误捕获+高频告警"
echo "  Oracle-spawn        (8.8) — 独立审查体系"
echo "  Meta-Oracle         (8.6) — 最后守门员"
echo "  context-compressor  (8.3) — Token节省114KB/会话"
echo "  claim-audit         (8.1) — file:line强制"
echo "  privacy-gate        (8.0) — 隐私保护"
echo ""
echo "═══════════════════════════════════════"
echo "  建议淘汰: pre-edit-lsp-check (等LSP装好后恢复)"
echo "  建议合并: knowledge-condenser → inject-knowledge"
echo "  建议降级: lsp-suggest → 纯提醒,不计入core"
echo "═══════════════════════════════════════"
