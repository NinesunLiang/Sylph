# CarrorOS 最终整合重构方案
## 第 1/8 部分：总纲、冲突裁决与目标架构

可以。我会把现有三类材料整合成**一套最终可实施版本**，不再按“Grok 版 / Opus 版 / GPT 版”并列堆放：

1. **最新全面重构内容**：CarrorOS 的 Intake → Plan → Execute → Verify → Archive 治理主链；
2. **Context Engine 专项优化**：文档记忆、渐进式披露、Context Compiler、压缩与恢复；
3. **多模型建议与既有实现**：DeepSeek、Opus、GPT 建议，以及当前 README、AGENTS、全览图和脚本约束。

最终输出控制在 **8 次**，每次都是可独立保存的一章；第 8 次给出总文件树、实施顺序、迁移清单和最终验收矩阵。后续实施应以这 8 部分组成的最终规范为准，不再直接照搬任何一份旧建议文档。

---

# 一、八次输出计划

| 次序 | 完整章节 | 主要交付 |
|---:|---|---|
| **1/8** | 总纲、冲突裁决、目标架构 | 本次：冻结术语、边界和最终架构 |
| **2/8** | L1 Base / L2 Enhance 工作流 | IntakeGate、PlanBuilder、PreActionGate、Executor、VerifyGate、Archive |
| **3/8** | 文档记忆系统 | `docs/INDEX.yaml`、ADR、Contracts、Manifest、权威级别、写回协议 |
| **4/8** | Context Engine | Progressive Disclosure、Working Set、Context Compiler、Capsule、Receipt |
| **5/8** | Compact / Resume 双栈治理 | Claude Code 与 OpenCode 分开设计，handoff、checkpoint、恢复算法 |
| **6/8** | 代码与配置实现 | Python 模块接口、JSON/YAML Schema、CLI、Hook、Claude/OpenCode 配置 |
| **7/8** | 模型路由、多 Agent、成本与审计 | DeepSeek V4 Flash / Opus 路径、隔离协同、指标和成本报表 |
| **8/8** | 实施手册与最终验收 | 文件树、分阶段迁移、测试夹具、DoD、回滚、上线顺序 |

每部分遵循以下标准：

```text
- 给出冻结裁决，而不是继续列多个候选方案
- 区分 L1 Base 与 L2 Enhance
- 区分 Claude Code 与 OpenCode
- 标注无损可回滚 / 有损不可逆
- 给出可粘贴配置或 Schema
- 给出可观测指标和验收条件
- 保持与前后章节接口一致
```

---

# 二、最终问题定义

CarrorOS 当前每次问答达到 **35K～320K token**，并非单一的 compaction 参数问题，而是四项架构责任没有分离：

```text
文档系统没有负责长期记忆；
Transcript 被错误地当作状态数据库；
Prompt 被错误地当作文档容器；
Compaction 被错误地当作正常记忆机制。
```

最终根因定义如下：

> **CarrorOS 没有分离 Memory Plane、Retrieval Plane、Context Plane 与 Governance Plane，导致项目知识、任务状态、工具证据和历史对话持续累加到 Prompt。**

因此，本轮重构不能只做以下表面动作：

```text
× 只把 CLAUDE.md 缩短；
× 只增加 Hot Card；
× 只在达到水位时做 LLM 摘要；
× 只换更大上下文模型；
× 只增加一个智能 Context Router；
× 只把长文移到 docs/，但每轮仍读取全文。
```

正确目标是：

> **文档系统负责记住，索引负责找到，Context Compiler 负责本轮携带什么，Prompt 只负责现在做什么。**

---

# 三、冻结术语与冲突裁决

现有材料中存在命名、职责和文件边界冲突。以下裁决在最终版中冻结。

## 3.1 只保留 L1 / L2 二元治理

```text
L1 = Base
L2 = Enhance
```

禁止继续使用：

```text
L1_L1
L2_L2
L2/
Base+、L1.5 等未定义层级
```

### L1 Base

