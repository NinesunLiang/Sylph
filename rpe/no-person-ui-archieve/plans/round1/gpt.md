# CarrorOS UI Autopilot v2：无人化高保真还原方案（第 1/5 部分）

> 本部分解决最根本的问题：**为什么现有流程会退出、为什么 Prompt Loop 不可靠，以及如何把它升级为可连续运行 6 小时以上的确定性 Goal Loop。**
>
> 后续四部分：
>
> 1. **本篇：总架构、状态机、持续循环控制器、停止条件**
> 2. 原型完整采集：页面、滚动、hover、弹窗、折叠、多路由的自动遍历
> 3. Design Token 自动提取、聚类、Tailwind/CSS Variables 生成与硬编码治理
> 4. 分层视觉还原：整体 → 区域 → 元素，视觉差异定位与自动修复
> 5. 多模型路由、CarrorOS 门禁、故障恢复、6 小时运行、验收和落地改造清单

---

## 一、先给结论：现有方案需要从“夜间 Prompt”升级为“确定性执行系统”

根据 `OPTIMIZATION-FACTSET.md`、`night-loop.md` 相关事实，以及 `UI_README.md` 的约束，我认为现有方案的问题不是简单增加一句 `/loop` 就能解决。

当前工作流更接近：

```text
给执行模型一份 night-loop.md
  ↓
模型自行理解步骤
  ↓
模型实现一部分
  ↓
运行门禁
  ↓
做少量修复
  ↓
上下文、预算或指令步数耗尽
  ↓
退出
```

这种架构无法稳定完成 80% → 99%，原因有四个。

### 1. LLM 被错误地当成了循环控制器

模型不应该决定：

- 当前运行到第几轮；
- 是否继续；
- 哪个区域尚未完成；
- 是否已经停滞；
- 是否需要回滚；
- 下一轮应修复什么；
- 什么时候调用昂贵模型；
- 什么时候允许结束。

这些必须由**外部确定性脚本**管理。

模型只负责一个非常窄的动作：

```text
读取一个有边界的差异任务
→ 修改允许范围内的代码
→ 返回结构化结果
```

也就是说：

> **Python orchestrator 是大脑，LLM 是受控执行器。**

---

### 2. “99%”目前不是一个可执行目标

如果只把目标写成“视觉还原度达到 99%”，系统无法准确判断是否完成。

必须定义：

- 在哪些 viewport 上比较；
- 比较哪些页面和交互状态；
- 是否排除动态区域；
- 用什么视觉指标；
- 几何差异和颜色差异如何加权；
- 页面未覆盖区域如何处罚；
- 弹窗、hover、折叠等状态缺失如何处罚；
- 单个区域不合格时，是否允许页面总分平均掩盖问题。

因此，不能只设：

```yaml
similarity: 0.99
```

而应建立多维验收：

```yaml
completion:
  state_coverage: 1.0
  route_coverage: 1.0
  scroll_coverage: 1.0
  required_interactions: 1.0

visual:
  global_similarity: 0.99
  minimum_region_similarity: 0.985
  minimum_critical_region_similarity: 0.995
  geometry_score: 0.995
  typography_score: 0.99
  color_score: 0.99

quality:
  token_compliance: 1.0
  runtime_errors: 0
  console_errors: 0
  c1_to_c8_passed: true
```

---

### 3. 现有 Phase A/B/C 方向正确，但粒度仍然不够

已有事实集提出：

- Phase A：宏观骨架；
- Phase B：中观区域；
- Phase C：微观元素。

这是正确方向，但还缺少三个关键能力：

#### 3.1 每个层级都要有独立门禁

不能 Phase A 还没对齐就开始调按钮圆角，否则后面修改布局会使微观工作全部失效。

#### 3.2 每个区域需要独立任务和独立视觉评分

例如：

```text
dashboard
├── app-shell
│   ├── sidebar
│   ├── topbar
│   └── content-container
├── summary-cards
├── trend-chart
├── ranking-table
└── floating-actions
```

每个节点都应该有：

- bounding box；
- 当前得分；
- 原型截图；
- 实现截图；
- diff 图片；
- 允许修改文件；
- 未解决差异；
- 修复历史；
- 停滞次数。

#### 3.3 需要支持“退回上一阶段”

例如微观阶段发现卡片宽度全部不对，根因可能不是卡片，而是内容容器宽度不正确。

系统应支持：

```text
ELEMENT 阶段发现系统性横向偏移
→ 根因分类为 ancestor_geometry
→ 退回 REGION 或 SHELL
→ 修复父级
→ 重新基线化子区域
```

---

### 4. `UI_README.md` 不能只是“必读文档”，必须编译成机器门禁

现在“要求模型阅读 UI_README”本质上是软约束。软约束在长任务里一定会逐渐失效。

例如 UI 铁律包括：

- 原型需登录时必须请求用户协助；
- Chrome DevTools 断线不得降级；
- 截图只能写指定目录；
- 颜色必须来自 Token；
- `.tsx` / `.module.scss` 不超过 300 行；
- 禁止裸色值和 px 魔法数；
- 完成后执行 React Review；
- 滚动、悬浮、点击、浮层、折叠、多模块必须完整覆盖。

这些应分别落到：

```text
UI_README.md
    ↓ 编译/映射
policy.yaml
    ↓
preflight gate
runtime gate
visual gate
source-code gate
evidence gate
finalization gate
```

不是让模型“记得”，而是让它**无法绕过**。

---

# 二、新总架构：CarrorOS UI Autopilot v2

推荐将系统拆成七层。

```text
┌────────────────────────────────────────────────────────────┐
│ 1. Constitution Layer                                      │
│ UI_README.md / DECISIONS.md / kernel.md / policy.yaml      │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 2. Intake & Prototype Discovery                            │
│ URL、静态截图、路由、viewport、登录、交互与页面状态发现      │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 3. Design Knowledge Base                                   │
│ tokens.json / page-tree.json / interaction-inventory.yaml  │
│ measurements.json / reference screenshots                  │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 4. Deterministic Goal Orchestrator                          │
│ 状态机、任务队列、预算、租约、续跑、回滚、停滞检测            │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 5. Model Workers                                           │
│ DeepSeek V4 Flash / Kimi K3 / 主执行模型                    │
│ 每次只处理一个 bounded task                                │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 6. Browser & Visual Verification                           │
│ Playwright 精确测量 + Chrome DevTools 验证 + image diff     │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 7. CarrorOS Gates & Evidence                               │
│ C0–C8a、视觉门禁、Token 门禁、完整性门禁、晨报、Draft PR      │
└────────────────────────────────────────────────────────────┘
```

核心原则：

```text
文档定义规则
脚本控制流程
浏览器产生事实
视觉算法定位差异
模型提出和执行补丁
门禁决定是否接受
状态文件保证断点续跑
```

---

# 三、不要只有一个 Loop，要采用四层闭环

单纯：

```text
while similarity < 0.99:
    ask_model_to_fix()
```

会迅速陷入随机修改、震荡和 Token 浪费。

推荐四层循环。

## Loop 1：Run Loop

负责整个 6 小时 Goal：

```text
直到：
- 所有目标验收通过；
- 到达硬时间预算；
- 出现必须人工处理的阻塞；
- 系统持续停滞且升级模型后仍无法推进。
```

## Loop 2：Phase Loop

按顺序执行：

```text
DISCOVERY
→ TOKENS
→ SHELL
→ REGIONS
→ ELEMENTS
→ INTERACTIONS
→ RESPONSIVE
→ FINAL_AUDIT
```

前一阶段未过门禁，不允许进入后一阶段。

## Loop 3：Target Loop

一个阶段包含多个目标：

```text
regions:
  - sidebar
  - topbar
  - main-content
  - summary-cards
  - chart-panel
  - data-table
```

系统优先修复：

```text
视觉影响最大 × 置信度最高 × 修改风险最低
```

## Loop 4：Repair Loop

对一个目标最多连续尝试若干次：

```text
测量
→ 诊断
→ 补丁
→ 静态门禁
→ 截图
→ 比较
→ 接受或回滚
```

这四层必须由脚本实现，而不是完全写进 `night-loop.md` 让模型自由发挥。

---

# 四、状态机设计

## 4.1 状态定义

```python
from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    PREFLIGHT = "preflight"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    EXHAUSTED = "exhausted"
    FAILED = "failed"


class Phase(StrEnum):
    DISCOVERY = "discovery"
    TOKENS = "tokens"
    SHELL = "shell"
    REGIONS = "regions"
    ELEMENTS = "elements"
    INTERACTIONS = "interactions"
    RESPONSIVE = "responsive"
    FINAL_AUDIT = "final_audit"


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    PASSED = "passed"
    RETRYABLE = "retryable"
    ESCALATED = "escalated"
    BLOCKED = "blocked"
    FAILED = "failed"
```

## 4.2 合法转换

```python
PHASE_TRANSITIONS = {
    Phase.DISCOVERY: Phase.TOKENS,
    Phase.TOKENS: Phase.SHELL,
    Phase.SHELL: Phase.REGIONS,
    Phase.REGIONS: Phase.ELEMENTS,
    Phase.ELEMENTS: Phase.INTERACTIONS,
    Phase.INTERACTIONS: Phase.RESPONSIVE,
    Phase.RESPONSIVE: Phase.FINAL_AUDIT,
}
```

但不能直接调用 `next_phase()`，必须满足门禁：

```python
def can_advance(phase: Phase, report: "PhaseReport") -> bool:
    common = (
        report.blocking_errors == 0
        and report.required_evidence_complete
        and report.runtime_errors == 0
    )

    thresholds = {
        Phase.DISCOVERY: (
            report.route_coverage == 1.0
            and report.state_inventory_complete
            and report.scroll_coverage == 1.0
        ),
        Phase.TOKENS: (
            report.token_inventory_complete
            and report.token_compliance >= 0.995
        ),
        Phase.SHELL: (
            report.geometry_score >= 0.995
            and report.similarity >= 0.985
        ),
        Phase.REGIONS: (
            report.similarity >= 0.99
            and report.minimum_target_score >= 0.985
        ),
        Phase.ELEMENTS: (
            report.similarity >= 0.99
            and report.typography_score >= 0.99
            and report.color_score >= 0.99
        ),
        Phase.INTERACTIONS: (
            report.interaction_coverage == 1.0
            and report.state_coverage == 1.0
        ),
        Phase.RESPONSIVE: (
            report.viewport_coverage == 1.0
            and report.minimum_target_score >= 0.985
        ),
        Phase.FINAL_AUDIT: report.final_gate_passed,
    }

    return common and thresholds[phase]
```

---

# 五、Goal Manifest：把目标从自然语言变为机器契约

建议新增：

```text
.omc/ui-autopilot/{task-id}/goal.yaml
```

示例：

```yaml
schema_version: 2

run:
  id: dashboard-restoration-20260729
  task_name: dashboard-restoration
  mode: goal
  unattended: true

budget:
  wall_clock_seconds: 21600       # 6 小时
  graceful_shutdown_seconds: 300
  max_total_iterations: 120
  max_target_attempts: 8
  max_consecutive_no_progress: 4
  checkpoint_every_seconds: 60

prototype:
  base_url: https://prototype.example.com
  authentication:
    required: false
    strategy: existing_browser_session
    on_missing_session: block_and_notify
  routes:
    - id: dashboard
      prototype_path: /dashboard
      implementation_path: /dashboard

viewports:
  - id: desktop-1440
    width: 1440
    height: 900
    device_scale_factor: 1
    required: true
  - id: desktop-1920
    width: 1920
    height: 1080
    device_scale_factor: 1
    required: true

references:
  screenshot_document: .claude/UI_README.md
  additional_screenshots:
    - .omc/doc/dashboard/header.png
    - .omc/doc/dashboard/sidebar-expanded.png
    - .omc/doc/dashboard/sidebar-collapsed.png

discovery:
  scroll:
    enabled: true
    capture_full_page: true
    step_ratio: 0.75
    settle_ms: 400
  hover:
    enabled: true
    candidate_selectors:
      - button
      - a
      - "[role=button]"
      - "[aria-haspopup]"
      - "[data-tooltip]"
  click:
    enabled: true
    destructive_actions: deny
  overlays:
    required: true
  sidebar_states:
    - expanded
    - collapsed

acceptance:
  route_coverage: 1.0
  interaction_coverage: 1.0
  state_coverage: 1.0
  scroll_coverage: 1.0

  global_similarity: 0.99
  minimum_region_similarity: 0.985
  critical_region_similarity: 0.995

  geometry_score: 0.995
  typography_score: 0.99
  color_score: 0.99

  token_compliance: 1.0
  console_errors: 0
  runtime_errors: 0

  required_gates:
    - C1
    - C2
    - C3
    - C4
    - C5
    - C6
    - C7
    - C8
    - C8a

model_routing:
  default:
    model: deepseek-v4-flash
  visual_diagnosis:
    model: kimi-k3
    invocation_policy:
      only_when:
        - stagnation_count_gte: 2
        - ambiguous_visual_root_cause: true
        - critical_region_score_lt: 0.97
      max_calls_per_run: 8
  fallback:
    model: primary-governance-model

safety:
  allowed_paths:
    - src/pages/dashboard/**
    - src/features/dashboard/**
    - src/components/**
    - src/styles/tokens/**
    - tests/ui/dashboard/**
  denied_paths:
    - src/auth/**
    - src/router/**
    - .env*
    - package-lock.json
    - pnpm-lock.yaml
  max_files_per_patch: 8
  max_changed_lines_per_patch: 400
  rollback_on_regression: true
```

这份文件应该成为 Goal Loop 的唯一运行参数来源，而不是把预算和完成标准散落在多个 Markdown 中。

---

# 六、运行目录：所有过程必须可恢复、可审计

建议目录：

```text
.omc/
└── ui-autopilot/
    └── dashboard-restoration-20260729/
        ├── goal.yaml
        ├── run-state.json
        ├── heartbeat.json
        ├── event-log.jsonl
        ├── task-graph.json
        ├── score-history.jsonl
        ├── model-usage.jsonl
        ├── blockers.yaml
        ├── prototype/
        │   ├── page-tree.json
        │   ├── interactions.yaml
        │   ├── measurements.json
        │   ├── tokens.raw.json
        │   ├── tokens.normalized.json
        │   └── screenshots/
        ├── implementation/
        │   ├── measurements.json
        │   └── screenshots/
        ├── diffs/
        │   ├── dashboard/
        │   └── regions/
        ├── tasks/
        │   ├── task-0001.yaml
        │   ├── task-0001.result.json
        │   └── task-0001.patch
        ├── checkpoints/
        ├── evidence/
        └── reports/
            ├── final-report.md
            └── morning-report.md
```

特别重要的是：

- `run-state.json`：唯一运行状态；
- `event-log.jsonl`：只追加，便于审计和故障恢复；
- `score-history.jsonl`：用于判断进步、震荡和退化；
- `task-graph.json`：确保模型不会遗漏页面区域；
- `heartbeat.json`：CarrorOS 判断任务是否活着；
- `checkpoints/`：每次有效改善后保存可回滚点。

---

# 七、核心 Goal Loop：不能靠 Prompt 自己继续

下面给出核心控制器的参考实现。建议新增：

```text
scripts/ui_autopilot/
├── __init__.py
├── cli.py
├── config.py
├── domain.py
├── state_store.py
├── orchestrator.py
├── scheduler.py
├── verifier.py
├── checkpoints.py
├── stagnation.py
└── model_router.py
```

## 7.1 数据模型

```python
# scripts/ui_autopilot/domain.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStatus(StrEnum):
    CREATED = "created"
    PREFLIGHT = "preflight"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    EXHAUSTED = "exhausted"
    FAILED = "failed"


class Phase(StrEnum):
    DISCOVERY = "discovery"
    TOKENS = "tokens"
    SHELL = "shell"
    REGIONS = "regions"
    ELEMENTS = "elements"
    INTERACTIONS = "interactions"
    RESPONSIVE = "responsive"
    FINAL_AUDIT = "final_audit"


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    PASSED = "passed"
    RETRYABLE = "retryable"
    ESCALATED = "escalated"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(slots=True)
class Score:
    global_similarity: float = 0.0
    geometry: float = 0.0
    typography: float = 0.0
    color: float = 0.0
    minimum_region_similarity: float = 0.0
    interaction_coverage: float = 0.0
    state_coverage: float = 0.0
    route_coverage: float = 0.0
    scroll_coverage: float = 0.0
    token_compliance: float = 0.0
    runtime_errors: int = 0
    console_errors: int = 0

    def optimization_value(self) -> float:
        """
        用于判断一次补丁是否真正进步。

        这里有意对最差区域和几何给予较高权重，
        防止页面大面积背景把局部严重错误平均掉。
        """
        visual = (
            self.global_similarity * 0.25
            + self.minimum_region_similarity * 0.30
            + self.geometry * 0.25
            + self.typography * 0.10
            + self.color * 0.10
        )

        completeness = min(
            self.interaction_coverage,
            self.state_coverage,
            self.route_coverage,
            self.scroll_coverage,
        )

        error_penalty = min(
            0.25,
            self.runtime_errors * 0.05 + self.console_errors * 0.01,
        )

        return visual * 0.85 + completeness * 0.15 - error_penalty


@dataclass(slots=True)
class Task:
    id: str
    phase: Phase
    target_id: str
    target_type: str
    status: TaskStatus = TaskStatus.PENDING
    priority: float = 0.0
    attempts: int = 0
    stagnation_count: int = 0
    allowed_paths: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunState:
    run_id: str
    status: RunStatus
    phase: Phase
    started_at: str
    updated_at: str
    iteration: int = 0
    current_task_id: str | None = None
    best_score: Score = field(default_factory=Score)
    latest_score: Score = field(default_factory=Score)
    consecutive_no_progress: int = 0
    last_checkpoint: str | None = None
    blocker: dict[str, Any] | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()
```

---

## 7.2 原子化状态存储

长时间执行最怕：

- 进程被杀；
- 文件只写了一半；
- 状态和代码不一致；
- 两个 runner 同时操作同一任务。

状态写入必须采用临时文件 + 原子替换。

```python
# scripts/ui_autopilot/state_store.py

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .domain import RunState


class StateStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "run-state.json"
        self.events_path = run_dir / "event-log.jsonl"
        self.heartbeat_path = run_dir / "heartbeat.json"

    def initialize(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: RunState) -> None:
        payload = json.dumps(
            asdict(state),
            ensure_ascii=False,
            indent=2,
        )

        temp_path = self.state_path.with_suffix(".json.tmp")
        temp_path.write_text(payload, encoding="utf-8")

        # 确保内容落盘后再进行原子替换
        with temp_path.open("r+", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp_path, self.state_path)

    def append_event(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def write_heartbeat(self, payload: dict[str, Any]) -> None:
        temp_path = self.heartbeat_path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.heartbeat_path)
```

---

## 7.3 6 小时运行预算不是“模型调用次数”

现有方案中，类似 `/lx-goal` 的“12 小时 budget”如果只是 Prompt 中的预算概念，不能保证真实持续运行。

需要以真实 wall clock 控制。

```python
# scripts/ui_autopilot/budget.py

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunBudget:
    started_monotonic: float
    wall_clock_seconds: int
    graceful_shutdown_seconds: int
    max_total_iterations: int

    @classmethod
    def start(
        cls,
        *,
        wall_clock_seconds: int,
        graceful_shutdown_seconds: int,
        max_total_iterations: int,
    ) -> "RunBudget":
        return cls(
            started_monotonic=time.monotonic(),
            wall_clock_seconds=wall_clock_seconds,
            graceful_shutdown_seconds=graceful_shutdown_seconds,
            max_total_iterations=max_total_iterations,
        )

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_monotonic

    def remaining_seconds(self) -> float:
        return max(0.0, self.wall_clock_seconds - self.elapsed_seconds())

    def may_start_iteration(self, current_iteration: int) -> bool:
        enough_time = (
            self.remaining_seconds() > self.graceful_shutdown_seconds
        )
        enough_iterations = current_iteration < self.max_total_iterations
        return enough_time and enough_iterations
```

注意：

> 目标不是“必须空跑 6 小时”，而是“允许自主运行最多 6 小时且中途不因 Prompt 完成而退出”。

如果 3 小时就满足全部严格门禁，应该成功退出；如果 6 小时仍未达到 99%，则应保存证据和状态，以 `EXHAUSTED` 退出，下一次可以断点续跑，而不是谎报完成。

---

## 7.4 主控制器

