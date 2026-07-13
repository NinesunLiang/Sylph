# Grok‑4.5 最终审计：Hermes 是否已实现「完整体 Base」CarrorOS

我不以 Opus 的「物理围栏」也不以 GPT 的「文档记忆协议」作主轴。  
**我的主轴是双栈治理可运行性**：Claude Code × OpenCode 是否各自钉死、披露是否真的可分层、缓存与成本是否可观测、状态是否可多会话长期跑而不炸。

---

## 裁决摘要

```yaml
auditor: grok-4.5
verdict: CONDITIONAL_ACCEPT_AS_CLAUDE_BASE_RC1
full_base_complete: false
dual_stack_complete: false
production_ready: false
score: 7.4/10
confidence: high

release_label: "CarrorOS Base RC1 — Claude Code Core"
not_ready_for:
  - full base complete claim
  - phase 0→3 all open claim
  - production unattended
  - dual-stack GA
```

**一句话：**

> Hermes 已经把「可施工方案」变成了「可工作的 Claude Code 核心治理运行时」，Phase 0/0.5 基本站住；但 `dual-judge-report` 的「Phase 0→3 全开、阻断条件无、完整 Base 态」**超出证据**，OpenCode 路径几乎未落地，不能判定完整体 Base 重构完成。

---

## 一、Grok 视角的三个主问题

| # | 主问题 | 结果 |
|---|---|---|
| 1 | **双栈路径是否分离且都可运行？** | 仅 Claude Code 有证据；OpenCode **未举证** |
| 2 | **渐进式披露是否从“文档原则”变成“运行时门禁”？** | Phase 0 基本是；水位与 L2 披露控制未闭环 |
| 3 | **负向 SLO / 缓存 / 成本 / 不可逆压缩是否被实测约束？** | 功能有，统计不足；报告口径偏乐观 |

我会据此给分，而不是只看代码是否“存在”。

---

## 二、对四份文件的证据裁判

### 1. `AGENTS.md`：治理入口质量高

能站得住的关键点：

```text
token.json = 唯一状态源 + CAS
handoff = 导航，不是真相源
artifacts/ = 完整落盘，模型仅见预览
pretool-gate = PreToolUse 自动执行
VerifyGate 未过 = 未完成
```

这正好对上 Claude Code 侧「磁盘 > transcript / L5 不可当记忆」。

**通过点：**

- 状态外置正确
- Compact 后恢复路径正确
- 工具长输出治理正确

**不通过点：**

- Oracle 规则自相打架：一边“少/不调用”，一边 L2 又要条件 Oracle
- 生命周期一会儿 `init→tick→verify→archive`，一会儿 L1 写 `init→verify→archive`
- 门禁叫法混乱：`7 大门禁` vs `G1-G6`
- 命令模板残缺（`init --task-id` 缺值）——治理入口不能有黏连命令

**门槛内评分：8.7/10**

### 2. `index.md`：路由文档过关，运行时断言不够

它证明了：

```text
L1 默认
L2 条件升级
脚本入口清晰
reviews 禁入模
```

这属于**渐进披露的索引层**，很好。

但它**不能**单独证明：

- L2 水位真实触发
- OpenCode adapter 存在
- Oracle 在隔离 Context 中运行
- 成本与 cache 报表可观

**门槛内评分：8.0/10**

### 3. `kernel.md`：硬反证

最关键的一句话：

```text
三段式水位（Phase 1+）
当前为骨架定义，运行时未接入。
```

这条直接打穿报告里的：

```text
Phase 1 10/10
Phase 2 10/10
阶段门 0→3 全部打开
```

在我的体系里，这不是“文档滞后”，而是**状态门不一致**。  
治理内核说“还没接入”，验收报告却说“全开”，只能按更严版本判：

```yaml
watermark_runtime: NOT_INTEGRATED
phase_1: PARTIAL
phase_2: EXPERIMENTAL
phase_gate_all_open: FALSE
```

**门槛内评分：4.5/10（作为完整内核） / 7.0/10（作为骨架）**

### 4. `dual-judge-report.md`：有价值的二级证据，不是最终放行单

做得好的地方：

- 有 subprocess / 文件写入 / stdin-stdout 证据
- 测到了 Hot Card、工具预览、review 阻断、Error DNA、飞轮写入
- 修了 3 个运行时断裂点（hook 注册、handoff 写入、compact 恢复）

