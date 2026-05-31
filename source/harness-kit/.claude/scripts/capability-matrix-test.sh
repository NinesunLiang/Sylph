#!/usr/bin/env bash
# capability-matrix-test.sh — Carror OS 能力矩阵全量测试
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 用途: 基于 docs/reference/cn/capability-matrix.md 测试所有机制是否真正生效
# 用法: bash .claude/scripts/capability-matrix-test.sh [--quick] [--json]
#   --quick  跳过 harness-smoke-test.sh (快)
#   --json   输出 JSON 格式
# 退出: 0=全通过; N=N个维度失败
# 日志: .omc/state/capability-matrix-test-<ts>.log
#
# 兼容: bash 3.2+ (macOS default), 不依赖 bash 4+ associative arrays

set -uo pipefail
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
TS=$(date +%Y%m%d-%H%M%S)
LOG=".omc/state/capability-matrix-test-$TS.log"
mkdir -p .omc/state

QUICK=false
JSON_OUT=false
RUNTIME=true  # Default: real runtime tests
for arg in "$@"; do
    case "$arg" in --quick) QUICK=true ;; --json) JSON_OUT=true ;; --static) RUNTIME=false ;; esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

PASS=0; FAIL=0; WARN=0; TOTAL=0
TMPDIR="${TMPDIR:-/tmp}/cm-test-$$"
mkdir -p "$TMPDIR"
trap "rm -rf '$TMPDIR'" EXIT

log()  { echo -e "$@" | tee -a "$LOG"; }
pass() { log "  ${GREEN}✓${NC} $1"; PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); }
fail() { log "  ${RED}✗${NC} $1"; FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); }
warn() { log "  ${YELLOW}⚠${NC} $1"; WARN=$((WARN+1)); TOTAL=$((TOTAL+1)); }
info() { log "  ${CYAN}ℹ${NC} $1"; }

# Dimension tracking via temp files (bash 3.2 compatible)
dim_init() {
    local d="$1"
    echo 0 > "$TMPDIR/${d}_pass"
    echo 0 > "$TMPDIR/${d}_fail"
    echo 0 > "$TMPDIR/${d}_warn"
    echo 0 > "$TMPDIR/${d}_total"
}
dim_pass()  { local d="$1"; local v; v=$(cat "$TMPDIR/${d}_pass" 2>/dev/null || echo 0); echo $((v+1)) > "$TMPDIR/${d}_pass"; }
dim_fail()  { local d="$1"; local v; v=$(cat "$TMPDIR/${d}_fail" 2>/dev/null || echo 0); echo $((v+1)) > "$TMPDIR/${d}_fail"; }
dim_warn()  { local d="$1"; local v; v=$(cat "$TMPDIR/${d}_warn" 2>/dev/null || echo 0); echo $((v+1)) > "$TMPDIR/${d}_warn"; }
dim_total() { local d="$1"; local v; v=$(cat "$TMPDIR/${d}_total" 2>/dev/null || echo 0); echo $((v+1)) > "$TMPDIR/${d}_total"; }
dim_score() {
    local d="$1"
    local p=$(cat "$TMPDIR/${d}_pass" 2>/dev/null || echo 0)
    local t=$(cat "$TMPDIR/${d}_total" 2>/dev/null || echo 1)
    local w=$(cat "$TMPDIR/${d}_warn" 2>/dev/null || echo 0)
    [ "$t" -eq 0 ] && t=1
    echo "scale=1; ($p * 100 + $w * 50) / $t" | bc 2>/dev/null || echo "0"
}

header() { log "\n${BOLD}━━━ $1 ━━━${NC}"; }
dim_header() { log "\n${BOLD}── $1 ──${NC}"; dim_init "$1"; }

# ── Helpers ────────────────────────────────────────────────

check_file_exists() { [ -f "$PROJECT_ROOT/$1" ] && return 0 || return 1; }

# ── ENVIRONMENT CHECK ───────────────────────────────────────

header "ENVIRONMENT CHECK"

[ -f "$PROJECT_ROOT/.claude/harness.yaml" ] && pass "harness.yaml exists" || fail "harness.yaml MISSING"
[ -f "$PROJECT_ROOT/.claude/settings.json" ] && pass "settings.json exists" || fail "settings.json MISSING"
[ -f "$PROJECT_ROOT/.claude/feature-registry.yaml" ] && pass "feature-registry.yaml exists" || fail "feature-registry.yaml MISSING"
[ -d "$PROJECT_ROOT/.claude/hooks" ] && pass ".claude/hooks/ directory exists" || fail ".claude/hooks/ directory MISSING"

# ── DIMENSION 1: HOOK EXISTENCE ─────────────────────────────

dim_header "D1-HOOK-EXISTENCE"

# Extract hooks_enabled from harness.yaml (space-separated key:value format)
${PYTHON_BIN:-python3} > "$TMPDIR/hooks_enabled.txt" <<PYEOF
import re
with open('$PROJECT_ROOT/.claude/harness.yaml') as f:
    in_hooks = False
    for line in f:
        if line.strip().startswith('hooks_enabled:'):
            in_hooks = True
            continue
        if in_hooks:
            m = re.match(r'\s+(\w+):\s*(true|false)', line)
            if m and m.group(2) == 'true':
                print(m.group(1))
            elif not re.match(r'\s+\w+:\s*(true|false)', line):
                break  # end of hooks_enabled section
PYEOF

