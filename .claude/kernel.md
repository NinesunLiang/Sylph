# kernel.md — 管理内核

> 不可自改。变更须人类裁决。

## 冻结规则
AI 不可自改 AGENTS.md / kernel.md / index.md 及 `.claude/hooks/*` / `scripts/carros-gates/harness.yaml`。

## 紧凑恢复（R2 Compact Storm）
紧凑后自动读取 `.omc/session-handoff.md` 恢复会话。
恢复流程：
1. 读 handoff → Current Goal / Current State / Next Action
2. 校验任务文件是否存在（token.json / plan.md）
3. 从 Next Action 的 step 继续
4. 拒绝进入 Auto Mode 直到恢复完成

## U 型注意力模型（R6）
信息注入采用 "U 型" 结构：
- **头部**（每次注入）：铁律摘要（本文件前 5 行）+ 当前 task level + scope
- **中部**（按需）：Gate 规则、文档、参考
- **尾部**（每 5 轮强制注入）：任务状态更新（doing/done/blocked）+ todo 列表 + 水位

## 决策框架（R9 智能化）
遇到需要决策时，按此链条执行：
1. **哲学**：验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少
2. **铁律**：不可逆操作问人，可逆操作自决
3. **ROI**：实现成本 vs 收益。低成本高收益 → 直接做
4. **Gate 模式**：L1（默认，6 门）/ L2（完整 16 门 + Oracle）
5. **Oracle 辅助**：仅 L2 模式下调用 phase3 oracle 辅助决策

## 学习飞轮（Phase 2，Enhance 专有）
飞轮数据落 `.omc/knowledge/`，不进默认 Context。

## 水位防线
**A. 可控预算水位**（prompt 预算纪律，分子=可控注入 token，分母=12000）
| 区间 | 动作 |
|:----:|:-----|
| 🟢 safe [0,40%) | 正常执行 |
| 🟡 warn [40%,70%) | checkpoint 提示，禁止扩张；触发 handoff 写入 |
| 🔴 crit [70%,100%] | 暂停+写 handoff+请求 compact |

**B. 上下文水位**（transcript 实测用量/窗口）
| 区间 | 动作 |
|:----:|:-----|
| 🟢 <50% | 正常执行 |
| 🟡 [50%,70%) | 提醒 compact |
| 🔴 [70%,80%) | 只读模式 |
| ⛔ ≥80% | 全阻强制 compact |

## 错误分析体系
每个错误都是养分。自动记录 → 分类 → 根因 → 预防。

## Gate 模式
- **L1 轻量**（默认）：6 核心门（watermark/sensitive/fallback/action/scope/stall）
- **L2 完整**：全部 17 门 + Oracle 审查
- 切换：`carros_base.py init --mode L2` 或 harness.yaml `gate_mode: l2`

## 降级规则
能力缺失可降级。证据缺失、安全缺失、状态冲突不可降级。
