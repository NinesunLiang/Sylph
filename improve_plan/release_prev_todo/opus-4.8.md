# Opus-4.8 对 Hermes Agent CarrorOS Base 实施的最终审计

我重新以 **Opus-4.8 的视角**审视这四份文件。我的关注点不是"规范是否完备"，而是：

1. **物理边界是否守住**（Context 是否真的被限制住）
2. **失效点是否被防御**（崩溃后能否恢复）
3. **成本锚点是否可观测**（Token/Cache/L5 是否有实测数据）
4. **状态外置是否无损**（磁盘状态是否真的可以重建会话）
5. **双栈机制是否分离**（Claude Code vs OpenCode 是否有清晰边界）

---

## 执行摘要

```yaml
opus_4_8_verdict: CONDITIONAL_APPROVE_AS_WORKING_PROTOTYPE
status: "可工作原型，距离生产级尚有距离"
confidence: HIGH

核心判断:
  - Context 物理边界基本守住（Hot Card + Artifact + Reviews 隔离）
  - 状态恢复路径清晰（token.json + handoff）
  - 但缺少成本实测数据、水位运行时、CAS 并发测试
  - Phase 1-3 完成度被高估

实际完成度:
  phase_0_context_slim: "80% — 功能有，median/P95 数据不足"
  phase_0_5_doc_infra: "85% — 结构清晰，恢复安全测试缺"
  phase_1_l2_governance: "50% — 骨架在，水位未接入是硬伤"
  phase_2_flywheel: "45% — 飞轮跑了，但无人运行硬化不足"
  phase_3_dual_judge: "15% — 仅报告结构，无独立性证明"

综合评分: 6.8/10
```

---

## 一、Opus 视角的核心关注点

我和 GPT-5.6 Sol / Grok-4.5 的差异：

| 维度 | GPT Sol | Grok | Opus（我） |
|---|---|---|---|
| **根因定位** | Memory/Context 未分离 | 渐进式披露失败 | **State Injection 最小化未落地** |
| **核心机制** | 文档记忆系统 | Context Router | **Hot Card + 物理围栏 + 无损落盘** |
| **第一优先级** | 文档图谱 | 分层加载 | **防 L5 AutoCompact 当记忆** |
| **验收重点** | 协议化披露 | 各层 token 达标 | **median/P95 + cache 稳定 + 成本实测** |
| **治理哲学** | 规范约束 | 智能分发 | **物理边界 + 可恢复** |

**一句话差异**：

> GPT 想建「文档记忆系统」，Grok 想建「上下文路由」，我想建「物理围栏 + 极简注入 + 无损回滚」。

---

## 二、从失效点倒推：四份文件能防御什么

### 2.1 已防御的失效点 ✅

#### ✅ 失效点 1：长工具输出污染 Context

**证据**：

```text
250KB → 1.3K preview
artifacts/ 完整保存
```

**评价**：**PASS**。原文在磁盘，模型只见预览，符合「无损可回滚」原则。

**但缺陷**：
- 没证明 preview 字节级稳定（同内容多次 store 是否完全相同）
- 没证明 Artifact 有 SHA-256 内容寻址
- 没证明 head/tail 都保留

---

#### ✅ 失效点 2：Review 长文回灌

**证据**：

```text
28 review files / 191K tokens isolated
reviews 路径 → continue: false
```

**评价**：**PASS**。肥源门禁生效，这是 Phase 0 的核心成果。

---

#### ✅ 失效点 3：AGENTS.md 膨胀

**证据**：

```text
43 行
无 Oracle 引用（L1）
```

**评价**：**PASS**。Slim Rail 基本守住。

**但缺陷**：
- Oracle 规则冲突（全局禁止 vs L2 启用）未解决
- 没证明 AGENTS.md 是否冻结前缀（Prompt Cache 友好）

---

#### ✅ 失效点 4：handoff 被当状态真相源

**证据**：

```text
NOT_SOURCE_OF_TRUTH 标注
token.json 唯一状态源
```

**评价**：**PASS**。这是相比旧版的重大进步。

**但缺陷**：
- archive 自动写 handoff 语义可疑（已完成任务不应有 next_action）
- 没证明删除 handoff 后仍能从 token.json 恢复

