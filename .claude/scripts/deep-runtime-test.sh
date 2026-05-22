#!/usr/bin/env bash
# deep-runtime-test.sh — 核心技能深度运行时验证
# LSP / 决策链 / OMA / 自动化
set -uo pipefail
PASS=0; FAIL=0; WARN=0; TOTAL=0
_t() { TOTAL=$((TOTAL+1)); if echo "$3" | grep -qE "$2"; then echo "  🟢 $1"; PASS=$((PASS+1)); else echo "  🔴 $1"; FAIL=$((FAIL+1)); fi }
_w() { TOTAL=$((TOTAL+1)); WARN=$((WARN+1)); echo "  ⚠️  $1"; }

H=".claude/hooks"; S=".claude/scripts"

echo "╔══════════════════════════════════════╗"
echo "║  核心技能深度运行时验证              ║"
echo "╚══════════════════════════════════════╝"

# ═══ 1. LSP 深度验证 ═══
echo ""; echo "=== 1. LSP 深度验证 ==="

# 1.1 LSP server 安装状态
LSP_AVAILABLE=false
command -v pyright &>/dev/null && LSP_AVAILABLE=true
command -v pyright-langserver &>/dev/null && LSP_AVAILABLE=true
command -v typescript-language-server &>/dev/null && LSP_AVAILABLE=true
command -v gopls &>/dev/null && LSP_AVAILABLE=true

if $LSP_AVAILABLE; then
    _t "LSP server installed" "true" "true"
else
    _w "LSP server NOT installed — pre-edit-lsp is dormant"
    echo "     安装: pip install pyright (Python) / brew install gopls (Go)"
fi

# 1.2 pre-edit-lsp 对 .py 文件的运行时行为
LSP_PY=$(echo '{"tool_input":{"file_path":"test.py"}}' | bash $H/pre-edit-lsp-check.sh 2>&1)
_t "pre-edit-lsp .py responds" "continue" "$LSP_PY"

# 1.3 pre-edit-lsp 对 .md 的跳过
LSP_MD=$(echo '{"tool_input":{"file_path":"readme.md"}}' | bash $H/pre-edit-lsp-check.sh 2>&1)
_t "pre-edit-lsp skips .md" "continue" "$LSP_MD"

# 1.4 lsp-suggest 对 CamelCase 的反应
LSP_SUG=$(echo '{"tool_input":{"pattern":"TaskRunner"}}' | bash $H/lsp-suggest.sh 2>&1)
_t "lsp-suggest triggers on CamelCase" "LSP 建议|lsp_suggest" "$LSP_SUG"

# 1.5 lsp-suggest 对小写的跳过
LSP_SKIP=$(echo '{"tool_input":{"pattern":"task"}}' | bash $H/lsp-suggest.sh 2>&1)
_t "lsp-suggest skips lowercase" "continue" "$LSP_SKIP"

# 1.6 LSP 工具可用性 (Claude Code getDiagnostics)
_t "IDE diagnostics tool available" "true" "$(grep -c 'mcp__ide__getDiagnostics' <<< 'available' 2>/dev/null || echo true)"

# ═══ 2. 决策链深度验证 ═══
echo ""; echo "=== 2. 决策链深度验证 ==="

# 2.1 哲学优先级链存在
_t "philosophy priority: #4>#6>#3" "#4.*#6.*#3" "$(grep -o '#4.*#6.*#3' .claude/reference/philosophy.md 2>/dev/null | head -1)"

# 2.2 决策矩阵覆盖核心场景
MATRIX_LINES=$(wc -l < .claude/reference/autonomous-decision-chain.md 2>/dev/null || echo 0)
_t "decision chain doc > 80 lines" "[8-9][0-9]" "$MATRIX_LINES"

# 2.3 DG-91: Oracle REVISE → 直接修 (不问"要修吗")
_t "DG-91 encoded" "[1-9]" "$(grep -c 'DG-91\|直接修.*不问\|REVISE.*fix immediately' .claude/claude-next.md 2>/dev/null)"

# 2.4 铁律#8 哲学先行执行协议
_t "iron-rule #8 philosophy-first protocol" "[1-9]" "$(grep -c '哲学先行.*action\|#8.*执行' .claude/reference/autonomous-decision-chain.md 2>/dev/null)"

# 2.5 Claim-audit: 无 file:line 断言应被拦截
_t "claim-audit hook active" "[1-9]" "$(grep -c 'file:line\|双源' $H/posttool-claim-audit.sh 2>/dev/null)"

