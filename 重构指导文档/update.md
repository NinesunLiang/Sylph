# 第三轮重构方案更新评价

## 总裁决

**裁决等级：附条件核准，但必须瘦身。**

结合最新知识后，第三轮方案的主方向仍然正确，但推荐做一次明确的“减法更新”。

第三轮已经把 CarrorOS 从提示词治理推进到了文件状态机治理：

```text
Intake → Plan → PreAction → Execute → Verify → Context → Oracle → Fallback → CLI → Archive
```

这条链路完整，但现在的问题不是“不够强”，而是：

```text
对 Base 来说太重。
对 Enhance 来说 Oracle 频率偏高。
对落地来说验证基准不足。
```

最新知识给出的方向非常清楚：

```text
Base:
  用状态系统增强模型，而不是用审判系统约束模型。

Enhance:
  用学习飞轮增强模型，而不是用 hook 数量堆安全感。
```

所以，第三轮应更新为：

```text
L1 / Base Workflow:
  负责把任务稳定做完。

L2 / Enhance Workflow:
  负责把复杂任务做对，并让系统变聪明。
```

不要继续扩展新层级、新 Gate、新 Oracle 规则。  
下一步不是继续写文档，是拿真实模型跑验证基准。

---

## 1. 最大更新：从 10 模块改成 2 层 4 核心

第三轮原链路是：

```text
IntakeGate
→ PlanBuilder
→ PreActionGate
→ Executor Evidence Ledger
→ VerifyGate
→ Context Engine
→ Oracle / Meta-Oracle
→ Fallback Protocol
→ CLI Integration
→ Archive Engine
```

这个作为内部设计可以保留，但不应作为模型和用户的主要认知入口。

推荐更新为：

```text
L1 / Base:
  Plan → Step → Verify → Archive

L2 / Enhance:
  Base + Context Watermark + Low-frequency Oracle + Learning Flywheel
```

也就是：

```text
Base 只暴露 4 个核心动作：
1. plan
2. step
3. verify
4. archive
```

其他模块降级为内部机制：

```text
PreActionGate     → step 前的轻量检查
Executor Ledger   → step 执行记录格式
Context Engine    → 内部状态同步
Fallback Protocol → 内部异常裁决
CLI Integration   → 展示和路由
```

这样更简单，也更符合最新知识里的二元法：

```text
默认 L1；
遇到跨系统、不可逆、安全权限、发布、长期无人或用户指定高可靠，升级 L2。
```

---

## 2. Base 推荐更新：砍掉重审判，保留状态闭环

第三轮 Base 原本包含：

```text
context_engine.py
verify_gate.py
fallback_engine.py
statusline_renderer.py
archive_engine.py
```

这仍然偏重。

更推荐的 Base 核心资产是：

```text
token.json
plan.md
executor.md
session-handoff.md
last-user-prompts.jsonl
counter
```

Base 的目标不是“审判模型”，而是减少遗忘、漂移、假完成。

推荐 Base 最小文件集：

```text
.omc/
  state/
    token.json
    session-handoff.md
    last-user-prompts.jsonl
  docs/
    plan.md
    executor.md
  audit/
    YYYYMMDD.jsonl
  bin/
    carros_base.py
```

Base 不需要拆出一堆脚本。  
更简单的做法是合并成一个标准库 Python 文件：

```text
carros_base.py
  init
  status
  tick
  verify
  archive
  lint
```

推荐 Base 规则：

```text
1. 默认 L1。
2. 不跑 Oracle。
3. 不跑 Multi-Judge。
4. 不跑复杂水位判断。
5. compact 用 15/20 轮。
6. 每 5 轮注入一次状态摘要。
7. VerifyGate 只做静态证据校验。
8. 高风险任务直接升级 L2 或 ASK_USER。
```

这样比第三轮的多脚本 Base 更稳。

---

## 3. Enhance 推荐更新：Oracle 降频，飞轮增值

第三轮的 Oracle / Meta-Oracle 很完整，但最新知识明确提醒：

```text
不要追求双法官的绝对正确。
同源盲区是 LLM 审 LLM 的天花板。
再投入边际收益递减。
```

所以 Oracle 不应该高频运行。

推荐更新：

```text
Oracle 只保留低频关键点：
1. L2 任务启动时的 levelgate
2. 高风险 step 前
3. phase_end
4. final_acceptance
5. 连续失败 3 次后
```

删除或降级：