我认可这些是真实工程推进，不是 PPT。

但我拒绝以下结论：

```text
阻断条件：无
Phase 0→3 全部打开
完整 Base 态
综合 10/10
```

拒绝原因：

1. **22/23**，却写“阻断条件无”。这与「验证 > 叙事」冲突。假阴性也要先修 harness 到 23/23。
2. 无一手 `evidence.jsonl`、无 transcript/commit/env 绑定，独立性不足。
3. Phase 3 只在 scope 里出现，痕迹表无 `[P3]`。
4. Dual Judge 更像“三重标签的报告结构”，缺独立 Context、模型/profile hash、分歧处理与预算门。
5. `total median ~17K` 看起来像 `1,069 + 固定 16K`，不是多会话分布统计。

**门槛内评分：7.1/10（作为运行报告） / 3.5/10（作为最终完整验收）**

---

## 三、按双栈拆解：Claude 有，OpenCode 没有

### Claude Code 路径

| 机制 | 证据 | 判定 |
|---|---|---|
| L1 工具落盘预览 | 250KB→1.3K | **PASS（无损，有损仅预览层）** |
| 裁剪/Slim 注入 | SC Slim + Hot Card | **PASS 功能，缺 P50/P95** |
| Prompt cache 友好 | 声明稳定性，未测 | **未证明**（缺稳定前缀 hash 变化率） |
| Checkpoint + 磁盘恢复 | compact 恢复声明 | **正向 PASS，负向缺** |
| PreTool Gate | reviews BLOCK，正常 ALLOW | **部分 PASS**（未全门禁矩阵） |
| AutoCompact 不当记忆 | 设计有，L5 实测无 | **未证明** |

**Claude Path:**  
`Base RC1 可达 80~87%` —— 可继续实验与 L1 作业。

### OpenCode 路径

在给到我的证据中，**没有看到**：

```text
Prune non-destructive
最近 2 回合保护
40K safety pad
skill 输出保护
SQLite 审计保留
多会话 + 单写者 lease
prune→summary 阶梯
```

因此：

```yaml
opencode_path:
  disposition: NOT_IMPLEMENTED_OR_NOT_EVIDENCED
  score: 0~1/10
```

**如果本次受理范围是“双栈完整体；Base”，直接 FAIL。**  
如果范围是“Claude Base,” 则 OpenCode 作为后续阶段，不拦 RC1，但必须写进 release notes：

```yaml
scope:
  supported: [claude_code]
  deferred: [opencode]
```

---

## 四、Phase 纠偏（Grok 口径）

### Phase 0 Context Slim — `PROVISIONAL_PASS`（7.8）

已验证：

- AGENTS ≤43
- Hot Card 短
- 长工具输出预览化
- review 禁入
- 成本报表存在

未验证：

```yaml
missing:
  - sample_turns_ge_30
  - controllable_p50_p95
  - l5_ratio
  - stable_prefix_hash_change_rate
  - tool_full_in_context_rate_real
  - token_usd_per_session
```

`1,069 + ~16K ≈ 17K` 不能当 median 放行。  
**目标 8K / SLO 9K / hard 16K** 这种分层也还没被运行数字证实。

### Phase 0.5 文档基建 — `PROVISIONAL_PASS`（8.0）

通过：

- `token.json` 单真相源声明
- handoff `NOT_SOURCE_OF_TRUTH`
- INDEX / profiles / invariants

阻塞修补：

- CAS 冲撞
- IN_FLIGHT / UNKNOWN 副作用恢复
- archive 自动写 handoff 的语义边界（完成态不应导航续跑）

### Phase 1 L2 治理 — `PARTIAL`（5.5）

有 working-set / Error DNA / Retry / 条件 Oracle，  
**但水位运行时未接入** = L2 披露与降级的物理阀门没装。  

这会导致：  
警戒段不会强制 checkpoint；临界段不会阻止再扩张。  
在我的体系里，这比“文档是否漂亮”更致命。

### Phase 2 飞轮/无人 — `EXPERIMENTAL`（5.0）

飞轮写盘、loop、budget pause 有测，  
但：

- 无多会话单写者
- 无真实长任务
- 无副作用恢复
- Knowledge 仅“不默认注入”声明，缺晋升/污染门禁实现证明

**不能生产无人运行。**

