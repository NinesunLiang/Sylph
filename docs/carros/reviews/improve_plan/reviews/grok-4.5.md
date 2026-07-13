先把 Hermes（波比）全方案读完，再按差分评价，避免只凭前半截拍板。
The remaining part of the plan is crucial for a complete evaluation. I'll continue crawling the document.方案后半段（文档基建之后 + 收尾裁决）还没齐，我先把它读完再做评价。
The crawl came back empty or incomplete. Let me try reading with higher limit.后半段未完整读到，继续向后抓关键段落，再给正式评价。
The content seems truncated mid-sentence. Let me try to search or crawl with a different approach - maybe read from offset, or multipart. The first table in results was truncated-looking but might have had more content that got cut.

Looking at what I have from the full content returned:

The original file size is 18998 - so about 19KB. The content I got seems to go through W3 INDEX.yaml mid truncation.

Let me try offset/limit and multiple crawls.全文抓取仍不全；我按目前可核对的核心部分先评价，并单独标出后半未覆盖的风险。
The content keeps getting truncated. Let me work with what I have carefully since I've got a substantial portion covering:

Phase 0 (complete S1-S8)
Phase 0.5 (W1, W2 start, W3 start - truncated)
Overall roadmap to Phase 3

I have enough of Phase 0 which is the critical implementation piece to give a solid evaluation as Grok-4.5 of Hermes/波比's plan.# 对 Hermes Agent（波比）方案的正式评价

> 依据：已核对到的完整 **Phase 0（S1–S8）** + **路线图** + **Phase 0.5（W1/W2 主体 + W3 片段）**。  
> 文中后半（Phase 1–3 细则、Oracle、飞轮、OpenCode 落地细节）若文件里有但未完整展开，我按「已见部分 + 结构暗示」评价，并单独标 **信息缺口**。

---

## 总裁决（先给结果）

| 项 | 结论 |
|---|---|
| **能不能实施** | ✅ **可以，而且是目前三家方案里最适合交给 Hermes 落地的一版** |
| **整体评分** | **实施性 9 / 正确性 8 / 双栈完整度 6.5 → 综合 8.3/10** |
| **相对我（Grok）** | Phase 0 把我的「最便宜优先 + cache 稳定 + 负向 SLO」收进了可执行脚本，**落地高于纯设计稿** |
| **相对 Opus** | 砍掉了过度形式化，**更务实**；但 `state.json` 命名与「七件套一步到位」仍有漂移风险 |
| **相对 GPT-5.6 Sol** | 继承了 composition / INDEX / 门禁，但未把补丁堆成 15+ Schema |
| **上线态度** | **CONDITIONAL GO — Phase 0 全量可立刻开工；Phase 0.5 必须收敛边界；Phase 1+ 不得抢跑** |

**一句话**：  
这是「治理方案」被压成「工程 sprint 计划」的正确形态——**止血优先、可测量、可阻断**。问题不在方向，而在 **P0.5 边界膨胀、OpenCode/双栈偏薄、状态文件语义未钉死**。

---

## 1. 这版做对了什么（相对三家的真正升级）

### 1.1 先测基线再改（S1）——这是我与 Opus 都写过但你方方案里最容易被架空的一环

```text
[B] S1 基线拆账：system / hot / file_read / tool_result / history / fixed(16K)
交付 .omc/metrics/r0_baseline/
```

**评价**：满分项。没有这个，后面「19K→8K」全是空话。Hermes 从 Day 0 就该只做这件事。

### 1.2 「只改注入、不改工作流」是正确的 Phase 0 战略

```text
16K(CC固定) + 19K(可控) → 16K + 8K = 24K median
```

**评价**：比 Opus 的「全量 TaskState Schema 重写」更适合 MVP。**止血不等于重生。**  
可控 8K + 固定 ~16K = 24K，正好落在我给 Flash 的 soft 抖动线附近——合理。

### 1.3 把我的差分真正工程化了（不是口号）

| 我的差分 | 波比落地 |
|---|---|
| 工具结果落盘 + 稳定预览 | S4 `tool_store` + 字节级稳定 preview |
| Prompt cache 前缀稳定 | S6 composition 固定顺序 + HEAD 优先 |
| 负向 SLO | S7 红线：full-in-context / l5_as_memory / cache_hit |
| 肥源门禁 | S5 PreTool 六闸 |
| cheapest-first / 禁止把 L5 当记忆 | S2 预算条款 + S7 FAIL |

