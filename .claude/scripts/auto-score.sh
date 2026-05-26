#!/usr/bin/env bash
# auto-score.sh v3 — Meta-Oracle 四维打分体系 (C/E/G 加权聚合 + UX 独立)
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# Role: 对 C/E/G 三维度加权聚合评分，UX 独立展示不参与总阈值
#
# 使用: bash .claude/scripts/auto-score.sh [--calibrated] [--meta-oracle]
# 输出: .omc/state/auto-score-<timestamp>.json
#
# 评分方法:
#   C/E/G 每子维度独立检测 (0-100%)，按权重 (40/35/25) 聚合为 0-10 分
#   UX 独立评分（调用 score-ux.sh 或内置简易评分），不参与 8.6/10 门禁
#   8.6/10 门禁: >= 8.6 → ACCEPT, < 8.6 → ADVISORY
#
# 权重: C=40% (哲学#4+#6 正确性是基础), E=35% (哲学#3 机制必须生效), G=25% (哲学#7 治理是长期保障)

set -u

# E7 校准模式: 对纯 grep 静态检测结果降权 15% (DG-28 校准偏移)
CALIBRATED=false
META_ORACLE_MODE=false
for arg in "$@"; do
  [ "$arg" = "--calibrated" ] && CALIBRATED=true
  [ "$arg" = "--meta-oracle" ] && META_ORACLE_MODE=true
done

cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 99
PROJECT_ROOT=$(pwd)
TS=$(date -u +%Y%m%d-%H%M%S)
OUTPUT_FILE="$PROJECT_ROOT/.omc/state/auto-score-$TS.json"
STATE_DIR="$PROJECT_ROOT/.omc/state"

echo "=== Auto Score v3 (4D: C/E/G weighted + UX independent) @ $TS ==="

# ───── 辅助函数 ─────
pct() { echo "scale=1; $1 * 100 / $2" | bc 2>/dev/null || echo "0"; }

# 运行时数据存在性检查
has_runtime_data() {
  local file="$1"
  [ -f "$file" ] && [ -s "$file" ] && return 0 || return 1
}

# ── E7 校准：运行时证据因子 (0.0-1.0) ──
# 参数: hook_name — 检查 flywheel.log 中该 hook 的事件数
# 返回: 因子值 (通过 stdout 输出浮点数)
# 0 事件 → 0.5 (机制存在但无运行时证据，半信任)
# 1+ 事件 → 0.85+ (有证据但不给满分，留 15% 给质量差异)
# 5+ 事件 → 1.0 (有充分运行时证据)
runtime_evidence_factor() {
  local hook_name="$1"
  local count=0
  local flywheel_log="${HOME}/.claude/flywheel.log"
  if [ -f "$flywheel_log" ]; then
    count=$(grep -c "$hook_name" "$flywheel_log" 2>/dev/null); count="${count:-0}"
  fi
  # Also check flywheel-report.json
  if [ -f ".omc/state/flywheel-report.json" ]; then
    local json_count
    json_count=$(${PYTHON_BIN:-python3} -c "
import json
try:
    d = json.load(open('.omc/state/flywheel-report.json'))
    print(d.get('$hook_name', 0))
except: print(0)" 2>/dev/null)
    [ -n "$json_count" ] && [ "$json_count" -gt 0 ] 2>/dev/null && count=$(( count + json_count ))
  fi
  if [ "$count" -ge 5 ]; then echo "1.00"
  elif [ "$count" -ge 1 ]; then echo "0.85"
  else echo "0.50"; fi
}

# ── DG-103: 运行时数据 bonus (0-2 pts) — 打破静态评分天花板 ──
# 从实际 state 文件读取活跃度，给静态检测加运行时加权。
# 所有 bash 条件用 if-elif-else (不用 &&/|| 防优先级 bug)。
runtime_bonus() {
  local dim="$1"
  case "$dim" in
    C2) # Token 节省比例: >80%=2, >50%=1
      ${PYTHON_BIN:-python3} -c "
import json,os
tf='.omc/state/token-savings.json'
if os.path.exists(tf):
  try:
    d=json.load(open(tf))
    r=float(d.get('session_ratio_pct',0))
    e=int(d.get('cumulative_events',0))
    if r>80 and e>0: print('2')
    elif r>50: print('1')
    else: print('0')
  except: print('0')
else: print('0')
" 2>/dev/null || echo "0"
      ;;
    C5) # 工具活跃度: total-ops >100=2, >10=1
      local ops=$(cat .omc/state/total-ops.txt 2>/dev/null || echo 0)
      if [ "$ops" -gt 100 ]; then echo "2"
      elif [ "$ops" -gt 10 ]; then echo "1"
      else echo "0"; fi
      ;;
    C6) # 知识密度: lessons ≥40=2, ≥20=1
      local lessons=$(grep -c 'DG-\|### \[' .claude/claude-next.md 2>/dev/null || echo 0)
      if [ "$lessons" -ge 40 ]; then echo "2"
      elif [ "$lessons" -ge 20 ]; then echo "1"
      else echo "0"; fi
      ;;
    C9) # 错误恢复: retry-budget 签名数
      ${PYTHON_BIN:-python3} -c "
import json,os
tf='.omc/state/retry-budget.json'
if os.path.exists(tf):
  try:
    d=json.load(open(tf))
    s=len(d.get('signatures',{}))
    if s>=5: print('2')
    elif s>=1: print('1')
    else: print('0')
  except: print('0')
else: print('0')
" 2>/dev/null || echo "0"
      ;;
    E5) # 症状混淆: error-signals 记录数
      local sigs=$(wc -l < .omc/state/error-signals.jsonl 2>/dev/null || echo 0)
      if [ "$sigs" -gt 50 ]; then echo "2"
      elif [ "$sigs" -gt 10 ]; then echo "1"
      else echo "0"; fi
      ;;
    E6) # 自我矛盾: contradiction 检测率
      ${PYTHON_BIN:-python3} -c "
import json
total=0; contra=0
try:
  with open('.omc/state/contradiction-log.jsonl') as f:
    for l in f:
      if not l.strip(): continue
      total+=1
      if json.loads(l).get('contradiction'): contra+=1
  if total>100 and contra>0: print('2')
  elif total>50: print('1')
  else: print('0')
except: print('0')
" 2>/dev/null || echo "0"
      ;;
    E8) # 上下文遗忘: handoff + compact
      ${PYTHON_BIN:-python3} -c "
import os
h=os.path.getsize('.omc/state/session-handoff.md') if os.path.exists('.omc/state/session-handoff.md') else 0
c=os.path.getsize('.omc/state/context-cache.md') if os.path.exists('.omc/state/context-cache.md') else 0
if h>20 and c>1000: print('2')
elif c>0: print('1')
else: print('0')
" 2>/dev/null || echo "0"
      ;;
    *) echo "0" ;;
  esac
}