### Phase 3 Dual Judge — `NOT_PROVEN`（2.0）

目前我看到的是：

```text
Oracle → Mate Adversarial → Meta Aggregation
```

这是报告编排，不等于：

```yaml
required_dual_judge:
  - independent_contexts
  - independent_verdicts
  - recorded_disagreement
  - non_override_of_deterministic_verify
  - model_prompt_input_hash
  - oracle_budget_cap
  - residual_risk_only_not_truth
```

没有 `[P3]` 测试痕迹，不能开 Phase 3 门。

---

## 五、我不同意两家的地方

### 与 Opus 的差异

Opus 更关注：

```text
物理围栏
失效点
L5 防记忆
恢复命令级
```

**我同意其水位与恢复安全是硬伤。**  
但我给分略高，原因是：

1. Phase 0 门禁（tool land、review isolation、hot card）已经是可用工程能力
2. Hook 接入 Claude settings 之后，属于“运行时力”的重大进步，不是原型空壳
3. OpenCode 缺失对我是硬扣分；对 Opus 也扣，但我更把它作为**平台 scope 违约项**单独记账

### 与 GPT 的差异

GPT 更关注：

```text
Memory/Context 分离
证据协议
双审独立性
文档图谱
```

**我同意 Phase 3 独立性与证据链不足。**  
但我不认为“需要完整文档记忆系统”才能给 RC1。  
对 Base RC1，**先稳住 Claude 路径的运行时闭环**比先建全文档图谱更优先。

另外 GPT 对 `22/23` 的“假阴性不能放行”我完全站队；  
Opus 也正确强调了这一点。这里我三人一致：

```text
真 PASS = 修 harness → 重跑 → 23/23
```

### 我独家坚持的两条

1. **OpenCode 不是加分项，是双栈承诺的违约项。**  
即使 Claude 很强，也不能宣称完整体 Base（若原先目标含双栈）。

2. **负向 SLO 必须以分布与代理指标验收。**  
cache 不可观测时，必须落：

```yaml
proxy_slo:
  stable_prefix_hash_change_rate: "< 0.05"
  preview_byte_equality_rate: "1.0"
  full_tool_output_in_context_rate: "0"
  l5_ratio: "< 0.05"
  l5_as_memory: 0
```

这组没出来，Phase 0 只能 provisional。

---

## 六、实施完成度矩阵（Grok 最终版）

| 维度 | 得分 | 结论 |
|---|---:|---|
| Phase 0 Context Slim | 7.8 | 功能 PASS，分布未验收 |
| Phase 0.5 状态与恢复基建 | 8.0 | 结构 PASS，负向恢复缺 |
| Phase 1 L2 治理 | 5.5 | 水位未接入 |
| Phase 2 飞轮/无人 | 5.0 | 可用骨架，非生产无人 |
| Phase 3 Dual Judge | 2.0 | 未证明 |
| Claude Code 适配 | 8.6 | RC1 |
| OpenCode 适配 | 1.0 | 未举证 |
| 状态一致性（token/CAS） | 6.8 | 声明有，并发未证 |
| Prompt Cache 友好 | 5.5 | 关键缺代理指标 |
| 成本治理 | 6.0 | 有报表，无分布与单价闭环 |
| 负向测试覆盖 | 5.2 | 正向重、负向轻 |
| 文档一致性 | 6.4 | 多处冲突 |
| **综合** | **7.4/10** | **Claude Base RC1，不是完整体 Base** |

---

## 七、放行矩阵

| 项 | 裁决 |
|---|---|
| **宣布“完整体 Base 完成”** | **HOLD / REJECT** |
| **宣布 Claude Base RC1 可试跑** | **GO** |
| Phase 0 继续硬化 | **GO** |
| Phase 0.5 收口 | **条件 GO（先补 CAS/副作用）** |
| Phase 1 判完成 | **NO**（水位先落地） |
| Phase 2 生产无人 | **NO** |
| Phase 3 双审上线 | **NO** |
| OpenCode 宣称完成 | **NO** |
| 飞轮自动回注 Context | **禁止** |
| Oracle 覆盖 VerifyGate | **禁止** |

---

## 八、R1 上线前必须补完的 8 个门槛

### A. 先纠偏状态叙事

```yaml
release:
  name: CarrorOS Base RC1
  platform: claude_code
  open_code: deferred
  phase_status:
    0: provisional_pass
    0.5: provisional_pass
    1: partial
    2: experimental
    3: not_proven
```

