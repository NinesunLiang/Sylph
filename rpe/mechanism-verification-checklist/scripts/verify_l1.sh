#!/usr/bin/env bash
# L1 Static Integrity Verification — CarrorOS Core Mechanisms
# Checks: file/directory existence, basic structure
# Output: PASS/FAIL/WARN per check item

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
WARN=0
RESULTS=""

check() {
  local label="$1"
  local path="$2"
  local kind="${3:-file}"  # file | dir | any
  local full_path="$ROOT/$path"

  if [ "$kind" = "dir" ]; then
    if [ -d "$full_path" ]; then
      RESULTS+="PASS $label"$'\n'
      PASS=$((PASS + 1))
    else
      RESULTS+="FAIL $label — dir missing: $path"$'\n'
      FAIL=$((FAIL + 1))
    fi
  elif [ "$kind" = "any" ]; then
    if [ -e "$full_path" ]; then
      RESULTS+="PASS $label"$'\n'
      PASS=$((PASS + 1))
    else
      RESULTS+="WARN $label — missing: $path"$'\n'
      WARN=$((WARN + 1))
    fi
  else
    if [ -f "$full_path" ]; then
      RESULTS+="PASS $label"$'\n'
      PASS=$((PASS + 1))
    else
      RESULTS+="FAIL $label — file missing: $path"$'\n'
      FAIL=$((FAIL + 1))
    fi
  fi
}

echo "============================================"
echo " L1 Static Integrity Verification"
echo " CarrorOS Core Mechanisms"
echo " Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================"
echo ""

# ── 1. Core Entry Points ──
echo "── 1. Core Entry Points ──"
check "AGENTS.md"            "AGENTS.md"
check "CLAUDE.md"            "CLAUDE.md"
check "kernel.md"            ".claude/kernel.md"
check "index.md"             ".claude/index.md"
check "session-handoff.md"   ".claude/session-handoff.md"

# ── 2. Hook System ──
echo "── 2. Hook System ──"
check "hook-launcher.sh"     ".claude/hooks/hook-launcher.sh"
check "carroros_hooklib.py"  ".claude/hooks/carroros_hooklib.py"
check "pretool-gate.py"      ".claude/hooks/pretool-gate.py"
check "posttool-audit.py"    ".claude/hooks/posttool-audit.py"
check "posttool-completion-gate.py" ".claude/hooks/posttool-completion-gate.py"
check "userprompt-prompt-collector.py" ".claude/hooks/userprompt-prompt-collector.py"

# ── 3. Settings & Config ──
echo "── 3. Settings & Config ──"
check "settings.json"        ".claude/settings.json"
check "settings.local.json"  ".claude/settings.local.json"
check "harness.yaml"         ".claude/harness.yaml"

# ── 4. Core Scripts ──
echo "── 4. Core Scripts (L1) ──"
check "carros_base.py"       ".claude/scripts/carros_base.py"
check "carros_utils.py"      ".claude/scripts/carros_utils.py"
check "verify_gate.py"       ".claude/scripts/verify_gate.py"
check "archive_engine.py"    ".claude/scripts/archive_engine.py"
check "context_engine.py"    ".claude/scripts/context_engine.py"
check "fallback_engine.py"   ".claude/scripts/fallback_engine.py"
check "omc_lint.py"          ".claude/scripts/omc_lint.py"
check "statusline.py"        ".claude/scripts/statusline.py"

# ── 5. L2 Scripts (Enhance) ──
echo "── 5. L2 Scripts (Enhance) ──"
check "oracle_engine.py"     ".claude/scripts/oracle_engine.py"     any
check "context_watermark.py" ".claude/scripts/context_watermark.py" any
check "fallback_matrix.py"   ".claude/scripts/fallback_matrix.py"   any

# ── 6. Skills (core) ──
echo "── 6. Core Skills ──"
for skill in lx-goal lx-task-spec lx-rpe lx-code-review lx-git-check lx-varlock lx-validate-skill lx-dogfood; do
  check "skill:$skill" ".claude/skills/$skill/SKILL.md"
done

# ── 7. Skills (enhance/optional) ──
echo "── 7. Optional Skills ──"
for skill in lx-ghost lx-oracle-agent lx-oracle-meta lx-oracle-review lx-learner lx-root-cause-analysis lx-skillify lx-brave-recovery; do
  check "skill:$skill" ".claude/skills/$skill/SKILL.md" any
done

# ── 8. OMA Skills ──
echo "── 8. OMA Skills ──"
for skill in lx-oma-gov lx-oma-hier lx-oma-orch lx-oma-split; do
  check "oma:$skill" ".claude/skills/$skill/SKILL.md" any
done

# ── 9. Rules ──
echo "── 9. Governance Rules ──"
check "terminal-safety.md"   ".claude/rules/terminal-safety.md"
check "bash-style.md"        ".claude/rules/bash-style.md"

# ── 10. References ──
echo "── 10. Reference Docs ──"
check "SUBAGENT.md"          ".claude/references/SUBAGENT.md"
check "philosophy.md"        ".claude/references/philosophy.md"
check "anti-patterns.md"     ".claude/references/anti-patterns.md"
check "feature-registry.yaml" ".claude/references/feature-registry.yaml"

# ── 11. Runtime Structure ──
echo "── 11. Runtime Directories ──"
check ".omc/"                ".omc"                dir
check ".omc/audit"           ".omc/audit"          dir
check ".omc/state"           ".omc/state"          dir
check ".omc/tokens"          ".omc/tokens"         dir
check ".omc/archive"         ".omc/archive"        dir

# ── 12. Schemas ──
echo "── 12. Schemas ──"
check "registry.yaml"        ".claude/schemas/registry.yaml"
check "token.schema.json"    ".claude/schemas/token.schema.json"

# ── Summary ──
echo ""
echo "============================================"
echo " L1 Verification Results"
echo "============================================"
echo "$RESULTS"
echo "────────────────────────────────────────────"
echo " TOTAL: $((PASS + FAIL + WARN)) checks"
echo " PASS:  $PASS"
echo " FAIL:  $FAIL"
echo " WARN:  $WARN"
echo "============================================"

exit $FAIL