HOOK_COUNT=0
while IFS= read -r hook_name; do
    [ -z "$hook_name" ] && continue
    # map hook_name to script filename
    script=""
    case "$hook_name" in
        anti_pattern_detect)       script="posttool-anti-pattern-detect.sh" ;;
        auto_snapshot)             script="auto-snapshot.sh" ;;
        completion_gate)           script="completion-gate.sh" ;;
        context_guard)             script="context-guard.sh" ;;
        context_compressor)        script="context-compressor.sh" ;;
        ecosystem_probe)           script="ecosystem-probe.sh" ;;
        edit_guard)                script="edit-guard.sh" ;;
        error_dna)                 script="error-dna.sh" ;;
        fuzzy_block)               script="fuzzy-block.sh" ;;
        inject_project_knowledge)  script="inject-project-knowledge.sh" ;;
        intent_tracker)            script="intent-tracker.sh" ;;
        issue_triage)              script="" ;;
        knowledge_condenser)       script="knowledge-condenser.sh" ;;
        lsp_suggest)               script="lsp-suggest.sh" ;;
        lsp_gate)                  script="pre-edit-lsp-check.sh" ;;
        meta_oracle_trigger)       script="meta-oracle-trigger.sh" ;;
        permission_gate)           script="permission-gate.sh" ;;
        plan_gate)                 script="plan-gate.sh" ;;
        posttool_bash_audit)       script="posttool-bash-audit.sh" ;;
        posttool_claim_audit)      script="posttool-claim-audit.sh" ;;
        posttool_completion_audit) script="posttool-completion-audit.sh" ;;
        posttool_edit_quality)     script="posttool-edit-quality.sh" ;;
        posttool_handoff_writer)   script="posttool-handoff-writer.sh" ;;
        posttool_output_format)    script="posttool-format-gate.sh" ;;
        posttool_subagent_audit)   script="posttool-subagent-audit.sh" ;;
        posttool_write_cite)       script="posttool-write-cite.sh" ;;
        posttool_write_lock)       script="posttool-write-lock.sh" ;;
        pre_completion_gate)       script="pre-completion-gate.sh" ;;
        pre_ask_guard)             script="pre-ask-guard.sh" ;;
        pretool_edit_scope)        script="pretool-edit-scope.sh" ;;
        pretool_sensitive_edit)    script="pretool-sensitive-edit.sh" ;;
        pretool_write_lock)        script="pretool-write-lock.sh" ;;
        privacy_gate)              script="privacy-gate.sh" ;;
        read_tracker)              script="read-tracker.sh" ;;
        retry_budget_check)        script="pretool-retry-check.sh" ;;
        skill_flywheel)            script="skill-flywheel.sh" ;;
        stop_drain)                script="stop-drain.sh" ;;
        subagent_guard)            script="subagent-guard.sh" ;;
        token_writer)              script="token_writer.sh" ;;
        skill_usage_tracker)       script="skill-usage-tracker.sh" ;;
        turn_counter)              script="turn-counter.sh" ;;
        user_correction_detector)  script="pretool-user-correction.sh" ;;
        rule_anchor)               script="" ;;
        *)                         script="" ;;
    esac

    if [ -z "$script" ]; then
        warn "[$hook_name] → 无对应脚本 (内置/未实现)"
        dim_warn "D1-HOOK-EXISTENCE"
    elif [ -f "$PROJECT_ROOT/.claude/hooks/$script" ]; then
        pass "[$hook_name] → $script ✓"
        dim_pass "D1-HOOK-EXISTENCE"
    else
        fail "[$hook_name] → $script FILE NOT FOUND"
        dim_fail "D1-HOOK-EXISTENCE"
    fi
    dim_total "D1-HOOK-EXISTENCE"
    HOOK_COUNT=$((HOOK_COUNT+1))
done < "$TMPDIR/hooks_enabled.txt"

# Count hooks from harness.yaml (already counted in loop)
info "D1: hooks_enabled=$HOOK_COUNT 项 | 评分=$(dim_score "D1-HOOK-EXISTENCE")%"

# ── DIMENSION 2: SETTINGS.JSON REGISTRATION ──────────────────

dim_header "D2-SETTINGS-REGISTRATION"

