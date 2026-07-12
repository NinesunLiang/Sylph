# data.md 资产筛选裁决：Skills + Hooks ROI 集合

## 0. 总裁决

**裁决等级：附条件核准，必须执行瘦身。**

`data.md` 是 CarrorOS 的重要资产清单，但当前资产规模已经明显超过第三轮重构后的推荐形态：

```text
Skills: 27
Hooks: 77
```

这与最新重构方向冲突。

当前 CarrorOS 的主方向已经从“多 Hook 治理”转向：

```text
Base:
  Plan → Step → Verify → Archive
  少 Hook、低噪声、低阶模型友好

Enhance:
  Base + 低频 Oracle + Context + Flywheel
  只在高风险、长任务、失败复盘、最终验收时增强
```

因此本轮筛选原则是：

```text
保留能增强状态、证据、验证、安全、归档、学习飞轮的资产。
删除或降级会制造注意力稀释、重复治理、常驻审判、高频噪声、伪智能感的资产。
```

一句话裁决：

```text
data.md 不是要扩展，而是要把 27 skills / 77 hooks 压成少量高 ROI 核心资产。
```

---

# 1. ROI 判定标准

## 1.1 高 ROI 资产

满足任一条件即可保留：

```text
1. 直接减少假完成 false_done。
2. 直接减少越界修改 scope_violation。
3. 保护敏感信息、危险命令、生产环境。
4. 支撑 compact / resume / archive 的状态闭环。
5. 支撑最小验证基准 bench。
6. 只在低频关键点触发，输出短、稳定、可审计。
7. 与 Base / Enhance 二元法一致。
```

典型高 ROI：

```text
VerifyGate
PreAction / Safety Gate
Context handoff
Archive tombstone
Audit JSONL
Varlock 隐私脱敏
Base todo / task loop
Skill validator / lint
低频 Oracle
error-dna 高价值过滤
```

---

## 1.2 低 ROI / 高噪声资产

满足任一条件应删除或降级：

```text
1. 常驻 PostToolUse 审判。
2. 每一步都触发 Oracle / Meta-Oracle。
3. 输出大量提示但不改变执行结果。
4. 与 token / plan / executor / audit 多真源冲突。
5. 在 Base 中引入 research / error-dna / claude-next。
6. 只做概念包装，没有硬证据或硬阻断。
7. 需要模型理解复杂层级 L1.5 / L2.5 / L3+ 才能正确使用。
8. Hook 撤掉后任务完成率不下降、假完成不上升。
```

典型低 ROI：

```text
Base PostToolUse
Enhance PostToolUse 常驻版
Oracle 常驻触发
Meta-Oracle 常规入口
无来源 watermark 百分比
handoff 内新状态定义
plan.md 内执行流水
executor.md 内新计划
acceptance.md 独立完成门
statusline 历史记录作为 evidence
```

---

# 2. 立即删除集合

这些资产与第三轮瘦身方向冲突，建议从 active 运行链路中删除。

## 2.1 Base PostToolUse

**裁决：删除。**

原因：

```text
1. Base 目标是低阶模型友好，PostToolUse 会持续打断注意力。
2. Base 应依赖 Plan → Step → Verify → Archive，而不是每次工具后审判。
3. Hook 输出增加 token 消耗，但不能保证减少假完成。
4. 知识库已明确列入删除清单。
```

ROI：

```text
收益：低
噪声：高
风险：注意力稀释、重复裁决、低阶模型迷失
最终处理：删除
```

替代：

```text
Base 使用 carros_base.py verify / archive 前静态检查。
```

---

## 2.2 Enhance PostToolUse 常驻版

**裁决：删除常驻触发，保留事件化触发。**

原因：

```text
1. Enhance 可以有更强治理，但不需要每次工具调用都审判。
2. PostToolUse 高频触发会吞噬上下文。
3. 真实高价值触发点应是 phase_end、final_acceptance、高风险 step、连续失败。
```

ROI：

```text
收益：中
噪声：高
最终处理：降级为低频事件触发
```

替代：

```text
只在以下事件触发：
- 高风险 step 前
- phase_end
- final_acceptance
- 连续失败 3 次
- 安全 / 生产 / 架构不可逆操作
```

---

## 2.3 Oracle 常驻触发

**裁决：删除。**

原因：

