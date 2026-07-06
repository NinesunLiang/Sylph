# 04 — 失败后修复场景

> 验证治理系统在 step 执行失败后能否正确记录、修复、重新验证

## Goal

模拟一个 step 执行失败（如命令退出码非零、产物不完整、验证未通过）的场景，验证治理系统能够：
1. 正确**记录**失败状态与错误信息（token / executor / audit）
2. 允许人类或系统**修复**失败原因（修复代码、重跑命令、补充产物）
3. **重新验证**修复后的 step，最终达成 VERIFIED 状态
4. 完整留存失败→修复→验证全过程的**审计迹**

## Expected Files

| 文件 | 说明 |
|------|------|
| `.omc/tokens/{date}/{task_id}.json` | 包含 step 失败->修复->verified 的完整状态变迁 |
| `.omc/tasks/{date}/{task_id}/plan.md` | plan 中该 step 标记过 `[FAILED]` 后改为 `[DONE]` |
| `.omc/tasks/{date}/{task_id}/executor.md` | 记录失败证据（错误输出/退出码）+ 修复证据 |
| `.omc/tasks/{date}/{task_id}/state/audit/*.jsonl` | 审计日志包含 failure、repair、reverify 三类事件 |
| `bench/04_failure_then_repair/README.md` | 本文件 |

## Expected Plan Steps

```text
S1: 触发一个受控失败（如运行一个必然失败的命令）
    预期：step 标记为 FAILED，错误信息记录到 executor.md
S2: 分析失败原因并执行修复
    预期：fix 动作写入 executor.md，plan.md 保留 FAILED 标记不变
S3: 重新验证修复后的 step
    预期：verify 输出 VERIFIED，plan.md 更新为 DONE
S4: 归档并确认审计日志完整性
    预期：archive 成功，audit JSONL 包含 failure→repair→verify 链条
```

## Required Evidence

| 证据项 | 验证方式 |
|--------|----------|
| `token.json` 中 state 字段记录 `failed` → `repairing` → `verified` | `cat .omc/tokens/{date}/{task_id}.json | jq '.state'` |
| 失败 step 的 `exit_code` 或 `error` 字段非空 | `grep -E '"exit_code"|"error"' .omc/tasks/{date}/{task_id}/executor.md` |
| 修复动作在 executor.md 有对应记录 | `grep -i 'fix|repair|re-run|retry' .omc/tasks/{date}/{task_id}/executor.md` |
| `plan.md` 中该 step 标记从 `FAILED` 变为 `DONE` | `grep 'S1' .omc/tasks/{date}/{task_id}/plan.md` |
| audit 日志包含至少一条 `"event":"step_failure"` 和一条 `"event":"step_verify"` | `cat .omc/tasks/{date}/{task_id}/state/audit/*.jsonl | grep -E 'step_failure|step_verify'` |
| `carros_base.py verify --step S1` 输出 `VERIFIED` | 直接运行验证命令 |

## Expected Final Status

```
VERIFIED — 所有 expected_files 存在，evidence 项全部通过
```

## 测试步骤

```bash
# 1. 初始化任务
python3 .claude/scripts/carros_base.py init --task-id bench-04-failure-repair

# 2. 执行 S1 — 触发失败（示例：故意运行一个不存在的命令）
python3 .claude/scripts/carros_base.py tick --step S1
# 手动或通过 script 注入失败：some-unreliable-command && false
# 检查 token.json state 变为 failed

# 3. 执行 S2 — 修复
# 修改或重跑失败的命令，记录修复过程到 executor.md
# python3 .claude/scripts/carros_base.py tick --step S2

# 4. 执行 S3 — 重新验证
python3 .claude/scripts/carros_base.py verify --step S1
# 预期输出：VERIFIED

# 5. 执行 S4 — 归档
python3 .claude/scripts/carros_base.py archive

# 6. 验证审计迹
cat .omc/tasks/{date}/{task_id}/state/audit/*.jsonl | grep -E 'step_failure|step_verify|step_repair'
```

## 失败场景示例

| 失败类型 | 注入方式 | 修复方式 |
|----------|----------|----------|
| 命令退出码非零 | `false` 或 `exit 1` | 替换为正确命令 |
| 产物缺失 | 删除生成文件 | 重新生成 |
| 验证不通过 | 修改校验规则使其不匹配 | 修正产物或规则 |
| 超时 | 注入 `sleep 300` | 缩短超时或优化命令 |
| 依赖缺失 | 移除关键依赖文件 | 恢复依赖 |

## 验收清单

- [ ] S1 失败后 `token.json.state` 为 `failed`
- [ ] executor.md 记录了失败错误信息
- [ ] S2 修复后 `token.json.state` 为 `repairing`
- [ ] S3 verify 输出 `VERIFIED`
- [ ] plan.md 中 S1 标记从 FAILED 变为 DONE
- [ ] audit JSONL 包含完整 failure→repair→verify 链条
- [ ] archive 成功，无残留状态
