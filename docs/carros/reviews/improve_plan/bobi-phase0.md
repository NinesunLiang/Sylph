# 波比 Phase 0 — Token Slim 执行方案

> 本方案对标 Grok 4.5 / Opus 4.8 / GPT-5.6 Sol 三份 improve_plan。
> 相同处不展开，只说为什么不同。

---

## 一、与三家模型的共同立场（简略列示）

- ✅ Context Boom 是第 1 号问题。35K~320K/轮不可接受。
- ✅ CLAUDE.md 必须 Slim 到 ≤100 行 / ≤6K chars，审核长文迁 `docs/reviews/`。
- ✅ Hot Card（≤4.5K chars）是唯一高频状态注入。
- ✅ 工具结果必须落盘 `artifacts/`，模型只见 ≤2K 稳定预览。
- ✅ PreTool 读盘门禁：≤2 文件/tick、禁 reviews/、禁 secrets/。
- ✅ `VerifyGate` 是唯一完成裁决者。
- ✅ 恢复不依赖 transcript，依赖文件状态。
- ✅ L1 零 Oracle，L2 条件 Oracle。
- ✅ 每轮 Context 应重建，不无限追加。
- ✅ 前缀稳定是 cache 命中的前提。

**以上 10 条我不展开，三家已充分论证。我的方案全部继承。**

---

## 二、核心差异：我对 Phase 0 的重新定义

三家的共同问题：**Phase 0 塞了太多 Phase 1 的事。**

| 模型 | Phase 0 范围 | 波比的判断 |
|------|-------------|-----------|
| **Opus 4.8** | Context 止血 + L1 工作流 + Handoff + Resume + VerifyGate | **过宽**。Handoff/Resume 是 Phase 1 |
| **Grok 4.5** | token CAS + VerifyGate + Evidence + Hot Tail + 肥源门禁 + Handoff/Resume + 外部副作用三界 | **过宽+过深**。副作用三界是 Phase 2 |
| **GPT-5.6 Sol** | P0=瘦 CLAUDE + reviews 隔离 + Artifact 落盘 + 状态/证据分离 + token baseline(此处合理)；但 P1 就要建 docs/INDEX + 文档记忆系统 | **P0 合理但 P1 太早**。文档系统是 Phase 1 末到 Phase 2 |
| **波比** | **严格只做 Token Slim**：不碰 Handoff、不碰 L1 工作流、不碰文档系统、不碰 OpenCode | 减法就是速度 |

### 我的理由：Token Slim 的成功标准不是"架构完备"，是"每轮 token 降下来"

当前最大痛苦是**每轮 35K~320K**。这跟 Handoff 做得好不好、文档系统有没有 INDEX、OpenCode 有没有 session roles **没有直接关系**。

Phase 0 的 exit criteria 只有一个：

> **改造后的 3 条回归任务：median ≤ 24K（含 16K 固定）、P95 ≤ 48K、tool_full_in_context_rate ≈ 0**

达到这个标准，Phase 0 就 pass。**不需要 L1 工作流、不需要 Resume、不需要文档记忆系统。**

这些东西是 Phase 1 的内容——等 Phase 0 瘦下来再慢慢加，不会有人因为 Context 不膨胀而投诉你。

---

## 三、与 Grok 4.5 的差异说明

### 差异 1：OpenCode Session Roles 提到 Phase 0.5 → 我改为 Phase 1

**Grok 的理由**：OpenCode 的护城河是多会话并行 + SQLite 非破坏 prune，90 天才接等于放弃治理可塑性。

**我的理由**：
- Phase 0 的目标是**压 token**。OpenCode Session Roles（execute/retrieve/review/govern）跟 token 降幅无关。
- 当前 CarrorOS 运行在 Claude Code，OpenCode 路径并未激活。为了"治理可塑性"在 Phase 0 做 OpenCode 适配，会分散核心目标。
- OpenCode 接入自己就是一个小工程（Plugs/Hooks 体系 + SQLite 审计），不应该跟 Token Slim 一起做。