```text
1. Oracle 是高阶复核，不是每步完成门。
2. 完成唯一硬门是 VerifyGate。
3. 常驻 Oracle 会制造“LLM 审 LLM”的虚假安全感。
4. 多次知识库均要求 Oracle 低频。
```

ROI：

```text
收益：中
噪声：极高
风险：成本高、延迟高、伪复核、模型自嗨
最终处理：删除常驻版
```

保留低频版：

```text
Oracle 保留：
- L2 任务启动 levelgate
- 高风险 step 前
- phase_end
- final_acceptance
- 连续失败 3 次后
```

---

## 2.4 Meta-Oracle 常规入口

**裁决：删除常规入口，仅保留极高风险入口。**

原因：

```text
1. Meta-Oracle 只能处理安全、生产、架构重大冲突。
2. 常规入口会把 Enhance 推向过度治理。
3. 双法官不是绝对正确，只能降低部分盲区。
```

ROI：

```text
收益：低到中
噪声：极高
最终处理：降级
```

保留条件：

```text
只允许：
- G1 架构不可逆
- G2 方案终审
- G3 Oracle 高分虚高 >= 9.0
- G4 Release / 生产发布
- 安全边界重大冲突
```

---

## 2.5 Base research.md

**裁决：删除。**

原因：

```text
1. Base 是中低风险执行闭环，不需要研究层。
2. research.md 会拉长上下文，增加模型分心。
3. 知识库明确要求 Base 不使用 research.md。
```

ROI：

```text
收益：低
噪声：中高
最终处理：删除 Base 入口
```

保留位置：

```text
只在 Enhance Plan 阶段使用。
```

---

## 2.6 Base error-dna.json

**裁决：删除。**

原因：

```text
1. Base 不做学习飞轮。
2. 低阶模型容易把 error-dna 当成当前任务证据。
3. error-dna 只适合 Enhance Archive 阶段沉淀。
```

ROI：

```text
收益：低
噪声：高
最终处理：删除 Base 入口
```

---

## 2.7 Base claude-next.md

**裁决：删除。**

原因：

```text
1. Base 不做长期风格学习。
2. claude-next 是经验层，不是任务执行层。
3. 写入时机必须是 Enhance Archive，而不是任务中途。
```

ROI：

```text
收益：低
噪声：高
最终处理：删除 Base 入口
```

---

## 2.8 无来源 watermark 百分比

**裁决：删除。**

原因：

```text
1. 没有 token 来源或 SQLite 来源的百分比是伪观测。
2. 伪水位会导致错误 compact / resume。
3. 知识库明确删除“无来源 watermark 百分比”。
```

ROI：

```text
收益：低
噪声：高
风险：错误降级、错误 compact
最终处理：删除
```

替代：

```text
Base:
  15/20 轮 compact

Enhance:
  只有可观测 token / SQLite 时使用 0-40 / 40-70 / 70+ 水位
  不可观测则 fallback 到 Base 轮数策略
```

---

## 2.9 handoff 中的新状态定义

**裁决：删除。**

原因：

```text
1. token.json 才是状态源。
2. handoff 只能是恢复摘要，不得定义新状态。
3. handoff 出现新状态会导致 resume 漂移。
```

ROI：

```text
收益：无
噪声：高
最终处理：删除
```

保留 handoff 最小字段：

```text
task_id
level
status
current_step
blocked
last_verified
next_action
risk
```

---

## 2.10 acceptance.md 独立完成门

**裁决：删除或降级为验收汇总。**

原因：

```text
1. VerifyGate 是唯一 step 完成硬门。
2. acceptance.md 作为完成门会制造第二真源。
3. Archive final-report 已经覆盖最终验收报告功能。
```

ROI：

```text
收益：低
噪声：中高
风险：多完成源冲突
最终处理：降级
```

保留方式：

```text
acceptance.md 只能作为验收摘要，不得裁决完成。
更推荐直接并入 final-report.md。
```

---

# 3. 保留集合：高 ROI 核心资产

## 3.1 lx-todo

**裁决：保留，但限制为 Base 轻量任务闭环。**

描述：

```text
轻量开发模式：捕获 → 分拣 → 执行 → 验证 → 关闭。
5 步单终端闭环，≤3 文件变更。
脚本：todo_queue.py
```

为什么保留：

