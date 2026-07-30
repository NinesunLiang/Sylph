# Grok 终审（UI Autopilot v2）

## 总判决

```yaml
reviewer: grok-4.5 (xAI)
role: third-model structural auditor
mode: design-stage final review (no runtime data expected)

decision:
  design_direction: ACCEPT_WITH_HARD_GATES
  overnight_unattended_6h: NO-GO
  supervised_dry_run: NO-GO_UNTIL_P0_CLOSED
  claim_"13_critical_gaps_fixed": REJECTED

architecture_score:
  state_machine_shape: 7.5/10
  safety_boundary: 3.0/10
  measurement_truth: 2.5/10
  recovery_semantics: 4.0/10
  model_orchestration_contract: 6.0/10
  overall_ready_for_execution: 3.5/10
```

Sol 的结论偏“控制平面与宿主编排”，Opus 的结论偏“评分–收敛三角”。  
**我这边给的是系统可证性终审：这个方案能不能在无人值守下，稳定地把 UI 推到真实的高还原，而不是把分数推到好看。**

当前答案：**还不能。**

它已经有一个可执行的骨架：Phase 分层、bounded task、EMA 收敛、gate 概念、状态落盘。  
但它还不具备“无人化高还原”所需的四条硬不变量。

---

## 四条硬不变量（设计必须先成立）

一个真正可用的 UI 无人化系统，至少要保证：

1. **可证明的写权限边界**
2. **可证明的失败回滚**
3. **可证明的评分来源**
4. **可证明的跨进程恢复**

现在这四条都还没闭合。下面按这个顺序终审。

---

## P0-1：Token 权限规则是自相矛盾的安全边界

再看一次 `phase_rules.py`：

```python
PHASE_ALLOWED_FILE_PATTERNS: dict[Phase, list[str]] = {
    Phase.TOKENS: [
        "src/styles/tokens/source/**/*.json",
        "src/styles/tokens/source/**/*.yaml",
    ],
    # ...
}

PHASE_PROHIBITED_ALWAYS: list[str] = [
    "src/styles/tokens/source/**",      # Token source is daytime-only
    "src/styles/tokens/generated/**",
    # ...
]
```

这不是风格问题，是安全规则失效：

- 如果 deny 优先：TOKENS 的 allowlist 是死规则。
- 如果 allow 优先：`NEVER writable` 是假话。
- 如果“调用方自己判断”：无人化夜间跑就会踩雷。

**无人化场景里，安全规则必须是 bits 级确定的，不能是文档级共识。**

### 正确设计：Token 夜间只出提案，不写正式 source

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from fnmatch import fnmatch

from .domain import Phase


class ScopeDecision(str, Enum):
    ALLOW = "allow"
    DENY_GLOBAL = "deny_global"
    DENY_PHASE = "deny_phase"
    DENY_ESCAPE = "deny_escape"


# 目标仓库内，夜间永远不可写
PHASE_PROHIBITED_ALWAYS = (
    "src/styles/tokens/source/**",
    "src/styles/tokens/generated/**",
    "scripts/carroros-gates/**",
    ".claude/**",
    "node_modules/**",
    "dist/**",
    "build/**",
)

# 注意：.omc 运行态不要放在被保护的目标仓库内；
# 或者显式允许极窄路径。我建议把 run artifacts 放到 target_repo 外。
PHASE_ALLOWED_FILE_PATTERNS: dict[Phase, tuple[str, ...]] = {
    Phase.DISCOVERY: (),  # 只读扫描
    Phase.TOKENS: (
        # 仅允许提案与证据，不允许正式 token source
        "artifacts/token-proposals/**/*.json",
        "artifacts/token-proposals/**/*.yaml",
        "artifacts/token-diffs/**/*.md",
    ),
    Phase.SHELL: (
        "src/shell/**/*.tsx",
        "src/shell/**/*.scss",
        "src/layouts/**/*.tsx",
        "src/layouts/**/*.scss",
    ),
    Phase.REGIONS: (
        "src/pages/**/*.tsx",
        "src/pages/**/*.scss",
        "src/components/**/*.tsx",
        "src/components/**/*.scss",
    ),
    Phase.ELEMENTS: (
        "src/pages/**/*.tsx",
        "src/pages/**/*.scss",
        "src/components/**/*.tsx",
        "src/components/**/*.scss",
    ),
    Phase.INTERACTIONS: (
        "src/pages/**/*.tsx",
        "src/pages/**/*.scss",
        "src/components/**/*.tsx",
        "src/components/**/*.scss",
        "src/overlays/**/*.tsx",
        "src/overlays/**/*.scss",
    ),
    Phase.POLISH: (
        # 可 polish 表现层，不可改 token 源
        "src/pages/**/*.scss",
        "src/components/**/*.scss",
        "src/overlays/**/*.scss",
        "src/shell/**/*.scss",
    ),
    Phase.FINAL_AUDIT: (),
}