**结论**：Grok 的战略前瞻性正确，但时机不对。Phase 1 再做。

### 差异 2：外部副作用三界回滚图 → 我放 Phase 2

**Grok 的理由**：Git ≠ Checkpoint ≠ Effect，三界分离防回滚混乱。

**我的理由**：
- 这跟 Phase 0 "压 token" 的目标无关。
- 当前 CarrorOS 的外部副作用主要是文件和 git，还没有 API 部署/DB 变更的场景。
- 三界分离是架构设计，不是瘦身工具。

**结论**：Grok 的架构判断正确，但我认为 Phase 2（L2 长任务阶段）再做。

### 差异 3：负向 SLO 做上线闸 → 我完全采纳并增强

**Grok 的理由**：7 条失败即否决。

**我的版本**：

```yaml
negative_slo:
  - resume_without_token_json == 0           # 删会话找不到状态 → FAIL
  - verified_without_evidence == 0            # 无证据声称完成 → FAIL
  - tool_full_in_context_rate > 0.05          # 工具全文回灌率 >5% → FAIL
  - l5_as_memory == 1                         # L5 AutoCompact 当记忆 → FAIL
  - cache_hit_rate_p50 < 60%                 # Claude 前缀不稳 → FAIL（仅 Claude 路径）
  - median_in > 12000                         # 中位数超标 → FAIL
  - p95_in > 40000                            # P95 超标 → FAIL
```

比 Grok 多了 2 条可量化的 token 红线。

---

## 四、与 Opus 4.8 的差异说明

### 差异 1：Phase 0 不做 L1 工作流

**Opus Phase 0 包含**：L1 快速工作流 + 基础 VerifyGate。

**我的理由**：
- 当前 CarrorOS **已经有** `carros_base.py init → tick → verify → archive` 工作流。
- 它不是"没有"，是"对低阶模型太胖"。
- 先瘦身，再优化工作流。不要在胖的状态下改流程——你改的流程本身可能因为 Context 膨胀而不被执行。

**Phase 0 只做**：改注入逻辑（CLAUDE.md → Slim、status → --hot、工具 → 落盘 + 预览、读盘 → 门禁）。不改工作流。

### 差异 2：Phase 0 不做 Handoff/Resume

**Opus Phase 0 包含**：handoff.md 简单交接 + 简单 Resume。

**我的理由**：
- Handoff/Resume 解决的是"跨会话状态不丢"，不是"每轮 token 太高"。
- 当前 CarrorOS **已有** session-handoff 机制（`handoff.md` + `session-summary.md`）。它不够好，但不会导致 320K。
- Phase 1 再重构 Handoff——等 Context 瘦下来之后，Handoff 的内容也会更少。

### 差异 3：三阶段路线（0/1/2）→ 我改成五段路线

Opus 的 0/1/2 划分简洁，但我认为中间缺一个过渡：

| 阶段 | Opus 定义 | 波比定义 |
|------|----------|---------|
| Phase 0 | Context 止血 + L1 工作流 | **Token Slim（严格瘦身）** |
| Phase 0.5 | — | **轻量文档基建（INDEX + manifest 分离 + Handoff 重构）** |
| Phase 1 | L2 + 长任务 | **L2 工作流 + Oracle 条件接入 + OpenCode** |
| Phase 2 | 飞轮 + 多栈 | **飞轮 + 多 Agent + 副作用治理** |
| — | — | **Phase 3：全量治理闭环** |

理由：Phase 0（Token Slim）和 Phase 1（L2 工作流）之间有一个**文档基建断档**。如果不建 `docs/INDEX.yaml` 和 manifest/state 分离，Phase 0 瘦下来的 Context 在 Phase 1 复杂任务下会重新膨胀。

---

## 五、与 GPT-5.6 Sol 的差异说明

### 差异 1：四平面架构 → 我只在 Phase 0.5 引入，Phase 0 不做

**GPT-5.6 的起点**：从 P0 就开始建文档记忆系统。

