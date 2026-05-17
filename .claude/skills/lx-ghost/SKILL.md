---
name: lx-ghost
version: v1.4.0
description: "幽灵模式 — 方向驱动的自主探索。Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告。人类离开后 AI 自主探索直到方向达成或最小迭代数满足。"
when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
model: sonnet
argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3] [最小迭代数=0]"
harness_version: ">=1.1.0"
status: stable
role: "Direction-driven autonomous exploration — Oracle-gated single briefing, zero interruptions"
execution_mode: stepwise
triggers:
  - "/lx-ghost"
---

# lx-ghost — 方向驱动自主探索

> **一次前置澄清 → 全自动探索 → 退出报告。人类在窗口期确认方向后离开，AI 自主探索直到过期或方向达成。**

## 与 lx-goal 的区别

| | lx-goal | lx-ghost |
|---|---------|----------|
| 驱动方式 | 目标驱动（具体任务列表） | 方向驱动（开放探索） |
| 执行模式 | 逐项 task-done | 增量 poll 迭代 |
| 适用场景 | 可分解的具体目标 | 需持续探索改进的方向 |
| 每步粒度 | 子任务级 | 单步操作级 |

## 自主决策框架

与 lx-goal 共享同一框架：Philosophy → Iron Rules → Existing Practices → AI 自主判断。

## 危险操作裁决链

**Level 1: AGENTS.md 裁决** → **Level 2: Oracle 第三方审核（留痕）** → **Level 3: 人类裁决（最后手段）**

---

## Phase 0: 前置澄清窗口（唯一的人类交互）

> **一次问清，永不回头。** 激活前必须穷尽所有不确定项。激活后 AI 不再提问，仅靠自主决策框架执行探索。

### Step 0.1: 方向自检

AI 检查方向适合性：
- "探索/扫描/修复/迭代" 等增量关键词 → ghost mode
- "分析/报告/评估/阅读" 等一次性关键词 → 建议 goal mode
- 区分不清 → 向人类说明理由，推荐模式

### Step 0.2: 扫描不确定项

**核心原则：一次问清，永不回头。**

扫描维度（必须全部覆盖）：范围边界、硬边界预检（rm/git写/敏感文件/API Key）、外部依赖、能力缺口、风险点、探索方向、成功信号、过期策略。

### Step 0.3: 输出探索计划 + 不确定项清单

展示：探索方向、每轮操作粒度（一步一操作）、预计轮询间隔、已识别风险、Q 项。回复 "开始" 激活。

### Step 0.4: Phase 0.5 — Oracle 自主计划审核（防 AI 自判漏洞）

> **哲学 #6（0信任）物化：AI 自判"不需要问人"不可信。独立 Oracle 对抗性审查自主计划，确保决策链覆盖完整。**

**触发条件**（所有 ghost 激活均强制执行）：
- Oracle critic agent（opus），独立上下文，不共享主会话

**审核维度**（5 维门禁）：

| # | 维度 | 检查内容 | 常见盲区 |
|---|------|---------|---------|
| D1 | **方向适配** | ghost vs goal 选择是否正确？有无 GL-01 方向漂移风险？ | 修复清单误用 ghost 模式 |
| D2 | **歧义穷尽** | Phase 0 是否有未覆盖的歧义？AI 自判"不需要问"是否合理？ | 技术决策误判为用户偏好 |
| D3 | **硬边界完整** | 任务触及面是否可能触碰未声明的禁区（敏感文件/git写）？ | 间接引用敏感文件 |
| D4 | **决策链覆盖** | autonomous-decision-chain 矩阵是否覆盖该任务场景？ | 新颖场景矩阵缺失 |
| D5 | **退出条件** | 成功/失败信号是否可验证？min_iterations 是否合理？ | 主观成功标准不可测 |

**裁决协议**：
- `[Oracle: ACCEPT]` → 进入 Step 0.5 激活
- `[Oracle: REVISE]` → AI 按 Oracle 反馈调整计划 → 重新提交 Oracle（最多 2 轮）
- `[Oracle: REJECT]` → 阻断激活，向人类报告 Oracle 驳回理由 + AI 原计划差异

**留痕**：Oracle 裁决写入 `.omc/state/oracle-verdicts.md`

### Step 0.5: 激活（物理执行，不可跳过）

人类 + Oracle 双确认后激活。从此不再询问任何问题。

**激活时 AI 必须立即执行**（不可跳过、不可手动 touch 替代）：

**1. 运行激活脚本**（必须用 Bash 工具执行）：
```
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "方向" [间隔秒] [过期小时] [最小迭代数]
```

此命令创建 `.omc/state/lx-ghost.json`（`is_mode_active()` 主检测文件）+ `.omc/state/autonomous.active`（completion-gate 等降级信号）。

**2. 验证信号文件存在**（激活后立即执行）：
```
ls -la .omc/state/lx-ghost.json .omc/state/autonomous.active
```

**为什么必须走脚本**：手动 touch 一个文件 = 半个系统仍在 normal mode = agentic_menu 照弹不误（DG-46 教训）。`is_mode_active()` 读取 `lx-ghost.json`（兼容旧格式 `ghost-mode.json`），不读手动创建的文件。

**3. 调用 CronCreate 注册轮询**（非 /loop，无 10 轮上限）：
   - cron 表达式: `*/N * * * *`（N = 间隔分钟数，最少 1 分钟）
   - prompt: `根据 lx-ghost.json 方向做一步探索，更新状态。方向: {方向描述}`
   - recurring: true
   - durable: false

**4. 告知用户** CronCreate job ID + Oracle 裁决结果，可随时 CronDelete 停止