```text
1. 与 Base 的 Plan → Step → Verify → Archive 高度一致。
2. 适合低阶模型和中小任务。
3. 单终端、少文件、少状态，抗分心能力强。
4. 可以作为 Base 的任务队列前身。
```

限制：

```text
1. 只用于 L1 / Base。
2. 限制 ≤3 文件变更。
3. 不接入 Oracle。
4. 不写 error-dna / claude-next。
5. 不做复杂长期项目治理。
```

ROI：

```text
收益：高
噪声：低
重构协调度：高
最终处理：保留并并入 Base
```

建议重命名或归属：

```text
lx-todo → base-task-loop
```

---

## 3.2 lx-validate-skill

**裁决：保留，升级为 omc_lint / skill_lint 的一部分。**

描述：

```text
验收新 skill 是否遵循原子化架构规则。
检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等规则。
脚本：validate_skill.py 等
```

为什么保留：

```text
1. 当前最大问题是资产膨胀，skill validator 正好用于阻止继续膨胀。
2. 与最小验证基准、omc_lint 方向一致。
3. 能把“高价值 skill”从主观判断变成结构化检查。
4. ROI 高于继续扩 Oracle。
```

限制：

```text
1. 不应作为每次任务执行 Hook。
2. 只在新增 / 修改 skill 时运行。
3. 只输出结构化错误，避免长篇建议。
```

ROI：

```text
收益：高
噪声：低
重构协调度：高
最终处理：保留并合并到 lint 系统
```

推荐并入：

```text
omc_lint.py:
  lint-token
  lint-plan
  lint-executor
  lint-audit
  lint-skill
```

---

## 3.3 lx-varlock

**裁决：强保留。**

描述：

```text
隐私脱敏代理管理器。
处理密码、API Key、Token 等敏感信息，确保明文不泄露在 AI 上下文中。
脚本：varlock.py
```

为什么保留：

```text
1. 直接防止敏感信息泄露，是硬安全资产。
2. 与第三轮 CLI 输出红线、audit 红线完全一致。
3. 对 Base 和 Enhance 都有价值。
4. 不依赖模型判断，属于确定性保护。
```

限制：

```text
1. 应作为敏感文件读写代理，不作为普通文件读取默认路径。
2. 输出必须短，默认只给 redacted diff / redacted summary。
3. 不得把完整 secret 写入 audit / executor / handoff。
```

ROI：

```text
收益：极高
噪声：低
风险降低：极高
重构协调度：极高
最终处理：保留为核心安全资产
```

推荐归属：

```text
Base + Enhance 共享。
```

---

## 3.4 update-carror-os

**裁决：保留，但加审批与隔离。**

描述：

```text
Carror OS 安装 / 更新技能。
自动保护 AGENTS.md 不被安装脚本污染。
备份 → 安装 → 恢复 → 验证 4 步闭环。
```

为什么保留：

```text
1. CarrorOS 自更新是高风险但必要能力。
2. 自动保护 AGENTS.md 与“AGENTS 是宪法，人类确认”原则一致。
3. 可作为系统更新的标准流程。
```

必须限制：

```text
1. 不得自动改 AGENTS.md。
2. 所有 AGENTS.md 修改只能生成 rule-suggestions.md。
3. 必须备份。
4. 必须验证。
5. 必须写 audit。
6. 高风险更新必须 ASK_USER。
```

ROI：

```text
收益：高
噪声：中
风险：高
重构协调度：中高
最终处理：保留，但只能 Enhance 或手动确认运行
```

推荐归属：

```text
Enhance-only / admin-only skill
```

---

# 4. 保留但降级集合

这些不是废物，但不能留在主执行链路。

## 4.1 research.md

**裁决：保留但 Enhance-only。**

为什么保留：

```text
1. 复杂任务需要事实层沉淀。
2. 可减少长任务中重复读取上下文。
3. 对架构、依赖、安全评估有价值。
```

为什么降级：

```text
1. Base 使用会分心。
2. research 不能成为状态源。
3. research 不能证明当前 step 完成。
```

ROI：

```text
Base ROI：低
Enhance ROI：高
最终处理：Enhance Plan 阶段使用
```

---

## 4.2 claude-next.md

**裁决：保留但只在 Enhance Archive 阶段写入。**

为什么保留：

```text
1. 可以沉淀用户纠正和重大失误。
2. 支撑长期学习飞轮。
```