```python
# scripts/ui_autopilot/orchestrator.py

from __future__ import annotations

import signal
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Protocol

from .budget import RunBudget
from .domain import RunState, RunStatus, Task, TaskStatus
from .state_store import StateStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Scheduler(Protocol):
    def next_task(self, state: RunState) -> Task | None: ...
    def mark_passed(self, task: Task) -> None: ...
    def mark_retryable(self, task: Task, reason: str) -> None: ...
    def escalate(self, task: Task, reason: str) -> None: ...
    def phase_complete(self, state: RunState) -> bool: ...
    def advance_phase(self, state: RunState) -> None: ...


class Worker(Protocol):
    def execute(self, task: Task) -> "WorkerResult": ...


class Verifier(Protocol):
    def capture_baseline(self, task: Task): ...
    def verify(self, task: Task, baseline): ...
    def accepts(self, baseline, verification) -> bool: ...
    def goal_satisfied(self, state: RunState) -> bool: ...


class CheckpointManager(Protocol):
    def create(self, label: str) -> str: ...
    def restore(self, checkpoint_id: str) -> None: ...


class GoalOrchestrator:
    def __init__(
        self,
        *,
        state: RunState,
        store: StateStore,
        budget: RunBudget,
        scheduler: Scheduler,
        worker: Worker,
        verifier: Verifier,
        checkpoints: CheckpointManager,
        max_target_attempts: int,
        max_consecutive_no_progress: int,
    ) -> None:
        self.state = state
        self.store = store
        self.budget = budget
        self.scheduler = scheduler
        self.worker = worker
        self.verifier = verifier
        self.checkpoints = checkpoints
        self.max_target_attempts = max_target_attempts
        self.max_consecutive_no_progress = max_consecutive_no_progress
        self.shutdown_requested = False

    def install_signal_handlers(self) -> None:
        def request_shutdown(signum, _frame) -> None:
            self.shutdown_requested = True
            self.store.append_event({
                "type": "shutdown_requested",
                "signal": signum,
                "timestamp": utc_now(),
            })

        signal.signal(signal.SIGTERM, request_shutdown)
        signal.signal(signal.SIGINT, request_shutdown)

    def run(self) -> RunState:
        self.install_signal_handlers()
        self.state.status = RunStatus.RUNNING
        self._persist("run_started")

        while self._should_continue():
            self._heartbeat()

            if self.verifier.goal_satisfied(self.state):
                self.state.status = RunStatus.SUCCEEDED
                self._persist("goal_satisfied")
                return self.state

            if self.scheduler.phase_complete(self.state):
                self.scheduler.advance_phase(self.state)
                self._persist("phase_advanced")
                continue

            task = self.scheduler.next_task(self.state)

            if task is None:
                self.state.status = RunStatus.BLOCKED
                self.state.blocker = {
                    "code": "NO_RUNNABLE_TASK",
                    "phase": self.state.phase.value,
                }
                self._persist("run_blocked")
                return self.state

            self._execute_task(task)

        if self.shutdown_requested:
            self.state.status = RunStatus.PAUSED
            event = "run_paused"
        else:
            self.state.status = RunStatus.EXHAUSTED
            event = "budget_exhausted"

        self._persist(event)
        return self.state

    def _execute_task(self, task: Task) -> None:
        self.state.iteration += 1
        self.state.current_task_id = task.id
        task.status = TaskStatus.RUNNING
        task.attempts += 1

        baseline = self.verifier.capture_baseline(task)
        checkpoint_id = self.checkpoints.create(
            f"{task.id}-attempt-{task.attempts}"
        )

        self.store.append_event({
            "type": "task_started",
            "task_id": task.id,
            "attempt": task.attempts,
            "checkpoint_id": checkpoint_id,
            "baseline": asdict(baseline.score),
            "timestamp": utc_now(),
        })

        try:
            result = self.worker.execute(task)
        except Exception as exc:
            self.checkpoints.restore(checkpoint_id)
            self.scheduler.mark_retryable(task, f"worker_error: {exc}")
            self._record_no_progress(task, str(exc))
            return

        if not result.success:
            self.checkpoints.restore(checkpoint_id)
            self.scheduler.mark_retryable(task, result.error or "unknown")
            self._record_no_progress(task, result.error)
            return

        task.status = TaskStatus.VERIFYING
        verification = self.verifier.verify(task, baseline)

        if self.verifier.accepts(baseline, verification):
            self.scheduler.mark_passed(task)
            self.state.latest_score = verification.score

            if (
                verification.score.optimization_value()
                > self.state.best_score.optimization_value()
            ):
                self.state.best_score = verification.score
                self.state.last_checkpoint = self.checkpoints.create(
                    f"best-{self.state.iteration}"
                )

            self.state.consecutive_no_progress = 0
            task.stagnation_count = 0

            self.store.append_event({
                "type": "patch_accepted",
                "task_id": task.id,
                "score": asdict(verification.score),
                "timestamp": utc_now(),
            })
        else:
            self.checkpoints.restore(checkpoint_id)
            self._record_no_progress(
                task,
                verification.rejection_reason,
            )

    def _record_no_progress(
        self,
        task: Task,
        reason: str | None,
    ) -> None:
        task.stagnation_count += 1
        self.state.consecutive_no_progress += 1

        if task.attempts >= self.max_target_attempts:
            self.scheduler.escalate(
                task,
                reason or "max attempts reached",
            )
        else:
            self.scheduler.mark_retryable(
                task,
                reason or "no measurable improvement",
            )

        self.store.append_event({
            "type": "no_progress",
            "task_id": task.id,
            "task_stagnation_count": task.stagnation_count,
            "run_stagnation_count": self.state.consecutive_no_progress,
            "reason": reason,
            "timestamp": utc_now(),
        })

    def _should_continue(self) -> bool:
        if self.shutdown_requested:
            return False

        if not self.budget.may_start_iteration(self.state.iteration):
            return False

        # 连续停滞不能直接成功或悄悄退出。
        # 实际实现中应进入诊断/升级队列。
        if (
            self.state.consecutive_no_progress
            >= self.max_consecutive_no_progress * 3
        ):
            self.state.status = RunStatus.BLOCKED
            self.state.blocker = {
                "code": "GLOBAL_STAGNATION",
                "count": self.state.consecutive_no_progress,
            }
            self._persist("global_stagnation")
            return False

        return True

    def _heartbeat(self) -> None:
        self.store.write_heartbeat({
            "run_id": self.state.run_id,
            "status": self.state.status.value,
            "phase": self.state.phase.value,
            "iteration": self.state.iteration,
            "current_task_id": self.state.current_task_id,
            "remaining_seconds": self.budget.remaining_seconds(),
            "timestamp": utc_now(),
        })

    def _persist(self, event_type: str) -> None:
        self.state.touch()
        self.store.save_state(self.state)
        self.store.append_event({
            "type": event_type,
            "run_id": self.state.run_id,
            "status": self.state.status.value,
            "phase": self.state.phase.value,
            "iteration": self.state.iteration,
            "timestamp": utc_now(),
        })
```

这里最重要的是：

1. 每个补丁前建 checkpoint；
2. 每个补丁后必须重新测量；
3. 没改善就回滚；
4. 改善后才进入 best checkpoint；
5. 模型调用失败不会结束总任务；
6. 任务失败会被重新调度或升级；
7. 预算耗尽会保存状态；
8. 进程终止信号会优雅暂停；
9. Goal 是否完成由 verifier 判断，不由模型声明。

---

# 八、补丁接受规则：不能只看全局 SSIM

如果只使用全局截图 SSIM，容易出现：

- 大面积白色背景抬高分数；
- 小按钮位置偏差被忽略；
- 字体错误不敏感；
- 弹窗没出现但静态页仍得高分；
- 页面缺少底部内容却因为 viewport 截图未覆盖而通过。

推荐使用复合指标。

```python
# scripts/ui_autopilot/acceptance.py

from dataclasses import dataclass

from .domain import Score


@dataclass(frozen=True, slots=True)
class VerificationResult:
    score: Score
    changed_pixels_ratio: float
    source_gates_passed: bool
    required_evidence_complete: bool
    regression_regions: tuple[str, ...]
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AcceptancePolicy:
    minimum_improvement: float = 0.0005
    maximum_allowed_regression: float = 0.001
    require_all_source_gates: bool = True
    reject_new_runtime_errors: bool = True

    def accepts(
        self,
        before: VerificationResult,
        after: VerificationResult,
    ) -> bool:
        if self.require_all_source_gates and not after.source_gates_passed:
            return False

        if not after.required_evidence_complete:
            return False

        if (
            self.reject_new_runtime_errors
            and after.score.runtime_errors > before.score.runtime_errors
        ):
            return False

        improvement = (
            after.score.optimization_value()
            - before.score.optimization_value()
        )

        if improvement < self.minimum_improvement:
            return False

        # 不允许通过改善背景来掩盖关键区域退化
        if after.regression_regions:
            return False

        return True
```

## 为什么每轮必须有“最小改善量”

因为 99% 附近可能出现测量噪声，例如字体栅格化或动画导致：

```text
0.98912
0.98918
0.98910
0.98917
```

如果不设有效改善阈值，系统会错误认为自己一直在推进。

---

# 九、停滞、震荡与回滚机制

仅检测“连续几次没提升”还不够，还要识别震荡：

```text
A → B → A → B
```

典型表现：

- 第一轮把 sidebar 改宽；
- 第二轮为了 main content 又把 sidebar 改窄；
- 第三轮重新改宽；
- 两个模型反复覆盖彼此。

建议给每次补丁建立 fingerprint：

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatchObservation:
    task_id: str
    changed_files: tuple[str, ...]
    normalized_diff: str
    score_before: float
    score_after: float

    def fingerprint(self) -> str:
        payload = {
            "task_id": self.task_id,
            "changed_files": sorted(self.changed_files),
            "normalized_diff": self.normalized_diff,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
```

升级策略：

```yaml
stagnation_policy:
  target:
    first_failure: retry_with_measurements
    second_failure: request_visual_diagnosis
    third_failure: narrow_scope_and_retry
    fourth_failure: escalate_model
    fifth_failure: freeze_target_and_continue_independent_targets
    eighth_failure: block_target

  global:
    repeated_patch_fingerprint: rollback_and_forbid
    alternating_geometry_values: lock_parent_geometry
    no_progress_iterations: 12
    action: produce_blocker_report
```

关键点：

> 某一个区域卡住，不应该让整个 6 小时任务立即退出。应冻结该区域，继续执行不依赖它的目标，最后再集中处理阻塞项。

---

# 十、任务调度不能按照 DOM 顺序，需要按照视觉影响排序

推荐优先级公式：

```python
def calculate_priority(task) -> float:
    return (
        task.visual_area_ratio * 0.25
        + task.current_error_severity * 0.30
        + task.descendant_count_ratio * 0.20
        + task.fix_confidence * 0.15
        + task.is_critical * 0.10
        - task.change_risk * 0.20
    )
```

这样会优先解决：

- 页面容器宽度；
- sidebar 宽度；
- header 高度；
- grid 列数；
- 大区域背景和边界；
- 会影响大量子元素的父布局。

而不是先调：

- 单个 icon 的 1px 偏移；
- 某个按钮的圆角；
- 一行文字的颜色。

推荐 Phase 内部顺序：

```text
1. viewport / root
2. app shell
3. primary layout tracks
4. region bounding boxes
5. component boxes
6. internal spacing
7. typography
8. colors / borders / shadows
9. icons
10. pseudo states / animations
```

---

# 十一、模型调用必须是 Bounded Task，不允许“继续优化整个页面”

错误 Prompt：

```text
请继续优化 dashboard，使它更接近原型。
```

这种 Prompt 会造成：

- 修改范围失控；
- 多区域互相影响；
- 无法判断补丁意图；
- 不能可靠回滚；
- 难以归因视觉得分变化。

正确的任务格式：

```yaml
task:
  id: region-dashboard-sidebar-004
  phase: regions
  target:
    page: dashboard
    state: sidebar-expanded
    viewport: desktop-1440
    region: sidebar

  objective:
    type: geometry_alignment
    before_score: 0.9412
    required_score: 0.985

  measured_differences:
    prototype:
      x: 0
      y: 0
      width: 256
      height: 900
    implementation:
      x: 0
      y: 0
      width: 240
      height: 900
    deltas:
      width: -16

  suspected_root_causes:
    - selector: "[data-ui-region=sidebar]"
      property: width
      confidence: 0.94
    - token: "--sidebar-width"
      confidence: 0.91

  allowed_files:
    - src/layouts/AppShell/AppShell.module.scss
    - src/styles/tokens/_geometry.scss

  forbidden_actions:
    - modify_router
    - modify_auth
    - add_dependency
    - edit_unrelated_regions
    - use_raw_color
    - bypass_token_system

  verification:
    command: python scripts/ui_autopilot/verify_task.py region-dashboard-sidebar-004
    minimum_improvement: 0.005

  output_contract:
    format: json
    fields:
      - diagnosis
      - changed_files
      - changed_properties
      - assumptions
      - verification_requested
```

模型每次只解决一个可验证问题。

---

# 十二、多模型路由：昂贵视觉模型只能用于诊断，不应承担普通编码

你提供：

- DeepSeek V4 Flash；
- Kimi K3，视觉关键时调用，价格高。

我的建议：

## DeepSeek V4 Flash

主要负责：

- 读取差异任务；
- 普通 CSS/React 修复；
- Token 迁移；
- 测试补全；
- 根据已有测量数据做局部调整；
- 低风险重复修复。

## Kimi K3

仅用于：

- 图片中区域语义识别；
- 无法通过像素差异判断根因；
- 原型 DOM 不可访问；
- 图表、复杂背景、插画等视觉结构判断；
- 连续两轮无进展；
- 关键区域低于阈值；
- 视觉差异被多个祖先布局因素耦合。

## 主治理模型

负责：

- Phase 规划；
- 冲突仲裁；
- 停滞根因判断；
- 是否退回上一层；
- 高风险补丁审查；
- 最终验收解释。

路由不能让执行模型自己决定，必须脚本化：

```python
# scripts/ui_autopilot/model_router.py

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutingContext:
    task_type: str
    stagnation_count: int
    visual_ambiguity: bool
    critical_region: bool
    current_score: float
    requires_image_understanding: bool


class ModelRouter:
    def choose(self, ctx: RoutingContext) -> str:
        if (
            ctx.requires_image_understanding
            and (
                ctx.visual_ambiguity
                or ctx.stagnation_count >= 2
                or (ctx.critical_region and ctx.current_score < 0.97)
            )
        ):
            return "kimi-k3"

        if ctx.stagnation_count >= 4:
            return "primary-governance-model"

        return "deepseek-v4-flash"
```

还要加调用额度：

```yaml
model_limits:
  kimi-k3:
    max_calls_per_run: 8
    max_calls_per_target: 2
    requires_artifacts:
      - reference_crop
      - implementation_crop
      - diff_crop
      - measurements
      - previous_attempts
```

昂贵模型每次调用必须同时得到：

1. 原型局部截图；
2. 实现局部截图；
3. diff 热力图；
4. 几何测量；
5. 已尝试补丁；
6. 明确问题。

否则是在浪费视觉模型能力。

---

# 十三、`night-loop.md` 应降级为 Worker Contract，而不是总控制器

现有事实集认为：

> `night-loop.md` 是执行模型的 prompt，它定义了一切。

这是现阶段最应改变的地方。

新版架构里：

```text
旧：
night-loop.md = 计划 + 循环 + 决策 + 执行 + 验收

新：
Python Orchestrator = 计划 + 循环 + 决策 + 验收
night-worker.md      = 单任务执行协议
```

建议保留 `night-loop.md` 作为人类可读规范，但运行时真正发送给模型的是精简后的 `night-worker.md`。

## 推荐的 `night-worker.md`

```md
# UI Autopilot Worker Contract

你是受 CarrorOS 管理的单任务 UI 修复执行器。

## 唯一职责

读取当前 task.yaml，完成其中一个有边界、可验证的 UI 修复任务。

## 禁止行为

1. 禁止自行结束总 Goal。
2. 禁止修改 allowed_files 之外的文件。
3. 禁止扩展任务范围。
4. 禁止跳过原型测量或验证。
5. 禁止以“看起来差不多”作为完成依据。
6. 禁止使用裸色值。
7. 禁止引入未登记的 px 魔法数。
8. 禁止绕过 C1–C8a。
9. 禁止删除失败测试或降低阈值。
10. 禁止修改截图、基准图或评分脚本来让门禁通过。

## 执行顺序

1. 读取 task.yaml。
2. 读取任务提供的原型测量、实现测量和 diff。
3. 仅分析当前 target 的根因。
4. 输出 patch plan。
5. 修改 allowed_files。
6. 执行 task 指定的静态检查。
7. 返回 result.json。
8. 不得声明总 Goal 已完成。

## 完成定义

你只能声明当前 patch 已生成。
是否接受 patch、是否进入下一任务、是否完成 Goal，
全部由外部 verifier 和 orchestrator 决定。

## 返回格式

{
  "task_id": "...",
  "success": true,
  "diagnosis": "...",
  "changed_files": ["..."],
  "changed_properties": ["..."],
  "assumptions": [],
  "risks": [],
  "recommended_next_measurement": "..."
}
```

这会显著降低模型“跑一段时间自行收尾”的概率，因为它根本没有总任务结束权。

---

# 十四、对“99%”目标的现实定义

99% 可以作为工程目标，但必须声明边界，否则不可证伪。

我建议将其定义为：

> 在冻结的浏览器版本、字体、DPR、viewport、数据集、动画状态和参考截图下，所有登记页面状态完成 100% 覆盖，关键区域达到既定几何和视觉阈值，复合视觉相似度不低于 99%。

需要固定：

```yaml
visual_environment:
  browser: chromium
  browser_version: pinned-by-playwright
  os_image: carroros-ui-runner-v2
  locale: zh-CN
  timezone: Asia/Shanghai
  color_scheme: light
  reduced_motion: reduce
  device_scale_factor: 1
  fonts:
    wait_until_ready: true
    missing_font_is_blocker: true
  network:
    external_requests: blocked
  data:
    fixture_set: dashboard-reference-v1
  animations:
    disabled_for_static_capture: true
```

否则同一页面在不同机器上可能因为字体抗锯齿就无法稳定达到 99%。

另外，应区分：

### 静态视觉 99%

冻结状态截图的视觉相似度。

### 完整性 100%

所有页面、滚动区、弹窗、hover、展开/折叠状态均已登记并验证。

### 交互正确性 100%

触发、关闭、Escape、点击外部、焦点、滚动锁定等语义正确。

三者缺一不可。不能静态首页 99%，但漏了底部内容和浮层，也称为“99% 完成”。

---

# 十五、第一阶段落地改造清单

基于你已有文件，第一轮不建议直接运行原型还原，而应先升级控制平面。

## 必须新增

```text
scripts/ui_autopilot/
├── cli.py
├── config.py
├── domain.py
├── budget.py
├── state_store.py
├── orchestrator.py
├── scheduler.py
├── verifier.py
├── acceptance.py
├── checkpoints.py
├── stagnation.py
├── model_router.py
└── heartbeat.py

.claude/workflows/frontend-overnight/
├── night-worker.md
├── goal.schema.json
├── task.schema.json
└── policy-map.yaml
```

## 必须修改

```text
.claude/workflows/frontend-overnight/night-loop.md
scripts/carroros-gates/run_all.py
scripts/carroros-gates/preflight.py
scripts/carroros-gates/evidence_check.py
scripts/carroros-gates/finalize_page.py
night-manifest.template.yaml
night-manifest.signoff.template.yaml
SOP.md
```

## 需要新增的门禁

```text
C0b  原型可访问/登录状态门禁
C0c  原型完整发现门禁
C5b  Token 合规门禁
C6b  分区域视觉门禁
C6c  交互状态覆盖门禁
C6d  全页面滚动覆盖门禁
C7b  Patch 范围与回归门禁
C8b  99% 验收证据门禁
```

不一定要破坏现有 C1–C8a 命名，也可以作为对应门禁的子项，但必须机器可执行。

---

# 十六、本篇最终判断

现有方案最关键的升级不是继续堆叠 Prompt，而是完成下面这个权力转移：

| 决策 | 旧方案 | 新方案 |
|---|---|---|
| 是否继续循环 | 模型 | Orchestrator |
| 当前修复目标 | 模型自行选择 | Task Scheduler |
| 是否接受补丁 | 模型/简单门禁 | Visual Verifier |
| 是否回滚 | 不稳定 | Checkpoint Manager |
| 是否调用 Kimi | 模型临时判断 | Model Router + 配额 |
| 是否完成 | 模型宣布 | Goal Acceptance Gate |
| 中断后续跑 | 上下文依赖 | 持久化状态机 |
| 6 小时预算 | Prompt 概念 | Wall-clock budget |
| UI_README 遵循 | 软提示 | 可执行 Policy Gates |
| 99% | 模糊目标 | 多维、分区域、全状态契约 |

最核心的一句话是：

> **不要让模型执行一个 6 小时的大任务；让确定性系统在 6 小时内持续给模型派发几分钟一个的可验证小任务。**

这才是从当前 80%～90% 且需要人工反复推动，升级到可长期无人值守、可恢复、可审计、可逼近 99% 的根本路径。




CarrorOS UI Autopilot v2：无人化高保真还原方案（第 2/5 部分）

本部分解决：如何完整理解原型，而不是只截一张首屏图。

目标是建立一个确定性的 Prototype Discovery & Capture Pipeline，自动发现并采集：

多页面、多路由；
完整纵向与横向滚动区域；
hover、focus、active、selected、disabled；
下拉菜单、Tooltip、Popover、Modal、Drawer；
侧边栏展开与收缩；
Tab、Accordion、分页、轮播；
固定、粘性、悬浮元素；
页面内部状态和跨模块状态；
每个状态的截图、DOM、几何、样式和交互证据。
这些结果会作为后续 Token 提取、分层视觉还原和 99% 验收的唯一基线。
一、现有方案的核心缺口：把“原型访问”误当成了“页面截图”

根据 UI_README.md 的铁律：



编码前先有 research.md + plan.md
做完一步立即更新 executor.md
失败立即留痕
无证据 = 没做
因此，打开原型并截一张首屏图，不足以作为实现依据。

当前问题通常表现为：



打开原型 URL
→ 截取初始 viewport
→ 让模型看图写页面
→ 视觉相似度达到 80%～90%
→ 人工发现底部、浮窗、hover、折叠或其他模块未实现
→ 再次手工推动
这实际上遗漏了原型的三个维度。

1. 空间维度

viewport 以下内容；
内部滚动容器；
横向滚动区域；
fixed、sticky 元素；
虚拟列表；
懒加载区域。
2. 状态维度

默认状态；
hover；
focus；
active；
selected；
expanded/collapsed；
open/closed；
enabled/disabled；
loading/empty/error/success；
有数据和无数据。
3. 路径维度

点击导航后的页面；
Tab 切换；
打开菜单后的选项；
弹窗内二级操作；
Drawer 中嵌套页面；
面包屑和返回；
分页后的内容；
侧边栏不同模块。
所以，一个原型不能建模为：



prototype:
  url: https://example.com/dashboard
  screenshot: dashboard.png
而应建模为一个有向状态图：



Prototype
├── Route
│   ├── Viewport
│   │   ├── Scroll position
│   │   ├── Interaction state
│   │   ├── Overlay state
│   │   └── Component state
│   └── Transition
└── Global state
二、原型事实模型：Page Graph，而不是 Screenshot List

推荐新增：



scripts/ui_autopilot/discovery/
├── models.py
├── browser.py
├── crawler.py
├── candidates.py
├── state_graph.py
├── interactions.py
├── scroll.py
├── capture.py
├── measurements.py
├── overlays.py
├── stabilization.py
├── redaction.py
└── report.py
2.1 核心数据结构



# scripts/ui_autopilot/discovery/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

class InteractionKind(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    HOVER = "hover"
    FOCUS = "focus"
    TOGGLE = "toggle"
    SELECT = "select"
    EXPAND = "expand"
    COLLAPSE = "collapse"
    OPEN_OVERLAY = "open_overlay"
    CLOSE_OVERLAY = "close_overlay"
    SWITCH_TAB = "switch_tab"
    NEXT_PAGE = "next_page"
    PREVIOUS_PAGE = "previous_page"

class StateKind(StrEnum):
    ROUTE = "route"
    SCROLL = "scroll"
    HOVER = "hover"
    FOCUS = "focus"
    MENU = "menu"
    TOOLTIP = "tooltip"
    POPOVER = "popover"
    MODAL = "modal"
    DRAWER = "drawer"
    SIDEBAR = "sidebar"
    TAB = "tab"
    ACCORDION = "accordion"
    PAGINATION = "pagination"
    COMPONENT = "component"

@dataclass(frozen=True, slots=True)
class Viewport:
    id: str
    width: int
    height: int
    device_scale_factor: float = 1.0

@dataclass(frozen=True, slots=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

@dataclass(slots=True)
class ElementIdentity:
    """
    稳定元素身份。

    selector 只是定位手段之一，不能单独作为元素身份：
    React 重渲染、动态 class、列表排序都可能使 selector 不稳定。
    """

    semantic_role: str | None = None
    accessible_name: str | None = None
    text_digest: str | None = None
    test_id: str | None = None
    dom_path_digest: str | None = None
    geometry_bucket: str | None = None

@dataclass(slots=True)
class InteractionCandidate:
    id: str
    identity: ElementIdentity
    kind: InteractionKind
    selector: str
    bounding_box: BoundingBox | None
    confidence: float
    destructive_risk: float
    expected_effect: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class PrototypeState:
    id: str
    route_id: str
    viewport_id: str
    kind: StateKind
    url: str
    title: str | None
    parent_state_id: str | None
    transition_id: str | None

    scroll_x: float = 0
    scroll_y: float = 0
    document_width: float = 0
    document_height: float = 0

    screenshot_path: str | None = None
    dom_snapshot_path: str | None = None
    measurement_path: str | None = None
    accessibility_path: str | None = None

    visible_overlays: list[str] = field(default_factory=list)
    fingerprints: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class StateTransition:
    id: str
    from_state_id: str

    // 需要补充断点


# CarrorOS UI Autopilot v2：第 2/5 部分（续）

下面续接 `PrototypeState`，完成原型全状态采集方案。核心产物不是截图集合，而是可回放、可去重、可验收的 `Page Graph`。

## 三、状态转换与页面图

```python
# scripts/ui_autopilot/discovery/models.py（续）

@dataclass(slots=True)
class StateTransition:
    id: str
    from_state_id: str
    to_state_id: str | None
    kind: InteractionKind
    candidate_id: str
    action: dict[str, Any]
    reversible: bool
    succeeded: bool = False
    blocked_reason: str | None = None


@dataclass(slots=True)
class PageGraph:
    states: dict[str, PrototypeState] = field(default_factory=dict)
    transitions: list[StateTransition] = field(default_factory=list)
    routes: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_state(self, state: PrototypeState) -> bool:
        fingerprint = state.fingerprints.get("visual_dom")
        if fingerprint and any(
            item.fingerprints.get("visual_dom") == fingerprint
            for item in self.states.values()
        ):
            return False
        self.states[state.id] = state
        return True
```

状态身份不能只使用 URL。打开 Modal、切换 Tab、收缩侧边栏时，URL 可能完全不变。推荐指纹：

```text
SHA256(
  canonical_url
  + viewport
  + normalized_visible_dom
  + accessibility_tree
  + overlay_inventory
  + quantized_geometry
  + perceptual_image_hash
)
```

视觉哈希只能辅助去重，不能单独决定状态相同。两个 Tab 可能布局相同但文本和交互语义不同。

## 四、浏览器环境必须完全冻结

原型和实现必须运行在同一采集环境：

```typescript
// scripts/ui-autopilot/browser/context.ts
import { chromium, type BrowserContext } from '@playwright/test';

export async function createCaptureContext(): Promise<BrowserContext> {
  const browser = await chromium.launch({
    headless: true,
    args: ['--font-render-hinting=none'],
  });

  return browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
  });
}
```

每次截图前执行稳定化：

```typescript
export async function stabilize(page: Page): Promise<void> {
  await page.waitForLoadState('domcontentloaded');
  await page.evaluate(() => document.fonts.ready);

  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-delay: 0s !important;
        animation-duration: 0s !important;
        caret-color: transparent !important;
        transition: none !important;
      }
    `,
  });

  await page.waitForFunction(() => {
    const images = [...document.images];
    return images.every(image => image.complete);
  });

  await waitForVisualSilence(page, {
    consecutiveFrames: 3,
    intervalMs: 150,
    maximumWaitMs: 5000,
  });
}
```

