# 05 — compact/resume 场景

## 目标

验证治理系统在 Context 压缩（compact）与会话恢复（resume）后，能否保持任务状态不丢失。这是防 Compact 机制（Handoff 保护）的核心验证。

## 测试场景

| 阶段 | 动作 | 预期行为 |
|:-----|:-----|:---------|
| 1. 任务启动 | 启动一个中等复杂度的治理任务（改多个文件、包含多个步骤） | 任务正常进入执行状态 |
| 2. Context 压缩 | 触发 `experimental.session.compacting` 事件 | 将当前任务状态序列化写入 `.claude/session-handoff.md` |
| 3. 会话恢复 | 新会话启动 | 读取持久化状态，注入恢复上下文到新会话 |
| 4. 继续执行 | 模型接收恢复上下文，继续未完成任务 | 任务从断点继续，不丢失已完成步骤和待办项 |

## 涉及组件

| 组件 | 路径 | 职责 |
|:-----|:-----|:-----|
| `carros_base.py` | `.claude/scripts/carros_base.py` | 核心状态管理：init/status/tick/verify/archive |
| `omc_lint.py` | `.claude/scripts/omc_lint.py` | 文档格式和状态一致性检查 |
| `session-handoff.md` | `.claude/session-handoff.md` | 状态持久化文件（含任务摘要、已完成/待办项、文件列表） |
| `token.json` | `.omc/tokens/{date}/{task_id}.json` | 任务令牌系统（状态机：in_progress → verify_done → archived） |

## 数据流

```
任务状态持久化：
  carros_base.py ──→ 写入 token.json + executor.md
                ──→ 同步 session-handoff.md

新会话恢复：
  session-handoff.md ──→ 读取当前任务状态
                     ──→ plan.md 读取 remaining steps
                     ──→ executor.md 读取已执行证据
```

## 预期产物

| 文件/产物 | 说明 |
|:----------|:-----|
| `.claude/session-handoff.md` | 持久化的会话状态快照 |
| `.omc/tokens/{date}/{task_id}.json` | 任务令牌（含 state/done/total） |
| `.omc/tasks/{date}/{task_id}/plan.md` | 任务计划文档 |
| `.omc/tasks/{date}/{task_id}/executor.md` | 执行证据记录 |

## 预期验收标准

1. **状态完整性**：compact 后 resume，已完成步骤数一致，pending 项不丢失
2. **文件关联性**：恢复上下文中的文件路径可访问
3. **上下文连贯性**：模型能在恢复后准确识别任务目标和当前进度
4. **token 时效性**：状态从 token.json 正确重建
5. **handoff 完整性**：session-handoff.md 包含足够上下文继续任务

## 验证方法

```bash
# 1. 查看当前任务状态
python3 .claude/scripts/carros_base.py status

# 2. 验证 token 完整性
cat .omc/tokens/$(date +%Y%m%d)/*.json | python3 -m json.tool

# 3. 查看 handoff 状态
cat .claude/session-handoff.md

# 4. lint 检查
python3 .claude/scripts/carros_base.py lint
```

## 失败模式

| 失败模式 | 影响 | 检测方式 |
|:---------|:-----|:---------|
| handoff 文件损坏 | 恢复时无法读取状态 | 检查 handoff 文件格式 |
| token.json 损坏 | 恢复时无法确定进度 | 检查 JSON 格式验证 |
| plan.md 缺失 | 无法获取待办步骤 | 检查 plan.md 是否存在 |
| 状态不一致（已完成 vs 待办） | 模型重复执行或遗漏步骤 | 比较 token done/total 与实际文件状态 |

## 相关哲学约束

- **哲学 #7（文档优先）**：从 executor.md/plan.md 重建上下文，而非依赖模型记忆
- **禁止编造**：恢复上下文中不能编造不存在的进度
- **证据门禁**：恢复后需有 VERIFIED 证据才能继续推进
- **范围冻结**：恢复后不应擅自扩展原始任务范围
