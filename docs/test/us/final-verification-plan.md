# Carror OS 交叉验收流程 — 终验方案

> 验证 A→B→A 双终端交叉验收流程的完整闭环

## 变更清单

| 文件 | 改动 |
|------|------|
| `.claude/hooks/completion-gate.sh:73-120` | A→B→A 交叉验收提醒 + 两阶段关键词匹配 + 自动写手off文件 |
| `AGENTS.md` | 铁律 #7（断言真实）+ 工作流原则 6 + 交接格式规范 |
| `VERSION.json` | 新建，版本号单源 `6.1.8` |
| `.claude/claude-next.md` | R27 hits: 1→2 |
| `docs/test/cross-verify-test-plan.md` | 测试方案修正 |

## 核心断言

1. **两阶段关键词匹配**：高精确率词（验收/通过率/benchmark）单命中即触发；中精确率词（报告/方案/评估）需 ≥2 命中
2. **`计划` `标准` 已移除**：不再因日常用语误触发
3. **`review analysis 评审 分析` 已补充**：覆盖更多验收场景
4. **手off文件自动写入**：`.omc/state/cross-verify-handoff.md` 含任务描述 + 近期文件列表
5. **`*****` 格式固化**：身份标记（A 方案方 / B 验收方）+ 边界线 + 返回报告占位

## 验证步骤

```bash
cd /Users/lucas.liang/Desktop/Sylph/Carror_OS

# TC-1：日常任务不应触发
printf '按计划完成重构，符合代码标准, VERIFIED' > /tmp/ev
echo '{"tool_input": {"status": "completed"}}' | bash .claude/hooks/completion-gate.sh 2>&1 | grep -c "交叉验收提醒"
# 期望输出: 0

# TC-2：中精确率词 ≥2 应触发
printf '评估并分析方案终验结果, VERIFIED' > /tmp/ev
echo '{"tool_input": {"status": "completed"}}' | bash .claude/hooks/completion-gate.sh 2>&1 | grep -c "交叉验收提醒"
# 期望输出: 1

# TC-3：高精确率词单命中应触发
printf '通过率报告已完成, VERIFIED' > /tmp/ev
echo '{"tool_input": {"status": "completed"}}' | bash .claude/hooks/completion-gate.sh 2>&1 | grep -c "交叉验收提醒"
# 期望输出: 1
```

## 验收标准

- [ ] TC-1 不触发（计划/标准 已移除）
- [ ] TC-2 触发（方案+评估+分析 ≥2）
- [ ] TC-3 触发（通过率 高精确率）
- [ ] 手off文件自动生成 `.omc/state/cross-verify-handoff.md`