为什么限制：

```text
1. 任务中途写入会污染执行上下文。
2. 不能自动改 AGENTS.md。
3. 不能记录普通失败。
```

写入条件：

```text
只记录：
- 用户明确纠正
- 重大失误
- 可复用规则建议
```

ROI：

```text
Base ROI：低
Enhance ROI：中高
最终处理：保留，Archive-only
```

---

## 4.3 error-dna.json

**裁决：保留但强过滤。**

为什么保留：

```text
1. 能沉淀重复失败模式。
2. 对 Enhance 长期任务有价值。
```

为什么限制：

```text
模糊“高价值错误”会让 error-dna 变噪音池。
```

必须满足三闸门：

```text
1. 有结构化触发源：
   测试失败码 / 构建非零退出 / Oracle REJECT / 用户显式纠正词

2. 非重复：
   与已有 pattern 去重

3. 可定位：
   有 file:line 或 command
```

三者缺一：

```text
不入库，只记 raw log。
```

ROI：

```text
无过滤 ROI：低，噪声极高
强过滤 ROI：高
最终处理：保留，Enhance Archive-only
```

---

## 4.4 Oracle / Meta-Oracle

**裁决：保留低频版，删除常驻版。**

为什么保留：

```text
1. 对高风险 auth / payment / permission / migration / release 有价值。
2. 可发现 VerifyGate 静态检查看不到的架构风险。
3. 对 final_acceptance 有复核价值。
```

为什么限制：

```text
1. LLM 审 LLM 有同源盲区。
2. 高频触发成本高。
3. 不能替代 VerifyGate。
```

ROI：

```text
常驻 Oracle ROI：低
低频关键点 Oracle ROI：高
Meta-Oracle 常规 ROI：低
Meta-Oracle 极高风险 ROI：中高
最终处理：低频保留
```

---

## 4.5 Statusline Hook

**裁决：保留，但只展示。**

为什么保留：

```text
1. 对 Claude Code / OpenCode 可观测性有价值。
2. 能提示 blocked、compact、fallback。
3. 输出短，对上下文影响小。
```

为什么限制：

```text
1. statusline 不是 evidence。
2. statusline 不得写 plan.md。
3. statusline 不得输出完整 token / executor / audit。
```

ROI：

```text
收益：中高
噪声：低
最终处理：保留展示层
```

---

# 5. Hooks 筛选总表

由于 `data.md` 里 Hooks 总数为 77，本轮不应逐个保留。应按类别裁决。

## 5.1 必保 Hook 类

```text
1. PreAction / Safety Gate
   用途：阻止危险命令、越界路径、生产操作。
   ROI：极高。

2. VerifyGate
   用途：防止假完成。
   ROI：极高。

3. Context Handoff
   用途：compact 前写 session-handoff。
   ROI：高。

4. Archive Hook
   用途：归档前 lint、final-report、tombstone。
   ROI：高。

5. Fallback Hook
   用途：能力不可用、Oracle 不可用、水位不可观测时裁决。
   ROI：高。

6. Varlock / Redaction Hook
   用途：敏感信息脱敏。
   ROI：极高。

7. Skill Lint Hook
   用途：新增 / 修改 skill 时检查。
   ROI：高。
```

---

## 5.2 应删除 Hook 类

```text
1. Base PostToolUse 全局 Hook
   删除原因：高频、低价值、注意力稀释。

2. Enhance PostToolUse 常驻 Hook
   删除原因：高频审判，成本过高。

3. 每 step Oracle Hook
   删除原因：Oracle 不应替代 VerifyGate。

4. 每 step Meta-Oracle Hook
   删除原因：极高噪声，边际收益低。

5. 无来源 context 百分比 Hook
   删除原因：伪观测。

6. 写入 handoff 新状态的 Hook
   删除原因：破坏 token 单一状态源。

7. 将 statusline 写成 evidence 的 Hook
   删除原因：展示层污染证据层。

8. 自动修改 AGENTS.md 的 Hook
   删除原因：AGENTS 是宪法，必须人类确认。

9. Base 飞轮写入 Hook
   删除原因：Base 不做长期学习。
```

---

## 5.3 应降级 Hook 类

