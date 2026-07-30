# GPT-5.6 Sol 终审

## 最终判决

```yaml
reviewer: gpt-5.6-sol
decision:
  production_overnight_6h: NO_GO
  supervised_dry_run: NO_GO_UNTIL_P0_FIXED
  architecture_direction: CONDITIONAL_ACCEPT

confirmed_blockers:
  - tick() 存在确定性 NameError
  - 跨进程时间预算实现错误
  - Gate 结果仍跨越不可信的 action_result 边界
  - checkpoint 只恢复状态，不恢复代码
  - Token 权限规则自相矛盾
  - 测量器不足以支撑报告声称的 D1-D7
  - 6h 执行仍依赖外部会话，没有持久化 supervisor

report_verdict:
  "13/13 Critical Gaps Fixed": REJECTED
```

这不是“证据暂时不足”的保守结论。上传的代码已经包含可以确定复现的 P0 问题。

---

## P0-1：`tick()` 会直接触发 `NameError`

[`orchestrator.py`](https://r2.xsimple-r2.com/files/495944/4bf54d26-1eba-4886-aabd-8b99de1e0481.py) 的 import：

```python
from .config import (
    PROJECT_ROOT,
    ensure_run_dir,
    get_run_dir,
    DEFAULT_TARGET_REPO,
    DEFAULT_WALL_CLOCK_SECONDS,
    MAX_TARGET_ATTEMPTS,
    MAX_CONSECUTIVE_NO_PROGRESS,
    MAX_VISUAL_CALLS,
    DEFAULT_MODEL,
)
```

但 `tick()` 使用了：

```python
if self.state.iteration >= MAX_TOTAL_ITERATIONS:
```

`MAX_TOTAL_ITERATIONS` 没有导入。只要进入非终态的 `tick()`，这一行就会抛出：

```text
NameError: name 'MAX_TOTAL_ITERATIONS' is not defined
```

### 最小修复

```python
from .config import (
    PROJECT_ROOT,
    ensure_run_dir,
    get_run_dir,
    DEFAULT_TARGET_REPO,
    DEFAULT_WALL_CLOCK_SECONDS,
    MAX_TARGET_ATTEMPTS,
    MAX_CONSECUTIVE_NO_PROGRESS,
    MAX_TOTAL_ITERATIONS,
    MAX_VISUAL_CALLS,
    DEFAULT_MODEL,
    CHECKPOINT_EVERY_SECONDS,
)
```

同时把 `CHECKPOINT_EVERY_SECONDS` 从 `tick()` 内部 import 移至模块顶部。

**判定**：当前版本连基础 dry-run 都不应放行。

---

## P0-2：跨进程时间预算确定错误

当前初始化逻辑：

```python
self.controller = LoopController(
    target_threshold=0.99,
    deadline_epoch=(
        self.state.wall_clock_start
        + self.state.wall_clock_budget_seconds
        if self.state.wall_clock_start > 0
        else time.monotonic() + DEFAULT_WALL_CLOCK_SECONDS
    ),
)
```

`tick()`：

```python
elapsed = time.monotonic() - self.state.wall_clock_start

if (
    self.state.wall_clock_start > 0
    and elapsed > self.state.wall_clock_budget_seconds
):
    self.state.status = RunStatus.EXHAUSTED
```

这里把 `wall_clock_start` 当成 monotonic 起点持久化。该值只能在当前系统启动周期内用于相对计时，不能作为可恢复 deadline。

后果包括：

- 进程或机器重启后，monotonic 基准可能变化；
- checkpoint 恢复后可能立即超时；
- 也可能获得错误的额外运行时间；
- `deadline_epoch` 这个命名还会误导调用者把 monotonic 值当 Unix epoch。

### 正确实现

持久化 UTC deadline，进程内 watchdog 才使用 monotonic：

```python
from datetime import datetime, timedelta, timezone

def utc_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


def initialize_budget(state: RunState, budget_seconds: int) -> None:
    now = utc_timestamp()
    state.wall_clock_started_at = now
    state.wall_clock_deadline = now + budget_seconds
    state.wall_clock_budget_seconds = budget_seconds


def remaining_budget(state: RunState) -> float:
    return max(0.0, state.wall_clock_deadline - utc_timestamp())
```

构造 controller：

```python
remaining = remaining_budget(self.state)

self.controller = LoopController(
    target_threshold=0.99,
    deadline_epoch=time.monotonic() + remaining,
)
```

检查耗尽：

```python
if remaining_budget(self.state) <= 0:
    self.state.status = RunStatus.EXHAUSTED
    save_run_state(self.state, self.run_dir)
    return self._build_status()
```

### 迁移要求

旧 checkpoint 中的 monotonic 起点不能可靠转换为 UTC。应显式拒绝或按保守策略处理：

```python
if state.schema_version < 3:
    raise IncompatibleCheckpointError(
        "Checkpoint uses a non-durable monotonic deadline"
    )
```

**判定**：GAP 4 不但没有完全修复，还引入了跨进程恢复语义错误。

---

## P0-3：Gate 的信任边界放错了

`tick()` 明确接受外部输入：

```python
def tick(
    self,
    action_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

其文档还声明外部结果可以包含：

```python
# - score
# - gate_results
# - task_status
# - evidence
```

然后：

```python
if action_result:
    self._process_result(action_result)
```

这意味着 Claude Code 主会话属于控制平面，同时还是 Gate 结果的输入方。除非 `_process_result()` 完全忽略外部 `gate_results`，并在本进程内重新执行 `_run_gates()`，否则 accept 仍可被伪造。

正确的边界应是：

```python
def tick(self, worker_result: dict[str, Any] | None = None) -> dict[str, Any]:
    if worker_result:
        result = self._validate_worker_envelope(worker_result)

        # Worker 只能报告产物位置，不能报告可信 gate 判决。
        gate_envelope = self._run_gates(
            task_id=result.task_id,
            patch_path=result.patch_path,
            evidence_paths=result.evidence_paths,
        )

        self._apply_gate_decision(result, gate_envelope)
```

外部出现 `gate_results` 应直接拒绝，而不是兼容：

```python
def _validate_worker_envelope(self, raw: dict[str, Any]) -> WorkerResult:
    forbidden = {"gate_results", "accepted", "phase_advance"}

    supplied = forbidden.intersection(raw)
    if supplied:
        raise UntrustedControlFieldError(
            f"Worker supplied control-plane fields: {sorted(supplied)}"
        )

    return WorkerResult.from_dict(raw)
```

最终 accept 必须只有一个函数能写入：

```python
def _apply_gate_decision(
    self,
    result: WorkerResult,
    gates: GateEnvelope,
) -> None:
    if not gates.complete or not gates.all_passed:
        self._reject_and_restore(result, gates)
        return

    self._accept_candidate(result, gates)
```

需要满足以下不变量：

```python
assert set(gates.results) == {
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8a"
}
assert all(result.executed for result in gates.results.values())
assert gates.all_passed
```

任何缺失、异常、超时必须失败：

```python
try:
    result = gate.run(timeout=gate.timeout)
except Exception as exc:
    result = GateResult(
        gate=gate.name,
        passed=False,
        error=repr(exc),
    )
```

**判定**：在提供 `_process_result()` 的完整实现及伪造输入测试前，GAP 2 不能判定为修复。

---

## P0-4：checkpoint 没有实现代码回滚

[`state_store.py`](https://r2.xsimple-r2.com/files/495944/d896054d-c188-4b00-98d5-d63123a1e442.py) 的 checkpoint 内容只有：

```python
data = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
_atomic_write(checkpoint_path, data)
```

restore 也只做：

```python
state = RunState.from_dict(data)
save_run_state(state, run_dir)
return state
```

这只是 **RunState 快照**，不是 patch 或工作树 checkpoint。

如果 worker 已修改源码，而 C2/C6 失败：

- JSON 状态可以回滚；
- 源码仍然处于失败后的状态；
- 下一次任务会建立在污染后的工作树上；
- “Gate reject + rollback”不成立。

### 必须使用隔离 worktree

```python
@dataclass(frozen=True)
class CandidateWorkspace:
    path: Path
    base_commit: str
    branch: str


def create_candidate(repo: Path, run_id: str, task_id: str) -> CandidateWorkspace:
    base = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    path = repo.parent / ".ui-autopilot-worktrees" / run_id / task_id
    branch = f"ui-autopilot/{run_id}/{task_id}"

    subprocess.run(
        [
            "git", "-C", str(repo), "worktree", "add",
            "-b", branch, str(path), base,
        ],
        check=True,
    )
    return CandidateWorkspace(path, base, branch)
```

所有 Gate 在 candidate worktree 执行：

```python
candidate = create_candidate(repo, run_id, task.id)
apply_patch(candidate.path, patch)
gates = self._run_gates(candidate.path, task)

if not gates.all_passed:
    remove_candidate(candidate)
    reject_task(task, gates)
    return
```

通过后才合并：

```python
commit_candidate(candidate.path, task.id)
merge_candidate(repo, candidate.branch)
remove_candidate(candidate)
```

checkpoint 至少要绑定：

```json
{
  "schema_version": 3,
  "base_commit": "abc123",
  "accepted_commit": "def456",
  "candidate_branch": null,
  "state": {}
}
```

**判定**：报告中的 “atomic evidence” 不能推导出 atomic rollback。二者是不同契约。

---

## P0-5：Token 权限规则自相矛盾

[`phase_rules.py`](https://r2.xsimple-r2.com/files/495944/2a9bb36c-4ede-4433-a5e4-807f622be104.py) 同时定义：

```python
Phase.TOKENS: [
    "src/styles/tokens/source/**/*.json",
    "src/styles/tokens/source/**/*.yaml",
]
```

以及：

```python
PHASE_PROHIBITED_ALWAYS = [
    "src/styles/tokens/source/**",
    "src/styles/tokens/generated/**",
]
```

也就是说，TOKENS 阶段的 allowlist 和全局 denylist 直接冲突。

如果 deny 优先，TOKENS allowlist 是死配置；如果 allow 优先，所谓 “NEVER writable” 就不成立。安全边界不能依赖调用方猜优先级。

### 正确权限表

```python
PHASE_ALLOWED_FILE_PATTERNS: dict[Phase, tuple[str, ...]] = {
    Phase.DISCOVERY: (),
    Phase.TOKENS: (
        ".omc/ui-autopilot/*/token-proposals/**/*.json",
        ".omc/ui-autopilot/*/token-proposals/**/*.yaml",
    ),
    Phase.SHELL: (
        "src/shell/**/*.tsx",
        "src/shell/**/*.scss",
        "src/layouts/**/*.tsx",
        "src/layouts/**/*.scss",
    ),
    # ...
    Phase.FINAL_AUDIT: (),
}

PHASE_PROHIBITED_ALWAYS = (
    "src/styles/tokens/source/**",
    "src/styles/tokens/generated/**",
    "scripts/carroros-gates/**",
    ".claude/**",
    "node_modules/**",
    "dist/**",
    "build/**",
)
```

注意 `.omc/**` 不能一边全局禁止，一边又作为 proposal/evidence 的目标。更清晰的做法是把控制平面运行目录放在目标仓库外。

匹配必须先 canonicalize：

```python
def normalize_changed_path(repo: Path, raw_path: str) -> str:
    if "\x00" in raw_path:
        raise ScopeViolation("NUL byte in path")

    candidate = (repo / raw_path).resolve(strict=False)
    root = repo.resolve(strict=True)

    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ScopeViolation("Path escapes repository") from exc

    if any(part == ".." for part in relative.parts):
        raise ScopeViolation("Parent traversal")

    return relative.as_posix()
```

并明确 deny 优先：

```python
if matches_any(path, PHASE_PROHIBITED_ALWAYS):
    return ScopeDecision(False, "globally prohibited")

if not matches_any(path, PHASE_ALLOWED_FILE_PATTERNS[phase]):
    return ScopeDecision(False, "not allowed in current phase")
```

**判定**：GAP 8 只能算“去重完成”，Token freeze 本身未正确落地。

---

## P1-1：测量器无法支撑 D1-D7 声明

[`measure_prototype.py`](https://r2.xsimple-r2.com/files/495944/e88b94da-ea44-4b3d-ac3a-60fcdd52084e.py) 实际只读取 region 根节点：

```javascript
const el = document.querySelector(selector);
const style = window.getComputedStyle(el);
```

它没有遍历 descendants，因此：

- `colors` 不是 region palette；
- `fonts` 只有 region 根节点字体；
- `borders` 只有根节点边框；
- 不包含元素级 spacing、层级结构、交互状态；
- 不包含 token 声明与使用分析；
- 不包含 interaction assertions；
- 不产生 D6；
- 不产生 D7。

报告声称“ScoringEngine computes D1-D7 from real browser measurements”与实现不符。

至少应该返回带 schema 和能力声明的结果，防止缺字段默认高分：

```json
{
  "schema_version": 1,
  "producer": "playwright-computed-style",
  "source_kind": "runnable_prototype",
  "viewport": {"width": 1280, "height": 1024},
  "dimensions": {
    "D1": {"status": "measured"},
    "D2": {"status": "measured"},
    "D3": {"status": "measured"},
    "D4": {"status": "measured"},
    "D5": {"status": "measured"},
    "D6": {"status": "not_implemented"},
    "D7": {"status": "not_implemented"}
  }
}
```

评分器必须 fail-closed：

```python
required = {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}

if set(measurement.dimensions) != required:
    raise IncompleteMeasurementError()

if any(d.status != "measured" for d in measurement.dimensions.values()):
    return ScoreResult(
        valid=False,
        hard_gate_pass=False,
        reason="Incomplete UIF-99 measurement",
    )
```

还存在资源清理问题：

```python
try:
    page.goto(...)
except Exception as e:
    return {"error": ...}
```

此处在 `browser.close()` 前返回。应使用：

```python
browser = p.chromium.launch(headless=True)
try:
    page = browser.new_page(viewport=viewport)
    page.goto(url, wait_until="networkidle", timeout=30_000)
    return extract_all(page, regions)
finally:
    browser.close()
```

---

## P1-2：`_atomic_write()` 不是完整的 durable atomic write

当前实现：

```python
os.write(fd, data.encode("utf-8"))
os.fsync(fd)
os.close(fd)
os.replace(tmp_path, str(path))
```

问题：

1. `os.write()` 允许 partial write；
2. `os.replace()` 失败时，异常分支再次 `os.close(fd)`，可能掩盖原异常；
3. rename 后没有 fsync 父目录；
4. 只能保证文件替换原子性，不能直接声称所有操作 crash-safe。

建议实现：

```python
def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = data.encode("utf-8")

    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(tmp_path, path)

        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise
```

---

## P1-3：周期 checkpoint 的“最多损失一分钟”仍不成立

checkpoint 检查在一次 `tick()` 尾部：

```python
if elapsed_since_checkpoint >= CHECKPOINT_EVERY_SECONDS:
    save_checkpoint(...)
```

因此它不是后台定时器。若外部 worker、Playwright 或 Gate 阻塞十分钟，这十分钟内没有 checkpoint。

准确表述应是：

```text
在 tick 正常返回的前提下，系统尝试每 60 秒保存一次状态。
实际恢复点受最长不可中断操作时长约束。
```

另外首次进入时：

```python
if not hasattr(self, "_last_checkpoint_time"):
    self._last_checkpoint_time = time.monotonic()
```

会导致本次必定不保存 checkpoint。重启后计时重新开始，即使上次 checkpoint 已非常陈旧，也要再等完整周期。

应持久化 UTC checkpoint 时间，且在关键边界强制保存：

```python
save_checkpoint(..., "before-worker")
save_checkpoint(..., "after-worker")
save_checkpoint(..., "before-gates")
save_checkpoint(..., "after-reject")
save_checkpoint(..., "after-accept")
save_checkpoint(..., "phase-transition")
```

---

## P1-4：Phase Entry Conditions 很可能只是声明，没有形成完整闭环

[`phase_gate.py`](https://r2.xsimple-r2.com/files/495944/2e7297b6-99c9-424b-a32e-7fa338a0da5d.py) 定义了 `PHASE_ENTRY_CONDITIONS`，但展示出来的核心推进路径是：

```python
if self._should_advance_phase():
    self._advance_phase()
```

而 `PhaseGate.can_advance()` 检查当前 phase 的退出条件。仅定义 entry rules 不代表 transition 时实际调用了 `can_enter(next_phase, report)`。

正确推进应双向校验：

```python
def can_transition(
    self,
    current_report: PhaseReport,
    next_report: PhaseReport,
) -> bool:
    expected = PHASE_TRANSITIONS.get(current_report.phase)

    if expected is None or expected != next_report.phase:
        return False

    return (
        self.can_advance(current_report)
        and self.can_enter(next_report.phase, next_report)
    )
```

还有一个逻辑问题：

```python
Phase.FINAL_AUDIT: PhaseGateRule(
    requires=["final_gate_passed"],
)
```

如果 `final_gate_passed` 是 FINAL_AUDIT 的结果，就不能同时作为进入 FINAL_AUDIT 的前提。这是循环依赖。更合理的是：

```python
Phase.FINAL_AUDIT: PhaseGateRule(
    requires=[
        "interaction_coverage >= 1.0",
        "state_coverage >= 1.0",
        "polish_score >= 0.99",
    ],
)
```

`final_gate_passed` 应作为 FINAL_AUDIT 的退出条件或成功条件。

---

## 宿主层结论

文件头已经明确：

```text
The orchestrator does NOT call models directly.
It produces directives that the CC session executes.
```

所以它不是独立的 6h runner，而是决策器。当前上传材料没有：

- 独立 supervisor；
- watchdog；
- stale heartbeat 后的重启动作；
- worker timeout/kill；
- 启动时自动 restore；
- 配额耗尽后的确定性降级；
- 会话断开后的 process ownership。

`write_heartbeat()` 只写文件，不会自动恢复任何东西。检测信号不等于恢复机制。

因此“6h unattended”仍不成立。

---

## 放行标准

修复后，至少执行以下自动测试：

```python
def test_tick_does_not_raise_name_error(): ...
def test_budget_survives_process_restart(): ...
def test_worker_cannot_supply_gate_results(): ...
def test_missing_gate_is_rejected(): ...
def test_gate_timeout_is_rejected(): ...
def test_failed_candidate_does_not_modify_main_worktree(): ...
def test_tokens_source_is_denied_in_every_phase(): ...
def test_path_traversal_and_symlink_escape_are_denied(): ...
def test_incomplete_d6_d7_cannot_pass_c6_or_c8a(): ...
def test_checkpoint_restores_state_and_accepted_commit(): ...
def test_final_audit_has_no_circular_entry_condition(): ...
```

必须提供四条集成证据：

```text
1. candidate accept → Gate 全通过 → 原子合并
2. C2/C6 fail → candidate 丢弃 → 主工作树 hash 不变
3. crash/restart → UTC 预算连续 → convergence 连续
4. token source patch → C1 在 apply 前拒绝
```

## 终审结论

当前版本应标记为：

```yaml
status: implementation_in_progress
critical_gaps_fixed: false
ready_for_supervised_dry_run: false
ready_for_6h_unattended: false
```

最先修复顺序：

1. `MAX_TOTAL_ITERATIONS` 导入，恢复基本可运行性；
2. UTC deadline，修复跨进程预算；
3. 移除外部 `gate_results` 信任，建立唯一 accept 路径；
4. 使用隔离 worktree，实现真正 rollback；
5. 消除 Token allow/deny 冲突；
6. 补齐 D6/D7 producers，并让缺测量 fail-closed；
7. 增加 session 外 supervisor 后，再谈 6h unattended。

在这七项完成且测试通过前，**最终结论为 NO-GO**。