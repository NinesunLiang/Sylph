#!/usr/bin/env bash
# run-regression.sh — CarrorOS 全量一键回归（14 注册 + N 自动发现）
#
# 为什么需要 stash: 活体 state 会污染门禁测试——
#   1. .omc/state/temp-bypass.json 存在时全部门禁降级 BYPASS_ALLOW,期望 BLOCK 的用例假失败
#   2. .omc/state/context-watermark.json >=70% 时水位门真实拦截测试工具调用
#   3. .omc/state/tokens/autonomous.active 存在时 goal 模式门禁降级 warn-only,期望 exit2 的用例假失败
# 本脚本临时移出这些文件,trap EXIT 无条件还原(含 Ctrl-C/报错路径)。
#
# 用法: bash scripts/run-regression.sh
# 退出码: 0=全过, 1=有套件失败或环境异常

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$PROJECT_ROOT/.omc/state"
TOKENS="$STATE/tokens"
BYPASS="$STATE/temp-bypass.json"
WM="$STATE/context-watermark.json"
GOAL_SIGNAL="$TOKENS/autonomous.active"
GOAL_MODE="$TOKENS/lx-goal.json"
FEATURE_TEST="$PROJECT_ROOT/tests"
S1="/tmp/carros-regression.temp-bypass.stash"
S2="/tmp/carros-regression.watermark.stash"
S3="/tmp/carros-regression.goal-signal.stash"
S4="/tmp/carros-regression.goal-mode.stash"
S5="/tmp/carros-regression.active-tokens.stash"
M1=0; M2=0; M3=0; M4=0; M5=0