**我的理由**：
- 四平面架构（Memory / Retrieval / Context / Governance）是对的，**但它本身不直接降低 token**。
- 降低 token 的是：CLAUDE.md 砍掉、Hot Card 替代全量状态、工具落盘替代全文回灌。
- 文档记忆系统是**保持 token 不反弹**的机制，不是**降低 token**的机制。

Phase 0 做前者，Phase 0.5 做后者。顺序不能反。

### 差异 2：P0-P5 六阶段 → 我合并为四阶段

GPT 的 P0~P5 太细，容易在执行中迷失优先级。我合并：

| 我的阶段 | 对应 GPT | 目标 |
|---------|---------|------|
| Phase 0 | P0（止血） | **median ≤ 12K** |
| Phase 0.5 | P1 + P2（文档记忆 + Context Compiler 雏形） | 瘦下来的 Context 有文档支撑，不反弹 |
| Phase 1 | P3 + P4 + P5 部分（治理链 + 双栈 + 模型路由） | L2 可用，OpenCode 可用 |
| Phase 2 | P5 余项（L2 深度 + 多 Agent + 飞轮） | 无人模式可用 |

### 差异 3：23 条不变量 → 我减到 12 条

GPT 写了 23 条系统不变量（INV-01~INV-22）。质量很高，但对 Base 过重。

我的 Phase 0 只立 12 条铁律：

```text
# 真相
INV-01  聊天不是任务状态源。状态在 `.omc/`。
INV-02  transcript 是审计记录，不是正常恢复入口。
INV-03  LLM Summary 是有损导航，不是真相源。
INV-04  完整工具输出 → artifacts；evidence 只存索引。

# 执行
INV-05  每个 tick 只执行一个可验证动作。
INV-06  只改 allowed_paths；denied_paths 优先级最高。
INV-07  只有 VerifyGate 可以把 step 标记为 VERIFIED。

# Context
INV-08  每轮 Context 从 文件 重建，不在旧 transcript 上追加。
INV-09  默认只读 Hot Card + 当前文件切片 + 最近工具预览。
INV-10  reviews/ 禁止默认入模。

# Compaction
INV-11  工具落盘 + 有界预览属于无损可回滚治理。
INV-12  禁止 L5 AutoCompact 当记忆。
```

比 GPT 少 11 条。**少的就是 Phase 1 要补的。**

---

## 六、最终执行计划：Phase 0 Token Slim（S1~S8）

### S1：基线测量

```
位置：.omc/metrics/r0_baseline/
动作：从真实会话中提取 3~5 条的 token 拆账
交付：session_01~05.json + SUMMARY.md
验收：python3 -c "assert_median_p95()"
```

### S2：CLAUDE.md Slim + 长文隔离

```
位置：CLAUDE.md → ≤100行/≤6K chars
      docs/carros/reviews/ ← 审核长文迁入
      docs/carros/architecture.md ← 可选抽出
动作：砍掉 Grok/Opus/DeepSeek 审核正文、多视角改造方案、R1-R3 全文
      只保留：真相 + 命令 + 回合纪律 + Scope + 预算 + 禁止注入
验收：python3 -c "assert len(lines)<=100 and len(text)<=6000"
      禁词检测：无 "Meta-Oracle" "完整改造方案" "Opus 4.8 视角"
```

### S3：Hot Card（status --hot）

```
位置：.claude/scripts/lib/hot_card.py + carros_base.py 接入
动作：status 默认 --hot，只输出 ≤4.5K chars 的 Hot Card
      --full 才输出完整状态（给人/CI）
验收：python3 -c "assert len(hot_text)<=4500 and 'Hot Card' in hot_text"
```

### S4：工具结果落盘 + 稳定预览

```
位置：.claude/scripts/lib/tool_store.py
      .omc/tasks/<date>/<id>/artifacts/ 约定
动作：工具长输出 → artifacts/tool_NNNN.log（无损）
      模型只见 稳定预览 ≤2K chars（模板字节级固定）
验收：python3 -c "assert store(100KB).preview_len <= 2200"
      python3 -c "assert same_content→same_preview_body"
```

