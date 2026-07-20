# lx-goal — 目标驱动自主执行

> **一次前置澄清 → 全自动执行 → 退出报告。人类在窗口期回答所有问题后离开，AI 不再请求任何交互。**

## 原子化声明

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/phase0-activation.md` | Phase 0 前置澄清 |
| `references/autonomous-execution.md` | Phase 1→N 全自动执行 |
| `references/exit-report.md` | 退出报告 |

> 共享 OMA 能力 `@../references/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining

## 执行模型

```
人类窗口期（Phase 0）  →  AI 全自动执行（Phase 1→N）  →  退出报告
澄清所有不确定项           不暂停·不提问·不问人            结构化报告待审阅
人说"开始"→激活          AI 自主决策直到完成或过期       已完成/已跳过/需人类
```

## 子任务执行引擎路由（引用决策矩阵）

参见 `docs/technical/cn/execution-mode-matrix.md` 完整决策矩阵。

快速判断（Phase 0 激活时自动评估）：

| 特征 | → 引擎 |
|:-----|:------|
| 可 MECE 分解 ≥3 同构子任务 | **lx-race**（`race-tool.py` 文档驱动） |
| 有依赖链 / 异构 / 跨模块 / 根因不明 | **lx-stepwise**（逐步串行） |
| 单文件小改 | **direct**（无模式，直接执行+证据） |

Phase 0 输出执行计划时必须包含模式选择理由（引用矩阵的 #1-#9 场景编号）。

## 执行流程

### Phase 0: 前置澄清 → `@references/phase0-activation.md`
一次问清所有不确定项 → 输出执行计划 → 人说"开始"→ 激活:
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh on "{目标描述}"
```

### Phase 1→N: 全自动执行 → `@references/autonomous-execution.md`
核心铁律：不暂停、不提问、不中断、只记录。
决策层级: Philosophy → Iron Rules → Practices → AI 判断。
危险操作走三级裁决链，硬边界立即跳过。

### 退出报告 → `@references/exit-report.md`
执行摘要 + 已完成任务 + 已跳过风险 + 需人为决策汇总。

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 主路径失败 | 输出当前进度摘要，标记未完成任务 |
| 硬边界触发 | 跳过该操作，记录原因 |
| 过期超时 | 保存状态，生成退出报告 |
