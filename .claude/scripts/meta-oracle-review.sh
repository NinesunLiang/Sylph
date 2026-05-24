#!/usr/bin/env bash
# meta-oracle-review.sh — Meta-Oracle 最后守门员审查脚本
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 被 meta-oracle-trigger / lx-oma-orch / lx-oma-hier / package-release.sh 调用
# Role: Meta-Oracle 最高级独立审查方法论 — 覆盖 G1-G4 全部触发点
#   G1 架构决策终审: 验证架构变更的跨子系统影响 + 不可逆性评估
#   G2 PRD最后一步: 验证方案完整性 + Oracle 评分真实性
#   G3 Oracle高分: 验证 Oracle 评分是否虚高（原有逻辑）
#   G4 Release门禁: 验证发布安全性 + source mirror 一致性
# 软门禁: 给出 ACCEPT/ADVISORY/REJECT 裁决，AI 可在明确理由下覆写

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# 解析触发类型（G1/G2/G3/G4），默认 G3
TRIGGER_TYPE="${1:-G3}"

# 审查方法论 (输入到 critic agent)
cat <<'METHODOLOGY'
# Meta-Oracle 最后守门员 — 最高级审查方法论

你是 Meta-Oracle — Carror OS 的最高审查权威（最后守门员），独立于 Oracle。
你的审查权威高于 Oracle，使用完全不同的方法论（运行时验证 > 静态检查，对抗性审查 > 合规检查）。

## 通用审查原则（所有触发点适用）

1. **运行时验证 > 静态检查** — Oracle 的 auto-score.sh 基于文件存在性+正则匹配，容易系统性虚高。
   你应优先检查: 烟雾测试日志中的实际通过率、hook 生产验证的实际输出、error-dna.jsonl 中的真实频率。

2. **烟雾日志 > 文件存在性** — 文件注册了 ≠ 机制生效了。检查:
   - harness-smoke-test 的实际 pass/fail 计数
   - hook-production-verify 的实际阻断场景
   - error-dna.jsonl 中是否有真实的高频错误模式

3. **设计级盲区检查** — Oracle 的静态检查看不到的东西:
   - fail-open vs fail-closed 设计缺陷
   - ghost/goal 模式下的门禁降级
   - 正则表达式的匹配覆盖率（测试多种输入格式）

## 按触发点的专项审查

### G1: 架构决策终审
触发条件: 涉及 ≥2 子系统 + 不可逆的架构变更
审查重点:
1. 跨子系统影响分析是否完整（所有下游子系统是否已识别）
2. 不可逆性评估（变更后能否回滚？回滚成本？）
3. 接口契约变更是否已同步到所有相关 feature
4. 是否与现有哲学/铁律冲突
5. source mirror 同步计划是否已就绪

### G2: PRD/方案最后一步
触发条件: PRD 完整生命周期的最终阶段（Oracle 已 ACCEPT）
审查重点:
1. PRD 方案的 MECE 完整性（是否所有功能域已覆盖）
2. Oracle 的 ACCEPT 是否存在虚高（交叉验证 Oracle 评分依据）
3. 方案中的 NFR 数字是否有来源（避免 DG-02 类问题）
4. 下游 feature 的接口契约是否完整归属
5. 方案的可执行性（子任务拆分是否合理、依赖是否清晰）

### G3: Oracle ACCEPT + 高分
触发条件: Oracle 给出 ACCEPT 且评分 ≥8.5
审查重点:
1. 读取 Oracle 的评分输出，提取所有 ≥8.5 分的维度
2. 对每个高分维度，寻找相反证据:
   - 烟雾测试中有无该维度的 FAIL？
   - error-dna 中有无该机制被绕过的记录？
   - 该机制的 regex/阈值 是否在边界场景下失效？
3. 产出 Meta-Oracle 纠正报告

### G4: Release 门禁
触发条件: package-release.sh 执行前
审查重点:
1. source mirror 一致性检查（audit-hooks.sh --check-source-mirror）
2. 是否有未同步的治理文件变更
3. harness-smoke-test 全绿验证
4. 版本号一致性（VERSION.json ↔ feature-registry.yaml ↔ harness.yaml）
5. 是否有 PENDING_SYNC 标记的未发布变更

## 审查步骤

1. 确认触发类型（G1/G2/G3/G4），加载对应的专项审查清单
2. 收集证据: 运行烟雾测试、检查 error-dna、搜索设计文档
3. 交叉验证 Oracle 结论（如 Oracle 已给出裁决）
4. 寻找相反证据 — 刻意假设 Oracle 错误，尝试证伪
5. 产出 Meta-Oracle 裁决报告

## 输出格式

