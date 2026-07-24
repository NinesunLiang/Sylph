#!/usr/bin/env bash
# run-regression.sh — CarrorOS 六套件一键回归
#
# 为什么需要 stash: 活体 state 会污染门禁测试——
#   1. .omc/state/temp-bypass.json 存在时全部门禁降级 BYPASS_ALLOW,期望 BLOCK 的用例假失败
#   2. .omc/state/context-watermark.json >=70% 时水位门真实拦截测试工具调用
# 本脚本临时移出这两个文件,trap EXIT 无条件还原(含 Ctrl-C/报错路径)。
#
# 用法: bash scripts/run-regression.sh
# 退出码: 0=全过, 1=有套件失败或环境异常

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$PROJECT_ROOT/.omc/state"
BYPASS="$STATE/temp-bypass.json"
WM="$STATE/context-watermark.json"
S1="/tmp/carros-regression.temp-bypass.stash"
S2="/tmp/carros-regression.watermark.stash"
M1=0
M2=0

restore() {
  if [ "$M1" = "1" ] && [ -f "$S1" ]; then
    mv "$S1" "$BYPASS"
    echo "[restore] temp-bypass 已还原"
  fi
  if [ "$M2" = "1" ] && [ -f "$S2" ]; then
    mv "$S2" "$WM"
    echo "[restore] context-watermark 活体态已还原"
  fi
}
trap restore EXIT

if [ -f "$S1" ] || [ -f "$S2" ]; then
  echo "ERROR: 发现上次异常退出的 stash 残留($S1 / $S2)" >&2
  echo "  请先人工核对: 若 .omc/state/ 下对应文件缺失,把 stash mv 回去;否则删 stash" >&2
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

run_suite "context-watermark" "watermark" python3 scripts/test-context-watermark.py
run_suite "oracle-gate"       "oracle"    python3 scripts/test-oracle-gate.py
run_suite "verify-gate"       "verify"    python3 scripts/test-verify-gate.py
run_suite "goal-mode-gate"    "goalmode"  python3 scripts/test-goal-mode-gate.py
run_suite "hook-launcher"     "launcher"  bash scripts/test-hook-launcher.sh
run_suite "pkg-c-lifecycle"   "pkgc"      python3 .claude/hooks/tests/test_pkg_c_lifecycle.py

echo "---"
echo "回归结果: $pass 过 / $fail 败 (共 $((pass + fail)) 套件)"
if [ "$rc_all" != "0" ]; then
  echo "ERROR: 存在失败套件,逐套日志见 /tmp/carros-regression.*.log" >&2
fi
exit "$rc_all"
