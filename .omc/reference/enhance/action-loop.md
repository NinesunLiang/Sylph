# Action Loop 检测 (E4)

> L2 Enhance Gate: pretool-gate 内置动作循环检测
> 检测同 tool+command 高频重复 → NARROW 软门警告 → 多次忽略后升级 BLOCK

## 触发条件

| 条件 | 阈值 | 行为 |
|------|------|------|
| 同 tool+command 重复（仅写工具/Bash） | ≥3 次 / 最近 20 事件 | NARROW 软门 + audit 记录 |
| 连续同签名 NARROW 被忽略 | ≥3 次连续 | **BLOCK** 硬阻断 + 停止执行 |

## E4 硬化（v7.2+）— 惯性执行升级

### 变更摘要

| 项 | 旧行为 | 新行为 |
|----|--------|--------|
| 监控范围 | 全部工具（含 Read/Glob/Grep） | **仅写工具+Bash**（Read 自然重复不触发） |
| NARROW 升级 | 永不升级 | **连续 3 次同签名 → 第 4 次 BLOCK** |
| 无命令/路径事件 | 退化为裸 tool 名（"bash"、"edit"） | 按 path 降级或跳过 |
| streak 持久化 | 无 | `action-loop-streak` 文件持久化，含签名 + 计数 |
| 升级后清理 | 无 | BLOCK 后自动删 streak，防无限重复 |

### 签名聚合规则

```
# 优先级:
1. tool + command[:80] → "bash:git push..."
2. tool + path[:80]    → "edit:.claude/hooks/...py"
3. 两者都空 → 跳过
```

### streak 升级条件

```python
_ACTION_LOOP_STREAK_FILE       # .omc/state/action-loop-streak (JSON: {"sig":"...", "count":N})
_ACTION_LOOP_ESCALATE_THRESHOLD = 3
_ACTION_LOOP_MUTATING_TOOLS = {"write", "edit", "multiedit", "notebookedit", "bash"}
```

## 检测逻辑

1. 读 `.omc/audit/{today}.jsonl` 最近 20 条记录
2. 过滤：仅 tool∈{write,edit,multiedit,notebookedit,bash} 的事件
3. 按 `tool:command{preview}` 或 `tool:path` 签名聚类
4. 最频繁签名 ≥3 → 触发软门警告
5. 读 streak 文件判定是否升级（同签名连续 ≥3 次 → BLOCK）

## 输出

```
⚠️ [action-loop] NARROW action-loop: {pattern} 重复 {N}/{20} 次
```
```
⛔ 操作被阻断: action-loop-escalated: {pattern} 重复 {N}/{20} 次
    （连续 {N} 次 NARROW 被忽略后升级为 BLOCK）
    💡 建议: 停止当前行为模式，分析是否在错误的方向上重复尝试
```

- NARROW 软门不阻断，仅写入 stderr + audit
- BLOCK 硬阻断，写入 stderr + audit（事件类型 `action_loop_warn`，含 streak 计数）
- audit 字段新增：`streak`（连续 NARROW 次数）

## 集成点

- `.claude/hooks/pretool-gate.py` — `_check_action_loop()` 函数，GATES 列表末尾
- `.omc/audit/` — 读取最近工具调用记录
- `.omc/state/action-loop-streak` — streak 持久化文件

## 配置

无需配置，纯自包含。检测窗口 20 次，阈值 3 次，escalation 阈值 3 次，均为硬编码。仅跟踪写工具和 Bash。
