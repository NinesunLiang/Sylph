#!/usr/bin/env bash
# core-mechanism-test.sh — 核心机制运行时验证
# LSP / 决策链 / 自动化 / OMA / 脱水
set -uo pipefail
PASS=0; FAIL=0; TOTAL=0

_t() { TOTAL=$((TOTAL+1)); if echo "$3" | grep -qE "$2"; then echo "  🟢 $1"; PASS=$((PASS+1)); else echo "  🔴 $1 — $(echo "$3" | head -c 100)"; FAIL=$((FAIL+1)); fi }

H=".claude/hooks"; S=".claude/scripts"

echo "╔══════════════════════════════════════╗"
echo "║  核心机制运行时验证                   ║"
echo "╚══════════════════════════════════════╝"

# ═══ 1. 脱水 (Dehydration) ═══
echo ""; echo "=== 1. 脱水能力 ==="
_t "compact cache exists" "[1-9]" "$(wc -c < .omc/state/context-cache.md 2>/dev/null | tr -d ' ')"
_t "compact files all present" "4" "$([ -s .claude/AGENTS-compact.md ]&&[ -s .claude/anti-patterns-compact.md ]&&[ -s .claude/claude-next-compact.md ]&&[ -s .claude/kernel-compact.md ]&&echo 4)"
_t "token savings tracked" "compact" "$(cat .omc/state/token-savings.json 2>/dev/null)"

# End-to-end: touch source → regenerate → verify new timestamp
OLD_TS=$(head -1 .omc/state/context-cache.md 2>/dev/null | grep -o '2026-[0-9-]*T[0-9:]*')
touch AGENTS.md 2>/dev/null
bash $H/context-compressor.sh 2>/dev/null
NEW_TS=$(head -1 .omc/state/context-cache.md 2>/dev/null | grep -o '2026-[0-9-]*T[0-9:]*')
_t "mtime-based cache refresh" "$NEW_TS" "$([ "$NEW_TS" != "$OLD_TS" ] && echo "$NEW_TS" || echo 'same')"

# ═══ 2. LSP 能力 ═══
echo ""; echo "=== 2. LSP 能力 ==="
_t "lsp-suggest registered" "[1-9]" "$(grep -c 'lsp-suggest.sh' .claude/settings.json 2>/dev/null)"
_t "pre-edit-lsp registered" "[1-9]" "$(grep -c 'pre-edit-lsp-check.sh' .claude/settings.json 2>/dev/null)"
_t "lsp_gate enabled" "[1-9]" "$(grep -c 'lsp_gate: true' .claude/harness.yaml 2>/dev/null)"
_t "lsp_suggest enabled" "[1-9]" "$(grep -c 'lsp_suggest: true' .claude/harness.yaml 2>/dev/null)"

# Runtime: simulate grep for export symbol → lsp-suggest responds
LSP_OUT=$(echo '{"tool_input":{"pattern":"TaskRunner"}}' | bash $H/lsp-suggest.sh 2>&1)
_t "lsp-suggest runtime responds" "continue" "$LSP_OUT"

# Runtime: pre-edit-lsp for .py file
LSP2=$(echo '{"tool_input":{"file_path":"test.py"}}' | bash $H/pre-edit-lsp-check.sh 2>&1)
_t "pre-edit-lsp .py triggers" "continue" "$LSP2"

# LSP skip non-code
LSP3=$(echo '{"tool_input":{"file_path":"readme.md"}}' | bash $H/pre-edit-lsp-check.sh 2>&1)
_t "pre-edit-lsp skips .md" "continue" "$LSP3"

# ═══ 3. 决策链 ═══
echo ""; echo "=== 3. 决策链 ==="
_t "autonomous-decision-chain doc" "[1-9]" "$(wc -c < .claude/reference/autonomous-decision-chain.md 2>/dev/null | tr -d ' ')"
_t "philosophy priority chain" "#4.*#6" "$(grep -o '#4.*#6\|#4.*验证.*#6.*0信任' .claude/reference/philosophy.md 2>/dev/null | head -1)"
_t "philosophy-mechanism matrix" "[4-9][0-9][0-9]" "$(wc -l < .claude/reference/philosophy-mechanism-matrix.md 2>/dev/null | tr -d ' ')"
_t "DG-91 (Oracle REVISE→直接修)" "[1-9]" "$(grep -c 'DG-91' .claude/claude-next.md 2>/dev/null)"
_t "铁律#8 哲学先行" "[1-9]" "$(grep -c '哲学先行' .claude/reference/philosophy.md 2>/dev/null)"

