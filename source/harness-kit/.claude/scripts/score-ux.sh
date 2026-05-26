#!/usr/bin/env bash
# score-ux.sh — Meta-Oracle UX 维度独立评分脚本
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# Role: 对 UX（用户体验）5 个子维度进行独立评分，满分 10 分
#       UX 独立参与打分，不影响 C/E/G 的 8.6/10 总阈值判定
#
# 使用: bash .claude/scripts/score-ux.sh [--json]
# 输出: .omc/state/score-ux-<timestamp>.json
#
# 5 个子维度（各 2 分）:
#   UX1 心智负担 — AI 输出的决策点密度与复杂度
#   UX2 交互次数 — 用户完成任务的必要交互频率
#   UX3 信息清晰度 — 输出结构化程度与格式一致性
#   UX4 错误可理解性 — 错误信息的可操作性与分类覆盖
#   UX5 自主模式顺畅度 — goal/ghost 模式是否无打断运行
#
# 评分方法: 配置存在性(1分) + 运行时验证(1分) = 每子维度满分 2 分

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
TS=$(date -u +%Y%m%d-%H%M%S)
OUTPUT_FILE="$PROJECT_ROOT/.omc/state/score-ux-$TS.json"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# ───── 辅助函数 ─────
pct() { echo "scale=1; $1 * 100 / $2" | bc 2>/dev/null || echo "0"; }

# 运行时数据存在性检查
has_runtime_data() {
  local file="$1"
  [ -f "$file" ] && [ -s "$file" ] && return 0 || return 1
}

# ───── 子维度检测函数 ─────
# 每个函数输出: <score_0_to_2> 2 <UXn=描述(详情)>

