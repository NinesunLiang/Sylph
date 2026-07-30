**审核结论：报告层面不通过“13/13 已修复”的验收，当前最多是 `CONDITIONAL-GO`，允许进入受限 Volume-0 dry-run，不足以批准 6h 无人夜跑。**

原因不是报告中的方向错误，而是它主要证明了“代码被修改”，尚未证明修改后的运行链在真实环境中完成过 `修改 → Gate → 重评分 → 接受/回滚 → checkpoint → resume`。以下是按严重性排序的审核发现。

**P0 Findings**

1. **“13/13”与报告正文无法核对**

报告的 GAP Summary 只列出了：

```text
GAP 1–9
GAP 12
```

也就是 10 项。`GAP 10`、`GAP 11`、`GAP 13` 没有可审计条目，无法确认所谓 13/13。

验收前需要补：

```text
GAP 10：问题、修改文件、函数/行号、测试
GAP 11：问题、修改文件、函数/行号、测试
GAP 13：问题、修改文件、函数/行号、测试
```

如果只是编号遗漏，也应修正报告，否则报告不能作为审计基线。

2. **报告声称 Gate Chain 已完成，但没有证明它处于不可绕过的 accept 路径**

`orchestrator.py:_run_gates()` 从 placeholder 改为 C1–C8a 是重要进展，但报告没有说明：

- `_run_gates()` 的唯一调用点；
- patch 是否先进入隔离 worktree；
- Gate fail 后是否原子回滚；
- Gate timeout、脚本异常、envelope 缺失是否全部 fail-closed；
- `action_result.gate_results` 是否仍可由外部 session 直接注入；
- accept/commit 是否存在绕开 `_run_gates()` 的路径。

核心验收条件应是：

```text
所有 accept
  必须来自 orchestrator 自己执行的 GateEnvelope
  不能信任调用方传入的布尔 gate_results
```

否则外部 Host 仍能提交：

```json
{"gate_results":{"C1":true,"C2":true,"C3":true,"C7":true}}
```

进而绕过真实 Gate。

3. **“Measurement Producers”不足以证明 D1–D7 来自真实测量**

报告只描述两个 Playwright computed-style extractor：

```text
measure_prototype.py
measure_implementation.py
```

computed style 可以支持 D1–D5 的一部分，但不能天然证明：

- D6 TokenAlign 来自源码声明和 `token-index`；
- D7 Interaction 来自 assertion catalog 的真实执行；
- 截图视觉相似度、区域 mask 和 C6 已实现；
- hover、scroll、overlay、dismiss 等状态被采集；
- 静态原型截图如何产生 computed styles。

特别需要澄清 `prototype` 的来源：

- 如果 prototype 是可运行页面，Playwright 可提取 computed styles；
- 如果 prototype 是静态截图，无法从图片直接取得 CSS computed styles；
- 如果使用 OCR/CV 推断，报告必须说明推断器和置信度。

目前“ScoringEngine computes D1-D7 from real browser measurements”这个结论证据不足。

4. **D7 交互链仍未在报告中闭环**

报告架构图列出 C4/C5，但没有列出：

```text
assertion catalog loader
interaction runner
trigger 执行
predicate 验证
assertion evidence
D7 covered/total 回灌
```

仅有 Playwright style extraction 不等于交互覆盖。

必须提供一次真实产物，证明至少包括：

```text
hover → overlay visible
Escape/outside click → overlay dismissed
scroll → end-state reached
assertion results → set_interaction_coverage()
D7 < 1 → composite cap 0.94
```

否则 UIF-99 中权重最大的 D7 仍只是字段。

5. **6h Host 依赖 Claude Code Main Session，仍缺少宿主可靠性证明**

架构图写的是：

```text
Claude Code Main Session
  ├── lx-goal
  └── ScheduleWakeup
```

但没有证明：

- Main Session 断开后任务是否继续；
- `ScheduleWakeup` 是否是持久化调度器；
- Host 崩溃后谁调用 restore；
- 模型请求挂起是否有 timeout/watchdog；
- resume 是否重新建立 monotonic deadline；
- 最终审计预留时间是否被保留。

因此当前系统可能是“可持续 tick 的状态机”，但尚未证明是“6h 无人运行系统”。

**P1 Findings**

6. **全部计时改成 `time.monotonic()`可能破坏跨进程 checkpoint 恢复**

`monotonic()`适合单进程内计算 duration，但不应无条件作为持久化截止时间。

需要区分：

```python
# 可持久化
started_at_utc
deadline_at_utc
budget_spent_seconds

# 仅当前进程有效
process_started_monotonic
last_checkpoint_monotonic
```

如果 checkpoint 保存的是：

```python
deadline_monotonic = start_monotonic + budget
```

那么进程重启、系统重启或运行环境迁移后，它不能作为可靠的恢复依据。尤其系统重启会重置 monotonic 时钟基准。

推荐恢复算法：

```text
remaining =
  configured_budget
  - persisted_budget_spent
  - elapsed_since_last_checkpoint_by_wall_clock

新进程再建立：
  local_deadline_monotonic = monotonic() + remaining
```

报告需给出 `RunState` 时间字段及 restore 代码，证明没有把进程本地 monotonic 值当作跨启动契约。

7. **60 秒周期 checkpoint 不等于最多损失 1 分钟工作**

报告写：

> Maximum 1min work loss on crash

这个结论只有在 tick 每 60 秒内返回时成立。若一个模型调用、Playwright、构建或 Gate 执行耗时 10 分钟，主线程里的周期检查不会运行。

生产实现至少需要：

