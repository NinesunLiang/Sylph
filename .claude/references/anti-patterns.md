# Anti-Patterns — 经验沉淀

_Updated: 2026-10-16 | 人类裁决精简：165 行 → ≤40 行（防膨胀闸 40 行阈值）_

> 只保留**被代码引用或仍活跃**的反模式。过期条目归档至 `references/archived/anti-patterns-20261016.md`。
> 飞轮追加纪律：本文件超 40 行 → `stop-flywheel.py` 停止追加，需先精简/晋升（人类裁决）。

## 保留条目（代码引用 / 仍活跃）

| ID | 一句话 | 对治 | 代码引用 |
|----|--------|------|---------|
| K2 | 同文件短期 Edit≥3 次签名漂移（编辑未收敛） | 大改动一次 Write；Edit 只改单句 | posttool-claim-audit `_autofix_log_edit_repeat` |
| L1 | plan.md 自创 Phase 格式被 PlanGate 拒 | 只用 `init` 生成的模板，不改 Phase 头 | test_index47_k1g1_removal 契约 |
| L2 | 单次 Write >8192 tokens 截断 | 分批 Write / >500 行用模板+Edit | pretool-gate 8000 字符 REDIRECT |
| L3 | 凭感觉传参 → TypeError | 调用前先 Read 函数签名 | — |
| L4 | EV 块缺 plan.verify 关键短语 | assertion 逐字复用 plan.verify 原文 | VerifyGate evidence_missing |
| L5 | 单次 sleep 超沙箱超时(120s) | 分段 sleep / 后台 / 轮询 | — |
| L6 | bug 修一半停手 → 下游连环错 | 修复后跑全流程（一镜到底） | — |

## 已归档（移入 references/archived/anti-patterns-20261016.md，含 index37 来源完整版 L 段）

- **K1**（数值断言无来源）— 机制 index47 已删（12 天 0 触发），条目过期
- **K3**（内容方向摇摆）— 0 触发，历史教训
- **I1 / J1 / J2 / assertion_recurring** — 2026-07/08 历史数据，未再触发
- **governance_intervention / redirect_recurring / blocked_recurring** — 飞轮升华条目，内容空转（仅指向 claude-next.md），无独立行为指令

速查：AI 行为模式 L1-L6 是本文件核心；机制类（K/I/J）条目随对应 hook 存亡。