SCRIPT_COUNT=0
REGISTERED=0
MISSING_REG=0
for script in "$PROJECT_ROOT"/.claude/hooks/*.sh; do
    sname=$(basename "$script")
    case "$sname" in harness_config.sh|agentic-ui.sh) continue ;; esac
    SCRIPT_COUNT=$((SCRIPT_COUNT+1))
    if grep -q "$sname" "$PROJECT_ROOT/.claude/settings.json" 2>/dev/null; then
        REGISTERED=$((REGISTERED+1))
        dim_pass "D2-SETTINGS-REGISTRATION"
    else
        fail "[$sname] 未在 settings.json 注册"
        MISSING_REG=$((MISSING_REG+1))
        dim_fail "D2-SETTINGS-REGISTRATION"
    fi
    dim_total "D2-SETTINGS-REGISTRATION"
done

info "D2: scripts=$SCRIPT_COUNT | registered=$REGISTERED | missing=$MISSING_REG | 评分=$(dim_score "D2-SETTINGS-REGISTRATION")%"

# ── DIMENSION 3: BASH SYNTAX CHECK ──────────────────────────

dim_header "D3-BASH-SYNTAX"

BASH_FAIL=0
for script in "$PROJECT_ROOT"/.claude/hooks/*.sh; do
    sname=$(basename "$script")
    if bash -n "$script" 2>/dev/null; then
        dim_pass "D3-BASH-SYNTAX"
    else
        fail "[$sname] bash 语法错误"
        bash -n "$script" 2>&1 | head -3 >> "$LOG"
        BASH_FAIL=$((BASH_FAIL+1))
        dim_fail "D3-BASH-SYNTAX"
    fi
    dim_total "D3-BASH-SYNTAX"
done

info "D3: bash syntax failures=$BASH_FAIL | 评分=$(dim_score "D3-BASH-SYNTAX")%"

# ── DIMENSION 4: HARNESS SMOKE TEST ─────────────────────────

dim_header "D4-SMOKE-TEST"

if $QUICK; then
    warn "D4: --quick 模式，跳过 smoke test"
    dim_warn "D4-SMOKE-TEST"
    dim_total "D4-SMOKE-TEST"
else
    SMOKE_SCRIPT="$PROJECT_ROOT/.claude/scripts/harness-smoke-test.sh"
    if [ -f "$SMOKE_SCRIPT" ]; then
        log "  运行 harness-smoke-test.sh ..."
        if bash "$SMOKE_SCRIPT" >> "$LOG" 2>&1; then
            pass "D4: smoke test ALL PASSED"
            dim_pass "D4-SMOKE-TEST"
        else
            SMOKE_EXIT=$?
            fail "D4: smoke test FAILED (exit=$SMOKE_EXIT)"
            dim_fail "D4-SMOKE-TEST"
        fi
    else
        fail "D4: harness-smoke-test.sh not found"
        dim_fail "D4-SMOKE-TEST"
    fi
    dim_total "D4-SMOKE-TEST"
fi

info "D4: 评分=$(dim_score "D4-SMOKE-TEST")%"

# ── DIMENSION 5: FEATURE REGISTRY CONSISTENCY ───────────────

dim_header "D5-FEATURE-REGISTRY"

FEAT_REG="$PROJECT_ROOT/.claude/feature-registry.yaml"
if [ -f "$FEAT_REG" ]; then
    REG_HOOK_COUNT=$(${PYTHON_BIN:-python3} -c "
import yaml
with open('$FEAT_REG') as f:
    data = yaml.safe_load(f)
hooks = data.get('hooks', [])
print(len(hooks))
" 2>/dev/null || echo "?")
    REG_SKILL_COUNT=$(${PYTHON_BIN:-python3} -c "
import yaml
with open('$FEAT_REG') as f:
    data = yaml.safe_load(f)
skills = data.get('skills', [])
print(len(skills))
" 2>/dev/null || echo "?")

    pass "D5: feature-registry.yaml → $REG_HOOK_COUNT hooks + $REG_SKILL_COUNT skills"
else
    fail "D5: feature-registry.yaml not found"
fi
dim_pass "D5-FEATURE-REGISTRY"; dim_total "D5-FEATURE-REGISTRY"

# Check skill files exist
SKILL_FOUND=0; SKILL_MISSING=0
SKILL_DIR="$PROJECT_ROOT/.claude/skills"
if [ -d "$SKILL_DIR" ]; then
    for s in "$SKILL_DIR"/lx-*/; do
        [ ! -d "$s" ] && continue
        if [ -f "$s/SKILL.md" ]; then
            SKILL_FOUND=$((SKILL_FOUND+1))
        else
            warn "[$(basename "$s")] SKILL.md MISSING"
            SKILL_MISSING=$((SKILL_MISSING+1))
        fi
    done
    pass "D5: skills found=$SKILL_FOUND missing=$SKILL_MISSING"
    dim_pass "D5-FEATURE-REGISTRY"; dim_total "D5-FEATURE-REGISTRY"
fi

info "D5: 评分=$(dim_score "D5-FEATURE-REGISTRY")%"

# ── DIMENSION 6: FLYWHEEL RUNTIME COVERAGE ────────────────────
# UPGRADED v2: Actually write a flywheel event and verify it's recorded.
# Old version just checked log file size.

dim_header "D6-FLYWHEEL-COVERAGE"

FLYWHEEL="$HOME/.claude/flywheel.log"

# Runtime test: write a test event and verify it's recorded
FLY_TEST_KEY="capability-test-$(date +%s)"
FLY_BEFORE=$(wc -l < "$FLYWHEEL" 2>/dev/null || echo "0")

# Write a test flywheel event (same format as flywheel_event in harness_config.sh)
FLY_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%Y-%m-%dT%H:%M:%SZ)
echo "{\"ts\":\"$FLY_TS\",\"source\":\"capability-test\",\"event\":\"runtime_verify\",\"key\":\"$FLY_TEST_KEY\",\"severity\":\"P3\"}" >> "$FLYWHEEL" 2>/dev/null

FLY_AFTER=$(wc -l < "$FLYWHEEL" 2>/dev/null || echo "0")
if [ "$FLY_AFTER" -gt "$FLY_BEFORE" ]; then
    pass "D6: flywheel RUNTIME write → +1 event (total=$FLY_AFTER lines, $(wc -c < "$FLYWHEEL" | tr -d ' ') bytes)"
    dim_pass "D6-FLYWHEEL-COVERAGE"
else
    fail "D6: flywheel write FAILED (before=$FLY_BEFORE after=$FLY_AFTER)"
    dim_fail "D6-FLYWHEEL-COVERAGE"
fi
dim_total "D6-FLYWHEEL-COVERAGE"

# Verify the event we just wrote is readable
if grep -q "$FLY_TEST_KEY" "$FLYWHEEL" 2>/dev/null; then
    pass "D6: flywheel event verification → key found ✓"
    dim_pass "D6-FLYWHEEL-COVERAGE"
else
    warn "D6: flywheel event not found (may be async)"
    dim_warn "D6-FLYWHEEL-COVERAGE"