`networkidle` 不能作为唯一稳定条件：轮询、WebSocket 和持续请求会使它永不满足；页面无请求也不代表布局已稳定。

## 五、候选交互元素自动发现

优先使用语义和 ARIA，不依赖动态 class：

```typescript
// scripts/ui-autopilot/discovery/candidates.ts
export async function discoverCandidates(page: Page) {
  return page.locator(`
    button,
    a[href],
    input,
    select,
    summary,
    [role="button"],
    [role="tab"],
    [role="menuitem"],
    [role="checkbox"],
    [role="switch"],
    [aria-expanded],
    [aria-haspopup],
    [data-tooltip],
    [tabindex]:not([tabindex="-1"])
  `).evaluateAll(elements => elements.flatMap((element, index) => {
    const node = element as HTMLElement;
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);

    if (
      rect.width < 2 ||
      rect.height < 2 ||
      style.visibility === 'hidden' ||
      style.display === 'none'
    ) {
      return [];
    }

    return [{
      index,
      tag: node.tagName.toLowerCase(),
      role: node.getAttribute('role'),
      name: node.getAttribute('aria-label')
        ?? node.getAttribute('title')
        ?? node.innerText.trim().slice(0, 120),
      expanded: node.getAttribute('aria-expanded'),
      hasPopup: node.getAttribute('aria-haspopup'),
      href: node.getAttribute('href'),
      disabled: node.matches(':disabled,[aria-disabled="true"]'),
      box: {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      },
    }];
  }));
}
```

随后对候选项分类：

| 特征 | 推断动作 |
|---|---|
| `role=tab` | 切换 Tab |
| `aria-expanded=false` | 展开 |
| `aria-haspopup=menu` | 打开菜单 |
| `aria-haspopup=dialog` | 打开弹窗 |
| `title`、`data-tooltip` | hover |
| 内部链接 | 路由导航 |
| checkbox/switch | toggle |
| 无语义但可点击 | 低置信度 click，需风险检测 |

## 六、安全探索与破坏性操作拦截

无人探索不能点击删除、支付、提交、退出登录等操作：

```yaml
discovery_policy:
  deny_text_patterns:
    - 删除
    - 清空
    - 注销
    - 退出登录
    - 支付
    - 提交订单
    - 确认发布
    - delete
    - remove
    - logout
    - pay
    - submit

  deny_attributes:
    data-danger: "true"

  deny_navigation:
    - external_origin
    - download
    - mailto
    - tel

  unknown_action:
    policy: capture_only
```

执行动作前保存浏览器状态；动作后若出现下载、跨域、确认框或数据突变，立即关闭当前 context，从初始状态重放。

## 七、滚动不是只做一次 `fullPage` 截图

必须同时扫描：

1. 文档滚动；
2. 内部纵向滚动容器；
3. 横向滚动容器；
4. 懒加载触发后的新增内容；
5. sticky/fixed 元素在不同滚动位置的状态。

```typescript
export async function discoverScrollContainers(page: Page) {
  return page.evaluate(() => [...document.querySelectorAll<HTMLElement>('*')]
    .flatMap((element, index) => {
      const style = getComputedStyle(element);
      const vertical = element.scrollHeight > element.clientHeight + 2
        && /(auto|scroll)/.test(style.overflowY);
      const horizontal = element.scrollWidth > element.clientWidth + 2
        && /(auto|scroll)/.test(style.overflowX);

      if (!vertical && !horizontal) return [];

      const rect = element.getBoundingClientRect();
      return [{
        index,
        vertical,
        horizontal,
        clientWidth: element.clientWidth,
        clientHeight: element.clientHeight,
        scrollWidth: element.scrollWidth,
        scrollHeight: element.scrollHeight,
        box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      }];
    }));
}
```

滚动采集采用重叠窗口，避免遗漏边界内容：

```python
def scroll_positions(total: int, viewport: int, ratio: float = 0.75) -> list[int]:
    if total <= viewport:
        return [0]

    step = max(1, int(viewport * ratio))
    positions = list(range(0, total - viewport + 1, step))
    last = total - viewport

    if positions[-1] != last:
        positions.append(last)

    return positions
```

每次滚动后再次运行稳定化和候选发现。若文档高度增长，则继续遍历，直到连续两轮高度与 DOM 指纹不再变化。

## 八、Overlay 必须单独建状态

不能只检测 `.modal`。应同时基于 ARIA、几何层和遮罩识别：

```typescript
export async function inspectOverlays(page: Page) {
  return page.evaluate(() => [...document.querySelectorAll<HTMLElement>('*')]
    .flatMap(element => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const role = element.getAttribute('role');
      const zIndex = Number.parseInt(style.zIndex, 10);

      const semantic = ['dialog', 'menu', 'tooltip', 'listbox']
        .includes(role ?? '');
      const elevated = ['fixed', 'absolute'].includes(style.position)
        && Number.isFinite(zIndex)
        && zIndex >= 100;

      if ((!semantic && !elevated) || rect.width < 2 || rect.height < 2) {
        return [];
      }

      return [{
        role,
        ariaModal: element.getAttribute('aria-modal'),
        zIndex,
        position: style.position,
        box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      }];
    }));
}
```

每个浮层至少验证：

- 正确触发；
- 内容和位置；
- 遮罩；
- 层级；
- 页面滚动是否锁定；
- Escape 关闭；
- 点击外部关闭；
- 关闭后焦点返回；
- 嵌套浮层状态。

## 九、BFS 状态遍历与预算控制

状态图推荐广度优先，先保证覆盖，再深入嵌套路径：

```python
from collections import deque

class PrototypeCrawler:
    def crawl(self, initial_state: PrototypeState) -> PageGraph:
        queue = deque([initial_state])
        graph = PageGraph()
        graph.add_state(initial_state)

        while queue and not self.budget.exhausted():
            state = queue.popleft()
            self.browser.restore(state)
            candidates = self.candidates.discover()

            for candidate in self.rank(candidates):
                if not self.policy.allows(candidate):
                    self.record_blocked(state, candidate)
                    continue

                before = self.capture.snapshot()
                outcome = self.interactions.execute(candidate)

                if not outcome.changed:
                    self.record_no_effect(state, candidate)
                    continue

                discovered = self.capture.current_state(
                    parent=state,
                    transition=outcome.transition,
                )
                self.graph.add_transition(outcome.transition)

                if graph.add_state(discovered):
                    queue.append(discovered)

                self.browser.restore_from_snapshot(before)

        return graph
```

必须设置防爆炸限制：

```yaml
discovery_budget:
  max_states_per_route: 120
  max_depth: 5
  max_actions_per_state: 40
  max_same_kind_siblings: 12
  max_pagination_samples: 3
  max_table_row_actions: 3
  max_runtime_seconds: 3600
```

相同结构的 100 行表格无需逐行点击。选取首行、中间行、末行代表性样本，并记录等价类。

## 十、原型截图文档如何接入

你提供的静态截图不能仅作为 Prompt 图片，需要登记到 `reference-map.yaml`：

```yaml
references:
  - id: dashboard-default
    file: .omc/doc/dashboard/default.png
    route: dashboard
    viewport: desktop-1440
    state:
      sidebar: expanded
      scroll: top

  - id: dashboard-user-menu
    file: .omc/doc/dashboard/user-menu.png
    route: dashboard
    viewport: desktop-1440
    transition:
      action: click
      target:
        role: button
        accessible_name: 用户菜单

  - id: dashboard-sidebar-collapsed
    file: .omc/doc/dashboard/sidebar-collapsed.png
    route: dashboard
    state:
      sidebar: collapsed
```

若截图没有 viewport、滚动位置或触发方式，标记为 `UNRESOLVED_REFERENCE`，不允许模型自行猜测。

## 十一、发现阶段门禁 C0c

建议在现有 `preflight.py` 与 `run_all.py` 前增加 C0c：

```yaml
C0c:
  required:
    - page_graph_exists
    - all_manifest_routes_visited
    - all_required_viewports_captured
    - full_document_scroll_scanned
    - nested_scroll_containers_scanned
    - required_reference_images_mapped
    - required_interactions_resolved
    - screenshots_have_digest
    - measurements_have_digest
    - no_unresolved_authentication
```

验收逻辑：

```python
def validate_discovery(report: dict) -> list[str]:
    errors: list[str] = []

    exact_requirements = {
        "route_coverage": 1.0,
        "viewport_coverage": 1.0,
        "required_reference_coverage": 1.0,
        "required_interaction_coverage": 1.0,
        "scroll_coverage": 1.0,
    }

    for key, expected in exact_requirements.items():
        if report.get(key) != expected:
            errors.append(f"{key}: expected {expected}, got {report.get(key)}")

    if report.get("unresolved_states"):
        errors.append("存在未解析的必需状态")

    if report.get("authentication_blocked"):
        errors.append("原型认证尚未完成")

    return errors
```

这与 `UI_README.md` 的“失败立即留痕、无证据=没做”一致。发现不完整时不能进入 Token 和编码阶段。

## 十二、本阶段最终产物

```text
prototype/
├── page-graph.json
├── route-inventory.yaml
├── interaction-inventory.yaml
├── scroll-inventory.yaml
├── reference-map.yaml
├── unresolved-states.yaml
├── coverage-report.json
├── screenshots/
│   └── {route}/{viewport}/{state-id}.png
├── dom/
│   └── {state-id}.json
├── accessibility/
│   └── {state-id}.json
└── measurements/
    └── {state-id}.json
```

发现阶段完成标准不是“已经看过原型”，而是：

```text
所有声明路由 × 所有必需 viewport × 所有必需交互状态
都具有可回放路径、稳定截图、DOM/ARIA/几何证据和内容摘要。
```

至此，第 2 部分完整结束。第 3 部分将进入 **Design Token 自动提取、值聚类、语义命名、Tailwind/CSS Variables 生成，以及裸值迁移门禁**。


# CarrorOS UI Autopilot v2：无人化高保真还原方案（第 3/5 部分）

> 本部分完整解决 **Design Token 自动提取、聚类、语义化、Tailwind/Ant Design 接入、现有裸值迁移，以及 Token 门禁**。
>
> 核心目标不是简单生成一份颜色表，而是建立一套闭环：
>
> ```text
> 原型事实采集
> → 值归一化
> → 聚类去噪
> → 基础 Token
> → 语义 Token
> → 组件 Token
> → Tailwind / Ant Design / CSS Variables 消费
> → 裸值扫描
> → 自动迁移
> → 视觉回归
> → Token 锁定
> ```
>
> Token 阶段必须在整体布局编码前基本完成，并在后续迭代中允许**受控增量修正**。否则模型会在每个区域重复发明颜色、间距、圆角和阴影，最终即使局部接近原型，整体风格仍然不统一。

---

# 一、为什么 Token 系统是 90% → 99% 的关键

当前高保真还原容易卡在 80%～90%，通常不是因为模型不会写 CSS，而是缺少统一约束。

例如原型中的卡片间距实际是 `16px`，不同模型可能分别写成：

```tsx
<div className="gap-4" />
<div style={{ gap: 15 }} />
<div className="gap-[17px]" />
<div className={styles.cardGrid} />
```

对应 CSS：

```scss
.cardGrid {
  gap: 1rem;
}
```

它们视觉上暂时接近，但系统内部已经出现多个表示：

```text
16px
15px
17px
1rem
gap-4
```

类似问题会扩散到：

- 页面背景；
- 卡片背景；
- 边框；
- 主色；
- 次级文字；
- 字号；
- 行高；
- 圆角；
- 阴影；
- 控件高度；
- sidebar 宽度；
- header 高度；
- 内容区 padding；
- z-index；
- 动画时长。

缺少 Token 系统会造成四种直接损失。

## 1. 一致性损失

同一层级组件出现不同颜色、圆角和间距。

## 2. 修复效率损失

原型主色判断错误时，需要改几十个文件，而不是改一个变量。

## 3. 模型上下文损失

每个模型都要重新判断“这个颜色是什么”“这个间距是多少”。

## 4. 收敛损失

自动修复器不断产生新的近似值，视觉指标在高分区间震荡，无法稳定逼近目标。

因此 Token 不是最后的代码清理项，而是：

> **视觉搜索空间压缩器。**

原本模型可能从任意 CSS 值中选择；Token 化后，模型只能从有限、稳定、来自原型的值集合中选择。

---

# 二、Token 分层模型

推荐采用五层 Token，不要只生成一个扁平 `tokens.json`。

```text
Layer 0：Raw Observations
原型中实际观测到的值，保留来源和频率

Layer 1：Primitive Tokens
无语义基础值，如 color.blue.600、space.4、radius.md

Layer 2：Semantic Tokens
语义值，如 color.text.primary、color.surface.page

Layer 3：Component Tokens
组件级值，如 card.radius、sidebar.width、button.height

Layer 4：State Tokens
hover、active、selected、disabled、focus、open 等状态值
```

示例：

```yaml
raw:
  colors:
    - value: "#1677ff"
      occurrences: 46
    - value: "rgb(22, 119, 255)"
      occurrences: 11

primitive:
  color:
    blue:
      600: "#1677ff"

semantic:
  color:
    action:
      primary: "{primitive.color.blue.600}"
    border:
      focus: "{primitive.color.blue.600}"

component:
  button:
    primary:
      background: "{semantic.color.action.primary}"

state:
  button:
    primary:
      hover:
        background: "{primitive.color.blue.500}"
```

这使系统能区分：

```text
“值相同”
与
“语义相同”
```

例如 `#1677ff` 可能同时用于主按钮背景和 focus ring，但它们的语义不能永久绑定在一起。未来原型可能只调整 focus 颜色。

---

# 三、Token 目录结构

建议建立统一目录：

```text
src/
├── styles/
│   ├── tokens/
│   │   ├── generated/
│   │   │   ├── primitives.css
│   │   │   ├── semantics.css
│   │   │   ├── components.css
│   │   │   ├── states.css
│   │   │   ├── tokens.ts
│   │   │   └── tokens.json
│   │   ├── aliases.css
│   │   ├── overrides.css
│   │   ├── index.css
│   │   └── README.md
│   └── globals.css
├── theme/
│   ├── antd-theme.ts
│   └── theme-provider.tsx
└── app/
```

