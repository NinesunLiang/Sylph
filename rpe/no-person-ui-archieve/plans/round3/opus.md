**Opus 审核：契约强制与证据完整性视角**

读取了 GAP-FIX-REPORT.md，但 `orchestrator.py` 文件404。基于报告文本进行审核：

---

## 核心判定：不通过验收

**原因：报告声称完成 13/13 修复，但只提供了 10项的可审计条目（GAP 1-9, 12），缺失 GAP 10/11/13。在提供完整材料之前，无法给出 GO判决。**

---

## 关键审核发现（按契约完整性分类）

### 一、报告完整性缺陷（阻断性）

**F-1: 声称与证据不匹配**
```yaml
claimed: "13/13 Critical Gaps Fixed"
documented: GAP 1-9, GAP 12 (共 10 项)
missing: GAP 10, GAP 11, GAP 13
```

验收前必须补充：
- GAP 10的问题描述、修改文件、测试结果
- GAP 11 的问题描述、修改文件、测试结果  
- GAP 13 的问题描述、修改文件、测试结果

或者，如果编号错误，修正报告使声称数量与实际条目一致。

**审计原则**：报告本身是验收契约的一部分，报告不自洽则审计无效。

---

### 二、Gate Chain 强制执行（P0 级风险）

<thinking>
报告说GAP 2 修复了 Gate Chain，实现了完整的 C1-C8a。但我需要验证的核心问题是：这个 Gate Chain 是否在 accept路径上强制执行，还是可以被绕过。
</thinking>

**F-2: Gate强制执行证明缺失**

报告声称：
```python
# GAP 2: Gate Chain Implementation (P0)
# File: orchestrator.py:440-690
# Fix: Full C1-C8a implementation with control_plane_lock
```

但未回答关键问题：

1. **调用强制性**：`_run_gates()` 是否是 accept 的唯一路径？
   - accept 决策是否只能来自 `orchestrator._run_gates()` 的返回值？
   - 外部调用者能否注入 `gate_results` 字典绕过实际 Gate 执行？

2. **Fail-closed 保证**：
   - Gate脚本不存在 → fail还是 skip？
   - Gate 超时 → fail 还是 warn？
   - Gate抛异常 → fail 还是 partial？
   - Evidence 文件缺失 → fail 还是默认 pass？

3. **原子性**：
   - Patch 是否先apply 到隔离 worktree？
   - Gate fail 后是否原子回滚？
   - 还是 patch 已经进入主worktree，依赖手动清理？

**验收要求**：
```python
#必须证明以下控制流
def tick():
    patch = generate_patch()
    gate_results = self._run_gates(patch)  # 唯一 Gate 执行点
    if not gate_results.all_passed:
        rollback_atomic()# 原子回滚
        returncommit_and_checkpoint()

#禁止以下模式
def external_accept(patch, claimed_gates: dict):
    # ❌ 外部传入 gate_results
    if claimed_gates["C1"] and claimed_gates["C2"]:
        apply_patch()
```

没有代码或运行日志证明，这条 fail-closed 链路处于"不可绕过"状态。

---

### 三、测量链完整性（P0 级风险）

**F-3: 测量生产者与评分引擎的端到端链路未证明**

报告声称：
```
GAP 3: Measurement Producers
Files: measure_prototype.py (new), measure_implementation.py (new)
Impact: ScoringEngine computes D1-D7 from real browser measurements
```

但"ScoringEngine computes D1-D7 from real browser measurements"这个结论的证据链是：

```
prototype screenshot →??? → D1-D5 gold measurements
implementation HTML → Playwright → D1-D5 candidate measurements
??? → D6token alignment
??? → D7 interaction coverage
scoring_engine.py → composite_score()
```

<thinking>
关键问题是：
1. 静态截图如何产生 computed styles？需要 OCR 还是有可运行的原型？
2. D6 Token Alignment 来自哪里？需要 AST parser 提取token 使用并与声明比对
3. D7 Interaction Coverage 需要 assertion catalog 和 runner，报告没提
4. C6 Visual Check 需要截图 diff 和区域mask，报告没说实现细节
</thinking>

缺失的证据：
1. **Prototype 测量源**：
   - 如果 prototype 是静态截图 → 无法用Playwright 提取 computed styles
   - 如果 prototype 是可运行页面 → 需要说明构建过程
   - 如果用CV/OCR 推断 → 需要说明推断器和置信度阈值

