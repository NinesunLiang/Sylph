# SubAgent 派发契约

> 参考 round3 设计：SubAgent 是轻量任务派发机制，仅在需要时才使用。

## 何时派发
- 局部调研（读代码/查文档）
- 单一改动（≤5 文件、≤5 分钟）
- 不熟悉的局部技术栈

**不做**：把整个任务丢给 subagent。要自己做主流程，subagent 只做局部。

## 派发四步

1. **写输入**：`subagent/{id}_input.md`
   - Goal（目标）
   - Scope（允许读/改/禁止的范围）
   - 期望产出（什么格式、什么内容）
   - Stop 条件（什么情况下必须停止并返回）

2. **spawn**：用 delegate_task 工具派发，传 id

3. **轮询**：每 10s 读 `subagent/{id}.json` 的 status
   - `done` → 合并 deliverable
   - `blocked` → 补信息 / 拆小重派 / 自己接管
   - `15s 无 ACK` 或 `5min 未 done` → 收 partial → 自己接管

4. **收官**：按状态处理

## 铁律约束
SubAgent 同样受铁律约束：
- 越界修改 → 违规
- 无证据改动 → 违规
- 埋头不报 > 15s → 违规

## 契约格式

```json
{
  "subagent_id": "research-01",
  "goal": "调研 X 模块的 API 设计",
  "scope": {
    "allow_read": ["src/x/**"],
    "allow_write": [],
    "forbidden": ["secrets/**", ".env"]
  },
  "expected_output": "report.md 格式：背景、API 设计、风险点",
  "stop_on": ["timeout_300s", "error_3_consecutive"]
}
```

## 参考
- poll-subagent.py — 轮询脚本
- subagent-schema.json — 输入/输出 JSON 模式