# UX1 心智负担 (2分) — AI 输出中的决策点密度与复杂度
score_UX1() {
  local score=0 max=2
  local config_ok=0 runtime_ok=0

  # 配置存在性 (1分): 决策链文档 + 方向指引机制
  if [ -f .claude/reference/autonomous-decision-chain.md ]; then
    config_ok=1
  fi

  # 运行时验证 (1分): 检查 session-turns.json 中轮次是否受控
  if has_runtime_data "$STATE_DIR/session-turns.json"; then
    local turns
    turns=$(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$STATE_DIR/session-turns.json')).get('count', 0))" 2>/dev/null || echo "999")
    turns="${turns:-999}"
    # 当前会话轮次 < 100 → 心智负担可控
    if [ "$turns" -lt 100 ] 2>/dev/null; then
      runtime_ok=1
    fi
  fi

  score=$(( config_ok + runtime_ok ))
  echo "$score $max UX1=心智负担(decision_chain=${config_ok} turns_ok=${runtime_ok})"
}

# UX2 交互次数 (2分) — 用户完成任务的必要交互频率
score_UX2() {
  local score=0 max=2
  local config_ok=0 runtime_ok=0

  # 配置存在性 (1分): 自主模式支持 (goal/ghost scripts)
  if [ -f .claude/skills/lx-goal/scripts/lx-goal.sh ] && \
     [ -f .claude/skills/lx-ghost/scripts/lx-ghost.sh ]; then
    config_ok=1
  fi

  # 运行时验证 (1分): check if autonomous mode infrastructure is in place
  if grep -q 'is_mode_active' .claude/hooks/harness_config.sh 2>/dev/null; then
    runtime_ok=1
  fi

  score=$(( config_ok + runtime_ok ))
  echo "$score $max UX2=交互次数(autonomous_support=${config_ok} meta_oracle_active=${runtime_ok})"
}

# UX3 信息清晰度 (2分) — 输出结构化程度与格式一致性
score_UX3() {
  local score=0 max=2
  local config_ok=0 runtime_ok=0

  # 配置存在性 (1分): 证据格式门禁 + 反模式文档
  if grep -q 'evidence.*level\|证据层级\|L1.*L2.*L3' AGENTS.md 2>/dev/null; then
    if [ -f .claude/anti-patterns.md ]; then
      config_ok=1
    fi
  fi

  # 运行时验证 (1分): completion-gate 实际拦截过软完成语
  if has_runtime_data "$STATE_DIR/error-signals.jsonl"; then
    if grep -q 'SOFT_WORD\|soft_completion\|虚假完成' "$STATE_DIR/error-signals.jsonl" 2>/dev/null; then
      runtime_ok=1
    fi
  fi
  # 备选: 检查 completion-gate 有 VERIFIED 格式强制
  if [ "$runtime_ok" = "0" ]; then
    if grep -qE 'VERIFIED|证据门禁|evidence.*missing' .claude/hooks/completion-gate.sh 2>/dev/null; then
      runtime_ok=1
    fi
  fi

  score=$(( config_ok + runtime_ok ))
  echo "$score $max UX3=信息清晰度(evidence_fmt=${config_ok} completion_gate=${runtime_ok})"
}

# UX4 错误可理解性 (2分) — 错误信息的可操作性与分类覆盖
score_UX4() {
  local score=0 max=2
  local config_ok=0 runtime_ok=0

  # 配置存在性 (1分): error-dna 分类 + RCA 机制
  if grep -q 'error-dna\|error_classifier' .claude/settings.json 2>/dev/null; then
    if grep -qE 'RCA|根因' .claude/hooks/completion-gate.sh 2>/dev/null; then
      config_ok=1
    fi
  fi

  # 运行时验证 (1分): error-dna.json 有实际分类记录
  if has_runtime_data "$STATE_DIR/error-dna.json"; then
    local classified
    classified=$(${PYTHON_BIN:-python3} -c "
import json
try:
    d = json.load(open('$STATE_DIR/error-dna.json'))
    patterns = d.get('patterns', d) if isinstance(d, dict) else {}
    print(len(patterns))
except: print(0)
" 2>/dev/null || echo "0")
    classified="${classified:-0}"
    if [ "$classified" -ge 1 ] 2>/dev/null; then
      runtime_ok=1
    fi
  fi

  score=$(( config_ok + runtime_ok ))
  echo "$score $max UX4=错误可理解性(error_dna=${config_ok} classified=${runtime_ok})"
}

# UX5 自主模式顺畅度 (2分) — goal/ghost 模式是否无打断运行
score_UX5() {
  local score=0 max=2
  local config_ok=0 runtime_ok=0

  # 配置存在性 (1分): 自主模式 hook 降级机制
  if grep -q 'is_mode_active' .claude/hooks/harness_config.sh 2>/dev/null; then
    # 检查至少 3 个 hook 在自主模式下降级
    local degraded=0
    grep -q 'is_mode_active' .claude/hooks/completion-gate.sh 2>/dev/null && degraded=$((degraded+1))
    grep -q 'is_mode_active' .claude/hooks/subagent-guard.sh 2>/dev/null && degraded=$((degraded+1))
    grep -q 'is_mode_active' .claude/hooks/edit-guard.sh 2>/dev/null && degraded=$((degraded+1))
    grep -q 'is_mode_active' .claude/hooks/pretool-retry-check.sh 2>/dev/null && degraded=$((degraded+1))
    [ "$degraded" -ge 3 ] && config_ok=1
  fi

  # 运行时验证 (1分): autonomous.active 存在 + subagent-usage 有实际调用
  if [ -f "$STATE_DIR/tokens/autonomous.active" ]; then
    if has_runtime_data "$STATE_DIR/subagent-usage.jsonl"; then
      local agent_calls
      agent_calls=$(wc -l < "$STATE_DIR/subagent-usage.jsonl" 2>/dev/null | tr -d ' ')
      agent_calls="${agent_calls:-0}"
      # 自主模式下有 agent 调用记录 → 实际在使用
      [ "$agent_calls" -ge 1 ] 2>/dev/null && runtime_ok=1
    else
      # 备选: 仅检查信号文件存在（当前会话正在自主模式）
      runtime_ok=1
    fi
  fi

  score=$(( config_ok + runtime_ok ))
  echo "$score $max UX5=自主模式顺畅度(degraded_hooks=${config_ok} autonomous_active=${runtime_ok})"
}

# ───── 执行评分 ─────
echo "=== Meta-Oracle UX Score @ $TS ==="
echo ""

# 使用 indexed arrays (bash 3.2 兼容)
ux_labels="UX1 UX2 UX3 UX4 UX5"
total_score=0 total_max=0
label_idx=0
subscores_json=""
metrics_json=""

for label in $ux_labels; do
  echo -n "  $label "
  result=$(score_${label})
  echo "$result"

  s=$(echo "$result" | awk '{print $1}')
  m=$(echo "$result" | awk '{print $2}')
  detail=$(echo "$result" | cut -d' ' -f4-)

  total_score=$(( total_score + s ))
  total_max=$(( total_max + m ))

  # 构建 JSON 片段（边执行边拼装）
  [ -n "$subscores_json" ] && subscores_json="$subscores_json,"
  subscores_json="$subscores_json\"$label\":{\"score\":$s,\"max\":$m,\"pct\":$(pct $s $m)}"

  [ -n "$metrics_json" ] && metrics_json="$metrics_json,"
  metrics_json="$metrics_json\"$label\":\"$detail\""

  label_idx=$(( label_idx + 1 ))
done

PCT=$(pct $total_score $total_max)

echo ""
echo "---"
echo "UX 总分: $total_score/$total_max ($PCT%)"
echo "UX 状态: 独立维度 — 不参与 C/E/G 的 8.6/10 总阈值判定"
echo "---"

# ───── JSON 输出 ─────
# subscores_json 和 metrics_json 已在评分循环中构建
RESULT=$(cat <<JSONEOF
{
  "generated_at": "$TS",
  "scored_by": "score-ux.sh v1",
  "methodology": "5 sub-dimensions x 2pts — config existence (1pt) + runtime verification (1pt)",
  "dimension": "UX",
  "description": "用户体验独立评分 — 不参与 C/E/G 总阈值判定",
  "total": { "score": $total_score, "max": $total_max, "pct": $PCT },
  "subscores": { $subscores_json },
  "metrics": { $metrics_json },
  "independence_note": "UX 维度独立展示，C/E/G 的 8.6/10 门禁仅基于 C/E/G 加权聚合"
}
JSONEOF
)

mkdir -p "$(dirname "$OUTPUT_FILE")" 2>/dev/null
echo "$RESULT" > "$OUTPUT_FILE"
echo "JSON written: $OUTPUT_FILE"
echo "$RESULT"

exit 0
