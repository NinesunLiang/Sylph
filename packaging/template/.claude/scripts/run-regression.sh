#!/usr/bin/env bash
# run-regression.sh — CarrorOS canonical full regression（自动发现现役测试树）
#
# 为什么需要 stash: 活体状态信号会污染门禁测试——
#   1. .omc/state/temp-bypass.json 存在时全部门禁降级 BYPASS_ALLOW
#   2. .omc/state/tokens/autonomous.active 存在时 goal 模式门禁降级 warn-only
#   3. .omc/state/tokens/lx-goal.json 存在时 goal 状态读取受真实任务影响
# 本脚本临时移出这些信号文件,trap EXIT 无条件还原(含 Ctrl-C/报错路径)。
#
# 用法: bash scripts/run-regression.sh
# 退出码: 0=全过, 1=有失败套件或环境异常

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"  # 位于 .claude/scripts/，上两级为仓库根
STATE="$PROJECT_ROOT/.omc/state"
TOKENS="$STATE/tokens"
BYPASS="$STATE/temp-bypass.json"
GOAL_SIGNAL="$TOKENS/autonomous.active"
GOAL_MODE="$TOKENS/lx-goal.json"
S1="/tmp/carros-regression.temp-bypass.stash"
S3="/tmp/carros-regression.goal-signal.stash"
S4="/tmp/carros-regression.goal-mode.stash"
M1=0; M3=0; M4=0

restore() {
  if [ "$M1" = "1" ] && [ -f "$S1" ]; then
    mv "$S1" "$BYPASS"
    echo "[restore] temp-bypass 已还原"
  fi
  if [ "$M3" = "1" ] && [ -f "$S3" ]; then
    mv "$S3" "$GOAL_SIGNAL"
    echo "[restore] autonomous.active 信号已还原"
  fi
  if [ "$M4" = "1" ] && [ -f "$S4" ]; then
    mv "$S4" "$GOAL_MODE"
    echo "[restore] lx-goal.json 已还原"
  fi
}
trap restore EXIT

if [ -f "$S1" ] || [ -f "$S3" ] || [ -f "$S4" ]; then
  echo "ERROR: 发现上次异常退出的 stash 残留($S1 $S3 $S4)" >&2
  exit 1
fi

if [ -f "$BYPASS" ]; then
  mv "$BYPASS" "$S1"
  M1=1
  echo "[stash] temp-bypass 移出(测试后自动还原)"
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

cd "$PROJECT_ROOT"

# ── canonical manifest：自动发现现役测试树（不引用已删除的占位测试） ──
TEST_FILES="$(
  find .claude/scripts .claude/skills .claude/hooks \
    \( -name 'test_*.py' -o -name 'test-*.py' -o -name 'test_*.sh' \) \
    2>/dev/null \
    | grep -v __pycache__ \
    | grep -v worktrees \
    | sort
)"

COUNT="$(printf '%s\n' "$TEST_FILES" | grep -c . || true)"
if [ -z "$TEST_FILES" ] || [ "$COUNT" = "0" ]; then
  echo "ERROR: 未发现任何测试文件" >&2
  exit 1
fi
echo "发现 $COUNT 个测试文件（canonical regression manifest）"

LOG="/tmp/carros-regression.pytest.log"
if python3 -m pytest $TEST_FILES -q >"$LOG" 2>&1; then
  PASSED="$(grep -oE '[0-9]+ passed' "$LOG" | grep -oE '[0-9]+' | head -1 || echo '?')"
  echo "PASS  全量回归（$COUNT 个文件，$PASSED 通过）"
  exit 0
else
  echo "FAIL  全量回归（$COUNT 个文件）— 日志: $LOG" >&2
  tail -40 "$LOG" >&2
  exit 1
fi