---

#### ✅ 失效点 5：状态机双写混乱

**证据**：

```text
token.json 唯一状态源，CAS revision
```

**评价**：**文档层 PASS**。`token.json` vs `state.json` 冲突已在文档统一。

**但缺陷**：
- **没有 CAS 并发冲突测试**
- 没证明两个 writer 同 revision 时第二个真的失败
- 没证明冲突被记录到 error-dna 或 audit

---

### 2.2 未防御的失效点 ❌

#### ❌ 失效点 6：L5 AutoCompact 当记忆

**文档声明**：

```text
l5_autocompact_used: false
目标应接近 0
```

**问题**：**没有实测数据**。

报告只有：

```text
注入 token 1,069
估算 total ~17K
```

但没有：

```yaml
missing_metrics:
  - l4_count: ?
  - l5_count: ?
  - l5_ratio: ?
  - 样本数: ?
  - P95: ?
```

**裁决**：**数据缺失，无法验证 L5 是否真的接近 0。**

---

#### ❌ 失效点 7：Context 线性增长

**需要证明**：

```text
多轮会话后 Context 不线性增长
每轮重建 Capsule
旧工具预览被替换
```

**当前证据**：

```text
S6 固定 composition
```

**问题**：
- 没有 30+ turns 的实测数据
- 没有 context_growth_per_turn 指标
- "固定 composition"是设计意图，不是运行时证据

**裁决**：**未充分证明。**

---

#### ❌ 失效点 8：Cache 破碎

**需要证明**：

```text
同一 content 的 preview 字节级一致
AGENTS.md 冻结前缀
Hot Card 字段顺序稳定
```

**当前证据**：

```text
Hot Card 157 chars
同一 tool_content 多次 store，preview 相同（文档声称）
```

**问题**：
- 没有 cache hit rate（可能不可观测）
- 没有 stable_prefix_hash_change_rate 代理指标
- 没有 snapshot test 证明 Hot Card 确定性

**裁决**：**缓存稳定性未充分证明。**

---

#### ❌ 失效点 9：外部副作用恢复不安全

**需要证明**：

```yaml
external_effects:
  IN_FLIGHT: BLOCK
  UNKNOWN: BLOCK
```

**当前证据**：

```text
Resume Preflight: 0 issues
```

**问题**：
- 只证明了"正常状态可恢复"
- 没证明"危险状态被阻断"
- 没有 H-IN-FLIGHT / H-UNKNOWN 测试

**裁决**：**长期无人运行安全未证明。**

---

#### ❌ 失效点 10：水位未接入，无降级

**kernel.md 明确承认**：

```text
三段式水位（Phase 1+）
当前为骨架定义，运行时未接入。
```

**这直接导致**：

- Phase 1 L2 治理不完整
- Phase 2 无人运行无物理保护
- 40%/70% 水位不生效

**裁决**：**BLOCKER。**

---

## 三、从成本锚点倒推：可观测性是否到位

### 我要求的运行时指标

```yaml
context_metrics:
  controllable_median: REQUIRED
  controllable_p95: REQUIRED
  total_median: REQUIRED
  total_p95: REQUIRED
  context_growth_per_turn: REQUIRED
  sample_turns: ">= 30"

cache_metrics:
  cache_hit_rate: "可选（可能不可观测）"
  stable_prefix_hash_change_rate: REQUIRED

compaction_metrics:
  l4_count: REQUIRED
  l5_count: REQUIRED
  l5_ratio: REQUIRED

cost_metrics:
  token_usd_per_session: REQUIRED
  token_usd_per_completed_task: REQUIRED
  oracle_cost_share: REQUIRED

correctness_metrics:
  verified_without_evidence: 0
  resume_without_token_state: 0
  cas_conflicts_detected: REQUIRED
```

### 当前实际提供

```yaml
provided:
  - hot_card_size: 157 chars
  - single_sample_inject: 1069 tokens
  - estimated_total: ~17K
  - negative_slo_claimed: "全绿"

missing:
  - 真实样本分布（median/P95）
  - L5 实际占比
  - 成本实测值
  - 增长率
  - Cache 稳定性代理指标
```