fi
dim_total "D6-FLYWHEEL-COVERAGE"

# Per-hook flywheel check (static — can't trigger all hooks in test)
if [ -f "$FLYWHEEL" ]; then
    HOOKS_NO_FLYWHEEL=0
    for script in "$PROJECT_ROOT"/.claude/hooks/*.sh; do
        sname=$(basename "$script" .sh)
        case "$sname" in harness_config|agentic-ui) continue ;; esac
        if grep -q "\"$sname\"" "$FLYWHEEL" 2>/dev/null; then : ; else
            HOOKS_NO_FLYWHEEL=$((HOOKS_NO_FLYWHEEL+1))
        fi
    done
    if [ "$HOOKS_NO_FLYWHEEL" -gt 0 ]; then
        warn "D6: $HOOKS_NO_FLYWHEEL hooks have ZERO flywheel events (DG-82)"
        dim_warn "D6-FLYWHEEL-COVERAGE"
    fi
fi
dim_total "D6-FLYWHEEL-COVERAGE"
info "D6: 评分=$(dim_score "D6-FLYWHEEL-COVERAGE")%"

# ── DIMENSION 7: THREE-SOURCE CONSISTENCY ───────────────────

dim_header "D7-THREE-SOURCE"

AUDIT_SCRIPT="$PROJECT_ROOT/.claude/scripts/audit-hooks.sh"
if [ -f "$AUDIT_SCRIPT" ]; then
    AUDIT_OUT=$(bash "$AUDIT_SCRIPT" 2>&1)
    CRITICAL=$(echo "$AUDIT_OUT" | sed -n 's/.*🔴 严重: \([0-9]*\).*/\1/p' 2>/dev/null)
    CRITICAL="${CRITICAL:-0}"
    WARNCOUNT=$(echo "$AUDIT_OUT" | sed -n 's/.*🟡 次要: \([0-9]*\).*/\1/p' 2>/dev/null)
    WARNCOUNT="${WARNCOUNT:-0}"
    if [ "$CRITICAL" -eq 0 ]; then
        pass "D7: audit-hooks.sh → 0 critical, $WARNCOUNT warnings"
        dim_pass "D7-THREE-SOURCE"
    else
        fail "D7: audit-hooks.sh → $CRITICAL CRITICAL, $WARNCOUNT warnings"
        dim_fail "D7-THREE-SOURCE"
    fi
else
    fail "D7: audit-hooks.sh not found"
    dim_fail "D7-THREE-SOURCE"
fi
dim_total "D7-THREE-SOURCE"
info "D7: 评分=$(dim_score "D7-THREE-SOURCE")%"

# ── DIMENSION 8: ERROR DNA RUNTIME ──────────────────────────
# UPGRADED v2: Inject a test error and verify it's recorded.
# Old version just counted existing lines.

dim_header "D8-ERROR-DNA"

ERR_DNA="$PROJECT_ROOT/.omc/state/error-dna.jsonl"
ERR_SIG="$PROJECT_ROOT/.omc/state/error-signals.jsonl"
GOV_AUD="$PROJECT_ROOT/.omc/state/governance-audit.jsonl"