# ═══ 4. 全自动化 ═══
echo ""; echo "=== 4. 全自动化 (goal/ghost) ==="
_t "lx-goal skill exists" "true" "$([ -d .claude/skills/lx-goal ] && echo true)"
_t "lx-ghost skill exists" "true" "$([ -d .claude/skills/lx-ghost ] && echo true)"
_t "lx-goal.sh activation" "[1-9]" "$(grep -c 'autonomous.active\|lx-goal.json' .claude/skills/lx-goal/scripts/lx-goal.sh 2>/dev/null)"
_t "hard boundary protocol" "[1-9]" "$(grep -c '硬边界\|hard.boundary' .claude/skills/lx-goal/SKILL.md 2>/dev/null)"
_t "autonomous decision chain loaded" "[1-9]" "$(wc -c < .claude/reference/autonomous-decision-chain.md 2>/dev/null | tr -d ' ')"
_t "goal mode gate degradation" "[1-9]" "$(grep -c 'is_mode_active\|autonomous' .claude/hooks/permission-gate.sh 2>/dev/null)"

# ═══ 5. OMA 能力 ═══
echo ""; echo "=== 5. OMA (一人成军) ==="
_t "lx-oma-hier exists" "true" "$([ -d .claude/skills/lx-oma-hier ] && echo true)"
_t "lx-oma-split exists" "true" "$([ -d .claude/skills/lx-oma-split ] && echo true)"
_t "lx-oma-orch exists" "true" "$([ -d .claude/skills/lx-oma-orch ] && echo true)"
_t "lx-oma-gov exists" "true" "$([ -d .claude/skills/lx-oma-gov ] && echo true)"
_t "oma_propagate script" "true" "$([ -f .claude/scripts/oma_propagate.py ] && echo true)"
_t "OMA governance spec" "true" "$([ -f .claude/skills/lx-oma-gov/governance-spec.md ] && echo true)"

# ═══ 6. 审查体系 ═══
echo ""; echo "=== 6. Oracle/Meta-Oracle ==="
_t "lx-oracle skill" "true" "$([ -d .claude/skills/lx-oracle ] && echo true)"
_t "meta-oracle-trigger" "true" "$([ -f $H/meta-oracle-trigger.sh ] && echo true)"
_t "meta-oracle-review" "true" "$([ -f $S/meta-oracle-review.sh ] && echo true)"
_t "G1-G4 triggers defined" "[1-9]" "$(grep -c 'G[1-4]' $H/meta-oracle-trigger.sh 2>/dev/null)"
_t "oracle verdicts tracked" "[1-9]" "$(wc -l < .omc/state/oracle-verdicts.md 2>/dev/null | tr -d ' ')"
_t "meta-oracle verdicts tracked" "[1-9]" "$(wc -l < .omc/state/meta-oracle-verdicts.md 2>/dev/null | tr -d ' ')"

# ═══ 7. 反模式+教训 ═══
echo ""; echo "=== 7. 知识体系 ==="
_t "anti-patterns ≥ 300 lines" "[3-9][0-9][0-9]" "$(wc -l < .claude/anti-patterns.md 2>/dev/null | tr -d ' ')"
_t "claude-next ≥ 40 lessons" "[4-9][0-9]" "$(grep -c 'DG-\|### \[' .claude/claude-next.md 2>/dev/null)"
_t "philosophy-matrix complete" "[4-9][0-9][0-9]" "$(wc -l < .claude/reference/philosophy-mechanism-matrix.md 2>/dev/null | tr -d ' ')"

echo ""
echo "═══════════════════════════════════════"
echo "  Core: $PASS/$TOTAL passed, $FAIL failed"
echo "═══════════════════════════════════════"