定位：中型任务、轻治理、低成本、稳定完成。

工作流：

```text
A. Intake / Plan
B. Execute
C. Verify / Archive
```

默认任务目录：

```text
.omc/tasks/<date>/<task-id>/
```

### L2 Enhance

定位：复杂任务、研究驱动、多 Agent、长期增强。

工作流：

```text
A. Research
B. Plan
C. Execute
D. Verify
E. Archive / Memory Writeback
```

默认特性：

```text
- 更完整的 Philosophy / Iron Rules / ROI / Current State
- 独立 Research 产物
- 多 Agent 或多会话
- Oracle/审查能力
- 更严格的文档写回和证据治理
```

注意：**L2 是治理深度，不等于把更多内容灌入主 Context。**

---

## 3.2 主治理链冻结

最终主链：

```text
IntakeGate
    ↓
PlanBuilder
    ↓
PreActionGate
    ↓
Executor Ledger
    ↓
VerifyGate
    ↓
Archive + Memory Writeback
```

Context Engine 是贯穿层，不是完成门：

```text
                   ┌──────────────────────────┐
                   │ Context Engine           │
                   │ compile / budget / resume│
                   └──────────────────────────┘
                         ↑ 覆盖全生命周期
Intake → Plan → PreAction → Execute → Verify → Archive
```

冻结裁决：

- `VerifyGate` 是唯一完成裁决者；
- Context compact 成功不代表任务完成；
- Agent 声称“已完成”不代表完成；
- Archive 只能接受 VERIFIED 任务；
- ASK_USER / BLOCKED 必须写入结构化状态，不能只留在聊天里。

---

## 3.3 状态载体从“四件套”升级为“分责七件套”

旧版常见四件套：

```text
token.json
plan.md
executor.md
session-handoff.md
```

它可以维持基本连续性，但 `executor.md` 容易同时承担状态、日志、证据和历史，最终持续膨胀。

最终版采用七类载体：

```text
manifest.yaml       # 任务入口、目标、等级、索引
state.json          # 唯一运行状态机
plan.md             # 完整计划；默认只披露当前 step
working-set.yaml    # 当前 Context 的白名单与预算
handoff.md          # 跨会话恢复入口
evidence.jsonl      # 证据索引，不存完整日志
artifacts/          # 完整工具结果、patch、测试报告
```

兼容裁决：

```text
旧 token.json 可在迁移期映射为 state.json；
旧 executor.md 可保留为人读 Ledger，但不得继续作为唯一证据库；
完整工具输出必须迁到 artifacts/；
恢复入口是 state + handoff，不是 executor 全文。
```

---

## 3.4 Hot Card 与 Context Capsule 的关系

现有建议中，Hot Card 与 Context Capsule 看起来像两套竞争方案。最终裁决：二者保留，但职责不同。

### Hot Card

```text
用途：CLI/status 的极简状态视图
目标：人和 Agent 快速看当前任务水位
上限：4500 chars，推荐 1500～3000 chars
性质：state/plan/evidence 的确定性投影
```

### Context Capsule

```text
用途：本轮实际提交给模型的完整最小工作集
组成：Stable Core + Hot State + Relevant Memory + File Slices
      + Evidence Preview + User Delta
目标：每轮可从文档和状态重新编译
性质：可丢弃缓存，不是真相源
```

关系：

```text
Hot Card ⊂ Context Capsule
```

因此：

- `status --hot` 输出 Hot Card；
- `context compile` 输出 Context Capsule；
- 不能把 Hot Card 扩成另一个完整计划；
- 不能把 Capsule 持续追加成新 transcript 数据库。

---

## 3.5 Context Router 与 Context Compiler 的裁决

最终 Base 不采用由 LLM 自主决定的智能 Router。

使用：

```text
确定性 Context Compiler
+
模型发起的结构化 Context Request
+
PreAction/Disclosure Gate 裁决升级
```

理由：