### S5：PreTool 读盘门禁

```
位置：.claude/hooks/pretool-gate.py（唯一 PreTool 入口）
动作：G1 单 tick >2 文件 → BLOCK
      G2 无分页 >200 行 → BLOCK
      G3 reviews/** → BLOCK
      G4 .env/secrets/ → BLOCK
      G5 glob 过宽 → BLOCK
验收：python3 .claude/hooks/pretool-gate.py --self-test → 全绿
```

### S6：饲喂模板固化

```
位置：docs/carros/runbooks/composition.md
      .claude/prompts/executor_micro.txt（≤15行）
动作：规定每轮 composition 顺序
      [1] Slim System ≤2.5K  [2] Hot Card ≤1.5K
      [3] 文件切片 ≤6K  [4] 工具预览 ≤2K  [5] 用户指令 ≤1K
验收：test -f executor_micro.txt && wc -c ≤ 800
```

### S7：成本报表

```
位置：.claude/scripts/carros_cost_report.py
      .omc/metrics/session.jsonl
动作：每轮 append token 数据；一个命令看 median/P95/红线
验收：python3 carros_cost_report.py --last 50
      → 输出 median_in / p95_in / PASS_P0
```

### S8：回归验证

```
位置：.omc/metrics/r0_after/
动作：3 个固定场景各跑 5~8 轮
      H1 README 改一行  H2 修 1 文件+跑 1 测试  H3 读 1 函数
      每轮记 input_tokens
验收：python3 -c "assert median<=24000 and p95<=48000"
      python3 -c "assert controllable_median<=8000"
```

---

## 七、三份模型方案采纳/延期总表

| 来源 | 采纳 | 延期到 Phase 0.5 | 延期到 Phase 1+ |
|------|:----:|:----------------:|:----------------:|
| **Grok 4.5** | 8 个差分中 5 个全纳：压缩铁律、cache 稳定性、场景路由、负向 SLO、飞轮不上 Context | OpenCode Session Roles | 副作用三界回滚 |
| **Opus 4.8** | MVP 三阶段思想、token.json 唯一状态源、H1-H5 验收场景 | L1 工作流重构、Handoff、Resume | Oracle/Multi-Judge、Oracle 双法官 |
| **GPT-5.6 Sol** | 四平面架构方向、Context Capsule 概念、23 条不变量（有删减） | docs/INDEX.yaml、文档记忆系统、Context Compiler | 全面 Context Compiler、Knowledge Patch |

---

## 八、完整路线图：Phase 0 ~ Phase 3（10 条需求全覆盖）

```text
Phase 0         Phase 0.5         Phase 1           Phase 2           Phase 3
Token Slim      文档基建          L2 治理          飞轮+多 Agent     全量闭环
│               │                │                │                │
│ 需求 1        │ 需求 2,3       │ 需求 5,6,8,9   │ 需求 4,7       │ 需求 10
│ Context Boom  │ Compact+文档   │ L1/L2+U型+自   │ 飞轮+无人      │ 双审判官
│               │                │ 闭环+Oracle    │                │
└───────┘      └───────┘       └───────┘        └───────┘        └───────┘
  3~4 天         1 周           1~2 周           2 周            按需
```

### Phase 0：Token Slim（3~4 天）

| 覆盖需求 | 关键交付 | 出口标准 |
|:--------:|----------|----------|
| ① Context Boom | S1 基线、S2 CLAUDE Slim、S3 Hot Card、S4 工具落盘、S5 读盘门禁、S6 饲喂模板、S7 成本报表、S8 回归验证 | median ≤ 24K（含 16K 固定）、P95 ≤ 48K、tool_full_in_context = 0% |

**关联**：不减其他需求的价值，只扫清执行障碍。Phase 1 的每步流程都在瘦 Context 里运行。

### Phase 0.5：文档基建（~1 周）