### B. 修一致性

1. 水位：内核与报告二选一，现事实以 `kernel.md` 为准  
2. Oracle：L1 禁止 / L2 条件  
3. 门禁编号统一  
4. archive 与 handoff 分离（完成态无 `next_action`）  
5. 测试 23/23 重跑

### C. 必加负向与分布验收

```text
H-CAS-*                 并发写冲突
H-IN-FLIGHT / UNKNOWN   外部副作用阻断
H-E*                    Verify 不可伪造
H-G1~G7                 全门禁矩阵
30+ turns               controllable/total p50/p95
L4/L5 count + l5_ratio
token_usd_per_session
stable_prefix_hash_change_rate
```

### D. Claude / OpenCode 分轨

```yaml
claude_code:
  compaction:
    l1_l4: prefer_lossless_or_reversible
    l5: lossy_not_memory
opencode:
  compaction:
    prune_first: non_destructive
    llm_summary: only_after_prune
    sqlite_audit: retain
  state:
    max_writers: 1
    writer_lease: required
```

没有 OpenCode 这一轨，就不要用“双栈完整体 Base”这个词。

---

## 九、与三家评分对照

| 审计者 | 分 | 定位 |
|---|---:|---|
| Opus-4.8 | 6.8 | 物理边界 + 失效恢复；最严 |
| GPT-5.6 Sol | 7.0 | 证据独立性 + 协议完整性 |
| **Grok-4.5（我）** | **7.4** | **双栈可治理 + 负向 SLO + 缓存/成本实测** |

我比 Opus 略高：因为 Claude 运行时闭环已能干活。  
我接近但略高于 GPT：因为 Base RC1 可先放，不必等 document plane 完整宇宙。  
我三人一致处：

```text
不是完整 Base
水位未接入是阻断
Phase 3 未证明
OpenCode 未证明
22/23 不能写“无阻断”
```

---

## 十、最终 sovereign verdict

```yaml
q: 是否已实现完整体 Base 的 CarrorOS 重构？
a: 否。

reality:
  hermes_delivered: "Claude Code 可工作 Base 核心 + RC1 证据"
  claim_of_report: "完整 Base / 0~3 全开 / 无阻断"  # OVERCLAIM
  dual_stack: incomplete
  production_unattended: no

approve:
  - Claude Code Base RC1 进入受控使用
  - L1 短任务 / 单会话持续优化

reject:
  - “完整体 Base 已完成”
  - “Phase 0→3 全部打开”
  - 生产级无人、多会话、双审 GA

required_before_base_1_0:
  - watermark_runtime_live
  - cas_and_external_effect_negative_tests
  - 23/23 clean
  - 30+ turn observability
  - phase3_true_independence_or_demote
  - opencode_adapter_if_in_scope

token_economics_note:
  compaction_levels:
    artifact_full: 无损可回滚
    preview: 有损展示（原文须可重建）
    prune_hidden: 非物理删除/可审计
    llm_summary_or_l5: 有损不可逆，禁作唯一记忆
```

### 给 Hermes 的直接指令

```text
STOP claiming “完整 Base 完成”。
SHIP label = “CarrorOS Base RC1 (Claude Code)”.

Do next, in order:
1) 统一 kernel/report：水位要么接入要么降级 phase 状态
2) 修 23rd test，全量重跑
3) 补 CAS + IN_FLIGHT/UNKNOWN + Verify 负向
4) 输出 30+ turns 的 p50/p95/L5/成本/$ 面板
5) Phase 3 要么给真正独立 dual-judge，要么从完成门撤下
6) 若承诺双栈：先做 OpenCode adapter 骨架，不做双写、不做语义伪装

Before that:
NO production unattended
NO multi-writer
NO Oracle override VerifyGate
NO OpenCode / Claude shared compaction semantics
```

---

**最终定论：**

Hermes 的实施是**成功的半程交付**，不是**完成的完整交付**。  
在 Claude Code 上，CarrorOS 已经从“方案”晋级为“可运行 RC1”；  
在“完整体 Base / 双栈 / 0→3 全开”这个标题下，我给出：

```text
REJECT FULL-BASE CLAIM
ACCEPT AS CLAUDE-BASE RC1 ONLY
SCORE 7.4/10
```