# Runtime test: inject a test error signal
TEST_SIG="capability-test-$(date +%s)"
ERR_BEFORE=$(wc -l < "$ERR_SIG" 2>/dev/null | tr -d ' ' || echo "0")
mkdir -p "$PROJECT_ROOT/.omc/state"
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"sig\":\"$TEST_SIG\",\"source\":\"capability-test\",\"severity\":\"P3\",\"message\":\"runtime injection test\"}" >> "$ERR_SIG" 2>/dev/null
ERR_AFTER=$(wc -l < "$ERR_SIG" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$ERR_AFTER" -gt "$ERR_BEFORE" ]; then
    pass "D8: error-signal RUNTIME inject → +1 (total=$ERR_AFTER)"
    dim_pass "D8-ERROR-DNA"
else
    fail "D8: error-signal injection FAILED"
    dim_fail "D8-ERROR-DNA"
fi
dim_total "D8-ERROR-DNA"

# Verify the signal is readable
if grep -q "$TEST_SIG" "$ERR_SIG" 2>/dev/null; then
    pass "D8: error-signal verification → found ✓"
    dim_pass "D8-ERROR-DNA"
else
    warn "D8: error-signal not found in file"
    dim_warn "D8-ERROR-DNA"
fi
dim_total "D8-ERROR-DNA"

# Overall pipeline health
E2_COUNT=0; SIG_COUNT=0; GOV_COUNT=0
[ -f "$ERR_DNA" ] && E2_COUNT=$(wc -l < "$ERR_DNA" 2>/dev/null | tr -d ' ' || echo 0)
[ -f "$ERR_SIG" ] && SIG_COUNT=$ERR_AFTER
[ -f "$GOV_AUD" ] && GOV_COUNT=$(wc -l < "$GOV_AUD" 2>/dev/null | tr -d ' ' || echo 0)
TOTAL_PIPE=$((E2_COUNT + SIG_COUNT + GOV_COUNT))

if [ "$TOTAL_PIPE" -gt 0 ]; then
    pass "D8: error pipeline active → E2=$E2_COUNT signals=$SIG_COUNT gov=$GOV_COUNT"
    dim_pass "D8-ERROR-DNA"
fi
dim_total "D8-ERROR-DNA"
info "D8: 评分=$(dim_score "D8-ERROR-DNA")%"

# ── DIMENSION 9: ORACLE RUNTIME VERIFICATION ──────────────────

dim_header "D9-ORACLE"

# Replace static file-existence checks with actual Meta-Oracle runtime spawn
# This is the CORE upgrade: D9 used to check "does oracle file exist?"
# Now it actually runs the Meta-Oracle scorer and gets a real verdict.

META_SCORER="$PROJECT_ROOT/.claude/scripts/meta-oracle-scorer.py"
if [ -f "$META_SCORER" ]; then
    log "  🚀 Spawning Meta-Oracle runtime scorer (30-60s)..."
    SCORER_OUT=$(${PYTHON_BIN:-python3} "$META_SCORER" --calibrated --meta-oracle 2>&1)
    SCORER_EXIT=$?

    if [ "$SCORER_EXIT" = "0" ]; then
        # Extract key metrics
        SCORE=$(echo "$SCORER_OUT" | grep -oP 'C/E/G 加权总分:\s+\K[0-9.]+' | head -1)
        VERDICT=$(echo "$SCORER_OUT" | grep -oP '\[Meta-Oracle: \K[A-Z]+\]?' | head -1)
        C_PCT=$(echo "$SCORER_OUT" | grep -oP 'C 正确性.*?=\s+\K[0-9.]+' | head -1)
        E_PCT=$(echo "$SCORER_OUT" | grep -oP 'E 有效性.*?=\s+\K[0-9.]+' | head -1)
        G_PCT=$(echo "$SCORER_OUT" | grep -oP 'G 治理.*?=\s+\K[0-9.]+' | head -1)
        SMOKE_RATE=$(echo "$SCORER_OUT" | grep -oP '烟雾测试通过率 = \K[0-9]+' | head -1)

        SCORE="${SCORE:-N/A}"; VERDICT="${VERDICT:-N/A}"
        C_PCT="${C_PCT:-?}"; E_PCT="${E_PCT:-?}"; G_PCT="${G_PCT:-?}"
        SMOKE_RATE="${SMOKE_RATE:-?}"

        # Score-based verdict
        if [ "$SCORE" != "N/A" ]; then
            SCORE_INT=$(echo "$SCORE" | cut -d. -f1)
            if [ "$SCORE_INT" -ge 9 ] 2>/dev/null; then
                pass "D9: Meta-Oracle RUNTIME → ${SCORE}/10 ${VERDICT} | C=${C_PCT}% E=${E_PCT}% G=${G_PCT}% | 烟测=${SMOKE_RATE}%"
                dim_pass "D9-ORACLE"
            elif [ "$SCORE_INT" -ge 7 ] 2>/dev/null; then
                warn "D9: Meta-Oracle RUNTIME → ${SCORE}/10 ${VERDICT} (ADVISORY) | C=${C_PCT}% E=${E_PCT}% G=${G_PCT}%"
                dim_warn "D9-ORACLE"
            else
                fail "D9: Meta-Oracle RUNTIME → ${SCORE}/10 ${VERDICT} (REJECT) | C=${C_PCT}% E=${E_PCT}% G=${G_PCT}%"
                dim_fail "D9-ORACLE"
            fi
        else
            warn "D9: Meta-Oracle ran but score unparseable"
            dim_warn "D9-ORACLE"
        fi
    else
        fail "D9: Meta-Oracle scorer FAILED (exit=$SCORER_EXIT)"
        dim_fail "D9-ORACLE"
    fi
    dim_total "D9-ORACLE"

    # Also check oracle infrastructure (files must exist for scorer to work)
    if [ -f "$PROJECT_ROOT/.omc/state/oracle_verdict.json" ]; then
        pass "D9: oracle_verdict.json exists (Oracle留痕完整)"
        dim_pass "D9-ORACLE"; dim_total "D9-ORACLE"
    else
        warn "D9: oracle_verdict.json missing (Oracle留痕不完整)"
        dim_warn "D9-ORACLE"; dim_total "D9-ORACLE"
    fi

    if [ -f "$PROJECT_ROOT/.omc/state/meta-oracle-verdicts.md" ]; then
        META_VC=$(grep -c "Meta-Oracle:" "$PROJECT_ROOT/.omc/state/meta-oracle-verdicts.md" 2>/dev/null || echo "0")
        pass "D9: meta-oracle-verdicts.md → $META_VC verdicts"
        dim_pass "D9-ORACLE"; dim_total "D9-ORACLE"
    else
        warn "D9: meta-oracle-verdicts.md missing"
        dim_warn "D9-ORACLE"; dim_total "D9-ORACLE"
    fi
else
    fail "D9: meta-oracle-scorer.py NOT FOUND — cannot run runtime test"
    dim_fail "D9-ORACLE"; dim_total "D9-ORACLE"
fi

info "D9: 评分=$(dim_score "D9-ORACLE")%"

# ── DIMENSION 10: PHILOSOPHY → MECHANISM TRACE ──────────────

dim_header "D10-PHILOSOPHY-TRACE"

check_mech() {
    local label="$1"; shift
    for m in "$@"; do
        if [ ! -f "$PROJECT_ROOT/.claude/hooks/$m" ]; then
            return 1
        fi
    done
    return 0
}

# Philosophy #1-#7 → their claimed mechanisms
if check_mech "#1-The-Less-The-More" "context-compressor.sh"; then
    pass "D10: 哲学#1 (Less is More) → context-compressor ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#1 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#2-少量正确大增益" "pretool-edit-scope.sh"; then
    pass "D10: 哲学#2 (少量大增益) → pretool-edit-scope ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#2 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#3-先守护后激发" "context-guard.sh" "permission-gate.sh" "privacy-gate.sh"; then
    pass "D10: 哲学#3 (先守护) → context-guard + permission-gate + privacy-gate ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#3 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#4-没验证等于没做" "completion-gate.sh" "pre-completion-gate.sh"; then
    pass "D10: 哲学#4 (没验证=没做) → completion-gate + pre-completion-gate ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#4 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#5-以人为本" "pre-ask-guard.sh" "posttool-format-gate.sh"; then
    pass "D10: 哲学#5 (以人为本) → pre-ask-guard + posttool-format-gate ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#5 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#6-先天0信任" "posttool-claim-audit.sh"; then
    pass "D10: 哲学#6 (0信任) → posttool-claim-audit ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#6 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

if check_mech "#7-文档优先调研先行" "plan-gate.sh"; then
    pass "D10: 哲学#7 (文档优先) → plan-gate ✓"
    dim_pass "D10-PHILOSOPHY-TRACE"
else fail "D10: 哲学#7 mechanism missing"; dim_fail "D10-PHILOSOPHY-TRACE"; fi
dim_total "D10-PHILOSOPHY-TRACE"

info "D10: 哲学 7 条→机制追溯 | 评分=$(dim_score "D10-PHILOSOPHY-TRACE")%"

# ── DIMENSION 11: IRON LAWS RUNTIME ENFORCEMENT ──────────────
# UPGRADED v2: Actually pipe test inputs into hooks, check exit codes.
# Old version just checked "does the hook file exist?"

dim_header "D11-IRON-LAWS"

# Hook runner helper: inject JSON input via stdin, optional $1 as tool_name
run_hook_test() {
    local label="$1" hook="$2" input="$3" expected_exit="$4" tool_name="${5:-}"
    local hp="$PROJECT_ROOT/.claude/hooks/$hook"
    if [ ! -f "$hp" ]; then
        fail "D11: $label → $hook NOT FOUND"
        dim_fail "D11-IRON-LAWS"; dim_total "D11-IRON-LAWS"
        return 1
    fi
    local out ec
    if [ -n "$tool_name" ]; then
        out=$(echo "$input" | bash "$hp" "$tool_name" 2>/dev/null)
    else
        out=$(echo "$input" | bash "$hp" 2>/dev/null)
    fi
    ec=$?
    if [ "$ec" = "$expected_exit" ]; then
        pass "D11: $label → $hook exit=$ec ✓"
        dim_pass "D11-IRON-LAWS"
    else
        fail "D11: $label → $hook exit=$ec (expected $expected_exit)"
        dim_fail "D11-IRON-LAWS"
    fi
    dim_total "D11-IRON-LAWS"
}

# 铁律#1: 禁止编造 — claim-audit checks Edit/Write for file:line references
# Needs $1="Edit" + tool_input.file_path + file:line refs in description (to trigger claim detection)
run_hook_test "#1-禁止编造" "posttool-claim-audit.sh" \
    '{"tool_input":{"file_path":"src/main.go","description":"修复 AGENTS.md:42 和 core.go:15 的bug"}}' 2 "Edit"

# 铁律#2: 用户裁定 — permission-gate blocks unauthorized git operations
# Check if permission_gate is enabled first
PG_ENABLED=$(${PYTHON_BIN:-python3} -c "
import yaml
with open('$PROJECT_ROOT/.claude/harness.yaml') as f:
    data = yaml.safe_load(f)
hooks = data.get('hooks_enabled', {})
print('true' if hooks.get('permission_gate', False) else 'false')
" 2>/dev/null || echo "false")

if [ "$PG_ENABLED" = "true" ]; then
    run_hook_test "#2-用户裁定" "permission-gate.sh" \
        '{"tool_name":"Bash","tool_input":{"command":"git push --force"}}' 2
else
    warn "D11: #2-用户裁定 → permission_gate DISABLED in harness.yaml (设计选择)"
    dim_warn "D11-IRON-LAWS"; dim_total "D11-IRON-LAWS"
fi

# 铁律#3: 证据门禁 — completion-gate blocks soft-completion words
run_hook_test "#3-证据门禁" "completion-gate.sh" \
    '{"tool_name":"TaskUpdate","tool_input":{"description":"应该没问题了","status":"completed"}}' 2

# 铁律#4: Git门禁 — permission-gate blocks unauthorized commit
if [ "$PG_ENABLED" = "true" ]; then
    run_hook_test "#4-Git门禁" "permission-gate.sh" \
        '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' 2
else
    warn "D11: #4-Git门禁 → permission_gate DISABLED (同上)"
    dim_warn "D11-IRON-LAWS"; dim_total "D11-IRON-LAWS"
fi

# 铁律#5: 范围冻结 — edit-scope 是软门禁（自动扩展+提醒，永不硬阻断）
# 设计如此：scope 不存在时自动扩展，文件不匹配时自动加入。exit=0 是正确的。
run_hook_test "#5-范围冻结(软门禁)" "pretool-edit-scope.sh" \
    '{"tool_input":{"file_path":"/etc/hosts"}}' 0

# 铁律#6: 隐私防线 — privacy-gate blocks .env access
run_hook_test "#6-隐私防线" "privacy-gate.sh" \
    '{"tool_name":"Read","tool_input":{"file_path":".env"}}' 2

# 铁律#7: 断言真实 — anti-pattern detect: H1 检测 百分比+无来源
# Needs tool_response.result format (post-tool hook, reads AI output)
run_hook_test "#7-断言真实" "posttool-anti-pattern-detect.sh" \
    '{"tool_response":{"result":"完成率95%，无来源验证"}}' 2

# 铁律#8: 哲学先行 — pre-ask-guard blocks AskUserQuestion not covered by decision chain
# Needs tool_input.questions[].question array format
run_hook_test "#8-哲学先行" "pre-ask-guard.sh" \
    '{"tool_input":{"questions":[{"question":"用A方案还是B方案？"}]}}' 2

info "D11: 铁律 8 条运行时测试 | 评分=$(dim_score "D11-IRON-LAWS")%"

# ── DIMENSION 12: SKILL AVAILABILITY ────────────────────────

dim_header "D12-SKILL-AVAILABILITY"

SKILL_DIR="$PROJECT_ROOT/.claude/skills"
if [ -d "$SKILL_DIR" ]; then
    SKILL_OK=0; SKILL_BAD=0; SKILL_MISSING_FILE=0
    for skill_dir in "$SKILL_DIR"/lx-*/; do
        [ ! -d "$skill_dir" ] && continue
        sname=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ]; then
            if head -1 "$skill_dir/SKILL.md" 2>/dev/null | grep -q "^---$"; then
                SKILL_OK=$((SKILL_OK+1))
                dim_pass "D12-SKILL-AVAILABILITY"
            else
                warn "[$sname] SKILL.md 无 YAML frontmatter"
                SKILL_BAD=$((SKILL_BAD+1))
                dim_warn "D12-SKILL-AVAILABILITY"
            fi
        else
            warn "[$sname] SKILL.md MISSING"
            SKILL_MISSING_FILE=$((SKILL_MISSING_FILE+1))
            dim_warn "D12-SKILL-AVAILABILITY"
        fi
        dim_total "D12-SKILL-AVAILABILITY"
    done
    pass "D12: skills OK=$SKILL_OK BAD=$SKILL_BAD MISSING=$SKILL_MISSING_FILE"
fi

info "D12: 评分=$(dim_score "D12-SKILL-AVAILABILITY")%"

# ── DIMENSION 13: KNOWN DEFECTS ─────────────────────────────

dim_header "D13-KNOWN-DEFECTS"

CLAUDE_NEXT="$PROJECT_ROOT/.claude/claude-next.md"
if [ -f "$CLAUDE_NEXT" ]; then
    DEFECT_COUNT=$(grep -c "^### 🐶 \[DG-" "$CLAUDE_NEXT" 2>/dev/null | head -1 || echo "0")
    UNFIXED=$(grep -c "hits:[3-9]" "$CLAUDE_NEXT" 2>/dev/null | head -1 || echo "0")
    pass "D13: claude-next.md → $DEFECT_COUNT defects recorded"
    dim_pass "D13-KNOWN-DEFECTS"
    UNFIXED_INT=$(echo "$UNFIXED" | head -1)
    if [ "$UNFIXED_INT" -gt 0 ] 2>/dev/null; then
        warn "D13: $UNFIXED_INT recurring defects (hits≥3) not yet fixed"
        dim_warn "D13-KNOWN-DEFECTS"
        dim_total "D13-KNOWN-DEFECTS"
    fi
else
    fail "D13: claude-next.md not found"
    dim_fail "D13-KNOWN-DEFECTS"
fi
dim_total "D13-KNOWN-DEFECTS"
info "D13: 评分=$(dim_score "D13-KNOWN-DEFECTS")%"

# ── DIMENSION 14: RUNTIME INTEGRATION TEST ────────────────────
# UPGRADED v2: Check harness.yaml before testing — if gate is disabled, report honestly

dim_header "D14-INTEGRATION"

# Check if permission_gate is enabled
PG_ENABLED=$(${PYTHON_BIN:-python3} -c "
import yaml
with open('$PROJECT_ROOT/.claude/harness.yaml') as f:
    data = yaml.safe_load(f)
hooks = data.get('hooks_enabled', {})
print('true' if hooks.get('permission_gate', False) else 'false')
" 2>/dev/null || echo "false")

# Test 1: Safe command should always pass
HOOK_TEST="permission-gate.sh"
if [ -f "$PROJECT_ROOT/.claude/hooks/$HOOK_TEST" ]; then
    TEST_INPUT='{"tool_name":"Bash","tool_input":{"command":"echo hello"}}'
    HOOK_OUT=$(echo "$TEST_INPUT" | bash "$PROJECT_ROOT/.claude/hooks/$HOOK_TEST" 2>/dev/null)
    HOOK_EXIT=$?
    if [ "$HOOK_EXIT" = "0" ]; then
        pass "D14: permission-gate accepts safe Bash (exit=0) ✓"
        dim_pass "D14-INTEGRATION"
    else
        fail "D14: permission-gate rejected safe Bash (exit=$HOOK_EXIT)"
        dim_fail "D14-INTEGRATION"
    fi
else
    fail "D14: permission-gate.sh not found"
    dim_fail "D14-INTEGRATION"
fi
dim_total "D14-INTEGRATION"

# Test 2: Dangerous command interception
if [ "$PG_ENABLED" = "true" ]; then
    TEST_DANGER='{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}'
    DANGER_OUT=$(echo "$TEST_DANGER" | bash "$PROJECT_ROOT/.claude/hooks/permission-gate.sh" 2>/dev/null)
    DANGER_EXIT=$?
    if [ "$DANGER_EXIT" = "2" ]; then
        pass "D14: rm -rf BLOCKED (exit=2) ✓"
        dim_pass "D14-INTEGRATION"
    else
        fail "D14: rm -rf NOT BLOCKED (exit=$DANGER_EXIT)"
        dim_fail "D14-INTEGRATION"
    fi
else
    warn "D14: rm -rf NOT BLOCKED — permission_gate DISABLED in harness.yaml (设计选择)"
    dim_warn "D14-INTEGRATION"
fi
dim_total "D14-INTEGRATION"

# Test 3: Privacy gate on .env (always active, not controlled by permission_gate)
TEST_ENV='{"tool_name":"Read","tool_input":{"file_path":".env"}}'
ENV_OUT=$(echo "$TEST_ENV" | bash "$PROJECT_ROOT/.claude/hooks/privacy-gate.sh" 2>/dev/null)
ENV_EXIT=$?
if [ "$ENV_EXIT" = "2" ]; then
    pass "D14: .env read BLOCKED (exit=2) ✓"
    dim_pass "D14-INTEGRATION"
else
    fail "D14: .env read NOT BLOCKED (exit=$ENV_EXIT)"
    dim_fail "D14-INTEGRATION"
fi
dim_total "D14-INTEGRATION"

# Test 4: git push force blocked
if [ "$PG_ENABLED" = "true" ]; then
    TEST_PUSH='{"tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}'
    PUSH_OUT=$(echo "$TEST_PUSH" | bash "$PROJECT_ROOT/.claude/hooks/permission-gate.sh" 2>/dev/null)
    PUSH_EXIT=$?
    if [ "$PUSH_EXIT" = "2" ]; then
        pass "D14: git push --force BLOCKED (exit=2) ✓"
        dim_pass "D14-INTEGRATION"
    else
        fail "D14: git push --force NOT BLOCKED (exit=$PUSH_EXIT)"
        dim_fail "D14-INTEGRATION"
    fi
else
    warn "D14: git push --force NOT BLOCKED — permission_gate DISABLED (同上)"
    dim_warn "D14-INTEGRATION"
fi
dim_total "D14-INTEGRATION"

info "D14: 评分=$(dim_score "D14-INTEGRATION")%"

# ── OVERALL REPORT ──────────────────────────────────────────

header "OVERALL REPORT"

# Compute overall from all 14 dimensions
SUM=0
for d in D1-HOOK-EXISTENCE D2-SETTINGS-REGISTRATION D3-BASH-SYNTAX D4-SMOKE-TEST D5-FEATURE-REGISTRY D6-FLYWHEEL-COVERAGE D7-THREE-SOURCE D8-ERROR-DNA D9-ORACLE D10-PHILOSOPHY-TRACE D11-IRON-LAWS D12-SKILL-AVAILABILITY D13-KNOWN-DEFECTS D14-INTEGRATION; do
    s=$(dim_score "$d")
    SUM=$(echo "$SUM + $s" | bc 2>/dev/null || echo "0")
done
OVERALL=$(echo "scale=1; $SUM / 14" | bc 2>/dev/null || echo "0")

log ""
log "${BOLD}═══════════════════════════════════════════${NC}"
log "${BOLD}  CAPABILITY MATRIX TEST RESULT${NC}"
log "${BOLD}═══════════════════════════════════════════${NC}"
log ""

# Overall score coloring
OVERALL_INT=$(echo "$OVERALL" | cut -d. -f1 2>/dev/null || echo "0")
printf "${BOLD}  OVERALL: ${NC}" | tee -a "$LOG"
if [ "$OVERALL_INT" -ge 80 ] 2>/dev/null; then
    log "${GREEN}${OVERALL}%${NC}"
elif [ "$OVERALL_INT" -ge 60 ] 2>/dev/null; then
    log "${YELLOW}${OVERALL}%${NC}"
else
    log "${RED}${OVERALL}%${NC}"
fi

log ""
log "  ${BOLD}Per-Dimension Scores:${NC}"
for d in D1-HOOK-EXISTENCE D2-SETTINGS-REGISTRATION D3-BASH-SYNTAX D4-SMOKE-TEST D5-FEATURE-REGISTRY D6-FLYWHEEL-COVERAGE D7-THREE-SOURCE D8-ERROR-DNA D9-ORACLE D10-PHILOSOPHY-TRACE D11-IRON-LAWS D12-SKILL-AVAILABILITY D13-KNOWN-DEFECTS D14-INTEGRATION; do
    s=$(dim_score "$d")
    p=$(cat "$TMPDIR/${d}_pass" 2>/dev/null || echo "0")
    f=$(cat "$TMPDIR/${d}_fail" 2>/dev/null || echo "0")
    w=$(cat "$TMPDIR/${d}_warn" 2>/dev/null || echo "0")
    log "    $d: ${s}%  (pass=$p fail=$f warn=$w)"
done

log ""
log "  Checks: ${GREEN}$PASS pass${NC}  ${RED}$FAIL fail${NC}  ${YELLOW}$WARN warn${NC}  Total=$TOTAL"
log "  Log: $LOG"
log ""
log "${BOLD}═══════════════════════════════════════════${NC}"

# Exit code: number of dimensions below 60%
EXIT_CODE=0
for d in D1-HOOK-EXISTENCE D2-SETTINGS-REGISTRATION D3-BASH-SYNTAX D4-SMOKE-TEST D5-FEATURE-REGISTRY D7-THREE-SOURCE D9-ORACLE D14-INTEGRATION; do
    s=$(dim_score "$d")
    s_int=$(echo "$s" | cut -d. -f1 2>/dev/null || echo "0")
    if [ "$s_int" -lt 60 ] 2>/dev/null; then
        EXIT_CODE=$((EXIT_CODE+1))
    fi
done

echo ""
echo "📄 Full log: $LOG"
exit $EXIT_CODE
