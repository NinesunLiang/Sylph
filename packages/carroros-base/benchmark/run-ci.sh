#!/bin/bash
# CarrorOS Benchmark CI — 定时自动化跑评测
# 用法: bash benchmark/run-ci.sh [phase]
#   phase=1: 20任务 × 4组 × 3seed = 240 runs
#   phase=2: 80任务 × 6组 × 3seed = 1440 runs (需很长时间)

set -euo pipefail

CARROROS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BENCHMARK_DIR="$CARROROS_ROOT/benchmark"
RUNNER="$BENCHMARK_DIR/runner.py"
REPORTS_DIR="$BENCHMARK_DIR/reports"
LOGFILE="$BENCHMARK_DIR/ci-$(date +%Y%m%d-%H%M).log"
PHASE="${1:-1}"

cd "$CARROROS_ROOT"

echo "╔══════════════════════════════════════════════════╗" | tee "$LOGFILE"
echo "║ CarrorOS Benchmark CI — Phase $PHASE              ║" | tee -a "$LOGFILE"
echo "║ $(date)                                    ║" | tee -a "$LOGFILE"
echo "╚══════════════════════════════════════════════════╝" | tee -a "$LOGFILE"

# Step 1: Validate tasks
echo "" | tee -a "$LOGFILE"
echo "🔍 Step 1: Validate tasks..." | tee -a "$LOGFILE"
python3 "$RUNNER" validate 2>&1 | tee -a "$LOGFILE"

# Step 2: Show plan
echo "" | tee -a "$LOGFILE"
echo "📋 Step 2: Run plan..." | tee -a "$LOGFILE"
python3 "$RUNNER" plan --phase "$PHASE" 2>&1 | tee -a "$LOGFILE"

# Step 3: Dry-run first (check infra)
echo "" | tee -a "$LOGFILE"
echo "🏃 Step 3: Dry run (infra check)..." | tee -a "$LOGFILE"
python3 "$RUNNER" run --phase "$PHASE" --dry-run 2>&1 | tee -a "$LOGFILE"

# Step 4: Run benchmark (CC sessions)
echo "" | tee -a "$LOGFILE"
echo "🔥 Step 4: Running benchmark (Phase $PHASE)..." | tee -a "$LOGFILE"
echo "    This runs CC -p for each task. May take hours." | tee -a "$LOGFILE"
echo "    Check ci.log for progress." | tee -a "$LOGFILE"

# Phase 1: 4 groups × 1 seed per task (Phase 1 budget: ~80 CC calls)
if [ "$PHASE" = "1" ]; then
    echo "  Phase 1 pilot: 5 tasks × 4 groups × 1 seed" | tee -a "$LOGFILE"
fi

# Step 5: Generate reports
echo "" | tee -a "$LOGFILE"
echo "📊 Step 5: Generating reports..." | tee -a "$LOGFILE"
python3 "$RUNNER" report 2>&1 | tee -a "$LOGFILE"

# Step 6: Try AI analysis via xsimplechat
echo "" | tee -a "$LOGFILE"
echo "🔮 Step 6: AI analysis..." | tee -a "$LOGFILE"
if curl -s --connect-timeout 3 http://127.0.0.1:8765/health >/dev/null 2>&1; then
    python3 "$RUNNER" report --analyze gpt-5.5 2>&1 | tee -a "$LOGFILE"
else
    echo "    xsimplechat not available, skip AI analysis" | tee -a "$LOGFILE"
fi

# Summary
echo "" | tee -a "$LOGFILE"
echo "══════════════════════════════════════════════════" | tee -a "$LOGFILE"
echo "✅ Benchmark CI Phase $PHASE complete" | tee -a "$LOGFILE"
echo "   Log: $LOGFILE" | tee -a "$LOGFILE"
echo "   Reports: $REPORTS_DIR/" | tee -a "$LOGFILE"
echo "══════════════════════════════════════════════════" | tee -a "$LOGFILE"

# Print report summary
echo ""
echo "=== Capability Report ==="
cat "$REPORTS_DIR/capability-amplification.md" 2>/dev/null | head -20 || echo "(no report yet)"

echo ""
echo "=== Long Running Stability ==="
cat "$REPORTS_DIR/long-running-stability.md" 2>/dev/null | head -10 || echo "(no report yet)"