```text
- 普通 step 后 Oracle
- 低风险 phase_end Oracle
- 多层 Meta-Oracle 常规投票
- 复杂 L2/L3 评分在 Base 中的模拟
```

更推荐的 Enhance 核心资产是：

```text
Base
+ research.md
+ claude-next.md
+ error-dna.json
+ low-frequency Oracle
+ context watermark
```

其中：

```text
research.md:
  事实层，只写任务内技术决策和架构边界。

claude-next.md:
  经验层，只写高价值用户纠正和模式性失误。

error-dna.json:
  失败模式层，只写可复用的系统性错误。
```

这比“Oracle 频繁审判”更有长期价值。

---

## 4. Context Engine 推荐更新：三段式水位更简单

第三轮使用：

```text
Base:
  15/20 轮 compact

Enhance:
  70%/85% watermark
  每 5 轮 State Injection
```

最新知识建议更具体的三段式水位管理：

```text
0-40%:
  正常执行

40-70%:
  停止加载新 reference 文档
  工具输出截断从 2000 chars 降到 1000 chars
  每个 step 结束同步写 executor.md

70%+:
  当前 step 完成后停止
  写完整 session-handoff.md
  建议 /compact
  不启动新 step
```

推荐用这个替代第三轮较粗的 70/85 二段式。

同时保留 Base 简单规则：

```text
Base:
  soft_turn = 15
  hard_turn = 20
```

并增加一个重要降级规则：

```text
mtime 检测失败:
  跳过缓存，重新读取。
  不因 mtime 异常阻断执行。
```

这比把 Context Engine 做成复杂状态图更实用。

---

## 5. Prompt / 文档入口推荐更新：三门户压缩

最新知识提出更清晰的文档入口：

```text
AGENTS.md  → 核心信息
kernel.md  → 飞轮机制 + 冻结机制
index.md   → hooks / references 注册表
```

推荐第三轮把治理说明压入这个结构，而不是让模型长期读完整方案。

### AGENTS.md

目标：

```text
≤ 2000 token
```

只保留：

```text
1. 哲学 7 条压缩版
2. 铁律 6 条
3. L1 / L2 路由规则
4. 工作流入口
```

哲学推荐压成：

```markdown
## 哲学体系
优先级：验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少

- 验证：没通过验证 = 没做
- 零信任：断言必须有证据
- 守护：危险操作须审批
- 文档：磁盘比 context 可靠
- 人本：战略权留人类
- 增益：能简单绝不复杂
- 少：只在必要时做
```

### kernel.md

目标：

```text
≤ 500 token
```

只保留：

```text
1. AI 不可自改 AGENTS.md
2. 飞轮入口
3. 冻结规则
```

### index.md

保留渐进披露：

```text
when_to_use → reference path
```

这个结构更简单，符合“正确的信息在正确时间出现”。

---

## 6. Fallback 推荐更新：保留矩阵，但入口隐藏

第三轮 Fallback Protocol 设计正确，不建议删除。

但推荐更新为：

```text
Fallback 不作为用户主入口。
Fallback 是内部裁决器。
```

也就是说，用户和模型只看到：

```text
status:
  running / awaiting_user / blocked / archived
```

内部再映射：

```text
context_watermark_unobservable → DOWNGRADE_TO_BASE
oracle_unavailable + high → BLOCKED
verify_not_completed → BLOCKED
authorization_missing → ASK_USER
```

推荐保留这条硬规则：

```text
能降级的是能力缺失。
不能降级的是证据缺失、安全缺失、状态冲突、授权缺失。
```

这是第三轮最好的规则之一，必须保留。

---

## 7. Archive 推荐更新：保留，但并入 Base 核心命令

第三轮 Archive Engine 很完整，方向正确。

但实现上建议不要单独暴露复杂 Archive 模块，而是作为：

```bash
carros_base.py archive
```

Archive 仍保留硬条件：

```text
1. 所有 plan step 已 [x]
2. 所有 step 有 VerifyGate VERIFIED
3. token done/total 与 plan 一致
4. executor.md 有 evidence
5. audit 可解析
6. Enhance final_acceptance 有 Oracle ACCEPT/WARN
```

推荐新增：

```text
archive 前强制运行 lint。
```

即：

```text
archive = lint + verify-summary + final-report + tombstone
```

这比第三轮直接 archive 更稳。

---

## 8. 必须新增：验证基准，而不是更多文档

