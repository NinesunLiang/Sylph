# 执行模式决策矩阵 v1.0

> 本文档定义 CarrorOS 四种执行场景（RPE / L2+监督 / Ghost 无人 / Goal 任务）的模式选择规则
> 哲学依据：#2(最小改动)、#4(验证驱动)、#7(文档优先)

---

## 模式定义回顾

| 模式 | 特性 | 并行度 | 适用 |
|:----|:-----|:------:|:----|
| **race** | 文档驱动并行蜂群（race-tool.py） | N 并行 | 同构独立子任务 |
| **stepwise** | 串行逐步推进，每步验证 | 1 | 复杂依赖链/根因不明 |
| **direct** | 无正式模式，直接执行+证据门禁 | 1 | L1 简单任务（<30min） |

---

## 决策矩阵

| # | 场景 | 子任务数 | 依赖关系 | 单任务复杂度 | 推荐模式 | 理由 |
|:-:|:----|:--------:|:--------:|:----------:|:--------:|:----|
| 1 | **RPE 特性开发** | 3~9（9步闭环） | 前后强依赖 | 中~高 | **stepwise** | RPE 9 步是串行门禁链，每步的产出是下一步的输入 |
| 2 | **RPE 内步骤扩展**（如 Step 5 实现 3 个独立组件） | ≥3 | MECE 无依赖 | 低~中 | **race** | 步骤内部可 fan-out，不影响 RPE 主门禁链 |
| 3 | **L2+ 监督模式修复**（根因已知，多文件改） | 2~5 | 部分依赖 | 中 | **stepwise** | 虽可拆子任务，但涉及跨模块影响需逐步验证 |
| 4 | **L2+ 监督模式修复**（根因不明） | 1 | — | 高 | **stepwise** | 根因不明是 stepwise 的典型场景，5 步定位法 |
| 5 | **Ghost 无人探索**（方向明确，多同构目标） | ≥3 | MECE | 低~中 | **race** | 多独立目标并行搜索，效率最大化 |
| 6 | **Ghost 无人探索**（深度单线分析） | 1~2 | 强依赖 | 高 | **stepwise** | 串行深挖，每步验证保证质量 |
| 7 | **Goal 任务**（可分解为 ≥3 同构子任务） | ≥3 | MECE | 低~中 | **race** | 目标可并行，典型 race 场景 |
| 8 | **Goal 任务**（异构/跨模块/有依赖） | 2~5 | 交错依赖 | 中~高 | **stepwise** | 子任务间有数据流或顺序依赖 |
| 9 | **单文件小改 / 配置调整** | 1 | — | 低 | **direct** | 不值得走模式，直接改+验证 |

---

## 模式选择流程图

```
任务进入
  │
  ├─ L1（单文件/低复杂度）→ direct
  │
  └─ L2+
      │
      ├─ 是否为 RPE？→ stepwise（全 9 步门禁链）
      │                        └─ 某步骤内 ≥3 同构组件 → race（步骤内 fan-out）
      │
      ├─ 是否为 Ghost 无人探索？
      │     ├─ 方向明确 + 多同构目标 → race
      │     └─ 深度单线分析 → stepwise
      │
      ├─ 是否为 Goal 目标任务？
      │     ├─ 可 MECE 分解 ≥3 → race
      │     └─ 有依赖/异构/跨模块 → stepwise
      │
      └─ 监督模式修复
            ├─ 根因已知 → stepwise（多文件逐步改）
            ├─ 根因不明 → stepwise（5 步定位法）
            └─ 单一简单修复 → direct
```

---

## 混合执行规则

### Race → Stepwise 嵌套
```
[Race: 并行探索 3 个独立组件]
  ├── [Stepwise: 组件 A — 复杂实现]
  ├── [Stepwise: 组件 B — 复杂实现]
  └── [Stepwise: 组件 C — 复杂实现]
```
规则：Race 负责并行调度和结果聚合，每个子任务内部可独立用 stepwise

### Stepwise → Race 展开
```
[Stepwise: Stage 3 — 实现功能]
  ├── [Race: 并行实现 4 个独立函数]
  │   ├── func-a
  │   ├── func-b
  │   ├── func-c
  │   └── func-d
  └── [Stage gate: 全部功能实现已验收]
```
规则：Stepwise 某阶段内部可展开为 Race，但 Race 必须在阶段门禁前聚合完毕

---

## 路由接入点

| 入口场景 | 路由逻辑 | 依据 |
|:--------|:--------|:----|
| 用户说"/lx-rpe" | → RPE stepwise | SKILL.md execution_mode:stepwise |
| 用户说"/lx-race" | → race | SKILL.md execution_mode:race |
| Goal 模式激活 | → 根据子任务特征选 race/stepwise | 本决策矩阵 |
| Ghost 模式激活 | → 根据方向类型选 race/stepwise | 本决策矩阵 |
| 监督模式下 L2+ | → 根据根因状态选 stepwise/direct | 本决策矩阵 |

---

## Fallback 回退机制

模式选错或执行中发现不符合预期时，降级路径：

| 原选模式 | 失败信号 | 降级路径 | 记录要求 |
|:--------|:--------|:--------|:--------|
| race | 子任务间发现共享依赖 | → **stepwise**（串行处理） | 记入退出报告「模式重选」 |
| race | >50% 子任务超时/失败 | → **stepwise**（剩余的串行） | 记入退出报告「模式重选」 |
| stepwise | 第一/第二阶段发现完全独立可并行 | → **race**（并行 fan-out） | 记入阶段记录「模式重选」 |
| stepwise | 连续 2 次阶段 gate 失败 | → 暂停，标记 blocked | 按决策链 L3 处理 |
| direct | 发现实际需跨文件/复杂逻辑 | → **stepwise** | 立即切换，不写额外记录 |

---

## 自检失败模式与验证

### 常见模式选择错误

| # | 错误类型 | 表现 | 纠正 |
|:-:|:--------|:-----|:-----|
| E1 | 把耦合任务误判为 MECE（选了 race） | 子任务间需互相等待数据 | → fallback 到 stepwise |
| E2 | 把简单同构任务误判为复杂（选了 stepwise） | 实际可并行 | → fallback 到 race |
| E3 | Ghost 选 race 但方向深度不够 | 各子任务产出浅 | → 提高 min_iterations |
| E4 | Goal 选 stepwise 浪费并行机会 | 子任务无依赖但串行执行 | → 下次选 race |

### Phase 0 验证检查（goal/ghost 激活时）

```
Phase 0 输出执行计划时，必须包含：
[ ] 场景编号（#1-#9）—— 引用矩阵
[ ] 模式选择依据 —— 引用理由列
[ ] Fallback 路径 —— 如果模式选错，降级到哪个模式
[ ] 自检项 —— 检查是否有 E1-E4 的苗头
```

| 文件 | 与本矩阵的关系 |
|:----|:-------------|
| `.claude/reference/execution-modes.md` | Race 和 Stepwise 的详细状态机定义，本矩阵引用其状态模型 |
| `lx-race/references/body.md` | Race 的执行协议，本矩阵指定何时用 race |
| `lx-stepwise/references/body.md` | Stepwise 的执行协议，本矩阵指定何时用 stepwise |
| `lx-goal/references/body.md` | Goal 模式激活后路由到此矩阵 |
| `lx-ghost/references/body.md` | Ghost 模式激活后路由到此矩阵 |
| `autonomous-decision-chain.md` | 自主模式下的决策链，与模式选择独立但并行工作 |