# ── DG-100: 语义质量因子 — 打破静态评分天花板 ──
# 测量运行时数据覆盖度，将纯文件存在检测无法感知的语义改进量化为分数
# (a) flywheel 埋点覆盖率: 已注册 hooks 中有多少有运行时数据
# (b) error-dna 噪声率: 错误签名中有多少是噪声 (ED-01: 83.5%)
# (c) 真实捕获率: 理论应检测 vs 实际已检测的事件比例
semantic_quality_factor() {
  local factor=1.00

  # (a) Flywheel 覆盖率: 统计 hooks 注册数 vs flywheel.log 中有事件的 hooks 数
  local registered=0 covered=0
  if [ -f "$HOME/.claude/flywheel.log" ] && [ -s "$HOME/.claude/flywheel.log" ]; then
    # Count hooks registered in settings.json
    registered=$(${PYTHON_BIN:-python3} -c "
import json,os
try:
  d=json.load(open('.claude/settings.json'))
  hooks=d.get('hooks',{})
  print(len(hooks))
except: print(0)" 2>/dev/null || echo "0")
    # Count unique hook names from CSV format: timestamp,hook_name,level,...
    covered=$(cut -d',' -f2 "$HOME/.claude/flywheel.log" 2>/dev/null | sort -u | wc -l | tr -d ' ')
    covered="${covered:-0}"
    if [ "$registered" -gt 0 ] 2>/dev/null && [ "$covered" -gt 0 ] 2>/dev/null; then
      local cov_pct
      cov_pct=$(echo "scale=2; $covered * 100 / $registered" | bc 2>/dev/null || echo "0")
      if [ "$(echo "$cov_pct >= 80" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        factor=$(echo "scale=2; $factor + 0.05" | bc)  # +5% bonus for high coverage
      elif [ "$(echo "$cov_pct < 10" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        factor=$(echo "scale=2; $factor - 0.05" | bc)  # -5% for very low coverage (was -10%)
      fi
    fi
  fi

  # (b) Error DNA 噪声率: 过高噪声率 = 症状混淆风险
  if [ -f ".omc/state/error-dna.jsonl" ]; then
    local total_edna noise_edna
    total_edna=$(wc -l < ".omc/state/error-dna.jsonl" 2>/dev/null | tr -d ' '); total_edna="${total_edna:-0}"
    noise_edna=$(grep -c '"status": "noise"' ".omc/state/error-dna.jsonl" 2>/dev/null); noise_edna="${noise_edna:-0}"
    if [ "$total_edna" -gt 0 ] 2>/dev/null; then
      local noise_pct
      noise_pct=$(echo "scale=2; $noise_edna * 100 / $total_edna" | bc 2>/dev/null || echo "0")
      if [ "$(echo "$noise_pct > 80" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        factor=$(echo "scale=2; $factor - 0.05" | bc)  # -5% for excessive noise
      elif [ "$(echo "$noise_pct < 30" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        factor=$(echo "scale=2; $factor + 0.03" | bc)  # +3% for low noise
      fi
    fi
  fi

  # (c) 真实捕获率: capability-matrix-test 最近通过率
  local cap_log
  cap_log=$(ls -t .omc/state/capability-matrix-*.log 2>/dev/null | head -1)
  if [ -n "$cap_log" ] && [ -f "$cap_log" ]; then
    local total_tests pass_tests
    total_tests=$(grep -c '^\[' "$cap_log" 2>/dev/null); total_tests="${total_tests:-0}"
    pass_tests=$(grep -c 'PASS' "$cap_log" 2>/dev/null); pass_tests="${pass_tests:-0}"
    if [ "$total_tests" -gt 0 ] 2>/dev/null; then
      local pass_pct
      pass_pct=$(echo "scale=2; $pass_tests * 100 / $total_tests" | bc 2>/dev/null || echo "0")
      if [ "$(echo "$pass_pct >= 95" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
        factor=$(echo "scale=2; $factor + 0.03" | bc)
      fi
    fi
  fi

  # Clamp to [0.80, 1.10]
  if [ "$(echo "$factor < 0.80" | bc -l 2>/dev/null || echo 0)" = "1" ]; then factor="0.80"; fi
  if [ "$(echo "$factor > 1.10" | bc -l 2>/dev/null || echo 0)" = "1" ]; then factor="1.10"; fi
  echo "$factor"
}

# ── 烟雾测试快速检查 ──
smoke_passes_for() {
  local test_label="$1"
  local log="${2:-.omc/state/harness-smoke-*.log}"
  # Find latest smoke log
  local latest_log
  latest_log=$(ls -t .omc/state/harness-smoke-*.log 2>/dev/null | head -1)
  [ -z "$latest_log" ] && return 1
  grep -q "$test_label" "$latest_log" 2>/dev/null && grep -A1 "$test_label" "$latest_log" | grep -q "PASS" && return 0
  return 1
}

# ===================================================================
# C 维度 — 正确性 / Correctness (9 子维度, max 105)
# ===================================================================

# C1 指令清晰度 (15分)
score_C1() {
  local score=0 max=15
  local flaws=0 total_checks=5
  (grep -q '^| . | .*铁律' AGENTS.md 2>/dev/null || grep -q '^| . | .*铁律' source/harness-kit/AGENTS.md 2>/dev/null) && : || flaws=$((flaws+1))
  grep -q '## 架构铁律' .claude/kernel.md 2>/dev/null && : || flaws=$((flaws+1))
  _AP_COUNT=$(grep -c '^### [A-Z][0-9]' .claude/anti-patterns.md 2>/dev/null); _AP_COUNT="${_AP_COUNT:-0}"; [ "$_AP_COUNT" -ge 14 ] 2>/dev/null && : || flaws=$((flaws+1))
  SCOPE_COUNT=$(grep '范围冻结' AGENTS.md .claude/kernel.md .claude/anti-patterns.md 2>/dev/null | wc -l | tr -d ' ')
  [ "$SCOPE_COUNT" -le 2 ] 2>/dev/null && : || flaws=$((flaws+1))
  RULE_COUNT=$(grep -c '^\s*| [0-9]' AGENTS.md 2>/dev/null); RULE_COUNT="${RULE_COUNT:-0}"
  [ "$RULE_COUNT" -le 10 ] 2>/dev/null && : || flaws=$((flaws+1))

  score=$(( max - (flaws * max / total_checks) ))
  [ "$score" -lt 0 ] && score=0
  echo "$score $max C1=指令清晰度(${flaws}/${total_checks}项缺陷)"
}

# C2 上下文完整度 (15分) — E7 校准: 每子维度要求双源证据
score_C2() {
  local score=0 max=15
  local index_ok=0
  if [ -f .claude/index.md ]; then
    if bash .claude/scripts/audit-hooks.sh --check-index 2>/dev/null | grep -qE "主表.*实际活跃|🔴 严重: 0"; then
      index_ok=1
    fi
  fi
  local compact_ok=0
  if [ -f .claude/hooks/compact-detect.sh ]; then
    if ${PYTHON_BIN:-python3} -c "
import json, time, os
try:
    d = json.load(open('.omc/state/token-compact-state.json'))
    ts = d.get('timestamp', 0) or d.get('pre_compact_usage', {}).get('timestamp', 0)
    age = time.time() - float(ts)
    print('recent' if age < 86400 else 'stale')
except: print('stale')
" 2>/dev/null | grep -q "recent"; then
      compact_ok=1
    fi
  fi
  local refresh_ok=0
  if grep -q "context.*50.*refresh\|L2\|周期刷新" .claude/hooks/turn-counter.sh 2>/dev/null; then
    if [ -f .omc/state/session-turns.json ]; then
      TC_COUNT=$(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('.omc/state/session-turns.json')).get('count', 0))" 2>/dev/null || echo "0")
      [ "$TC_COUNT" -ge 1 ] 2>/dev/null && refresh_ok=1
    fi
  fi
  local size_ok=0
  INDEX_SIZE=$(wc -c < .claude/index.md 2>/dev/null || echo "0")
  [ "$INDEX_SIZE" -le 5000 ] 2>/dev/null && size_ok=1

  score=$(( index_ok * 5 + compact_ok * 4 + refresh_ok * 3 + size_ok * 3 ))
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus C2) ))
  [ "$score" -gt "15" ] && score=15
  echo "$score $max C2=上下文(index=${index_ok} compact=${compact_ok} refresh=${refresh_ok} size=${size_ok})"
}

# C3 流程结构化 (15分)
score_C3() {
  local score=0 max=15
  local has_l1l4=0 has_7step=0 has_triple=0 has_prd=0
  grep -q 'L1.*简单\|L2.*中等\|L3.*复杂\|L4.*关键' AGENTS.md 2>/dev/null && has_l1l4=1
  grep -q '7-step\|7 步\|Step [1-7]' AGENTS.md 2>/dev/null && has_7step=1
  grep -q '三重门\|Triple Gate\|triple_gate' AGENTS.md 2>/dev/null && has_triple=1
  [ -f .omc/prd.json ] && has_prd=1

  score=$(( has_l1l4 * 4 + has_7step * 4 + has_triple * 4 + has_prd * 3 ))
  echo "$score $max C3=流程(L1-L4=${has_l1l4} 7step=${has_7step} triple=${has_triple} prd=${has_prd})"
}

# C4 输出规范化 (10分) — E7 校准: 要求至少 2/3 方面同时满足
score_C4() {
  local score=0 max=10
  local soft_detect=0 direction_fmt=0 evidence_level=0
  grep -q "A2_SOFT_WORDS" .claude/hooks/posttool-anti-pattern-detect.sh 2>/dev/null && soft_detect=1
  grep -qr "方向指引\|suggested_next" .claude/ --include="*.sh" --include="*.md" 2>/dev/null && direction_fmt=1
  grep -q '证据层级\|L1.*L2.*L3.*L4' AGENTS.md 2>/dev/null && evidence_level=1

  local aspects=$(( soft_detect + direction_fmt + evidence_level ))
  if [ "$aspects" -ge 2 ]; then
    score=$(( soft_detect * 4 + direction_fmt * 3 + evidence_level * 3 ))
  else
    score=$(( soft_detect * 3 + direction_fmt * 2 + evidence_level * 2 ))
  fi
  echo "$score $max C4=输出(soft=${soft_detect} dir=${direction_fmt} evidence=${evidence_level} aspects=${aspects})"
}

# C5 工具生命周期 (10分)
score_C5() {
  local score=0 max=10
  local audit_red=0
  AUDIT_RED=$(bash .claude/scripts/audit-hooks.sh 2>/dev/null | grep -oE '🔴 严重: [0-9]+' | grep -oE '[0-9]+' || echo "99")
  local settings_count disk_count
  settings_count=$(grep -cE '\.claude/hooks/' .claude/settings.json 2>/dev/null); settings_count="${settings_count:-0}"
  disk_count=$(ls .claude/hooks/*.sh 2>/dev/null | grep -v 'harness_config.sh\|agentic-ui.sh' | grep -v '\.bak$\|\.disabled$' | wc -l | tr -d ' ')
  local reg_rate=0
  [ "$disk_count" -gt 0 ] && reg_rate=$(( settings_count * 100 / disk_count ))

  local audit_score=5 consistency_score=5
  [ "$AUDIT_RED" = "0" ] && audit_score=5 || audit_score=$(( 5 - AUDIT_RED ))
  [ "$audit_score" -lt 0 ] && audit_score=0
  [ "$reg_rate" -ge 85 ] && consistency_score=5 || consistency_score=$(( reg_rate / 17 ))

  score=$(( audit_score + consistency_score ))
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus C5) ))
  [ "$score" -gt "10" ] && score=10
  echo "$score $max C5=生命周期(audit_red=${AUDIT_RED} reg=${reg_rate}%)"
}

# C6 知识密度 (10分)
score_C6() {
  local score=0 max=10
  local cn_entries=0 edna_size=0 has_anti=0
  cn_entries=$(grep -c '^### \[' .claude/claude-next.md 2>/dev/null )
  edna_size=$(cat .omc/state/error-signals.jsonl 2>/dev/null | wc -c | tr -d ' ' || echo "0"); edna_size="${edna_size:-0}"
  [ -f .claude/anti-patterns.md ] && has_anti=1

  local cn_score=4 edna_score=4 anti_score=2
  [ "$cn_entries" -ge 10 ] && cn_score=4 || cn_score=$(( cn_entries * 4 / 10 ))
  [ "$edna_size" -ge 1000 ] && edna_score=4 || edna_score=$(( edna_size * 4 / 1000 ))
  anti_score=$(( has_anti * 2 ))

  score=$(( cn_score + edna_score + anti_score ))
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus C6) ))
  [ "$score" -gt "10" ] && score=10
  echo "$score $max C6=知识(cn=${cn_entries}条 edna=${edna_size}b anti=${has_anti})"
}

# C7 关联编排 (10分) — E7 校准: 读实际 subagent 调用次数
score_C7() {
  local score=0 max=10
  local orch_count=0
  if [ -f ".omc/state/subagent-usage.jsonl" ]; then
    orch_count=$(wc -l < ".omc/state/subagent-usage.jsonl" 2>/dev/null | tr -d ' ')
    orch_count="${orch_count:-0}"
  fi
  local orch_score=0
  if [ "$orch_count" -ge 11 ]; then orch_score=6
  elif [ "$orch_count" -ge 6 ]; then orch_score=5
  elif [ "$orch_count" -ge 3 ]; then orch_score=3
  else orch_score=0; fi

  local skill_count=0 skill_score=4
  skill_count=$(find .claude/skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
  [ "$skill_count" -ge 3 ] && skill_score=4 || skill_score=$(( skill_count ))

  score=$(( orch_score + skill_score ))
  echo "$score $max C7=编排(实际调用=${orch_count} skills=${skill_count})"
}

# C8 可维护性 (10分)
score_C8() {
  local score=0 max=10
  local pv_failed=0
  pv_failed=$(bash .claude/scripts/hook-production-verify.sh 2>/dev/null | grep '^summary:' | sed -n 's/.* \([0-9]*\) failed.*/\1/p' || echo "0")
  [ -z "$pv_failed" ] && pv_failed=0
  local naming_ok=0
  grep -qE 'snake-case|蛇形命名' .claude/kernel.md 2>/dev/null && naming_ok=1

  local pv_score=5 naming_score=5
  [ "$pv_failed" = "0" ] && pv_score=5 || pv_score=$(( 5 - pv_failed * 2 ))
  [ "$pv_score" -lt 0 ] && pv_score=0
  naming_score=$(( naming_ok * 5 ))

  score=$(( pv_score + naming_score ))
  echo "$score $max C8=维护(pv_fail=${pv_failed} naming=${naming_ok})"
}

# C9 错误恢复 (10分)
score_C9() {
  local score=0 max=10
  local edna_auto=0 escape=0 rca=0
  [ -f .omc/state/error-signals.jsonl ] && [ -s .omc/state/error-signals.jsonl ] && edna_auto=1
  grep -q 'context-force-override\|force.override' .claude/hooks/context-guard.sh 2>/dev/null && escape=1
  [ -f .claude/hooks/posttool-completion-audit.sh ] && rca=1

  score=$(( edna_auto * 4 + escape * 3 + rca * 3 ))
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus C9) ))
  [ "$score" -gt "10" ] && score=10
  echo "$score $max C9=恢复(edna=${edna_auto} escape=${escape} rca=${rca})"
}