自动化产物和人工维护内容必须分开：

```text
generated/     只能由生成器修改
aliases.css    语义别名，可审查修改
overrides.css  有证据的例外
```

禁止模型直接编辑：

```text
src/styles/tokens/generated/**
```

模型需要新增 Token 时，应修改：

```text
.omc/ui-autopilot/{run-id}/prototype/tokens.normalized.json
```

然后重新运行生成器。

---

# 四、原型 Token 事实采集

第 2 部分已经采集了所有关键状态。Token 提取不能只在默认页面执行，必须覆盖：

```text
所有路由
× 必需 viewport
× 默认状态
× hover/focus/active
× 弹窗/菜单/Drawer
× 展开/收缩
× 页面顶部/中部/底部
```

否则会漏掉：

- 菜单阴影；
- Tooltip 背景；
- Modal 圆角；
- Drawer 宽度；
- hover 颜色；
- selected 状态；
- disabled 透明度；
- 底部区域背景；
- 粘性 header 阴影。

## 4.1 浏览器侧样式采集器

```typescript
// scripts/ui-autopilot/tokens/extractStyles.ts

import type { Page } from '@playwright/test';

const STYLE_PROPERTIES = [
  'color',
  'background-color',
  'border-top-color',
  'border-right-color',
  'border-bottom-color',
  'border-left-color',
  'border-top-width',
  'border-right-width',
  'border-bottom-width',
  'border-left-width',
  'border-top-left-radius',
  'border-top-right-radius',
  'border-bottom-right-radius',
  'border-bottom-left-radius',
  'box-shadow',
  'font-family',
  'font-size',
  'font-weight',
  'line-height',
  'letter-spacing',
  'opacity',
  'gap',
  'row-gap',
  'column-gap',
  'padding-top',
  'padding-right',
  'padding-bottom',
  'padding-left',
  'margin-top',
  'margin-right',
  'margin-bottom',
  'margin-left',
  'width',
  'height',
  'min-width',
  'min-height',
  'max-width',
  'max-height',
  'z-index',
] as const;

export interface ExtractedStyle {
  stateId: string;
  selectorHint: string;
  role: string | null;
  accessibleName: string | null;
  tagName: string;
  visible: boolean;
  box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  styles: Record<string, string>;
}

export async function extractComputedStyles(
  page: Page,
  stateId: string,
): Promise<ExtractedStyle[]> {
  return page.evaluate(
    ({ properties, stateId }) => {
      const isVisible = (element: HTMLElement): boolean => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);

        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          Number.parseFloat(style.opacity || '1') > 0
        );
      };

      const selectorHint = (element: HTMLElement): string => {
        const testId = element.dataset.testid;
        if (testId) return `[data-testid="${testId}"]`;

        const region = element.dataset.uiRegion;
        if (region) return `[data-ui-region="${region}"]`;

        if (element.id) return `#${CSS.escape(element.id)}`;

        const role = element.getAttribute('role');
        const ariaLabel = element.getAttribute('aria-label');

        if (role && ariaLabel) {
          return `[role="${role}"][aria-label="${ariaLabel}"]`;
        }

        return element.tagName.toLowerCase();
      };

      return [...document.querySelectorAll<HTMLElement>('body *')]
        .filter(isVisible)
        .map(element => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();

          const styles = Object.fromEntries(
            properties.map(property => [
              property,
              style.getPropertyValue(property).trim(),
            ]),
          );

          return {
            stateId,
            selectorHint: selectorHint(element),
            role: element.getAttribute('role'),
            accessibleName:
              element.getAttribute('aria-label') ??
              element.getAttribute('title') ??
              element.innerText?.trim().slice(0, 120) ??
              null,
            tagName: element.tagName.toLowerCase(),
            visible: true,
            box: {
              x: rect.x,
              y: rect.y,
              width: rect.width,
              height: rect.height,
            },
            styles,
          };
        });
    },
    {
      properties: STYLE_PROPERTIES,
      stateId,
    },
  );
}
```

## 4.2 伪元素采集

按钮装饰、角标、分隔线可能存在于 `::before` / `::after`：

```typescript
export async function extractPseudoStyles(page: Page, stateId: string) {
  return page.evaluate(({ stateId }) => {
    const properties = [
      'content',
      'color',
      'background-color',
      'width',
      'height',
      'border-radius',
      'box-shadow',
      'position',
      'inset',
      'top',
      'right',
      'bottom',
      'left',
    ];

    return [...document.querySelectorAll<HTMLElement>('body *')]
      .flatMap((element, index) =>
        ['::before', '::after'].flatMap(pseudo => {
          const style = getComputedStyle(element, pseudo);

          if (!style.content || style.content === 'none') return [];

          return [{
            stateId,
            elementIndex: index,
            pseudo,
            styles: Object.fromEntries(
              properties.map(property => [
                property,
                style.getPropertyValue(property).trim(),
              ]),
            ),
          }];
        }),
      );
  }, { stateId });
}
```

## 4.3 CSS 自定义变量采集

如果原型本身已有 Token，应优先读取，而不是从计算值反向猜测：

```typescript
export async function extractCustomProperties(page: Page) {
  return page.evaluate(() => {
    const result: Record<string, string> = {};

    for (const sheet of [...document.styleSheets]) {
      try {
        for (const rule of [...sheet.cssRules]) {
          if (!(rule instanceof CSSStyleRule)) continue;

          for (const name of [...rule.style]) {
            if (name.startsWith('--')) {
              result[name] = rule.style.getPropertyValue(name).trim();
            }
          }
        }
      } catch {
        // 跨域 stylesheet 不可读，记录到采集报告，不中断整个流程。
      }
    }

    const rootStyle = getComputedStyle(document.documentElement);

    for (const name of Object.keys(result)) {
      const resolved = rootStyle.getPropertyValue(name).trim();
      if (resolved) result[name] = resolved;
    }

    return result;
  });
}
```

优先级：

```text
原型公开 CSS Variables
> 原型可访问样式表声明
> computed style 聚类
> 截图像素取色
> 视觉模型推断
```

截图取色和视觉模型只应作为降级手段。

---

# 五、建立 Raw Observation 数据库

每个值必须保留来源，不能只输出去重后的列表。

```python
# scripts/ui_autopilot/tokens/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TokenObservation:
    category: str
    property_name: str
    raw_value: str
    normalized_value: str

    route_id: str
    state_id: str
    viewport_id: str

    selector_hint: str
    role: str | None
    accessible_name: str | None

    visible_area: float
    element_width: float
    element_height: float

    source_kind: str = "computed_style"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TokenCluster:
    id: str
    category: str
    canonical_value: str
    observations: list[TokenObservation] = field(default_factory=list)

    frequency: int = 0
    weighted_frequency: float = 0.0
    confidence: float = 0.0
    proposed_primitive_name: str | None = None
    proposed_semantic_names: list[str] = field(default_factory=list)
```

推荐输出：

```text
prototype/
├── tokens.raw.jsonl
├── tokens.normalized.json
├── token-clusters.json
├── token-semantic-map.yaml
└── token-evidence/
    ├── colors/
    ├── spacing/
    ├── typography/
    └── geometry/
```

每个 Token 都应可追溯到：

- 哪个路由；
- 哪个页面状态；
- 哪个元素；
- 哪个 CSS 属性；
- 出现多少次；
- 视觉面积权重；
- 哪张证据截图。

---

# 六、值归一化

聚类前必须将表达形式统一。

## 6.1 颜色归一化

以下表达应视为同值：

```css
#fff
#ffffff
rgb(255, 255, 255)
rgba(255, 255, 255, 1)
hsl(0 0% 100%)
```

统一转成带 alpha 的八位十六进制或结构体：

```python
# scripts/ui_autopilot/tokens/normalize.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rgba:
    r: int
    g: int
    b: int
    a: float

    def to_hex(self) -> str:
        alpha = round(self.a * 255)
        if alpha == 255:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{alpha:02x}"


def composite(foreground: Rgba, background: Rgba) -> Rgba:
    alpha = foreground.a + background.a * (1 - foreground.a)

    if alpha == 0:
        return Rgba(0, 0, 0, 0)

    return Rgba(
        r=round(
            (
                foreground.r * foreground.a
                + background.r * background.a * (1 - foreground.a)
            )
            / alpha
        ),
        g=round(
            (
                foreground.g * foreground.a
                + background.g * background.a * (1 - foreground.a)
            )
            / alpha
        ),
        b=round(
            (
                foreground.b * foreground.a
                + background.b * background.a * (1 - foreground.a)
            )
            / alpha
        ),
        a=alpha,
    )
```

需要同时保留：

```yaml
declared_color: rgba(0, 0, 0, 0.65)
effective_color: "#595959"
background_context: "#ffffff"
```

否则半透明文字在不同背景下会被误聚类。

## 6.2 长度归一化

统一到 CSS pixel：

```text
1rem      → 根据根字号计算
0.5em     → 根据元素字号计算
12pt      → 转为 px
calc(...) → 使用 computed style 最终值
normal    → 需要根据浏览器实际计算
```

保留浮点值，不要过早四舍五入：

```python
@dataclass(frozen=True, slots=True)
class LengthValue:
    css_px: float
    raw_value: str
    context_font_size: float | None
```

## 6.3 字体归一化

```text
"Inter", Arial, sans-serif
Inter, Arial, sans-serif
```

应归一为字体栈数组：

```json
["Inter", "Arial", "sans-serif"]
```

字重统一到数值：

```text
normal    → 400
bold      → 700
medium    → 原型字体映射，通常为 500
semibold  → 600
```

## 6.4 阴影归一化

阴影不能作为纯字符串处理，应解析成层：

```typescript
interface ShadowLayer {
  inset: boolean;
  offsetX: number;
  offsetY: number;
  blur: number;
  spread: number;
  color: string;
}
```

示例：

```json
{
  "layers": [
    {
      "inset": false,
      "offsetX": 0,
      "offsetY": 2,
      "blur": 8,
      "spread": 0,
      "color": "#00000014"
    }
  ]
}
```

## 6.5 无效值过滤

以下值不应直接进入 Token 候选：

```text
auto
none
normal（未解析时）
fit-content
max-content
min-content
0px（部分类型需保留）
透明且无视觉效果的颜色
由内容自然产生的动态 width/height
transform matrix
临时动画中间值
```

但 `0` 不能统一删除，它在圆角、边框和间距体系中可能有明确意义。

---

# 七、值聚类：解决截图噪声和近似值膨胀

原型中可能观察到：

```text
15.98px
16px
16.02px
```

它们多数来自缩放、布局计算或子像素，不应生成三个 Token。

## 7.1 几何值聚类

```python
# scripts/ui_autopilot/tokens/cluster_lengths.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LengthPoint:
    value: float
    weight: float
    observation_id: str


def cluster_lengths(
    points: list[LengthPoint],
    tolerance_px: float = 0.5,
) -> list[list[LengthPoint]]:
    if not points:
        return []

    sorted_points = sorted(points, key=lambda item: item.value)
    clusters: list[list[LengthPoint]] = [[sorted_points[0]]]

    for point in sorted_points[1:]:
        cluster = clusters[-1]
        center = weighted_median(cluster)

        if abs(point.value - center) <= tolerance_px:
            cluster.append(point)
        else:
            clusters.append([point])

    return clusters


def weighted_median(points: list[LengthPoint]) -> float:
    ordered = sorted(points, key=lambda item: item.value)
    total_weight = sum(item.weight for item in ordered)
    cumulative = 0.0

    for item in ordered:
        cumulative += item.weight
        if cumulative >= total_weight / 2:
            return item.value

    return ordered[-1].value
```

不同类别使用不同容差：

```yaml
clustering:
  spacing:
    tolerance_px: 0.5
  radius:
    tolerance_px: 0.5
  border_width:
    tolerance_px: 0.25
  font_size:
    tolerance_px: 0.25
  line_height:
    tolerance_px: 0.5
  component_geometry:
    tolerance_px: 1.0
```

## 7.2 颜色聚类

颜色不应只比较 RGB 欧氏距离，推荐转到 OKLab/OKLCH 或 Lab 空间后计算感知距离。

```python
@dataclass(frozen=True, slots=True)
class Oklab:
    lightness: float
    a: float
    b: float
    alpha: float


def color_distance(left: Oklab, right: Oklab) -> float:
    color_delta = (
        (left.lightness - right.lightness) ** 2
        + (left.a - right.a) ** 2
        + (left.b - right.b) ** 2
    ) ** 0.5

    alpha_delta = abs(left.alpha - right.alpha)
    return color_delta + alpha_delta * 0.25
```

建议：

```yaml
color_clustering:
  exact_computed_styles:
    distance_threshold: 0.002
  screenshot_sampled_colors:
    distance_threshold: 0.012
  preserve_distinct_when:
    - different_interaction_state
    - different_semantic_role
    - contrast_boundary_crossed
```

即使两个颜色视觉接近，若一个用于 `text-primary`、另一个用于 `text-secondary`，也不能盲目合并。

## 7.3 频率不能是唯一依据

Token 重要度应考虑：

```python
def observation_weight(observation: TokenObservation) -> float:
    area_weight = min(
        4.0,
        max(0.25, observation.visible_area / 10_000),
    )

    semantic_weight = {
        "banner": 1.5,
        "navigation": 1.4,
        "heading": 1.3,
        "button": 1.2,
        "dialog": 1.4,
        "generic": 1.0,
    }.get(observation.role or "generic", 1.0)

    source_weight = {
        "prototype_variable": 2.0,
        "stylesheet_declaration": 1.5,
        "computed_style": 1.0,
        "screenshot_sample": 0.5,
        "vision_inference": 0.3,
    }.get(observation.source_kind, 1.0)

    return area_weight * semantic_weight * source_weight
```

例如页面背景只出现一次，但覆盖整个页面，显然比表格中偶发的一个颜色更重要。

---

# 八、识别间距系统，而不是机械收录所有距离

Token 提取不应将所有 `margin-left: 13px` 都收入间距集合。很多值可能是布局结果，而非设计 Token。

需要区分：

## 1. 设计间距

- 容器 padding；
- Grid gap；
- Stack gap；
- 卡片内边距；
- 表单项间距；
- 标题与正文间距。

## 2. 几何尺寸

- sidebar 宽度；
- header 高度；
- 输入框高度；
- Avatar 尺寸；
- icon 尺寸。

## 3. 偶然布局值

- flex 分配后的宽度；
- 文本内容撑开的宽度；
- 百分比计算结果；
- viewport 变化后的动态尺寸。

候选规则：

```python
TOKENIZABLE_LENGTH_PROPERTIES = {
    "gap",
    "row-gap",
    "column-gap",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "border-radius",
    "border-width",
    "font-size",
    "line-height",
    "letter-spacing",
}

GEOMETRY_PROPERTIES = {
    "width",
    "height",
    "min-width",
    "min-height",
    "max-width",
    "max-height",
}
```

`width` 和 `height` 只有满足以下条件才进入组件 Token：

- 多状态保持稳定；
- 多 viewport 中保持固定；
- 对应明确组件角色；
- 出现频率高；
- 原型变量有直接证据；
- 或属于 shell 关键几何。

---

# 九、基础 Token 生成

基础 Token 只表达值，不表达用途。

```json
{
  "primitive": {
    "color": {
      "neutral": {
        "0": "#ffffff",
        "50": "#fafafa",
        "100": "#f5f5f5",
        "200": "#f0f0f0",
        "300": "#d9d9d9",
        "600": "#595959",
        "700": "#434343",
        "900": "#141414"
      },
      "brand": {
        "500": "#4096ff",
        "600": "#1677ff",
        "700": "#0958d9"
      }
    },
    "space": {
      "0": "0px",
      "1": "4px",
      "2": "8px",
      "3": "12px",
      "4": "16px",
      "5": "20px",
      "6": "24px",
      "8": "32px"
    },
    "radius": {
      "none": "0px",
      "xs": "2px",
      "sm": "4px",
      "md": "6px",
      "lg": "8px",
      "xl": "12px",
      "full": "9999px"
    },
    "font": {
      "size": {
        "xs": "12px",
        "sm": "13px",
        "md": "14px",
        "lg": "16px",
        "xl": "20px",
        "2xl": "24px"
      },
      "weight": {
        "regular": 400,
        "medium": 500,
        "semibold": 600,
        "bold": 700
      }
    }
  }
}
```

命名不应完全照搬 Tailwind 默认值。原型中若存在 `10px、14px、18px` 的稳定间距体系，应如实生成，不要为了“漂亮”强行映射到默认 Tailwind。

> 原型事实优先于框架默认设计系统。

---

# 十、语义 Token 自动推断

仅聚类无法知道颜色语义，需要结合：

- CSS 属性；
- 元素 role；
- 可访问名称；
- DOM 祖先；
- 页面区域；
- 交互状态；
- 背景上下文；
- 出现频率；
- 对比关系。

## 10.1 语义推断规则

```yaml
semantic_rules:
  color.text.primary:
    properties:
      - color
    contexts:
      - heading
      - paragraph
      - table-cell
    preferred_clusters:
      - darkest-neutral

  color.text.secondary:
    properties:
      - color
    contexts:
      - description
      - metadata
      - helper-text

  color.surface.page:
    properties:
      - background-color
    contexts:
      - body
      - app-root
      - main-content

  color.surface.container:
    properties:
      - background-color
    contexts:
      - card
      - dialog
      - drawer
      - panel

  color.action.primary:
    properties:
      - background-color
      - border-color
    contexts:
      - primary-button
      - selected-navigation
```

## 10.2 推断结果必须有置信度

```yaml
semantic:
  color:
    text:
      primary:
        value: "{primitive.color.neutral.900}"
        confidence: 0.96
        evidence:
          observation_count: 182
          routes:
            - dashboard
            - reports
          roles:
            - heading
            - cell
            - paragraph

      tertiary:
        value: "{primitive.color.neutral.600}"
        confidence: 0.61
        review_required: true
```

低置信度 Token 不允许自动锁定：

```yaml
semantic_inference:
  auto_accept_confidence: 0.90
  accept_with_visual_verification: 0.75
  require_model_review_below: 0.75
```

Kimi K3 可用于低置信度视觉语义判断，但不能直接写 Token。它只输出建议，由确定性验证器检查应用前后的视觉得分。

---

# 十一、组件 Token：保持复用，也允许高保真几何

不能把所有几何值放进全局空间 Token。以下值应进入组件层：

```yaml
component:
  appShell:
    header:
      height: 64px
    sidebar:
      expandedWidth: 256px
      collapsedWidth: 80px
    content:
      maxWidth: 1440px
      paddingInline: "{primitive.space.6}"
      paddingBlock: "{primitive.space.5}"

  card:
    radius: "{primitive.radius.lg}"
    padding: "{primitive.space.5}"
    borderColor: "{semantic.color.border.subtle}"
    shadow: "{primitive.shadow.sm}"

  button:
    controlHeight: 32px
    controlHeightLarge: 40px
    radius: "{primitive.radius.md}"

  modal:
    widthDefault: 520px
    radius: "{primitive.radius.lg}"
    maskColor: "#00000073"
```

组件 Token 的准入标准：

```text
有明确组件语义
+ 在多个实例或状态中复用
+ 值相对稳定
+ 修改它会系统性影响一组视觉区域
```

页面独有尺寸可以使用页面 Token：

```yaml
page:
  dashboard:
    summaryGrid:
      columns: 4
      gap: "{primitive.space.4}"
    trendPanel:
      minHeight: 360px
```

不要为了“通用化”把页面独有值错误提升为全局 Token。

---

# 十二、状态 Token 与交互差异提取

第 2 部分已经建立状态图，因此可以比较同一元素在状态转换前后的样式：

```text
button.default
→ button.hover
→ button.focus
→ button.active
→ button.disabled
```

状态差异提取器：

```python
# scripts/ui_autopilot/tokens/state_diff.py

from __future__ import annotations

STATEFUL_PROPERTIES = {
    "color",
    "background-color",
    "border-color",
    "box-shadow",
    "opacity",
    "transform",
}


def extract_state_delta(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, dict[str, str]]:
    changes: dict[str, dict[str, str]] = {}

    for property_name in STATEFUL_PROPERTIES:
        before_value = before.get(property_name)
        after_value = after.get(property_name)

        if before_value != after_value:
            changes[property_name] = {
                "before": before_value or "",
                "after": after_value or "",
            }

    return changes
```

产物：

```yaml
state:
  button:
    primary:
      default:
        background: "{semantic.color.action.primary}"
        text: "{semantic.color.text.onPrimary}"
      hover:
        background: "{semantic.color.action.primaryHover}"
      active:
        background: "{semantic.color.action.primaryActive}"
      focus:
        ring: "{semantic.color.border.focus}"
      disabled:
        background: "{semantic.color.action.disabled}"
        opacity: 0.65
