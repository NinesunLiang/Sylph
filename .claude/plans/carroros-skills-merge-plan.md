# CarrorOS 技能合并方案

> 文档版本: v1.0
> 创建日期: 2026-07-12
> 覆盖范围: lx-oma-* 四合一 + lx-oracle-* 三合一 + lx-ghost 评估

---

## 目录

1. [当前技能全景](#1-当前技能全景)
2. [A. OMA 四件套分析 (lv1)](#a-oma-四件套分析)
3. [B. Oracle 三件套分析 (lv1)](#b-oracle-三件套分析)
4. [C. lx-ghost 重叠分析](#c-lx-ghost-重叠分析)
5. [D. 合并方案详述 (lv2)](#d-合并方案详述)
6. [E. 风险与注意事项](#e-风险与注意事项)

---

## 1. 当前技能全景

### 1.1 被分析技能清单

| 技能 | 版本 | 类别 | 角色 | 文件数 |
|------|------|------|------|--------|
| lx-oma-gov | v1.2.1 | OMA 治理 | PRD 治理、漂移检测 | 8 |
| lx-oma-hier | v1.3.2 | OMA 拆解 L1 | 分层 PRD 拆解 | 6 |
| lx-oma-orch | v1.2.2 | OMA 编排 | Pipeline 编排器 | 10 |
| lx-oma-split | v1.2.1 | OMA 拆解 L2 | 特性级 RPE 拆解 | 5 |
| lx-oracle-review | 无版本号 | Oracle 编排 | 双 Agent 审核编排 | 2 |
| lx-oracle-agent | 无版本号 | Oracle 静态 | 静态分析 (Oracle-D) | 2 |
| lx-oracle-meta | 无版本号 | Oracle 运行时 | 运行时验证 (Oracle-V) | 2 |
| lx-ghost | v1.4.1 | 自主探索 | 方向驱动自主探索 | 5 |

**7 个技能总计: 40 个文件**

### 1.2 技能依赖图（来自 skill-dependencies.yaml）

```
┌──────────────────────────────────────────────────────────────┐
│                     lx-oma-orch (编排器)                       │
│   orchestrates: hier, split, gov, rpe                         │
└────┬───────────┬───────────┬──────────────┬──────────────────┘
     │           │           │              │
     ▼           ▼           ▼              ▼
 lx-oma-hier  lx-oma-split lx-oma-gov   lx-rpe (不在范围)
 (L1 拆解)    (L2 拆解)    (治理)       (开发执行)

 Pipeline: hier → split → gov → rpe → dev
```

```
┌─────────────────────────────────────────────────────┐
│              lx-oracle-review (编排器)                │
│  oracle_spawn.py → 静态 + 运行时 → meta_oracle.py    │
└────┬────────────────────────────┬───────────────────┘
     │                            │
     ▼                            ▼
 lx-oracle-agent              lx-oracle-meta
 (static_oracle_agent.py)     (runtime_oracle_agent.py)
 (Oracle-D, 偏紧, 广度优先)   (Oracle-V, 偏松, 深度优先)
                              → meta_oracle.py (G1-G4 聚合)
```

---

## 2. A. OMA 四件套分析

### 2.1 逐技能提取

#### lx-oma-gov — OMA PRD 治理
| 项目 | 内容 |
|------|------|
| **用途** | reconcile/propagate 增量同步、冲突裁决、漂移检测、治理状态面板 |
| **状态机** | need_input → init/reconcile/status/audit → done |
| **关键流程** | 变更检测(L1/L2/L3分级) → verifier质量门禁 → resolve人工裁决 → propagate增量传播 |
| **Dependencies** | 自行管理 state/ + source-prds/ + snapshots/ |
| **文件** | SKILL.md + governance-spec.md + HUMAN-IN-THE-LOOP-GATE.md + 4 references + 1 state |
| **共享引用** | degradation-escalation · decision-chain · execution-workflow · skill-chaining · observability |

#### lx-oma-hier — 分层 PRD 拆解大脑
| 项目 | 内容 |
|------|------|
| **用途** | 超大型 PRD 按功能域 MECE 拆分为多个 Sub PRD（黑盒/接口契约/Mock数据/内部闭环） |
| **状态机** | need_input → reading → analyzing → generating → verifying → done |
| **关键流程** | 识别业务实体 → 按职责聚类 → 正交性校验 → 边界确认 → 依赖分析 → 输出 Sub PRD |
| **Dependencies** | 委托 lx-oma-split 进一步拆解为特性级 RPE；引用 lx-oma-orch 编排 |
| **文件** | SKILL.md + 5 references |
| **共享引用** | degradation-escalation · decision-chain · execution-workflow · skill-chaining |

#### lx-oma-orch — Pipeline Orchestrator
| 项目 | 内容 |
|------|------|
| **用途** | 4-skill 管线编排（状态查看/阶段推进/Oracle 门禁/并行开发管理） |
| **状态机** | idle → status/advance/gate/run/dev → done |
| **关键流程** | status(管线全景) → advance(推进阶段) → gate(Oracle门禁) → run(直接路由) → dev(并行开发) |
| **Dependencies** | 编排 lx-oma-hier, lx-oma-split, lx-oma-gov, lx-rpe |
| **文件** | SKILL.md + 9 references |
| **共享引用** | degradation-escalation · decision-chain · execution-workflow · skill-chaining |

#### lx-oma-split — 一人成军拆解大脑
| 项目 | 内容 |
|------|------|
| **用途** | 将 Sub PRD 拆解为正交 feature 分支 (prd/{sub_prd}/{feature}) |
| **状态机** | need_input → reading → analyzing → scaffolding → verifying → done |
| **关键流程** | 参数读取 → MECE正交拆解(3-6 Feature) → 脚手架构建 → 接口归属校验 → 战报交付 |
| **Dependencies** | 委托 lx-oma-hier 提供 Sub PRD；引用 lx-oma-orch 编排 |
| **文件** | SKILL.md + 4 references |
| **共享引用** | degradation-escalation · decision-chain · execution-workflow · skill-chaining · pipeline-contract · observability |

### 2.2 异同点矩阵

| 维度 | lx-oma-hier | lx-oma-split | lx-oma-gov | lx-oma-orch |
|------|-------------|--------------|-------------|-------------|
| **管线阶段** | Stage 1 | Stage 2 | Stage 3 | 编排器（跨阶段） |
| **输入** | master-prd.md | sub-prd domain | master + feature PRDs | pipeline state |
| **输出** | sub-prds/domain-*.md | prd/{sub_prd}/feat-* | gov-report.yaml | pipeline_advancement |
| **Oracle 门禁** | 使用 (G1) | 使用 (接口校验) | 使用 (L3 冲突) | 创建门禁 |
| **MECE 原则** | 是（核心方法） | 是（核心方法） | 否 | 否 |
| **状态机风格** | 线性 5 步 | 线性 4 步 | 分支状态机 | 分支路由 |
| **人工介入** | 否 | 是（审核门禁） | 是（L3 冲突裁决） | 是（Oracle 门禁） |
| **并行能力** | 否 | 否（输出后并行 rpe） | 否 | 管理并行开发 |
| **共享引用路径** | 同 ../references/oma/ | 同 | 同 | 同 |
| **专属引用数** | 5 | 4 | 4 | 9 |
| **互相引用的重复 refs** | error-codes (hier+orch), observability (hier+orch), pipeline (hier/orch/split) |

### 2.3 合并可行性

**高度可行。** 四个技能构成清晰的管线链：hier→split→gov 为三个顺序阶段，orch 为编排器统筹三者。天然适合合为一个 lx-oma 技能，通过 subcommand 分发。

**关键考量:**
- 四个技能共享同一套 OMA 公共引用（../references/oma/），天然共享基础
- 每个 skill 的 references 可合并为 references/ 下的子目录
- orch 的 9 个 ref、hier 的 5 个 ref、gov 的 4 个 ref、split 的 4 个 ref – 存在 3 个重复引用（error-codes, observability, pipeline）
- execution_mode 不同：hier/gov/orch 为 stepwise, split 为 race — 合并后需要统一声明或按 subcommand 动态选择

---

## 3. B. Oracle 三件套分析

### 3.1 逐技能提取

#### lx-oracle-review — 完整双 Agent Oracle 审核
| 项目 | 内容 |
|------|------|
| **用途** | 同时执行静态分析 + 运行时分析，再经 Meta-Oracle G1-G4 聚合评分 |
| **角色** | orchestrator — 编排 Static + Runtime 双 Oracle |
| **Dependencies** | lx-oracle-agent, lx-oracle-meta |
| **文件** | SKILL.md + references/body.md (81 行) |
| **脚本** | oracle_spawn.py（scripts/ 目录） |

#### lx-oracle-agent — Oracle Agent 静态分析审核
| 项目 | 内容 |
|------|------|
| **用途** | 基于 Oracle-D 协议的偏紧静态检查：scope 越界、危险路径/命令、file:line 证据 |
| **角色** | critic — 静态分析，偏紧审查 |
| **Dependencies** | 无 |
| **文件** | SKILL.md + references/body.md (85 行) |
| **脚本** | static_oracle_agent.py（scripts/ 目录） |

#### lx-oracle-meta — Meta-Oracle 运行时验证审核
| 项目 | 内容 |
|------|------|
| **用途** | 基于 Oracle-V 协议的偏松运行时验证：token 进度、executor 证据、audit 事件、G1-G4 门禁评分 |
| **角色** | critic — 运行时验证，偏松审查 |
| **Dependencies** | 依赖 Oracle Agent 的静态输出做二次判断 |
| **文件** | SKILL.md + references/body.md (103 行) |
| **脚本** | runtime_oracle_agent.py, meta_oracle.py（scripts/ 目录） |

### 3.2 异同点矩阵

| 维度 | lx-oracle-agent | lx-oracle-meta | lx-oracle-review |
|------|-----------------|----------------|------------------|
| **类型** | 执行引擎 | 执行引擎 | 编排器 |
| **协议** | Oracle-D (Decision) | Oracle-V (Verification) | Oracle-D+V 双检 |
| **倾向** | 偏紧（不确定=有问题） | 偏松（不确定=运行时确认） | 互补 |
| **扫描方法** | 广度优先 — 全文件扫描 | 深度优先 — 针对性证伪 | 双上下文独立执行 |
| **检查维度** | scope/危险路径/命令/证据完整性 | G1(进度)/G2(失败)/G3(通过)/G4(哲学) | 聚合静态+运行时 |
| **是否执行代码** | 否 | **是**（实弹测试/bash 执行） | 是（编排） |
| **输出** | file:line 级别的静态裁决 | token 进度 + G1-G4 评分 | 聚合裁决 (ACCEPT/ADVISORY/REJECT/ESCALATE) |
| **SKILL.md 体积** | 15 行 frontmatter | 15 行 frontmatter | 18 行 frontmatter |
| **body.md 体积** | 85 行 | 103 行 | 81 行 |
| **脚本依赖** | static_oracle_agent.py | runtime_oracle_agent.py, meta_oracle.py | oracle_spawn.py |

### 3.3 合并可行性

**高度可行。** 三个技能形成"编排器 + 2 个执行引擎"的经典架构，天然适合合并。

**关键考量:**
- SKILL.md 都非常小（15-18 行），合并后约 50 行 frontmatter + 模式路由逻辑
- body.md 各自独立且充实（81-103 行），建议保留为 3 个独立 body 文件
- 脚本已经在 scripts/ 下统一存放，无需移动
- lx-oracle-review 的审核原则(body.md 行 9-18) 可提取为公共原则
- lx-oracle-meta 的 G1-G4 评分部分可以留在运行时 body 中

---

## 4. C. lx-ghost 重叠分析

### 4.1 lx-ghost 定位

| 项目 | 内容 |
|------|------|
| **用途** | 方向驱动的自主探索 — Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告 |
| **执行模式** | 增量 poll 迭代（每轮只做一步，方向漂移自检） |
| **触发** | ghost mode / 幽灵模式 / 自主探索 |
| **文件** | SKILL.md + 3 references + 1 script (lx-ghost.sh) |
| **关键阶段** | Phase 0: 前置澄清 → Phase 0.5: Oracle 审核(5维门禁) → 全自动轮询 → 退出报告 |

### 4.2 lx-ghost Phase 0.5 Oracle 审核 vs lx-oracle-meta G1-G4

| 维度 | lx-ghost Phase 0.5 | lx-oracle-meta |
|------|--------------------|----------------|
| **触发时机** | ghost 激活前（计划验证） | 执行后（结果验证） |
| **检查目的** | "计划是否可执行" | "执行是否完整" |
| **D1 方向适配** | 检查 ghost vs goal 选择 | 不涉及 |
| **D2 歧义穷尽** | Phase 0 是否有未覆盖歧义 | 不涉及 |
| **D3 硬边界完整** | 任务是否触碰未声明禁区 | 不涉及 |
| **D4 决策链覆盖** | 矩阵是否覆盖该场景 | 不涉及 |
| **D5 退出条件** | 成功/失败信号是否可验证 | 不涉及 |
| **G1 Token 进度** | 不涉及 | 检查 done/total 匹配 |
| **G2 失败模式** | 不涉及 | 检查 FAIL/ERROR/Traceback |
| **G3 通过证据** | 不涉及 | 检查 PASS/exit code 0 |
| **G4 哲学一致性** | 不涉及 | 检查软完成语 |
| **审计事件** | 不涉及 | 检查 verify 事件 |

### 4.3 重叠结论

**lx-ghost 与 lx-oracle-meta 功能上不重叠。**

两者检查的维度、触发时机、目的完全不同：
- lx-ghost Phase 0.5: **事前计划质量门禁**（自主探索计划是否安全、完整、可退出）
- lx-oracle-meta: **事后执行验证引擎**（代码变更是否通过测试、证据完整）

**建议的方案：**
1. **保留 lx-ghost**（其自主探索模式是独特功能，与 lx-goal 的"目标驱动"形成互补）
2. **精简 ghost 的 Oracle 审核逻辑** — 将 Phase 0.5 改为委托调用合并后的 lx-oracle duo 模式，删除 ghost-oracle-audit.md 中重复的 Oracle 逻辑
3. **不删除 lx-ghost** — 除非其功能可完全被 lx-goal 吸收（需要额外分析 lx-goal 的能力边界）

---

## 5. D. 合并方案详述

### 5.1 方案总览

| 合并组 | 原技能 | 目标技能 | 合并方式 |
|--------|--------|----------|----------|
| OMA | lx-oma-hier, lx-oma-split, lx-oma-gov, lx-oma-orch | **lx-oma** | subcommand 分发 |
| Oracle | lx-oracle-agent, lx-oracle-meta, lx-oracle-review | **lx-oracle** | mode 参数分发 |
| Ghost | lx-ghost | **保留但精简** | 移除内嵌 Oracle 逻辑 |

---

### 5.2 OMA 合并方案: lx-oma-gov + hier + orch + split → lx-oma

#### 5.2.1 新 SKILL.md 结构

```yaml
---
name: lx-oma
description: OMA Pipeline — hierarchically decompose, split into features, govern, orchestrate
version: v2.0.0
harness_version: ">=6.3.0"
status: stable
argument-hint: >
  hier <path> [output_dir] | split <path> [--pipeline <id>] |
  gov init|reconcile|resolve|propagate|status|audit [path] |
  orch status|advance|gate|run|dev
when_to_use: PRD 全生命周期 — 拆解、拆分、治理、编排
triggers: ["/lx-oma", "oma", "pipeline"]
role: "OMA — Pipeline lifecycle (hier → split → gov → rpe)"
execution_mode: stepwise
---
```

#### 5.2.2 Subcommand 分发逻辑

```
/lx-oma hier <path>          → L1 分层拆解（原 lx-oma-hier）
/lx-oma split <path>         → L2 特性拆解（原 lx-oma-split）
/lx-oma gov init|reconcile... → 治理操作（原 lx-oma-gov）
/lx-oma orch status|advance... → 管线编排（原 lx-oma-orch）
```

#### 5.2.3 文件重组

| 阶段 | 文件 | 去向 |
|------|------|------|
| **主文件** | SKILL.md × 4 | 合并为 1 个 SKILL.md |
| **Gov 专属** | governance-spec.md, HUMAN-IN-THE-LOOP-GATE.md, state/sync-state.md | `gov/` 子目录 |
| **Gov refs** | directory-structure.md, commands-reconcile.md, commands-audit.md, pipeline-integration.md | `references/gov/` |
| **Hier refs** | error-codes.md, observability.md, pipeline.md, sub-prd-template.md, verification-gate.md | `references/hier/` |
| **Orch refs** | status-panel.md, advance-flow.md, oracle-gate.md, dev-management.md, pipeline-contract.md, interface-contract.md, manual-review.md | `references/orch/` |
| **(+ error-codes.md, observability.md)** | | `references/orch/` 去重 |
| **Split refs** | mece-checklist.md, scaffolding-template.md, interface-verification.md, delivery-report.md | `references/split/` |
| **共享引用** | degradation-escalation.md, decision-chain.md, execution-workflow.md, skill-chaining.md, observability.md, pipeline-contract.md | `skills/references/oma/`（不变） |

#### 5.2.4 去重清单

| 引用文件 | 出现于 | 处理方式 |
|----------|--------|----------|
| error-codes.md | hier + orch | 去重 → 只留 `references/orch/` 或 `shared/` |
| observability.md | hier + orch + 共享 | 保留共享(`skills/references/oma/`)，删除 hier 和 orch 中本地副本 |
| pipeline.md / pipeline-contract.md | hier + orch + split + 共享 | 保留共享(`skills/references/oma/`)，删除本地副本 |

#### 5.2.5 预估文件数变化

| 指标 | 合并前 | 合并后 | 变化 |
|------|--------|--------|------|
| SKILL.md | 4 | 1 | -3 |
| references | 22 | 19 | -3（去重） |
| state/nodes | 1 | 1 | 不变 |
| 总计 | 29 | 22 | **-7** |

---

### 5.3 Oracle 合并方案: lx-oracle-review + agent + meta → lx-oracle

#### 5.3.1 新 SKILL.md 结构

```yaml
---
name: lx-oracle
description: Oracle quality gate system — static analysis, runtime verification, dual-agent review
version: v2.0.0
harness_version: ">=6.3.0"
status: stable
argument-hint: >
  static <task-id> [--plan <path>] [--executor <path>] |
  runtime <task-id> [--token <path>] [--executor <path>] [--audit-dir <path>] |
  duo <task-id> [--plan <path>] [--executor <path>] [--token <path>] [--audit-dir <path>]
when_to_use: >
  static: verify/archive 前静态预检、架构终审、危险操作前置审核
  runtime: 执行后运行时验证、方案事前审核
  duo: 高风险场景双重验证、Release 门禁
triggers: ["/lx-oracle", "oracle", "oracle审核"]
role: "Oracle gate — static (Oracle-D) + runtime (Oracle-V) + dual review"
execution_mode: stepwise
---
```

#### 5.3.2 Mode 分发逻辑

```
/lx-oracle static <task-id>   → 静态分析（原 lx-oracle-agent）
/lx-oracle runtime <task-id>  → 运行时验证（原 lx-oracle-meta）
/lx-oracle duo <task-id>      → 双 Agent 审核（原 lx-oracle-review）
```

#### 5.3.3 文件重组

| 原文件 | 去向 |
|--------|------|
| lx-oracle-review/SKILL.md | 吸收进 lx-oracle/SKILL.md (duo 模式) |
| lx-oracle-agent/SKILL.md | 吸收进 lx-oracle/SKILL.md (static 模式) |
| lx-oracle-meta/SKILL.md | 吸收进 lx-oracle/SKILL.md (runtime 模式) |
| lx-oracle-review/references/body.md | `references/body-duo.md`（双审流程） |
| lx-oracle-agent/references/body.md | `references/body-static.md`（静态审核） |
| lx-oracle-meta/references/body.md | `references/body-runtime.md`（运行时审核） |
| 公共审核原则（body.md 行 9-18 等） | `references/principles.md`（提取公共部分） |
| scripts/oracle_spawn.py | 不变（keep in scripts/） |
| scripts/static_oracle_agent.py | 不变 |
| scripts/runtime_oracle_agent.py | 不变 |
| scripts/meta_oracle.py | 不变 |

#### 5.3.4 公共审核原则提取

当前三个 body.md 中存在重复的审核原则描述，合并后可提取为 `references/principles.md`：

- Oracle-D / Oracle-V 协议统一声明
- 哲学层级的优先级 (#4>#6>#3>#7>#5>#2>#1)
- 0 信任原则定义
- 证据门禁规则
- 裁决等级体系 (ACCEPT/ADVISORY/REJECT/ESCALATE) — 现在定义在 body-duo.md 中，但三模式共享

#### 5.3.5 预估文件数变化

| 指标 | 合并前 | 合并后 | 变化 |
|------|--------|--------|------|
| SKILL.md | 3 | 1 | -2 |
| references | 3 | 4（含 principles.md） | +1 |
| 脚本 | 4 | 4 | 不变 |
| 总计 | 10 | 9 | **-1** |

---

### 5.4 lx-ghost 处理方案

#### 5.4.1 建议：保留 + 精简（非删除）

**理由：** lx-ghost 的功能域（方向驱动自主探索）与 lx-oracle-meta（通用运行时验证）不重叠。lx-ghost 提供了独特的"方向驱动、增量 poll 迭代、事前 Oracle 门禁"模式，与 lx-goal 的"目标驱动、逐项 task-done"形成互补。

#### 5.4.2 精简措施

| 当前 | 建议 |
|------|------|
| 内嵌 Phase 0.5 Oracle 审核逻辑（ghost-oracle-audit.md） | 改为委托调用 `lx-oracle duo` 模式 |
| ghost-oracle-audit.md | 删除（或简化为委托 lx-oracle 的说明） |
| ghost-phase0.md 中部分 Oracle 描述 | 精简为引用 lx-oracle |
| 与原 lx-oracle-meta 重复的审核基础设施 | 完全移除，复用 lx-oracle |

#### 5.4.3 若强行删除

如果用户坚持删除 lx-ghost，需要考虑：
1. **lx-goal 能力评估** — lx-goal 是否可覆盖方向驱动模式（当前 lx-goal 是目标驱动，不适合开放探索）
2. **lx-oracle 能否接管** — 可以接管 Phase 0.5 审核部分，但自主 poll 迭代需要新 skill 或 lx-goal 扩展
3. **功能损失** — 丢失"方向驱动自主探索"模式，变为仅在明确目标下工作

---

## 6. E. 风险与注意事项

### 6.1 执行风险

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 修改 skill-dependencies.yaml 中的依赖声明 | 低 | 确保更新所有技能引用路径 |
| references/oma/ 公共引用被多个 skill 引用 | 低 | 保持 skills/references/oma/ 不变 |
| oracle_spawn.py 中硬编码的 skill 路径 | 中 | 脚本中无硬编码 skill 路径，全部通过参数传递 |
| execution_mode 不一致（stepwise vs race） | 低 | SKILL.md 根级声明 stepwise，在正文中注明 split 子命令的 race 模式 |
| 其他技能引用这些 skill 名称 | 中 | 搜索全库的 `/lx-oma-*` `/lx-oracle-*` 引用并更新 |

### 6.2 向后兼容

| 原命令 | 新命令 | 兼容方式 |
|--------|--------|----------|
| /lx-oma-hier | /lx-oma hier | 保留触发器别名 /lx-oma-hier → /lx-oma hier |
| /lx-oma-split | /lx-oma split | 同上 |
| /lx-oma-gov | /lx-oma gov | 同上 |
| /lx-oma-orch | /lx-oma orch | 同上 |
| /lx-oracle-agent | /lx-oracle static | 保留触发器别名 |
| /lx-oracle-meta | /lx-oracle runtime | 保留触发器别名 |
| /lx-oracle-review | /lx-oracle duo | 保留触发器别名 |
| /lx-ghost | 不变 | 保留 |

### 6.3 后续行动建议

1. **先执行 Oracle 合并**（3→1，改动最小，风险最低）
2. **再执行 OMA 合并**（4→1，改动最大，建议分步做）
3. **最后处理 lx-ghost**（确认策略后再改）
4. **更新 skill-dependencies.yaml** — 将 8 个技能声明缩减为 4 个
5. **更新 AGENTS.md** — 搜索所有 `/lx-oma-*` 和 `/lx-oracle-*` 引用并替换
6. **更新其他技能** — 搜索引用这些旧 skill 名称的技能文件
7. **回归验证** — 验证所有管线命令在新入口下正常工作

---

## 附录 A: 技能文件完整性清单

### OMA 合并前 (29 文件)

```
lx-oma-gov/ (8)
├── SKILL.md
├── governance-spec.md
├── HUMAN-IN-THE-LOOP-GATE.md
├── state/sync-state.md
└── references/
    ├── directory-structure.md
    ├── commands-reconcile.md
    ├── commands-audit.md
    └── pipeline-integration.md

lx-oma-hier/ (6)
├── SKILL.md
└── references/
    ├── error-codes.md
    ├── observability.md
    ├── pipeline.md
    ├── sub-prd-template.md
    └── verification-gate.md

lx-oma-orch/ (10)
├── SKILL.md
└── references/
    ├── status-panel.md
    ├── advance-flow.md
    ├── oracle-gate.md
    ├── dev-management.md
    ├── pipeline-contract.md
    ├── interface-contract.md
    ├── manual-review.md
    ├── error-codes.md
    └── observability.md

lx-oma-split/ (5)
├── SKILL.md
└── references/
    ├── mece-checklist.md
    ├── scaffolding-template.md
    ├── interface-verification.md
    └── delivery-report.md
```

### OMA 合并后 (22 文件)

```
lx-oma/ (22)
├── SKILL.md
├── gov/
│   ├── governance-spec.md
│   ├── HUMAN-IN-THE-LOOP-GATE.md
│   └── state/sync-state.md
├── references/
│   ├── gov/
│   │   ├── directory-structure.md
│   │   ├── commands-reconcile.md
│   │   ├── commands-audit.md
│   │   └── pipeline-integration.md
│   ├── hier/
│   │   ├── sub-prd-template.md
│   │   └── verification-gate.md
│   ├── orch/
│   │   ├── status-panel.md
│   │   ├── advance-flow.md
│   │   ├── oracle-gate.md
│   │   ├── dev-management.md
│   │   ├── pipeline-contract.md
│   │   ├── interface-contract.md
│   │   └── manual-review.md
│   └── split/
│       ├── mece-checklist.md
│       ├── scaffolding-template.md
│       ├── interface-verification.md
│       └── delivery-report.md
```

### Oracle 合并前 (6 文件)

```
lx-oracle-agent/ (2)
├── SKILL.md
└── references/body.md

lx-oracle-meta/ (2)
├── SKILL.md
└── references/body.md

lx-oracle-review/ (2)
├── SKILL.md
└── references/body.md
```

### Oracle 合并后 (5 文件)

```
lx-oracle/ (5)
├── SKILL.md
└── references/
    ├── principles.md          (公共审核原则，新增)
    ├── body-static.md         (原 lx-oracle-agent body)
    ├── body-runtime.md        (原 lx-oracle-meta body)
    └── body-duo.md            (原 lx-oracle-review body)
```

---

> **本合并方案可作为实际合并执行的基准文档。** 建议合并时保持"先搬后拆"策略：先创建目标 lx-oma/ 和 lx-oracle/ 目录并同步文件，确认无误后再删除旧技能目录。