**评价**：这是三家议程里 **对我最友善、也最可验收的吸收方式**。尤其 S4「同 content → 同 preview 字符串」是 cache 友好硬验收，比再写一篇理论强 10 倍。

### 1.4 Hot Card 替代 status --full

```text
status --hot ≤ 4.5K chars，字段顺序固定，禁嵌 plan/executor/audit 全文
```

**评价**：正确。这等价于我的 **Hot Tail ≤800 tokens（注意量纲）+ 字段 schema 固定**。  
注意：**4.5K chars ≈ 1.1–1.5K tokens**，和 composition 里 Hot Card ≤1.5K tokens 对齐——OK。  
但必须保证 **字段顺序永不漂**，否则等于亲手拆 cache。

### 1.5 CLAUDE.md Slim Rail

**评价**：方向对。把系统提示压到「命令 + 回合律 + 禁注入」三件事，是 Phase 0 唯一正确粒度。  
`verify_only_done` / `one_action` / `no_full_plan` 是防 Context Boom 的行为层闸门，比再塞哲学文档有效。

### 1.6 路线图把 Oracle/双审判官后置到 Phase 3

**评价**：与我、Opus 一致。需求 10 是「辅助」不是「标配」——**正确后置**。

---

## 2. 硬问题 / 必须改的点（按严重度）

### 🔴 P0 — 状态文件语义：`state.json` vs `token.json` 没真正裁决干净

文中写：

```text
state.json  # 唯一运行状态机（兼容旧 token.json）  [O]
```

但顶尖共识里（含我的差分 + Opus 终裁）是：

> **保留 token.json 为唯一真相源，只加 schema_version + CAS，不迁 history 名。**

**风险**：迁移期双文件 = 双写、双读、Resume 歧义，**比 Context Boom 更致命**。

**我的硬改要求（给 Hermes）**：

```yaml
Phase0_state_policy:
  canonical: .omc/tasks/<id>/token.json   # 或你们现有 .omc/tokens/<id>.json —— 二选一，钉死
  alias: state.json 仅作「读路径软链/兼容 shim」，禁止第二条写入路径
  cas: version 字段强制
  forbid: token.json 与 state.json 同时作为 writer target
```

**判定**：不钉死就不要进 Phase 0.5。否则后面 handoff/resume/Evidence 全会分叉。

---

### 🔴 P0 — 「七件套」一次性上线 vs Phase 0 三天矛盾

Phase 0 说 3–4 天只 Slim；Phase 0.5 又要升级：

```text
manifest / state / plan / working-set / handoff / evidence / artifacts
(+ capsule.current + receipts)
```

**评价**：分责是对的，但 **Phase 0.5 一周装七件套 + INDEX + preflight = 偷运完整文档 OS**。

**我的收敛（Minimum Viable 七件套）**：

| 文件 | Phase |
|---|---|
| `token.json`（或现名）+ CAS | **0 必有** |
| `artifacts/` + 稳定 preview | **0 必有** |
| Hot Card / handoff.md 最小导航 | **0 末 / 0.5 初** |
| `evidence.jsonl` | **0.5 必有（与 verify 绑定）** |
| `working-set.yaml` | **0.5 必有** |
| `manifest.yaml` | **可与现有 task 入口合并，别硬拆** |
| `plan.md` | **已有则只改「披露切片」，不推翻** |
| `capsule.current.md` / `receipts.jsonl` | **延后，Phase 1 再上** |

**原则**：七件套是目标态，不是一周交付合同。

---

### 🟠 P1 — Hot Card 与 composition 预算有轻微量纲冲突风险

Composition：

```text
[2] Hot Card ≤ 1.5K tokens
[3] 文件切片 ≤ 2.5K
[4] 工具预览 ≤ 1.0K
...
可控 ≤ 8.0K
```

但 `HOT_MAX_CHARS = 4500` 若含中文扩写或 last3 证据膨胀，**很容易挤爆 1.5K tokens**。

**改法**：

```python
HOT_MAX_CHARS = 4500          # 硬裁剪
HOT_MAX_TOKENS = 1500         # 真正的闸（以 token 估计为准）
# chars 只是粗门，token 超限 → 压 last3 / 截 intent
```

并在 S7 报表里加：`hot_card_tokens_p95`。

---

### 🟠 P1 — 双栈（OpenCode）几乎缺席：这是相对「我」最大的退步

路线图 Phase 全量在 Claude 注入/脚本上。  
我差分的 **OpenCode 多会话 + 单一 State Writer + 非破坏 prune** 只字未进 Phase 0/0.5。