# ===================================================================
# E 维度 — 有效性 / Effectiveness (8 子维度, max 110)
# ===================================================================

# E1 目标漂移 (20分) — E7校准: scope+freeze机制存在 + 运行时证据验证
score_E1() {
  local score=0 max=20
  local scope=0 freeze=0 scope_from_goal=0 intent_rt=0
  grep -q 'pretool-edit-scope' .claude/settings.json 2>/dev/null && scope=1
  grep -q '范围冻结\|scope.freeze' AGENTS.md 2>/dev/null && freeze=1
  # Scope-from-Goal: lx-goal 激活时自动调用 auto-scope.sh 推导范围（意志延伸物化）
  grep -q 'auto-scope.sh' .claude/skills/lx-goal/scripts/lx-goal.sh 2>/dev/null && scope_from_goal=1
  # pre-ask-guard: 问人前强制过决策链，杜绝无意义打断
  grep -q 'pre-ask-guard' .claude/settings.json 2>/dev/null && grep -q 'pre_ask_guard.*true' .claude/harness.yaml 2>/dev/null && scope_from_goal=1
  # 运行时证据: 仅用 pretool-edit-scope（不应跨机制代理 intent_tracker 的证据）
  local scope_rt
  scope_rt=$(runtime_evidence_factor "pretool_edit_scope")
  intent_rt="$scope_rt"
  # scope-from-goal 提升运行时因子底线（机制已部署，待积累数据）
  if [ "$scope_from_goal" = "1" ] && [ "$(echo "$intent_rt < 0.70" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    intent_rt="0.70"
  fi

  score=$(echo "scale=0; ($scope * 12 + $freeze * 8) * $intent_rt / 1" | bc 2>/dev/null || echo "0")
  echo "$score $max E1=漂移(scope=${scope} freeze=${freeze} scope_from_goal=${scope_from_goal} rt_factor=${intent_rt})"
}

# E2 幻觉输出 (20分) — E7校准: 禁令+门禁+双源机制存在 + 运行时claim-audit/anti-pattern证据
score_E2() {
  local score=0 max=20
  local no_fabricate=0 evidence_gate=0 dual_source=0
  (grep -q '禁止编造\|no.fabricate' AGENTS.md 2>/dev/null || grep -q '禁止编造\|no.fabricate' source/harness-kit/AGENTS.md 2>/dev/null) && no_fabricate=1
  grep -q 'EVIDENCE_FILE\|evidence_freshness' .claude/hooks/completion-gate.sh 2>/dev/null && evidence_gate=1
  grep -q 'cross-verify-handoff' .claude/hooks/completion-gate.sh 2>/dev/null && dual_source=1
  # 运行时证据: claim-audit 和 anti-pattern-detect 都有 flywheel 事件
  local claim_rt anti_rt best_rt
  claim_rt=$(runtime_evidence_factor "posttool_claim_audit")
  anti_rt=$(runtime_evidence_factor "anti_pattern_detect")
  if [ "$(echo "$claim_rt > $anti_rt" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    best_rt="$claim_rt"
  else
    best_rt="$anti_rt"
  fi

  score=$(echo "scale=0; ($no_fabricate * 5 + $evidence_gate * 8 + $dual_source * 7) * $best_rt / 1" | bc 2>/dev/null || echo "0")
  echo "$score $max E2=幻觉(禁令=${no_fabricate} 门禁=${evidence_gate} 双源=${dual_source} rt_factor=${best_rt})"
}

# E3 虚假完成 (15分) — E7校准: VERIFIED门禁+软词检测 + 运行时completion-gate事件
score_E3() {
  local score=0 max=15
  local qc=0 soft_word=0
  grep -q 'VERIFIED\|required_keyword' .claude/hooks/completion-gate.sh 2>/dev/null && qc=1
  grep -q 'A2_SOFT_WORDS' .claude/hooks/posttool-anti-pattern-detect.sh 2>/dev/null && soft_word=1
  # 运行时证据: completion_gate + autonomous log 非空
  local cg_rt
  cg_rt=$(runtime_evidence_factor "completion_gate")
  # 额外加分: completion-gate-autonomous.log 有内容
  if [ -f .omc/state/completion-gate-autonomous.log ] && [ -s .omc/state/completion-gate-autonomous.log ]; then
    cg_rt=$(echo "scale=2; $cg_rt + 0.15" | bc 2>/dev/null || echo "$cg_rt")
    [ "$(echo "$cg_rt > 1.0" | bc -l 2>/dev/null || echo 0)" = "1" ] && cg_rt="1.00"
  fi

  score=$(echo "scale=0; ($qc * 8 + $soft_word * 7) * $cg_rt / 1" | bc 2>/dev/null || echo "0")
  echo "$score $max E3=虚假(threshold=${qc} soft=${soft_word} rt_factor=${cg_rt})"
}

# E4 惯性执行 (12分) — E7校准: 3轮上限+context-guard + 运行时permission-gate事件
score_E4() {
  local score=0 max=12
  local round3=0 guard=0
  grep -q '修复.*3.*轮\|3.*轮.*上限' .claude/kernel.md 2>/dev/null && round3=1
  grep -q 'context-guard\|Context Guard' .claude/hooks/context-guard.sh 2>/dev/null && guard=1
  # 运行时证据: permission_gate + sensitive_edit 都有 flywheel
  local perm_rt sens_rt best_rt
  perm_rt=$(runtime_evidence_factor "permission_gate")
  sens_rt=$(runtime_evidence_factor "sensitive_edit")
  if [ "$(echo "$perm_rt > $sens_rt" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    best_rt="$perm_rt"
  else
    best_rt="$sens_rt"
  fi

  score=$(echo "scale=0; ($round3 * 6 + $guard * 6) * $best_rt / 1" | bc 2>/dev/null || echo "0")
  echo "$score $max E4=惯性(3轮=${round3} guard=${guard} rt_factor=${best_rt})"
}

# E5 症状混淆 (10分) — E7校准: RCA强制+编译反模式 + 运行时retry-check诊断门禁 + error-dna活跃性
score_E5() {
  local score=0 max=10
  local rca_enforced=0 compile_anti=0
  grep -qE 'RCA|根因' .claude/hooks/completion-gate.sh 2>/dev/null && rca_enforced=1
  grep -q '编译错误盲修\|编译盲修' .claude/anti-patterns.md 2>/dev/null && compile_anti=1
  # 运行时证据: pretool-retry-check 有诊断门禁执行记录 + error-signals 有数据
  local retry_rt errsig_ok
  retry_rt=$(runtime_evidence_factor "pretool_retry_check")
  errsig_ok=0
  has_runtime_data ".omc/state/error-signals.jsonl" && errsig_ok=1
  # 综合运行时因子: retry-check flywheel 权重 0.6, error-signals 权重 0.4
  local combined_rt
  combined_rt=$(echo "scale=2; $retry_rt * 0.6 + $errsig_ok * 0.4" | bc 2>/dev/null || echo "0.50")
  [ "$(echo "$combined_rt < 0.50" | bc -l 2>/dev/null || echo 0)" = "1" ] && combined_rt="0.50"

  score=$(echo "scale=0; ($rca_enforced * 6 + $compile_anti * 4) * $combined_rt / 1" | bc 2>/dev/null || echo "0")
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus E5) ))
  [ "$score" -gt "10" ] && score=10
  echo "$score $max E5=症状(rca=${rca_enforced} compile_anti=${compile_anti} rt_factor=${combined_rt} errsig=${errsig_ok})"
}