---

## 全自动轮询

间隔默认 600s，最小 30s，不可为 0。

每轮 poll 全自动：
1. 读 lx-ghost.json 确认方向
2. `iterations_completed++`
3. 方向漂移自检 → 偏离则修正，完全漂移则停用
4. **每轮只做一步** — 不并行 agent，不做大规模分析
5. 危险 → 走裁决链；歧义 → 自主判断
6. 更新状态

### min_iterations 强制探索

> 解决「一次性做完就停」的过早收敛。即使当前方向无增量工作，达到最小迭代数前必须继续探索。

```
有工作 → 执行一步
无工作 + iterations < min_iterations:
  → 拓宽探索半径 — 扫描 side findings / 边缘问题 / Oracle minor 项 / 相邻文件调用方
  → 仍无 → skip-risk 记录"方向枯竭，强制拓宽"，继续
无工作 + iterations >= min_iterations:
  → 自检: 方向目标是否达成？
  → 是 → 自动退出 + 退出报告
  → 否 → 报告差距，可延长
```

### Ghost + 执行引擎路由

Ghost 的增量 poll 天然适合 stepwise 模式。但发现可并行子任务时，可调用 race：

```
每轮 poll
  │
  ├─ 发现独立同构子任务（如"批量改 5 个文件的 import"）
  │     → 临时 spawn lx-race 并行处理 → 收集结果 → 继续下一轮 poll
  │
  └─ 单步操作（探索/修复/验证）
        → lx-stepwise 模式：隔离 → 定位 → 方案 → 修复 → 加固
```

> 每轮 poll 默认 stepwise 串行。只有当前轮明确发现可并行的独立子任务时才 spawn race。

---

## 常见场景自主处理

| 场景 | 自主处理 |
|------|---------|
| 方向漂移 | skip-risk 记录，修正方向 |
| 修复阻塞（3 次） | skip-risk，换方向继续 |
| Context Guard 阻断 | override + Bash |
| Permission Gate 拦截 | 走三级裁决链 |
| 发现范围外问题 | 记入附带发现 |
| 令牌过高 | 增加间隔或提前关闭 |
| Git 只读操作 | 自主执行（status/diff/log/blame） |
| 硬边界触发 | 立即跳过 → hard-boundary-hit → 继续其他 |
| 敏感文件被要求读取 | 拒绝 → 记录 hard-boundary-hit → 报告原因 |
| 需 git commit/push | 拒绝 → 记录 hard-boundary-hit → 列出变更清单供人类 |

## 硬边界 — AI 绝对不可触碰的禁区

以下操作与 lx-goal 共享同一硬边界定义。在无人值守模式下 **绝不可执行**。遇到时「跳过→记录→报告」，**不裁决、不绕过**。

### 禁区清单
1. **破坏性文件操作**：`rm` / `rm -rf` / `rmdir` / `dd` / `mkfs` / `git clean -fd`
2. **Git 写操作**：`git commit` / `git push` / `git rebase` / `git reset --hard`
3. **敏感文件触碰**：`.env*` / `*.pem` / `*.key` / `id_rsa*` / `credentials*` / `secret*`
4. **API Key / Token**：命令行明文 Token / 写入 Token 到文件 / 环境变量传递 Token

### 硬边界协议
```
遇到硬边界 → 立即跳过 → 记录: lx-ghost hard-boundary-hit "..." → 继续探索 → 退出报告列出
```

## 最大自主权声明

在硬边界之外，AI 拥有完全自主权。与 lx-goal 共享同一自主权范围（文件创建/修改、代码重构、架构决策、子 Agent 调度、依赖安装、测试运行、编译构建、Git 只读）。

---

## 退出

### 退出协议（强制门禁）

> **哲学 #4（没验证=没做）物化：无报告，不关闭。**

```
完成探索
  │
  ├─ 1. 按退出报告结构在对话中生成报告
  │
  ├─ 2. lx-ghost report '报告内容'  — 写入并通过 5/5 章节验证
  │     ├─ 缺失章节 → 提示补充，继续步骤 1
  │     └─ 5/5 通过 ✅ → 进入步骤 3
  │
  ├─ 3. lx-ghost off                 — 再次验证报告完整性
  │     ├─ 报告缺失 → 🛑 阻断，redirect 回步骤 2
  │     └─ 报告完整 ✅ → 关闭
  │
  └─ 紧急绕过: lx-ghost off --force  — 跳过报告检查，留下 ghost-exit-pending 桩
       → 下次 SessionStart inject-project-knowledge.sh 检测桩文件并提醒补交
```

### 退出报告结构（5 个必填章节 + 1 个强制汇总段）

- **## 探索摘要**：方向、轮次、关键发现
- **## 已完成操作**：逐项列出 + Before/After 对比
- **## ⚠️ 需人为决策汇总（强制）**：聚合所有需人类关注项（硬边界 + 阻断 + 推迟决策 + 不确定判断）到一张汇总表。每行含: 类型 / 描述 / AI 推荐 / 依据。人类不应逐节翻找。
- **## ⚠️ 需人类介入项（硬边界）**：被硬边界跳过的操作 + 原因 + 建议人类操作
- **## 已跳过风险**：skip-risk 记录项
- **## 附带发现**：范围外问题

---

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级 warn-only，危险走裁决链 |
| #4 | 没验证=没做 | 每轮 poll 报告状态 |
| #6 | 0 信任 | Phase 0.5 Oracle 自主计划审核（5维门禁），危险记录 skipped_risks，裁决链 Level 2 |
| #2 | 少量大增益 | 只做方向相关的事，min_iterations 强制拓宽防过早收敛 |