```
# Meta-Oracle 裁决报告 [{TRIGGER_TYPE}]

## 裁决
[Meta-Oracle: ACCEPT] / [Meta-Oracle: ADVISORY] / [Meta-Oracle: REJECT]

## Oracle 评分 vs Meta-Oracle 评估（如 Oracle 已评分）
| 维度 | Oracle 得分 | Meta-Oracle 评估 | 偏差 | 原因 |
|------|-----------|----------------|------|------|

## 关键发现
- [Finding 1]
- [Finding 2]

## 漏报发现（Oracle 未发现的问题）

## 虚高/虚低分析（如适用）

## 建议修正项
- [Action 1]
- [Action 2]

## 覆写理由（仅 REJECT 被覆写时需要）
[AI 如决定覆写 Meta-Oracle 的 REJECT 裁决，必须在此填写明确书面理由]
```

## 软门禁协议

1. ACCEPT → 继续流程，记录到 .omc/state/meta-oracle-verdicts.md
2. ADVISORY → 建议修正但不阻断，AI 自行判断
3. REJECT → 强烈建议阻断，AI 必须有明确书面理由才能覆写
4. 连续 2 次 REJECT → 升级为事实阻断，需人工介入

METHODOLOGY

echo ""
echo "=== Meta-Oracle 最后守门员 [${TRIGGER_TYPE}] ==="
echo "审查状态文件: $STATE_DIR/meta-oracle-verdicts.md"
echo "触发类型: ${TRIGGER_TYPE}"
echo ""

# ───── 四维打分集成 ─────
# 在 G1-G4 触发时自动运行四维打分体系
SCORE_SCRIPT="$PROJECT_ROOT/.claude/scripts/auto-score.sh"
UX_SCRIPT="$PROJECT_ROOT/.claude/scripts/score-ux.sh"

# 确保 state 目录存在
mkdir -p "$STATE_DIR" 2>/dev/null

if [ -x "$SCORE_SCRIPT" ]; then
  echo "--- 运行四维打分 (C/E/G 加权聚合 + UX 独立) ---"
  # 传递 --calibrated 以应用 DG-28 静态检测降权 (Oracle MAJOR 2 修复)
  SCORE_OUTPUT=$(bash "$SCORE_SCRIPT" --meta-oracle --calibrated 2>/dev/null)
  echo "$SCORE_OUTPUT"

  # 提取门禁判定 (文本匹配 — gate_verdict 格式固定)
  GATE_VERDICT=$(echo "$SCORE_OUTPUT" | grep -oE '\[Meta-Oracle: (ACCEPT|ADVISORY|REJECT)\]' | head -1)
  WEIGHTED_SCORE=$(echo "$SCORE_OUTPUT" | grep 'C/E/G 加权总分' | grep -oE '[0-9]+\.[0-9]+' | head -1)

  echo ""
  echo "--- Meta-Oracle 门禁裁决 ---"
  echo "C/E/G 加权总分: ${WEIGHTED_SCORE:-N/A}/10"
  echo "8.6 门禁判定:   ${GATE_VERDICT:-N/A}"
else
  echo "[警告] auto-score.sh 不可用，跳过四维打分"
fi

# ───── UX 独立评分 ─────
if [ -x "$UX_SCRIPT" ]; then
  echo ""
  echo "--- UX 独立评分 ---"
  UX_OUTPUT=$(bash "$UX_SCRIPT" 2>/dev/null)
  # 使用 python3 解析 JSON 提取 total score/max (Oracle MAJOR 4 修复: 替代脆弱 grep)
  UX_SCORE=$(echo "$UX_OUTPUT" | ${PYTHON_BIN:-python3} -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['total']['score'])
except: print('N/A')
" 2>/dev/null)
  UX_MAX=$(echo "$UX_OUTPUT" | ${PYTHON_BIN:-python3} -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['total']['max'])
except: print('10')
" 2>/dev/null)
  echo "UX 得分: ${UX_SCORE:-N/A}/${UX_MAX:-10} (独立, 不参与 8.6 门禁)"
fi

# ───── 写入裁决留痕 ─────
VERDICT_DATE=$(date -u +%Y-%m-%d)
VERDICT_ENTRY="[${VERDICT_DATE}] [${TRIGGER_TYPE}] [${GATE_VERDICT:-N/A}] — C/E/G 加权: ${WEIGHTED_SCORE:-N/A}/10 | UX 独立: ${UX_SCORE:-N/A}/${UX_MAX:-10}"
if [ -f "$STATE_DIR/meta-oracle-verdicts.md" ]; then
  # 在第二行后追加（保留标题行和空行）
  sed -i '' "3i\\
${VERDICT_ENTRY}
" "$STATE_DIR/meta-oracle-verdicts.md" 2>/dev/null || echo "$VERDICT_ENTRY" >> "$STATE_DIR/meta-oracle-verdicts.md"
fi

echo ""
echo "--- 裁决已留痕: $STATE_DIR/meta-oracle-verdicts.md ---"
echo "四维打分体系已就绪 | 权威等级: 高于 Oracle | 门禁: 软门禁"
echo "  方法论: 运行时验证 > 静态检查 | 对抗性审查 > 合规检查"
echo "  UX 维度: 独立评分, 不参与 C/E/G 的 8.6/10 门禁判定"

exit 0