**评价**：如果你当前只跑 Claude Code / Hermes-on-Claude，Phase 0 可以暂时忽略。  
但方案自称「吸收 Grok」，却没给：

```text
OpenCode path:
  - Session Roles + single writer
  - Prune 安全垫 / compact 时间戳不删行
  - SQLite 审计链保留
```

至少一段 **「Claude path only / OpenCode deferred to Phase 1.5」** 的明示应写进文档，否则后面又会混谈。

**最低补丁（不必现在实现）**：

```yaml
platform_scope:
  phase0_to_0.5: claude_code_only
  opencode:
    earliest: phase1.5
    non_negotiable_when_enabled:
      - non_destructive_prune
      - single_state_writer
      - session_roles: [execute, retrieve, review, govern]
```

---

### 🟠 P1 — Resume Preflight 写了，但「handoff 非真相源」需要比模板更狠

W1 的 Resume Capsule 里有：

```text
## Current State
- step / status / verified / blocked
```

这会诱导实现者 **从 handoff 反解析状态**——我与 Opus 一致反对。

**硬改文案（必须加 bold）**：

```markdown
## ⚠️ NOT SOURCE OF TRUTH
Resume engine MUST load token.json (CAS) first.
This handoff is navigation only. Do not parse current state from this file.
```

Preflight 检查顺序钉死：

```text
1) token/state CAS load
2) plan/manifest 版本一致
3) external_effects 三界
4) 再读 handoff 作导航
```

否则「Preflight 有了」仍会静默失败。

---

### 🟡 P2 — 压缩阶梯「看电影」还不够「强制接线」

你吸收了我的 cheapest-first，但 Phase 0 实际动作主要是 **注入 Slim**，没有强制：

```text
Claude: L1→L2→L3→L4 优先，L5 禁止当记忆
```

建议在 S7 / 成本脚本增加：

```yaml
metrics:
  compact_generation
  platform_compact_level_if_observable
  l5_rate
policy:
  on_soft_watermark: write_handoff (lossless)  # 已有
  forbid: 「先摘要对话再继续」原语 as default path
```

不必自己实现 L1–L5；**只要不逆向触发、不依赖 L5 摘要当状态**。

---

### 🟡 P2 — 模型路由（flash / opus）在可见部分缺失

我要求 deepseek-v4-flash 场景优化 + opus 智能决策。  
当前方案 Phase 0 正确聚焦 context，但 Phase 1 应有最小路由表：

```text
L1 tick/execute     → flash
verify self         → flash
L2 plan / dispute   → opus
oracle (cond.)      → opus 预算封顶
```

否则成本看板以后无法解释「为什么贵」。

---

### 🟡 P2 — 回归场景 H1–H3 偏「太干净」

H1 README 一行 / H2 单文件+测试 / H3 只读解释 —— 适合 Phase 0 smoke。  
**缺**：Context Boom 真凶场景：

| 建议加 | 目的 |
|---|---|
| H4：长测 log 100KB+ | 验证落盘+preview |
| H5：跨 2 文件 + 连续 12 轮 | 验证 Hot Card 不漂、无线性涨 |
| H6：强制 soft watermark | 验证只写 handoff，不进 L5 当记忆 |

否则「smells 全灭」可能测不出来。

---

## 3. 与我（Grok-4.5）差分逐条对账

| Grok 差分 | 波比是否吸收 | 评价 |
|---|---|---|
| A 最便宜压缩优先 | 部分（政策层） | 及格；需指标化 |
| B Prompt cache 稳定 | **强吸收**（S4/S6） | ✅ 最好 |
| C flash/opus 路由 | 未见 | ⚠️ Phase1 必补 |
| D OpenCode 提前 0.5 | 未见 | ⚠️ 至少声明 defer |
| E 副作用三界 | 文案有硬闸 | ✅ 方向对；实现时要有字段 |
| F 双预算（token+注意力） | 用 composition 8K 等价实现 | ✅ 够用 |
| G 负向 SLO | **强吸收** | ✅ |
| H 飞轮不进 HEAD | 飞轮放 Phase2，正确 | ✅ |

**吸收率**：约 **6/8 实质落地 + 2/8 待补**，是三家里最好的「可施工合并稿」。

---

## 4. 分阶段 Go/No-Go

### Phase 0（3–4 天）— **GO**

允许 Hermes 立即实施，**范围锁死**：