def normalize_repo_path(repo: Path, raw: str) -> str:
    if "\x00" in raw:
        raise ValueError("NUL path")

    candidate = (repo / raw).resolve(strict=False)
    root = repo.resolve(strict=True)

    try:
        rel = candidate.relative_to(root)
    except ValueError as e:
        raise ValueError("path escapes repository") from e

    if any(p in ("..",) for p in rel.parts):
        raise ValueError("parent traversal")

    return rel.as_posix()


def matches_any(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(fnmatch(path, pat) for pat in patterns)


def decide_write_scope(repo: Path, phase: Phase, raw_path: str) -> ScopeDecision:
    """
    Deny always wins.
    Token freeze is absolute overnight.
    """
    try:
        path = normalize_repo_path(repo, raw_path)
    except ValueError:
        return ScopeDecision.DENY_ESCAPE

    if matches_any(path, PHASE_PROHIBITED_ALWAYS):
        return ScopeDecision.DENY_GLOBAL

    allowed = PHASE_ALLOWED_FILE_PATTERNS.get(phase, ())
    if not matches_any(path, allowed):
        return ScopeDecision.DENY_PHASE

    return ScopeDecision.ALLOW
```

### 强制 C1 前置断言（apply 之前）

```python
def assert_patch_in_scope(repo: Path, phase: Phase, changed_files: list[str]) -> None:
    bad = []
    for f in changed_files:
        decision = decide_write_scope(repo, phase, f)
        if decision != ScopeDecision.ALLOW:
            bad.append((f, decision.value))
    if bad:
        raise PermissionError(f"C1 scope violation: {bad}")
```

**Grok 结论**：没有这层，晚上任何“修 token”都会直接污染正式资产，或者规则表变成死代码。这是无人化安全的第一枪。

---

## P0-2：当前 checkpoint 不是回滚，只是状态快照

`state_store.save_checkpoint()` / `restore_checkpoint()` 只序列化 `RunState`。

这意味着：

- Gate 失败后，状态可回到上一版；
- 但代码工作树可能仍是污染后；
- 下一个 task 会继续在失败残迹上搜索。

对无人化还原，这是**灾难化石化**：错误路径会被“继续修正”，而不是被“判定失败后丢弃”。

### 正确模型：candidate workspace，而不是 in-place mutate

```python
from dataclasses import dataclass
from pathlib import Path
import subprocess
import shutil


@dataclass(frozen=True)
class Candidate:
    run_id: str
    task_id: str
    base_commit: str
    worktree: Path
    branch: str


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def create_candidate(repo: Path, run_id: str, task_id: str) -> Candidate:
    base = git(repo, "rev-parse", "HEAD")
    branch = f"ui-autopilot/{run_id}/{task_id}"
    worktree = repo.parent / ".ui-autopilot-worktrees" / run_id / task_id

    if worktree.exists():
        shutil.rmtree(worktree)

    # isolated mutable workspace
    git(repo, "worktree", "add", "-b", branch, str(worktree), base)
    return Candidate(run_id, task_id, base, worktree, branch)


def destroy_candidate(repo: Path, c: Candidate) -> None:
    # best-effort cleanup; never throw away main tree state
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(c.worktree)],
        check=False,
    )
    subprocess.run(
        ["git", "-C", str(repo), "branch", "-D", c.branch],
        check=False,
    )


