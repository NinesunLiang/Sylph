# Orchestrator Node → 路由到 `task_sys/orchestrator.md`

> 本文件是路由指针。权威状态机、Gate 检查点、失败回退策略的唯一定义在:
> [`../task_sys/orchestrator.md`](../task_sys/orchestrator.md)

## 节点职责

作为 Enhanced 任务系统的入口节点，负责:
1. 接收 `task_input` → 路由到正确子节点
2. 状态机转换遵循 `task_sys/orchestrator.md` 的 6 状态定义
3. 失败回退策略遵循 `task_sys/orchestrator.md` 的 Fallback 降级流程
4. 质量控制遵循 A/B Terminal 分离验收

## 路由决策 (速查)

| 条件 | 路由到 |
|------|--------|
| pass_criteria / role 缺失 | A0 Clarifier |
| 非琐碎任务 (≥3 步 / 架构决策) | Plan Node |
| 琐碎任务 / 计划已确认 | Execute Node |
| 执行完成 | A-Terminal → B-Terminal |

完整定义见 [`task_sys/orchestrator.md`](../task_sys/orchestrator.md)。