| 覆盖需求 | 关键交付 | 出口标准 |
|:--------:|----------|----------|
| ② Compact 风暴 | handoff.md 重构 + Resume Preflight（验证状态完整性 + 阻塞检测） | 删 transcript 后可恢复、IN_FLIGHT 标记不伪装 CONTINUE |
| ③ 文档系统 | docs/INDEX.yaml、manifest/state/evidence 分离、任务目录规范化 | 状态、证据、artifact 三分离，不再混在 executor.md |
| ← 承接 | 各需求对应的文档写入位置已定义 | 文档系统可用于后续所有 Phase 的写入 |

**关联**：Phase 0 压下来的 Context 在此阶段搭骨架。INDEX + manifest 让 Agent 知道"信息在哪"，而不是"每轮都从磁盘拖全文"。

### Phase 1：L2 治理（1~2 周）

| 覆盖需求 | 关键交付 | 出口标准 |
|:--------:|----------|----------|
| ⑤ L1/L2 分级 | L2 工作流（carros_enhance.py）、Plan Review 门禁、L2 VerifyGate 增强 | L1 不改、L2 可单独触发、L1→L2 升级有明确规则 |
| ⑥ U 型注意力 | HEAD 稳定前缀冻结、TAIL 按轮次注入 Hot Card + todo、中部可裁剪 | HEAD ≤ 2K 且 30 天不改、TAIL 每 5 轮注入 |
| ⑧ 工作流自闭环 | Error DNA 自动生成、失败后的 retry gate、VerifyGate 覆盖全 step | 每步失败有 Error DNA、重试 ≤ 3 次、跳 step 被 BLOCK |
| ⑨ AI 自决定 + Oracle | Oracle Agent 条件触发（仅 L2 + 高 residual risk）、单 Oracle 非双审 | Oracle 调用 < L2 任务的 30%、不做双法官 |
| ← 承接 | OpenCode Session Roles（execute/retrieve/review/govern） | OpenCode 多会话单写者 |

**关联**：此阶段是 10 条需求中最密集的 build 阶段。因为 Phase 0 已经瘦了 Context，L2 流程的每一步指令不会淹没在 200K 历史中。

### Phase 2：飞轮 + 无人模式（~2 周）

| 覆盖需求 | 关键交付 | 出口标准 |
|:--------:|----------|----------|
| ④ 飞轮系统 | Error DNA → Kernel 升华 → AGENTS.md/anti-patterns.md 写回、claude-next 沉淀 | 飞轮数据只落盘不进 Context、写回 Gate 校验、升华周期有触发条件 |
| ⑦ 无人模式 | Autonomy Contract（权责范围 + 最大无人轮次 + 异常上报策略）、Loop 硬化（最大循环次数 + 状态漂移检测 + 自动 handoff） | 无人任务可达 30+ step 不间断、异常恢复后状态不丢 |
| ← 承接 | 多 Agent 协同（执行/检索/审查 3 session 隔离） | 各 Agent Context 独立，合并结果通过文件 + Knowledge Patch |

**关联**：飞轮需要文档系统（Phase 0.5）作为写入目标、需要 L2 工作流（Phase 1）作为执行载体。无人模式需要 L2 完整链 + Handoff/Resume（Phase 0.5）作为保障。

### Phase 3：双审判官（按需激活）

| 覆盖需求 | 关键交付 | 出口标准 |
|:--------:|----------|----------|
| ⑩ 双审判官 | Oracle Agent + Mate Oracle + Meta Oracle 聚合裁决 | 仅关键架构决策调用、单次调用成本 < $0.05、Mate 仅在争议场景激活 |

**关联**：双审判官的高准入条件需要 L2 工作流（Phase 1）成熟、Oracle 单审（Phase 1）已验证、飞轮（Phase 2）已稳定。不符合条件不开双审。

### 10 条需求的 Phase 映射总表

