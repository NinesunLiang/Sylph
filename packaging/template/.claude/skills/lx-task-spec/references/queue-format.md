## Todo 文件规范

**存储位置**：`{项目根}/.omc/state/todo-queue.md`（首次使用时自动创建）
> **独立系统**：lx-todo 是独立的零散任务系统，与 lx-rpe（主任务/step 概念）完全分开。
> >
> ⚠️ **统一路径**：与 `turn-counter.sh` 共享同一文件，两者读写同一个 todo 队列。
> `turn-counter.sh` 每 10 轮自动注入此文件内容到 AI context；`lx-todo` 负责增删改查。
**文件格式**（严格遵循，不可变体）：

```markdown
# Todo List
## 待处理- [ ] #1 🐛 P1 QueryTasks 空 slice 未做 len 检查 · source:code-review-H4 · 2024-01-15- [ ] #2 ✨ P2 日志加 requestID 上下文 · source:自发现 · 2024-01-15
## 进行中- [-] #3 🔧 P1 TaskModel 接口拆分 · source:code-review-D2 · started:2024-01-15
## 已完成- [x] #0 🐛 P1 FindTask nil 检查缺失 · source:code-review-H1 · done:2024-01-14 · files:1
## 已升级到 lx-task-spec- [↑] #4 ✨ P0 新增批量导出 API · reason:需设计+>3文件 · upgraded:2024-01-15
```
**字段定义**：
| 字段 | 必填 | 格式 | 说明|
|------|------|------|------|
|ID | 是 | `#N` 自增整数，不复用 | 唯一标识|
|类型 | 是 | `🐛bug` `✨feat` `🔧refactor` `📝docs` | 决定执行路径|
|优先级 | 是 | `P0` `P1` `P2` `P3` | P0>P1>P2>P3，同级按 ID 升序|
|描述 | 是 | 一句话，≤50 字 | 可定位问题的最小信息|
|source | 是 | 来源标识 | `code-review-{规则号}` / `security-review` / `自发现`|
|日期 | 是 | YYYY-MM-DD | 创建/完成/升级日期|
|files | 完成时 | 数字 | 实际变更文件数|
|reason | 升级时 | 文本 | 升级原因 |