def accept_candidate(repo: Path, c: Candidate, message: str) -> str:
    # 1) commit only after gates (called after gates all pass)
    git(c.worktree, "add", "-A")
    git(c.worktree, "commit", "-m", message)
    commit = git(c.worktree, "rev-parse", "HEAD")

    # 2) fast-forward/merge back to main workspace ownership branch
    # 这里用 merge --ff-only 更安全，禁止强推历史重写
    git(repo, "merge", "--ff-only", c.branch)
    destroy_candidate(repo, c)
    return commit
```

### tick 的写法必须改成：candidate 上验，主树上只吃通过结果

```python
def _execute_task_safely(self, task: Task) -> None:
    candidate = create_candidate(self.repo, self.state.run_id, task.id)
    try:
        apply_patch(candidate.worktree, task.patch_or_diff)
        assert_patch_in_scope(candidate.worktree, self.state.phase, task.changed_files)

        gates = self._run_gates_in_workspace(candidate.worktree, task)
        if not gates.all_passed:
            destroy_candidate(self.repo, candidate)
            self._mark_task_rejected(task, gates)
            return

        accepted_commit = accept_candidate(
            self.repo,
            candidate,
            f"ui-autopilot: accept {task.id}",
        )
        self._mark_task_accepted(task, accepted_commit, gates)
    except Exception as e:
        destroy_candidate(self.repo, candidate)
        self._mark_task_failed(task, error=repr(e))
```

**Grok 结论**：没有 candidate isolation，就没有真正的“Gate reject = 安全失败”。  
`state_store` 解决的是“脑能记住”，解决不了“手写错了怎么办”。

---

## P0-3：评分系统在数学上不可用于 0.99 目标（D6/D7 黑洞）

`domain.Score` 的权重把真相讲得非常清楚：

```text
D6 TokenAlign = 0.18
D7 Interaction = 0.24
合计 = 0.42
```

而现有 measurement producer（prototype + implementation）只产出：

```json
{ "bbox", "colors", "fonts", "borders", "shadows", "layout" }
```

这最多支持 D1–D5 的局部形态。  
D6/D7 是“高还原无人化”的真正硬核，却是空心的。

### 诚实默认策略（设计阶段就必须定死）

```python
@dataclass(slots=True)
class DimensionStatus:
    status: str  # measured | unavailable | not_applicable
    value: float | None = None
    reason: str | None = None


@dataclass(slots=True)
class MeasurementBundle:
    schema_version: int
    dimensions: dict[str, DimensionStatus]


REQUIRED_FOR_UIF99 = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")


def score_or_fail(bundle: MeasurementBundle, gates_h1_h2: tuple[bool, bool]) -> Score:
    h1, h2 = gates_h1_h2
    if not h1 or not h2:
        return Score(h1_engineering_pass=False, h2_evidence_pass=False)

    missing = [
        k for k in REQUIRED_FOR_UIF99
        if k not in bundle.dimensions or bundle.dimensions[k].status != "measured"
    ]
    if missing:
        # fail-closed: incomplete evidence is not a high score
        return Score(
            h1_engineering_pass=True,
            h2_evidence_pass=False,  # 证据不全
        )

    return Score(
        geometry=bundle.dimensions["D1"].value or 0.0,
        color=bundle.dimensions["D2"].value or 0.0,
        typography=bundle.dimensions["D3"].value or 0.0,
        decoration=bundle.dimensions["D4"].value or 0.0,
        layout=bundle.dimensions["D5"].value or 0.0,
        token_align=bundle.dimensions["D6"].value or 0.0,
        interaction=bundle.dimensions["D7"].value or 0.0,
        h1_engineering_pass=True,
        h2_evidence_pass=True,
    )
```

### D6（最小可证明实现）

```python
# token_align.py
import re
from pathlib import Path

RAW_HEX = re.compile(r"#(?:[0-9a-fA-F]{3,8})\b")
RAW_RGB = re.compile(r"rgba?\([^)]*\)")
TOKEN_REF = re.compile(r"var\(--[A-Za-z0-9_-]+\)")


