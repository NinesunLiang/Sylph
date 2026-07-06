---
name: lx-root-cause-analysis
version: v4.0.0
description: "Trace recurring Go bugs via Five Whys: evidence chains → confidence scoring → immunity defense."
complexity: intermediate
when_to_use: "Use when bug recurs after fix, systematic debugging failed, or user says 'root cause', 'keeps happening'."
argument-hint: "<recurring bug symptom and history>"
harness_version: ">=6.3.0"
status: mature
role: "Five Whys root cause analysis for recurring Go bugs"
execution_mode: stepwise
triggers:
  - "/lx-root-cause-analysis"
  - "root cause"
---
# lx-root-cause-analysis — 五层 Why + 免疫防护

> **侦探 → 免疫设计师。** 证据链发现根因 → 三重防护免疫复现。

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| target_resolver | `../../nodes/target_resolver.md` | 定位 bug 代码 |
| context_collector | `../../nodes/context_collector.md` | 收集历史 |
| report_generator | `../../nodes/report_generator.md` | RCA 报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 研究阶段约束 |
| verifier | `../../nodes/verifier.md` | finding 质量验证 |

Schema: scan_target / context_summary / finding / verdict → `../../schemas/atomic/`

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/anti-patterns.md` | anti patterns 阶段 |
| `references/confidence-scoring.md` | confidence scoring 阶段 |
| `references/go-root-cause-patterns.md` | go root cause patterns 阶段 |
| `references/oracle-escalation.md` | oracle escalation 阶段 |
| `references/phase-five-whys.md` | phase five whys 阶段 |
| `references/phase-fix-immunity.md` | phase fix immunity 阶段 |
| `references/rca-feedback-template.md` | rca feedback template 阶段 |
| `references/repair-loop-rules.md` | repair loop rules 阶段 |
| `references/tool-output-rules.md` | tool output rules 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
症状收集 → 证据链构建 → 5-Why 根因 → 置信度评分 → 免疫防御
```

## 入口检查

```bash
ls go.mod                       # 缺失 → 不适用
grep "go-zero" go.mod           # 存在 → go-zero 模式
```

## 执行步骤

### Phase 1: 症状映射

Agent A（历史 + 已知模式）：git log / claude-next.md → 匹配已知模式
Agent B（故障链）：错误日志 → 数据流追踪 → `go test -race`

Go 模式 → `references/go-root-cause-patterns.md`

### Phase 2: 断点隔离

精确定位预期 vs 实际行为的分叉点。LSP hover/references / ast-grep / go test -race / pprof。

CP-2 检查点：故障链 → 断点 → 直接原因 → 并发评估 → 初始置信度 [N]/5

### Phase 3: 五层 Why + 证据链 → `references/phase-five-whys.md`

每层 Why 必填：答案 + 工具 + 原始输出 + 证据类型 + 解读 + 反事实验证 + 一致性。

置信度 5 维 × 5 分 = 25 分。≥18 → Phase 4，13-17 → Oracle，<13 → 中止。

CP-3 检查点：故障链 → 断点 → 根因 → 置信度 → 修复目标 file:line

### Phase 4-5: 修复 + 免疫 → `references/phase-fix-immunity.md`

根因级修复（不修症状）→ 三重防护（测试/验证/监控）→ 经验反哺 claude-next.md。

## 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| go test -race 不稳定 | 并发根因 | count=50 → count=10 + 人工 |
| 5-Why 第3层无进展 | 根因分析 | 标注 [根因待定] + 升级 |

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/go-root-cause-patterns.md` | Go 症状搜索命令 |
| `references/confidence-scoring.md` | 5 维置信度评分标准 |
| `references/tool-output-rules.md` | 工具输出引用规则 |
| `references/anti-patterns.md` | 修复反模式 |
| `references/repair-loop-rules.md` | 修复循环规则 |
| `references/checklists/danger-signals.md` | 修复前危险信号 |
| `references/oracle-escalation.md` | Oracle 升级协议 |
| `references/rca-feedback-template.md` | 经验反哺模板 |
