# kernel.md — 管理内核

> 不可自改。变更须人类裁决。

## 冻结规则
AI 不可自改 AGENTS.md / kernel.md / index.md。

## 学习飞轮（Phase 2）
飞轮数据落 `.omc/knowledge/`，不进默认 Context。

## 三段式水位（已接入）

| 区间 | 动作 | 条件 |
|:----:|:-----|:-----|
| 🟢 安全 0-40% | 正常执行 | 无额外动作 |
| 🟡 警戒 40-50% | CHECKPOINT 提示 | 超过 50% 且任务 stop → 自动 compact |
| 🔴 临界 50-70%+ | 超过 70% 暂停+写 handoff | 超 70% 且任务未停止 → 暂停执行，写 handoff，compact 后恢复 |

水位检测脚本: `.claude/scripts/lib/water_level.py` — 通过 `get_water_detail()` 实时读取可控注入 token 数并与阈值比较。

## 降级规则
能力缺失可降级。证据缺失、安全缺失、状态冲突不可降级。
