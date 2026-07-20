# kernel.md — 管理内核

> 不可自改。变更须人类裁决。

## 冻结规则
AI 不可自改 AGENTS.md / kernel.md / index.md。

## 学习飞轮（Phase 2）
飞轮数据落 `.omc/knowledge/`，不进默认 Context。

## 水位防线（两套，各司其职）

**A. 可控预算水位**（prompt 预算纪律，分子=可控注入 token，分母=12000）

| 区间 | 动作 |
|:----:|:-----|
| 🟢 safe [0,40%) | 正常执行 |
| 🟡 warn [40%,70%) | checkpoint 提示，禁止扩张 |
| 🔴 crit [70%,100%] | 暂停+写 handoff+请求 compact（`run_water_gate` → PAUSED_CONTEXT_CRITICAL） |

检测脚本: `.claude/scripts/lib/water_level.py` — `get_water_detail()` 实时读取可控注入 token 数并与阈值比较。

**B. 上下文水位**（transcript 实测用量/窗口，任务18 落地）

| 区间 | 动作 |
|:----:|:-----|
| 🟢 <50% | 正常执行 |
| 🟡 [50%,70%) | 提醒 compact（compact_decision: 50=COMPACT_SOON） |
| 🔴 [70%,80%) | 只读模式（pretool-gate 禁写 BLOCK） |
| ⛔ ≥80% | 全阻强制 compact |

链: pretool-user-approve 实测 → pretool-gate watermark 门 → context_engine compact_decision；详见 `.claude/references/context-watermark.md`。

## 降级规则
能力缺失可降级。证据缺失、安全缺失、状态冲突不可降级。
