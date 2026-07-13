# Grok-4.5 差分方案：只列「不一样」的地方

抱歉刚才中断。下面是**我的方案相对 Opus-4.8 / GPT-5.5sol 的差分对照**——两边已经写过且我同意的，一律不展开。

---

## 0. 结果先讲清楚

| 维度 | 我的裁决 |
|---|---|
| **总体是否成立** | ✅ 可以做，但要砍掉「完整治理」幻想，走 **MVG（Minimum Viable Governance）** |
| **对 Opus-4.8** | 战略方向对（MVP 优先），但 **Context 稳定性与双栈边界仍不够狠** |
| **对 GPT-5.5sol** | 补丁化很强，但容易变成「8/8 继续扩表」，实施路径偏重 |
| **我的最终站位** | **先止血 → 再双栈安全 → 最后飞轮**；Oracle/Archive/飞轮全部后置 |

**一句话结果**：同意两边 70% 共识；我只追加 8 个「不重复」的硬差分，并砍掉 4 个两边都偏肥的点。

---

## 1. 相同共识（不列细节）

这些我**直接继承**，不再重写：

- `token.json` 作唯一真相源 + CAS  
- `handoff.md` 只导航、不回填状态  
- D0～D5 渐进披露 + 每轮 Hot Tail  
- L1 无 Oracle / L2 条件 Oracle  
- VerifyGate 必须 Evidence，禁止 compact 后跳过验证  
- Resume 只读盘，不信 transcript  

---

## 2. 我与两边的 8 个硬差分

### 差分 A — 压缩优先级铁律：「最便宜优先，最重最后」

**Opus/GPT** 多在谈 watermark / handoff / L2 checkpoint。  
**我明确要求平台原生压缩阶梯先跑满，再谈 handoff。**

```text
Claude Code（必须这顺序，不可跳级抢 LLM 摘要）:
  L1 工具结果落盘+稳定预览  → 无损可回滚
  L2 历史裁剪               → 无损可回滚
  L3 微压缩                 → 近似无损
  L4 上下文折叠（~90%）     → 有损但可回滚
  L5 AutoCompact            → 有损不可逆（目标：触发率 <5%）

OpenCode:
  Prune(hidden) 保留 ~40K 垫 + 最近 2 回合 + skill 输出不剪
  → 不够才起隐藏 Agent 做 5-header 摘要（标记 lossy）
  → compact 只写时间戳，SQLite 永不物理删（审计关键）
```

**可观测指标**：`l5_ratio`、`l4_rollback_count`、`prune_vs_summary_ratio`  
**治理含义**：治理工具若一上来就 LLM 摘要 = 设计失败。

---

### 差分 B — Prompt Cache 稳定性（Claude 独有，两边几乎没落地）

这是 **Claude Code 表现抖动的头号元凶**，必须一等公民：

```text
规则：
1. 同一 tool_result 的 preview 文本必须字节级复用（ContentReplacementState）
2. 替换决策一旦确定，禁止同 turn 再抖动
3. Head(D0) + 稳定 token 前缀不因 middle 切片变化而重排
4. 监控 cache hit rate，< 60% 视为回归
```

**与 Opus 差异**：Opus 的 Capsule 重建只谈「每轮重建」；我要求 **重建 ≠ 前缀洗牌**——Tail 可动，**稳定前缀锁定**。

---

### 差分 C — Flash / Opus 是「场景路由」，不是「能力升降级」

你明确要求 deepseek-v4-flash 场景优化 + opus 智能决策。我给死路由：

| 场景 | 模型 | 理由 |
|---|---|---|
| search / test / 读文件摘要 | **deepseek-v4-flash** | 便宜、吞吐高 |
| L1 小修执行 | flash | 风险可控 |
| L2 规划 / 架构 / 争议裁决 | **opus-4.8** | 需要长程一致性 |
| Oracle（条件触发） | opus，预算 **<$0.05/次** | 绝非每 step |
| OpenCode 隐私/本地 | Ollama/本地 + BYOK | 合规优先 |

**成本目标**（可观测，非口号）：单 task 从 ~$0.16 → ~$0.04 区间，成功率掉幅 ≤3pt。  
**与两边差异**：不搞 Multi-Judge / Meta-Oracle；flash 失败 ≠ 立刻上 opus，先看 **confidence + residual risk**。

---

### 差分 D — OpenCode「会话角色 + 单一写者」提前到 Phase 0.5（不是 Phase 2）

Opus 把 OpenCode 放到 60～90 天；我反对。

**原因**：OpenCode 的护城河是 **多会话并行 + SQLite 非破坏 prune**。如果你 90 天才接，等于放弃其治理可塑性。

```text
OpenCode 最早接入（Phase 0 末）：
  Session Roles: execute | retrieve | review | govern
  硬约束：只有 govern/execute 之一可以写 token.json（单一 State Writer）
  retrieve/review：只产出 Artifact，不得改 state
  /sessions 分离：bugfix / feature / review 并行 ≠ 多写者
```

这是 **OpenCode 路径专属**，不能照搬到 Claude subagent。

---

### 差分 E — 外部副作用三界回滚图（Git ≠ Checkpoint ≠ Effect）

两边都有 external_effects，但**回滚边界常混谈**。我画死：

```text
界 1 文件修改：Git / Claude Checkpoint → 无损可回滚
界 2 任务状态：token/plan CAS 版本 → 可回退到 last VERIFIED
界 3 外部副作用：API/部署/DB → 默认 UNKNOWN 阻断 Resume
               必须状态机：PENDING → IN_FLIGHT → COMMITTED | FAILED
               不可逆副作用：禁止自动回滚，只生成补偿清单
```