```text
1. Oracle Trigger
   降级为低频关键点。

2. Meta-Oracle Trigger
   降级为安全 / 生产 / 架构不可逆。

3. LearningGate
   降级为 Archive-only。

4. Research Loader
   降级为 Enhance Plan-only。

5. OpenCode SQLite Observer
   降级为 Enhance-only，失败时 fallback 到 Base turn counter。

6. Claude Code Statusline
   降级为展示层，不参与完成裁决。
```

---

# 6. Skills 筛选总表

## 6.1 强保留 Skills

| Skill | 裁决 | 原因 | ROI |
|---|---|---|---|
| `lx-varlock` | 强保留 | 敏感信息脱敏，硬安全资产 | 极高 |
| `lx-todo` | 保留 | 与 Base 轻量闭环一致 | 高 |
| `lx-validate-skill` | 保留 | 抑制 skill 膨胀，支撑 lint | 高 |
| `update-carror-os` | 保留但审批 | 自更新必要，但高风险 | 高但需管控 |

---

## 6.2 条件保留 Skills

| 类型 | 裁决 | 条件 |
|---|---|---|
| research 类 skill | Enhance-only | 只在 Plan 阶段 |
| error-dna 类 skill | Enhance Archive-only | 三闸门过滤 |
| claude-next 类 skill | Enhance Archive-only | 只记录用户纠正 / 重大失误 |
| oracle 类 skill | Enhance-only | 低频关键点 |
| opencode / statusline 类 skill | 保留展示层 | 不做 evidence |

---

## 6.3 删除 Skills 类型

| 类型 | 删除原因 |
|---|---|
| Base 学习飞轮 skill | Base 不做长期学习，噪声高 |
| 常驻审判 skill | 注意力稀释，成本高 |
| 重复 todo / queue / planner skill | 与 `lx-todo` 功能重叠 |
| 自动改 AGENTS 的 skill | 违反人类确认原则 |
| 独立 acceptance 完成门 skill | 与 VerifyGate 冲突 |
| 无验证的总结 / 复盘 skill | 容易制造叙事性完成 |
| 复杂多层路由 skill | 与 L1/L2 二元法冲突 |

---

# 7. ROI 集合

## 7.1 Keep：高 ROI 核心集合

```text
KEEP_CORE = {
  "lx-varlock",
  "lx-todo",
  "lx-validate-skill",
  "update-carror-os",

  "PreActionGate",
  "VerifyGate",
  "ContextHandoff",
  "FallbackProtocol",
  "ArchiveTombstone",
  "AuditJsonl",
  "StatuslineDisplay",
  "SkillLint",
  "omc_lint",
  "bench_minimal_dataset"
}
```

理由：

```text
这些资产直接提升安全、验证、状态恢复、归档闭环、资产治理能力。
它们不是概念装饰，而是能降低 false_done、scope_violation、secret_leak、resume_drift 的确定性机制。
```

---

## 7.2 Keep-Limited：限制保留集合

```text
KEEP_LIMITED = {
  "research.md": "Enhance Plan-only",
  "claude-next.md": "Enhance Archive-only",
  "error-dna.json": "Enhance Archive-only + 三闸门",
  "Oracle": "Enhance low-frequency",
  "Meta-Oracle": "security/production/architecture only",
  "OpenCode SQLite Observer": "Enhance-only + fallback",
  "Claude Code Statusline Hook": "display-only",
  "LearningGate": "Archive-only"
}
```

理由：

```text
这些资产有价值，但只有在正确时机使用才有 ROI。
一旦常驻或进入 Base，就会变成噪声源。
```

---

## 7.3 Delete：删除集合

```text
DELETE = {
  "Base PostToolUse",
  "Enhance PostToolUse always-on",
  "Oracle always-on",
  "Meta-Oracle regular entry",
  "Base research.md",
  "Base error-dna.json",
  "Base claude-next.md",
  "acceptance.md as completion gate",
  "statusline as evidence",
  "handoff new-state definitions",
  "token large text fields",
  "plan execution logs",
  "executor new plans",
  "unsourced watermark percentage",
  "auto AGENTS.md modification",
  "user_continue_as_confirmation"
}
```

理由：

```text
这些资产要么制造多真源，要么增加注意力噪声，要么让 Base 变重，要么让完成裁决变模糊。
它们与第三轮瘦身后的方向冲突。
```

---

# 8. 推荐重构后的资产布局

