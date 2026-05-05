# Oracle 升级协议

## 触发条件

- Phase 3 完成后根因置信度为 13-17/25
- 同一根因修复失败 2 次以上（预防性升级）
- 修复循环到达第 4 轮（强制升级）

## Oracle Agent

```
Task(subagent_type="oh-my-claudecode:architect", model="opus")

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
Hypotheses under consideration:A) [hypothesis A with evidence for/against]B) [hypothesis B with evidence for/against]C) [hypothesis C with evidence for/against]
Request: Based on Go runtime behavior and [framework] architecture constraints, determine the true root cause.
```

## Oracle 后续动作

1. 以 Oracle 的结论更新 Phase 3 根因结论
2. 用新证据重新计算置信度
3. 若置信度 ≥ 18 → 进入 Phase 4
4. 若仍 < 18 → 调查终止，输出阻断模板

## Artistry Agent（用于并发专项根因）针对竞态条件、跨进程状态污染、分布式时序问题：

```
Task(subagent_type="oh-my-claudecode:scientist-high", model="opus")

```
使用相同提交模板，重点强调并发专项证据。

## 关键规则

- Oracle 输出不可自动信任——必须通过相同质量关卡（G06-G16）
- Oracle 工具输出引用遵循相同规则（原始输出 → 解读）
- 反模式 X14：Oracle 咨询后未更新根因 → 强制重走 Phase 3-5
