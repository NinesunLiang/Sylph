# kernel.md — 管理内核

> 冻结 / 飞轮 / 降级。不可自改。

## 冻结规则
AI 不可自改 AGENTS.md / kernel.md / index.md。变更须人类裁决。

## 学习飞轮（L2 Enhance）
Base + 2 学习资产：
- `references/claude-next.md` — 经验层，用户纠正 + 模式失误
- `references/error-dna.json` — 失败模式层，可复用系统性错误

飞轮触发：失败 > 修复 > 记录 > 复用。不阻塞主流程。

## 三段式水位（L2 Enhance）
| 水位 | 范围 | 行为 |
|------|------|------|
| 🟢 安全 | 0-40% | 正常执行 |
| 🟡 警戒 | 40-70% | 停止加载新 reference；工具输出截断 |
| 🔴 临界 | 70%+ | 当前 step 完成后停；写 handoff；询问是否进行compact，三十秒内容无回应ai尝试自行 compact |

检测脚本：`.claude/scripts/context_watermark.py`

## Oracle 门
5 点触发：跨系统 / 不可逆 / 安全权限 / 发布 / 长时间无人
检测脚本：`.claude/scripts/oracle_gate.py`

## 降级规则
能力缺失可降级（Oracle 不可用、Watermark 不可观测）。
证据缺失、安全缺失、状态冲突不可降级。
降级矩阵：`.claude/scripts/fallback_matrix.py`