def file_align_rate(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")
    raw = len(RAW_HEX.findall(text)) + len(RAW_RGB.findall(text))
    refs = len(TOKEN_REF.findall(text))
    total = raw + refs
    return 1.0 if total == 0 else refs / total


def compute_d6(src_dirs: list[Path]) -> float:
    rates: list[float] = []
    for d in src_dirs:
        for p in d.rglob("*"):
            if p.suffix in {".scss", ".css", ".tsx", ".ts"}:
                rates.append(file_align_rate(p))
    return sum(rates) / len(rates) if rates else 0.0
```

### D7（最小可证明实现）

```python
# interaction_catalog.py
from dataclasses import dataclass
from playwright.sync_api import Page


@dataclass(frozen=True)
class InteractionCase:
    id: str
    selector: str
    action: str  # hover|click|focus
    expect_visible: str | None = None
    expect_attr: tuple[str, str] | None = None  # (name, value)


def run_case(page: Page, case: InteractionCase) -> bool:
    loc = page.locator(case.selector).first
    if case.action == "hover":
        loc.hover()
    elif case.action == "click":
        loc.click()
    elif case.action == "focus":
        loc.focus()
    else:
        return False

    if case.expect_visible:
        return page.locator(case.expect_visible).first.is_visible(timeout=800)
    if case.expect_attr:
        name, value = case.expect_attr
        return (loc.get_attribute(name) or "") == value
    return True


def compute_d7(page: Page, cases: list[InteractionCase]) -> float:
    if not cases:
        return 0.0
    ok = sum(1 for c in cases if run_case(page, c))
    return ok / len(cases)
```

**Grok 结论**：在 D6/D7 真实量测落地前，系统任何“已达 0.98/0.99”的叙述都不可信。  
报告必须写：`max trustworthy score ceiling ≈ D1–D5 only`。

---

## P0-4：Gate 信任边界放错了（不能吃 worker 自报 gate_results）

`tick(action_result)` 文档契约包含 `gate_results`。  
这等于让 tool 自己写检查单，再自己打勾。

无人化系统只能接受：

- worker 产物位置
- patch 路径
- evidence 文件路径
- 执行日志

不能接受：

- accepted
- gate_results
- phase_advance
- score 最终判决（除非你想把它当 caching hint）

### 唯一可信入口

```python
from dataclasses import dataclass
from typing import Any


FORBIDDEN_WORKER_FIELDS = {
    "gate_results",
    "accepted",
    "phase_advance",
    "h1_engineering_pass",
    "h2_evidence_pass",
    "uif_composite",
}


@dataclass(frozen=True)
class WorkerEnvelope:
    task_id: str
    patch_path: str | None
    changed_files: list[str]
    evidence_paths: list[str]
    notes: dict[str, Any]


def parse_worker_envelope(raw: dict[str, Any]) -> WorkerEnvelope:
    leaked = FORBIDDEN_WORKER_FIELDS.intersection(raw)
    if leaked:
        raise ValueError(f"untrusted control-plane fields from worker: {sorted(leaked)}")

    return WorkerEnvelope(
        task_id=raw["task_id"],
        patch_path=raw.get("patch_path"),
        changed_files=list(raw.get("changed_files", [])),
        evidence_paths=list(raw.get("evidence_paths", [])),
        notes=dict(raw.get("notes", {})),
    )
```

### accept 权限只能在 orchestrator 内产生

```python
def _process_worker_result(self, raw: dict[str, Any]) -> None:
    env = parse_worker_envelope(raw)

    # 1) scope first
    assert_patch_in_scope(self.repo, self.state.phase, env.changed_files)

    # 2) gates only by local trusted runners
    gates = self._run_full_gate_chain(
        task_id=env.task_id,
        patch_path=env.patch_path,
        evidence_paths=env.evidence_paths,
    )

    # 3) score only after gates
    if not gates.all_passed:
        self._reject(env, gates)
        return

    score = self._measure_and_score(env)
    self._accept(env, gates, score)
```

**Grok 结论**：这是“控制平面污染”问题。不修，系统在白天 demo 看起来聪明，晚上无人会自己给自己发通行证。

---

## P0-5：跨进程时间语义错误（monotonic 不能持久化）

当前预算把 `time.monotonic()` 相关值塞进可恢复状态，这在设计上就错。

正确分层：

- **可持久化权威时钟**：UTC deadline
- **进程内 watchdog**：monotonic remaining

```python
from dataclasses import dataclass
from datetime import datetime, timezone
import time


def utc_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


@dataclass(slots=True)
class Budget:
    started_at_utc: float
    deadline_utc: float
    budget_seconds: int

    @classmethod
    def start(cls, budget_seconds: int) -> "Budget":
        now = utc_ts()
        return cls(now, now + budget_seconds, budget_seconds)

    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_utc - utc_ts())

    def exhausted(self) -> bool:
        return self.remaining_seconds() <= 0.0

    def process_deadline_monotonic(self) -> float:
        # only for in-process LoopController
        return time.monotonic() + self.remaining_seconds()

    def to_dict(self) -> dict:
        return {
            "started_at_utc": self.started_at_utc,
            "deadline_utc": self.deadline_utc,
            "budget_seconds": self.budget_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Budget":
        return cls(d["started_at_utc"], d["deadline_utc"], d["budget_seconds"])
```

`LoopController` 的 deadline 每次进程启动时从 Budget 重新推导，不落盘 monotonic 时间。

---

## P1：Opus 捕获到的关键交互缺陷，我确认并用更强约束加强

### 1) Gate fail → score 0 → EMA 判 DIVERGING

这是**反馈回路污染**。  
收敛器只能吃“有效样本”，不能吃“失败惩罚分”。

```python
def record_and_decide(self, score: float, *, sample_valid: bool) -> str:
    if not sample_valid:
        self.invalid_samples += 1
        if self.invalid_samples >= 3:
            return "ESCALATE_TO_ROOT_CAUSE"
        return "RETRY_FIX_GATES"

    self.invalid_samples = 0
    status = self.tracker.record(score)
    return self.map_status_to_action(status)
```

### 2) StrategyState.locked_until 不能用 monotonic

与 Budget 同一类错误。锁定策略必须用 UTC。

### 3) completeness 维度需 phase-aware

早期 phase 没有 interaction/scroll coverage 是正常的。  
否则 SHELL 阶段就会被逼去“伪优化交互”。

```python
PHASE_COMPLETENESS_KEYS = {
    "discovery": ("route_coverage",),
    "tokens": ("route_coverage",),
    "shell": ("route_coverage",),
    "regions": ("route_coverage", "scroll_coverage"),
    "elements": ("route_coverage", "scroll_coverage"),
    "interactions": ("route_coverage", "scroll_coverage", "state_coverage", "interaction_coverage"),
    "polish": ("route_coverage", "scroll_coverage", "state_coverage", "interaction_coverage"),
    "final_audit": ("route_coverage", "scroll_coverage", "state_coverage", "interaction_coverage"),
}
```

---

## Grok 额外发现（两位可能低估了）

### A. DISCOVERY 允许写 `src/**` 过于危险

```python
Phase.DISCOVERY: [
    "src/**/*.tsx", "src/**/*.ts", "src/**/*.scss", "src/**/*.css",
],
```

Discovery 应当只读：

- 扫描 prototype
- 产出 region inventory / route map / gold metadata

直接给全源码写权限，夜间“探索”会变成“随手重构”。  
**Discovery 写权限应清空，产物只进 artifacts。**

### B. measure_* 只读 region 根节点，会系统性地偏向 shell 级一致性

```js
const el = document.querySelector(selector);
const style = window.getComputedStyle(el);
```

高还原失败经常发生在 descendants：

- 子项间距
- 嵌套卡片圆角
- 文本层级
- 图标与标签对齐
- sticky/fixed 栈

所以至少扫描一层 descendants，并输出元素集合摘要：

```javascript
(selector) => {
  const root = document.querySelector(selector);
  if (!root) return null;

  const nodes = [root, ...root.querySelectorAll("*")].slice(0, 80);
  const sample = nodes.map((el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute("role"),
      textLen: (el.textContent || "").trim().length,
      bbox: { x: r.x, y: r.y, w: r.width, h: r.height },
      color: s.color,
      bg: s.backgroundColor,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      radius: s.borderRadius,
      display: s.display,
      gap: s.gap,
    };
  });
  return { sampleCount: sample.length, sample };
}
```

否则 scorer 会长期“shell 过关、细节不过关”，而系统还不承认。

### C. 现在不是 6h runner，只是 decision module

`orchestrator` 明确不调用模型，不杀进程，不接管会话。  
那它就不是 unattended runner。

真正的无人化还缺一层：

```text
Supervisor (OS process)
  ├── heartbeat watchdog
  ├── restart on stale
  ├── hard kill worker timeout
  ├── budget enforced externally
  └── crash recovery from accepted_commit + UTC budget