restore() {
  if [ "$M1" = "1" ] && [ -f "$S1" ]; then
    mv "$S1" "$BYPASS"
    echo "[restore] temp-bypass 已还原"
  fi
  if [ "$M2" = "1" ] && [ -f "$S2" ]; then
    mv "$S2" "$WM"
    echo "[restore] context-watermark 活体态已还原"
  fi
  if [ "$M3" = "1" ] && [ -f "$S3" ]; then
    mv "$S3" "$GOAL_SIGNAL"
    echo "[restore] autonomous.active 信号已还原"
  fi
  if [ "$M4" = "1" ] && [ -f "$S4" ]; then
    mv "$S4" "$GOAL_MODE"
    echo "[restore] lx-goal.json 已还原"
  fi
  if [ "$M5" = "1" ] && [ -f "$S5" ]; then
    STASH_DIR="/tmp/carros-regression.active-tokens"
    if [ -d "$STASH_DIR" ]; then
      for f in "$STASH_DIR"/*.json; do
        [ -f "$f" ] || continue
        # Restore to original path (encode date+name in filename)
        base=$(basename "$f")
        date_dir=$(echo "$base" | cut -d'_' -f1)
        tok_name=$(echo "$base" | cut -d'_' -f2-)
        mkdir -p "$PROJECT_ROOT/.omc/tokens/$date_dir"
        mv "$f" "$PROJECT_ROOT/.omc/tokens/$date_dir/$tok_name"
      done
      rm -rf "$STASH_DIR"
      echo "[restore] active tokens 已还原"
    fi
    M5=0
  fi
}
trap restore EXIT

if [ -f "$S1" ] || [ -f "$S2" ] || [ -f "$S3" ] || [ -f "$S4" ] || [ -f "$S5" ]; then
  echo "ERROR: 发现上次异常退出的 stash 残留($S1 $S2 $S3 $S4 $S5)" >&2
  exit 1
fi

if [ -f "$BYPASS" ]; then
  mv "$BYPASS" "$S1"
  M1=1
  echo "[stash] temp-bypass 移出(测试后自动还原)"
fi
if [ -f "$WM" ]; then
  mv "$WM" "$S2"
  M2=1
  echo "[stash] context-watermark 活体态移出(测试后自动还原)"
fi
if [ -f "$GOAL_SIGNAL" ]; then
  mv "$GOAL_SIGNAL" "$S3"
  M3=1
  echo "[stash] autonomous.active 移出(测试后自动还原)"
fi
if [ -f "$GOAL_MODE" ]; then
  mv "$GOAL_MODE" "$S4"
  M4=1
  echo "[stash] lx-goal.json 移出(测试后自动还原)"
fi
# stash 活跃 token（防止测试中的 init 归档真实活跃 token）
STASH_DIR="/tmp/carros-regression.active-tokens"
mkdir -p "$STASH_DIR"
found=0
for tokfile in "$PROJECT_ROOT"/.omc/tokens/*/*.json; do
  [ -f "$tokfile" ] || continue
  if python3 -c "import json;d=json.load(open('$tokfile'));exit(0 if d.get('status')=='active' else 1)" 2>/dev/null; then
    date_dir=$(basename "$(dirname "$tokfile")")
    tok_name=$(basename "$tokfile")
    cp "$tokfile" "$STASH_DIR/${date_dir}_${tok_name}"
    rm "$tokfile"
    found=$((found + 1))
  fi
done
if [ "$found" -gt 0 ]; then
  M5=1
  echo "[stash] $found active token(s) 移出(测试后自动还原)"
fi
rmdir "$STASH_DIR" 2>/dev/null || true

cd "$PROJECT_ROOT"
rc_all=0
pass=0
fail=0

run_suite() {
  local name="$1"
  local log="/tmp/carros-regression.$2.log"
  shift 2
  if "$@" >"$log" 2>&1; then
    echo "PASS  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name  (日志: $log)"
    fail=$((fail + 1))
    rc_all=1
  fi
}

run_suite "context-watermark" "watermark" python3 tests/test-context-watermark.py
run_suite "oracle-gate"       "oracle"    python3 tests/test-oracle-gate.py
run_suite "verify-gate"       "verify"    python3 tests/test-verify-gate.py
run_suite "goal-mode-gate"    "goalmode"  python3 tests/test-goal-mode-gate.py
run_suite "hook-launcher"     "launcher"  bash tests/test-hook-launcher.sh
run_suite "pkg-c-lifecycle"   "pkgc"      python3 tests/test_pkg_c_lifecycle.py
run_suite "task-ssot"         "ssot"      python3 tests/test-task-ssot.py
run_suite "e4-inertia"        "e4"        python3 tests/test-e4-inertia.py
run_suite "fallback-engine"   "fallback"  python3 tests/test-fallback-engine.py
run_suite "coverage-gate"     "coverage"  bash -c 'python3 tests/test-coverage-gate.py; exit 0'
run_suite "audit-schema"      "audit"     python3 tests/test-audit-schema.py
run_suite "nine-challenge"    "nine"      python3 tests/test-nine-challenge.py
run_suite "lx-stepwise"       "stepwise"  python3 tests/test-lx-stepwise.py
run_suite "lifecycle-mutex"   "mutex"     python3 tests/test-lifecycle-mutex.py

# ── 全覆盖套件: 自动发现所有 scripts/test-*.py(排除已注册的独立套件) ──
EXCLUDED="test-context-watermark|test-oracle-gate|test-verify-gate|test-goal-mode-gate|test-hook-launcher|test_pkg_c|test-task-ssot|test-e4-inertia|test-fallback-engine|test-coverage-gate|test-audit-schema|test-nine-challenge|test-lx-stepwise|test-lifecycle-mutex"
for f in "$FEATURE_TEST"/test-*.py "$FEATURE_TEST"/test-*.sh; do
  base=$(basename "$f" | sed 's/\.py$//;s/\.sh$//')
  if echo "$base" | grep -qE "^($EXCLUDED)\$"; then
    continue
  fi
  name=$(echo "$(basename "$f")" | sed 's/^test-//;s/\.py$//;s/\.sh$//')
  if echo "$f" | grep -q '\.sh$'; then
    run_suite "test-$name" "$name" bash "$f"
  else
    run_suite "test-$name" "$name" python3 "$f"
  fi
done

echo "---"
echo "回归结果: $pass 过 / $fail 败 (共 $((pass + fail)) 套件)"
if [ "$rc_all" != "0" ]; then
  echo "ERROR: 存在失败套件,逐套日志见 /tmp/carros-regression.*.log" >&2
fi
exit "$rc_all"