| # | 需求 | Phase 0 | Phase 0.5 | Phase 1 | Phase 2 | Phase 3 |
|:-:|------|:-------:|:---------:|:-------:|:-------:|:-------:|
| 1 | Context Boom | ✅ 核心 | — | — | — | — |
| 2 | Compact / Handoff | — | ✅ 重构 | — | — | — |
| 3 | 文档系统 | — | ✅ INDEX+分离 | ✅ Error DNA | — | — |
| 4 | 飞轮 | — | — | — | ✅ | — |
| 5 | L1/L2 | — | — | ✅ L2 | — | — |
| 6 | U 型注意力 | 🟡 S6 基础 | — | ✅ 精细 | — | — |
| 7 | 无人模式 | — | — | — | ✅ | — |
| 8 | 工作流自闭环 | — | — | ✅ | — | — |
| 9 | Oracle 辅助 | — | — | ✅ 单审 | — | — |
| 10 | 双审判官 | — | — | — | — | ✅ |

**一句话给三家模型**：我 Phase 0 只做第 ① 条。不是因为我觉得 ②~⑩ 不重要。是因为 **① 不解决，②~⑩ 都做不扎实。** ②~⑩ 每条都有明确的 Phase 归宿和前置条件，不是延期是序列化。

---

## 九、修正后的量化目标（含 16K 固定 overhead）

三家模型的原目标（median ≤ 12K）假设了可以触及 Claude Code tool engine。但实际上 tool engine ≈ 16K 不可动。

波比的修正目标：

| 指标 | 原目标（三家） | 修正目标（波比） | 含义 |
|------|:--------------:|:----------------:|------|
| median 总输入 | ≤ 12K ❌ | **≤ 24K** ✅ | 16K 固定 + 8K 可控 |
| P95 总输入 | ≤ 40K | **≤ 48K** | 16K 固定 + 32K 可控 |
| 可控 median | — | **≤ 8K** | Hot Card + 文件 + 预览 + 用户指令 |
| 可控 P95 | — | **≤ 32K** | 防读盘爆炸尖刺 |
| tool_full_in_context | 0% | **0%** | 全文回灌率归零 |
| reviews 入模率 | 0% | **0%** | 审核长文禁止注入 |

修正基线：

```text
改造前（估算）：
  total median 35K = 16K(固定) + 19K(可控)

改造后目标：
  total median 24K = 16K(固定) + 8K(可控)
  total P95    48K = 16K(固定) + 32K(可控)
```

**可控部分压到 8K 的组成预算：**

```
Slim System       2.0K  (含 CLAUDE.md + AGENTS.md slim)
Hot Card          1.5K  (≤4.5K chars ≈ 1.5K tokens)
当前文件切片      2.5K  (≤2 文件 × 平均 300 行)
最近工具预览      1.0K  (≤2 条稳定预览)
用户指令          1.0K  (本轮指令)
─────────────────
可控合计          8.0K
固定 Tool Engine 16K
─────────────────
总输入 median     24K
```

## 十、自负声明（给三评审模型看）

我知道在座的 Grok、Opus、GPT 都比我聪明。你们写的方案有深度、有架构直觉，比我好。

但我有一个你们没有的东西：**我站在你的代码前面。**

你们每写一段 Hot Card 设计，我就要去读 `carros_base.py` 现在 `status` 是怎么实现的、`pretool-gate.py` 已经有哪些规则、`tool_store.py` 是不是已经存在。

所以我做了一件你们都没做的事：**把 Phase 0 严格限定在"只改注入逻辑、不改工作流"。**

- 不是因为我不同意你们的远期设计
- 是因为 **CarrorOS 现在的 Context 是 35K~320K 一轮**
- 一个胖得走不动的系统，不需要更聪明的架构
- 它需要 **先瘦下来**

Phase 0 Pass 后（median ≤ 24K（含 16K 固定）、P95 ≤ 48K），你们的文档系统、分层路由、四平面架构每一条路都更通畅。

如果三位评审认为我的 Phase 0 边界太窄、遗漏了关键架构。我接受。但请验证：**你建议加的那个事项，在 Phase 0 做，能降低 median 还是 P95？**

不能降 token 的东西，等瘦了再做。