```

交互状态缺失不能由默认样式平均分掩盖，必须进入状态覆盖门禁。

---

# 十三、生成 CSS Variables

建议以 CSS Variables 作为跨 Tailwind、Ant Design 和 CSS Modules 的单一事实源。

```css
/* src/styles/tokens/generated/primitives.css */

:root {
  --ui-color-neutral-0: #ffffff;
  --ui-color-neutral-50: #fafafa;
  --ui-color-neutral-100: #f5f5f5;
  --ui-color-neutral-200: #f0f0f0;
  --ui-color-neutral-300: #d9d9d9;
  --ui-color-neutral-600: #595959;
  --ui-color-neutral-700: #434343;
  --ui-color-neutral-900: #141414;

  --ui-color-brand-500: #4096ff;
  --ui-color-brand-600: #1677ff;
  --ui-color-brand-700: #0958d9;

  --ui-space-0: 0px;
  --ui-space-1: 4px;
  --ui-space-2: 8px;
  --ui-space-3: 12px;
  --ui-space-4: 16px;
  --ui-space-5: 20px;
  --ui-space-6: 24px;
  --ui-space-8: 32px;

  --ui-radius-none: 0px;
  --ui-radius-sm: 4px;
  --ui-radius-md: 6px;
  --ui-radius-lg: 8px;
  --ui-radius-xl: 12px;
  --ui-radius-full: 9999px;

  --ui-font-size-xs: 12px;
  --ui-font-size-sm: 13px;
  --ui-font-size-md: 14px;
  --ui-font-size-lg: 16px;
  --ui-font-size-xl: 20px;

  --ui-font-weight-regular: 400;
  --ui-font-weight-medium: 500;
  --ui-font-weight-semibold: 600;
  --ui-font-weight-bold: 700;
}
```

语义层：

```css
/* src/styles/tokens/generated/semantics.css */

:root {
  --ui-color-surface-page: var(--ui-color-neutral-50);
  --ui-color-surface-container: var(--ui-color-neutral-0);
  --ui-color-surface-elevated: var(--ui-color-neutral-0);

  --ui-color-text-primary: var(--ui-color-neutral-900);
  --ui-color-text-secondary: var(--ui-color-neutral-600);
  --ui-color-text-tertiary: var(--ui-color-neutral-600);
  --ui-color-text-on-primary: var(--ui-color-neutral-0);

  --ui-color-border-subtle: var(--ui-color-neutral-200);
  --ui-color-border-default: var(--ui-color-neutral-300);
  --ui-color-border-focus: var(--ui-color-brand-600);

  --ui-color-action-primary: var(--ui-color-brand-600);
  --ui-color-action-primary-hover: var(--ui-color-brand-500);
  --ui-color-action-primary-active: var(--ui-color-brand-700);
}
```

组件层：

```css
/* src/styles/tokens/generated/components.css */

:root {
  --ui-shell-header-height: 64px;
  --ui-shell-sidebar-width-expanded: 256px;
  --ui-shell-sidebar-width-collapsed: 80px;
  --ui-shell-content-padding-inline: var(--ui-space-6);
  --ui-shell-content-padding-block: var(--ui-space-5);

  --ui-card-padding: var(--ui-space-5);
  --ui-card-radius: var(--ui-radius-lg);
  --ui-card-background: var(--ui-color-surface-container);
  --ui-card-border-color: var(--ui-color-border-subtle);

  --ui-control-height-sm: 24px;
  --ui-control-height-md: 32px;
  --ui-control-height-lg: 40px;
}
```

统一入口：

```css
/* src/styles/tokens/index.css */

@import './generated/primitives.css';
@import './generated/semantics.css';
@import './generated/components.css';
@import './generated/states.css';
@import './aliases.css';
@import './overrides.css';
```

---

# 十四、生成类型安全的 TypeScript Token

```typescript
// src/styles/tokens/generated/tokens.ts

export const token = {
  color: {
    surface: {
      page: 'var(--ui-color-surface-page)',
      container: 'var(--ui-color-surface-container)',
    },
    text: {
      primary: 'var(--ui-color-text-primary)',
      secondary: 'var(--ui-color-text-secondary)',
    },
    action: {
      primary: 'var(--ui-color-action-primary)',
      primaryHover: 'var(--ui-color-action-primary-hover)',
    },
  },
  space: {
    0: 'var(--ui-space-0)',
    1: 'var(--ui-space-1)',
    2: 'var(--ui-space-2)',
    3: 'var(--ui-space-3)',
    4: 'var(--ui-space-4)',
    5: 'var(--ui-space-5)',
    6: 'var(--ui-space-6)',
    8: 'var(--ui-space-8)',
  },
  radius: {
    sm: 'var(--ui-radius-sm)',
    md: 'var(--ui-radius-md)',
    lg: 'var(--ui-radius-lg)',
    full: 'var(--ui-radius-full)',
  },
  component: {
    shell: {
      headerHeight: 'var(--ui-shell-header-height)',
      sidebarExpandedWidth:
        'var(--ui-shell-sidebar-width-expanded)',
      sidebarCollapsedWidth:
        'var(--ui-shell-sidebar-width-collapsed)',
    },
  },
} as const;

export type UiToken = typeof token;
```

React 行内样式必须使用类型化 Token：

```tsx
import { token } from '@/styles/tokens/generated/tokens';

export function DashboardPanel() {
  return (
    <section
      style={{
        background: token.color.surface.container,
        borderRadius: token.radius.lg,
        padding: token.space[5],
      }}
    />
  );
}
```

但优先级依然是：

```text
Tailwind utility
> CSS Module + CSS Variable
> 类型化 inline style
> 裸 inline style（禁止）
```

---

# 十五、Tailwind 接入

如果项目使用 Tailwind v3，可在配置中引用 CSS Variables：

```typescript
// tailwind.config.ts