**裁决**：**成本可观测性不足，Phase 0 验收不完整。**

---

## 四、从状态恢复倒推：磁盘状态是否真的无损

### 4.1 恢复路径设计 ✅

```text
token.json (CAS) → handoff.md (导航) → Resume Preflight → 继续
```

**评价**：**路径清晰，基本正确。**

### 4.2 缺失的恢复测试 ❌

```yaml
missing_tests:
  H-HANDOFF-DELETE: "删除 handoff 后仍能从 token 恢复"
  H-NO-TOKEN: "只有 handoff、无 token，必须 BLOCK"
  H-CAS-CONFLICT: "两个 writer 同 revision，第二个失败"
  H-IN-FLIGHT: "外部副作用 IN_FLIGHT，BLOCK"
  H-UNKNOWN: "外部副作用 UNKNOWN，BLOCK"
  H-COMPACT-E2E: "真实 /compact 后继续执行并验证 revision"
  H-ARCHIVED: "已归档任务不得被 handoff 重启"
```

**当前只证明了**：

```text
9 个 active token.json
2 个 handoff.md
Resume Preflight: 0 issues
```

**这只是"正向路径通"，不是"负向路径阻断"。**

**裁决**：**恢复安全测试不足。**

---

## 五、从双栈机制倒推：平台边界是否清晰

### Claude Code 路径

**证据充分**：

```yaml
- settings.json hooks
- pretool-gate.py
- .claude/scripts/
- /compact 恢复（声称）
- AGENTS.md 注入
```

**裁决**：**Claude Code Base RC1 水平，85% 完成度。**

---

### OpenCode 路径

**证据缺失**：

```yaml
missing:
  - opencode config
  - SQLite audit
  - non-destructive prune
  - 最近两回合保护
  - 40K safety margin
  - skill output 保护
  - 多会话角色
  - single state writer lease
```

**裁决**：**OpenCode 未实施或未举证，0~15% 完成度。**

---

## 六、从 kernel.md 矛盾倒推：报告是否过度声称

### kernel.md 自述

```text
三段式水位（Phase 1+）
当前为骨架定义，运行时未接入。
```

### dual-judge-report.md 声称

```text
Phase 1 L2 治理: 10/10
Phase 2 飞轮+无人: 10/10
阶段门 Phase 0 → 0.5 → 1 → 2 → 3 全部打开
完整 Base 态
阻断条件：无
```

### 逻辑判定

```python
if kernel.md == "watermark NOT integrated":
    Phase_1_complete = FALSE
    Phase_2_production_unattended = FALSE
    "all gates open" = FALSE
    "阻断条件无" = FALSE
```

**裁决**：**报告结论明显强于实际证据，BLOCKER。**

---

## 七、Opus 视角的 Phase 裁决

### Phase 0：Context Slim

```yaml
status: PROVISIONAL_PASS
score: 7.5/10

已实现:
  - Hot Card
  - 工具落盘
  - Reviews 隔离
  - AGENTS Slim

缺失:
  - 真实 median/P95 样本
  - L5 实际占比
  - Cache 稳定性证明
  - 成本实测值
```

---

### Phase 0.5：文档与恢复

```yaml
status: PROVISIONAL_PASS
score: 7.8/10

已实现:
  - token.json 唯一源
  - handoff 非真相源
  - INDEX 路由
  - task-profiles

缺失:
  - 恢复负向测试（IN_FLIGHT/UNKNOWN/CAS）
  - archive/handoff 边界修正
```

---

### Phase 1：L2 治理

```yaml
status: PARTIAL_PASS
score: 5.0/10

已实现:
  - Error DNA
  - Retry 配置
  - 条件 Oracle

BLOCKER:
  - 水位运行时未接入（kernel.md 自述）
  - 外部副作用三界未证明
```

---

### Phase 2：飞轮与无人

```yaml
status: EXPERIMENTAL_PASS
score: 4.5/10

已实现:
  - 飞轮骨架
  - loop detection
  - budget pause

缺失:
  - 多次长任务
  - CAS 并发安全
  - 外部副作用安全
  - 生产级无人运行硬化
```

---