**Resume Preflight 新增硬闸**：任一 `IN_FLIGHT/UNKNOWN` ⇒ **BLOCKED**，不得装成 CONTINUE。

---

### 差分 F — Context Capsule 双预算制（token 预算 + 注意力预算）

Opus 的 U-型注意力约 15～25K 是对的。我加约束：

```text
Token Soft Cap: 25K（Flash 抖动警示线）
Attention Cap:
  HEAD  ≤ 2K  且 80% 内容 30 分钟内不改
  MIDDLE 可压
  TAIL  ≤ 800，每轮重生成，但 schema 固定（字段不加减）
禁止：
  review 全文 / 三方审核长文 默认进 system
  test log 全文回灌
  plan 全文每轮塞入
```

这是对「肥源（fat sources）」做门禁——比再发明一个 Schema 更重要。

---

### 差分 G — 验收红线用「负向 SLO」而非「功能完成清单」

两边有很多 ACC-xxx 通过项。我只要 7 条**失败即否决（any FAIL ⇒ not production）**：

```yaml
negative_slo:
  - resume_without_token_json == 0
  - verified_without_evidence == 0
  - l5_as_memory == 0
  - handoff_parsed_as_state == 0
  - oracle_share_of_tasks > 10%  → FAIL
  - cache_hit_rate_p50 < 60%     → FAIL   # Claude Code path
  - prune_physical_delete == true → FAIL   # OpenCode path
```

功能清单可以是 43 项；**上线裁决看负向红线**。

---

### 差分 H — 飞轮「只写盘、不进上下文」

两边都有 Error DNA / Knowledge Patch。我加硬隔离：

```text
Error DNA / Patch 默认落 .omc/knowledge/**
写回 CLAUDE.md / AGENTS.md 必须经 Memory Writeback Gate
进 Context 仅通过 D2 白名单 + token 预算
禁止：飞轮数据默认塞进 HEAD / Hot Tail
```

否则会重新制造 Context Boom——飞轮过量等于自杀。

---

## 3. 我砍掉两边容易过肥的 4 点

| 砍掉 | 理由 |
|---|---|
| Multi-Judge / Meta-Oracle | 需求是「辅助决策」不是合规法庭 |
| Archive Transaction 完整事务层进 MVP | Phase 2 再做；Phase 0 用 tar+hash 够 |
| state.json 迁移争论 | 死：保留 token.json，只加 schema_version |
| OpenCode 等到 90 天才做 | 改成 Phase 0.5 接入会话角色 + prune 审计 |

---

## 4. 我的 30 天路径（与 Opus 不同）

```text
Week 1：token.json CAS + VerifyGate L1 + Evidence JSONL
Week 2：Hot Tail + working-set 白名单 + 肥源门禁
Week 3：Handoff/Resume + 外部副作用三界 + Checkpoint 前硬闸
Week 4：Claude L1～L4 优先 + cache 稳定性指标
         同步：OpenCode Session Roles + non-destructive prune

不在 30 天：
Oracle 系统、Archive 事务、飞轮自动化、Multi-Judge
```

**Exit 标准（只要这 5 个）**：

1. 删 transcript 仍能 Resume  
2. Context 无线性膨胀（soft ≤25K 中位数）  
3. 无 DONE without Verify  
4. L5 占比 <5% 或 OpenCode 未物理删  
5. flash 任务均摊成本在目标区间上下  

---

## 5. 对你现在这套方案的最终结果判定

```yaml
verdict:
  status: CONDITIONAL APPROVE
  meaning: "架构可落地，但不要按 10/10 全量终稿一次上线"
  
  accept_from_opus:
    - MVP 三阶段
    - token.json 正式化 + CAS
    - handoff 非真相源
    - L1/L2 Oracle 条件化

  accept_from_gpt:
    - 补丁化纠错意识
    - Gate 可组合

  my_non_negotiables:
    - cheapest-first compaction
    - prompt cache 稳定前缀
    - OpenCode 多会话+单写者更早接入
    - 负向 SLO 做上线闸
    - flash/opus 场景路由
    - 副作用三界分离

  go_live_now:
    components:
      - token.json + plan + evidence + handoff
      - VerifyGate L1
      - Capsule(D0/D1/D2/D3)
      - Resume preflight
    deferred:
      - Oracle Warp
      - Archive 公证事务
      - Learning pipeline 自动化
      - Meta 审视结构

  overall_score:
    correctness: 9/10
    implementability: 8/10（若砍后）; 5/10（若全搬 Opus 终稿）
    dual_stack_fit: 我高于 Opus 半档（OpenCode 提前 + Claude cache）
```

---

## 6. 你该怎么选

| 选择 | 何时合适 |
|---|---|
| **纯 Opus-4.8 终稿** | 团队 ≥5 且要一次做完治理史诗 |
| **GPT-5.5 增量补丁** | 已有 8/8 跑着，只修破洞 |
| **我的差分（推荐）** | 要 **30 天见效**、双栈真接、成本/稳定性可观测 |

**推荐落地顺序**：  
`Opus 状态机内核` + **我的 8 差分** − `Oracle/Archive/飞轮早期复杂度`。

---

如果你要，我下一条可以直接输出：

1. **可粘贴的 `.claude/settings.json` + OpenCode config 差分补丁**，或  
2. **一张「与 Opus 10 轮对照表：采纳/替换/砍掉」机器可读 YAML**。