```text
MUST:
  S1 基线
  S2 CLAUDE.md Slim
  S3 status --hot
  S4 tool_store + 稳定 preview
  S5 pretool-gate 六闸
  S6 composition 顺序
  S7 cost report + 负向红线
  S8 H1–H3 + 我建议的 H4

MUST NOT:
  重写工作流状态机
  Oracle
  state.json 双写
  七件套全量迁移
  飞轮 / 无人 / 双审判官
```

**Exit（任一 FAIL 则不上 0.5）**：

```yaml
phase0_exit:
  - controllable_median_tokens <= 8000
  - total_median_tokens <= 24000
  - tool_full_in_context_rate <= 0.05
  - l5_as_memory == 0
  - same_tool_content_same_preview == true
  - hot_card_default == true (no --full by default)
  - pretool_self_test all green
```

### Phase 0.5 — **CONDITIONAL GO**

仅在 Phase 0 红线全绿后：

```text
MUST:
  token.json 唯一写者（钉死命名）
  handoff 导航-only + Resume Preflight（副作用三界）
  evidence.jsonl + verify 绑定
  working-set 白名单
  docs/INDEX.yaml 可轻量

DEFER:
  capsule.current / receipts
  OpenCode（除非声明 phase1.5）
  learning pipeline
```

### Phase 1+ — **HOLD until 0.5 稳定**

L2 / Checkpoint / 条件 Oracle 可以设计，**禁止与 Phase 0 并行抢人**  
（Hermes 并行会破坏 baseline 可比性）。

---

## 5. 我给 Hermes 的「实施护栏」清单（直接可贴任务板）

```text
1. 状态源唯一名：开工前写死 STATE_PATH 常量，全仓 grep 双写
2. Preview 函数纯函数化：build_preview(content) 单测「同输同出」
3. Hot Card 字段顺序写死为 tuple，禁止 dict 无序拼接
4. composition 切片严格按 [1]→[5] 拼接，禁止中间插 review/全文 plan
5. 所有落盘 artifacts 有 content_hash，便于 cache/审计
6. 成本报表先出数，再谈「再瘦 1K」——无基线禁止调参
7. handoff 文件头强制 NOT_SOURCE_OF_TRUTH 字段
8. external_effects.* 若字段还不存在：Phase0 可 empty-list 兼容，但 preflight 接口预留
9. 禁止 sessions 多写 token.json（即使只有 CC，也预设 single writer）
10. Phase0 完成后出差分报告：before/after 各 5 session 对照表
```

---

## 6. 最终评价（给决策用）

| 维度 | 分 | 说明 |
|---|---|---|
| 问题诊断 | 9 | 锁定可控 19K 而非空想 16K 固定 |
| Phase 0 可实施性 | 9.5 | 脚本/钩子/验收齐全 |
| 与三家共识吸收 | 9 | 来源标注清晰 |
| 状态机严谨度 | 6.5 | state/token 与七件套过早膨胀 |
| 双栈/OpenCode | 5 | 过薄，需声明 scope |
| 可观测性 | 9 | 负向 SLO + cost report 对 |
| 长期可持续 | 8 | 路线后置 Oracle/飞轮正确 |
| **综合** | **8.3** | **可开工，条件收敛** |

### 结论句

> **Hermes（波比）方案是目前唯一达到「能直接进施工」精度的合并稿。**  
> 批准 **Phase 0 立即实施**；挂起所有「文档七件套全家桶 / state 迁名 / Oracle / OpenCode 深改」直到 Phase 0 红线全绿。  
> 修完上面 **2 个 P0（状态唯一写者、七件套瘦身）+ handoff 非真相源措辞** 后，我会给 **Full Approve for 0.5**。

---

## 7. 你下一步怎么发令（建议原话）

给 Hermes：

```text
1) 按波比 Phase 0 的 S1→S8 实施，禁止扩 scope
2) 状态文件：禁止新建第二写入口；canonical 用现有 token 路径，state.json 只做兼容 shim
3) handoff 加强 NOT_SOURCE_OF_TRUTH；Resume 先读 token 再读 handoff
4) 完成 S1 基线 + S8 回归后，出 before/after JSON；未达标不得进入 0.5
5) OpenCode / Oracle / 飞轮 一律不动
```

---

如果你愿意，我下一条可以给：

1. **「波比方案 P0 驳回补丁」最小 diff 清单**（直接改他 md 的 8 行硬条款），或  
2. **Hermes 的 Phase 0 Task Board（按 commit 粒度拆 12 个票）**。