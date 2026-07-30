---
name: lx-goal
version: v1.5.0
description: "目标模式 — 一次前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。入口：`/lx-goal` 或 `/executor`"
when_to_use: "Use when user says 'goal mode', 'lx-goal', '无人值守', '自主执行', `/lx-goal`, `/executor`, or auto-detects a well-defined L2+ task with clear AC"
argument-hint: "[目标描述] [过期小时=6]"
harness_version: ">=6.3.0"
status: stable
role: "Goal-driven autonomous execution — single briefing, zero interruptions, final report"
execution_mode: stepwise
triggers: ["/lx-goal", "/executor"]
auto_detect: "Clear goals with defined ACs, 'do X for me' requests, well-specified tasks"
nodes:
  - behavior_rules          # 铁律#7(文档优先)#8(哲学先行)+自洽检查
  - interactive_prompt      # Phase 0 引导式问答
  - execute_node            # 全自动执行(降级触发+3轮上限)
  - a_terminal              # AC 验收方案生成
  - b_terminal              # 验收执行
schemas:
  - atomic/verdict          # 退出报告最终判定
---
# lx-goal — 目标驱动自主执行

**一般前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。**

本质：人类回答所有问题后离开，AI 不再请求交互。卡点按决策链处理，硬边界跳过记录。

**⚠️ 文档强约束**：每执行一步前，必须先更新 progress.md + 写 evidence，再执行。跳过文档直接执行=违反哲学 #7（文档优先）。

## 一句话定位

目标是**已知**的结果。Ghost 是**方向**未知的探索。用户说"帮我做 X" → Goal。用户说"帮我看看 Y 有没有问题" → Ghost。

## 3 步流程

```
Phase 0. 一次问清（人类窗口期） → AI 激活 → Phase 1→N. 全自动执行 → 退出报告
```

### Phase 0：前置澄清

> **HARD-GATE**: Phase 0 未完成并获用户确认前，不得进入 Phase 1 执行。再简单的任务也不跳过。

**🔴 EnterPlanMode 反劫持规则** — 当用户命令同时包含 `/lx-goal`（或 goal/gost 关键词）和 "plan模式"/"plan mode"/"先规划"/"先做plan" 等词汇时，Phase 0 **本身就是 plan 阶段**（探索→澄清→输出执行计划）。**严禁**调用 EnterPlanMode 工具——那会跳过 Phase 0 的人类澄清窗口，直接进入只读等待态。正确行为：直接在 lx-goal Phase 0 协议内探索+输出计划，不调用额外 plan 工具。判断依据：SKILL.md 已加载 = `/lx-goal` 已触发，"plan" 指的是 Phase 0 而非 CC 内置 plan mode。

1. **🔴 先探索，再提问** — 硬规则。先读项目文件、文档、近期 commits，能自答的问题不问用户
2. **🔴 一次一个问题** — 硬规则。不堆叠，逐分支推进决策树。违反=重新 Phase 0
3. **判断任务规模** — 含多个独立子系统 → 先拆解为子项目，逐个进入 Phase 0
4. 一次性扫描所有不确定项：范围边界、硬边界预检、外部依赖、能力缺口、风险点、执行顺序、验收条件、过期策略
5. 对非平凡任务 → **🟡 建议提出 2-3 种方案**（带权衡 + 你的推荐理由）
6. 输出执行计划（子任务列表 + AC + 依赖 + 风险 + Q 项）
7. **🔴 自审计划** — 硬规则。检查执行计划是否有占位符、矛盾、模糊项，修正后再提交。不自审=违反铁律#2
8. 人类确认后激活：`python3 .claude/skills/lx-goal/scripts/lx-goal.py on "{目标描述}"`
    - 激活时 lx-goal.py 委托 **carros_base.py init --task-mode goal** 创建任务文档目录 + 结构化模板
    - carros_base.py 负责 research/plan/executor 模板生成，不再由 lx-goal.py 自建骨架
9. **🔴 绑定 plan_dir** — 激活后必须调用 `lx-goal.py assert-plan-dir` 获取 carros_base 创建的 unique plan_dir 路径并 `cd` 到该目录。**禁止自行 mkdir、猜测或创建新目录作为 plan_dir**。后续所有文档 I/O（research/plan/executor）必须锁定此路径。
10. **🔴 填写 research.md** — 硬规则。必须填写 research.md 的所有 8 个 section（背景/约束/已知信息/不确定性/全貌/依赖树/方案/Dependency TDD），每个 section 至少 1 行非占位内容。依赖树必须至少 1 条。
11. **🔴 Phase 0 门禁** — 硬规则。填写完成后必须调用 `lx-goal.py phase0-done`，触发 ResearchGate 验证 + GoalMachine 状态转换。验证失败会阻断进入 Phase 1。**不调用此命令 = 跳过 Phase 0 = 违反铁律**。
12. 验证激活标志存在：`ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active`

> ⚠️ Anti-Pattern: "这任务太简单不需要澄清" — 简单的任务恰恰是未检视假设导致最多返工的地方。澄清可以短（几句话），但不能跳过。

### Phase 1→N：全自动执行