# E6 自我矛盾 (13分) — E7校准: 三重门+矛盾日志存在 + 运行时矛盾检测率 + 纠正检测
score_E6() {
  local score=0 max=13
  local triple=0 contradict_log=0 intent_fw=0
  grep -q 'cross-verify\|三重门\|triple' .claude/hooks/completion-gate.sh 2>/dev/null && triple=1
  [ -f .omc/state/contradiction-log.jsonl ] && contradict_log=1
  # intent-tracker flywheel 埋点 (P3: 信号文件机制已部署)
  grep -q 'flywheel_event.*intent_tracker' .claude/hooks/intent-tracker.sh 2>/dev/null && intent_fw=1
  # 运行时证据: 矛盾检测率 (contradiction=true / total)
  local detect_rate=0
  if [ -f .omc/state/contradiction-log.jsonl ]; then
    local total contrad
    total=$(wc -l < .omc/state/contradiction-log.jsonl 2>/dev/null | tr -d ' '); total="${total:-0}"
    contrad=$(grep -c '"contradiction": true' .omc/state/contradiction-log.jsonl 2>/dev/null); contrad="${contrad:-0}"
    if [ "$total" -gt 0 ] 2>/dev/null; then
      detect_rate=$(echo "scale=2; $contrad / $total" | bc 2>/dev/null || echo "0")
    fi
  fi
  # 用户纠正检测运行时证据
  local corr_rt
  corr_rt=$(runtime_evidence_factor "user_correction")
  # 综合: 矛盾日志存在性(0.2) + 检测率(0.3) + 纠正检测运行时(0.3) + flywheel埋点(0.2)
  local log_ok=0
  [ "$contradict_log" = "1" ] && log_ok=1
  local rate_score=0
  [ "$(echo "$detect_rate >= 0.01" | bc -l 2>/dev/null || echo 0)" = "1" ] && rate_score=1
  local corr_score=0
  [ "$(echo "$corr_rt >= 0.70" | bc -l 2>/dev/null || echo 0)" = "1" ] && corr_score=1
  local combined_rt
  combined_rt=$(echo "scale=2; $log_ok * 0.35 + $rate_score * 0.25 + $corr_score * 0.2 + $intent_fw * 0.2" | bc 2>/dev/null || echo "0.50")
  [ "$(echo "$combined_rt < 0.50" | bc -l 2>/dev/null || echo 0)" = "1" ] && combined_rt="0.50"

  score=$(echo "scale=0; ($triple * 7 + $contradict_log * 6) * $combined_rt / 1" | bc 2>/dev/null || echo "0")
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus E6) ))
  [ "$score" -gt "13" ] && score=13
  echo "$score $max E6=矛盾(triple=${triple} log=${contradict_log} intent_fw=${intent_fw} detect_rate=${detect_rate} rt_factor=${combined_rt})"
}

