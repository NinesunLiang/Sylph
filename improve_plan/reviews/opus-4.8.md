# 对 bobi-adopted-plan.md 完整方案的全面评价

> 前面我只读到 Phase 0 + 0.5 片段，现在基于知识库全文 + 检索到的补充段落给出完整评价。

---

## 总评（更新后）

| 维度 | 评分 | 变化 |
|---|:---:|---|
| **Phase 0 实施性** | 9.5/10 | 保持 |
| **文档基建完整度** | 8.5/10 | ↑ 看到 INDEX.yaml + decisions.md |
| **状态机严谨性** | 7/10 | ↑ 看到 plan/executor schema，但 state.json 问题仍在 |
| **验收可测性** | 9/10 | ↑ 看到 omc_lint + 负向红线 |
| **双栈覆盖** | 6/10 | 保持偏薄 |
| **长期可持续** | 8.5/10 | ↑ 飞轮/Archive 后置正确 |
| **与三家对账** | 8.8/10 | 标注清晰 |
| **综合（weighted）** | **8.5/10** | ↑ 从 8.3 → 8.5 |

**最终裁决（更新）**：

```yaml
verdict: APPROVE with 2 P0 blocks
status: Phase 0 可立即施工；Phase 0.5 需先修 2 个 P0 再放行
confidence: 高（基于完整文本 + schema 细节 + lint 机制）
```

---

## 新发现的亮点（补完后才看到）

### 1. **omc_lint.py 最小校验项** `[B][G5]`

```text
12 条强制检查：
  - schema_version 存在且合法
  - token/plan/executor 三件套一致性
  - archive 前 verified_steps == total_steps
  - 不允许 decision: BASE / ENHANCE（防模型自创决策类型）
```

**评价**：**这是整个方案里对我「负向 SLO」吸收最狠的一段**。  
我要的「any FAIL ⇒ not production」在 lint 层落地了。  
尤其 **禁止 `decision: BASE/ENHANCE`** 这种防模型瞎编字段的细节——非常好。

**加分项**：把它作为 **Phase 0 S7 成本报表后的 S8'**（lint gate），变成 CI 门禁。

---

### 2. **plan.md 的 verify schema 细化到 command 级** `[O][B]`

```yaml
verify:
  - id: V-S1-CMD-1
    type: command
    command: pnpm test tests/auth/refresh.test.ts
    expect_exit: 1
    expect_match: "received 3"
```

**评价**：这比我与 Opus 的「Evidence 泛谈」更可执行——**自动验证能跑脚本**。  
这已经是 **Infrastructure-as-Code 里的 test spec 风格**，可以对接 CI。

**建议补充**：加一个 `type: oracle` 的 verify 项，预留 L2 条件 Oracle 的接口：

```yaml
verify:
  - id: V-S2-ORACLE-1
    type: oracle
    model: opus-4
    prompt_ref: artifacts/oracle_prompt_S2.txt
    threshold: confidence > 0.8
```

---

### 3. **decisions.md 任务级决策层** `[G5][B]`

```markdown
# Task Decisions
schema_version: carros.task_decisions.v1
task_id: fix-auth-001
```

**评价**：正确。解决了我之前担心的「所有决策都要立刻升 ADR 否则无处记录」的困境。  
现在有三层：

```text
Task decisions.md  →  (promoted) ADR  →  (stable) Architecture docs
   临时任务决策          跨任务复用          长期规范
```

这对应我「飞轮只写盘、不进上下文」的分级治理思想——**精准吸收**。

---

### 4. **Review front matter 的 disclosure 控制** `[G5]`

```yaml
disclosure:
  default: denied
  require_explicit_user_request: true
promoted_claims:
  - target: ADR-001#decision
    status: accepted_with_rewrite
```

**评价**：**这是三家方案里唯一明确「Review 不进默认检索」的实现细节**。  
对我「肥源门禁」的最佳响应——三方长审核不污染 Context。

**唯一担心**：`require_explicit_user_request` 若由模型判断会漂移。  
建议改成：

```yaml
disclosure:
  default: denied
  allow_if: user_message contains "读 REVIEW-GPT-CONTEXT"
```

---

### 5. **archive summary 的 `l5_autocompact_used` 字段**

```yaml
l5_autocompact_used: false
# Claude L5 AutoCompact，有损不可逆。Base 目标应接近 0。
```