### Phase 3：双审判官

```yaml
status: NOT_PROVEN
score: 2.0/10

已实现:
  - 报告结构

缺失:
  - 双模型独立性
  - Context 隔离
  - Disagreement 处理
  - 全部 P3 测试
```

---

## 八、Opus 视角的最终裁决

```yaml
═══════════════════════════════════════════════
  Opus-4.8 最终裁决
═══════════════════════════════════════════════

question:
  "是否已实现完整体的 base 版本的 CarrorOS 重构任务？"

answer: |
  NO — 未实现完整体 Base。
  
  实际达成：Claude Code Base 可工作原型
  
  物理边界基本守住（Hot Card + Artifact + Reviews）
  状态恢复路径清晰（token.json + handoff）
  
  但：
  - 水位运行时未接入（kernel.md 自述）
  - 成本实测数据不足
  - 恢复安全测试缺失
  - Phase 3 无证据
  
  报告"Phase 0→3 全部打开"明显过度声称。

release_recommendation: |
  CarrorOS Base Prototype v0.8
  
  - Claude Code 核心骨架已成型
  - 可用于受控实验
  - 不可用于生产级无人运行
  
  距离 1.0 生产版需要：
  - 接入水位运行时
  - 补全恢复安全测试
  - 补全成本可观测数据
  - 修复 23/23 测试

opus_score: 6.8/10

confidence: HIGH

blocker_count: 3
  1. kernel.md 水位矛盾
  2. 恢复安全测试缺失
  3. Phase 3 无证据
```

---

## 九、Opus 独特关注：必须立即修复的物理边界漏洞

### 1. Hot Card 必须派生，不可编辑

```yaml
hot_card:
  source: [token.json, plan.md, executor.md]
  writable: false
  deterministic: true
  snapshot_test: required
```

### 2. Artifact preview 必须内容寻址

```python
artifact_id = f"sha256:{sha256(content).hexdigest()}"
preview = {
    "artifact_id": artifact_id,
    "head": utf8_slice(normalized, 1200),
    "tail": utf8_tail(normalized, 600),
}
```

### 3. CAS 必须有并发冲突测试

```bash
# 必须补的测试
H-CAS-01: A、B 同时读 revision=7
H-CAS-02: A 写 revision=8 成功
H-CAS-03: B 用 expected_revision=7 写入失败
H-CAS-04: 最终内容仍为 A 的状态
```

### 4. 外部副作用必须有恢复阻断

```yaml
resume_preflight:
  NOT_STARTED: continue
  APPLIED: continue_or_verify
  IN_FLIGHT: BLOCK  # 必须测试
  UNKNOWN: BLOCK     # 必须测试
```

---

## 十、对比三家评价

| 评价者 | 综合评分 | 核心关注 | 我的独特点 |
|---|:---:|---|---|
| **Grok-4.5** | 8.3/10 | 双栈治理 + 负向 SLO | 更关注规范和模型路由 |
| **GPT-5.6 Sol** | 7.0/10 | 证据独立性 + 测试覆盖 | 更关注文档系统和协议化 |
| **Opus-4.8（我）** | **6.8/10** | **物理边界 + 失效点 + 成本实测** | **更关注可恢复和可观测** |

**我的评分最保守，因为**：

1. 我更看重**实测数据**而非设计意图
2. 我更看重**失效后能否恢复**而非正向路径通
3. 我更看重**物理边界守住**而非规范约束完备
4. 我认为 **kernel.md 的矛盾是硬阻断**，不能被"报告声称"覆盖

---

## 最终建议

```yaml
release_as: "CarrorOS Base Prototype v0.8"

can_use_for:
  - 受控实验
  - L1 短任务
  - 单会话开发

cannot_use_for:
  - 生产级无人运行
  - 多会话并发
  - 长期状态演进

next_steps:
  immediate:
    - 接入水位运行时（修正 kernel.md 矛盾）
    - 补 H-CAS / H-IN-FLIGHT / H-UNKNOWN 测试
    - 修复第 23 项测试并重跑
  
  before_1_0:
    - 30+ turns 真实样本分布
    - L5 实际占比
    - 成本实测值
    - Phase 3 独立性证明
```