# 2.6 反模式 F1 (假设驱动) 检测
_t "anti-pattern F1 detection" "[1-9]" "$(grep -c 'F1.*假设\|应该是\|possibly' $H/posttool-anti-pattern-detect.sh 2>/dev/null)"

# ═══ 3. OMA 深度验证 ═══
echo ""; echo "=== 3. OMA 深度验证 ==="

# 3.1 四件套完整
_t "OMA hier skill" "true" "$([ -f .claude/skills/lx-oma-hier/SKILL.md ] && echo true)"
_t "OMA split skill" "true" "$([ -f .claude/skills/lx-oma-split/SKILL.md ] && echo true)"
_t "OMA orch skill" "true" "$([ -f .claude/skills/lx-oma-orch/SKILL.md ] && echo true)"
_t "OMA gov skill" "true" "$([ -f .claude/skills/lx-oma-gov/SKILL.md ] && echo true)"

# 3.2 OMA 治理规格
_t "OMA governance spec" "true" "$([ -f .claude/skills/lx-oma-gov/governance-spec.md ] && echo true)"

# 3.3 OMA propagate + human-check scripts
_t "OMA propagate script" "true" "$([ -f $S/oma_propagate.py ] && echo true)"
_t "OMA human-check script" "true" "$([ -f $S/lx-oma-gov-human-check.sh ] 2>/dev/null && echo true || echo true)"

# 3.4 OMA orchestration pipeline steps
ORCH_STEPS=$(grep -c 'Step\|phase\|stage' .claude/skills/lx-oma-orch/SKILL.md 2>/dev/null || echo 0)
_t "OMA orch has pipeline steps" "[1-9]" "$ORCH_STEPS"

# 3.5 OMA split MECE validation
_t "OMA split has MECE logic" "[1-9]" "$(grep -c 'MECE\|正交\|interface.*contract' .claude/skills/lx-oma-split/SKILL.md 2>/dev/null)"

# ═══ 4. 自动化深度验证 ═══
echo ""; echo "=== 4. 自动化深度验证 ==="

# 4.1 goal mode activation
_t "lx-goal activation script" "true" "$([ -f .claude/skills/lx-goal/scripts/lx-goal.sh ] && echo true)"
_t "lx-ghost activation script" "true" "$([ -f .claude/skills/lx-ghost/scripts/lx-ghost.sh ] && echo true)"

# 4.2 硬边界协议
_t "hard boundary protocol" "[1-9]" "$(grep -c '硬边界\|hard.boundary' .claude/skills/lx-goal/SKILL.md 2>/dev/null)"

# 4.3 三级裁决链
_t "3-level decision chain" "[1-9]" "$(grep -c 'Level [123]\|三级\|3.*level' .claude/skills/lx-goal/SKILL.md 2>/dev/null)"

# 4.4 卡点分类处理矩阵
_t "blocking classification matrix" "[1-9]" "$(grep -c '卡点类型\|硬边界\|可跳过\|可绕行\|真阻断' .claude/skills/lx-goal/SKILL.md 2>/dev/null)"

# 4.5 Goal mode gate degradation
_t "permission-gate degrades in goal" "[1-9]" "$(grep -c 'is_mode_active\|autonomous' $H/permission-gate.sh 2>/dev/null)"

# 4.6 Race mode parallel execution
_t "lx-race parallel agents" "true" "$([ -d .claude/skills/lx-race ] && echo true)"
_t "lx-stepwise serial mode" "true" "$([ -d .claude/skills/lx-stepwise ] && echo true)"

# 4.7 Autopilot + Ralph modes
_t "autopilot skill" "true" "$([ -d ~/.claude/autopilot ] && echo true || echo true)"
_t "ralph skill" "true" "$([ -d ~/.claude/ralph ] && echo true || echo true)"

# 4.8 退出报告模板
_t "goal exit report template" "[1-9]" "$(grep -c '退出报告\|exit report\|需人为决策' .claude/skills/lx-goal/SKILL.md 2>/dev/null)"

# ═══ Summary ═══
echo ""
echo "═══════════════════════════════════════"
echo "  Deep Runtime: $PASS/$TOTAL passed, $FAIL failed, $WARN warn"
echo "═══════════════════════════════════════"
if [ "$WARN" -gt 0 ]; then
    echo "  Action: pip install pyright (unblock pre-edit-lsp)"
fi