**评价**：满分。这是我差分 A「禁止把 L5 当记忆」的直接落地指标。  
并且注释写明「Base 目标应接近 0」——**这就是我要的负向 SLO 措辞**。

---

## 仍需修正的 2 个 P0（重申 + 加强）

### 🔴 P0-1：`state.json` vs `token.json` 双轨问题未解决

文中多处出现：

```text
state.json  # 唯一运行状态机（兼容旧 token.json）  [O]
```

但 **plan.md / executor.md / omc_lint 校验项里全部写的是 `token.json`**。

**这说明实际代码路径仍是 token.json，state.json 只是文档层改名意图**——但没钉死迁移策略。

**我的最终裁决（必须二选一）**：

#### 选项 A（推荐）：保留 token.json，废弃 state.json 迁移

```yaml
phase0_state_file_policy:
  canonical: .omc/tokens/<task_id>.json  # 或现有路径
  add_fields:
    - schema_version: carros.token.v1
    - version: int (CAS)
    - last_modified_at / last_modified_by
  forbid:
    - 新建 state.json 作为第二写入路径
    - 从 token 迁移到 state 的数据重命名
  reason: |
    工具链、lint、用户习惯已在 token 路径上；
    改名不改协议本质；避免迁移期双文件风险。
```

#### 选项 B：激进迁移到 state.json（不推荐 Phase 0）

```yaml
phase1_state_migration:  # 注意：不在 Phase 0
  old: .omc/tokens/<id>.json
  new: .omc/tasks/<id>/state.json
  migration_tool: python3 .claude/scripts/migrate_token_to_state.py
  validation:
    - omc_lint 通过
    - 历史任务可 Resume
    - 双写期 ≤ 1 周
  rollback: 保留 token.json 备份 90 天
```

**我强烈建议 Phase 0 走选项 A**，把 state.json 迁移推到 Phase 1 或完全不做。

---

### 🔴 P0-2：七件套目录结构与「3 天 Phase 0」时间矛盾

Phase 0 说 3–4 天；Phase 0.5 要上：

```text
.omc/tasks/<id>/
  ├── manifest.yaml
  ├── state.json
  ├── plan.md
  ├── working-set.yaml
  ├── handoff.md
  ├── evidence.jsonl
  ├── context/
  │   ├── capsule.current.md
  │   └── receipts.jsonl
  └── artifacts/
```

加上 `docs/INDEX.yaml` + Review front matter。

**这不是 1 周能干完的——除非你已有 80% 文件只是重命名**。

**我的收敛（必须）**：

```yaml
phase0_deliverables:  # 3-4 天
  must_have:
    - token.json (with CAS)
    - artifacts/ + tool_store
    - status --hot
    - pretool_gate
    - omc_lint 基础版
  
  can_defer:
    - manifest.yaml → 可与现有任务入口合并
    - working-set.yaml → 用 pretool_gate 硬编码规则先顶
    - capsule.current / receipts → Phase 1
    - INDEX.yaml → Phase 1

phase0.5_deliverables:  # 1 周
  must_have:
    - handoff.md v2 (Resume Preflight)
    - evidence.jsonl (与 verify 绑定)
    - working-set.yaml 落地
    - omc_lint 完整 12 条
  
  can_defer:
    - docs/INDEX.yaml → 轻量版或 Phase 1
    - Review front matter → Phase 1
    - capsule 快照 → Phase 1
```

**红线**：Phase 0 不得因「补目录结构」拖到 7 天；Phase 0.5 不得因「写 INDEX」拖到 2 周。

---

## 与我（Grok-4.5）8 个差分的最终对账（完整版）

| Grok 差分 | 波比吸收情况 | 证据 | 评分 |
|---|---|---|:---:|
| **A 最便宜压缩优先** | 政策层强吸收 | `l5_autocompact_used` 字段 + 红线 | ✅ 9/10 |
| **B Prompt cache 稳定** | 工程落地最佳 | S4 tool_store + S6 composition | ✅ 10/10 |
| **C flash/opus 路由** | **仍缺失** | 未见模型路由表 | ⚠️ 4/10 |
| **D OpenCode 提前 0.5** | **明确 defer** | 文中未提，知识库可能有但未见 | ⚠️ 5/10 |
| **E 副作用三界** | Resume Preflight 有硬闸 | W1 `IN_FLIGHT/UNKNOWN → BLOCKED` | ✅ 8/10 |
| **F 双预算（token+注意力）** | 用 composition 8K 等价 | S6 可控 ≤8K + 固定 16K | ✅ 8.5/10 |
| **G 负向 SLO** | **满分落地** | omc_lint 12 条 + S7 红线 | ✅ 10/10 |
| **H 飞轮不进 HEAD** | 正确后置 Phase 2 | decisions.md 分层 | ✅ 9/10 |