```text
.omc/
  bin/
    carros_base.py
    omc_lint.py
    varlock.py
    statusline_renderer.py
    opencode_observer.py      # Enhance only
    oracle_engine.py          # Enhance only

  state/
    token.json
    counter.json
    session-handoff.md
    last-user-prompts.jsonl
    rule-suggestions.md       # AGENTS 修改建议，不自动应用

  docs/
    plan.md
    executor.md
    research.md               # Enhance Plan only
    claude-next.md            # Enhance Archive only
    error-dna.json            # Enhance Archive only

  audit/
    YYYYMMDD.jsonl

  archive/
    {task_id}/
      final-report.md
      token.final.json
      token.tombstone.json
      audit-manifest.json

bench/
  dataset.json
  tasks/
  results/
  reports/
```

---

# 9. 最终执行指令

## 9.1 Base 最小运行资产

Base 只允许默认加载：

```text
1. token.json
2. counter.json
3. plan.md
4. executor.md
5. session-handoff.md
6. audit jsonl
7. carros_base.py
8. omc_lint.py
9. varlock.py
```

Base 禁止默认加载：

```text
1. research.md
2. claude-next.md
3. error-dna.json
4. Oracle
5. Meta-Oracle
6. OpenCode SQLite
7. 常驻 PostToolUse
```

---

## 9.2 Enhance 允许加载资产

Enhance 可加载：

```text
Base 全部资产
+ research.md
+ claude-next.md
+ error-dna.json
+ oracle_engine.py
+ opencode_observer.py
+ low-frequency Oracle
+ context watermark
```

但必须满足：

```text
1. Oracle 低频。
2. error-dna 三闸门。
3. claude-next 只在 Archive。
4. research 只在 Plan。
5. AGENTS.md 不自动改。
6. Hook 输出总量 ≤1500 token。
```

---

# 10. 最终裁决

```text
data.md 当前资产有价值，但资产数量已经超过 CarrorOS vNext 的治理承载能力。
重构方向不是继续增加 skill/hook，而是把高 ROI 资产收束到 Base / Enhance 二元法。
```

最终保留：

```text
lx-varlock
lx-todo
lx-validate-skill
update-carror-os
VerifyGate
PreActionGate
ContextHandoff
FallbackProtocol
ArchiveTombstone
AuditJsonl
omc_lint
bench
低频 Oracle
受限飞轮
展示型 Statusline
```

最终删除或降级：

```text
常驻 PostToolUse
常驻 Oracle
常规 Meta-Oracle
Base 飞轮
Base research
Base claude-next
Base error-dna
无来源 watermark
acceptance 完成门
handoff 新状态
自动改 AGENTS
statusline evidence
```

最终一句话：

```text
CarrorOS 的高 ROI 资产不是“更多 Hook”，而是更少入口、更硬验证、更短输出、更强安全边界，以及能用 bench 证明有效的机制。
```


更新：

收到，这个更新是正确的，而且应该作为新的资产归属红线冻结。

之前我把部分可复用脚本、skill、hook、kernel/index、bench 等放在 `.omc` 下，这会混淆“系统可复用资产”和“单次任务运行时状态”。现在应统一改成：

```text
.claude/ = 可复用资产层
.omc/    = 运行时实例层
```

## 更新后的目录裁决

```text
.claude/
  skills/
    lx-varlock/
    lx-todo/
    lx-validate-skill/
    update-carror-os/

  hooks/
    pre-action/
    verify-gate/
    context-handoff/
    fallback/
    archive/
    statusline/
    redaction/
    skill-lint/

  scripts/
    carros_base.py
    omc_lint.py
    varlock.py
    statusline_renderer.py
    oracle_engine.py          # Enhance reusable
    opencode_observer.py      # Enhance reusable

  docs/
    AGENTS.md
    kernel.md
    index.md
    hook-registry.md
    skill-registry.md

  bench/
    dataset.json
    tasks/
    scoring.md
    runner.md
```

```text
.omc/
  config/
    base.json
    enhance.json

  state/
    token.json
    counter.json
    session-handoff.md
    last-user-prompts.jsonl
    rule-suggestions.md

  docs/
    plan.md
    executor.md
    research.md               # Enhance runtime doc
    claude-next.md            # Enhance runtime learning output
    error-dna.json            # Enhance runtime learning output
    oracle-verdicts.md

  audit/
    YYYYMMDD.jsonl
    index.json

  archive/
    {task_id}/
      final-report.md
      token.final.json
      token.tombstone.json
      plan.md
      executor.md
      session-handoff.md
      audit-manifest.json
```