```

没有 supervisor，6h 是“文档承诺”，不是“工程能力”。

---

## 设计阶段可接受的最小闭环（ADR）

如果目标是继续设计而不是马上跑夜，我建议把 v2 设计锁死为：

```yaml
ADR-001: Token freeze overnight
  - token source 夜间只读
  - TOKENS 阶段只产出 proposal

ADR-002: Candidate isolation
  - 任何写操作先进入 worktree
  - gates 只在 candidate 上运行
  - accept 才 merge

ADR-003: Trust boundary
  - worker 不可提交 gate_results / final score
  - orchestrator 是唯一 accept authority

ADR-004: Measurement honesty
  - D6/D7 未实现时 h2_evidence_pass=false
  - 不允许默认满分填充

ADR-005: Durable time
  - budget/strategy lock 全部用 UTC
  - monotonic 仅进程内

ADR-006: Phase-aware scoring
  - completeness keys 按 phase 启用
  - 早期阶段不对交互硬考核
```

这 6 条不闭合，后面写再多 router / EMA / phase report 都是装饰。

---

## 终审对“还能不能继续设计”的态度

这套方向不是错的。  
**错的是过早宣称 gap 已 partially/fully fixed，以及把“状态机成型”等同于“无人化可用”。**

我对架构本身的评价：

- Phase 分层：**对**
- bounded task + file scope：**方向对，实现未闭合**
- EMA 收敛：**好想法，反馈入口还脏**
- UIF-99 七维：**目标对，测量缺口致命**
- state_store 原子写：**可靠底座，但不是 rollback 本体**

所以：

```yaml
design_continue: YES
execution_start: NO
overnight_claim: FORBIDDEN
next_milestone: "P0 closed design freeze + contract tests"
```

---

## 设计冻结前必须补齐的核心代码清单

最少补这 6 个 contract（先写测试再写完整实现也行）：

1. `scope_guard.py`：deny 优先、token freeze、path escape 防护  
2. `candidate_workspace.py`：create/apply/gate/accept/destroy  
3. `worker_envelope.py`：禁止控制平面字段  
4. `budget.py`：UTC deadline + process watchdog  
5. `measure_d6_token_align.py` + `measure_d7_interactions.py`  
6. `score_fail_closed.py`：缺维、缺门控一律不可“高分过关”

示例 contract test 集合（设计期就应存在用例名）：

```python
def test_token_source_denied_in_all_phases(): ...
def test_discovery_is_read_only(): ...
def test_worker_cannot_inject_gate_results(): ...
def test_gate_fail_does_not_mutate_main_tree(): ...
def test_incomplete_d6_d7_cannot_set_h2_pass(): ...
def test_budget_restores_from_utc_deadline(): ...
def test_invalid_gate_sample_does_not_update_ema(): ...
def test_polish_cannot_write_token_source(): ...
```

---

## 最终一句话

**这是一个“高级编排器设计草案”，还不是一个“可无人值守的 UI 高还原执行系统”。**

可以继续设计。  
可以把 Phase / Task / Gate / Convergence 继续打磨。  
但在 Token freeze、candidate rollback、可信 gate、D6/D7 真实测量、UTC 恢复语义闭合前：

### 终审 = NO-GO

你现在最该做的，不是继续堆 orchestrator 复杂度，而是先把上面 6 条 ADR 写成**不可违反的 contract + 核心代码骨架**。  
那之后，再谈 6h 无人化、模型路由配额和夜间冲刺，才有物理意义。