最新知识给出的最高优先级是：

```text
验证基准。
```

这是第三轮最缺的部分。

推荐新增 `bench/`：

```text
bench/
  01_doc_update/
  02_single_file_fix/
  03_multi_file_test/
  04_failure_then_repair/
  05_compact_resume/
  06_fallback_downgrade/
  07_archive_close/
```

每个基准必须记录：

```text
goal
expected_files
expected_plan_steps
required_evidence
expected_final_status
```

评估指标只保留少量：

```text
1. task_completed
2. verify_passed
3. false_done_count
4. user_intervention_count
5. compact_resume_success
6. archive_success
```

裁决：

```text
没有基准，就不能继续声称方案更稳。
```

---

## 9. 必须新增：omc_lint.py

第三轮大量依赖 Markdown 和 JSON 文件，因此必须有统一 lint。

推荐 `omc_lint.py` 检查：

```text
1. token.json schema
2. plan.md step 格式
3. executor.md evidence block
4. audit jsonl 可解析
5. token done/total 与 plan 一致
6. VerifyGate audit 与 plan step 一致
7. archive readiness
```

这是比继续扩 Oracle 更高 ROI 的改进。

推荐执行时机：

```text
1. 每次 archive 前
2. compact 前
3. resume 后
4. fallback 后
5. 用户要求 status --strict 时
```

---

## 10. 推荐删除或降级的内容

### 10.1 删除作为主概念

```text
IntakeGate
PlanBuilder
PreActionGate
Executor Evidence Ledger
VerifyGate
Context Engine
Oracle / Meta-Oracle
Fallback Protocol
CLI Integration
Archive Engine
```

不是删除实现，而是不再作为用户主心智暴露。

主心智只保留：

```text
L1 Base:
  Plan → Step → Verify → Archive

L2 Enhance:
  Base + Flywheel + Oracle
```

---

### 10.2 删除或降级高频 Oracle

删除：

```text
普通 step 后 Oracle
低风险任务 Oracle
Base Oracle stub 的“高阶复核”称呼
```

保留：

```text
高风险点 Oracle
phase_end Oracle
final_acceptance Oracle
连续失败后 Oracle
```

---

### 10.3 不要再增加

```text
1. 不要再细分 L1.5 / L3 / L4。
2. 不要给 Base 加飞轮。
3. 不要再扩 Hook。
4. 不要追求双法官绝对正确。
5. 不要继续扩写治理文档替代真实验证。
```

---

## 11. 更新后的推荐最终形态

```text
CarrorOS vNext

L1 / Base Workflow
  目标：稳定完成中低风险任务
  入口：plan / step / verify / archive
  状态：token + plan + executor + handoff + audit
  compact：15/20 轮
  校验：static verify + omc_lint
  禁止：Oracle / Multi-Judge / 飞轮学习

L2 / Enhance Workflow
  目标：复杂任务做对，并沉淀经验
  组成：Base + research + claude-next + error-dna
  context：三段式水位 0-40 / 40-70 / 70+
  Oracle：低频关键点复核
  Fallback：高风险不可静默降级
  CLI：只展示，不做真相源
```

一句路由规则：

```text
默认 L1；
跨系统、不可逆、安全权限、发布、长期无人、用户指定高可靠 → L2。
```

---

## 12. 最终更新裁决

第三轮不是要推翻，而是要瘦身。

保留：

```text
1. VerifyGate 唯一完成硬门
2. token / plan / executor / handoff / audit 五源边界
3. Context compact/resume 机制
4. Fallback 不可用裁决
5. CLI 非真相源
6. Archive tombstone
```

更新：

```text
1. 10 模块主链路降级为内部实现。
2. 用户主心智改为 L1 / L2 二元法。
3. Base 合并为单文件轻量状态系统。
4. Enhance Oracle 降频。
5. Context 使用三段式水位。
6. AGENTS / kernel / index 三门户压缩。
7. 新增 omc_lint.py。
8. 新增 bench 验证基准。
```

最终裁决：

```text
第三轮方案：附条件核准，执行瘦身更新。
推荐方向：少设计，多验证。
下一步最高优先级：实现 Base 最小闭环 + omc_lint.py + 7 个基准任务。
```

最终一句话：

```text
CarrorOS 不需要更复杂的治理树。
CarrorOS 现在需要一个更小的 Base、一个低频但高价值的 Enhance，以及一套能证明它真的有效的验证基准。
```