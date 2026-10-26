---
name: lx-goal
version: v1.7.0
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
  - behavior_rules          # 铁律（文档约束）+#1（哲学先行）+自洽检查
  - interactive_prompt      # Phase 0 引导式问答
  - execute_node            # 全自动执行(降级触发+3轮上限)
  - a_terminal              # AC 验收方案生成
  - b_terminal              # 验收执行
schemas:
  - atomic/verdict          # 退出报告最终判定
---
# lx-goal — 目标驱动自主执行

## 定位与分级（index49）

**无人值守路径**——下命令后 AI 自主完成，不暂停、不提问、不中断。
与 `lx-rpe` 的区别：RPE 是**人机协作**（每步人审），goal 是**无人**。两者不要混用。

### 🔴 分级由 AI 判，**不要让人记参数**（人类裁决 2026-09-10）

人类只说目标，**不需要**知道或指定 L1/L2。AI 在 Phase 0 按「难度 / 危险系数 / 工程量」三轴自判：

| 判为 | 条件（满足任一即 L2） |
|---|---|
| **L2 完备** | 跨模块 / 不可逆 / 触及安全·权限·架构 / 工程量显著（>3 文件或多步依赖链） |
| **L1 简易** | 上述皆不满足：范围清楚、单模块、可逆、改动小 |

**判不准 → 问人类选路线**（Phase 0 本就是人类窗口，用 `AskUserQuestion` 给 A/B 两条路线 + 推荐项）。
**不要猜**，也不要因为省事而默认走完备模式。

判定后由 AI 把结果传进激活命令：`on "<目标>" --level L1|L2`。
`--level` 是 **AI 内部参数**，不是给人准备的开关——人类从不手写它。

| 级别 | 流程 |
|---|---|
| **L1 简易** | 只做必要项：research → plan → 执行 → verify → 归档 |
| **L2 完备** | 简易项 **+** worktree 隔离 **+** 依赖树 **+** 前置/后置 TDD 门 **+**（可选）双法官验收 |

**完备模式（L2）的硬性链条**：

1. 进入执行态前自动建 **worktree 隔离**（`plan-done` 时；worktree 内 `.omc` 链接回主树，账本不随 worktree 删除而丢失）
2. **前置 TDD 门**（进入执行态前）：依赖树 TDD **全绿** + 特性 TDD **全红**（红=测试确实在测未实现行为）
3. 执行
4. **后置 TDD 门**：依赖树与特性 TDD **均全绿**（`done` 自动校验，不可跳过）
5. **双法官验收（可选）**：高风险任务建议跑 `accept`；简单任务不必
6. 归档时自动合回发起分支并清理 worktree（`accept` 跑过就由它合回）

plan.md 须声明两条判据命令：`- dep_tdd_cmd: <命令>` 与 `- feature_tdd_cmd: <命令>`。

**隔离强制执行**：隔离执行期间，`worktree-scope` 门禁会拦下**主树**的代码写入并指向 worktree 内等价路径
（只有 `.omc/` 账本目录按设计共享主树）。即「在 worktree 下干活」由机制保证，不靠自觉。

**哲学约束（人类强调）**：符合「the less, the more」——改动必须**必要且最小范围**；
不为完备而完备，L1 能解决的就不要上 L2。

**一般前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。**

本质：人类回答所有问题后离开，AI 不再请求交互。卡点按决策链处理，硬边界跳过记录。

**⚠️ 文档强约束**：每执行一步前，必须先更新 progress.md + 写 evidence，再执行。跳过文档直接执行=违反哲学 #5（文档优先）。

## 一句话定位

目标是**已知**的结果。Ghost 是**方向**未知的探索。用户说"帮我做 X" → Goal。用户说"帮我看看 Y 有没有问题" → Ghost。

## 3 步流程

```
Phase 0. 一次问清（人类窗口期） → AI 激活 → Phase 1→N. 全自动执行 → 退出报告
```

**每一步都提前告知，不靠事后报错**：每个生命周期命令结束时都会打印「下一步入参契约」
（下一步要准备哪些文件/字段/命令）。照它准备再执行；门禁只做兜底，不作为发现问题的第一手段。

### Phase 0：前置澄清

> **HARD-GATE**: Phase 0 未完成并获用户确认前，不得进入 Phase 1 执行。再简单的任务也不跳过。

**🔴 EnterPlanMode 反劫持规则** — 当用户命令同时包含 `/lx-goal`（或 goal/gost 关键词）和 "plan模式"/"plan mode"/"先规划"/"先做plan" 等词汇时，Phase 0 **本身就是 plan 阶段**（探索→澄清→输出执行计划）。**严禁**调用 EnterPlanMode 工具——那会跳过 Phase 0 的人类澄清窗口，直接进入只读等待态。正确行为：直接在 lx-goal Phase 0 协议内探索+输出计划，不调用额外 plan 工具。判断依据：SKILL.md 已加载 = `/lx-goal` 已触发，"plan" 指的是 Phase 0 而非 CC 内置 plan mode。

