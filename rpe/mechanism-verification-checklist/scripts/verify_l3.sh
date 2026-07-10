#!/usr/bin/env bash
# L3 Runtime Verification — compile checks + basic execution tests
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
WARN=0

pycheck() {
  local label="$1"
  local script="$2"
  local full="$ROOT/$script"

  if [ ! -f "$full" ]; then
    echo "WARN $label — file missing: $script"
    WARN=$((WARN + 1))
    return
  fi

  if python3 -m py_compile "$full" 2>/dev/null; then
    echo "PASS $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL $label — compile error"
    FAIL=$((FAIL + 1))
  fi
}

hooktest() {
  local label="$1"
  local script="$2"
  local input="${3:-'{"tool_name":"Bash","tool_input":{"command":"echo test"}}'}"
  local full="$ROOT/$script"

  if [ ! -f "$full" ]; then
    echo "WARN $label — file missing: $script"
    WARN=$((WARN + 1))
    return
  fi

  local out
  if out=$(echo "$input" | python3 "$full" 2>&1); then
    echo "PASS $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL $label — runtime error: $(echo "$out" | head -1)"
    FAIL=$((FAIL + 1))
  fi
}

echo "============================================"
echo " L3 Runtime Verification"
echo " Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================"
echo ""

# ── 1. Core scripts compile check ──
echo "── 1. Core Scripts Compile ──"
for script in \
  ".claude/scripts/carros_base.py" \
  ".claude/scripts/carros_utils.py" \
  ".claude/scripts/verify_gate.py" \
  ".claude/scripts/archive_engine.py" \
  ".claude/scripts/context_engine.py" \
  ".claude/scripts/fallback_engine.py" \
  ".claude/scripts/omc_lint.py" \
  ".claude/scripts/statusline.py" \
  ".claude/scripts/context_watermark.py" \
  ".claude/scripts/fallback_matrix.py" \
  ".claude/scripts/oracle_engine.py" \
  ".claude/scripts/output_compress.py" \
  ".claude/scripts/plan_builder.py"; do
  pycheck "compile:$(basename $script)" "$script"
done

# ── 2. Hook scripts compile check ──
echo "── 2. Hook Scripts Compile ──"
for script in .claude/hooks/*.py; do
  pycheck "compile:$(basename $script)" "$script"
done

# ── 3. Hook runtime test ──
echo "── 3. Hook Runtime Test ──"
hooktest "runtime:pretool-gate.py" ".claude/hooks/pretool-gate.py"
hooktest "runtime:posttool-completion-gate.py" ".claude/hooks/posttool-completion-gate.py" '{"response":"test OK"}'
hooktest "runtime:posttool-audit.py" ".claude/hooks/posttool-audit.py"
hooktest "runtime:userprompt-prompt-collector.py" ".claude/hooks/userprompt-prompt-collector.py" '{"prompt":"test"}'

# ── 4. carros_base.py --help ──
echo "── 4. carros_base.py --help ──"
if python3 .claude/scripts/carros_base.py --help >/dev/null 2>&1; then
  echo "PASS carros_base.py --help"
  PASS=$((PASS + 1))
else
  echo "WARN carros_base.py --help — may need args"
  WARN=$((WARN + 1))
fi

# ── 5. omc_lint.py ──
echo "── 5. omc_lint.py ──"
if python3 .claude/scripts/omc_lint.py 2>&1; then
  echo "PASS omc_lint.py"
  PASS=$((PASS + 1))
else
  echo "WARN omc_lint.py — may have lint findings (non-zero exit ok)"
  WARN=$((WARN + 1))
fi

# ── Summary ──
echo ""
echo "============================================"
echo " L3 Runtime Verification Results"
echo "============================================"
echo " TOTAL: $((PASS + FAIL + WARN))"
echo " PASS:  $PASS"
echo " FAIL:  $FAIL"
echo " WARN:  $WARN"
echo "============================================"
exit $FAIL