**执行期唯一规则源 = `references/autonomous-execution.md`**(§Phase 1→N 全自动执行 / §卡点分类处理矩阵 / §危险操作裁决链）。goal 模式下 `.claude/nodes/behavior_rules.md` 与 `.claude/nodes/execute_node.md` 中的交互式条款（用户裁定/澄清/确认/批准/每步确认）**全部不适用**；仅非交互条款（自洽检查/防编造/证据门禁/失败留痕）继续生效。降级触发参考 execute_node §降级触发条件，但其「用户确认新方案」由决策链自主裁决替代（见该文件 goal 模式覆盖节）。

| 铁律 | 含义 |
|------|------|
| **不暂停** | 不等待人类输入 |
| **不提问** | 歧义按决策框架判断 |
| **不中断** | 卡点处理后继续 |
| **只记录** | 风险和阻断写入 skipped_risks |
| **只锚定** | 调用 `assert-plan-dir` 绑定 plan_dir，禁止另建目录 [已验证: SKILL.md §Phase 0 step 9](/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/skills/lx-goal/SKILL.md) |

**卡点处理**：

| 类型 | 处理 |
|------|------|
| 硬边界（rm/git写/密钥/API Key） | 立即跳过 → `lx-goal hard-boundary-hit` 记录 → 继续 |
| **中高风险项（medium+）** | **只跳过不执行** → `lx-goal skip-risk "描述" <level> "理由" "影响"` → 自动进入退出报告「需人为决策汇总」反馈人工干预 |
| 可跳过（有替代路径） | `lx-goal skip-risk` 记录，继续 |
| 可绕行（换方案可达目标） | 自动降级备选方案 |
| 危险操作（远程推送/破坏性） | 三级裁决链（AGENTS → Oracle → 记录 blocked_human） |
| 真阻断/需人类 | 记录 blocked/blocked_human，继续其他 |

> 中高风险安全阀：`skip-risk` 第二参数为 risk_level（low/medium/high/critical）。medium 及以上级别**禁止执行只许跳过**，退出报告强制聚合成表反馈人类；low 级记录后可继续。

**progress 更新**：
```bash
lx-goal task-done "完成了什么"
lx-goal skip-risk "跳过了什么"
lx-goal hard-boundary-hit "操作X被跳过" "原因Y" "建议人类执行Z"
lx-goal blocked-human "决策X" "AI推荐Y" "依据Z"
```

### 退出前验证

> 进入退出报告前必须完成以下验证。未验证 = 软完成语违规。

**Step V: 验收确认**
1. `git status --short` — 确认文件变更与预期一致
2. 跑项目测试命令（`go test ./...` / `npm test` / `pytest`）— **必须有实际输出证据**
3. 逐项核对 plan.md 中的所有 AC — 每一项标注 ✅ 通过 / ❌ 未通过 / ⚠️ 跳过
4. 自审：有无调试代码、硬编码值、未处理的边界 case
5. 输出验证摘要：

```
🧪 lx-goal 退出前验证
变更文件: {N} 文件
测试结果: ✅ {N} passed / ❌ {N} failed
AC 完成度: {N}/{M}（{N} 项通过）
自审: ✅ 无遗留 / ⚠️ {N} 项需注意
```

**验证未通过 → 不生成退出报告，返回 Phase 1→N 修复问题。**

```bash
lx-goal report   # 生成执行报告（含 verdict schema）
lx-goal off      # 关闭模式 + 清理信号文件
```

报告结构：执行摘要 → 已完成任务 → 跳过风险 → ⚠️ 需人类介入项 → 推迟决策项 → 附带发现

## 物理锁约束

`.omc/tokens/{date}/{task_slug}_token.json`

- 创建时机：`lx-goal on` 成功时自动创建
- 存在含义：任务正在执行，AI 不可说"完成了"
- 删除时机：`lx-goal done` 任务真实验收通过后删除

## SubAgent 调度记录

```bash
lx-goal subagent-log assign "<agent_name>" "<subtask描述>"
lx-goal subagent-log complete "<agent_name>" "<subtask>" "<结果摘要>"
lx-goal subagent-log fail "<agent_name>" "<subtask>" "<失败原因>"
lx-goal subagent-log summary
```

**异常接管**：SubAgent 超时/stalled/failed 时，引用 `@references/autonomous-execution.md §SubAgent异常接管机制` 自动处理，永不等待用户。

## 跨会话续跑

1. 检测：`.omc/state/tokens/lx-goal.json` 存在则读 goal + expires_at
2. 恢复：读 `.omc/tasks/{date}/{slug}/` — research.md / plan.md / executor.md
3. 继续：检测 token 中最后未完成（status != done）的 step，从该 step 继续。若所有 step 均 done 则跳至退出报告。不需要重新 Phase 0。
4. 关闭：`lx-goal done` 删锁 → `lx-goal off`

## 子任务引擎路由

| 特征 | → 引擎 |
|:-----|:------|
| ≥3 同构独立子任务 | **原生并行 Task 调用**（一条消息内多个 Agent 并发执行） |
| 有依赖链/异构/跨模块/根因不明 | **串行 direct + lx-stepwise**（按依赖顺序执行+证据） |
| 单文件小改 | **direct**（无模式，直接执行+证据） |

## 硬边界

遇到硬边界 → 立即跳过 → 记录 → 继续。不裁决、不绕过、不尝试任何 workaround。

## 自主权范围

文件创建/修改（非治理）、代码重构、架构决策、子 Agent 调度、依赖安装（sudo 需 skip-risk）、测试运行、Git 只读操作——**完全自主，不询问**。
