#!/usr/bin/env bash
# run_tests.sh — CarrorOS 全量测试入口
# 同时运行两种测试格式：自定义 runner (test-*.py) 和 pytest 格式 (test_*.py)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
FAILED_FILES=""
TIMEOUT=120

echo "========================================="
echo " CarrorOS Test Runner"
echo "========================================="
echo ""

# ── Phase 1: 自定义 runner (test-*.py) ──
echo "--- 自定义测试脚本 (test-*.py) ---"
for f in tests/test-*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    printf "  %-40s " "$name"
    start=$(date +%s)
    if python3 "$f" 2>&1; then
        PASS=$((PASS + 1))
        elapsed=$(( $(date +%s) - start ))
        echo "  ✅ (${elapsed}s)"
    else
        FAIL=$((FAIL + 1))
        elapsed=$(( $(date +%s) - start ))
        echo "  ❌ (${elapsed}s)"
        FAILED_FILES="$FAILED_FILES $name"
    fi
done

# ── Phase 2: pytest 格式 (test_*.py) ──
echo ""
echo "--- pytest 格式 (test_*.py) ---"
if python3 -m pytest tests/test_*.py -q --tb=short --no-header 2>&1; then
    echo "  ✅ pytest 全部通过"
else
    rc=$?
    echo "  ❌ pytest 有失败 (exit=$rc)"
    FAIL=$((FAIL + rc))
    FAILED_FILES="$FAILED_FILES pytest(test_*.py)"
fi

# ── 汇总 ──
echo ""
echo "========================================="
echo " 结果: $PASS 通过, $FAIL 失败"
if [ -n "$FAILED_FILES" ]; then
    echo " 失败文件:$FAILED_FILES"
fi
echo "========================================="
exit $(( FAIL > 0 ? 1 : 0 ))
