---
name: lx-goal
version: v1.5.0-enhance
description: "目标模式(Enhance版) — grill-me式澄清 → TDD优先执行 → 退出报告 + 知识采集。高阶模型专用，无spec模板限制"
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

### Phase 0：grill-me 式前置澄清

> HARD-GATE: Phase 0 未完成并获用户确认前，不得进入 Phase 1 执行。

**Enhance 模式** — 无 spec 模板限制，grill-me 式自由对话调研。

1. **先探索，再提问** — 读项目文件/文档/commits，能自答不问用户
2. **一次一个问题** — 不堆叠，逐分支推进决策树
3. **判断任务复杂度**（影响后续流程）：
   - **简单**：单文件改动/配置修改/纯文档 → 跳过方案对比
   - **复杂**：跨文件重构/架构变更/新增功能 → 强制 2-3 方案对比
   - **判定标准**：
     - 定量：3+ 文件修改 → 自动复杂
     - 定性（覆盖定量）：DB schema / 认证逻辑 / API 契约 / 安全敏感路径 → 任意修改都算复杂
4. 一次性扫描：边界/依赖/风险/验收/过期
5. 输出执行计划（子任务 + AC + 依赖 + 风险）
6. **自审计划** — 检查占位符/矛盾/模糊项

> HARD-GATE 不跳过（Base 一样）。但 Enhance 不需 spec 模板格式，对话式记录即可。

### Phase 1→N：TDD 优先的全自动执行

**执行期唯一规则源 = `references/autonomous-execution.md`**(§Phase 1→N 全自动执行 / §卡点分类处理矩阵 / §危险操作裁决链）。goal 模式下 `.claude/nodes/behavior_rules.md` 与 `.claude/nodes/execute_node.md` 中的交互式条款（用户裁定/澄清/确认/批准/每步确认）**全部不适用**；仅非交互条款（自洽检查/防编造/证据门禁/失败留痕）继续生效。降级触发参考 execute_node §降级触发条件，但其「用户确认新方案」由决策链自主裁决替代（见该文件 goal 模式覆盖节）。

| 铁律 | 含义 |
|------|------|
| **不暂停** | 不等待人类输入 |
| **不提问** | 歧义按决策框架判断 |
| **不中断** | 卡点处理后继续 |
| **只记录** | 风险和阻断写入 skipped_risks |

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

### 退出前验证（TDD 双模式）

> 进入退出报告前必须完成验证。未验证 = 软完成语违规。

**Step V: TDD 优先验收确认**
1. `git status --short` — 确认文件变更与预期一致
2. 跑项目测试 — **必须有实际输出证据**
3. TDD 判定：
   - **改动了测试文件** → TDD 强制，不可降级
   - **架构/安全变更**（DB schema / auth / API / 安全路径）→ TDD 强制（即使没改测试）
   - 其他情况 → TDD 优先，Base check-list 降级
4. 逐项核对 plan.md 中的所有 AC
5. 自审：调试代码/硬编码/边界 case
6. 📥 知识采集：记录本次执行的决策要点 + 新学到的项目知识 → 写入 `.claude-next.md`

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
2. 恢复：读 `.omc/plans/{date}/{slug}/` — research.md / plan.md / executor.md
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