2. **D6 Token Alignment**：
   - 需要 token 声明 catalog（`src/styles/tokens/source/`）
   - 需要 usage extractor（AST parser 提取 `token.*` 引用）
   - 需要 matcher（声明 vs 使用）
   - 报告未提及任何相关脚本

3. **D7 Interaction Coverage**：
   - 需要 assertion catalog（hover/scroll/dismiss/overlay assertions）
   - 需要 interaction runner（Playwright automation）
   - 需要 evidence collector（assertion results → coverage ratio）
   - 报告架构图列出 C4/C5，但没有 D7 专用runner

**验收要求**：
提供至少一次完整的测量产物，证明：
```json
{
  "run_id": "...",
  "page": "HomePage",
  "region": "Header",
  "prototype_measurements": {
    "source": "screenshots/HomePage-Header-prototype.png",
    "method": "playwright_on_static_build | ocr_cv_inference",
    "D1_layout": {...},
    "D2_typography": {...},
    "D3_color": {...},
    "D4_spacing": {...},
    "D5_border_shadow": {...}
  },
  "implementation_measurements": {...},
  "D6_token_alignment": {
    "declared_tokens": 47,
    "used_tokens": 45,
    "coverage": 0.957
  },
  "D7_interaction_coverage": {
    "total_assertions": 8,
    "passed_assertions": 6,
    "coverage": 0.75
  },
  "composite_score": 0.87
}
```

---

### 四、Checkpoint恢复契约（P1 级风险）

**F-4: 时间契约的跨进程可恢复性未证明**

报告声称：
```
GAP 4: Time Consistency
Fix: Changed all timers to time.monotonic()
Impact: Immune to clock adjustments
```

`time.monotonic()` 适合**单进程内**计算duration，但不适合作为**可持久化契约**：

```python
# ❌ 错误模式
start_mono = time.monotonic()
deadline_mono = start_mono + budget
checkpoint.save({"deadline": deadline_mono})

#进程重启后
restored_deadline = checkpoint.load()["deadline"]
remaining = restored_deadline - time.monotonic()# ❌ 错误：monotonic 基准已重置
```

正确模式：
```python
# ✅ 可持久化
start_utc = datetime.now(timezone.utc)
deadline_utc = start_utc + timedelta(seconds=budget)
budget_spent = 0

# 每个阶段结束
budget_spent += time.monotonic() - phase_start_mono
checkpoint.save({
    "deadline_utc": deadline_utc.isoformat(),
    "budget_spent_seconds": budget_spent
})

# 恢复
remaining = (deadline_utc - datetime.now(timezone.utc)).total_seconds() - budget_spent
new_deadline_mono = time.monotonic() + remaining
```

**验收要求**：
提供 `RunState` 的时间字段定义和 restore逻辑，证明：
- checkpoint 不持久化进程本地monotonic 值
- 或者，如果持久化 monotonic，证明恢复算法考虑了基准重置

---

### 五、Token边界冻结（P1 级风险）

**F-5: Token source 冻结边界未完全闭合**

报告声称：
```
GAP 8: Phase Pattern Deduplication
Impact: Includes Grok G-P0-2 fix (POLISH excludes tokens/source)
```

这修复了 POLISH 阶段，但未说明 **TOKENS 阶段**的边界：

```python
# phase_rules.py 应该明确
TOKENS_PHASE_ALLOWED = [
    ".omc/ui-autopilot/{run_id}/token-proposals/**",  # ✅ 只能写建议
    "artifacts/**/token-analysis.yaml"# ✅ 只读分析
]

# 禁止
TOKENS_PHASE_PROHIBITED = [
    "src/styles/tokens/source/**",  # ❌ 不能修改 source
    "src/styles/tokens/generated/**"  # ❌ 不能修改 generated
]
```