import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          page: 'var(--ui-color-surface-page)',
          container: 'var(--ui-color-surface-container)',
          elevated: 'var(--ui-color-surface-elevated)',
        },
        content: {
          primary: 'var(--ui-color-text-primary)',
          secondary: 'var(--ui-color-text-secondary)',
          tertiary: 'var(--ui-color-text-tertiary)',
        },
        action: {
          primary: 'var(--ui-color-action-primary)',
          'primary-hover': 'var(--ui-color-action-primary-hover)',
          'primary-active': 'var(--ui-color-action-primary-active)',
        },
        border: {
          subtle: 'var(--ui-color-border-subtle)',
          DEFAULT: 'var(--ui-color-border-default)',
          focus: 'var(--ui-color-border-focus)',
        },
      },
      spacing: {
        'ui-1': 'var(--ui-space-1)',
        'ui-2': 'var(--ui-space-2)',
        'ui-3': 'var(--ui-space-3)',
        'ui-4': 'var(--ui-space-4)',
        'ui-5': 'var(--ui-space-5)',
        'ui-6': 'var(--ui-space-6)',
        'ui-8': 'var(--ui-space-8)',
      },
      borderRadius: {
        'ui-sm': 'var(--ui-radius-sm)',
        'ui-md': 'var(--ui-radius-md)',
        'ui-lg': 'var(--ui-radius-lg)',
        'ui-xl': 'var(--ui-radius-xl)',
      },
      height: {
        'control-sm': 'var(--ui-control-height-sm)',
        'control-md': 'var(--ui-control-height-md)',
        'control-lg': 'var(--ui-control-height-lg)',
        header: 'var(--ui-shell-header-height)',
      },
      width: {
        'sidebar-expanded':
          'var(--ui-shell-sidebar-width-expanded)',
        'sidebar-collapsed':
          'var(--ui-shell-sidebar-width-collapsed)',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

使用方式：

```tsx
<section
  className="
    rounded-ui-lg
    border border-border-subtle
    bg-surface-container
    p-ui-5
    text-content-primary
  "
/>
```

## 禁止任意值泛滥

```tsx
// 禁止
<div className="p-[17px] rounded-[7px] text-[#434343]" />

// 正确
<div className="p-ui-4 rounded-ui-lg text-content-primary" />
```

但高保真还原确实可能存在原型特有的 `17px`。正确流程是：

```text
发现 17px
→ 检查是否稳定、复用、有证据
→ 登记为 Token 或页面组件 Token
→ 重新生成 Tailwind 映射
→ 使用命名类
```

不是直接允许 `[17px]`。

---

# 十六、Ant Design Token 接入

Ant Design 自带 Token 系统，不应通过全局 CSS 暴力覆盖 `.ant-*` 来实现原型。

```typescript
// src/theme/antd-theme.ts

import type { ThemeConfig } from 'antd';

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: 'var(--ui-color-action-primary)',
    colorPrimaryHover: 'var(--ui-color-action-primary-hover)',
    colorPrimaryActive: 'var(--ui-color-action-primary-active)',

    colorText: 'var(--ui-color-text-primary)',
    colorTextSecondary: 'var(--ui-color-text-secondary)',

    colorBgLayout: 'var(--ui-color-surface-page)',
    colorBgContainer: 'var(--ui-color-surface-container)',
    colorBgElevated: 'var(--ui-color-surface-elevated)',

    colorBorder: 'var(--ui-color-border-default)',
    colorBorderSecondary: 'var(--ui-color-border-subtle)',

    borderRadius: 6,
    borderRadiusLG: 8,

    controlHeight: 32,
    controlHeightLG: 40,

    fontSize: 14,
  },

  components: {
    Layout: {
      headerHeight: 64,
      headerBg: 'var(--ui-color-surface-container)',
      siderBg: 'var(--ui-color-surface-container)',
      bodyBg: 'var(--ui-color-surface-page)',
    },

    Card: {
      borderRadiusLG: 8,
      paddingLG: 20,
      colorBorderSecondary: 'var(--ui-color-border-subtle)',
    },

    Button: {
      controlHeight: 32,
      controlHeightLG: 40,
      borderRadius: 6,
      primaryShadow: 'none',
    },

    Modal: {
      borderRadiusLG: 8,
      paddingContentHorizontalLG: 24,
    },

    Menu: {
      itemHeight: 40,
      itemBorderRadius: 6,
      itemSelectedBg: 'var(--ui-color-brand-soft)',
      itemSelectedColor: 'var(--ui-color-action-primary)',
    },
  },
};
```

接入：

```tsx
// src/theme/theme-provider.tsx

import type { PropsWithChildren } from 'react';
import { ConfigProvider } from 'antd';
import { antdTheme } from './antd-theme';

export function ThemeProvider({ children }: PropsWithChildren) {
  return (
    <ConfigProvider theme={antdTheme}>
      {children}
    </ConfigProvider>
  );
}
```

## Ant Design 的数值限制

部分 Ant Design Token 类型只接受 number，不接受 CSS Variable。对此不能复制裸值后失去单一事实源，建议生成器同时产出：

```typescript
export const resolvedToken = {
  radius: {
    md: 6,
    lg: 8,
  },
  component: {
    controlHeight: {
      md: 32,
      lg: 40,
    },
  },
} as const;
```

然后：

```typescript
import { resolvedToken } from '@/styles/tokens/generated/resolved-tokens';

export const antdTheme: ThemeConfig = {
  token: {
    borderRadius: resolvedToken.radius.md,
    borderRadiusLG: resolvedToken.radius.lg,
    controlHeight: resolvedToken.component.controlHeight.md,
  },
};
```

`resolved-tokens.ts` 仍由同一个 Token JSON 生成，避免双重维护。

---

# 十七、Token 生成器

推荐使用一个确定性生成器，而不是让模型分别手写 CSS、TS 和 Tailwind 配置。

```python
# scripts/ui_autopilot/tokens/generate.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HEADER = """/*
 * AUTO-GENERATED FILE.
 * Source: prototype/tokens.normalized.json
 * Do not edit directly.
 */
"""


def flatten_tokens(
    node: dict[str, Any],
    prefix: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Any]]:
    result: list[tuple[tuple[str, ...], Any]] = []

    for key, value in node.items():
        path = (*prefix, key)

        if isinstance(value, dict) and "value" not in value:
            result.extend(flatten_tokens(value, path))
        else:
            resolved = value["value"] if isinstance(value, dict) else value
            result.append((path, resolved))

    return result


def css_variable_name(path: tuple[str, ...]) -> str:
    normalized = "-".join(
        part.replace("_", "-").lower()
        for part in path
    )
    return f"--ui-{normalized}"


def generate_css(tokens: dict[str, Any]) -> str:
    lines = [HEADER, ":root {"]

    for path, value in flatten_tokens(tokens):
        lines.append(f"  {css_variable_name(path)}: {value};")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    source = Path(
        ".omc/ui-autopilot/current/prototype/tokens.normalized.json"
    )
    output = Path("src/styles/tokens/generated/all.css")

    tokens = json.loads(source.read_text(encoding="utf-8"))
    atomic_write(output, generate_css(tokens))


if __name__ == "__main__":
    main()
```

生成后必须计算摘要：

```json
{
  "source_digest": "sha256:...",
  "generator_version": "2.0.0",
  "generated_files": {
    "primitives.css": "sha256:...",
    "semantics.css": "sha256:...",
    "tokens.ts": "sha256:...",
    "resolved-tokens.ts": "sha256:..."
  }
}
```

`preflight.py` 和最终门禁检查：

- 源摘要是否一致；
- 生成文件是否被手工修改；
- 生成器是否可重复运行；
- Git 工作区重新生成后是否产生差异。

---

# 十八、现有代码裸值扫描

Token 系统建立后，必须迁移已有页面中的裸值。

## 18.1 扫描范围

```text
.ts
.tsx
.css
.scss
.module.css
.module.scss
less
tailwind className
style={{ ... }}
Ant Design theme
SVG fill/stroke
图表配置
```

## 18.2 禁止项

```text
十六进制裸色
rgb/hsl 裸色
Tailwind 任意颜色
任意 spacing
未登记 px/rem
重复阴影
重复圆角
未登记 z-index
直接覆盖 Ant Design 内部 class
```

## 18.3 Python 扫描器

```python
# scripts/carroros-gates/token_compliance.py

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


HEX_COLOR = re.compile(
    r"(?<![\w-])#[0-9a-fA-F]{3,8}\b"
)

FUNCTION_COLOR = re.compile(
    r"\b(?:rgb|rgba|hsl|hsla|oklch|oklab)\([^)]*\)",
    re.IGNORECASE,
)

ARBITRARY_TAILWIND = re.compile(
    r"(?:"
    r"(?:bg|text|border|ring|shadow)-\[[^\]]+\]"
    r"|"
    r"(?:p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|"
    r"w|h|min-w|min-h|max-w|max-h|rounded)-\[[^\]]+\]"
    r")"
)

PIXEL_VALUE = re.compile(
    r"(?<![\w.-])(-?\d+(?:\.\d+)?)px\b"
)


@dataclass(frozen=True, slots=True)
class Violation:
    file: str
    line: int
    column: int
    rule: str
    value: str


class TokenComplianceScanner:
    def __init__(
        self,
        root: Path,
        allowlisted_values: set[str],
        ignored_paths: tuple[str, ...],
    ) -> None:
        self.root = root
        self.allowlisted_values = allowlisted_values
        self.ignored_paths = ignored_paths

    def scan_file(self, path: Path) -> list[Violation]:
        relative = path.relative_to(self.root).as_posix()

        if any(Path(relative).match(pattern) for pattern in self.ignored_paths):
            return []

        violations: list[Violation] = []

        for line_number, line in enumerate(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines(),
            start=1,
        ):
            violations.extend(
                self._scan_pattern(
                    relative,
                    line_number,
                    line,
                    HEX_COLOR,
                    "raw-color",
                )
            )
            violations.extend(
                self._scan_pattern(
                    relative,
                    line_number,
                    line,
                    FUNCTION_COLOR,
                    "raw-color-function",
                )
            )
            violations.extend(
                self._scan_pattern(
                    relative,
                    line_number,
                    line,
                    ARBITRARY_TAILWIND,
                    "tailwind-arbitrary-value",
                )
            )

            for match in PIXEL_VALUE.finditer(line):
                value = match.group(0)

                if value not in self.allowlisted_values:
                    violations.append(
                        Violation(
                            file=relative,
                            line=line_number,
                            column=match.start() + 1,
                            rule="unregistered-pixel-value",
                            value=value,
                        )
                    )

        return violations

    @staticmethod
    def _scan_pattern(
        file: str,
        line_number: int,
        line: str,
        pattern: re.Pattern[str],
        rule: str,
    ) -> list[Violation]:
        return [
            Violation(
                file=file,
                line=line_number,
                column=match.start() + 1,
                rule=rule,
                value=match.group(0),
            )
            for match in pattern.finditer(line)
        ]
```

## 18.4 不能只靠正则

正则可作为第一层，但正式实现应增加 AST 扫描：

- TypeScript：TypeScript Compiler API / ESLint；
- CSS：PostCSS；
- SCSS：PostCSS SCSS parser；
- Tailwind：class AST 或受控 parser；
- SVG：XML parser。

否则容易误报：

```tsx
const issueId = '#fff123'; // 不是颜色
const text = '尺寸为 16px'; // 文档文本
```

---

# 十九、ESLint 和 Stylelint 门禁

## 19.1 ESLint 自定义规则

目标：

```tsx
// 禁止
<div style={{ color: '#1677ff', padding: 16 }} />

// 允许
<div
  style={{
    color: token.color.action.primary,
    padding: token.space[4],
  }}
/>
```

规则伪实现：

```typescript
// eslint-rules/no-raw-ui-values.ts

export default {
  meta: {
    type: 'problem',
    schema: [],
    messages: {
      rawColor: '禁止使用裸颜色 {{value}}，请使用 Design Token。',
      rawPixel: '禁止使用未登记尺寸 {{value}}，请使用 Design Token。',
    },
  },

  create(context) {
    return {
      Property(node) {
        const propertyName =
          node.key.type === 'Identifier'
            ? node.key.name
            : null;

        if (!propertyName) return;

        const colorProperties = new Set([
          'color',
          'background',
          'backgroundColor',
          'borderColor',
          'fill',
          'stroke',
        ]);

        if (
          colorProperties.has(propertyName) &&
          node.value.type === 'Literal' &&
          typeof node.value.value === 'string' &&
          /^(#|rgb|hsl|oklch)/i.test(node.value.value)
        ) {
          context.report({
            node: node.value,
            messageId: 'rawColor',
            data: { value: node.value.value },
          });
        }
      },
    };
  },
};
```

## 19.2 Stylelint 配置

```javascript
// stylelint.config.mjs

export default {
  extends: ['stylelint-config-standard-scss'],
  rules: {
    'color-no-hex': true,

    'declaration-property-value-disallowed-list': {
      '/^color$/': [
        '/^(?!var\\().+/',
      ],
      '/background(?:-color)?/': [
        '/^(?!var\\(|transparent|none|inherit|currentColor).+/',
      ],
      '/border(?:-.*)?-color/': [
        '/^(?!var\\(|transparent|inherit|currentColor).+/',
      ],
    },
  },

  ignoreFiles: [
    'src/styles/tokens/generated/**',
    '**/*.generated.css',
  ],
};
```

实际项目中应避免配置过度误报，可以由生成器输出允许值列表，供 Stylelint 自定义插件读取。

---

# 二十、自动迁移器

迁移过程不能全局替换字符串，因为相同值可能具有不同语义。

错误：

```text
将所有 #ffffff 替换为 --ui-color-surface-container
```

`#ffffff` 可能是：

- 页面容器背景；
- 按钮文字；
- 图标颜色；
- Modal 背景；
- selected 文本。

正确迁移需要结合属性和上下文：

```python
def resolve_semantic_replacement(
    *,
    value: str,
    property_name: str,
    component_role: str | None,
    state: str | None,
) -> str | None:
    candidates = semantic_index.lookup(value)

    scored = [
        (
            candidate,
            semantic_match_score(
                candidate=candidate,
                property_name=property_name,
                component_role=component_role,
                state=state,
            ),
        )
        for candidate in candidates
    ]

    if not scored:
        return None

    best, score = max(scored, key=lambda item: item[1])

    if score < 0.85:
        return None

    return f"var({best.css_variable})"
```

迁移任务分三类：

```yaml
migration:
  exact:
    confidence: 1.0
    action: auto_apply

  contextual:
    confidence_gte: 0.85
    action: auto_apply_then_visual_verify

  ambiguous:
    confidence_lt: 0.85
    action: create_bounded_task
```

每批迁移后必须：

```text
lint
→ typecheck
→ unit test
→ 目标页面截图
→ 分区域视觉比较
→ 接受或回滚
```

不能一次迁移整个仓库再统一验证。

---

# 二十一、例外机制：不是绝对禁止所有裸值

高保真系统需要允许极少量、明确登记的例外，例如：

- 第三方图表库必须接收计算后的数值；
- Canvas 颜色不能直接消费 CSS Variable；
- 一次性 SVG path；
- 浏览器兼容性常量；
- `1px` hairline；
- `9999px` pill radius；
- `0px`。

但例外必须有登记、有范围、有过期策略：

```yaml
# .claude/ui-token-exceptions.yaml

exceptions:
  - id: chart-runtime-color-resolution
    paths:
      - src/features/dashboard/charts/**
    values:
      - "#1677ff"
    reason: >
      Chart runtime requires resolved color values and cannot consume
      CSS custom properties directly.
    replacement_strategy: resolveCssVariableAtRuntime
    owner: ui-autopilot
    expires_at: 2026-09-01

  - id: one-pixel-hairline
    paths:
      - src/components/Divider/**
    values:
      - 1px
    reason: 原型明确使用设备像素分隔线
    evidence:
      - .omc/doc/tokens/divider-measurement.json
```

没有以下字段的例外无效：

```text
id
paths
values
reason
evidence 或 replacement_strategy
expires_at
```

门禁必须检测过期例外。

---

# 二十二、Token 漂移检测

后续视觉修复中，模型可能不断添加近似 Token：

```text
--ui-space-card: 16px
--ui-space-panel: 17px
--ui-space-section: 16.5px
```

需要 Token Drift Gate。

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriftFinding:
    left_token: str
    right_token: str
    left_value: float
    right_value: float
    distance: float
    severity: str


def detect_length_drift(
    tokens: dict[str, float],
    tolerance: float = 1.0,
) -> list[DriftFinding]:
    names = sorted(tokens)
    findings: list[DriftFinding] = []

    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            left = tokens[left_name]
            right = tokens[right_name]
            distance = abs(left - right)

            if 0 < distance <= tolerance:
                findings.append(
                    DriftFinding(
                        left_token=left_name,
                        right_token=right_name,
                        left_value=left,
                        right_value=right,
                        distance=distance,
                        severity="warning",
                    )
                )

    return findings
```

判断逻辑：

```text
两个值非常接近
+ 语义无明确区分
+ 原型证据不足
→ 合并

两个值非常接近
+ 分别对应不同交互状态
+ 原型证据稳定
→ 保留
```

---

# 二十三、Token 变更影响分析

修改一个全局 Token 可能提升当前区域，却让其他页面退化。因此需要记录消费者。

```json
{
  "--ui-color-text-secondary": {
    "consumers": [
      "src/components/Description/Description.module.scss:14",
      "src/features/dashboard/MetricCard.tsx:42",
      "src/features/reports/FilterBar.module.scss:28"
    ],
    "affected_routes": [
      "dashboard",
      "reports"
    ],
    "affected_states": [
      "dashboard-default",
      "reports-default",
      "reports-filter-open"
    ]
  }
}
```

Token 修复任务必须根据影响范围选择回归集：

```python
def regression_states_for_token(
    token_name: str,
    dependency_graph: dict,
) -> set[str]:
    node = dependency_graph[token_name]
    return set(node["affected_states"])
```

采用风险分级：

```yaml
token_change_risk:
  primitive:
    default: critical
  semantic:
    default: high
  component:
    default: medium
  page:
    default: low
```

Primitive Token 修改默认需要全量视觉回归；页面 Token 只需目标页面及共享组件回归。

---

# 二十四、Token 阶段的任务图

建议将 Token 阶段拆成以下确定性任务：

```text
TKN-001 采集原型公开 CSS Variables
TKN-002 采集所有状态 computed styles
TKN-003 采集伪元素和浮层样式
TKN-004 归一化颜色
TKN-005 归一化长度和几何
TKN-006 归一化字体和排版
TKN-007 解析阴影、边框和透明度
TKN-008 聚类 Primitive 候选
TKN-009 推断 Semantic Token
TKN-010 推断 Component Token
TKN-011 提取 State Token
TKN-012 生成 Token 证据报告
TKN-013 生成 CSS Variables
TKN-014 生成 TypeScript Token
TKN-015 生成 Tailwind 映射
TKN-016 生成 Ant Design Theme
TKN-017 扫描现有代码裸值
TKN-018 分批自动迁移
TKN-019 执行视觉回归
TKN-020 锁定 Token 基线
```

依赖图：

```text
TKN-001 ─┐
TKN-002 ─┼→ TKN-004/005/006/007
TKN-003 ─┘            ↓
                  TKN-008
                     ↓
              TKN-009/010/011
                     ↓
                  TKN-012
                     ↓
          TKN-013/014/015/016
                     ↓
                  TKN-017
                     ↓
                  TKN-018
                     ↓
                  TKN-019
                     ↓
                  TKN-020
```

---

# 二十五、Token 阶段完成门禁 C5b

结合现有 `preflight.py → run_all.py → evidence_check.py → finalize_page.py` 链路，建议增加一个 `token_compliance.py`，由 `run_all.py` 调用。

## 25.1 门禁配置

```yaml
# gate-contract.yaml 增量示意

gates:
  C5b:
    name: design-token-compliance
    blocking: true
    command:
      - python
      - scripts/carroros-gates/token_compliance.py
      - --manifest
      - "{manifest}"
    required_artifacts:
      - prototype/tokens.raw.jsonl
      - prototype/tokens.normalized.json
      - prototype/token-clusters.json
      - prototype/token-semantic-map.yaml
      - evidence/token-extraction-report.json
      - evidence/token-compliance-report.json
      - evidence/token-generation-digests.json
    acceptance:
      extraction_coverage: 1.0
      generated_files_consistent: true
      unresolved_critical_tokens: 0
      unauthorized_raw_colors: 0
      unauthorized_arbitrary_values: 0
      expired_exceptions: 0
      token_visual_regressions: 0
```

## 25.2 Manifest 增量

```yaml
# night-manifest.template.yaml 增量示意

ui_tokens:
  enabled: true

  source:
    normalized_tokens:
      .omc/ui-autopilot/${RUN_ID}/prototype/tokens.normalized.json
    semantic_map:
      .omc/ui-autopilot/${RUN_ID}/prototype/token-semantic-map.yaml

  generated_paths:
    - src/styles/tokens/generated/**
    - src/theme/antd-theme.ts

  scan_paths:
    - src/**/*.ts
    - src/**/*.tsx
    - src/**/*.css
    - src/**/*.scss

  ignored_paths:
    - src/styles/tokens/generated/**
    - "**/*.generated.*"
    - node_modules/**

  exceptions:
    .claude/ui-token-exceptions.yaml

  thresholds:
    minimum_extraction_coverage: 1.0
    minimum_token_compliance: 1.0
    maximum_unresolved_critical_tokens: 0
    maximum_visual_regressions: 0
```

## 25.3 Signoff 增量

```yaml
# night-manifest.signoff.template.yaml 增量示意

token_signoff:
  raw_observations_reviewed: false
  semantic_mapping_reviewed: false
  antd_mapping_reviewed: false
  exception_registry_reviewed: false

  approved_digests:
    normalized_tokens: ""
    semantic_map: ""
    exception_registry: ""
```

对于全自动任务，signoff 不意味着每次都需要人工签字。Phase 0 可以对 Token 提取策略和允许范围一次确认，后续同一 run 内由摘要锁定。

---

# 二十六、Token 门禁完整实现骨架

```python
# scripts/carroros-gates/token_compliance.py

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

from ui_autopilot.tokens.scanner import TokenComplianceScanner


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_generator(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    )
    return completed.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--report",
        default=".omc/evidence/token-compliance-report.json",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_yaml(manifest_path)
    config = manifest.get("ui_tokens") or {}

    if not config.get("enabled"):
        print("FAIL: manifest 未启用 ui_tokens")
        return 1

    required_sources = [
        Path(config["source"]["normalized_tokens"]),
        Path(config["source"]["semantic_map"]),
    ]

    missing_sources = [
        str(path) for path in required_sources if not path.is_file()
    ]

    generated_before: dict[str, str] = {}
    for pattern in config.get("generated_paths", []):
        for path in Path(".").glob(pattern):
            if path.is_file():
                generated_before[str(path)] = sha256_file(path)

    generator_code, generator_output = run_generator([
        sys.executable,
        "scripts/ui_autopilot/tokens/generate.py",
    ])

    generated_after: dict[str, str] = {}
    for pattern in config.get("generated_paths", []):
        for path in Path(".").glob(pattern):
            if path.is_file():
                generated_after[str(path)] = sha256_file(path)

    generated_consistent = (
        generator_code == 0
        and generated_before == generated_after
    )

    scanner = TokenComplianceScanner(
        root=Path("."),
        allowlisted_values={
            "0px",
            "1px",
            "9999px",
        },
        ignored_paths=tuple(config.get("ignored_paths", [])),
    )

    violations = []

    for pattern in config.get("scan_paths", []):
        for path in Path(".").glob(pattern):
            if path.is_file():
                violations.extend(scanner.scan_file(path))

    report = {
        "gate": "C5b",
        "passed": (
            not missing_sources
            and generated_consistent
            and not violations
        ),
        "missing_sources": missing_sources,
        "generator": {
            "exit_code": generator_code,
            "output": generator_output,
            "consistent": generated_consistent,
        },
        "violations": [asdict(item) for item in violations],
        "digests": generated_after,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if report["passed"]:
        print("PASS C5b: Design Token 合规")
        return 0

    print(
        "FAIL C5b: "
        f"missing={len(missing_sources)}, "
        f"violations={len(violations)}, "
        f"generated_consistent={generated_consistent}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

正式版本还需补充：

- AST 扫描；
- 例外文件校验；
- 过期检查；
- Token 引用完整性；
- 循环引用检测；
- 未使用 Token 检测；
- 视觉回归摘要绑定；
- 证据文件 digest；
- `scope_check.py` 范围约束。

---

# 二十七、Token 图循环引用检测

语义 Token 可能形成错误循环：

```text
text.primary
→ neutral.900
→ text.primary
```

实现：

```python
def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    active: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        if node in active:
            start = stack.index(node)
            cycles.append([*stack[start:], node])
            return

        if node in visited:
            return

        visited.add(node)
        active.add(node)
        stack.append(node)

        for dependency in graph.get(node, set()):
            visit(dependency)

        stack.pop()
        active.remove(node)

    for node in graph:
        visit(node)

    return cycles
```

C5b 要求：

```yaml
token_reference_cycles: 0
missing_token_references: 0
```

---

# 二十八、与 CarrorOS 证据链整合

根据现有治理原则：

```text
失败立即留痕
无证据 = 没做
双源验证
禁止虚假完成
```

Token 门禁至少应保留三类证据。

## 1. 原型事实证据

```text
computed styles
CSS Variables
截图
DOM/ARIA
状态转换前后样式
```

## 2. 实现证据

```text
生成 Token
源码消费者
扫描结果
Tailwind 映射
Ant Design Theme
```

## 3. 视觉证据

```text
迁移前截图
迁移后截图
diff
区域评分
回归状态列表
```

`evidence_check.py` 应验证：

```yaml
token_evidence:
  prototype_sources:
    minimum_types: 2
  implementation_sources:
    minimum_types: 2
  visual_verification:
    required: true
  digest_binding:
    required: true
```

推荐 evidence index：

```json
{
  "gate": "C5b",
  "evidence": {
    "prototype": [
      {
        "type": "computed-style",
        "path": "prototype/tokens.raw.jsonl",
        "sha256": "..."
      },
      {
        "type": "screenshot",
        "path": "prototype/screenshots/dashboard/default.png",
        "sha256": "..."
      }
    ],
    "implementation": [
      {
        "type": "generated-token",
        "path": "src/styles/tokens/generated/semantics.css",
        "sha256": "..."
      },
      {
        "type": "source-scan",
        "path": "evidence/token-compliance-report.json",
        "sha256": "..."
      }
    ],
    "verification": [
      {
        "type": "visual-regression",
        "path": "evidence/token-visual-regression.json",
        "sha256": "..."
      }
    ]
  }
}
```

---

# 二十九、Token 冻结与增量学习

Token 阶段完成后不能完全禁止变更，因为后续区域还原可能发现漏项。但要从“自由变更”变成“提案制”。

## 29.1 Token Lock

```json
{
  "schemaVersion": 1,
  "runId": "dashboard-restoration-20260729",
  "tokenSourceDigest": "sha256:...",
  "semanticMapDigest": "sha256:...",
  "generatedDigest": "sha256:...",
  "lockedAt": "2026-07-29T12:00:00Z"
}
```

## 29.2 新 Token 提案

```yaml
proposal:
  id: TOKEN-PROP-0042
  phase: regions
  requested_by_task: region-dashboard-chart-tooltip-007

  category: component
  proposed_name: chart.tooltip.shadow
  proposed_value: 0 4px 12px 0 "#0000001f"

  reason: >
    图表 Tooltip 阴影不属于当前 elevation 集合，
    且在 3 个图表 hover 状态中稳定出现。

  evidence:
    observations: 3
    states:
      - dashboard-chart-revenue-hover
      - dashboard-chart-orders-hover
      - dashboard-chart-users-hover
    screenshots:
      - prototype/screenshots/dashboard/chart-revenue-hover.png

  nearest_existing_tokens:
    - name: shadow.md
      visual_distance: 0.082

  impact:
    affected_components:
      - RevenueChart
      - OrdersChart
      - UsersChart
```

自动接受条件：

```text
原型证据充分
+ 至少在多个实例或状态复用
+ 与现有 Token 差异超过合并阈值
+ 不引入语义重复
+ 视觉验证提升
+ 无其他区域退化
```

否则应继续使用已有 Token 或登记页面级例外。

---

# 三十、Token 阶段的模型路由

模型不能承担确定性的颜色解析和聚类，这些应由脚本完成。

| 工作 | 执行方 |
|---|---|
| CSS Variables 读取 | 脚本 |
| computed style 采集 | Playwright |
| 颜色/长度归一化 | 脚本 |
| 聚类 | 脚本 |
| 高频统计 | 脚本 |
| 语义初步推断 | 规则引擎 |
| 低置信度视觉语义 | Kimi K3 |
| Token 架构审查 | 主治理模型 |
| 普通迁移补丁 | DeepSeek V4 Flash |
| 补丁接受 | Verifier |
| 门禁判定 | CarrorOS |

Kimi 输入应是小范围任务：

```yaml
task:
  type: token_semantic_disambiguation

  candidates:
    - primitive.color.neutral.600
    - primitive.color.neutral.700

  target:
    property: color
    region: dashboard.metric-card
    element_role: description

  artifacts:
    - reference_crop.png
    - implementation_crop.png
    - computed-style.json
    - contrast-context.json

  output:
    selected_candidate: string
    semantic_role: string
    confidence: number
    visual_reason: string
```

Kimi 输出不直接生效，仍由应用后视觉比较决定是否接受。

---

# 三十一、Token 阶段的停止条件

Token 阶段不能要求“所有可能 Token 永远完整”，而应满足当前 Goal 的冻结基线。

```python
def token_phase_complete(report: dict) -> bool:
    return all([
        report["required_state_coverage"] == 1.0,
        report["style_extraction_coverage"] == 1.0,
        report["critical_token_conflicts"] == 0,
        report["unresolved_critical_semantics"] == 0,
        report["missing_references"] == 0,
        report["reference_cycles"] == 0,
        report["generated_files_consistent"],
        report["unauthorized_raw_colors"] == 0,
        report["unauthorized_arbitrary_values"] == 0,
        report["expired_exceptions"] == 0,
        report["token_visual_regressions"] == 0,
        report["token_compliance"] >= 0.995,
    ])
```

为什么不是一开始就要求 `token_compliance == 1.0`：

- 老项目可能存在当前 Goal 范围之外的遗留裸值；
- 当前夜间任务不能越权修改所有模块；
- `scope_check.py` 会阻止跨范围改动。

因此需要区分：

```yaml
token_compliance:
  goal_scope: 1.0
  changed_files: 1.0
  entire_repository:
    value: 0.93
    blocking: false
    baseline_regression_forbidden: true
```

当前任务负责的页面和变更文件必须 100% 合规；仓库遗留问题可以进入技术债报告，但不允许比基线变差。

---

# 三十二、推荐的 Token 报告

最终生成：

```text
reports/token-system-report.md
```

结构：

```markdown
# Design Token Report

## 1. 采集覆盖
- 路由：4/4
- 必需状态：38/38
- Viewport：2/2
- Overlay：7/7

## 2. Token 数量
- Primitive colors：18
- Semantic colors：24
- Spacing：9
- Radius：6
- Typography：12
- Shadows：5
- Component geometry：31
- State tokens：28

## 3. 置信度
- 自动接受：112
- 视觉验证后接受：17
- 人工/治理模型审查：3
- 未解决关键项：0

## 4. 合规性
- Goal scope：100%
- Changed files：100%
- Repository baseline：93.2%
- 新增违规：0

## 5. 视觉回归
- 验证状态：38
- 改善：14
- 不变：24
- 退化：0

## 6. 例外
- 有效例外：2
- 过期例外：0
- 无证据例外：0

## 7. 摘要
- Token source digest：...
- Semantic map digest：...
- Generated files digest：...
```

`morning_report.py` 应读取这些字段，而不是只报告“Token gate passed”。

---

# 三十三、完整执行命令建议

```bash
# 1. 从第 2 阶段产物中采集样式
python -m scripts.ui_autopilot.tokens extract \
  --run-id dashboard-restoration-20260729

# 2. 归一化
python -m scripts.ui_autopilot.tokens normalize \
  --run-id dashboard-restoration-20260729

# 3. 聚类和语义推断
python -m scripts.ui_autopilot.tokens infer \
  --run-id dashboard-restoration-20260729

# 4. 生成 CSS/TS/Tailwind/AntD
python -m scripts.ui_autopilot.tokens generate \
  --run-id dashboard-restoration-20260729

# 5. 扫描 Goal 范围
python scripts/carroros-gates/token_compliance.py \
  --manifest .omc/ui-autopilot/dashboard-restoration-20260729/goal.yaml

# 6. 分批迁移
python -m scripts.ui_autopilot.tokens migrate \
  --run-id dashboard-restoration-20260729 \
  --batch-size 20

# 7. 执行视觉回归
python -m scripts.ui_autopilot.tokens verify \
  --run-id dashboard-restoration-20260729

# 8. 冻结 Token 基线
python -m scripts.ui_autopilot.tokens lock \
  --run-id dashboard-restoration-20260729

# 9. 进入 CarrorOS 总门禁
python scripts/carroros-gates/run_all.py \
  --manifest .omc/ui-autopilot/dashboard-restoration-20260729/goal.yaml
```

---

# 三十四、第三部分最终结论

升级后的 Token 系统应具备以下性质：

1. **来自原型事实**，不是照搬 Tailwind 或 Ant Design 默认值；
2. **覆盖所有关键页面状态**，不只覆盖默认首屏；
3. **值与语义分层**，避免相同颜色永久耦合；
4. **能够生成 CSS Variables、TypeScript、Tailwind 和 Ant Design 配置**；
5. **自动生成文件不可手工修改**；
6. **所有 Token 可追溯到原型证据**；
7. **新增 Token 必须通过提案和视觉验证**；
8. **Token 变更必须执行影响分析和回归测试**；
9. **当前 Goal 范围内禁止裸色、任意值和魔法数**；
10. **门禁结果进入 CarrorOS 证据链与晨报**。

最终结构是：

```text
原型状态图
    ↓
Computed Styles / CSS Variables / Screenshot Evidence
    ↓
Raw Observations
    ↓
Normalize
    ↓
Cluster
    ↓
Primitive Tokens
    ↓
Semantic + Component + State Tokens
    ↓
CSS Variables（唯一事实源）
    ├── Tailwind
    ├── Ant Design
    ├── CSS Modules
    └── TypeScript
    ↓
裸值扫描与自动迁移
    ↓
视觉回归
    ↓
C5b Token Gate
    ↓
Token Lock
```

至此，**第 3/5 部分完整结束**。下一部分将进入最关键的执行层：**整体框架 → 页面区域 → 区域元素的分层视觉比对、差异定位、根因分类、自动补丁、局部回滚与 99% 收敛算法**。

# CarrorOS UI Autopilot v2：无人化高保真还原方案（第 4/5 部分）

> 本部分解决整个系统最关键的执行问题：**如何按照整体框架 → 页面区域 → 区域元素的顺序，对视觉差异进行量化、定位、归因、修复、验证和回滚，并在避免震荡的前提下持续逼近 99%。**
>
> 完整闭环：
>
> ```text
> 冻结环境
> → 建立对应关系
> → 截图和 DOM 几何测量
> → 多指标视觉比较
> → 差异区域定位
> → 根因分类
> → 生成有边界任务
> → 模型修改
> → CarrorOS 静态门禁
> → 局部与全局视觉验证
> → 接受或回滚
> → 更新任务图
> ```
>
> 本阶段遵守现有治理原则：
>
> - 编码前已有 `research.md + plan.md`；
> - 完成一步立即更新 `executor.md`；
> - 失败立即留痕；
> - 无证据等于没做；
> - 数值断言必须绑定来源；
> - 完成证据不足时自动回到验证阶段；
> - 重复重定向达到上限后阻断当前方向，但继续其他独立任务。

---

## 一、视觉还原不是“截图相似度循环”

最简单的循环：

```python
while screenshot_similarity < 0.99:
    ask_model_to_improve()
```

无法可靠收敛，原因包括：

1. 全局分数无法指出根因；
2. 大面积背景会掩盖小区域严重错误；
3. 字体、阴影、透明度和几何需要不同指标；
4. 子元素偏移可能由父级布局引起；
5. 修复一个区域可能破坏其他页面；
6. 动态内容和抗锯齿会造成测量噪声；
7. 模型可能在两个近似方案之间反复切换；
8. 静态截图无法证明 hover、Modal、折叠等状态完整。

因此，需要建立两套图：

```text
页面结构图 Page Structure Graph
状态转换图 State Transition Graph
```

再对每个节点分别评分。

---

# 二、视觉目标树

每个页面状态都拆成层级目标：

```text
PageState
├── viewport
├── shell
│   ├── sidebar
│   ├── header
│   └── content
├── regions
│   ├── summary
│   ├── trend
│   ├── ranking
│   └── data-table
└── elements
    ├── heading
    ├── metric
    ├── icon
    ├── button
    ├── chart
    └── table-cell
```

数据结构：

```python
# scripts/ui_autopilot/visual/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TargetLevel(StrEnum):
    VIEWPORT = "viewport"
    SHELL = "shell"
    REGION = "region"
    ELEMENT = "element"


class DifferenceKind(StrEnum):
    MISSING = "missing"
    EXTRA = "extra"
    GEOMETRY = "geometry"
    TYPOGRAPHY = "typography"
    COLOR = "color"
    BORDER = "border"
    RADIUS = "radius"
    SHADOW = "shadow"
    ICON = "icon"
    CONTENT = "content"
    OVERFLOW = "overflow"
    LAYERING = "layering"
    INTERACTION = "interaction"
    RESPONSIVE = "responsive"


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


@dataclass(slots=True)
class VisualTarget:
    id: str
    page_id: str
    state_id: str
    viewport_id: str
    level: TargetLevel
    parent_id: str | None

    prototype_selector: str | None
    implementation_selector: str | None
    prototype_box: Box | None
    implementation_box: Box | None

    critical: bool = False
    children: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

为了提高定位稳定性，建议实现代码中增加非视觉语义标记：

```tsx
<aside data-ui-region="sidebar">...</aside>
<header data-ui-region="topbar">...</header>
<main data-ui-region="dashboard-content">
  <section data-ui-region="summary-grid">...</section>
  <section data-ui-region="trend-panel">...</section>
</main>
```

这些属性不影响视觉，但能显著提高自动截图、测量和回归定位的确定性。

---

# 三、建立原型与实现的元素对应关系

原型和实现的 DOM 通常不同，不能直接比较 CSS selector。对应关系按以下优先级建立：

```text
显式 reference-map
→ data-ui-region / data-testid
→ ARIA role + accessible name
→ 文本摘要 + 元素类型
→ 父区域 + 相对几何
→ 截图特征匹配
→ 视觉模型判断
```

对应置信度：

```python
def correspondence_score(candidate) -> float:
    return (
        candidate.explicit_mapping * 0.35
        + candidate.semantic_similarity * 0.25
        + candidate.parent_match * 0.15
        + candidate.text_similarity * 0.10
        + candidate.geometry_similarity * 0.10
        + candidate.visual_similarity * 0.05
    )
```

阈值建议：

```yaml
correspondence:
  auto_accept: 0.90
  accept_with_verification: 0.75
  unresolved_below: 0.75
```

低置信度对应关系不得直接进入自动修复，否则系统可能为了匹配错误元素而破坏正确组件。

产物：

```yaml
# visual/correspondence-map.yaml

mappings:
  - target_id: dashboard.summary-grid
    prototype:
      selector: "[data-region=summary]"
    implementation:
      selector: "[data-ui-region=summary-grid]"
    confidence: 0.98
    method: semantic_and_geometry

  - target_id: dashboard.user-menu
    prototype:
      role: button
      name: 用户菜单
    implementation:
      role: button
      name: 账户
    confidence: 0.78
    verification_required: true
```

---

# 四、冻结视觉比较环境

达到 99% 前必须固定：

```yaml
visual_environment:
  browser: chromium
  playwright_version: locked
  browser_version: locked
  viewport: manifest_defined
  device_scale_factor: 1
  locale: zh-CN
  timezone: Asia/Shanghai
  color_scheme: light
  reduced_motion: reduce
  font_ready_required: true
  missing_font_is_blocker: true
  deterministic_fixture_required: true
  external_network: blocked
  cursor_hidden: true
  caret_hidden: true
  animations_disabled_for_capture: true
```

截图前稳定化需要满足：

```text
字体加载完成
+ 图片加载完成
+ 连续多个采样帧 DOM 几何无明显变化
+ 页面请求进入允许状态
+ 无未处理错误
+ 数据 fixture 已确认
```

动态区域必须采用明确策略：

```yaml
dynamic_regions:
  - target: dashboard.clock
    strategy: fixed_fixture

  - target: chart.animation
    strategy: disable_animation

  - target: avatar.remote-image
    strategy: local_fixture

  - target: generated-id
    strategy: mask
```

不能为了提高分数随意扩大 mask。每个 mask 都必须登记原因和边界，关键区域默认禁止 mask。

---

# 五、多指标视觉评分

最终分数不能只使用 SSIM 或像素一致率。建议建立六类指标。

## 1. 完整性

```text
required target 是否存在
多余元素是否出现
文本、图标、图片是否完整
滚动内容是否完整
```

## 2. 几何

比较：

```text
x / y / width / height
中心点
面积
边缘
父子间距
对齐线
Grid/Flex 轨道
滚动范围
```

## 3. 排版

比较：

```text
字体族
字号
字重
行高
字间距
换行位置
文本块尺寸
基线和对齐
```

## 4. 表面视觉

比较：

```text
颜色
背景
边框
圆角
阴影
透明度
```

## 5. 像素视觉

比较：

```text
像素差异
SSIM
感知哈希
边缘图
局部特征
```

## 6. 状态与交互

比较：

```text
hover
focus
active
selected
expanded
open
loading
empty
error
```

评分模型：

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetScore:
    completeness: float
    geometry: float
    typography: float
    color: float
    decoration: float
    pixel: float
    interaction: float

    def composite(self, level: TargetLevel) -> float:
        weights = {
            TargetLevel.VIEWPORT: {
                "completeness": 0.20,
                "geometry": 0.35,
                "typography": 0.10,
                "color": 0.10,
                "decoration": 0.05,
                "pixel": 0.15,
                "interaction": 0.05,
            },
            TargetLevel.REGION: {
                "completeness": 0.20,
                "geometry": 0.25,
                "typography": 0.15,
                "color": 0.10,
                "decoration": 0.10,
                "pixel": 0.15,
                "interaction": 0.05,
            },
            TargetLevel.ELEMENT: {
                "completeness": 0.15,
                "geometry": 0.20,
                "typography": 0.20,
                "color": 0.10,
                "decoration": 0.15,
                "pixel": 0.15,
                "interaction": 0.05,
            },
        }[level]

        values = {
            "completeness": self.completeness,
            "geometry": self.geometry,
            "typography": self.typography,
            "color": self.color,
            "decoration": self.decoration,
            "pixel": self.pixel,
            "interaction": self.interaction,
        }

        return sum(values[key] * value for key, value in weights.items())
```

权重必须写入 manifest 并锁定。运行中禁止为了通过门禁临时修改权重或阈值。

---

# 六、几何评分

几何误差应相对 viewport 和目标尺寸归一化：

```python
def geometry_score(reference: Box, actual: Box, viewport: Box) -> float:
    position_error = (
        abs(reference.x - actual.x) / max(1.0, viewport.width)
        + abs(reference.y - actual.y) / max(1.0, viewport.height)
    ) / 2

    size_error = (
        abs(reference.width - actual.width) / max(1.0, reference.width)
        + abs(reference.height - actual.height) / max(1.0, reference.height)
    ) / 2

    iou_score = intersection_over_union(reference, actual)

    error = (
        position_error * 0.30
        + size_error * 0.35
        + (1.0 - iou_score) * 0.35
    )

    return max(0.0, 1.0 - error)
```

还要记录可操作差异：

```json
{
  "target": "dashboard.summary-grid",
  "prototype": {
    "x": 280,
    "y": 88,
    "width": 1136,
    "height": 156
  },
  "implementation": {
    "x": 264,
    "y": 80,
    "width": 1152,
    "height": 168
  },
  "delta": {
    "x": -16,
    "y": -8,
    "width": 16,
    "height": 12
  },
  "suspectedAncestor": "dashboard.content"
}
```

模型应读取这些测量，而不是仅凭截图猜测 `margin`。

---

# 七、像素差异必须分层处理

推荐生成四类 diff：

```text
absolute-diff.png       直接像素差
threshold-diff.png      过滤微小栅格化噪声
edge-diff.png           边缘和几何偏差
heatmap.png             差异密度可视化
```

Playwright 截图：

```typescript
export async function captureTarget(
  page: Page,
  selector: string,
  path: string,
): Promise<void> {
  const target = page.locator(selector);
  await target.waitFor({ state: 'visible' });

  await target.screenshot({
    path,
    animations: 'disabled',
    caret: 'hide',
    scale: 'css',
  });
}
```

像素比较要允许极小噪声，但不能使用过宽阈值：

```yaml
pixel_comparison:
  per_channel_threshold: 8
  maximum_noise_ratio: 0.001
  antialiasing_tolerance: limited
  critical_regions:
    per_channel_threshold: 4
  text_regions:
    combine_with_geometry: true
```

字体区域不能只依赖像素差，因为不同平台抗锯齿可能产生大量假阳性。必须结合字体计算值和文本边界。

---

# 八、差异连通域定位

整张 diff 应切成可处理的连通区域：

```python
@dataclass(frozen=True, slots=True)
class DifferenceRegion:
    id: str
    box: Box
    changed_pixel_ratio: float
    mean_delta: float
    edge_delta: float
    overlapping_targets: tuple[str, ...]


def merge_nearby_regions(
    regions: list[DifferenceRegion],
    distance_px: int = 8,
) -> list[DifferenceRegion]:
    # 使用膨胀后的矩形相交关系构图，再合并连通分量。
    ...
```

每个差异区域映射到视觉目标树：

```text
diff box
→ 找出重叠目标
→ 优先选择最小可解释共同祖先
→ 判断是局部问题还是祖先系统性问题
```

例如四张卡片都向右偏移 `16px`：

```text
不要生成 4 个卡片 margin 修复任务
→ 识别相同方向和幅度
→ 找到共同祖先 summary-grid
→ 检查 content padding
→ 生成 1 个父级几何任务
```

---

# 九、根因分类器

建议定义以下根因：

```yaml
root_causes:
  - missing_component
  - extra_component
  - ancestor_geometry
  - local_geometry
  - wrong_layout_model
  - spacing_token
  - component_token
  - typography_token
  - color_token
  - state_style
  - overflow_clipping
  - stacking_context
  - asset_mismatch
  - content_fixture
  - browser_environment
  - correspondence_error
  - unknown
```

规则示例：

```python
def classify_root_cause(observation) -> str:
    if observation.reference_exists and not observation.actual_exists:
        return "missing_component"

    if not observation.reference_exists and observation.actual_exists:
        return "extra_component"

    if observation.same_delta_across_siblings:
        return "ancestor_geometry"

    if observation.text_box_differs and observation.font_style_differs:
        return "typography_token"

    if observation.geometry_matches and observation.color_differs:
        return "color_token"

    if observation.clipped_content and observation.overflow_hidden:
        return "overflow_clipping"

    if observation.overlay_position_wrong:
        return "stacking_context"

    if observation.reference_asset_digest != observation.actual_asset_digest:
        return "asset_mismatch"

    return "unknown"
```

根因诊断必须满足现有 RCA 门禁要求：包含量化数据、代码位置和跨步骤错误去重。仅写“样式不一致”不算有效根因。

---

# 十、分阶段收敛

## Phase S：整体框架

只允许修改：

```text
viewport
body/root
app shell
sidebar/header/content
主要 Grid/Flex 轨道
全局背景
主滚动容器
```

门禁：

```yaml
shell:
  completeness: 1.0
  geometry: 0.995
  minimum_region_geometry: 0.985
  runtime_errors: 0
```

此阶段禁止微调图标、阴影和单个按钮。

## Phase R：页面区域

按区域修复：

```text
summary-grid
chart-panel
ranking-panel
table
filter-bar
floating-actions
```

门禁：

```yaml
regions:
  average_similarity: 0.99
  minimum_similarity: 0.985
  critical_similarity: 0.995
  missing_regions: 0
  extra_regions: 0
```

## Phase E：元素和排版

处理：

```text
文字
图标
按钮
边框
圆角
阴影
内部间距
单元格
图表细节
```

门禁：

```yaml
elements:
  typography: 0.99
  color: 0.99
  decoration: 0.99
  minimum_critical_element: 0.99
```

## Phase I：交互状态

处理：

```text
hover/focus/active
Tab
菜单
Tooltip
Popover
Modal
Drawer
折叠/展开
loading/empty/error
```

门禁：

```yaml
interactions:
  required_transition_coverage: 1.0
  required_state_coverage: 1.0
  visual_similarity: 0.99
  semantic_assertions_passed: true
```

后一个阶段发现父级根因时允许降级：

```text
ELEMENT → REGION
REGION → SHELL
INTERACTION → ELEMENT/REGION
```

降级必须写入事件日志，禁止静默扩大修改范围。

---

# 十一、任务优先级

每轮不应该简单选择最低分目标。推荐：

```python
def repair_priority(target) -> float:
    return (
        target.error_severity * 0.30
        + target.visible_area_ratio * 0.20
        + target.descendant_impact * 0.20
        + target.fix_confidence * 0.15
        + float(target.critical) * 0.15
        - target.change_risk * 0.20
        - target.recent_attempt_penalty * 0.15
    )
```

调度规则：

1. 先修复高影响父级；
2. 同层级先修复缺失和额外内容；
3. 再修几何；
4. 再修排版；
5. 最后修颜色、阴影和图标；
6. 连续失败目标降低优先级并进入诊断队列；
7. 被阻塞目标不影响独立目标继续运行。

---

# 十二、有边界修复任务

任务必须包含量化事实和允许范围：

```yaml
task:
  id: VIS-REGION-0042
  phase: regions
  target_id: dashboard.summary-grid
  root_cause: ancestor_geometry
  confidence: 0.93

  score:
    current: 0.9471
    required: 0.985

  measurements:
    prototype:
      x: 280
      y: 88
      width: 1136
      height: 156
    implementation:
      x: 264
      y: 80
      width: 1152
      height: 168

  diagnosis:
    common_sibling_offset: true
    suspected_selector: "[data-ui-region=dashboard-content]"
    suspected_properties:
      - padding-inline
      - padding-top

  allowed_files:
    - src/layouts/AppShell/AppShell.module.scss
    - src/features/dashboard/DashboardPage.module.scss

  prohibited:
    - edit_reference_images
    - change_visual_thresholds
    - add_masks
    - edit_unrelated_regions
    - add_raw_css_values
    - modify_auth_or_router
    - modify_generated_tokens

  verification:
    target_states:
      - dashboard-default-desktop-1440
      - dashboard-sidebar-collapsed-desktop-1440
    regression_states:
      - reports-default-desktop-1440
    minimum_target_improvement: 0.005
    maximum_regression: 0.001
```

模型只能生成补丁和诊断结果，不能决定任务是否通过。

---

# 十三、修复事务

每次修复都是一个事务：

```text
1. 保存 Git/文件 checkpoint
2. 记录基线截图、分数和源码摘要
3. 执行 bounded worker
4. 检查修改范围
5. 执行 lint/typecheck/test
6. 执行 CarrorOS 门禁
7. 重启或刷新实现
8. 重放状态路径
9. 截取局部和全局截图
10. 计算新分数
11. 检查目标改善与旁路回归
12. 接受或恢复 checkpoint
13. 写 event-log、executor 和 evidence
```

接受规则：

```python
def accept_patch(before, after, policy) -> tuple[bool, str]:
    if not after.scope_gate_passed:
        return False, "scope_violation"

    if not after.static_gates_passed:
        return False, "static_gate_failure"

    if after.runtime_errors > before.runtime_errors:
        return False, "runtime_regression"

    improvement = after.target_score - before.target_score

    if improvement < policy.minimum_target_improvement:
        return False, "insufficient_improvement"

    if after.minimum_regression_delta < -policy.maximum_regression:
        return False, "visual_regression"

    if after.required_evidence_missing:
        return False, "missing_evidence"

    return True, "accepted"
```

目标分数提高但其他关键区域退化时仍然拒绝。

---

# 十四、局部验证与全局验证

每次都跑所有状态会浪费大量时间，因此采用分级回归。

```text
L0：当前元素 crop
L1：当前区域
L2：当前页面状态
L3：相邻和共享组件状态
L4：所有页面与 viewport
```

选择策略：

```yaml
verification_scope:
  page_local_change:
    required:
      - L0
      - L1
      - L2

  shared_component_change:
    required:
      - L0
      - L1
      - L2
      - L3

  semantic_token_change:
    required:
      - L2
      - L3
      - L4

  primitive_token_change:
    required:
      - L4

  final_audit:
    required:
      - L4
```

依赖图用于计算受影响状态：

```text
源码文件
→ 组件
→ 页面区域
→ 页面状态
→ 路由和 viewport
```

---

# 十五、震荡和重复编辑检测

系统需要识别：

```text
sidebar width: 240 → 256 → 248 → 256
padding: 20 → 24 → 20
模型 A 与模型 B 交替覆盖
```

记录：

```json
{
  "target": "dashboard.sidebar",
  "property": "width",
  "history": [
    {"value": "240px", "score": 0.94},
    {"value": "256px", "score": 0.97},
    {"value": "248px", "score": 0.96},
    {"value": "256px", "score": 0.97}
  ]
}
```

策略：

```yaml
churn:
  repeated_patch_fingerprint:
    action: reject

  alternating_property_values:
    threshold: 2
    action: lock_best_known_value

  repeated_file_edits:
    threshold: 4
    action: require_root_cause_review

  same_failure_signature:
    threshold: 3
    action: abandon_direction_for_6h
```

这与现有自主执行规则一致：连续重定向达到上限后升级为阻断并放弃当前方向，但不结束其他可运行任务。

---

# 十六、停滞诊断与模型升级

停滞不能直接继续发送同一 Prompt。

```text
第 1 次失败：
补充 DOM、computed style 和几何测量后重试

第 2 次失败：
重新检查元素对应关系与父级根因

第 3 次失败：
生成局部 reference / implementation / diff crop，调用 Kimi K3

第 4 次失败：
交给主治理模型判断是否降级阶段或修改任务边界

第 5 次失败：
锁定最佳 checkpoint，冻结该目标，继续其他独立目标

达到目标最大次数：
标记 BLOCKED，形成 blocker report
```

视觉模型输入必须包括：

```text
原型 crop
实现 crop
diff heatmap
目标和祖先几何
computed styles
Token 候选
历史补丁
历史得分
当前任务边界
```

视觉模型只输出诊断，不拥有修改门禁、阈值或基准图的权限。

---

# 十七、图标、图片与图表的专项比较

## 图标

优先比较：

```text
图标语义
资源身份
viewBox
宽高
strokeWidth
颜色
对齐
```

若原型使用已有图标库，优先使用项目现有库或 `lucide-react`，不手写近似 SVG。

## 图片

比较：

```text
资源摘要
object-fit
object-position
裁剪区域
透明度
圆角
清晰度
```

错误资源不能通过 CSS 调整“修成”正确图片。

## 图表

图表必须固定：

```text
数据 fixture
时间范围
颜色序列
坐标范围
tick
tooltip 状态
动画关闭
canvas DPR
```

Canvas 图表除了截图，还要执行像素非空检查：

```typescript
const hasRenderedPixels = await page.locator('canvas').evaluate(canvas => {
  const context = canvas.getContext('2d');
  if (!context) return false;

  const pixels = context.getImageData(
    0,
    0,
    canvas.width,
    canvas.height,
  ).data;

  return pixels.some((value, index) => index % 4 !== 3 && value !== 0);
});
```

---

# 十八、交互状态验证

每个状态必须绑定：

```text
进入路径
视觉快照
语义断言
关闭或回退路径
副作用断言
```

`assertion-catalog.yaml` 应登记：

```yaml
state_assertions:
  sidebar_collapsed:
    helper: assertSidebarCollapsed
    required:
      - width_matches
      - labels_hidden
      - icons_visible
      - content_reflowed

overlay_assertions:
  user_menu_open:
    helper: assertUserMenuOpen
    required:
      - overlay_visible
      - trigger_expanded
      - focus_valid
      - outside_click_closes
      - escape_closes
```

现有 `preflight.py` 已检查 catalog ID 是否在 `tests/e2e/helpers/assertions.ts` 中绑定。第四阶段新增断言时，必须同步 helper，否则不能进入执行。

Playwright 示例：

```typescript
test('用户菜单完整状态', async ({ page }) => {
  const trigger = page.getByRole('button', { name: '用户菜单' });

  await trigger.click();
  await assertUserMenuOpen(page);

  await expect(page).toHaveScreenshot('dashboard-user-menu.png', {
    animations: 'disabled',
  });

  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
});
```

---

# 十九、视觉门禁 C6b/C6c/C6d

建议扩展 `gate-contract.yaml`：

```yaml
gates:
  C6b:
    name: regional-visual-fidelity
    blocking: true
    acceptance:
      global_similarity: 0.99
      minimum_region_similarity: 0.985
      critical_region_similarity: 0.995
      geometry_score: 0.995
      visual_regressions: 0

  C6c:
    name: interaction-state-coverage
    blocking: true
    acceptance:
      required_state_coverage: 1.0
      required_transition_coverage: 1.0
      assertion_failures: 0
      unresolved_overlays: 0

  C6d:
    name: scroll-and-content-coverage
    blocking: true
    acceptance:
      document_scroll_coverage: 1.0
      nested_scroll_coverage: 1.0
      missing_content_regions: 0
      overflow_failures: 0
```

门禁产物：

```text
evidence/
├── visual-score-report.json
├── region-score-report.json
├── interaction-coverage-report.json
├── scroll-coverage-report.json
├── correspondence-map.yaml
├── regression-impact.json
├── screenshots/
├── diffs/
└── measurements/
```

---

# 二十、`run_all.py` 集成顺序

建议顺序：

```text
preflight
→ control-plane lock
→ scope check
→ C1 lint
→ C2 typecheck
→ C3 unit tests
→ C4 build
→ C5/C5b Token gate
→ C6 browser runtime
→ C6b regional visual gate
→ C6c interaction gate
→ C6d scroll coverage gate
→ C7/c7_check
→ evidence_check
→ finalize_page
→ morning_report
```

视觉验证不能早于：

```text
构建成功
+ fixture 可用
+ 浏览器环境一致
+ Token 合规
```

`finalize_page.py` 不得只检查总分，应确认每个 blocking gate 都有成功结果和摘要绑定。

---

# 二十一、Manifest 增量

```yaml
visual_verification:
  enabled: true

  correspondence_map:
    .omc/ui-autopilot/${RUN_ID}/visual/correspondence-map.yaml

  scoring:
    global_similarity: 0.99
    minimum_region_similarity: 0.985
    critical_region_similarity: 0.995
    geometry_score: 0.995
    typography_score: 0.99
    color_score: 0.99
    minimum_effective_improvement: 0.0005
    maximum_allowed_regression: 0.001

  phases:
    - shell
    - regions
    - elements
    - interactions
    - responsive

  screenshots:
    reference_root:
      .omc/ui-autopilot/${RUN_ID}/prototype/screenshots
    actual_root:
      .omc/ui-autopilot/${RUN_ID}/implementation/screenshots
    diff_root:
      .omc/ui-autopilot/${RUN_ID}/diffs

  masks:
    registry:
      .omc/ui-autopilot/${RUN_ID}/visual/masks.yaml
    critical_regions_allowed: false

  repair:
    max_attempts_per_target: 8
    rollback_on_regression: true
    freeze_after_repeated_stagnation: true
```

所有阈值在生成控制面锁后不得修改。`gen_control_plane_lock.py` 应将以下内容加入摘要：

```text
评分权重
验收阈值
mask registry
参考截图摘要
correspondence map
viewport
浏览器环境
动态区域策略
```

---

# 二十二、完成判定

不能采用平均分单点判定：

```python
def visual_phase_complete(report: dict) -> bool:
    return all([
        report["required_target_coverage"] == 1.0,
        report["required_state_coverage"] == 1.0,
        report["required_transition_coverage"] == 1.0,
        report["scroll_coverage"] == 1.0,

        report["global_similarity"] >= 0.99,
        report["minimum_region_similarity"] >= 0.985,
        report["critical_region_similarity"] >= 0.995,
        report["geometry_score"] >= 0.995,
        report["typography_score"] >= 0.99,
        report["color_score"] >= 0.99,

        report["missing_required_targets"] == 0,
        report["extra_blocking_targets"] == 0,
        report["visual_regressions"] == 0,
        report["runtime_errors"] == 0,
        report["console_errors"] == 0,
        report["unresolved_blockers"] == 0,
        report["required_evidence_complete"],
    ])
```

模型输出“已完成”不改变任务状态。只有该函数及 CarrorOS blocking gates 全部通过后，Orchestrator 才能将阶段标记为完成。

---

# 二十三、完整执行流程

```text
1. 从第 2 部分读取原型 Page Graph
2. 从第 3 部分读取冻结 Token
3. 为实现页面添加 data-ui-region
4. 建立 prototype ↔ implementation 对应关系
5. 捕获全量实现状态
6. 生成目标树和初始评分
7. 进入 Shell 阶段
8. 选择最高影响差异
9. 执行 bounded patch transaction
10. 接受改善补丁，回滚退化补丁
11. Shell 通过后进入 Region
12. Region 通过后进入 Element
13. 完成 Interaction 和 Responsive
14. 执行全量 L4 回归
15. 运行 C6b/C6c/C6d
16. 将结果交给 evidence_check
17. 仅在所有 blocking gate 通过后允许 finalize
```

推荐命令：

```bash
python -m scripts.ui_autopilot.visual baseline \
  --run-id dashboard-restoration-20260729

python -m scripts.ui_autopilot.visual build-target-tree \
  --run-id dashboard-restoration-20260729

python -m scripts.ui_autopilot.visual run-repair-loop \
  --run-id dashboard-restoration-20260729 \
  --phase shell

python -m scripts.ui_autopilot.visual verify-all \
  --run-id dashboard-restoration-20260729

python scripts/carroros-gates/run_all.py \
  --manifest .omc/ui-autopilot/dashboard-restoration-20260729/goal.yaml
```

---

# 二十四、第四部分最终结论

视觉还原执行层必须具备以下性质：

1. 原型和实现通过稳定身份对应，不依赖偶然 DOM；
2. 页面被拆成 viewport、shell、region 和 element 四层；
3. 先完整性、再几何、再排版和装饰；
4. 使用多指标评分，不让全局 SSIM 掩盖局部错误；
5. 差异区域映射到最小可解释共同祖先；
6. 每个修复任务都包含测量、根因、范围和验收条件；
7. 每次补丁都是可回滚事务；
8. 当前目标改善但旁路区域退化时拒绝补丁；
9. 重复失败触发重新测量、视觉诊断、阶段降级或冻结；
10. 所有页面、滚动区域和交互状态必须 100% 覆盖；
11. 视觉阈值、mask、参考图和评分权重受控制面锁保护；
12. 最终完成权只属于 Verifier 和 CarrorOS 门禁。

最终闭环是：

```text
页面状态图 + Token 基线
          ↓
建立目标树和对应关系
          ↓
Shell → Region → Element → Interaction → Responsive
          ↓
测量 → 归因 → 有边界补丁 → 静态门禁 → 视觉验证
          ↓
       改善？
      /     \
    是       否
    ↓        ↓
  接受      回滚
    ↓        ↓
更新最佳点  重新诊断/升级/冻结
          ↓
全量状态与 viewport 回归
          ↓
C6b + C6c + C6d + Evidence Gate
          ↓
严格达到 99% 且无局部、交互和覆盖缺口
```

至此，**第 4/5 部分完整结束**。第 5 部分将完成整套方案：多模型调用协议、CarrorOS C0–C8a 集成、控制面锁、6 小时守护与恢复、故障分类、晨报、最终验收，以及针对现有文件的逐项改造清单。

# CarrorOS UI Autopilot v2：第 5/5 部分

> 本部分完成整个方案：**三模型协作协议、CarrorOS C0-C8a 集成、控制面锁、6 小时无人守护、故障恢复、晨报、最终验收，以及现有文件的逐项升级清单。**

最终运行链路：

```text
Phase 0 人工签署
→ 冻结 Goal、范围、原型、阈值和模型权限
→ 原型发现与 Token 建模
→ 分层视觉修复循环
→ C0-C8a 全门禁
→ 证据校验与最终验收
→ 晨报
```

## 一、三模型职责必须互斥

三个模型不能同时自由修改代码。建议固定角色：

| 模型 | 角色 | 权限 |
|---|---|---|
| `gpt-5.6 Sol` | Orchestrator / Architect | 拆解 Goal、调度任务、根因升级、最终综合判断；默认不直接接受自己的补丁 |
| `opus-5` | Reviewer / Adversarial Verifier | 审查架构、对应关系、视觉根因和高风险补丁；只读或输出建议补丁 |
| `grok-4.5` | Worker / Alternative Diagnostician | 执行边界明确的 React、Tailwind、Ant Design 修复任务；无权改门禁与基准 |
| CarrorOS | Deterministic Authority | 范围、静态检查、测试、证据、视觉阈值和完成状态的唯一裁决者 |

核心约束：

```text
模型提出修改 ≠ 修改有效
模型声称完成 ≠ 阶段完成
只有确定性门禁通过，状态才能向前推进
```

每次模型调用统一使用结构化信封：

```yaml
request:
  task_id: VIS-REGION-0042
  role: worker
  goal: 修复 dashboard.summary-grid 父级几何偏差
  allowed_files:
    - src/features/dashboard/DashboardPage.module.scss
  prohibited_files:
    - scripts/carroros-gates/**
    - src/styles/tokens/generated/**
  evidence:
    measurements: evidence/measurements/VIS-REGION-0042.json
    reference_crop: evidence/reference/VIS-REGION-0042.png
    actual_crop: evidence/actual/VIS-REGION-0042.png
    diff: evidence/diffs/VIS-REGION-0042.png
  acceptance:
    minimum_improvement: 0.005
    maximum_regression: 0.001
  output_schema:
    diagnosis: string
    changed_files: string[]
    patch_summary: string
    risks: string[]
```

模型不得修改：参考图、mask、评分权重、验收阈值、signoff、control-plane lock、门禁脚本和自己的任务边界。

## 二、控制面锁

`gen_control_plane_lock.py` 应将以下输入规范化后计算摘要：

```text
night manifest + signoff
Goal 和 allowed paths
原型 URL、Page Graph、参考截图 digest
viewport、浏览器与 fixture
Token 源和语义映射
assertion catalog
评分权重与阈值
mask registry
模型路由与调用预算
重试、回滚和停止策略
```

建议锁文件：

```json
{
  "schemaVersion": 2,
  "runId": "dashboard-restoration-20260729",
  "manifestSha256": "...",
  "signoffSha256": "...",
  "prototypeSha256": "...",
  "tokenSha256": "...",
  "visualPolicySha256": "...",
  "assertionCatalogSha256": "...",
  "modelPolicySha256": "...",
  "createdAt": "2026-07-29T12:00:00Z"
}
```

`preflight.py` 已有 signoff 与 manifest 字节哈希校验；应继续扩展为上述多源摘要校验。运行中任何锁定输入改变，都立即停止并记录 `CONTROL_PLANE_DRIFT`，不能自动重签。

## 三、C0-C8a 完整门禁链

建议最终门禁顺序：

```text
C0a  manifest / signoff / control-plane lock
C0b  research.md + plan.md + executor.md
C0c  原型 Page Graph 和全状态发现覆盖
C1   lint
C2   typecheck
C3   unit/component tests
C4   production build
C5   UI 宪法与代码规范
C5b  Design Token 合规与漂移检测
C6   浏览器运行时、console、network、fixture
C6b  Shell/Region/Element 视觉保真
C6c  交互状态与 assertion catalog 覆盖
C6d  文档滚动、嵌套滚动和内容完整性
C7   文件规模、职责边界、抽象与魔法值
C8   evidence_check 双源证据和摘要绑定
C8a  finalize_page 最终完成判定
```

`UI_README.md` 已明确：Web 优先、最小 1280px；Token 唯一来源为 `src/styles/tokens/`；`.tsx` 和 `.module.scss` 均不超过 300 行、单文件不超过 3 个功能块，并禁止裸色和 px 魔法数。新门禁应直接复用这些规则，不建立第二套相互冲突的规范。

## 四、6 小时无人守护循环

夜间控制器采用持久化状态机：

```text
BOOTSTRAP → DISCOVER → TOKENS → IMPLEMENT
→ VERIFY → REPAIR → FULL_AUDIT → FINALIZE
```

每轮执行：

```python
while not deadline_reached():
    reconcile_runtime_state()
    verify_control_plane_lock()
    recover_interrupted_transaction()
    runnable = scheduler.get_runnable_tasks()

    if not runnable:
        if scheduler.has_blockers():
            write_blocker_report()
        break

    task = scheduler.select_highest_priority(runnable)
    checkpoint = transaction.begin(task)
    result = worker.execute(task)
    verification = verifier.verify(task, result)

    if verification.accepted:
        transaction.commit(checkpoint)
        task.mark_completed(verification.evidence)
    else:
        transaction.rollback(checkpoint)
        retry_policy.record_failure(task, verification)

    persist_state_atomically()
    update_executor_immediately()
```

持久化目录：

```text
.omc/ui-autopilot/{run-id}/
├── control-plane.lock.json
├── state.json
├── task-graph.json
├── event-log.jsonl
├── checkpoints/
├── transactions/
├── prototype/
├── evidence/
├── blockers/
└── reports/
```

所有状态文件采用临时文件写入后原子替换。进程重启时根据 transaction journal 判断：已验证但未提交则补提交；修改未验证则回滚；状态不明则恢复 checkpoint 并重新验证。

## 五、故障分类和恢复策略

```yaml
failure_policy:
  transient_browser:
    retries: 3
    action: restart_context
  dev_server_crash:
    retries: 2
    action: restart_server_and_replay
  model_timeout:
    retries: 2
    action: retry_with_same_bounded_task
  invalid_model_output:
    retries: 1
    action: schema_repair_then_switch_model
  static_gate_failure:
    action: return_to_worker
  visual_regression:
    action: rollback
  repeated_failure_signature:
    threshold: 3
    action: freeze_direction_and_escalate
  control_plane_drift:
    retries: 0
    action: abort_run
  missing_reference_or_auth:
    retries: 0
    action: block_goal
```

错误签名应由错误类型、目标、关键日志和失败断言规范化后哈希，避免同一错误换一种文本后重复消耗预算。

## 六、预算和停止条件

```yaml
runtime_budget:
  wall_clock_hours: 6
  model_calls: 120
  repair_attempts_per_target: 8
  browser_restarts: 8
  full_regressions: 12
  reserve_minutes_for_final_audit: 30
```

提前停止仅有三种合法情况：

1. 所有 blocking gate 通过并成功 finalize；
2. 剩余任务全部被不可恢复依赖阻断；
3. 进入最终审计保留时间，停止新修复并验证当前最佳 checkpoint。

超时不能伪装为完成。系统应保留最佳已验证版本，并明确输出 `PARTIAL` 或 `BLOCKED`。

## 七、证据与最终完成协议

`evidence_check.py` 应验证每项结论至少拥有：

```text
原型事实源：截图、DOM、ARIA、computed style、状态路径之一
实现事实源：源码、构建产物、浏览器测量、测试日志之一
验证事实源：diff、评分报告、断言结果、回归报告之一
```

`finalize_page.py` 只在以下条件全部满足时写入完成状态：

```python
finalizable = all([
    control_plane_lock_valid,
    all_blocking_gates_passed,
    required_state_coverage == 1.0,
    required_transition_coverage == 1.0,
    scroll_coverage == 1.0,
    global_similarity >= 0.99,
    minimum_region_similarity >= 0.985,
    critical_region_similarity >= 0.995,
    visual_regressions == 0,
    runtime_errors == 0,
    scope_violations == 0,
    unresolved_blockers == 0,
    evidence_complete,
])
```

最终记录必须绑定当前 Git tree、manifest、signoff、原型、Token、截图和报告摘要，防止验证完成后文件又被修改。

## 八、晨报

`morning_report.py` 不应只输出 PASS/FAIL。推荐内容：

```markdown
# Night Run Report

- 结果：PASS / PARTIAL / BLOCKED / FAILED
- 运行时间：5h 42m
- 最佳 checkpoint：abc123
- 完成任务：37/41
- 门禁：18 PASS，1 BLOCKED
- 全局相似度：99.24%
- 最低区域：98.71%
- 状态覆盖：38/38
- 回滚补丁：12
- 模型调用：Sol 18 / Opus 11 / Grok 46
- 剩余阻断：原型缺失 mobile drawer 打开态
```

同时列出改动文件、失败签名、例外、阈值、mask、Token 提案和用户早晨需要处理的最小动作。

## 九、现有文件逐项升级

| 文件 | 必需升级 |
|---|---|
| `night-manifest.template.yaml` | 新增 prototype、token、visual、model routing、budget、recovery 和 artifact 配置 |
| `night-manifest.signoff.template.yaml` | 签署 Goal、范围、参考基准、阈值、mask、模型权限及对应 digest |
| `preflight.py` | 校验 C0a-C0c、原型可访问性、断言绑定、字体、fixture 和控制面摘要 |
| `gen_control_plane_lock.py` | 锁定所有治理输入，而非只锁 manifest |
| `gate-contract.yaml` | 声明 C0c、C5b、C6b、C6c、C6d、C8a 及其产物和阈值 |
| `run_gate.py` | 统一超时、日志、摘要、退出码和可重入行为 |
| `run_all.py` | 按依赖图运行门禁，阻断项 fail-closed，写结构化总报告 |
| `scope_check.py` | 校验任务 allowed files、实际 diff、生成文件和例外路径 |
| `assertion-catalog.yaml` | 增加原型状态 ID、进入/退出路径和 helper 绑定 |
| `c7_check.py` | 加入 300 行、3 功能块、裸值、任意 Tailwind 值和重复抽象检查 |
| `abstraction_check.py` | 发现重复组件和无依据抽象，但避免阻塞原型独有组件 |
| `evidence_check.py` | 双源/三源证据、digest、时效性和任务关联验证 |
| `finalize_page.py` | 按全部 blocking gate 和不可变摘要进行唯一完成判定 |
| `morning_report.py` | 输出分数、覆盖、回滚、模型成本、阻断和下一动作 |
| `install_night_hook.py` | 安装 watchdog、恢复入口、日志轮转和异常退出处理 |
| `night-loop.md` | 写入新状态机、事务、升级、预算和恢复协议 |
| `phase0-checklist.md` | 增加原型权限、viewport、字体、fixture、阈值和 mask 签署 |
| `intake.md` | 定义输入成熟度，缺少关键状态时禁止夜间点火 |
| `UI_README.md` | 保留 UI 宪法，补充自动发现、Token 和视觉证据规则 |
| `SOP.md` | 将操作者动作继续限制为放输入、签署、晨审 |

建议新增模块：

```text
scripts/ui_autopilot/
├── discovery/
├── tokens/
├── visual/
├── orchestration/
│   ├── scheduler.py
│   ├── transactions.py
│   ├── retry_policy.py
│   ├── model_router.py
│   └── watchdog.py
└── reports/
```

## 十、实施顺序

不要一次性重写全部门禁。按风险递增实施：

```text
M1：扩展 manifest/signoff/control-plane lock
M2：实现原型 Page Graph 与 C0c
M3：实现 Token 管线与 C5b
M4：实现目标树、区域评分与 C6b
M5：实现交互/滚动覆盖 C6c/C6d
M6：接入事务、回滚和多模型路由
M7：实现 watchdog、恢复、晨报与 C8a
M8：以一个页面进行 shadow run
M9：与人工结果对照并校准阈值
M10：扩大到多页面 6 小时无人运行
```

每个里程碑都必须兼容现有 `run_all.py`，先以可选 gate 接入；经过 shadow run 后再转为 blocking，避免治理基础设施一次性替换导致夜间链路不可用。

## 十一、最终验收清单

上线无人模式前至少通过：

- 同一输入连续运行两次，产物和结论可重复；
- 任意模型修改阈值、参考图或门禁时被拦截；
- 浏览器、服务器和主进程崩溃后可以恢复；
- 退化补丁自动回滚，且不会污染最佳 checkpoint；
- 相同错误不会无限重试；
- 页面底部、嵌套滚动和浮层均有覆盖证据；
- Goal 范围内 Token 合规率为 100%；
- 所有必需状态和转换覆盖率为 100%；
- 全局相似度至少 99%，关键区域至少 99.5%；
- `finalize_page.py` 无法被模型文本或伪造单个报告绕过；
- 晨报能够解释做了什么、为什么停止、还缺什么。

## 最终结论

五部分组合后，CarrorOS UI Autopilot v2 不再是“让模型看图写页面”，而是一个受控的软件工程闭环：

```text
Goal 与控制面冻结
→ 原型全状态建模
→ Design Token 事实提取
→ Shell / Region / Element / Interaction 分层修复
→ 三模型按权限协作
→ 每个补丁独立验证和回滚
→ C0-C8a 确定性门禁
→ 完整证据链与晨报
```

真正的无人化标准不是模型能持续写 6 小时代码，而是系统能在无人值守期间持续作出四个可靠判断：**下一步做什么、补丁是否改善、失败后如何恢复、何时才允许宣布完成。**

至此，CarrorOS UI Autopilot v2 的 **5/5 完整方案结束**。当前仍是设计方案，尚未修改实际文件；正式落地应从 M1 的 manifest、signoff 和 control-plane lock 开始。