- 每个阶段开始和完成时 checkpoint；
- patch apply 前后 checkpoint；
- accept/reject 后立即 checkpoint；
- 模型调用和 Gate 有 timeout；
- 长任务状态单独持久化；
- 必要时由独立 heartbeat/watchdog 写活性状态。

应把报告结论改成：

```text
空闲或短 tick 场景下，周期 checkpoint 间隔为 60 秒；
实际恢复点还受单个阻塞操作时长影响。
```

8. **Token source 的 POLISH 漏洞据称已修，但 ProposeToken 目标未说明**

报告确认：

```text
POLISH excludes tokens/source
```

这是正确修复，但还需要核实：

```text
generate_propose_token_task.allowed_files
```

此前实现允许：

```text
src/styles/tokens/source/**
```

正确目标应是类似：

```text
.omc/ui-autopilot/<run>/proposals/**
artifacts/.../token-proposals.yaml
```

夜间 ProposeToken 必须只输出建议，不能获得 source 写权限。报告只说明了 POLISH，不足以证明整个 Token 冻结边界已经关闭。

9. **`patch_validator` 的行数修复可能存在 off-by-one**

从：

```python
len(text)
```

改为：

```python
text.count("\n")
```

确实从字符数变成了换行符数，但它不等于严格行数：

```python
"one line"       → 0 个换行符，实际 1 行
"a\nb"           → 1 个换行符，实际 2 行
"a\nb\n"         → 2 个换行符，通常视为 2 行
```

更稳妥的表达是：

```python
line_count = len(text.splitlines())
```

还需明确限制的是：

- patch JSON 文本行数；
- diff 新增行数；
- `before + after` 总行数；
- 所有 changed files 的累计变更行数。

如果目标是限制 patch blast radius，应该统计 diff 的新增与删除行，而不是序列化字符串行数。

10. **Phase 规则去重正确，但需验证规则消费者使用相同匹配语义**

把规则集中到 `phase_rules.py` 解决了定义重复，但仍需检查：

- `phase_gate.py` 和 `task_generator.py` 是否都用相同 glob matcher；
- 路径是否先 `resolve()` 并相对 target repo 规范化；
- 是否拒绝 `../`、symlink escape、大小写差异；
- untracked files 是否纳入 scope；
- prohibited 规则是否优先于 allowed；
- 空 allowed patterns 是否 fail-closed。

“共享常量”不自动等于“共享授权语义”。

11. **C8a 与 C7/H2 的职责可能循环或重复**

报告描述：

```text
C7 Evidence Check
C8a Finalize Gate — H1+H2 hard gates
```

而 UIF `H2` 本身又是 evidence pass。需明确：

```text
C7 产生 evidence envelope
H2 从可信 C7 envelope 派生
C8a 只消费 H1/H2，并验证 run/page 状态
```

C8a 不应自己再构造或默认 H2，也不应允许普通 patch acceptance 依赖“最终 evidence”而形成循环。建议区分：

```text
Patch acceptance: C1-C6 + patch evidence
Page finalize: C1-C7 + UIF goal + coverage
Run finalize: C8a
```

**P2 Findings**

12. **“atomic evidence”没有说明原子性边界**

报告需要定义原子性究竟是：

- 临时文件 + `os.replace()`；
- 一个 patch transaction ID 下的完整 evidence set；
- evidence 与 commit SHA 绑定；
- checkpoint 与 score 同时提交。

建议每轮产物至少绑定：

```json
{
  "run_id": "...",
  "iteration": 12,
  "task_id": "...",
  "base_sha": "...",
  "candidate_sha_or_diff_hash": "...",
  "gate_contract_version": "...",
  "measurement_config_hash": "...",
  "token_set_hash": "..."
}
```

否则证据可能属于前一轮代码，却被后一轮 finalize 消费。

13. **报告缺少测试结果和真实运行结果**

一份 Fix Report 至少应列出：

```text
测试命令
通过/失败数量
耗时
一次 reject + rollback
一次 accept + commit/checkpoint
一次 crash + resume
一次 D7 不满导致 0.94 cap
一次 Token source 越权被拒
一次 Kimi cap 耗尽后的降级
```

目前 Executive Summary 是实现声明，不是验收证据。

**建议判决**

```yaml
report_integrity: FAIL
static_implementation_claims: PARTIALLY_VERIFIED
token_freeze: PARTIALLY_VERIFIED
uif99_formula: PREVIOUSLY_VERIFIED
uif99_measurement_chain: UNVERIFIED
interaction_chain: UNVERIFIED
gate_enforcement: UNVERIFIED
checkpoint_resume: PARTIALLY_VERIFIED
six_hour_host: UNVERIFIED

verdict: CONDITIONAL_GO_VOLUME_0_ONLY
allow_6h_unattended: false
allow_token_source_write: false
```

下一轮不需要再补设计说明。请直接补以下材料，我可以继续做代码级终审：

1. 修改后的 `orchestrator.py`，重点是 `tick()`、`_run_gates()`、accept/reject、restore。
2. `measure_prototype.py`、`measure_implementation.py` 和一次真实输出。
3. assertion catalog、interaction runner、D7 回灌调用点。
4. `phase_rules.py` 与修改后的 `generate_propose_token_task()`。
5. `state_store.py`、时间字段和 checkpoint 样例。
6. 一次最小 dry-run 的完整 `.omc/ui-autopilot/<run_id>/`。
7. 修正后的 GAP 10、11、13 说明及测试汇总。

最小 Volume-0 验收应覆盖：**1 页、2 状态、3 Region、1 次 accept、1 次 Gate reject 并回滚、1 个 hover/overlay、1 个 scroll-end、1 次 checkpoint+resume、1 次 Token source 越权拦截**。这些全部有 artifacts 后，才能从 `CONDITIONAL-GO` 升到 `GO-VOLUME-0`。