- Base 要求稳定、可回放、低阶模型可执行；
- LLM 自主路由会增加成本和不可预测性；
- 编译规则必须能够单元测试；
- 每个披露来源必须能生成 Receipt。

L2 可以在独立检索 Agent 中使用语义检索或智能路由，但返回主执行轨的只能是结构化 `Knowledge Patch`，不能返回完整探索 transcript。

---

# 四、最终四平面架构

```text
┌────────────────────────────────────────────────────────────┐
│ 1. Memory Plane · 持久记忆平面                             │
│ docs / ADR / contracts / manifest / state / evidence       │
│ artifacts / handoff                                        │
│                                                            │
│ 特性：持久、可寻址、可审计、可版本化                       │
│ 默认：不全文进入模型                                       │
└───────────────────────────┬────────────────────────────────┘
                            │ index / section / symbol
┌───────────────────────────▼────────────────────────────────┐
│ 2. Retrieval Plane · 检索与渐进披露平面                    │
│ INDEX → Summary → Section → Neighborhood → Full             │
│ working-set / context-request / disclosure-gate             │
│                                                            │
│ 特性：精确选择、按预算升级、记录 reason                     │
└───────────────────────────┬────────────────────────────────┘
                            │ deterministic compile
┌───────────────────────────▼────────────────────────────────┐
│ 3. Context Plane · 一次性工作上下文                        │
│ Stable Core + Hot Card + Relevant Memory + File Slices      │
│ + Evidence Preview + User Delta                             │
│                                                            │
│ 特性：每轮重建、可丢弃、不承担长期记忆                     │
└───────────────────────────┬────────────────────────────────┘
                            │ actions / receipts / metrics
┌───────────────────────────▼────────────────────────────────┐
│ 4. Governance Plane · 治理控制平面                         │
│ Intake / PreAction / Verify / token budget / cache          │
│ compact / checkpoint / audit / permission / cost report     │
│                                                            │
│ 特性：阻止越权、控制成本、保证恢复、验证完成               │
└────────────────────────────────────────────────────────────┘
```

---

# 五、最终系统不变量

以下不变量应进入最终 `CLAUDE.md`、`AGENTS.md` 和自动测试。

## 5.1 真相不变量

```text
INV-01  聊天不是任务状态源。
INV-02  Transcript 是审计记录，不是正常恢复入口。
INV-03  LLM Summary 是有损导航，不是事实源。
INV-04  state.json 是运行状态的唯一权威来源。
INV-05  关键架构结论必须写入 ADR/Contract，不得只留在回答中。
INV-06  完整工具输出必须进入 artifacts；evidence 只保存索引。
```

## 5.2 执行不变量

```text
INV-07  每个 tick 只执行一个可验证动作。
INV-08  只操作 allowed_paths；denied_paths 优先级最高。
INV-09  ASK_USER / BLOCKED 必须持久化。
INV-10  只有 VerifyGate 可以把 step/task 标记为 VERIFIED。
INV-11  未 VERIFIED 的任务不得进入成功归档。
```

## 5.3 Context 不变量

```text
INV-12  每轮 Context 必须由 Compiler 重建，不能无限追加旧工作集。
INV-13  每个非静态 Context 来源必须出现在 Disclosure Receipt 中。
INV-14  默认只读文档索引/摘要，再按 heading 或 symbol 升级。
INV-15  reviews/** 默认禁止进入执行 Context。
INV-16  完整 plan、完整 executor、完整 transcript 默认禁止入模。
INV-17  Context 丢失后必须能从 state + handoff + documents 重建。
```

## 5.4 Compaction 不变量

```text
INV-18  先减少进入 Context 的内容，再考虑压缩历史。
INV-19  工具落盘 + 有界预览属于无损可回滚治理。
INV-20  Claude L5 AutoCompact 是有损不可逆兜底，不能作为记忆机制。
INV-21  OpenCode 先 Prune(hidden)，后 LLM Summary。
INV-22  任何有损摘要都不能覆盖 state、ADR、evidence 或 artifact。
```

