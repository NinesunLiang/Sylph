# Context Guard - 上下文守卫

>
> 上下文
> 40% 即触发总结并重置
> 版本：v1.0.0

---

## 触发条件

当会话上下文使用量达到阈值，**且当前 Step 已结束并记录文档**时触发：
| 阈值 | 动作|
|------|------|
|**>40%** | 触发渐进式总结（仅当当前 Step 已完成并写入文档）|
|**>60%** | 强制总结 + 状态快照（即使 Step 未完成，也必须安全断点）|
|**>80%** | 紧急总结 + 建议新会话（兜底保护） |
> **防中断原则**：Reset 清理上下文的前提是当前 Step 已经结束，且关键信息已记录到 `.omc/state/` 文档中。绝不在大任务执行中途强制 Reset。

---

## 总结流程

### Step 1: 状态快照

将当前任务状态写入 `.omc/state/{date}/{task_name}/output/`：
- `executor.md` — 当前执行进度
- `plan.md` — 计划清单（已勾选/未完成）
- `summary.md` — 本轮总结

### Step 2: 关键信息归档

将以下信息写入 `.omc/state/{date}/{task_name}/context/`：
- `research.md` — 已完成的调研结论
- `lessons.md` — 本轮学到的错误模式

### Step 3: 上下文清理

保留以下信息在新会话中：
1. 任务基本信息（task_name / role / target / priority）
2. 当前 state
3. plan.md 中的未完成步骤
4. 最近一轮的证据块
清除以下信息：
1. 已完成的调研过程细节
2. 中间调试记录
3. 已验证通过的步骤详情（只保留结论）

### Step 4: 恢复指令

在总结末尾写入：

```
mark
down## 恢复指令
下一会话启动时：
1. Read `.omc/state/{date}/{task_name}/output/plan.md`
2. Read `.omc/state/{date}/{task_name}/output/executor.md`
3. 从第一个未勾选的 step 继续执行
4. 不要重复已完成的步骤
```

---

## 渐进式披露原则

| 层级 | 内容 | 访问时机|
|------|------|---------|
|L1 大纲 | 任务目标 + 当前 state | 始终|
|L2 步骤 | 当前 step 详情 | 执行该 step 时|
|L3 执行 | 涉及文件的 file:line | 改动该文件时 |
**严格边界**：当前步骤只访问必要资源，不越界 Read 其他 step 的文件。

---

## 会话初始化时

收到 task_input 后：
1. 检查 `.omc/state/` 下是否有同名任务的未完成记录
2. 若有 → 加载最近状态，从断点继续
3. 若无 → 按 orchestrator.md 的状态机从头启动