**吸收率（更新）**：6/8 强落地 + 2/8 待补 = **75% 工程化吸收 + 25% 政策层吸收**。

### 对 C（模型路由）的补救建议

在 Phase 1（L2 工作流）前增加：

```yaml
# .omc/config/model_routing.yaml
schema_version: carros.routing.v1

routes:
  - task: tick_execute
    condition: level == L1
    model: deepseek-v4-flash
    reason: 低风险快速执行
  
  - task: verify_self
    model: deepseek-v4-flash
    reason: 自验无需强推理
  
  - task: plan_step
    condition: level == L2 OR complexity > 0.7
    model: opus-4
    reason: 架构/高复杂需长程一致
  
  - task: oracle_verify
    condition: risk.level == high OR retry_count >= 2
    model: opus-4
    budget_cap: 0.05  # USD per call
    reason: 条件触发，预算封顶
```

并在 S7 cost_report 增加：

```bash
model_breakdown:
  flash: 78% of tokens, $0.03
  opus: 22% of tokens, $0.12
  oracle: 0 calls
```

---

### 对 D（OpenCode）的声明建议

在 Phase 1 前增加：

```yaml
# Platform Scope Declaration
schema_version: carros.platform_scope.v1

phase0_to_1:
  target_platform: claude_code_only
  reason: |
    Hermes 当前工作流基于 Claude Code；
    Phase 0 聚焦 Context Boom，不涉及平台切换。

opencode_support:
  earliest_phase: phase1.5_or_phase2
  non_negotiable_when_enabled:
    - session_roles: [execute, retrieve, review, govern]
    - single_state_writer: true  # 多会话仍只一条写 token.json 路径
    - non_destructive_prune: true  # SQLite compact 标记时间戳，不物理删
    - audit_chain: receipts.jsonl 保留
  
  defer_reason: |
    OpenCode 多会话+审计链是 Phase 2 治理能力；
    Phase 0 优先稳定 Claude 单平台注入与压缩。
```

---

## 验收门更新（基于完整方案）

### Phase 0 Exit（任一 FAIL 则不进 0.5）

```yaml
must_pass:
  metrics:
    - controllable_median_tokens <= 8000
    - total_median_tokens <= 24000
    - tool_full_in_context_rate <= 0.05
    - l5_as_memory == 0
    - cache_hit_rate >= 60% (if observable)
  
  behavioral:
    - same_tool_content_same_preview == true
    - hot_card_default == true
    - pretool_self_test: all 6 rules green
    - omc_lint: basic 8 rules pass (full 12 in 0.5)
  
  regression:
    - H1/H2/H3 median <= 24K
    - H1/H2/H3 p95 <= 48K
    - no review markdown in prompt (H1/H2/H3)
  
  deliverables:
    - .omc/metrics/r0_baseline/ (3-5 sessions)
    - .omc/metrics/r0_after/ (H1/H2/H3)
    - CLAUDE.md <= 100 lines
    - tool_store.py + pretool_gate.py
    - cost_report.py with red lines
```

### Phase 0.5 Exit（任一 FAIL 则不进 Phase 1）

```yaml
must_pass:
  file_structure:
    - token.json (or state.json 二选一钉死)
    - handoff.md with NOT_SOURCE_OF_TRUTH header
    - evidence.jsonl schema valid
    - working-set.yaml exists
    - omc_lint full 12 rules pass
  
  resume:
    - resume_without_token_json == 0
    - resume_preflight blocks IN_FLIGHT effects
    - handoff_parsed_as_state == 0 (code review)
  
  verify:
    - verified_without_evidence == 0
    - plan.verify schema matches executor output
  
  cost:
    - oracle_call_rate == 0 for L1 tasks
    - l5_autocompact_used close to 0
```

---

## 最终建议（给决策用）

### 1. 立即可开工的范围（Hermes Phase 0，不必等）

```text
✅ S1 基线测量
✅ S2 CLAUDE.md Slim
✅ S3 status --hot
✅ S4 tool_store + 稳定 preview
✅ S5 pretool_gate 六闸
✅ S6 composition 固化
✅ S7 cost_report + 红线
✅ S8 H1/H2/H3 回归
```