---

# 六、最终目录骨架

```text
CarrorOS/
├── CLAUDE.md                         # 极简运行契约
├── AGENTS.md                         # Agent 边界；不得复制整套百科
├── README.md                         # 面向人的入口
├── docs/
│   ├── INDEX.yaml                    # 全局文档索引
│   ├── project/
│   │   ├── overview.md
│   │   ├── constraints.md
│   │   └── glossary.md
│   ├── architecture/
│   │   ├── INDEX.yaml
│   │   ├── governance-runtime.md
│   │   ├── context-engine.md
│   │   └── verify-gate.md
│   ├── contracts/
│   │   ├── task-state.md
│   │   ├── evidence.md
│   │   ├── context-capsule.md
│   │   └── cli.md
│   ├── adr/
│   │   ├── INDEX.yaml
│   │   ├── ADR-001-document-first-memory.md
│   │   └── ADR-002-compaction-boundary.md
│   ├── runbooks/
│   │   ├── token-governance.md
│   │   ├── resume.md
│   │   └── context-overflow.md
│   └── reviews/                      # 参考材料，默认禁止入模
│       ├── grok/
│       ├── opus/
│       ├── deepseek/
│       └── gpt/
├── .omc/
│   ├── tasks/<date>/<task-id>/
│   │   ├── manifest.yaml
│   │   ├── state.json
│   │   ├── plan.md
│   │   ├── working-set.yaml
│   │   ├── handoff.md
│   │   ├── decisions.md
│   │   ├── evidence.jsonl
│   │   ├── context/
│   │   │   ├── capsule.current.md
│   │   │   └── receipts.jsonl
│   │   └── artifacts/
│   ├── profiles/
│   │   ├── deepseek-v4-flash.yaml
│   │   └── opus-4.8.yaml
│   ├── metrics/
│   │   ├── session.jsonl
│   │   └── context.jsonl
│   └── audit/
│       └── events.jsonl
└── .claude/
    ├── scripts/
    │   ├── carros_base.py            # L1 单入口
    │   ├── carros_enhance.py         # L2；可后置实现
    │   └── lib/
    │       ├── context_engine.py
    │       ├── document_index.py
    │       ├── artifact_store.py
    │       ├── verify_gate.py
    │       └── metrics.py
    ├── hooks/
    │   └── pretool_gate.py            # 唯一 PreTool 强制入口
    └── prompts/
        └── executor_micro.md
```

### Base 体积裁决

知识库指出 Base 不能因模块众多而变重。最终采用：

```text
对用户：只有 carros_base.py 一个 L1 CLI 入口；
对实现：允许 lib/ 内部分模块，避免单文件不可维护；
对 Context：模块数量不等于注入数量，默认只注入 Slim Contract。
```

也就是：**CLI 单入口，内部模块化，Prompt 不暴露实现百科。**

---

# 七、L1 与 L2 的最终职责边界

| 能力 | L1 Base | L2 Enhance |
|---|---|---|
| IntakeGate | 必须 | 必须，规则更严格 |
| PlanBuilder | A/B/C | A/B/C/D/E |
| PreActionGate | 必须 | 必须 |
| Executor Ledger | 短记录 + Artifact 指针 | 同左，附研究/协同引用 |
| VerifyGate | 必须 | 必须，多维验证 |
| Document Index | 使用 | 使用并可扩充 |
| Context Compiler | 确定性、固定规则 | 确定性主链 + 检索 Agent |
| 多 Agent | 默认不用 | 可用，但上下文隔离 |
| Oracle | 禁止默认调用 | 按 ROI 与预算调用 |
| 全局架构审查 | 新任务或新会话 | 独立审查会话 |
| Compaction | cheapest first | 同左，不扩大依赖 |
| Memory Writeback | 状态、证据、必要 ADR | 完整研究、ADR、复用知识 |

关键裁决：

> L2 可以更聪明，但不能更混乱；L2 的增强能力必须通过文件和结构化补丁返回，不能让主会话膨胀。

