# Oracle 升级协议

## 触发条件

- Phase 3 完成后根因置信度为 13-17/25
- 同一根因修复失败 2 次以上（预防性升级）
- 修复循环到达第 4 轮（强制升级）

## Oracle Agent

```
Task(subagent_type="oh-my-claudecode:architect")
```

## 提交模板

以如下结构（自然语言，非 JSON）提交给 Oracle：

```
Context: [Go version] project ([framework] framework), [symptom] has been fixed [N] times but recurs.
Investigation summary:
- Phase 1 symptoms: [symptom summary + timeline]
- Phase 2 breakpoint: [isolation result]
- Phase 3 Five Whys: [Why chain summary with evidence]
- Confidence: [X]/25 (shortfall dimensions: [list])
- -race report: [paste if applicable]
- goroutine count: [if applicable]
Hypotheses under consideration:
A) [hypothesis A with evidence for/against]
B) [hypothesis B with evidence for/against]
C) [hypothesis C with evidence for/against]
Request: Based on Go runtime behavior and [framework] architecture constraints, determine the true root cause.
```

## Oracle 后续动作

### 裁决判定

| 裁决 | 含义 | 后续动作 |
|------|------|---------|
| ACCEPT | Oracle确认根因正确 | 继续Phase4，用Oracle证据更新置信度 |
| REJECT | Oracle认为根因不正确 | 置信度≥15→再尝试1次修正假设后提交；<15→ABORT，退出报告标记"Oracle rejected" |
| ESCALATE | Oracle也无法确定 | 记录blocked_human，退出报告汇总需人为决策项 |

### 超时处理

Oracle审核等待超时30秒 → 降级为ADVISORY → 允许继续但标记低置信度。

ADVISORY 行为：允许继续执行Phase4，但必须标记"低置信度修复"，并在退出报告中突出显示。

## Artistry Agent（用于并发专项根因）

针对竞态条件、跨进程状态污染、分布式时序问题：

```
Task(subagent_type="oh-my-claudecode:scientist-high")
```

使用相同提交模板，重点强调并发专项证据。

## 关键规则

- Oracle 输出不可自动信任——必须通过相同质量关卡（G06-G16）
- Oracle 工具输出引用遵循相同规则（原始输出 → 解读）
- 反模式 X14：Oracle 咨询后未更新根因 → 强制重走 Phase 3-5