## 归属规则

### `.claude/` 放可复用资产

放这里的东西必须满足：

```text
1. 跨任务复用。
2. 不代表当前任务状态。
3. 可以被多个项目或多次运行共享。
4. 修改需要更高审慎度。
5. 不得存储当前任务完成度。
```

因此以下资产应归 `.claude/`：

```text
Skills
Hooks
通用脚本
通用 lint 规则
通用 benchmark 数据集
AGENTS.md
kernel.md
index.md
hook registry
skill registry
Oracle prompt / protocol
Statusline renderer
Varlock 工具
```

### `.omc/` 放运行时资产

放这里的东西必须满足：

```text
1. 属于当前项目 / 当前任务实例。
2. 会随着任务执行变化。
3. 是状态、证据、审计、归档的一部分。
4. 可被 Archive 封存。
```

因此以下资产应归 `.omc/`：

```text
token.json
counter.json
plan.md
executor.md
session-handoff.md
last-user-prompts.jsonl
research.md
claude-next.md
error-dna.json
oracle-verdicts.md
audit jsonl
archive final-report
tombstone
```

## 对前一版 ROI 集合的修正

### KEEP_CORE 更新

```text
KEEP_CORE = {
  ".claude/skills/lx-varlock",
  ".claude/skills/lx-todo",
  ".claude/skills/lx-validate-skill",
  ".claude/skills/update-carror-os",

  ".claude/hooks/pre-action",
  ".claude/hooks/verify-gate",
  ".claude/hooks/context-handoff",
  ".claude/hooks/fallback",
  ".claude/hooks/archive",
  ".claude/hooks/statusline",
  ".claude/hooks/redaction",

  ".claude/scripts/carros_base.py",
  ".claude/scripts/omc_lint.py",
  ".claude/scripts/varlock.py",

  ".claude/bench"
}
```

### KEEP_LIMITED 更新

```text
KEEP_LIMITED = {
  ".omc/docs/research.md": "Enhance Plan-only runtime artifact",
  ".omc/docs/claude-next.md": "Enhance Archive-only runtime learning output",
  ".omc/docs/error-dna.json": "Enhance Archive-only runtime learning output + 三闸门",
  ".claude/scripts/oracle_engine.py": "Enhance low-frequency reusable protocol/tool",
  ".claude/scripts/opencode_observer.py": "Enhance-only reusable observer",
  ".claude/hooks/statusline": "display-only",
  ".claude/docs/kernel.md": "SessionStart reusable read-only policy",
  ".claude/docs/index.md": "SessionStart reusable registry"
}
```

### DELETE 规则更新

继续删除这些模式，不因目录变化而恢复：

```text
DELETE = {
  "Base PostToolUse always-on",
  "Enhance PostToolUse always-on",
  "Oracle always-on",
  "Meta-Oracle regular entry",
  "acceptance.md as completion gate",
  "statusline as evidence",
  "handoff new-state definitions",
  "unsourced watermark percentage",
  "auto AGENTS.md modification",
  "user_continue_as_confirmation",
  ".omc 中存放可复用 skill/hook",
  ".claude 中存放当前任务 token/plan/executor/audit"
}
```

## 关键修正点

`kernel.md` 和 `index.md` 不应再放 `.omc/docs/`。

旧归属：

```text
.omc/docs/kernel.md
.omc/docs/index.md
```

新归属：

```text
.claude/kernel.md
.claude/index.md
```

原因：

```text
kernel.md / index.md 是跨任务复用的治理入口，不是当前任务运行产物。
```

但 `research.md / claude-next.md / error-dna.json` 仍放 `.omc/docs/`，因为它们是当前任务运行期间产生或演化的材料，需要被 Archive 封存。

## 最终红线

```text
.claude 不存运行状态。
.omc 不存可复用资产。
```

更具体地说：

```text
.claude 可以被复制到新项目。
.omc 应该随任务生命周期创建、更新、归档、清理。
```

这条边界比单纯按 `config/scripts/state/docs` 分层更清楚，也更符合 CarrorOS vNext 的瘦身方向。