**验收要求**：
提供 `phase_rules.py` 完整内容，证明：
- TOKENS 阶段只能输出proposals，不能修改 source/generated
- POLISH 阶段不能访问 tokens/**
- 违规时 C1Scope Check fail

---

### 六、6 小时无人运行保证（P0 级风险）

**F-6: Host 可靠性未证明**

架构图写：
```
Host: Claude Code Main Session (DeepSeek V4 Pro)
  ├── lx-goal (autonomous executor)
  └── ScheduleWakeup (6h overnight run)
```

但未说明：
1. **Session 断开后**任务是否继续？
   - Claude Code Main Session 依赖 WebSocket/HTTP 长连接
   - 连接断开后，`lx-goal` 是否仍在运行？
   - 还是需要重新 `lx-goal` 触发 resume？

2. **ScheduleWakeup** 是什么？
   - 是否是持久化调度器（cron/systemd timer）？
   - 还是 Main Session 内的`time.sleep()`？
   - 如果是后者，Session 断开即失效

3. **Checkpoint 恢复谁触发**？
   - 是否有 watchdog/supervisor 进程？
   - 还是依赖人工重新启动？

**验收要求**：
证明以下场景的恢复路径：
```yaml
scenario_1:
  event: "Main Session WebSocket 断开"
  expected: "后台任务继续 tick，或supervisor 自动重启"
  
scenario_2:
  event: "模型请求超时 5分钟"
  expected: "watchdog kill 并resume，或 timeout 机制 fail该tick"
  
scenario_3:
  event: "DeepSeek V4 Pro 账号配额耗尽"
  expected: "ModelRouter 降级到 Kimi，或 graceful shutdown 保留 audit预算"
```

没有这些证明，"6h unattended"只是理论可能，不是工程保证。

---

### 七、周期 Checkpoint 的损失边界（P1 级风险）

**F-7: "最多损失 1 分钟"结论不成立**

报告声称：
```
GAP 9: Periodic Checkpoint
Fix: Save checkpoint every CHECKPOINT_EVERY_SECONDS (60s)
Impact: Maximum 1min work loss on crash
```

这个结论只在"tick每 60 秒内返回"时成立。实际场景：

```python
# tick 可能包含
model_call = request_claude_opus()# 耗时 2-10 分钟
playwright_measure = run_playwright()  # 耗时 30-120秒
gate_compile = run_tsc()  # 耗时 10-60 秒
gate_playwright = run_gate_script()  # 耗时 30-90 秒
```

如果一个 tick 耗时 10 分钟，主线程阻塞在模型调用，60 秒周期检查不会触发。

**正确实现**应该：
1. **每个阶段边界** checkpoint（patch apply前后、Gate 执行前后、accept/reject 后）
2. **长任务异步化** + 独立 heartbeat（模型调用、Playwright、Gate 脚本都有独立状态持久化）
3. **Timeout 机制** + watchdog（超时则 checkpoint 当前状态并fail）

**验收要求**：
将结论修改为：
```
空闲或短tick 下，周期 checkpoint 间隔 60 秒；
实际恢复点受单个阻塞操作时长影响；
长任务（模型调用/Gate 脚本）有独立 timeout 和 checkpoint 机制。
```

---

## 缺失的材料清单

要完成代码级审核，需要提供：

```yaml
code_files:
  - orchestrator.py (完整代码，特别是 _run_gates(), tick(), restore)
  - phase_rules.py (完整 PHASE_ALLOWED/PROHIBITED patterns)
  - measure_prototype.py
  - measure_implementation.py
  - convergence.py (to_dict/from_dict 实现)
  - domain.py (RunState.convergence_state 定义)

artifacts:
  - .omc/ui-autopilot/{run_id}/checkpoint-*.json (至少一个完整 checkpoint)
  - .omc/ui-autopilot/{run_id}/measurements/*.json (至少一个完整测量产物)
  - .omc/ui-autopilot/{run_id}/gate-results/*.json (至少一次Gate 执行结果)

test_results:
  - 一次 accept 的完整日志
  - 一次 Gate reject + rollback 的日志
  - 一次 checkpoint + resume 的日志
  - 一次 Token source 越权拦截的日志

missing_gaps:
  - GAP 10 完整说明
  - GAP 11 完整说明
  - GAP 13 完整说明
```

---

## 最终判决

```yaml
report_integrity: FAIL (10/13 documented, 3missing)
gate_enforcement: UNVERIFIED (code404, no fail-closed proof)
measurement_chain: UNVERIFIED (D6/D7 producers missing)
checkpoint_contract: UNVERIFIED (monotonic cross-process issues)
token_freeze: PARTIALLY_VERIFIED (POLISH fixed, TOKENS boundary unclear)
six_hour_host: UNVERIFIED (no session/supervisor reliability proof)

verdict: CONDITIONAL_GO_DRY_RUN_ONLY
restrictions:
  - 禁止真实 overnight 6h 运行
  - 禁止 Token source 写权限
  - 仅允许 30 分钟监督下dry-run
  - 至少覆盖：1 accept + 1 reject + 1 resume + 1 scope violation
```

**下一步**：补齐上述材料后，我进行终审。重点关注：
1. Gate Chain 的fail-closed 调用链
2. D6/D7 的完整测量管道
3. Checkpoint 恢复的时间契约正确性
4. 至少一次完整 dry-run 的所有 artifacts