1. **🔴 先探索，再提问** — 硬规则。先读项目文件、文档、近期 commits，能自答的问题不问用户
1b. **🔴 分级判定（AI 自决；判不准才问人类）** — 按「难度 / 危险系数 / 工程量」三轴判定走 L1 简易还是 L2 完备（判据见本文件「定位与分级」表）。
    - **能自判就自判**，并在计划里写明判据；**不要把 `--level` 抛给人类记**——人类只说目标。
    - **判不准时**用一张澄清卡给 A/B 两条路线 + 你的推荐项，让人类选。
    - 激活时把结果写进命令：`on "<目标>" --level L1|L2`。
2. **🔴 一次一个问题** — 硬规则。每张澄清卡只能包含一个待决策问题，不堆叠、不预列后续问题
3. **🔴 卡片循环直到收敛** — 用户回答当前卡后，重新扫描剩余不确定项并生成下一张卡；只有确认没有新的用户决策项时，才能进入计划确认
4. **判断任务规模** — 含多个独立子系统 → 先拆解为子项目，逐个进入 Phase 0
5. 每轮只扫描当前可决策项：范围边界、硬边界预检、外部依赖、能力缺口、风险点、执行顺序、验收条件、过期策略
6. 对非平凡任务 → **🟡 建议提出 2-3 种方案**（带权衡 + 你的推荐理由），但方案必须服务于当前这一张卡
7. 输出执行计划（子任务列表 + AC + 依赖 + 风险）；不得把尚未提问的 Q 项批量展示给用户
8. **🔴 自审计划** — 硬规则。检查占位符、矛盾、模糊项和遗漏的决策项，修正后再提交。不自审=违反铁律#2
8. 人类确认后激活：`python3 .claude/skills/lx-goal/scripts/lx-goal.py on "{目标描述}" --level L1|L2`
   （`--level` 用第 1b 步的判定结果；**由 AI 填，不询问人类**）
    - 激活时 lx-goal.py 委托 **carros_base.py init --task-mode goal** 创建任务文档目录 + 结构化模板
    - carros_base.py 负责 research/plan/executor 模板生成，不再由 lx-goal.py 自建骨架
9. **绑定 task_dir** — 激活后记录 carros_base 输出的绝对 task_dir，后续命令显式传 `--task-dir <path>`。不扫描、不猜测其它任务；plan 可在任务范围内合理变更并记录原因。
10. **🔴 工具读写协议** — 修改现有文件前，必须先对同一绝对路径调用 `Read`；粘贴内容、旧会话记录或 read-tracker 记录都不能替代这次真实 Read。若工具返回 `File must be read first`，停止重试，先 Read 再进行唯一一次修改。
11. **🔴 先 research 后 plan** — 激活只创建三个空骨架；先填写 research.md 的 8 个 section（背景/约束/已知信息/不确定性/全貌/依赖树/方案/Dependency TDD），每个 section 至少 1 行非占位内容，依赖树至少 1 条；然后只调用 `lx-goal.py phase0-done` 进入 PLANNING。
11b. **🔴 路径契约同步（AI 生成白名单）** — research 阶段把任务声明的输入/输出路径写入 `{task_dir}/working-set.yaml` 的 `allowed_paths`（支持绝对路径声明，如 `/Users/xx/Desktop/daily_tasks/`；仓库外路径也应声明，避免路径契约误拦）。让 working-set 反映任务真实接触面。若任务不涉及任务外文件，本步可跳过。
12. **🔴 PlanGate 门禁** — 仅在 PLANNING 状态填写并审查 plan.md；完成后调用 `lx-goal.py plan-done`，ResearchGate + PlanGate 通过后才进入 EXECUTING。未通过不得 tick、subagent-log 或填充 executor.md。
13. 验证任务绑定存在：`lx-goal.py status --task-dir <task_dir>`；不扫描其它任务。

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
lx-goal accept   # 可选：双法官验收（高风险任务建议跑）
lx-goal done     # 校验 checklist/verdict → L2 跑后置 TDD → 合回 worktree → 归档 → 删锁
```

`off` 是另一条关闭路径（只做 checklist + 报告，不推进 GoalMachine 到 ARCHIVED）；
正式闭环一律走 `done`，不要混用。

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

1. compact 后消费一次性 resume-note，取得 `task_dir` 与 token 指针
2. 恢复：读取该 `.omc/tasks/{date}/{slug}/` — research.md / plan.md / executor.md / checklist
3. 继续：用该 task_dir 定位 `.omc/tokens/{date}/{slug}.json`，不扫描其它 active token
4. 关闭：`lx-goal done --task-dir <path>` 或 `lx-goal off --task-dir <path>`，保留 token、删除 sidecar lock

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