### 2. Phase 0.5 前必须先修的（挂起施工直到修完）

```text
🔴 P0-1: token.json vs state.json 二选一钉死（选项 A 推荐）
🔴 P0-2: 七件套瘦身到 Phase 0.5 可交付范围（去掉 capsule/INDEX）
🟠 P1: handoff 加强 NOT_SOURCE_OF_TRUTH 头部措辞
🟠 P1: Hot Card token 预算验证（不只 chars）
```

### 3. Phase 1 前必须补的（不影响 0/0.5 开工）

```text
🟡 模型路由表（flash/opus 场景切分）
🟡 OpenCode 平台 scope 声明（或明确 defer）
🟡 verify type: oracle 预留接口
🟡 回归场景补 H4/H5/H6（长 log / 多轮 / watermark）
```

---

## 综合评价（最终版）

### 对三家方案的整合质量

| 方面 | 评价 |
|---|---|
| **吸收 Grok** | 75% 工程化 + cache 稳定性满分吸收 |
| **吸收 Opus** | token/plan/evidence 结构 + Hot Card 等价 |
| **吸收 GPT-5.6 Sol** | decisions.md / INDEX / Review front matter |
| **来源标注** | 清晰（每段标 [G]/[O]/[G5]/[B]） |
| **超越三家** | omc_lint 最小校验项是唯一落地的负向 SLO |

### 相对原始 8/8 方案的进步

```text
✅ 砍掉过度形式化（15+ Schema → 7 文件 + lint）
✅ 压缩优先级从理论变可验收脚本
✅ 验收从功能清单变负向红线
✅ Oracle/飞轮正确后置
✅ 状态机 schema 细化到 command 级可执行
```

### 未来风险（需持续监控）

```text
⚠️ 状态文件双轨若不及时收敛会裂化工具链
⚠️ 七件套若一次性上线会拖累 Phase 0.5 时间
⚠️ OpenCode 推太晚可能失去多会话治理窗口
⚠️ 无模型路由会让成本看板缺解释力
```

---

## 最终裁决（Decision Record）

```yaml
decision_id: GROK-EVAL-BOBI-20260713
evaluator: Grok-4.5 (AI 编码 Agent 双栈治理顾问)
evaluated: bobi-adopted-plan.md (Hermes Agent 方案)
timestamp: 2026-07-13

verdict: CONDITIONAL APPROVE

approve_scope:
  - Phase 0 (S1-S8) 全量
  - Phase 0.5 核心（handoff/evidence/working-set/lint）

conditional_on:
  p0_blocks:
    - token.json vs state.json 迁移策略二选一钉死
    - 七件套范围收敛到可 1 周交付子集
  
  p1_before_phase1:
    - 模型路由表
    - OpenCode scope 声明
    - handoff NOT_SOURCE_OF_TRUTH 加强

score:
  correctness: 9/10
  implementability: 9.5/10 (Phase 0); 7/10 (Phase 0.5 若不收敛)
  dual_stack_fit: 6.5/10
  sustainability: 8.5/10
  integration_quality: 9/10
  overall: 8.5/10

comparison:
  vs_opus: "更务实，可施工性高 1.5 档"
  vs_gpt_sol: "避免了补丁堆积，负向 SLO 更强"
  vs_grok_self: "工程化落地超越纯设计稿"

recommendation: |
  这是目前唯一达到「Sprint-Ready」精度的 CarrorOS 实施方案。
  批准 Phase 0 立即开工；Phase 0.5 修完 P0 再放行；Phase 1+ 按序推进。
  
  Hermes 应优先完成 Phase 0 的 8 个 Step，交付 before/after 对比报告，
  证明可控 token 从 19K → 8K，再进入文档基建阶段。

next_action:
  for_hermes: "开始 S1 基线测量，输出 .omc/metrics/r0_baseline/SUMMARY.md"
  for_decision_maker: "批准 Phase 0 预算与时间；挂起 Phase 0.5 直到 P0 修复"
```

---

如果需要，我下一条可以给：

1. **P0 修复的具体 diff patch**（直接改 bobi-adopted-plan.md 的 8 行条款）  
2. **Hermes Phase 0 的 Sprint Board**（按 Git commit 拆 14 个票 + 验收标准）  
3. **omc_lint.py 的完整实现建议**（基于你们现有 Python 工具链风格）