# E7 过度自信 (10分) — E7校准: 断言规则+置信度格式 + 运行时claim-audit强制校验
score_E7() {
  local score=0 max=10
  local assert_rule=0 confidence_fmt=0
  (grep -q '断言真实\|file:line' AGENTS.md 2>/dev/null || grep -q '断言真实\|file:line' source/harness-kit/AGENTS.md 2>/dev/null) && assert_rule=1
  grep -q '置信度\|\[已验证:\|\[已测试:' .claude/kernel.md AGENTS.md 2>/dev/null && confidence_fmt=1
  # 运行时证据: posttool-claim-audit 实际执行 (flywheel events)
  local claim_rt
  claim_rt=$(runtime_evidence_factor "posttool_claim_audit")
  # 回测: 前次 auto-score E维度是否有全满分 (全满分=虚高证据)
  local prev_inflated=0
  if ls .omc/state/auto-score-*.json >/dev/null 2>&1; then
    local prev_all_100
    prev_all_100=$(${PYTHON_BIN:-python3} -c "
import json, glob, os
files = sorted(glob.glob('.omc/state/auto-score-*.json'), key=os.path.getmtime, reverse=True)
# Skip current run's file (just written), check previous
prev_files = [f for f in files if not f.endswith('$TS.json')]
if prev_files:
    d = json.load(open(prev_files[0]))
    subs = d.get('subscores', {})
    e_pcts = [v.get('pct', 0) for k, v in subs.items() if k.startswith('E')]
    if e_pcts and all(p >= 99.9 for p in e_pcts):
        print('1')
    else:
        print('0')
else:
    print('0')
" 2>/dev/null)
    [ "$prev_all_100" = "1" ] && prev_inflated=1
  fi
  # 综合: claim-audit运行时(0.5) - 回溯虚高惩罚(0.5)
  local combined_rt
  combined_rt=$(echo "scale=2; $claim_rt * 0.5 + (1 - $prev_inflated) * 0.5" | bc 2>/dev/null || echo "$claim_rt")

  score=$(echo "scale=0; ($assert_rule * 5 + $confidence_fmt * 5) * $combined_rt / 1" | bc 2>/dev/null || echo "0")
  echo "$score $max E7=自信(assert=${assert_rule} fmt=${confidence_fmt} rt_factor=${combined_rt} prev_inflated=${prev_inflated})"
}

# E8 上下文遗忘 (10分) — E7校准: compact+turns+handoff 存在 + context-guard运行时事件
score_E8() {
  local score=0 max=10
  local compact=0 tc=0 handoff=0
  [ -f .claude/hooks/compact-detect.sh ] && compact=1
  grep -q 'turn-counter\|UserPromptSubmit' .claude/settings.json 2>/dev/null && tc=1
  [ -f .claude/hooks/auto-snapshot.sh ] && grep -q 'handoff\|交接' .claude/hooks/auto-snapshot.sh 2>/dev/null && handoff=1
  # 运行时证据: inject_project_knowledge (SessionStart 知识注入防上下文丢失) + auto-snapshot
  # inject-project-knowledge 将核心规则注入每会话 = 最直接的上下文遗忘防御
  local know_rt snap_rt best_rt
  know_rt=$(runtime_evidence_factor "inject_project_knowledge")
  snap_rt=$(runtime_evidence_factor "auto_snapshot")
  if [ "$(echo "$know_rt > $snap_rt" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
    best_rt="$know_rt"
  else
    best_rt="$snap_rt"
  fi

  score=$(echo "scale=0; ($compact * 4 + $tc * 3 + $handoff * 3) * $best_rt / 1" | bc 2>/dev/null || echo "0")
  # DG-103: runtime bonus
  score=$(( score + $(runtime_bonus E8) ))
  [ "$score" -gt "10" ] && score=10
  echo "$score $max E8=遗忘(compact=${compact} turns=${tc} handoff=${handoff} rt_factor=${best_rt})"
}

# ===================================================================
# G 维度 — 治理 / Governance (5 子维度, max 50)
# 对齐 Prompt #4: 哲学一致性 / 铁律合规 / 反模式避让 / Oracle 裁决留痕 / 文档漂移
# ===================================================================

# G1 哲学一致性 (10分)
score_G1() {
  local score=0 max=10
  local philo_has_mech=0 philo_ref=0 dual_check=0

  # 检查 7 条哲学是否都有对应的机制实现
  local philo_count=0
  grep -q '没通过验证等于没做\|#4.*验证' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q '先守护.*后激发\|#3.*守护' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q '0.*信任\|#6.*信任' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q '文档优先\|#7.*文档' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q '以人为本\|#5.*人' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q '少量正确\|#2.*少量' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  grep -q 'The Less.*The More\|#1.*Less' AGENTS.md 2>/dev/null && philo_count=$((philo_count+1))
  [ "$philo_count" -ge 6 ] && philo_has_mech=1

  # 哲学参考文档存在
  [ -f .claude/reference/philosophy.md ] && philo_ref=1

  # 哲学→机制 逆向追溯矩阵存在
  grep -q '机制→哲学.*逆向追溯\|哲学一致性.*机制' AGENTS.md 2>/dev/null && dual_check=1

  score=$(( philo_has_mech * 4 + philo_ref * 3 + dual_check * 3 ))
  echo "$score $max G1=哲学一致性(mech=${philo_has_mech} ref=${philo_ref} dual=${dual_check})"
}

# G2 铁律合规 (10分)
score_G2() {
  local score=0 max=10
  local audit_pass=0 smoke_pass=0 rule_count_ok=0

  # audit-hooks 红色错误 = 0
  local aud_red
  aud_red=$(bash .claude/scripts/audit-hooks.sh 2>/dev/null | grep -oE '🔴 严重: [0-9]+' | grep -oE '[0-9]+' || echo "99")
  [ "$aud_red" = "0" ] 2>/dev/null && audit_pass=1

  # harness-smoke-test 全绿
  local smoke_failed
  smoke_failed=$(bash .claude/scripts/harness-smoke-test.sh 2>/dev/null | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "99")
  [ "$smoke_failed" = "0" ] 2>/dev/null && smoke_pass=1

  # B-terminal: 独立跨终端验证 (三扇门 B 环节)
  local bterm_pass=0
  if [ -f .omc/state/b-terminal-result.json ]; then
    ${PYTHON_BIN:-python3} -c "import json; d=json.load(open('.omc/state/b-terminal-result.json')); assert d.get('failed',1)==0" 2>/dev/null && bterm_pass=1
  fi
  # 铁律条数合理 (6<=N<=10) — DG-125 精确提取「8 条铁律」段
  local rule_count
  rule_count=$(sed -n '/^## 8 条铁律/,/^## /p' AGENTS.md 2>/dev/null | grep -c '^| [0-9] |' 2>/dev/null); rule_count="${rule_count:-0}"
  [ "$rule_count" -ge 6 ] 2>/dev/null && [ "$rule_count" -le 10 ] 2>/dev/null && rule_count_ok=1

  score=$(( audit_pass * 3 + smoke_pass * 3 + bterm_pass * 2 + rule_count_ok * 2 ))
  echo "$score $max G2=铁律合规(audit=${audit_pass} smoke=${smoke_pass} rules=${rule_count_ok})"
}

# G3 反模式避让 (10分)
score_G3() {
  local score=0 max=10
  local anti_exists=0 anti_complete=0 lessons_active=0

  # anti-patterns.md 存在且覆盖 A-H 共 8 类
  if [ -f .claude/anti-patterns.md ]; then
    anti_exists=1
    local cat_count
    cat_count=$(grep -cE '^## [A-H]\.' .claude/anti-patterns.md 2>/dev/null)
    [ "${cat_count:-0}" -ge 7 ] 2>/dev/null && anti_complete=1
  fi

  # claude-next.md 有狗粮教训 (DG-* entries) — 证明从错误中学习
  local dg_count
  dg_count=$(grep -c 'DG-[0-9]' .claude/claude-next.md 2>/dev/null); dg_count="${dg_count:-0}"
  [ "$dg_count" -ge 5 ] 2>/dev/null && lessons_active=1

  score=$(( anti_exists * 4 + anti_complete * 3 + lessons_active * 3 ))
  echo "$score $max G3=反模式避让(anti=${anti_exists} complete=${anti_complete} lessons=${lessons_active})"
}

# G4 Oracle 裁决留痕 (10分)
score_G4() {
  local score=0 max=10
  local oracle_verdict=0 meta_verdict=0 override_log=0

  # Oracle 裁决文件存在
  [ -f .omc/state/oracle_verdict.json ] && oracle_verdict=1

  # Meta-Oracle 裁决文件存在且有内容
  if [ -f .omc/state/meta-oracle-verdicts.md ]; then
    local verdict_lines
    verdict_lines=$(wc -l < .omc/state/meta-oracle-verdicts.md 2>/dev/null | tr -d ' ')
    [ "${verdict_lines:-0}" -ge 3 ] 2>/dev/null && meta_verdict=1
  fi

  # 覆写日志存在
  [ -f .omc/state/meta-oracle-overrides.md ] && override_log=1

  score=$(( oracle_verdict * 4 + meta_verdict * 3 + override_log * 3 ))
  echo "$score $max G4=Oracle裁决留痕(oracle=${oracle_verdict} meta=${meta_verdict} override=${override_log})"
}

# G5 文档漂移 (10分)
score_G5() {
  local score=0 max=10
  local source_mirror_ok=0 index_consistent=0 doc_refs_ok=0

  # source mirror 一致性检查
  # DG-95: "有意分歧" is an info header, not a pass signal. Use precise match.
  if bash .claude/scripts/audit-hooks.sh --check-source-mirror 2>/dev/null | grep -qE '✅|通过|无漂移[^:]*$'; then
    source_mirror_ok=1
  fi

  # index.md 与 hooks 表一致性
  if [ -f .claude/index.md ]; then
    local idx_hooks disk_hooks
    idx_hooks=$(grep -c '\.claude/hooks/' .claude/index.md 2>/dev/null); idx_hooks="${idx_hooks:-0}"
    disk_hooks=$(ls .claude/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
    # 允许 ±5 的容差（index.md 可能不是 1:1 映射）
    local diff=$(( idx_hooks - disk_hooks ))
    [ "$diff" -lt 0 ] && diff=$(( -diff ))
    [ "$diff" -le 5 ] 2>/dev/null && index_consistent=1
  fi

  # doc-sync-check 脚本存在
  [ -f .claude/scripts/doc-sync-check.sh ] && doc_refs_ok=1

  score=$(( source_mirror_ok * 4 + index_consistent * 3 + doc_refs_ok * 3 ))
  echo "$score $max G5=文档漂移(mirror=${source_mirror_ok} index=${index_consistent} docs=${doc_refs_ok})"
}

# ===================================================================
# UX 维度 — 用户体验 (独立评分, max 10)
# 优先调用独立 score-ux.sh，不存在时使用内置简易评分
# ===================================================================
score_UX() {
  # 优先使用独立 UX 评分脚本
  if [ -f .claude/scripts/score-ux.sh ]; then
    local ux_output
    ux_output=$(bash .claude/scripts/score-ux.sh 2>/dev/null)
    local ux_score ux_max
    ux_score=$(echo "$ux_output" | grep 'UX 总分:' | grep -oE '[0-9]+/[0-9]+' | cut -d'/' -f1)
    ux_max=$(echo "$ux_output" | grep 'UX 总分:' | grep -oE '[0-9]+/[0-9]+' | cut -d'/' -f2)
    ux_score="${ux_score:-0}"
    ux_max="${ux_max:-10}"
    echo "$ux_score $ux_max UX=独立评分(score-ux.sh)"
    return 0
  fi

  # 内置简易评分 (max 10)
  local score=0 max=10
  local has_decision_chain=0 has_meta_oracle=0 has_auto_mode=0 has_error_class=0 has_completion_gate=0

  [ -f .claude/reference/autonomous-decision-chain.md ] && has_decision_chain=1
  grep -q 'meta_oracle_trigger' .claude/hooks/meta-oracle-trigger.sh 2>/dev/null && has_meta_oracle=1
  [ -f .claude/skills/lx-goal/scripts/lx-goal.sh ] && [ -f .claude/skills/lx-ghost/scripts/lx-ghost.sh ] && has_auto_mode=1
  grep -q 'error-dna\|error_classifier' .claude/settings.json 2>/dev/null && has_error_class=1
  grep -q 'SOFT_WORDS\|违禁词\|evidence.*gate' .claude/hooks/completion-gate.sh 2>/dev/null && has_completion_gate=1

  score=$(( has_decision_chain * 2 + has_meta_oracle * 2 + has_auto_mode * 2 + has_error_class * 2 + has_completion_gate * 2 ))
  [ "$score" -gt "$max" ] && score=$max
  echo "$score $max UX=内置简易评分(chain=${has_decision_chain} ask=${has_ask_guard} auto=${has_auto_mode} err=${has_error_class} gate=${has_completion_gate})"
}

# ───── 聚合评分 ─────
scoredata=""
agg_scores=""
agg_metrics=""

append_score() {
  local label="$1" data="$2"
  local s m
  s=$(echo "$data" | awk '{print $1}')
  m=$(echo "$data" | awk '{print $2}')
  local detail="$data"
  [ -n "$agg_scores" ] && agg_scores="$agg_scores,"
  agg_scores="$agg_scores\"$label\":{\"score\":$s,\"max\":$m,\"pct\":$(pct $s $m)}"
  [ -n "$agg_metrics" ] && agg_metrics="$agg_metrics,"
  agg_metrics="$agg_metrics\"$label\":\"$(echo "$detail" | cut -d' ' -f4-)\""
}

echo "--- 子维度检测 ---"

echo -n "  C1 "; r1=$(score_C1); echo "$r1"; append_score "C1" "$r1"
echo -n "  C2 "; r2=$(score_C2); echo "$r2"; append_score "C2" "$r2"
echo -n "  C3 "; r3=$(score_C3); echo "$r3"; append_score "C3" "$r3"
echo -n "  C4 "; r4=$(score_C4); echo "$r4"; append_score "C4" "$r4"
echo -n "  C5 "; r5=$(score_C5); echo "$r5"; append_score "C5" "$r5"
echo -n "  C6 "; r6=$(score_C6); echo "$r6"; append_score "C6" "$r6"
echo -n "  C7 "; r7=$(score_C7); echo "$r7"; append_score "C7" "$r7"
echo -n "  C8 "; r8=$(score_C8); echo "$r8"; append_score "C8" "$r8"
echo -n "  C9 "; r9=$(score_C9); echo "$r9"; append_score "C9" "$r9"

echo -n "  E1 "; e1=$(score_E1); echo "$e1"; append_score "E1" "$e1"
echo -n "  E2 "; e2=$(score_E2); echo "$e2"; append_score "E2" "$e2"
echo -n "  E3 "; e3=$(score_E3); echo "$e3"; append_score "E3" "$e3"
echo -n "  E4 "; e4=$(score_E4); echo "$e4"; append_score "E4" "$e4"
echo -n "  E5 "; e5=$(score_E5); echo "$e5"; append_score "E5" "$e5"
echo -n "  E6 "; e6=$(score_E6); echo "$e6"; append_score "E6" "$e6"
echo -n "  E7 "; e7=$(score_E7); echo "$e7"; append_score "E7" "$e7"
echo -n "  E8 "; e8=$(score_E8); echo "$e8"; append_score "E8" "$e8"

echo -n "  G1 "; g1=$(score_G1); echo "$g1"; append_score "G1" "$g1"
echo -n "  G2 "; g2=$(score_G2); echo "$g2"; append_score "G2" "$g2"
echo -n "  G3 "; g3=$(score_G3); echo "$g3"; append_score "G3" "$g3"
echo -n "  G4 "; g4=$(score_G4); echo "$g4"; append_score "G4" "$g4"
echo -n "  G5 "; g5=$(score_G5); echo "$g5"; append_score "G5" "$g5"

echo -n "  UX "; ux=$(score_UX); echo "$ux"; append_score "UX" "$ux"

# ───── 三维度原始分数 ─────
C_score=$(( $(echo "$r1" | awk '{print $1}') + $(echo "$r2" | awk '{print $1}') + $(echo "$r3" | awk '{print $1}') + $(echo "$r4" | awk '{print $1}') + $(echo "$r5" | awk '{print $1}') + $(echo "$r6" | awk '{print $1}') + $(echo "$r7" | awk '{print $1}') + $(echo "$r8" | awk '{print $1}') + $(echo "$r9" | awk '{print $1}') ))
C_max=$(( 15+15+15+10+10+10+10+10+10 ))

E_score=$(( $(echo "$e1" | awk '{print $1}') + $(echo "$e2" | awk '{print $1}') + $(echo "$e3" | awk '{print $1}') + $(echo "$e4" | awk '{print $1}') + $(echo "$e5" | awk '{print $1}') + $(echo "$e6" | awk '{print $1}') + $(echo "$e7" | awk '{print $1}') + $(echo "$e8" | awk '{print $1}') ))
E_max=$(( 20+20+15+12+10+13+10+10 ))

G_score=$(( $(echo "$g1" | awk '{print $1}') + $(echo "$g2" | awk '{print $1}') + $(echo "$g3" | awk '{print $1}') + $(echo "$g4" | awk '{print $1}') + $(echo "$g5" | awk '{print $1}') ))
G_max=$(( 10+10+10+10+10 ))

UX_score=$(echo "$ux" | awk '{print $1}')
UX_max=$(echo "$ux" | awk '{print $2}')

# ───── C/E/G 加权聚合 (40/35/25) → 0-10 分制 ─────
# 先计算每个维度百分比，再按权重聚合为 0-10 分
C_pct=$(pct $C_score $C_max)
E_pct=$(pct $E_score $E_max)
G_pct=$(pct $G_score $G_max)

# Weighted score = (C_pct * 0.40 + E_pct * 0.35 + G_pct * 0.25) / 100 * 10
#                 = (C_pct * 0.40 + E_pct * 0.35 + G_pct * 0.25) / 10
WEIGHTED_10=$(echo "scale=2; ($C_pct * 0.40 + $E_pct * 0.35 + $G_pct * 0.25) / 10" | bc 2>/dev/null || echo "0")

# ───── DG-100: 语义质量因子调整 — 打破静态评分天花板 ─────
# 运行时数据覆盖度/噪声率/捕获率 对静态评分的质量加权
SEMANTIC_FACTOR=$(semantic_quality_factor)
WEIGHTED_10_SEMANTIC=$(echo "scale=2; $WEIGHTED_10 * $SEMANTIC_FACTOR" | bc 2>/dev/null || echo "$WEIGHTED_10")
echo "  语义质量因子: ${SEMANTIC_FACTOR} (flywheel覆盖+噪声率+捕获率) → 调整后: ${WEIGHTED_10_SEMANTIC}/10"
WEIGHTED_10="$WEIGHTED_10_SEMANTIC"

# ───── E7 校准: 对纯静态检测降权 15% ─────
if [ "$CALIBRATED" = true ]; then
  echo "  [已校准] 所有维度静态检测下调 15%（DG-28 校准偏移）"
  WEIGHTED_10=$(echo "scale=2; $WEIGHTED_10 * 0.85" | bc 2>/dev/null || echo "0")
fi

# ───── 8.6/10 门禁判定 ─────
GATE_VERDICT=""
GATE_REASON=""
if (( $(echo "$WEIGHTED_10 >= 8.6" | bc -l 2>/dev/null || echo "0") )); then
  GATE_VERDICT="[Meta-Oracle: ACCEPT]"
  GATE_REASON="C/E/G 加权总分 ${WEIGHTED_10}/10 >= 8.6 阈值"
elif (( $(echo "$WEIGHTED_10 >= 5.0" | bc -l 2>/dev/null || echo "0") )); then
  GATE_VERDICT="[Meta-Oracle: ADVISORY]"
  GATE_REASON="C/E/G 加权总分 ${WEIGHTED_10}/10 < 8.6 阈值 — 建议修正但不阻断"
else
  GATE_VERDICT="[Meta-Oracle: REJECT]"
  GATE_REASON="C/E/G 加权总分 ${WEIGHTED_10}/10 < 5.0 阈值 — 强烈建议阻断"
fi

echo ""
echo "--- 四维分数 ---"
echo "C 正确性 (40%):   $C_score/$C_max = ${C_pct}%"
echo "E 有效性 (35%):   $E_score/$E_max = ${E_pct}%"
echo "G 治理   (25%):   $G_score/$G_max = ${G_pct}%"
echo "---"
echo "C/E/G 加权总分:   ${WEIGHTED_10}/10"
echo "---"
echo "UX 用户体验:      $UX_score/$UX_max = $(pct $UX_score $UX_max)%  [独立, 不参与门禁]"
echo "---"
echo "8.6 门禁判定:     $GATE_VERDICT"
echo "  → $GATE_REASON"
echo ""

# ───── E7 过度自信免责声明 ─────
if [ "$C_score" = "$C_max" ]; then
  if ! has_runtime_data ".omc/state/subagent-usage.jsonl" && ! has_runtime_data ".omc/state/error-signals.jsonl"; then
    echo "  ⚠️ [静态评分可能虚高] C 维度满分但无可验证的运行时数据"
  fi
fi
if [ "$E_score" = "$E_max" ]; then
  if ! has_runtime_data ".omc/state/error-signals.jsonl"; then
    echo "  ⚠️ [静态评分可能虚高] E 维度满分但无错误信号数据"
  fi
fi

# ───── JSON 输出 ─────
RESULT=$(cat <<JSONEOF
{
  "generated_at": "$TS",
  "scored_by": "auto-score.sh v3",
  "methodology": "4D scoring — C/E/G weighted aggregate (40/35/25) → 0-10 scale + UX independent",
  "weights": { "C": 0.40, "E": 0.35, "G": 0.25, "UX_note": "independent, not in aggregate" },
  "dimensions": {
    "C": { "score": $C_score, "max": $C_max, "pct": $C_pct, "weight": 0.40 },
    "E": { "score": $E_score, "max": $E_max, "pct": $E_pct, "weight": 0.35 },
    "G": { "score": $G_score, "max": $G_max, "pct": $G_pct, "weight": 0.25 },
    "UX": { "score": $UX_score, "max": $UX_max, "pct": $(pct $UX_score $UX_max), "independent": true }
  },
  "aggregate": {
    "weighted_score_10": $WEIGHTED_10,
    "threshold": 8.6,
    "gate_verdict": "$GATE_VERDICT",
    "gate_reason": "$GATE_REASON"
  },
  "subscores": { $agg_scores },
  "metrics": { $agg_metrics },
  "calibrated": $CALIBRATED
}
JSONEOF
)

mkdir -p "$(dirname "$OUTPUT_FILE")" 2>/dev/null
echo "$RESULT" > "$OUTPUT_FILE"
echo "---"
echo "JSON written: $OUTPUT_FILE"
echo "$RESULT"

exit 0