---

# 八、第一阶段目标与可观测指标

## 8.1 成本目标

| 指标 | 止血阶段 | 最终稳态 |
|---|---:|---:|
| 全模型 `input_tokens/turn` median | ≤12K | ≤10K |
| 全模型 P95 | ≤40K | ≤24K |
| DeepSeek V4 Flash median | ≤10K | ≤8K |
| DeepSeek V4 Flash P95 | ≤20K | ≤16K |
| 高阶推理执行轨 median | ≤20K | ≤16K |
| `tool_full_in_context_rate` | 0 | 0 |
| `full_document_load_rate` | <5% | <2% |
| `resume_without_transcript_success` | ≥90% | ≥95% |

## 8.2 Claude Code 指标

```text
prompt_cache_hit_rate ≥ 70%，目标 ≥ 85%
stable_prefix_hash_changes 接近 0
L5 dependency rate = 0
compaction events/session < 0.2
artifact preview reuse rate 持续监控
```

## 8.3 OpenCode 指标

```text
prune_before_summary_rate = 100%
lossy_summary_as_truth = 0
SQLite audit retention = 100%
recent_2_turns_preserved = 100%
多会话写冲突 = 0
```

## 8.4 文档记忆指标

```text
claims_with_source_reference_rate ≥ 90%
handoff_completeness_rate = 100%
context_rebuild_success_rate ≥ 99%
stale_document_reference_rate < 2%
关键决策当轮写回率 = 100%
```

---

# 九、实施优先级冻结

最终不能直接从“全面重构”所有模块同时开工。实施顺序冻结为：

```text
P0：先止住 Context 泄漏
    Slim CLAUDE/AGENTS
    reviews 隔离
    Artifact 落盘
    状态/证据分离
    token baseline

P1：建立文档记忆
    docs/INDEX
    文档 authority/status
    manifest/state/handoff
    冷启动恢复

P2：建立确定性 Context Compiler
    working-set
    section/symbol retrieval
    Capsule
    Receipt
    context_request gate

P3：接回完整治理链
    Intake
    Plan
    PreAction
    Execute
    Verify
    Archive

P4：双栈 Compact/Resume
    Claude Code cache + L1-L5 边界
    OpenCode prune + SQLite 审计

P5：L2、多 Agent 与模型路由
    Flash 原子执行
    高阶模型隔离审查
    Knowledge Patch 回传
```

这里有一个重要调整：

> 从文档规范描述上，主链仍是 Intake → Plan → Execute → Verify → Archive；从工程迁移顺序上，必须先止住 Context 泄漏，否则实施重构本身就会继续产生巨量上下文。

---

# 十、本部分完成判定

第 1/8 部分冻结了以下内容：

```text
✅ 最终分 8 次，不超过用户要求的 10 次
✅ 统一 L1 Base / L2 Enhance
✅ 冻结主治理链与 Context Engine 的横切职责
✅ 状态四件套升级为分责七件套
✅ 明确 Hot Card ⊂ Context Capsule
✅ 选择确定性 Context Compiler，不选 Base 智能 Router
✅ 冻结四平面架构与系统不变量
✅ 给出最终目录骨架、指标与实施优先级
```

后续章节不得推翻本部分；若发现知识库实现与本裁决冲突，按以下优先级处理：

```text
安全与真相不变量
  > VerifyGate 完成语义
  > 文档记忆 / Context 分离
  > 最新可执行实现
  > 旧命名和旧目录兼容
  > 历史建议原文
```

## 下一部分：第 2/8 部分

将完整输出：

```text
L1 Base / L2 Enhance 最终工作流
- IntakeGate
- PlanBuilder
- PreActionGate
- Executor Ledger
- VerifyGate
- Archive + Memory Writeback
- 状态转换图
- manifest/state/plan/evidence Schema
- ASK_USER / BLOCKED / VERIFIED 的持久化规则
- L1 三步法与 L2 五步法的完整可执行模板
```

