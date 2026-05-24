#!/usr/bin/env bash
# score-self-check.sh — P3 长期评测框架：C1-C9 + E1-E8 自动评分
# Role: Carror OS 四维评分体系自动基线生成与差异比较
# 哲学 #4: 没通过验证等于没做 — 每个得分必须有 file:line 证据
# 哲学 #6: 先天对 AI 0 信任 — 评分来自实际配置检查，非 AI 估算
#
# 用法：
#   bash .claude/scripts/score-self-check.sh          # 输出 JSON 报告
#   bash .claude/scripts/score-self-check.sh --init    # 保存基线
#   bash .claude/scripts/score-self-check.sh --diff <baseline>  # 差异比较
#
# 输出：JSON 到 stdout, 摘要到 stderr

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null || true

# ─── 参数解析 ───
INIT=false
DIFF_FILE=""
for arg in "$@"; do
    case "$arg" in
        --init) INIT=true ;;
        --diff) shift; DIFF_FILE="${1:-}"; break ;;
    esac
done

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S+00:00")

# ─── 辅助函数 ───

# 检查文件存在
file_exists() {
    [ -f "$1" ]
}

# 计算数组数量
count_files() {
    local pattern="$1"
    local count=0
    for f in $pattern; do
        [ -f "$f" ] && count=$((count + 1))
    done
    echo "$count"
}

# grep 计数
grep_count() {
    local pattern="$1" file="$2"
    if [ -f "$file" ]; then
        n=$(grep -c "$pattern" "$file" 2>/dev/null); n="${n:-0}"; printf "%d" "$n"
    else
        echo 0
    fi
}

grep_match() {
    local pattern="$1" file="$2"
    if [ -f "$file" ]; then
        grep -q "$pattern" "$file" 2>/dev/null && echo "true" || echo "false"
    else
        echo "false"
    fi
}

# claude-next.md 行数
file_line_count() {
    local file="$1"
    if [ -f "$file" ]; then
        wc -l < "$file" 2>/dev/null | tr -d ' '
    else
        echo 0
    fi
}

# 四舍五入到两位小数
round2() {
    ${PYTHON_BIN:-python3} -c "print(round($1, 2))" 2>/dev/null || echo "$1"
}

# ──────────────────────────────────────────────
# C 维度检查
# ──────────────────────────────────────────────

echo "--- Carror OS 自评分报告 ---" >&2
echo "时间戳: $TIMESTAMP" >&2
echo "" >&2

# ── C1: 指令清晰度 ──
# 检查: .claude/hooks/*.sh 中带 Role 注释的脚本比例
HOOK_DIR="$PROJECT_ROOT/.claude/hooks"
HOOK_TOTAL=$(count_files "$HOOK_DIR/*.sh")
HOOK_WITH_ROLE=0
if [ "$HOOK_TOTAL" -gt 0 ]; then
    for f in "$HOOK_DIR"/*.sh; do
        [ -f "$f" ] && head -5 "$f" 2>/dev/null | grep -q '^# Role:' && HOOK_WITH_ROLE=$((HOOK_WITH_ROLE + 1))
    done
fi

if [ "$HOOK_TOTAL" -gt 0 ]; then
    C1_SCORE=$(round2 "$(echo "scale=4; $HOOK_WITH_ROLE / $HOOK_TOTAL" | bc 2>/dev/null || echo 0)")
else
    C1_SCORE="0"
fi
C1_SOURCE=".claude/hooks/*.sh Role comment coverage ($HOOK_WITH_ROLE/$HOOK_TOTAL = $C1_SCORE)"
echo "  C1: $C1_SCORE ($C1_SOURCE)" >&2

# ── C2: 上下文完整度 ──
# 检查 index.md 是否存在 + 内容覆盖
INDEX_FILE="$PROJECT_ROOT/.claude/index.md"
C2_FEATURES=0
C2_TOTAL=3
if [ -f "$INDEX_FILE" ]; then
    # 检查铁律速查
    grep -q '铁律速查\|铁律' "$INDEX_FILE" 2>/dev/null && C2_FEATURES=$((C2_FEATURES + 1))
    # 检查 hooks reference pointer
    grep -q 'hooks.*reference\|Hooks.*速查\|hooks-table' "$INDEX_FILE" 2>/dev/null && C2_FEATURES=$((C2_FEATURES + 1))
    # 检查 anti-patterns/kernel reference
    grep -q 'anti-patterns\|kernel\.md\|kernel' "$INDEX_FILE" 2>/dev/null && C2_FEATURES=$((C2_FEATURES + 1))
fi
C2_SCORE=$(round2 "$(echo "scale=4; $C2_FEATURES / $C2_TOTAL" | bc 2>/dev/null || echo 0)")
C2_SOURCE=".claude/index.md feature coverage ($C2_FEATURES/$C2_TOTAL = $C2_SCORE)"
echo "  C2: $C2_SCORE (index.md: $C2_FEATURES/$C2_TOTAL features)" >&2

# ── C3: 流程结构化 ──
# 检查: completion-gate.sh L3 complexity gate + Oracle block + smoke-test E2E-6
C3_FEATURES=0
C3_TOTAL=3
COMPLETION_GATE="$HOOK_DIR/completion-gate.sh"

# L3 complexity gate
if grep -qE 'L[34]|Oracle 终审|三重门' "$COMPLETION_GATE" 2>/dev/null; then
    C3_FEATURES=$((C3_FEATURES + 1))
fi

# Oracle block support in evidence format
if grep -qE 'Oracle Q1|交叉验证|handoff.*cross-verify|cross-verify-handoff' "$COMPLETION_GATE" 2>/dev/null; then
    C3_FEATURES=$((C3_FEATURES + 1))
fi

# harness-smoke-test has E2E-6 or completeness test case
SMOKE_TEST="$PROJECT_ROOT/.claude/scripts/harness-smoke-test.sh"
if [ -f "$SMOKE_TEST" ]; then
    # Check if it has a test case that validates gate functionality
    if grep -qE 'E2E-6|completion.*gate|evidence.*block|Oracle.*终审' "$SMOKE_TEST" 2>/dev/null; then
        C3_FEATURES=$((C3_FEATURES + 1))
    fi
fi

C3_SCORE=$(round2 "$(echo "scale=4; $C3_FEATURES / $C3_TOTAL" | bc 2>/dev/null || echo 0)")
C3_SOURCE="completion-gate.sh L3 gate + Oracle block + smoke-test completeness ($C3_FEATURES/$C3_TOTAL = $C3_SCORE)"
echo "  C3: $C3_SCORE ($C3_FEATURES/$C3_TOTAL features)" >&2

# ── C4: 输出规范化 ──
# 检查: posttool-format-gate.sh 注册 + matcher
SETTINGS_JSON="$PROJECT_ROOT/.claude/settings.json"
C4_SCORE="0"
C4_SOURCE="未注册"
if grep -q 'format-gate' "$SETTINGS_JSON" 2>/dev/null; then
    # Check matcher (appears BEFORE the hook command in JSON, so use -B5)
    # Use grep -F (fixed string) to avoid regex escaping issues with .*
    if grep -B5 'format-gate' "$SETTINGS_JSON" 2>/dev/null | grep -Fq '"matcher": ".*"'; then
        C4_SCORE="1.0"
        C4_SOURCE="posttool-format-gate.sh registered with matcher=.* (1.0)"
    else
        C4_SCORE="0.5"
        C4_SOURCE="posttool-format-gate.sh registered but matcher != .* (0.5)"
    fi
fi
echo "  C4: $C4_SCORE ($C4_SOURCE)" >&2

# ── C5: 工具生命周期 ──
# 检查: settings.json 中注册的事件类型数（最大 6 种）
C5_EVENTS=0
C5_TOTAL=6
for event in PreToolUse PostToolUse PostToolUseFailure Stop UserPromptSubmit SessionStart; do
    grep -q "\"$event\"" "$SETTINGS_JSON" 2>/dev/null && C5_EVENTS=$((C5_EVENTS + 1))
done
C5_SCORE=$(round2 "$(echo "scale=4; $C5_EVENTS / $C5_TOTAL" | bc 2>/dev/null || echo 0)")
C5_SOURCE="settings.json event type coverage ($C5_EVENTS/$C5_TOTAL = $C5_SCORE)"
echo "  C5: $C5_SCORE ($C5_EVENTS/$C5_TOTAL events)" >&2

# ── C6: 知识密度 ──
# 检查: claude-next.md 行数 + R-prefix lessons + 记忆系统文件
CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
NEXT_LINES=$(file_line_count "$CLAUDE_NEXT")
# 行数评分
if [ "$NEXT_LINES" -gt 200 ]; then
    C6_LINE_SCORE=1.0
elif [ "$NEXT_LINES" -gt 100 ]; then
    C6_LINE_SCORE=0.7
else
    C6_LINE_SCORE=0.4
fi

# R-prefix lessons
R_COUNT=$(grep_count '\[R' "$CLAUDE_NEXT")
R_SCORE=$(echo "scale=4; $R_COUNT / 20.0" | bc 2>/dev/null || echo 0)
[ "$(echo "$R_SCORE > 1.0" | bc 2>/dev/null)" = "1" ] && R_SCORE=1.0

# Memory system files
MEMORY_FILES=0
MEMORY_TOTAL=4
for mf in ".omc/state/error-dna.json" ".omc/state/session-handoff.md" ".omc/state/session-snapshot.json" ".omc/state/todo-queue.md"; do
    [ -f "$PROJECT_ROOT/$mf" ] && MEMORY_FILES=$((MEMORY_FILES + 1))
done
MEM_SCORE=$(echo "scale=4; $MEMORY_FILES / $MEMORY_TOTAL" | bc 2>/dev/null || echo 0)

# Composite C6: 50% line count + 30% R-lessons + 20% memory
C6_SCORE=$(round2 "$(echo "scale=4; $C6_LINE_SCORE * 0.5 + $R_SCORE * 0.3 + $MEM_SCORE * 0.2" | bc 2>/dev/null || echo 0)")
C6_SOURCE="claude-next.md ${NEXT_LINES}行 R×${R_COUNT} mem=${MEMORY_FILES}/${MEMORY_TOTAL} → ${C6_SCORE}"
echo "  C6: $C6_SCORE ($C6_SOURCE)" >&2

# ── C7: 关联编排 ──
# 检查: OMA skill 目录数 / 4
SKILL_DIR="$PROJECT_ROOT/.claude/skills"
C7_COUNT=0
C7_TOTAL=4
for skill in lx-oma-hier lx-oma-split lx-oma-gov lx-oma-orch; do
    [ -d "$SKILL_DIR/$skill" ] && C7_COUNT=$((C7_COUNT + 1))
done
C7_SCORE=$(round2 "$(echo "scale=4; $C7_COUNT / $C7_TOTAL" | bc 2>/dev/null || echo 0)")
C7_SOURCE="OMA skill directories ($C7_COUNT/$C7_TOTAL = $C7_SCORE)"
echo "  C7: $C7_SCORE ($C7_COUNT/$C7_TOTAL OMA skills)" >&2

# ── C8: 可维护性 ──
# 检查: audit-hooks.sh + harness-smoke-test.sh + hook-production-verify.sh
C8_COUNT=0
C8_TOTAL=3
[ -f "$PROJECT_ROOT/.claude/scripts/audit-hooks.sh" ] && C8_COUNT=$((C8_COUNT + 1))
[ -f "$SMOKE_TEST" ] && C8_COUNT=$((C8_COUNT + 1))
[ -f "$PROJECT_ROOT/.claude/scripts/hook-production-verify.sh" ] && C8_COUNT=$((C8_COUNT + 1))
C8_SCORE=$(round2 "$(echo "scale=4; $C8_COUNT / $C8_TOTAL" | bc 2>/dev/null || echo 0)")
C8_SOURCE="维护脚本存在性 ($C8_COUNT/$C8_TOTAL = $C8_SCORE)"
echo "  C8: $C8_SCORE ($C8_SOURCE)" >&2

# ── C9: 错误恢复 ──
# 检查: error-dna.sh + escape-patch-apply.sh + error-dna.jsonl
C9_COUNT=0
C9_TOTAL=3
[ -f "$HOOK_DIR/error-dna.sh" ] && C9_COUNT=$((C9_COUNT + 1))
[ -f "$SCRIPT_DIR/escape-patch-apply.sh" ] && C9_COUNT=$((C9_COUNT + 1))
# Check error-dna.jsonl has entries
DNA_JSONL="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
if [ -f "$DNA_JSONL" ]; then
    DNA_ENTRIES=$(wc -l < "$DNA_JSONL" 2>/dev/null | tr -d ' ')
    [ "$DNA_ENTRIES" -gt 0 ] 2>/dev/null && C9_COUNT=$((C9_COUNT + 1))
fi
C9_SCORE=$(round2 "$(echo "scale=4; $C9_COUNT / $C9_TOTAL" | bc 2>/dev/null || echo 0)")
C9_SOURCE="error-dna infrastructure ($C9_COUNT/$C9_TOTAL = $C9_SCORE)"
echo "  C9: $C9_SCORE ($C9_SOURCE)" >&2

# ──────────────────────────────────────────────
# E 维度检查（学习维度）
# ──────────────────────────────────────────────

# ── E1: 目标漂移 ──
# 检查: pretool-edit-scope.sh + scope drift lessons
E1_FEATURES=0
E1_TOTAL=3
PRETOOL_SCOPE="$HOOK_DIR/pretool-edit-scope.sh"
if [ -f "$PRETOOL_SCOPE" ] && grep -q 'SCOPE_FILE\|scope.*freeze\|编辑范围' "$PRETOOL_SCOPE" 2>/dev/null; then
    E1_FEATURES=$((E1_FEATURES + 1))
fi
if [ -f "$CLAUDE_NEXT" ] && grep -qE 'R28|R37|scope.*drift|目标漂移|漂移' "$CLAUDE_NEXT" 2>/dev/null; then
    E1_FEATURES=$((E1_FEATURES + 1))
fi
if [ -f "$HOOK_DIR/turn-counter.sh" ] && grep -q '漂移\|drift\|范围扩展\|scope.*extend' "$HOOK_DIR/turn-counter.sh" 2>/dev/null; then
    E1_FEATURES=$((E1_FEATURES + 1))
fi
E1_SCORE=$(round2 "$(echo "scale=4; $E1_FEATURES / $E1_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E1: $E1_SCORE (scope drift defense: $E1_FEATURES/$E1_TOTAL)" >&2

# ── E2: 幻觉输出 ──
E2_FEATURES=0
E2_TOTAL=3
if [ -f "$HOOK_DIR/posttool-claim-audit.sh" ]; then
    E2_FEATURES=$((E2_FEATURES + 1))
fi
if [ -f "$SETTINGS_JSON" ] && grep -q 'claim-audit' "$SETTINGS_JSON" 2>/dev/null; then
    E2_FEATURES=$((E2_FEATURES + 1))
fi
if [ -f "$CLAUDE_NEXT" ] && grep -qE '幻觉|hallucinat|编造|claim.*audit|虚假断言' "$CLAUDE_NEXT" 2>/dev/null; then
    E2_FEATURES=$((E2_FEATURES + 1))
fi
E2_SCORE=$(round2 "$(echo "scale=4; $E2_FEATURES / $E2_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E2: $E2_SCORE (hallucination defense: $E2_FEATURES/$E2_TOTAL)" >&2

# ── E3: 虚假完成 ──
E3_FEATURES=0
E3_TOTAL=2
if [ -f "$COMPLETION_GATE" ] && grep -qE 'evidence|BLOCKED|证据' "$COMPLETION_GATE" 2>/dev/null; then
    E3_FEATURES=$((E3_FEATURES + 1))
fi
ANTI_PATTERNS="$PROJECT_ROOT/.claude/anti-patterns.md"
if [ -f "$ANTI_PATTERNS" ] && grep -qE 'A2|虚假完成|false.*completion' "$ANTI_PATTERNS" 2>/dev/null; then
    E3_FEATURES=$((E3_FEATURES + 1))
fi
E3_SCORE=$(round2 "$(echo "scale=4; $E3_FEATURES / $E3_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E3: $E3_SCORE (false completion defense: $E3_FEATURES/$E3_TOTAL)" >&2

# ── E4: 惯性执行 ──
E4_FEATURES=0
E4_TOTAL=3
if [ -f "$HOOK_DIR/fuzzy-block.sh" ]; then
    E4_FEATURES=$((E4_FEATURES + 1))
fi
if [ -f "$HOOK_DIR/turn-counter.sh" ] && grep -q '模糊\|fuzzy\|fuzzy_verb' "$HOOK_DIR/turn-counter.sh" 2>/dev/null; then
    E4_FEATURES=$((E4_FEATURES + 1))
fi
if [ -f "$CLAUDE_NEXT" ] && grep -q 'R37\|ghost.*mode.*豁免\|ghost.*exempt' "$CLAUDE_NEXT" 2>/dev/null; then
    E4_FEATURES=$((E4_FEATURES + 1))
fi
E4_SCORE=$(round2 "$(echo "scale=4; $E4_FEATURES / $E4_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E4: $E4_SCORE (inertial execution defense: $E4_FEATURES/$E4_TOTAL)" >&2

# ── E5: 症状混淆 ──
E5_FEATURES=0
E5_TOTAL=2
if [ -f "$HOOK_DIR/error-dna.sh" ] && grep -q 'NOISE_PATTERNS' "$HOOK_DIR/error-dna.sh" 2>/dev/null; then
    E5_FEATURES=$((E5_FEATURES + 1))
fi
if [ -f "$DNA_JSONL" ]; then
    DNA_ENTRIES=$(wc -l < "$DNA_JSONL" 2>/dev/null | tr -d ' ')
    [ "$DNA_ENTRIES" -gt 10 ] 2>/dev/null && E5_FEATURES=$((E5_FEATURES + 1))
fi
E5_SCORE=$(round2 "$(echo "scale=4; $E5_FEATURES / $E5_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E5: $E5_SCORE (symptom confusion defense: $E5_FEATURES/$E5_TOTAL)" >&2

# ── E6: 自我矛盾 ──
E6_FEATURES=0
E6_TOTAL=3
if [ -f "$CLAUDE_NEXT" ] && grep -q 'R42' "$CLAUDE_NEXT" 2>/dev/null; then
    E6_FEATURES=$((E6_FEATURES + 1))
fi
if [ -f "$CLAUDE_NEXT" ] && grep -q 'R43' "$CLAUDE_NEXT" 2>/dev/null; then
    E6_FEATURES=$((E6_FEATURES + 1))
fi
# pre-commit-self-review not found, check for alternative
if [ -f "$HOOK_DIR/posttool-anti-pattern-detect.sh" ] || [ -f "$HOOK_DIR/posttool-completion-audit.sh" ]; then
    E6_FEATURES=$((E6_FEATURES + 1))
fi
E6_SCORE=$(round2 "$(echo "scale=4; $E6_FEATURES / $E6_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E6: $E6_SCORE (self-contradiction defense: $E6_FEATURES/$E6_TOTAL)" >&2

# ── E7: 过度自信 ──
E7_FEATURES=0
E7_TOTAL=3
if [ -f "$COMPLETION_GATE" ] && grep -q 'SOFT_WORDS\|soft_completion\|软完成语' "$COMPLETION_GATE" 2>/dev/null; then
    E7_FEATURES=$((E7_FEATURES + 1))
fi
if [ -f "$ANTI_PATTERNS" ] && grep -qE 'A2|F1|假设驱动|assumption.driven' "$ANTI_PATTERNS" 2>/dev/null; then
    E7_FEATURES=$((E7_FEATURES + 1))
fi
if [ -f "$COMPLETION_GATE" ] && grep -q 'quality_threshold\|质量评分\|evidence.*score' "$COMPLETION_GATE" 2>/dev/null; then
    E7_FEATURES=$((E7_FEATURES + 1))
fi
E7_SCORE=$(round2 "$(echo "scale=4; $E7_FEATURES / $E7_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E7: $E7_SCORE (overconfidence defense: $E7_FEATURES/$E7_TOTAL)" >&2

# ── E8: 上下文遗忘 ──
E8_FEATURES=0
E8_TOTAL=3
if [ -f "$HOOK_DIR/compact-detect.sh" ] && grep -qE '知识重新注入|知识注入|知识.*恢复|reinjection|knowledge.*re' "$HOOK_DIR/compact-detect.sh" 2>/dev/null; then
    E8_FEATURES=$((E8_FEATURES + 1))
fi
if [ -f "$HOOK_DIR/inject-project-knowledge.sh" ]; then
    E8_FEATURES=$((E8_FEATURES + 1))
fi
if [ -f "$HOOK_DIR/context-guard.sh" ]; then
    E8_FEATURES=$((E8_FEATURES + 1))
fi
E8_SCORE=$(round2 "$(echo "scale=4; $E8_FEATURES / $E8_TOTAL" | bc 2>/dev/null || echo 0)")
echo "  E8: $E8_SCORE (context amnesia defense: $E8_FEATURES/$E8_TOTAL)" >&2

# ──────────────────────────────────────────────
# G 维度检查（长期治理）
# ──────────────────────────────────────────────

HARNESS_YAML="$PROJECT_ROOT/.claude/harness.yaml"

# G1: 抗衰减防线 — audit-hooks + hook-production-verify + smoke test + auto-snapshot
G1_COUNT=0; G1_TOTAL=4
[ -f "$PROJECT_ROOT/.claude/scripts/audit-hooks.sh" ] && G1_COUNT=$((G1_COUNT+1))
[ -f "$PROJECT_ROOT/.claude/scripts/hook-production-verify.sh" ] && G1_COUNT=$((G1_COUNT+1))
[ -f "$SMOKE_TEST" ] && G1_COUNT=$((G1_COUNT+1))
[ -f "$HOOK_DIR/auto-snapshot.sh" ] && G1_COUNT=$((G1_COUNT+1))
G1_SCORE=$(round2 "$(echo "scale=4; $G1_COUNT / $G1_TOTAL" | bc 2>/dev/null || echo 0)")
G1_SOURCE="anti-decay scripts: $G1_COUNT/$G1_TOTAL = $G1_SCORE"
echo "  G1: $G1_SCORE (anti-decay: $G1_COUNT/$G1_TOTAL)" >&2

# G2: AI自动化 — compact-detect + auto-snapshot + error-dna auto-capture + error-dna-auto-fix
G2_COUNT=0; G2_TOTAL=4
[ -f "$HOOK_DIR/compact-detect.sh" ] && G2_COUNT=$((G2_COUNT+1))
[ -f "$HOOK_DIR/auto-snapshot.sh" ] && G2_COUNT=$((G2_COUNT+1))
grep -q 'error-dna' "$SETTINGS_JSON" 2>/dev/null && G2_COUNT=$((G2_COUNT+1))
[ -f "$HOOK_DIR/error-dna-auto-fix.sh" ] && G2_COUNT=$((G2_COUNT+1))
G2_SCORE=$(round2 "$(echo "scale=4; $G2_COUNT / $G2_TOTAL" | bc 2>/dev/null || echo 0)")
G2_SOURCE="AI automation: $G2_COUNT/$G2_TOTAL = $G2_SCORE"
echo "  G2: $G2_SCORE (AI automation: $G2_COUNT/$G2_TOTAL)" >&2

# G3: 学习笔记 — claude-next.md + memory files + lesson tracking
G3_COUNT=0; G3_TOTAL=4
NEXT_LINES_G=$(wc -l < "$CLAUDE_NEXT" 2>/dev/null || echo 0)
[ "$NEXT_LINES_G" -gt 100 ] && G3_COUNT=$((G3_COUNT+1))
[ -f "$STATE_DIR/session-handoff.md" ] && G3_COUNT=$((G3_COUNT+1))
[ -f "$STATE_DIR/session-snapshot.json" ] && G3_COUNT=$((G3_COUNT+1))
R_LEARN=$(grep -c '\[R' "$CLAUDE_NEXT" 2>/dev/null); R_LEARN="${R_LEARN:-0}"
[ "$R_LEARN" -gt 10 ] && G3_COUNT=$((G3_COUNT+1))
G3_SCORE=$(round2 "$(echo "scale=4; $G3_COUNT / $G3_TOTAL" | bc 2>/dev/null || echo 0)")
G3_SOURCE="learning notes: $G3_COUNT/$G3_TOTAL = $G3_SCORE"
echo "  G3: $G3_SCORE (learning notes: $G3_COUNT/$G3_TOTAL)" >&2

# G4: 功能标志治理 — harness.yaml hooks_enabled + hc_enabled coverage + audit-hooks
G4_COUNT=0; G4_TOTAL=3
grep -q 'hooks_enabled' "$HARNESS_YAML" 2>/dev/null && G4_COUNT=$((G4_COUNT+1))
[ -f "$PROJECT_ROOT/.claude/scripts/audit-hooks.sh" ] && G4_COUNT=$((G4_COUNT+1))
HOOKS_HC=0
for hf in "$HOOK_DIR"/*.sh; do
    [ -f "$hf" ] && grep -q 'hc_enabled' "$hf" 2>/dev/null && HOOKS_HC=$((HOOKS_HC+1))
done
HOOK_TOTAL_G=$(count_files "$HOOK_DIR/*.sh")
[ "$HOOK_TOTAL_G" -gt 0 ] && [ "$HOOKS_HC" -eq "$HOOK_TOTAL_G" ] 2>/dev/null && G4_COUNT=$((G4_COUNT+1))
G4_SCORE=$(round2 "$(echo "scale=4; $G4_COUNT / $G4_TOTAL" | bc 2>/dev/null || echo 0)")
G4_SOURCE="feature flags: $G4_COUNT/$G4_TOTAL = $G4_SCORE"
echo "  G4: $G4_SCORE (feature flags: $G4_COUNT/$G4_TOTAL)" >&2

# G5: 内置安全 — permission-gate + privacy-gate + sensitive-edit + context-guard
G5_COUNT=0; G5_TOTAL=4
grep -q 'permission-gate' "$SETTINGS_JSON" 2>/dev/null && G5_COUNT=$((G5_COUNT+1))
grep -q 'privacy-gate' "$SETTINGS_JSON" 2>/dev/null && G5_COUNT=$((G5_COUNT+1))
grep -q 'sensitive-edit' "$SETTINGS_JSON" 2>/dev/null && G5_COUNT=$((G5_COUNT+1))
grep -q 'context-guard' "$SETTINGS_JSON" 2>/dev/null && G5_COUNT=$((G5_COUNT+1))
G5_SCORE=$(round2 "$(echo "scale=4; $G5_COUNT / $G5_TOTAL" | bc 2>/dev/null || echo 0)")
G5_SOURCE="built-in security: $G5_COUNT/$G5_TOTAL = $G5_SCORE"
echo "  G5: $G5_SCORE (built-in security: $G5_COUNT/$G5_TOTAL)" >&2

# G6: 评测框架 — score-self-check exists, baseline, diff, weights documented
G6_COUNT=0; G6_TOTAL=4
[ -f "$PROJECT_ROOT/.claude/scripts/score-self-check.sh" ] && G6_COUNT=$((G6_COUNT+1))
[ -f "$STATE_DIR/score-baseline.json" ] && G6_COUNT=$((G6_COUNT+1))
[ -f "$STATE_DIR/score-report.json" ] && G6_COUNT=$((G6_COUNT+1))
grep -q 'WEIGHTS\|C_WEIGHTS\|原始评分体系' "$PROJECT_ROOT/.claude/scripts/score-self-check.sh" 2>/dev/null && G6_COUNT=$((G6_COUNT+1))
G6_SCORE=$(round2 "$(echo "scale=4; $G6_COUNT / $G6_TOTAL" | bc 2>/dev/null || echo 0)")
G6_SOURCE="eval framework: $G6_COUNT/$G6_TOTAL = $G6_SCORE"
echo "  G6: $G6_SCORE (eval framework: $G6_COUNT/$G6_TOTAL)" >&2

# ──────────────────────────────────────────────
# U 维度检查（用户体验）
# ──────────────────────────────────────────────

# U1: 心智负担减轻 — CAPTCHA clear prompts + ghost exemption + format direction + R38
U1_COUNT=0; U1_TOTAL=4
grep -q '方法 A\|方法 B\|输入框中按 Enter' "$HOOK_DIR/pretool-sensitive-edit.sh" 2>/dev/null && U1_COUNT=$((U1_COUNT+1))
grep -q 'ghost.*mode.*豁免\|ghost.*exempt\|HAS_EXPLICIT_TARGET' "$HOOK_DIR/turn-counter.sh" 2>/dev/null && U1_COUNT=$((U1_COUNT+1))
grep -q '格式\|方向感\|方向\|摘要\|结构化' "$HOOK_DIR/posttool-format-gate.sh" 2>/dev/null && U1_COUNT=$((U1_COUNT+1))
grep -q 'evidence.*score\|质量评分\|quality.*breakdown\|提升方向' "$HOOK_DIR/completion-gate.sh" 2>/dev/null && U1_COUNT=$((U1_COUNT+1))
U1_SCORE=$(round2 "$(echo "scale=4; $U1_COUNT / $U1_TOTAL" | bc 2>/dev/null || echo 0)")
U1_SOURCE="mental load: $U1_COUNT/$U1_TOTAL = $U1_SCORE"
echo "  U1: $U1_SCORE (mental load: $U1_COUNT/$U1_TOTAL)" >&2

# U2: 用户掌控感 — permission-gate + sensitive-edit + git gate + Oracle gates
U2_COUNT=0; U2_TOTAL=4
grep -q 'permission-gate' "$SETTINGS_JSON" 2>/dev/null && [ -f "$HOOK_DIR/permission-gate.sh" ] && U2_COUNT=$((U2_COUNT+1))
[ -f "$HOOK_DIR/pretool-sensitive-edit.sh" ] && grep -q '验证码\|CAPTCHA\|approve' "$HOOK_DIR/pretool-sensitive-edit.sh" 2>/dev/null && U2_COUNT=$((U2_COUNT+1))
grep -q 'Git.*门禁\|git.*commit\|git.*push.*block' "$INDEX_FILE" 2>/dev/null && U2_COUNT=$((U2_COUNT+1))
grep -q 'Oracle\|oracle_gate\|终审\|og-' "$PROJECT_ROOT/.claude/skills/lx-oma-orch/SKILL.md" 2>/dev/null && U2_COUNT=$((U2_COUNT+1))
U2_SCORE=$(round2 "$(echo "scale=4; $U2_COUNT / $U2_TOTAL" | bc 2>/dev/null || echo 0)")
U2_SOURCE="user control: $U2_COUNT/$U2_TOTAL = $U2_SCORE"
echo "  U2: $U2_SCORE (user control: $U2_COUNT/$U2_TOTAL)" >&2

# U3: 行为可预测 — iron laws in index.md + scope freeze + fix cap + confidence format
U3_COUNT=0; U3_TOTAL=4
grep -q '铁律速查\|Iron Laws' "$INDEX_FILE" 2>/dev/null && U3_COUNT=$((U3_COUNT+1))
grep -q '范围冻结\|scope.*freeze' "$INDEX_FILE" 2>/dev/null && U3_COUNT=$((U3_COUNT+1))
grep -q '修复上限\|fix.*cap\|3 轮\|3轮' "$INDEX_FILE" 2>/dev/null && U3_COUNT=$((U3_COUNT+1))
grep -q '置信度\|confidence\|\[已验证\|\[已测试' "$INDEX_FILE" 2>/dev/null && U3_COUNT=$((U3_COUNT+1))
U3_SCORE=$(round2 "$(echo "scale=4; $U3_COUNT / $U3_TOTAL" | bc 2>/dev/null || echo 0)")
U3_SOURCE="predictability: $U3_COUNT/$U3_TOTAL = $U3_SCORE"
echo "  U3: $U3_SCORE (predictability: $U3_COUNT/$U3_TOTAL)" >&2

# U4: 交互质量 — format-gate方向感 + AskUserQuestion usage + structured output
U4_COUNT=0; U4_TOTAL=3
grep -q '方向感\|方向\|摘要' "$HOOK_DIR/posttool-format-gate.sh" 2>/dev/null && U4_COUNT=$((U4_COUNT+1))
grep -B5 'format-gate' "$SETTINGS_JSON" 2>/dev/null | grep -Fq '"matcher": ".*"' && U4_COUNT=$((U4_COUNT+1))
[ -f "$HOOK_DIR/posttool-anti-pattern-detect.sh" ] && U4_COUNT=$((U4_COUNT+1))
U4_SCORE=$(round2 "$(echo "scale=4; $U4_COUNT / $U4_TOTAL" | bc 2>/dev/null || echo 0)")
U4_SOURCE="interaction quality: $U4_COUNT/$U4_TOTAL = $U4_SCORE"
echo "  U4: $U4_SCORE (interaction quality: $U4_COUNT/$U4_TOTAL)" >&2

# U5: 人机权限分明 — permission-gate scope + sensitive-edit file list + git gate + privacy gate
U5_COUNT=0; U5_TOTAL=4
grep -q 'SCOPE_WRITE_RE\|gh_write_regex\|destructive.*regex' "$HOOK_DIR/permission-gate.sh" 2>/dev/null && U5_COUNT=$((U5_COUNT+1))
grep -q 'CLAUDE.md.*AGENTS.md\|sensitive.*match\|_IS_SENSITIVE' "$HOOK_DIR/pretool-sensitive-edit.sh" 2>/dev/null && U5_COUNT=$((U5_COUNT+1))
grep -q 'Git.*门禁\|git.*approve\|git.*commit.*wait' "$INDEX_FILE" 2>/dev/null && U5_COUNT=$((U5_COUNT+1))
grep -q '\.env\|private.*key\|私钥' "$HOOK_DIR/privacy-gate.sh" 2>/dev/null && U5_COUNT=$((U5_COUNT+1))
U5_SCORE=$(round2 "$(echo "scale=4; $U5_COUNT / $U5_TOTAL" | bc 2>/dev/null || echo 0)")
U5_SOURCE="permission clarity: $U5_COUNT/$U5_TOTAL = $U5_SCORE"
echo "  U5: $U5_SCORE (permission clarity: $U5_COUNT/$U5_TOTAL)" >&2

# ──────────────────────────────────────────────
# 权重 + 质量惩罚 + 加权汇总
# ──────────────────────────────────────────────

# 这一步交给 Python（需要读 claude-next.md 做质量惩罚）
SCORE_JSON_OUT="$STATE_DIR/score-report.json"
${PYTHON_BIN:-python3} -c "
import json, sys, re, os

# ── 权重（原始评分体系） ──
C_WEIGHTS = {
    'C1': 15, 'C2': 15, 'C3': 15,
    'C4': 10, 'C5': 10, 'C6': 10,
    'C7': 10, 'C8': 10, 'C9': 10
}
E_WEIGHTS = {
    'E1': 20, 'E2': 20, 'E3': 15,
    'E4': 12, 'E5': 10, 'E6': 13,
    'E7': 10, 'E8': 10
}
C_TOTAL_WEIGHT = sum(C_WEIGHTS.values())   # 105
E_TOTAL_WEIGHT = sum(E_WEIGHTS.values())    # 110

G_WEIGHTS = {
    'G1': 10, 'G2': 10, 'G3': 10,
    'G4': 10, 'G5': 15, 'G6': 10
}
U_WEIGHTS = {
    'U1': 15, 'U2': 15, 'U3': 10,
    'U4': 10, 'U5': 15
}
G_TOTAL_WEIGHT = sum(G_WEIGHTS.values())  # 65
U_TOTAL_WEIGHT = sum(U_WEIGHTS.values())  # 65

# ── 基础分数（从环境变量读入） ──
C_SCORES = {
    'C1': float('$C1_SCORE'),
    'C2': float('$C2_SCORE'),
    'C3': float('$C3_SCORE'),
    'C4': float('$C4_SCORE'),
    'C5': float('$C5_SCORE'),
    'C6': float('$C6_SCORE'),
    'C7': float('$C7_SCORE'),
    'C8': float('$C8_SCORE'),
    'C9': float('$C9_SCORE')
}
E_SCORES = {
    'E1': float('$E1_SCORE'),
    'E2': float('$E2_SCORE'),
    'E3': float('$E3_SCORE'),
    'E4': float('$E4_SCORE'),
    'E5': float('$E5_SCORE'),
    'E6': float('$E6_SCORE'),
    'E7': float('$E7_SCORE'),
    'E8': float('$E8_SCORE')
}
G_SCORES = {
    'G1': float('$G1_SCORE'),
    'G2': float('$G2_SCORE'),
    'G3': float('$G3_SCORE'),
    'G4': float('$G4_SCORE'),
    'G5': float('$G5_SCORE'),
    'G6': float('$G6_SCORE')
}
U_SCORES = {
    'U1': float('$U1_SCORE'),
    'U2': float('$U2_SCORE'),
    'U3': float('$U3_SCORE'),
    'U4': float('$U4_SCORE'),
    'U5': float('$U5_SCORE')
}

C_SOURCES = {
    'C1': '''$C1_SOURCE''',
    'C2': '''$C2_SOURCE''',
    'C3': '''$C3_SOURCE''',
    'C4': '''$C4_SOURCE''',
    'C5': '''$C5_SOURCE''',
    'C6': '''$C6_SOURCE''',
    'C7': '''$C7_SOURCE''',
    'C8': '''$C8_SOURCE''',
    'C9': '''$C9_SOURCE'''
}

G_SOURCES = {
    'G1': '''$G1_SOURCE''',
    'G2': '''$G2_SOURCE''',
    'G3': '''$G3_SOURCE''',
    'G4': '''$G4_SOURCE''',
    'G5': '''$G5_SOURCE''',
    'G6': '''$G6_SOURCE'''
}
U_SOURCES = {
    'U1': '''$U1_SOURCE''',
    'U2': '''$U2_SOURCE''',
    'U3': '''$U3_SOURCE''',
    'U4': '''$U4_SOURCE''',
    'U5': '''$U5_SOURCE'''
}

# ── 从 claude-next.md 解析教训 → 维度映射 ──
# 每条教训格式: [R数字] 标题 @日期 hits:N
# 映射表: R 编号 → (维度, 基础惩罚)
LESSON_DIM_MAP = {
    'R22': ('C5', 0.06),   # PostToolUse 不派发失败事件
    'R23': ('C8', 0.06),   # harness.yaml = 注册 ≠ 实际
    'R24': ('C8', 0.06),   # Bash unquoted glob
    'R25': ('E4', 0.04),   # max_turns 只能软约束
    'R26': ('C4', 0.04),   # 白名单 vs matcher 一致
    'R27': ('E7', 0.05),   # 百分比必须有来源
    'R28': ('E1', 0.06),   # 废弃架构描述不同步
    'R29': ('E8', 0.05),   # context-guard matcher 放宽
    'R30': ('E2', 0.06),   # AI 用文档默认值代替配置
    'R31': ('E2', 0.04),   # gh CLI 写操作盲区
    'R32': ('C8', 0.03),   # install.sh 标题层级
    'R33': ('E8', 0.04),   # compact-detect 知识注入
    'R34': ('E2', 0.05),   # 逐文件交叉验证
    'R35': ('C1', 0.03),   # hook 行为变更后更新注释
    'R36': ('C8', 0.04),   # hook 合并/废弃三方同步
    'R37': ('E4', 0.02),   # ghost mode 模糊指令豁免
    'R38': ('E3', 0.03),   # 证据门禁展示评分方向
    'R39': ('C2', 0.03),   # 注入预算约束
    'R40': ('E8', 0.03),   # Stop hook 运行时验证
    'R41': ('C9', 0.10),   # Error DNA 轮转丢失 99%
    'R42': ('E6', 0.08),   # hook 规则误用于 skill
    'R43': ('E6', 0.08),   # CAPTCHA 脚本化批准
}

CLAUDE_NEXT_PATH = '$CLAUDE_NEXT'
LESSON_HITS = {}  # dim → total_penalty

if os.path.isfile(CLAUDE_NEXT_PATH):
    with open(CLAUDE_NEXT_PATH) as f:
        content = f.read()
    # 解析每条教训的 hits
    for r_id, (dim, base_penalty) in LESSON_DIM_MAP.items():
        # 找 hits:N
        pattern = r'\\[' + re.escape(r_id) + r'\\].*?hits:(\\d+)'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            hits = int(m.group(1))
            # 检查是否已修复（限本条目范围，避免跨条目误匹配）
            entry_pat = r'### \[' + re.escape(r_id) + r'\].*?(?=\n### \[|\Z)'
            entry_m = re.search(entry_pat, content, re.DOTALL)
            fixed = '已修复' in (entry_m.group(0) if entry_m else '')
            penalty = base_penalty * hits
            if fixed:
                penalty *= 0.3  # 已修复的只记 30% 惩罚
            LESSON_HITS[dim] = LESSON_HITS.get(dim, 0) + penalty

# ── 机制成熟度（比功能存在更深入的质量维度） ──
# 1.00 = 硬阻断 (exit 2, 可中止执行)
# 0.90 = 主动机制 (产生可操作警告/上下文, 不阻断)
# 0.85 = 建议性/静态 (作为参考或被动检查)
MATURITY_MAP = {
    'C1': 0.85, 'C2': 0.85, 'C3': 1.00, 'C4': 0.85,
    'C5': 0.90, 'C6': 0.85, 'C7': 0.85, 'C8': 0.90, 'C9': 0.85,
    'E1': 0.85, 'E2': 0.90, 'E3': 1.00, 'E4': 1.00,  # E2 claim-audit exit 2
    'E5': 0.85, 'E6': 0.85, 'E7': 1.00, 'E8': 0.90,  # E7 anti-pattern A2/F1/H1 all exit 2
    'G1': 0.90, 'G2': 0.85, 'G3': 0.85, 'G4': 0.90,
    'G5': 1.00, 'G6': 0.85,
    'U1': 0.90, 'U2': 0.90, 'U3': 0.85, 'U4': 0.85, 'U5': 0.90,
}

# ── 计算质量衰减后的分数 ──
C_FINAL = {}
E_FINAL = {}
G_FINAL = {}
U_FINAL = {}
C_QUALITY_NOTES = {}
E_QUALITY_NOTES = {}
G_QUALITY_NOTES = {}
U_QUALITY_NOTES = {}

for dim, base in C_SCORES.items():
    maturity = MATURITY_MAP.get(dim, 0.85)
    penalty = LESSON_HITS.get(dim, 0)
    penalty = min(penalty, 0.3)
    final = max(0, round(base * maturity - penalty, 2))
    C_FINAL[dim] = final
    note = f'base={base:.2f} maturity={maturity:.2f}'
    if penalty > 0.01:
        note += f' penalty=-{penalty:.2f}'
    C_QUALITY_NOTES[dim] = note

for dim, base in E_SCORES.items():
    maturity = MATURITY_MAP.get(dim, 0.85)
    penalty = LESSON_HITS.get(dim, 0)
    penalty = min(penalty, 0.3)
    final = max(0, round(base * maturity - penalty, 2))
    E_FINAL[dim] = final
    note = f'base={base:.2f} maturity={maturity:.2f}'
    if penalty > 0.01:
        note += f' penalty=-{penalty:.2f}'
    E_QUALITY_NOTES[dim] = note

for dim, base in G_SCORES.items():
    maturity = MATURITY_MAP.get(dim, 0.85)
    penalty = LESSON_HITS.get(dim, 0)
    penalty = min(penalty, 0.3)
    final = max(0, round(base * maturity - penalty, 2))
    G_FINAL[dim] = final
    note = f'base={base:.2f} maturity={maturity:.2f}'
    if penalty > 0.01:
        note += f' penalty=-{penalty:.2f}'
    G_QUALITY_NOTES[dim] = note

for dim, base in U_SCORES.items():
    maturity = MATURITY_MAP.get(dim, 0.85)
    penalty = LESSON_HITS.get(dim, 0)
    penalty = min(penalty, 0.3)
    final = max(0, round(base * maturity - penalty, 2))
    U_FINAL[dim] = final
    note = f'base={base:.2f} maturity={maturity:.2f}'
    if penalty > 0.01:
        note += f' penalty=-{penalty:.2f}'
    U_QUALITY_NOTES[dim] = note

# ── 加权汇总 ──
c_weighted_sum = sum(C_FINAL[d] * C_WEIGHTS[d] for d in C_WEIGHTS)
e_weighted_sum = sum(E_FINAL[d] * E_WEIGHTS[d] for d in E_WEIGHTS)
g_weighted_sum = sum(G_FINAL[d] * G_WEIGHTS[d] for d in G_WEIGHTS)
u_weighted_sum = sum(U_FINAL[d] * U_WEIGHTS[d] for d in U_WEIGHTS)
c_weighted_avg = round(c_weighted_sum / C_TOTAL_WEIGHT, 4)
e_weighted_avg = round(e_weighted_sum / E_TOTAL_WEIGHT, 4)
g_weighted_avg = round(g_weighted_sum / G_TOTAL_WEIGHT, 4)
u_weighted_avg = round(u_weighted_sum / U_TOTAL_WEIGHT, 4)

# Composite: 权重加权（C 105 + E 110 + G 65 + U 65 = 345 总分）
total_weight = C_TOTAL_WEIGHT + E_TOTAL_WEIGHT + G_TOTAL_WEIGHT + U_TOTAL_WEIGHT
composite_raw = (c_weighted_sum + e_weighted_sum + g_weighted_sum + u_weighted_sum) / total_weight
composite_8 = round(composite_raw * 8, 2)
composite_10 = round(composite_raw * 10, 2)

# ── stderr 输出（人类可读） ──
print('', file=sys.stderr)
print(f'C 维度加权均分: {c_weighted_avg:.4f} (权重: {C_TOTAL_WEIGHT}分)', file=sys.stderr)
for d in ['C1','C2','C3','C4','C5','C6','C7','C8','C9']:
    print(f'  {d}: {C_FINAL[d]:.2f} (权重{C_WEIGHTS[d]}) [{C_QUALITY_NOTES[d]}]', file=sys.stderr)
print(f'E 维度加权均分: {e_weighted_avg:.4f} (权重: {E_TOTAL_WEIGHT}分)', file=sys.stderr)
for d in ['E1','E2','E3','E4','E5','E6','E7','E8']:
    print(f'  {d}: {E_FINAL[d]:.2f} (权重{E_WEIGHTS[d]}) [{E_QUALITY_NOTES[d]}]', file=sys.stderr)
print(f'G 维度加权均分: {g_weighted_avg:.4f} (权重: {G_TOTAL_WEIGHT}分)', file=sys.stderr)
for d in ['G1','G2','G3','G4','G5','G6']:
    print(f'  {d}: {G_FINAL[d]:.2f} (权重{G_WEIGHTS[d]}) [{G_QUALITY_NOTES[d]}]', file=sys.stderr)
print(f'U 维度加权均分: {u_weighted_avg:.4f} (权重: {U_TOTAL_WEIGHT}分)', file=sys.stderr)
for d in ['U1','U2','U3','U4','U5']:
    print(f'  {d}: {U_FINAL[d]:.2f} (权重{U_WEIGHTS[d]}) [{U_QUALITY_NOTES[d]}]', file=sys.stderr)
print(f'', file=sys.stderr)
print(f'综合(8分制): {composite_8}', file=sys.stderr)
print(f'综合(10分制): {composite_10}', file=sys.stderr)
print(f'质量衰减详情:', file=sys.stderr)
for dim, total_pen in sorted(LESSON_HITS.items()):
    print(f'  {dim}: penalty {total_pen:.2f}', file=sys.stderr)
if not LESSON_HITS:
    print(f'  (无质量衰减)', file=sys.stderr)

# ── JSON 输出 ──
timestamp = '$TIMESTAMP'
report = {
    'timestamp': timestamp,
    'scoring_method': 'weighted + quality_penalty',
    'weights': {
        'C': C_WEIGHTS,
        'E': E_WEIGHTS,
        'C_total': C_TOTAL_WEIGHT,
        'E_total': E_TOTAL_WEIGHT
    },
    'quality_penalties': {dim: round(p, 3) for dim, p in sorted(LESSON_HITS.items())},
    'dimensions': {},
    'lessons': {},
    'summary': {
        'c_weighted_average': c_weighted_avg,
        'e_weighted_average': e_weighted_avg,
        'g_weighted_average': g_weighted_avg,
        'u_weighted_average': u_weighted_avg,
        'composite_8': composite_8,
        'composite_10': composite_10,
        'total_weight': total_weight,
        'note': 'C权重: 15+15+15+10+10+10+10+10+10=105, E权重: 20+20+15+12+10+13+10+10=110, G权重: 10+10+10+10+15+10=65, U权重: 15+15+10+10+15=65'
    }
}

for d in ['C1','C2','C3','C4','C5','C6','C7','C8','C9']:
    report['dimensions'][d] = {
        'score': C_FINAL[d],
        'weight': C_WEIGHTS[d],
        'source': C_SOURCES[d],
        'quality_note': C_QUALITY_NOTES[d]
    }

E_FEATS = {
    'E1': [$E1_FEATURES, $E1_TOTAL],
    'E2': [$E2_FEATURES, $E2_TOTAL],
    'E3': [$E3_FEATURES, $E3_TOTAL],
    'E4': [$E4_FEATURES, $E4_TOTAL],
    'E5': [$E5_FEATURES, $E5_TOTAL],
    'E6': [$E6_FEATURES, $E6_TOTAL],
    'E7': [$E7_FEATURES, $E7_TOTAL],
    'E8': [$E8_FEATURES, $E8_TOTAL],
}

for d in ['E1','E2','E3','E4','E5','E6','E7','E8']:
    fp, ft = E_FEATS[d]
    report['lessons'][d] = {
        'score': E_FINAL[d],
        'weight': E_WEIGHTS[d],
        'features_present': fp,
        'features_total': ft,
        'quality_note': E_QUALITY_NOTES[d]
    }

G_FEATS = {
    'G1': [$G1_COUNT, $G1_TOTAL],
    'G2': [$G2_COUNT, $G2_TOTAL],
    'G3': [$G3_COUNT, $G3_TOTAL],
    'G4': [$G4_COUNT, $G4_TOTAL],
    'G5': [$G5_COUNT, $G5_TOTAL],
    'G6': [$G6_COUNT, $G6_TOTAL],
}
for d in ['G1','G2','G3','G4','G5','G6']:
    fp, ft = G_FEATS[d]
    report['dimensions'][d] = {
        'score': G_FINAL[d],
        'weight': G_WEIGHTS[d],
        'features_present': fp,
        'features_total': ft,
        'quality_note': G_QUALITY_NOTES[d]
    }

U_FEATS = {
    'U1': [$U1_COUNT, $U1_TOTAL],
    'U2': [$U2_COUNT, $U2_TOTAL],
    'U3': [$U3_COUNT, $U3_TOTAL],
    'U4': [$U4_COUNT, $U4_TOTAL],
    'U5': [$U5_COUNT, $U5_TOTAL],
}
for d in ['U1','U2','U3','U4','U5']:
    fp, ft = U_FEATS[d]
    report['dimensions'][d] = {
        'score': U_FINAL[d],
        'weight': U_WEIGHTS[d],
        'features_present': fp,
        'features_total': ft,
        'quality_note': U_QUALITY_NOTES[d]
    }

with open('$SCORE_JSON_OUT', 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
"

SCORE_PY_EXIT=$?

if [ "$SCORE_PY_EXIT" -ne 0 ] || [ ! -f "$SCORE_JSON_OUT" ]; then
    echo '{"error": "Weighted scoring generation failed"}' >&2
    exit 1
fi

cat "$SCORE_JSON_OUT"

# ─── --init 模式：保存基线 ───
if [ "$INIT" = true ]; then
    cp "$STATE_DIR/score-report.json" "$STATE_DIR/score-baseline.json"
    echo "" >&2
    echo "✅ 基线已保存: .omc/state/score-baseline.json" >&2
fi

# ─── --diff 模式：差异比较（读取 JSON 的输出而非存变量） ───
if [ -n "$DIFF_FILE" ]; then
    if [ ! -f "$DIFF_FILE" ]; then
        echo "错误: 基线文件不存在: $DIFF_FILE" >&2
        exit 1
    fi

    echo "" >&2
    echo "═══ 与基线差异 ($DIFF_FILE) ═══" >&2

    ${PYTHON_BIN:-python3} -c "
import json, sys

try:
    with open('$DIFF_FILE') as f:
        baseline = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f'基线文件加载失败: {e}', file=sys.stderr)
    sys.exit(1)

current_report_path = '$STATE_DIR/score-report.json'
try:
    with open(current_report_path) as f:
        current = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f'当前报告加载失败: {e}', file=sys.stderr)
    sys.exit(1)

for dim in ['C1','C2','C3','C4','C5','C6','C7','C8','C9']:
    b = baseline.get('dimensions', {}).get(dim, {}).get('score', 0)
    c = current.get('dimensions', {}).get(dim, {}).get('score', 0)
    diff = c - b
    if abs(diff) < 0.001:
        marker = '＝'
    elif diff > 0:
        marker = '▲'
    else:
        marker = '▼'
    print(f'{dim}: {b:.2f} \\u2192 {c:.2f} ({marker} {diff:+.2f})')

for dim in ['E1','E2','E3','E4','E5','E6','E7','E8']:
    b = baseline.get('lessons', {}).get(dim, {}).get('score', 0)
    c = current.get('lessons', {}).get(dim, {}).get('score', 0)
    diff = c - b
    if abs(diff) < 0.001:
        marker = '＝'
    elif diff > 0:
        marker = '▲'
    else:
        marker = '▼'
    print(f'{dim}: {b:.2f} \\u2192 {c:.2f} ({marker} {diff:+.2f})')

for dim in ['G1','G2','G3','G4','G5','G6']:
    b = baseline.get('dimensions', {}).get(dim, {}).get('score', 0)
    c = current.get('dimensions', {}).get(dim, {}).get('score', 0)
    diff = c - b
    if abs(diff) < 0.001:
        marker = '＝'
    elif diff > 0:
        marker = '▲'
    else:
        marker = '▼'
    print(f'{dim}: {b:.2f} \\u2192 {c:.2f} ({marker} {diff:+.2f})')

for dim in ['U1','U2','U3','U4','U5']:
    b = baseline.get('dimensions', {}).get(dim, {}).get('score', 0)
    c = current.get('dimensions', {}).get(dim, {}).get('score', 0)
    diff = c - b
    if abs(diff) < 0.001:
        marker = '＝'
    elif diff > 0:
        marker = '▲'
    else:
        marker = '▼'
    print(f'{dim}: {b:.2f} \\u2192 {c:.2f} ({marker} {diff:+.2f})')

bs = baseline.get('summary', {})
cs = current.get('summary', {})
print('---')
print(f'C加权: {bs.get(\"c_weighted_average\", 0):.3f} \\u2192 {cs.get(\"c_weighted_average\", 0):.3f}')
print(f'E加权: {bs.get(\"e_weighted_average\", 0):.3f} \\u2192 {cs.get(\"e_weighted_average\", 0):.3f}')
print(f'G加权: {bs.get(\"g_weighted_average\", 0):.3f} \\u2192 {cs.get(\"g_weighted_average\", 0):.3f}')
print(f'U加权: {bs.get(\"u_weighted_average\", 0):.3f} \\u2192 {cs.get(\"u_weighted_average\", 0):.3f}')
print(f'综合8: {bs.get(\"composite_8\", 0):.2f} \\u2192 {cs.get(\"composite_8\", 0):.2f}')
print(f'综合10: {bs.get(\"composite_10\", 0):.2f} \\u2192 {cs.get(\"composite_10\", 0):.2f}')
" 2>&1
fi
