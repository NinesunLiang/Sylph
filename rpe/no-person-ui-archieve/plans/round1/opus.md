# Opus 视角：CarrorOS UI Autopilot v2 根本性分歧与替代方案（第1/5 部分）

> 我对 GPT 方案的核心判断是：**架构方向正确，但解决的是错误问题
>
> GPT 把失败归因于"缺少管道阶段"，因此用五个部分填充了更多阶段。但 OPTIMIZATION-FACTSET.md 揭示的真实失败不是缺阶段，而是：**循环的退出条件和进度信号从根本上是坏掉的。**
>
> 本部分聚焦三个根本性分歧，每个都有完整代码。

---

## 分歧一：循环为什么退出？GPT 的诊断是错的

GPT 说："需要增加自迭代机制：similarity< threshold → continue"。

这是在描述症状，不是根因。真正的问题是：

```text
当前系统有两个退出条件，但把它们合并成了一个：

1. "目标达成"   → similarity >= threshold
2. "真正卡住了" → 连续 N 次无改善

GPT 的方案区分了这两个，但在实现层面仍然用同一个
"无进展计数器"来触发退出。

致命问题在于：
改善0.001% 会重置计数器，
让系统在 0.82→ 0.82 → 0.821
这种"微颤"中永远不退出，
也永远不前进。
```

正确的信号不是"是否有改善"，而是**改善速率的 EMA 是否在收缩**：

```python
# scripts/ui_autopilot/orchestration/convergence.py

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum


class ConvergenceStatus(StrEnum):
    PROGRESSING = "progressing"
    DECELERATING = "decelerating"
    STAGNANT = "stagnant"
    OSCILLATING = "oscillating"
    CONVERGED = "converged"
    DIVERGING = "diverging"


@dataclass(slots=True)
class ConvergenceTracker:
    """
    用改善速率的 EMA 判断收敛状态，而不是简单计数。

    区分四种不同状态：
    - PROGRESSING：EMA 稳定为正，继续当前策略
    - DECELERATING：EMA 在缩小但仍为正，缩小步长换精确补丁
    - STAGNANT：EMA 接近零，触发根因重新诊断
    - OSCILLATING：分数在区间内震荡，触发方向锁定
    - CONVERGED：分数超过阈值且EMA 稳定
    - DIVERGING：分数持续下降，触发紧急回滚
    """

    target_threshold: floatema_alpha: float = 0.3
    stagnant_ema_threshold: float = 0.0005
    oscillation_window: int = 6
    history_max: int = 40

    _scores: deque[float] = field(default_factory=deque, repr=False)
    _ema: float = field(default=0.0, repr=False)
    _ema_initialized: bool = field(default=False, repr=False)

    def record(self, score: float) ->ConvergenceStatus:
        self._scores.append(score)

        if len(self._scores) > self.history_max:
            self._scores.popleft()

        if len(self._scores) < 2:
            return ConvergenceStatus.PROGRESSING

        delta = self._scores[-1] - self._scores[-2]

        if not self._ema_initialized:
            self._ema = delta
            self._ema_initialized = True
        else:
            self._ema = (
                self.ema_alpha * delta
                + (1 - self.ema_alpha) * self._ema
            )

        # 检查是否达到目标
        if score >= self.target_threshold:
            if abs(self._ema) < self.stagnant_ema_threshold:
                return ConvergenceStatus.CONVERGED

        # 检查发散
        if self._ema < -0.005:
            return ConvergenceStatus.DIVERGING

        # 检查震荡
        if len(self._scores) >= self.oscillation_window:
            window = list(self._scores)[-self.oscillation_window:]
            if self._is_oscillating(window):
                return ConvergenceStatus.OSCILLATING

        # 检查停滞
        if abs(self._ema) < self.stagnant_ema_threshold:
            return ConvergenceStatus.STAGNANT

        # 检查减速
        if 0 < self._ema < self.stagnant_ema_threshold * 4:
            return ConvergenceStatus.DECELERATING

        return ConvergenceStatus.PROGRESSING

    @staticmethod
    def _is_oscillating(window: list[float]) -> bool:
        """检测分数在上下交替，但净进展为零。"""
        if len(window) < 4:
            return False

        direction_changes = sum(
            1
            for i in range(1, len(window) - 1)
            if (window[i] - window[i - 1]) * (window[i + 1] - window[i]) < 0
        )

        net_progress = window[-1] - window[0]

        return direction_changes >= 3 and abs(net_progress) < 0.003

    @property
    def current_ema(self) -> float:
        return self._ema

    @property
    def latest_score(self) -> float | None:
        return self._scores[-1] if self._scores else None

    @property
    def best_score(self) -> float:
        return max(self._scores) if self._scores else 0.0
```

状态机的退出逻辑基于收敛状态，而不是计数器：

```python
# scripts/ui_autopilot/orchestration/loop_controller.py

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .convergence import ConvergenceStatus, ConvergenceTracker


@dataclass(slots=True)
class StrategyState:
    current: str = "normal"
    locked_direction: str | None = None
    locked_until: float = 0.0

    def lock(self, direction: str, duration_seconds: float) -> None:
        self.locked_direction = direction
        self.locked_until = time.monotonic() + duration_seconds
        self.current = "locked"

    def unlock(self) -> None:
        if time.monotonic() >= self.locked_until:
            self.locked_direction = None
            self.current = "normal"


@dataclass(slots=True)
class LoopController:
    """
    与 GPT 方案的关键区别：
    退出策略完全基于收敛状态机，而不是全局iteration count。
    不同收敛状态触发不同的下一步动作，而不是统一 exit。
    """

    target_threshold: float
    deadline_epoch: float
    reserve_seconds: float = 1800
    budget: dict[str, int] = field(default_factory=dict)

    _tracker: ConvergenceTracker = field(init=False)
    _strategy: StrategyState = field(default_factory=StrategyState)
    _consecutive_stagnant: int = field(default=0)
    _consecutive_diverging: int = field(default=0)
    _phase_attempts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._tracker = ConvergenceTracker(
            target_threshold=self.target_threshold,
        )

    def record_and_decide(
        self,
        score: float,
        phase: str,
        on_strategy_change: Callable[[str, str], None] | None = None,
    ) -> str:
        """
        返回下一步动作，永远不直接 exit。
        退出是调度器读到TERMINATE 后的决策，不是 loop_controller 的决策。
        """
        self._strategy.unlock()
        status = self._tracker.record(score)
        self._phase_attempts[phase] = self._phase_attempts.get(phase, 0) + 1

        remaining = self.deadline_epoch - time.monotonic()

        if remaining< self.reserve_seconds:
            return "ENTER_FINAL_AUDIT"

        if score >= self.target_threshold:
            return "CONVERGED_PROCEED_TO_GATE"

        if status == ConvergenceStatus.DIVERGING:
            self._consecutive_diverging += 1

            if self._consecutive_diverging >= 2:
                return "EMERGENCY_ROLLBACK_TO_BEST"

            return "ROLLBACK_LAST_PATCH"

        self._consecutive_diverging = 0

        if status == ConvergenceStatus.OSCILLATING:
            direction = f"{phase}_{score:.4f}"
            self._strategy.lock(direction, 21600)  # 锁定 6h，跳过该方向

            if on_strategy_change:
                on_strategy_change("oscillating", direction)

            return "LOCK_AND_TRY_DIFFERENT_APPROACH"

        if status == ConvergenceStatus.STAGNANT:
            self._consecutive_stagnant += 1

            thresholds = [1, 2, 3, 5, 8]

            for i, threshold in enumerate(thresholds):
                if self._consecutive_stagnant == threshold:
                    actions = [
                        "RETRY_WITH_MORE_MEASUREMENTS",
                        "ESCALATE_TO_ROOT_CAUSE_ANALYSIS",
                        "INVOKE_KIMI_VISUAL_DIAGNOSIS",
                        "DEMOTE_PHASE_AND_RETRY_PARENT","FREEZE_TARGET_CONTINUE_OTHERS",
                    ]
                    return actions[i]

            return "TERMINATE_BLOCKER_REPORT"

        self._consecutive_stagnant = 0

        if status == ConvergenceStatus.DECELERATING:
            return "SWITCH_TO_PRECISION_PATCH_MODE"

        return "CONTINUE_NORMAL"

    @property
    def best_score(self) -> float:
        return self._tracker.best_score
```

---

## 分歧二：GPT 的三阶段是对的，但阶段边界定错了

GPT 定义：Shell → Region → Element → Interaction

这个层次正确，但**每层的完成条件和进入条件定错了**。

GPT 说："Shell 通过后进入 Region"。

问题在于：Shell 通过的标准是几何分≥ 0.995，但 Shell 的几何取决于 Token 是否正确。如果 Token 错了，Shell 几何不可能稳定通过。所以正确顺序不是线性的：

```text
GPT 的线性流：
Token → Shell → Region → Element

实际应该是菱形依赖：
Token (冻结) ────────────────────┐
     │                           │
     ↓                           ↓
Shell (几何骨架)              Element (排版/颜色)
     │                           │
     ↓                           │
Region (内容对齐) ──────────────→ Interaction
```

Shell阶段**只处理几何骨架**，不允许修颜色和排版（即使颜色错了）。颜色和排版在 Element 阶段统一处理。这样避免两个阶段互相争夺同一个 Token 值。

具体阶段进入条件：

```python
# scripts/ui_autopilot/orchestration/phase_gate.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PhaseGate:
    """
    阶段门禁规则。

    与 GPT 方案的区别：
    - 阶段门禁是双向的：进入条件 + 退出条件
    - 退出条件允许"带伤"进入下一阶段（partial pass）
    - 绝不允许带伤进入 INTERACTION 阶段
    """ENTRY_CONDITIONS: dict[str, dict[str, Any]] = {
        "SHELL": {
            "requires": ["token_baseline_frozen"],
            "blocked_by": [],"allows_partial": False,
        },
        "REGION": {
            "requires": [
                "shell_geometry_score >= 0.990",
                "no_missing_shell_components",
            ],
            "blocked_by": ["shell_runtime_errors > 0"],
            "allows_partial": True,
            # Region 阶段可以允许个别非关键区域 pending
            "partial_conditions": [
                "critical_regions_complete",
                "shell_geometry_score >= 0.995",
            ],
        },
        "ELEMENT": {
            "requires": [
                "region_geometry_score >= 0.985",
                "no_missing_required_regions",
            ],
            "blocked_by": [],
            "allows_partial": True,
            "partial_conditions": [
                "critical_region_geometry_score >= 0.990",],
        },
        "INTERACTION": {
            # 交互阶段是严格门禁，不允许带伤进入
            "requires": [
                "element_visual_score >= 0.97",
                "token_compliance >= 1.0",
                "no_runtime_errors",
                "no_console_errors",
            ],
            "blocked_by": [
                "open_geometry_regressions",
                "missing_critical_elements",
            ],
            "allows_partial": False,
        },
    }

    EXIT_CONDITIONS: dict[str, dict[str, Any]] = {
        "SHELL": {
            "must_pass": [
                "layout_geometry_score >= 0.995",
                "scroll_container_structure_correct",
                "z_index_layer_correct",
                "fixed_sticky_elements_positioned",
            ],
            "can_defer": [
                # 这些交给 Element阶段处理
                "typography_correct",
                "color_correct",
                "shadow_correct",
            ],
        },
        "REGION": {
            "must_pass": [
                "all_required_regions_present",
                "region_geometry_score >= 0.985",
                "no_overflow_clipping",
            ],
            "can_defer": [
                "element_level_typography",
                "micro_spacing",],
        },
        "ELEMENT": {
            "must_pass": [
                "typography_score >= 0.99",
                "color_score >= 0.99",
                "decoration_score >= 0.99",],
            "can_defer": [
                "hover_states",
                "focus_rings",
            ],
        },
        "INTERACTION": {
            "must_pass": [
                "all_required_interaction_states_covered",
                "all_overlay_assertions_pass",
                "keyboard_navigation_correct",
            ],
            "can_defer": [],# 交互阶段没有可以推迟的项
        },
    }
```

每个阶段的修复任务生成器基于阶段定义，确保 Shell阶段的Worker 物理上无法写入颜色 Token：

```python
# scripts/ui_autopilot/orchestration/task_generator.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


PHASE_ALLOWED_FILE_PATTERNS: dict[str, list[str]] = {
    "SHELL": [
        "src/layouts/**/*.module.scss",
        "src/layouts/**/*.tsx",
        "src/app/App.module.scss",
    ],
    "REGION": [
        "src/features/{feature}/**/*.module.scss",
        "src/features/{feature}/**/*.tsx",
        "src/components/layout/**",],
    "ELEMENT": [
        "src/features/{feature}/**",
        "src/components/{component}/**",
        # 允许只写overrides，不允许重写 generated
        "src/styles/tokens/overrides.css",
    ],
    "INTERACTION": [
        "src/features/{feature}/**",
        "src/components/{component}/**",
        "tests/e2e/**",
    ],
}

PHASE_PROHIBITED_ALWAYS: list[str] = [
    "src/styles/tokens/generated/**",
    "scripts/carroros-gates/**",
    ".claude/**",
    "*.lock.json",
]


@dataclass(frozen=True, slots=True)
class BoundedTask:
    id: str
    phase: Literal["SHELL", "REGION", "ELEMENT", "INTERACTION"]
    target_id: str
    root_cause: str
    measurements: dict
    allowed_files: list[str]
    prohibited_patterns: list[str]
    acceptance: dict
    evidence: dict
    retry_count: int = 0
    parent_task_id: str | None = None

    def to_worker_prompt_context(self) -> dict:
        """
        生成发给 Worker 模型的上下文。
        注意：绝对不包含阈值和门禁路径，
        防止模型通过修改门禁来"通过"检查。
        """
        return {
            "task_id": self.id,
            "phase": self.phase,
            "target": self.target_id,
            "diagnosis": self.root_cause,
            "measurements": self.measurements,
            "allowed_files": self.allowed_files,
            "evidence": self.evidence,
            # 明确告知不得修改的内容
            "constraints": {
                "prohibited_patterns": self.prohibited_patterns,
                "output_required_fields": [
                    "changed_files",
                    "diagnosis",
                    "patch_reasoning",
                    "risks",
                ],},
        }
```

---

## 分歧三：GPT 的 Token 提取管线是可行的，但初始化顺序是错的

GPT 提出：采集computed styles → 归一化 → 聚类 → 生成 Token。

这个流程是对的，但**时机错了**。GPT 把Token 提取放在"第3 部分"，作为独立管线。实际项目里，Token 错误是Shell 几何偏差的隐藏根因之一。

我的观点：**Token 系统的第一版本必须在第一个Playwright 测量之前就冻结**，因为：

```text
Playwright 测量 sidebar-width 是 256px
→ 实现里写了 256px
→ Token 提取后发现原型变量是 --sidebar-width: 240px（有缩放）
→ 实现里的 256px 从哪来的？

如果 Token 先冻结，Worker 模型从一开始就只能用 var(--sidebar-width)。
即使当时值是错的，后来修正 Token 值，所有引用自动生效。
```

因此，Token 系统分两个子阶段：

```text
T0（点火前）：快速 Token Bootstrap→ 只提取最关键的 30-50 个 Token
  → 目标不是正确，而是"有变量可用"
  → 与 signoff 一起完成，是 Phase 0 的一部分

T1（Loop 中）：Token 精化
  → 每次视觉评分后自动识别裸值违规
  → 按影响面排序逐步精化
  → Token 精化本身是一种高价值补丁
```

T0 Bootstrap脚本：

```typescript
// scripts/ui-autopilot/tokens/bootstrap.ts

import { chromium } from '@playwright/test';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';

/**
 * Token Bootstrap：点火前运行，目标是在 5 分钟内生成可用的初始 Token。
 *
 * 与 GPT 完整Token 管线的区别：
 * -不做聚类，只做频率排名
 * - 只提取 top-50 最高频值
 * - 立刻生成可用的 CSS Variables文件
 * - 允许后续精化覆盖
 */

interface RawToken {
  property: string;
  value: string;
  count: number;
  weight: number;
}

const BOOTSTRAP_PROPERTIES = new Set([
  'color',
  'background-color',
  'border-color',
  'font-size',
  'font-weight',
  'line-height',
  'border-radius',
  'gap',
  'padding',
  'padding-top',
  'padding-right',
  'padding-bottom',
  'padding-left',
  'width',
  'height',
  'box-shadow',
]);

const CATEGORY_MAP: Record<string, string> = {
  'color': 'color',
  'background-color': 'color',
  'border-color': 'color',
  'font-size': 'font-size',
  'font-weight': 'font-weight',
  'line-height': 'line-height',
  'border-radius': 'radius',
  'gap': 'spacing',
  'padding': 'spacing',
  'padding-top': 'spacing',
  'padding-right': 'spacing',
  'padding-bottom': 'spacing',
  'padding-left': 'spacing',
  'box-shadow': 'shadow',
};

export async function bootstrapTokens(
  prototypeUrl: string,
  outputDir: string,
  auth?: { storageState?: string },
): Promise<void> {
  const browser = await chromium.launch({ headless: true });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,locale: 'zh-CN',
    reducedMotion: 'reduce',
    storageState: auth?.storageState,
  });

  const page = await context.newPage();
  await page.goto(prototypeUrl, { waitUntil: 'domcontentloaded' });

  // 等待字体加载
  await page.evaluate(() => document.fonts.ready);

  // 提取可见元素的 computed styles
  const observations = await page.evaluate(
    ({ properties }) => {
      const results: Array<{
        property: string;
        value: string;
        area: number;
        tagName: string;
        role: string | null;
      }> = [];

      const elements = document.querySelectorAll<HTMLElement>('body *');

      for (const element of elements) {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);

        if (
          rect.width < 2||
          rect.height < 2 ||
          style.display === 'none' ||
          style.visibility === 'hidden'
        ) {
          continue;
        }

        const area = rect.width * rect.height;

        for (const property of properties) {
          const value = style.getPropertyValue(property).trim();

          if (
            !value ||
            value === 'none' ||
            value === 'normal' ||
            value === 'auto' ||
            value === 'transparent' ||
            value === 'rgba(0, 0, 0, 0)'
          ) {
            continue;
          }

          results.push({
            property,
            value,
            area,
            tagName: element.tagName.toLowerCase(),
            role: element.getAttribute('role'),
          });
        }
      }

      return results;
    },
    { properties: [...BOOTSTRAP_PROPERTIES] },
  );

  // 优先读取原型的 CSS自定义变量（如果有）
  const customProperties = await page.evaluate(() => {
    const result: Record<string, string> = {};
    const root = getComputedStyle(document.documentElement);

    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          if (!(rule instanceof CSSStyleRule)) continue;

          for (const name of rule.style) {
            if (name.startsWith('--')) {
              const resolved = root.getPropertyValue(name).trim();
              if (resolved) result[name] = resolved;
            }
          }
        }
      } catch {
        // 跨域stylesheet跳过
      }
    }

    return result;
  });

  await browser.close();

  // 按property + value 聚合，用面积加权
  const freq = new Map<string, RawToken>();

  for (const obs of observations) {
    const key = `${obs.property}::${obs.value}`;
    const existing = freq.get(key);

    if (existing) {
      existing.count +=1;
      existing.weight += obs.area;
    } else {
      freq.set(key, {
        property: obs.property,
        value: obs.value,
        count: 1,
        weight: obs.area,
      });
    }
  }

  // 分类并取top-N
  从中断处继续，完成 Token Bootstrap，然后进入第1 部分剩余内容。

```typescript// 分类并取 top-N，按面积加权频率排序
  const byCategory = new Map<string, RawToken[]>();

  for (const token of freq.values()) {
    const category = CATEGORY_MAP[token.property] ??'other';
    const list = byCategory.get(category) ?? [];
    list.push(token);
    byCategory.set(category, list);
  }

  // 每个分类取前 N 个
  const TOP_N: Record<string, number> = {
    color: 20,
    'font-size': 8,
    'font-weight': 6,
    'line-height': 6,
    radius: 6,
    spacing: 12,
    shadow: 4,
    other: 4,
  };

  const selected: RawToken[] = [];

  for (const [category, tokens] of byCategory) {
    const sorted = tokens.sort((a, b) => b.weight - a.weight);
    const limit = TOP_N[category] ?? 4;
    selected.push(...sorted.slice(0, limit));
  }

  // 生成 CSS Variables草稿
  const cssLines: string[] = [
    '/* AUTO-GENERATED: Token Bootstrap Draft */',
    '/* Source: prototype computed styles*/',
    '/* Run T1 refinement to improve accuracy  */',
    ':root {',
  ];

  // 如果原型自身有 CSS 变量，优先输出
  if (Object.keys(customProperties).length > 0) {
    cssLines.push('  /* === Prototype Native Variables === */');
    for (const [name, value] of Object.entries(customProperties)) {
      cssLines.push(`  ${name}: ${value};`);
    }cssLines.push('');
  }

  // 按分类生成命名变量
  const categoryCounters = new Map<string, number>();

  cssLines.push('  /* === Bootstrap Extracted Values === */');

  for (const token of selected) {
    const category = CATEGORY_MAP[token.property] ?? 'other';
    const count = (categoryCounters.get(category) ?? 0) + 1;
    categoryCounters.set(category, count);

    const varName = `--ui-bootstrap-${category}-${count}`;
    cssLines.push(`  ${varName}: ${token.value}; /* freq:${token.count} */`);
  }

  cssLines.push('}', '');

  // 同时生成 JSON 供后续 T1 精化读取
  const jsonOutput = {
    generatedAt: new Date().toISOString(),
    prototypeUrl,
    nativeVariables: customProperties,
    extracted: selected.map(t => ({
      category: CATEGORY_MAP[t.property] ?? 'other',
      property: t.property,
      value: t.value,
      frequency: t.count,
      areaWeight: t.weight,
    })),
  };

  await fs.mkdir(outputDir, { recursive: true });

  await fs.writeFile(
    path.join(outputDir, 'bootstrap-tokens.css'),
    cssLines.join('\n'),
    'utf-8',
  );

  await fs.writeFile(
    path.join(outputDir, 'bootstrap-tokens.json'),
    JSON.stringify(jsonOutput, null, 2),
    'utf-8',
  );

  console.log(
    `Bootstrap complete: ${selected.length} tokens, `+`${Object.keys(customProperties).length} native variables`,
  );
}
```

---

## 分歧三（续）：T1 Token精化如何嵌入修复循环

Bootstrap 生成了草稿，T1 精化在每次 Region/Element阶段完成后自动运行，并比较新旧 Token 的视觉影响：

```python
# scripts/ui_autopilot/tokens/refine.py

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenProposal:
    """
    T1 精化产生的单个 Token 修改提案。
    提案不直接生效，必须通过视觉验证后才能写入 generated/。
    """
    token_name: str
    current_value: str
    proposed_value: str
    confidence: float
    evidence_state_ids: list[str]
    affected_targets: list[str]
    source: str  # 'computed_style' | 'prototype_variable' | 'visual_model'


class TokenRefiner:
    """
    与 GPT 完整Token 管线的关键区别：
    精化是增量的，每次只处理当前阶段暴露出的错误 Token，
    而不是每次都跑全量重新聚类。
    """

    def __init__(
        self,
        bootstrap_json: Path,
        generated_css: Path,
        measurements_dir: Path,
    ) -> None:
        self.bootstrap = json.loads(bootstrap_json.read_text())
        self.generated_css = generated_css
        self.measurements_dir = measurements_dirdef find_violating_targets(
        self,
        score_report: dict[str, Any],
        threshold: float = 0.985,
    ) -> list[str]:
        """找出得分低于阈值且根因与 Token 相关的目标。"""
        return [
            target_id
            for target_id, scores in score_report.get('targets', {}).items()
            if scores.get('composite', 1.0) < threshold
            and scores.get('root_cause_category') in {
                'color_token',
                'typography_token',
                'spacing_token',
                'component_token',
            }
        ]

    def propose_refinements(
        self,
        violating_targets: list[str],
        prototype_measurements: dict[str, Any],
        implementation_measurements: dict[str, Any],
    ) -> list[TokenProposal]:
        """
        对每个违规目标，比较原型和实现的 computed style，
        生成 Token 修改提案。
        """
        proposals: list[TokenProposal] = []

        for target_id in violating_targets:
            proto = prototype_measurements.get(target_id, {})
            impl = implementation_measurements.get(target_id, {})

            if not proto or not impl:
                continue

            # 逐属性比较
            for prop, proto_value in proto.get('styles', {}).items():
                impl_value = impl.get('styles', {}).get(prop)

                if impl_value is None or proto_value == impl_value:
                    continue

                # 找当前实现里用的是哪个 Token 变量
                token_name = self._find_token_for_property(
                    prop, impl_value,
                )

                if token_name is None:
                    #裸值，先登记为违规，不生成提案
                    continue

                proposals.append(TokenProposal(
                    token_name=token_name,
                    current_value=impl_value,
                    proposed_value=proto_value,
                    confidence=0.85,
                    evidence_state_ids=[target_id],
                    affected_targets=[target_id],
                    source='computed_style',
                ))

        # 合并同一 Token 的多个提案
        return self._merge_proposals(proposals)

    def _find_token_for_property(
        self,
        css_property: str,
        value: str,
    ) -> str | None:
        """从 generated CSS 中找出 value 对应的变量名。"""
        css_text = self.generated_css.read_text()

        for line in css_text.splitlines():
            if ':' not in line:
                continue
            name, _, declared = line.partition(':')
            name = name.strip()
            declared = declared.strip().rstrip(';').strip()

            if declared == value and name.startswith('--ui-'):
                return name

        return None

    def _merge_proposals(
        self,
        proposals: list[TokenProposal],
    ) -> list[TokenProposal]:
        """同一 Token 被多个目标指向同一新值时合并，提升置信度。"""
        merged: dict[str, TokenProposal] = {}

        for proposal in proposals:
            key = f"{proposal.token_name}::{proposal.proposed_value}"
            existing = merged.get(key)

            if existing is None:
                merged[key] = proposal
            else:
                # 合并证据并提升置信度
                new_states = list(set(
                    existing.evidence_state_ids
                    + proposal.evidence_state_ids
                ))
                new_targets = list(set(
                    existing.affected_targets
                    + proposal.affected_targets
                ))
                # 多目标指向同一值，置信度提升
                new_confidence = min(
                    0.99,
                    existing.confidence + 0.05* len(new_targets),
                )
                merged[key] = TokenProposal(
                    token_name=existing.token_name,
                    current_value=existing.current_value,
                    proposed_value=existing.proposed_value,
                    confidence=new_confidence,
                    evidence_state_ids=new_states,
                    affected_targets=new_targets,
                    source=existing.source,
                )

        return sorted(
            merged.values(),
            key=lambda p: (p.confidence, len(p.affected_targets)),reverse=True,
        )
```

---

## 分歧四：我与 GPT 在"Kimi K3使用时机"上的根本分歧

GPT 说："低置信度 Token 语义判断时用 Kimi K3"。

这样用法成本控制困难且不精确。Kimi K3 的真正价值窗口是：

```text
GPT 建议的Kimi 使用时机：
→ Token 语义模糊时（很宽，会频繁触发）

我的建议：
→ 仅在人类凭文字无法解释差异时触发
→ 具体条件：
   1. 视觉得分 < 0.96
   2. root_cause = 'unknown' 或 'stacking_context'
   3. 连续 2 次补丁无改善
   4. 非几何差异（几何差异可以靠测量精确定位）
```

Kimi 的调用协议：

```python
# scripts/ui_autopilot/diagnosis/kimi_visual.py

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx


@dataclass(frozen=True, slots=True)
class KimiVisualRequest:
    """
    每次调用 Kimi 的输入必须高度精确。
    不允许把整页截图发给 Kimi，只发crop + diff + 定量测量。
    目的：降低成本，提高返回质量。
    """
    task_id: str
    target_id: str
    question: str  # 必须是可回答的具体问题，不能是开放式
    reference_crop: Path
    actual_crop: Path
    diff_heatmap: Path
    measurements: dict
    attempt_history: list[dict]  # 前几次失败的诊断摘要


@dataclass(frozen=True, slots=True)
class KimiVisualResponse:
    diagnosis: str
    suspected_property: str | None
    suspected_value: str | None
    confidence: float
    reasoning: str


# Kimi K3 调用预算跟踪
_kimi_call_log: list[dict] = []
KIMI_DAILY_BUDGET = 20# 每个 run-id 最多调用 20 次


def should_invoke_kimi(
    root_cause: str,
    attempt_count: int,
    score: float,
    is_geometry: bool,
) -> bool:
    """
    严格的触发条件，防止超出预算。
    """
    if len(_kimi_call_log) >= KIMI_DAILY_BUDGET:
        return False

    if is_geometry:
        # 几何问题靠测量解决，不需要视觉模型
        return False

    if score >= 0.96:
        # 高分区间不值得花费
        return False

    if attempt_count < 2:
        # 至少让确定性诊断先尝试
        return False

    if root_cause not in {'unknown', 'stacking_context', 'color_token'}:
        return False

    return True


async def invoke_kimi(
    request: KimiVisualRequest,
    api_key: str,
) -> KimiVisualResponse:
    _kimi_call_log.append({
        'task_id': request.task_id,
        'target_id': request.target_id,
        'timestamp': time.time(),
    })

    def encode_image(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode()

    # 构建精确的问题上下文
    # 注意：不允许发送整页截图
    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': (
                        f'UI 还原问题诊断。目标区域：{request.target_id}\n\n'
                        f'问题：{request.question}\n\n'
                        f'测量数据：{request.measurements}\n\n'
                        f'前几次诊断均失败，历史：{request.attempt_history}\n\n'
                        '请直接指出视觉差异的具体 CSS 属性和可能的正确值，'
                        '用 JSON 格式回答：'
                        '{"suspected_property": "...", '
                        '"suspected_value": "...", '
                        '"diagnosis": "...", '
                        '"confidence": 0.0-1.0, '
                        '"reasoning": "..."}'
                    ),
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/png;base64,{encode_image(request.reference_crop)}',
                        'detail': 'high',
                    },
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/png;base64,{encode_image(request.actual_crop)}',
                        'detail': 'high',
                    },
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/png;base64,{encode_image(request.diff_heatmap)}',
                        'detail': 'low',
                    },
                },
            ],
        }
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            'https://api.moonshot.cn/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'moonshot-v1-8k-vision-preview',
                'messages': messages,
                'temperature': 0.1,
                'max_tokens': 512,
            },
        )
        response.raise_for_status()
        data = response.json()

    content = data['choices'][0]['message']['content']

    # 解析 JSON 响应
    import json
    import re

    json_match = re.search(r'\{.*\}', content, re.DOTALL)

    if not json_match:
        return KimiVisualResponse(
            diagnosis=content,
            suspected_property=None,
            suspected_value=None,
            confidence=0.3,
            reasoning='Failed to parse structured response',
        )

    parsed = json.loads(json_match.group())

    return KimiVisualResponse(
        diagnosis=parsed.get('diagnosis', ''),
        suspected_property=parsed.get('suspected_property'),
        suspected_value=parsed.get('suspected_value'),
        confidence=float(parsed.get('confidence', 0.5)),
        reasoning=parsed.get('reasoning', ''),
    )
```

---

## 分歧五：测量层必须先于截图层

GPT 和我都提到了测量，但 GPT 把它当成辅助信息。我的观点是：

> **测量是主要诊断源，截图是验证工具。顺序反了，所有问题都要靠截图猜。**

每次修复循环必须先运行精确测量，再决定是否需要截图诊断：

```typescript
// scripts/ui-autopilot/visual/measure.ts

import type { Page } from '@playwright/test';

export interface RegionMeasurement {
  targetId: string;
  selector: string;
  found: boolean;
  box: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  styles: Record<string, string>;
  children: ChildMeasurement[];
  scrollState: {
    scrollTop: number;
    scrollHeight: number;
    clientHeight: number;
    hasVerticalScroll: boolean;
    hasHorizontalScroll: boolean;
  };
  overlays: OverlayMeasurement[];
  errors: string[];
}

export interface ChildMeasurement {
  role: string | null;
  name: string | null;
  tagName: string;
  box: { x: number; y: number; width: number; height: number };
  styles: Record<string, string>;
}

export interface OverlayMeasurement {
  role: string | null;
  zIndex: number;
  position: string;
  box: { x: number; y: number; width: number; height: number };
  visible: boolean;
}

const MEASUREMENT_PROPERTIES = [
  'display',
  'position',
  'flex-direction',
  'flex-wrap',
  'justify-content',
  'align-items',
  'grid-template-columns',
  'grid-template-rows',
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
  'overflow-x',
  'overflow-y',
  'color',
  'background-color',
  'font-size',
  'font-weight',
  'line-height',
  'letter-spacing',
  'font-family',
  'border-top-left-radius',
  'border-top-right-radius',
  'border-bottom-right-radius',
  'border-bottom-left-radius',
  'box-shadow',
  'border-top-width',
  'border-top-color',
  'border-top-style',
  'opacity',
  'z-index',
  'transform',
] as const;

/**
 * 对单个目标区域进行完整测量。
 *
 * 与 GPT 方案的区别：
 * 1. 同时测量原型和实现（调用两次），返回可直接比较的结构
 * 2. 包含滚动状态，覆盖 overflow 类根因
 * 3. 子元素前20 个也一并测量，覆盖 flex/grid 对齐类根因
 * 4. 测量结果写入 evidence，不只用于当前任务
 */
export async function measureRegion(
  page: Page,
  selector: string,
  targetId: string,
): Promise<RegionMeasurement> {
  return page.evaluate(
    ({ selector, targetId, properties }) => {
      const element = document.querySelector<HTMLElement>(selector);

      if (!element) {
        return {
          targetId,
          selector,
          found: false,
          box: null,
          styles: {},
          children: [],
          scrollState: {
            scrollTop: 0,
            scrollHeight: 0,
            clientHeight: 0,
            hasVerticalScroll: false,
            hasHorizontalScroll: false,
          },
          overlays: [],
          errors: [`Selector not found: ${selector}`],
        };
      }

      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);

      const styles = Object.fromEntries(
        properties.map(p => [p, style.getPropertyValue(p).trim()]),
      );

      // 子元素测量
      const children: ChildMeasurement[] = [];
      const childElements = [...element.children].slice(0, 20);

      for (const child of childElements) {
        const childRect = (child as HTMLElement).getBoundingClientRect();
        const childStyle = getComputedStyle(child as HTMLElement);

        children.push({
          role: child.getAttribute('role'),
          name: child.getAttribute('aria-label')
            ?? (child as HTMLElement).innerText?.trim().slice(0, 60)
            ?? null,
          tagName: child.tagName.toLowerCase(),
          box: {
            x: childRect.x,
            y: childRect.y,
            width: childRect.width,
            height: childRect.height,
          },
          styles: Object.fromEntries(
            ['display', 'flex', 'grid-column', 'margin', 'padding'].map(p => [
              p,
              childStyle.getPropertyValue(p).trim(),
            ]),
          ),
        });
      }

      // 滚动状态
      const scrollState = {
        scrollTop: element.scrollTop,
        scrollHeight: element.scrollHeight,
        clientHeight: element.clientHeight,
        hasVerticalScroll: element.scrollHeight > element.clientHeight + 2,
        hasHorizontalScroll: element.scrollWidth > element.clientWidth + 2,
      };

      // 浮层检测（z-index > 100且 position fixed/absolute）
      const overlays: OverlayMeasurement[] = [];

      for (const candidate of document.querySelectorAll<HTMLElement>('*')) {
        const cs = getComputedStyle(candidate);
        const zi = Number.parseInt(cs.zIndex, 10);

        if (
          Number.isFinite(zi) &&
          zi >= 100 &&
          ['fixed', 'absolute'].includes(cs.position)
        ) {
          const or = candidate.getBoundingClientRect();

          if (or.width > 2 && or.height > 2) {
            overlays.push({
              role: candidate.getAttribute('role'),
              zIndex: zi,
              position: cs.position,
              box: {
                x: or.x,
                y: or.y,
                width: or.width,
                height: or.height,
              },
              visible: cs.display !== 'none' && cs.visibility !== 'hidden',
            });
          }
        }
      }

      return {
        targetId,
        selector,
        found: true,
        box: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
        styles,
        children,
        scrollState,
        overlays,
        errors: [],
      };
    },
    { selector, targetId, properties: [...MEASUREMENT_PROPERTIES] },
  );
}

/**
 * 同时测量原型和实现，生成可比较的差异报告。
 * 这是 diagnose_root_cause 的主要输入。
 */
export async function compareMeasurements(
  prototypeMeasurement: RegionMeasurement,
  implementationMeasurement: RegionMeasurement,
): Promise<MeasurementDiff> {
  const diff: Record<string, { prototype: string; implementation: string }> = {};

  if (
    !prototypeMeasurement.found ||
    !implementationMeasurement.found
  ) {
    return {
      targetId: prototypeMeasurement.targetId,
      prototypeFound: prototypeMeasurement.found,
      implementationFound: implementationMeasurement.found,
      styleDiffs: diff,
      geometryDiff: null,
      childCountDiff: null,
    };
  }

  // 样式差异
  for (const [prop, protoValue] of Object.entries(
    prototypeMeasurement.styles,
  )) {
    const implValue = implementationMeasurement.styles[prop];
    if (implValue !== protoValue) {
      diff[prop] = { prototype: protoValue, implementation: implValue ?? '' };
    }
  }

  // 几何差异
  const pb = prototypeMeasurement.box!;
  const ib = implementationMeasurement.box!;

  const geometryDiff = {
    xDelta: ib.x - pb.x,
    yDelta: ib.y - pb.y,
    widthDelta: ib.width - pb.width,
    heightDelta: ib.height - pb.height,
    significantDifference: (
      Math.abs(ib.x - pb.x) > 2 ||
      Math.abs(ib.y - pb.y) > 2 ||
      Math.abs(ib.width - pb.width) > 2 ||
      Math.abs(ib.height - pb.height) > 2
    ),
  };

  return {
    targetId: prototypeMeasurement.targetId,
    prototypeFound: true,
    implementationFound: true,
    styleDiffs: diff,
    geometryDiff,
    childCountDiff:
      prototypeMeasurement.children.length !==
      implementationMeasurement.children.length
        ? {
            prototype: prototypeMeasurement.children.length,
            implementation: implementationMeasurement.children.length,
          }
        : null,
  };
}

export interface MeasurementDiff {
  targetId: string;
  prototypeFound: boolean;
  implementationFound: boolean;
  styleDiffs: Record<string, { prototype: string; implementation: string }>;
  geometryDiff: {
    xDelta: number;
    yDelta: number;
    widthDelta: number;
    heightDelta: number;
    significantDifference: boolean;
  } | null;
  childCountDiff: {
    prototype: number;
    implementation: number;
  } | null;
}
```

---

## 第1部分总结：我与 GPT 方案的五个根本分歧

| 问题 | GPT 方案 | Opus 方案 |
|---|---|---|
| 循环退出 | 无进展计数器 | EMA 收敛状态机，区分停滞/震荡/发散 |
| 阶段边界 | Shell几何通过→进入Region |阶段进入条件双向+阶段内禁修项 |
| Token 时机 | 独立第3阶段 | T0 Bootstrap 先于第一次测量冻结 |
| Kimi 触发 | Token 语义模糊时 | 严格：非几何+连续失败+分数<0.96 |
| 诊断主源 | 截图为主，测量为辅 | 测量先行，截图验证 |

第2 部分将完成：**原型全状态采集的差异化方案（与 GPT 的BFS 相比，我采用优先级驱动的混合遍历）、基于 diff 的增量重采集、以及如何在 6 小时预算内完成完整状态图的首次建立。**

# Opus 视角：第2/5 部分——原型全状态采集的根本性重构

> **核心分歧**：GPT 提出 BFS + Page Graph 的静态遍历方案。我认为这个方案对"发现你不知道存在的状态"无能为力。原型里最难还原的状态（折叠侧边栏、深层浮层、滚动底部内容）恰恰是 BFS 最容易遗漏的。
>
> 本部分提出**优先级驱动的混合遍历 + 差分增量重采集**，解决现有方案对滚动、浮层、交互状态的系统性盲区。

---

## 一、BFS 遍历的三个根本盲区

GPT 的 Page Graph 基于 BFS：从入口 URL 出发，找链接，发现页面，记录状态。

```text
BFS 能发现：
→ href 导航到的新页面
→ 显式 route 切换

BFS 发现不了：
→ 同一页面的浮层状态（Modal、Drawer、Popover、Tooltip）
→ 内容在滚动后才出现的区域
→ 需要特定交互序列才能进入的状态（如：先折叠侧边栏，再进入某子菜单）
→ Ant Design 的 Tabs、Collapse、Select 内部状态
→ loading/empty/error 这类数据驱动状态
```

这三类盲区正好对应用户描述的问题：

```text
"悬浮显示菜单"        → 浮层状态，BFS 不遍历
"点击浮窗"            → 交互序列状态，BFS 不遍历
"侧边栏的收缩展开"    → 组件内部状态，BFS 不遍历
"滚动到底"            → 滚动内容，BFS 不遍历
```

---

## 二、替代方案：三层混合遍历

```text
Layer 1：路由遍历（静态分析 + 导航）
  → 发现所有 Route，不用 BFS 爬链接
  → 直接从代码的路由配置读

Layer 2：交互状态矩阵（基于 ARIA + 事件分析）
  → 对每个页面，识别可触发状态的交互点
  → 按交互序列穷举可达状态

Layer 3：滚动内容探测（动态滚动采集）
  → 对每个滚动容器，分段截图
  → 识别懒加载和虚拟滚动边界
```

### Layer 1：从路由配置直接构建页面列表

```typescript
// scripts/ui-autopilot/discovery/route-extractor.ts

import * as fs from 'node:fs/promises';
import * as path from 'node:path';

export interface RouteNode {
  path: string;
  componentFile: string;
  name: string | null;
  children: RouteNode[];
  requiresAuth: boolean;
  params: string[];  // 动态路由参数
}

/**
 * 从 React Router / Vue Router 配置静态提取路由树。
 * 
 * 比BFS 爬链接更可靠：
 * 1. 不遗漏没有入口链接的页面
 * 2. 发现动态路由参数
 * 3. 识别受保护路由（需要登录）
 * 4. 在原型运行前就可以执行
 */
export async function extractRoutes(
  srcDir: string,
): Promise<RouteNode[]> {
  // 查找路由配置文件
  const candidates = [
    'src/router/index.tsx',
    'src/router/index.ts',
    'src/routes/index.tsx',
    'src/App.tsx',
    'src/main.tsx',
  ];

  let routerFile: string | null = null;

  for (const candidate of candidates) {
    const full = path.join(srcDir, candidate);
    try {
      await fs.access(full);
      routerFile = full;
      break;
    } catch {
      // 继续查找
    }
  }

  if (!routerFile) {
    throw new Error('Cannot find router configuration file');
  }

  const source = await fs.readFile(routerFile, 'utf-8');

  return parseRouterConfig(source, routerFile);
}

function parseRouterConfig(source: string, filePath: string): RouteNode[] {
  const routes: RouteNode[] = [];

  // 匹配 React Router v6 风格：{ path: '/xxx', element: <Component /> }
  const routePattern =
    /\{\s*path:\s*['"`]([^'"`]+)['"`][^}]*element:\s*<(\w+)/g;

  let match: RegExpExecArray | null;

  while ((match = routePattern.exec(source)) !== null) {
    const [, routePath, componentName] = match;

    routes.push({
      path: routePath,
      componentFile: resolveComponentFile(componentName, filePath),
      name: componentName,
      children: [],
      requiresAuth: source.includes(`PrivateRoute`) || source.includes(`RequireAuth`),
      params: (routePath.match(/:(\w+)/g) ?? []).map(p => p.slice(1)),
    });
  }

  return routes;
}

function resolveComponentFile(componentName: string, routerFile: string): string {
  // 简化实现：实际需要 AST 解析 import 声明
  const dir = path.dirname(routerFile);
  return path.join(dir, '..', 'features', componentName, `${componentName}.tsx`);
}
```

### Layer 2：交互状态矩阵构建器

这是与 GPT 方案最大的差异。GPT 把交互状态当作"第四阶段"来处理，我认为交互状态必须在采集阶段就全部发现，否则后期根本不知道要还原什么：

```python
# scripts/ui_autopilot/discovery/interaction_matrix.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TriggerType(StrEnum):
    CLICK = "click"
    HOVER = "hover"
    FOCUS = "focus"
    KEYBOARD = "keyboard"
    SCROLL = "scroll"
    RESIZE = "resize"
    DATA = "data"  # 数据状态驱动（loading/empty/error）


@dataclass(slots=True)
class InteractionPoint:
    """
    页面上的一个可触发状态变化的交互点。
    """
    element_selector: str
    aria_role: str | None
    aria_label: str | None
    trigger_type: TriggerType
    expected_state_change: str
    sequence_index: int  # 在交互序列中的位置
    depends_on: list[str]  # 前置条件状态 ID
    produces_states: list[str]  # 触发后产生的状态 ID
    reversible: bool = True
    revert_action: str | None = None


@dataclass(slots=True)
class PageStateGraph:
    """
    单个页面的完整状态图。
    
    与 GPT Page Graph 的区别：
    GPT 的 Page Graph 是页面间的路由图。
    这里是单个页面内的交互状态图。
    """
    page_id: str
    route: str
    base_state_id: str
    states: dict[str, PageState] = field(default_factory=dict)
    transitions: list[StateTransition] = field(default_factory=list)
    interaction_points: list[InteractionPoint] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PageState:
    state_id: str
    description: str
    is_base: bool
    requires_sequence: list[str]  # 进入此状态的交互序列
    viewport_ids: list[str]
    screenshot_required: bool
    assertion_ids: list[str]


@dataclass(frozen=True, slots=True)
class StateTransition:
    from_state: str
    to_state: str
    trigger: str
    selector: str | None
    keyboard_key: str | None


class InteractionMatrixBuilder:
    """
    自动发现页面上所有可触发状态变化的交互点，
    构建完整的状态转换矩阵。
    """

    # 已知会产生视觉状态变化的 ARIA role
    STATE_PRODUCING_ROLES = {
        'button': ['click'],
        'menuitem': ['click'],
        'menuitemcheckbox': ['click'],
        'tab': ['click'],
        'treeitem': ['click'],
        'checkbox': ['click'],
        'radio': ['click'],
        'switch': ['click'],
        'combobox': ['click'],
        'listbox': ['click'],
        'option': ['click'],
        'slider': ['click'],
        'link': ['click'],
        'disclosure': ['click'],
    }

    # 已知 Ant Design 组件的状态触发模式
    ANT_DESIGN_TRIGGERS = {
        '.ant-menu-submenu-title': {
            'trigger': TriggerType.CLICK,
            'state': 'submenu_expanded',
        },
        '.ant-collapse-header': {
            'trigger': TriggerType.CLICK,
            'state': 'panel_expanded',
        },
        '.ant-tabs-tab': {
            'trigger': TriggerType.CLICK,
            'state': 'tab_active',
        },
        '.ant-select-selector': {
            'trigger': TriggerType.CLICK,
            'state': 'dropdown_open',
        },
        '.ant-dropdown-trigger': {
            'trigger': TriggerType.CLICK,
            'state': 'dropdown_open',
        },
        '.ant-modal-confirm-btns .ant-btn': {
            'trigger': TriggerType.CLICK,
            'state': 'modal_closed',
        },
        '[data-sidebar-toggle]': {
            'trigger': TriggerType.CLICK,
            'state': 'sidebar_collapsed_or_expanded',
        },
    }

    async def discover(
        self,
        page_html: str,
        page_id: str,
        route: str,
    ) -> PageStateGraph:
        """
        静态分析 HTML，发现所有潜在的交互点。
        不需要运行浏览器，速度快，用于构建初始状态矩阵。
        动态验证在后续步骤中运行。
        """
        from html.parser import HTMLParser

        graph = PageStateGraph(
            page_id=page_id,
            route=route,
            base_state_id=f"{page_id}__base",
        )

        # 基础状态
        graph.states[graph.base_state_id] = PageState(
            state_id=graph.base_state_id,
            description="页面默认加载状态",
            is_base=True,
            requires_sequence=[],
            viewport_ids=['desktop-1440', 'desktop-1280', 'tablet-768'],
            screenshot_required=True,
            assertion_ids=[],
        )

        interaction_points = self._extract_interaction_points(page_html)

        for point in interaction_points:
            graph.interaction_points.append(point)

            state_id = f"{page_id}__{point.expected_state_change}"

            if state_id not in graph.states:
                graph.states[state_id] = PageState(
                    state_id=state_id,
                    description=point.expected_state_change,
                    is_base=False,
                    requires_sequence=[point.element_selector],
                    viewport_ids=['desktop-1440'],
                    screenshot_required=True,
                    assertion_ids=[],
                )

            graph.transitions.append(StateTransition(
                from_state=graph.base_state_id,
                to_state=state_id,
                trigger=point.trigger_type.value,
                selector=point.element_selector,
                keyboard_key=None,
            ))

        return graph

    def _extract_interaction_points(
        self,
        html: str,
    ) -> list[InteractionPoint]:
        """
        从 HTML 字符串提取交互点。
        优先使用 data-ui-region 和ARIA 属性。
        """
        points: list[InteractionPoint] = []

        # 1. ARIA role匹配
        import re

        role_pattern = re.compile(
            r'<[^>]+role=["\'](\w+)["\'][^>]*'r'(?:aria-label=["\']([^"\']*)["\'])?[^>]*/?>',
            re.IGNORECASE,
        )

        for match in role_pattern.finditer(html):
            role, label = match.group(1), match.group(2)

            if role not in self.STATE_PRODUCING_ROLES:
                continue

            for trigger in self.STATE_PRODUCING_ROLES[role]:
                state_name = f"{role}_{trigger}_active"

                # 构建尽量稳定的 selector
                full_tag = match.group(0)
                selector = self._build_selector_from_tag(full_tag, role, label)

                points.append(InteractionPoint(
                    element_selector=selector,
                    aria_role=role,
                    aria_label=label,
                    trigger_type=TriggerType(trigger),
                    expected_state_change=state_name,
                    sequence_index=len(points),
                    depends_on=[],
                    produces_states=[state_name],
                    reversible=True,
                    revert_action=None,
                ))

        # 2. Ant Design 组件模式匹配
        for css_selector, config in self.ANT_DESIGN_TRIGGERS.items():
            # 简化：用 class 名匹配
            class_name = css_selector.lstrip('.')
            if class_name in html:
                points.append(InteractionPoint(
                    element_selector=css_selector,
                    aria_role=None,
                    aria_label=None,
                    trigger_type=config['trigger'],
                    expected_state_change=config['state'],
                    sequence_index=len(points),
                    depends_on=[],
                    produces_states=[config['state']],
                    reversible=True,
                    revert_action=None,
                ))

        return points

    @staticmethod
    def _build_selector_from_tag(
        tag_html: str,
        role: str,
        label: str | None,
    ) -> str:
        """
        优先使用 data-testid > aria-label > role 构建稳定 selector。
        """
        import re

        testid_match = re.search(r'data-testid=["\']([^"\']+)["\']', tag_html)
        if testid_match:
            return f'[data-testid="{testid_match.group(1)}"]'

        if label:
            return f'[role="{role}"][aria-label="{label}"]'

        return f'[role="{role}"]'
```

---

## 三、动态状态验证器：让Playwright 实际走一遍状态矩阵

静态分析只能发现"可能存在的状态"。动态验证才能确认状态真实存在并截图：

```typescript
// scripts/ui-autopilot/discovery/state-validator.ts

import type { Page } from '@playwright/test';
import { chromium } from '@playwright/test';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';

export interface StateCapture {
  stateId: string;
  pageId: string;
  viewportId: string;
  screenshotPath: string;
  domSnapshot: string;  // outerHTML of body
  measurements: Record<string, unknown>;
  capturedAt: string;
  success: boolean;
  failureReason?: string;
}

export interface CaptureConfig {
  baseUrl: string;
  route: string;
  viewports: Array<{ id: string; width: number; height: number }>;
  outputDir: string;
  authStorageState?: string;
  stabilizationMs?: number;
}

/**
 * 对单个页面状态执行完整采集。
 * 
 * 关键设计：
 * 1. 每次捕获都从 base_state 重新开始（避免状态污染）
 * 2. 交互序列中每步都有独立截图（定位问题位置）
 * 3.滚动到底后重新采集（避免遗漏懒加载内容）
 * 4. 失败不抛异常，记录 failureReason 继续下一个状态
 */
export class StateValidator {
  private config: CaptureConfig;

  constructor(config: CaptureConfig) {
    this.config = config;
  }

  async captureAllStates(
    stateSequences: StateSequence[],
  ): Promise<StateCapture[]> {
    const captures: StateCapture[] = [];

    for (const viewport of this.config.viewports) {
      const browser = await chromium.launch({ headless: true });

      try {
        for (const sequence of stateSequences) {
          const capture = await this.captureSequence(
            browser,
            sequence,
            viewport,
          );
          captures.push(capture);
        }
      } finally {
        await browser.close();
      }
    }

    return captures;
  }

  private async captureSequence(
    browser: import('@playwright/test').Browser,
    sequence: StateSequence,
    viewport: { id: string; width: number; height: number },
  ): Promise<StateCapture> {
    const stateDir = path.join(
      this.config.outputDir,
      sequence.stateId,
      viewport.id,
    );
    await fs.mkdir(stateDir, { recursive: true });

    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,locale: 'zh-CN',
      reducedMotion: 'reduce',storageState: this.config.authStorageState,
    });

    const page = await context.newPage();

    // 屏蔽外部网络请求，使用 fixture 数据
    await page.route('**/api/**', route => {
      const fixtureFile = this.resolveFixture(route.request().url());
      if (fixtureFile) {
        route.fulfill({ path: fixtureFile });
      } else {
        route.continue();
      }
    });

    try {
      await page.goto(
        `${this.config.baseUrl}${this.config.route}`,
        { waitUntil: 'domcontentloaded', timeout: 15000 },
      );

      await this.stabilize(page);

      // 执行交互序列
      for (const step of sequence.steps) {
        await this.executeStep(page, step, stateDir);
      }

      // 等待最终稳定
      await this.stabilize(page);

      const screenshotPath = path.join(stateDir, 'capture.png');

      await page.screenshot({
        path: screenshotPath,
        fullPage: false,  // 先截viewport，再单独滚动截全图animations: 'disabled',
        caret: 'hide',
      });

      // 额外：全页滚动截图
      await this.captureFullPageScroll(page, stateDir);

      const domSnapshot = await page.evaluate(
        () => document.body.outerHTML,
      );

      return {
        stateId: sequence.stateId,
        pageId: sequence.pageId,
        viewportId: viewport.id,
        screenshotPath,
        domSnapshot,
        measurements: {},
        capturedAt: new Date().toISOString(),
        success: true,
      };
    } catch (error) {
      return {
        stateId: sequence.stateId,
        pageId: sequence.pageId,
        viewportId: viewport.id,
        screenshotPath: '',
        domSnapshot: '',
        measurements: {},
        capturedAt: new Date().toISOString(),
        success: false,
        failureReason: error instanceof Error ? error.message : String(error),
      };
    } finally {
      await context.close();
    }
  }

  /**
   * 全页滚动采集：分段截图拼接。
   * 
   * 解决用户提到的"滚动到底"问题：
   * 标准 fullPage: true 对懒加载无效。
   * 必须实际滚动并等待内容加载。
   */
  private async captureFullPageScroll(
    page: Page,
    outputDir: string,
  ): Promise<void> {
    const scrollInfo = await page.evaluate(() => {
      const scrollEl =
        document.querySelector('[data-ui-region="content"]')??
        document.documentElement;

      return {
        scrollHeight: scrollEl.scrollHeight,
        clientHeight: scrollEl.clientHeight,
        selector: scrollEl === document.documentElement
          ? 'document'
          : '[data-ui-region="content"]',
      };
    });

    if (scrollInfo.scrollHeight <= scrollInfo.clientHeight * 1.2) {
      // 不需要滚动截图
      return;
    }

    const segments: string[] = [];
    const segmentHeight = scrollInfo.clientHeight;
    let scrollPos = 0;
    let segmentIndex = 0;

    while (scrollPos < scrollInfo.scrollHeight) {
      //滚动到目标位置
      await page.evaluate(
        ({ pos, selector }) => {
          const el = selector === 'document'
            ? document.documentElement
            : document.querySelector(selector);
          el?.scrollTo({ top: pos, behavior: 'instant' });
        },
        { pos: scrollPos, selector: scrollInfo.selector },
      );

      // 等待懒加载内容
      await page.waitForTimeout(300);
      await this.stabilize(page);

      const segmentPath = path.join(
        outputDir,
        `scroll-segment-${segmentIndex.toString().padStart(3, '0')}.png`,
      );

      await page.screenshot({
        path: segmentPath,
        animations: 'disabled',
        caret: 'hide',
      });

      segments.push(segmentPath);
      scrollPos += segmentHeight;
      segmentIndex++;

      // 防止无限滚动
      if (segmentIndex > 20) break;
    }

    // 回到顶部
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));

    // 写入滚动采集清单
    await fs.writeFile(
      path.join(outputDir, 'scroll-segments.json'),
      JSON.stringify({
        totalScrollHeight: scrollInfo.scrollHeight,
        viewportHeight: scrollInfo.clientHeight,
        segments,
      }, null, 2),
      'utf-8',
    );
  }

  private async executeStep(
    page: Page,
    step: InteractionStep,
    outputDir: string,
  ): Promise<void> {
    switch (step.type) {
      case 'click': {
        const element = page.locator(step.selector!);
        await element.waitFor({ state: 'visible', timeout: 5000 });
        await element.click();
        break;
      }

      case 'hover': {
        const element = page.locator(step.selector!);
        await element.waitFor({ state: 'visible', timeout: 5000 });
        await element.hover();
        break;
      }

      case 'keyboard': {
        await page.keyboard.press(step.key!);
        break;
      }

      case 'scroll_to_bottom': {
        await page.evaluate(() => {
          window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' });
        });
        await page.waitForTimeout(500);
        break;
      }

      case 'wait_for': {
        await page.waitForSelector(step.selector!, { timeout: 5000 });
        break;
      }
    }

    // 每步执行后等待稳定
    await this.stabilize(page);
  }

  private async stabilize(page: Page): Promise<void> {
    const stabilizationMs = this.config.stabilizationMs ?? 300;

    // 等待网络空闲
    try {
      await page.waitForLoadState('networkidle', { timeout: 3000 });
    } catch {
      // 超时不报错，继续
    }

    // 等待字体
    await page.evaluate(() => document.fonts.ready);

    // 等待无动画帧
    await page.waitForTimeout(stabilizationMs);
  }

  private resolveFixture(url: string): string | null {
    // 根据 URL 映射到 fixture 文件
    // 实际实现需要读取 fixture-map.yaml
    return null;
  }
}

export interface StateSequence {
  stateId: string;
  pageId: string;
  steps: InteractionStep[];
}

export interface InteractionStep {
  type: 'click' | 'hover' | 'keyboard' | 'scroll_to_bottom' | 'wait_for';
  selector?: string;
  key?: string;description: string;
}
```

---

## 四、侧边栏折叠展开的专项处理

这是用户明确提到的问题，GPT 方案没有专项覆盖。侧边栏折叠是一个**布局级状态变化**，会影响所有其他区域的几何。必须作为独立状态采集：

```typescript
// scripts/ui-autopilot/discovery/sidebar-states.ts

import type { Page } from '@playwright/test';

export interface SidebarState {
  mode: 'expanded' | 'collapsed' | 'hidden' | 'mobile-open';
  width: number;
  contentOffset: number;  // content 区域的margin-left 或 padding-left
  labelsVisible: boolean;
  iconsVisible: boolean;
}

/**
 * 侧边栏状态的完整采集序列。
 * 
 * 必须在以下状态下各截一次全页截图：
 * 1. 默认展开
 * 2. 折叠（只显示图标）
 * 3.鼠标悬浮在折叠侧边栏上（如有展开动画）
 * 4. 特定子菜单展开
 * 5. 在折叠状态下的子菜单 Popover
 */
export async function captureSidebarStates(
  page: Page,
  sidebarSelector: string = '[data-ui-region="sidebar"]',
  toggleSelector: string = '[data-sidebar-toggle]',
  outputDir: string,
): Promise<Record<string, SidebarState>> {
  const states: Record<string, SidebarState> = {};

  // 状态1：默认展开
  const expandedState = await measureSidebarState(page, sidebarSelector);
  states['sidebar_expanded'] = expandedState;

  await page.screenshot({
    path: `${outputDir}/sidebar-expanded.png`,
    animations: 'disabled',
  });

  // 状态2：触发折叠
  const toggle = page.locator(toggleSelector);
  const toggleExists = await toggle.count() > 0;

  if (toggleExists) {
    await toggle.click();

    // 等待折叠动画完成
    await waitForSidebarTransition(page, sidebarSelector);

    const collapsedState = await measureSidebarState(page, sidebarSelector);
    states['sidebar_collapsed'] = collapsedState;

    await page.screenshot({
      path: `${outputDir}/sidebar-collapsed.png`,
      animations: 'disabled',
    });

    // 状态3：悬浮在折叠侧边栏（有时会弹出标签 Tooltip）
    const sidebarEl = page.locator(sidebarSelector);
    await sidebarEl.hover({ position: { x: 10, y: 80 } });
    await page.waitForTimeout(400);  // 等待 hover tooltip

    await page.screenshot({
      path: `${outputDir}/sidebar-collapsed-hover.png`,
      animations: 'disabled',
    });

    // 恢复展开状态，用于其他测试
    await toggle.click();
    await waitForSidebarTransition(page, sidebarSelector);
  }

  return states;
}

async function measureSidebarState(
  page: Page,
  selector: string,
): Promise<SidebarState> {
  return page.evaluate(
    ({ selector }) => {
      const sidebar = document.querySelector<HTMLElement>(selector);

      if (!sidebar) {
        return {
          mode: 'hidden' as const,
          width: 0,
          content

          #第2/5 部分续完+ 第3/5 部分开始

接上文`measureSidebarState` 中断处：

```typescript
async function measureSidebarState(
  page: Page,
  selector: string,
): Promise<SidebarState> {
  return page.evaluate(
    ({ selector }) => {
      const sidebar = document.querySelector<HTMLElement>(selector);

      if (!sidebar) {
        return {
          mode: 'hidden' as const,
          width: 0,
          contentOffset: 0,
          labelsVisible: false,
          iconsVisible: false,
        };
      }

      const style = getComputedStyle(sidebar);
      const rect = sidebar.getBoundingClientRect();
      const width = rect.width;

      // 检测侧边栏当前模式
      const dataState = sidebar.getAttribute('data-state');
      const ariaExpanded = sidebar.getAttribute('aria-expanded');
      const classNames = Array.from(sidebar.classList);

      const isCollapsed =
        dataState === 'collapsed' ||
        ariaExpanded === 'false' ||
        classNames.some(c => c.includes('collapsed') || c.includes('shrink')) ||
        width< 80;

      const isHidden =
        style.display === 'none' ||
        style.visibility === 'hidden' ||
        parseFloat(style.opacity) === 0;

      // 判断是否是移动端打开状态
      const isMobileOpen =
        style.position === 'fixed' &&
        classNames.some(c => c.includes('open') || c.includes('mobile'));

      let mode: SidebarState['mode'];
      if (isHidden) {
        mode = 'hidden';
      } else if (isMobileOpen) {
        mode = 'mobile-open';
      } else if (isCollapsed) {
        mode = 'collapsed';
      } else {
        mode = 'expanded';
      }

      // 计算 content 区域偏移
      // 优先找相邻的 main/content 区域
      const contentRegion =
        document.querySelector<HTMLElement>('[data-ui-region="content"]')??
        document.querySelector<HTMLElement>('main') ??
        sidebar.nextElementSibling as HTMLElement | null;

      const contentOffset = contentRegion
        ? parseFloat(getComputedStyle(contentRegion).marginLeft ||
            getComputedStyle(contentRegion).paddingLeft || '0')
        : 0;

      // 检测 labels 是否可见（文字菜单项）
      const menuLabels = sidebar.querySelectorAll<HTMLElement>(
        '[data-menu-label], .ant-menu-title-content, [role="menuitem"] span',
      );

      const labelsVisible =
        menuLabels.length > 0 &&
        Array.from(menuLabels).some(el => {
          const s = getComputedStyle(el);
          return (
            s.display !== 'none' &&
            s.visibility !== 'hidden' &&
            s.opacity !== '0' &&
            el.getBoundingClientRect().width > 0
          );
        });

      // 检测 icons 是否可见
      const icons = sidebar.querySelectorAll<HTMLElement>(
        'svg, [data-icon], .anticon, [class*="icon"]',
      );

      const iconsVisible =
        icons.length > 0 &&
        Array.from(icons).some(el => {
          const s = getComputedStyle(el);
          return (
            s.display !== 'none' &&
            el.getBoundingClientRect().width > 0
          );
        });

      return {
        mode,
        width,
        contentOffset,
        labelsVisible,
        iconsVisible,
      };
    },
    { selector },
  );
}

async function waitForSidebarTransition(
  page: Page,
  selector: string,
  maxWaitMs = 800,
): Promise<void> {
  // 采样两次几何，直到宽度稳定
  const startTime = Date.now();
  let prevWidth = -1;

  while (Date.now() - startTime < maxWaitMs) {
    const width = await page.evaluate(
      ({ sel }) =>
        document.querySelector<HTMLElement>(sel)?.getBoundingClientRect().width ?? -1,
      { sel: selector },
    );

    if (Math.abs(width - prevWidth)< 1&& prevWidth !== -1) {
      // 宽度连续两次采样相同，认为 transition 完成
      return;
    }

    prevWidth = width;
    await page.waitForTimeout(80);
  }
}
```

---

## 五、采集结果的版本管理：防止原型漂移

GPT 方案没有提到采集结果的版本控制。这是实际运行中的大问题：

```text
问题场景：
夜间 Loop 第3次迭代时，原型设计师更新了原型。
实现代码正在往旧的截图逼近。
没有版本控制的话，系统不会发现这件事，
继续把新原型当旧原型还原，浪费整夜工时。
```

```python
# scripts/ui_autopilot/discovery/capture_registry.py

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CaptureVersion:
    version_id: str
    captured_at: float
    state_digests: dict[str, str]# state_id → screenshot digest
    prototype_url: str
    total_states: int


@dataclass(slots=True)
class CaptureRegistry:
    """
    追踪所有已采集的原型截图版本。
    核心功能：
    1. 每次采集后生成 digest，与上次比对
    2. 检测到原型变化时发出PROTOTYPE_DRIFT 警告
    3. 保留最近 N 个版本，支持回滚到上次稳定版本
    """

    registry_path: Path
    max_versions: int = 5

    _data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.registry_path.exists():
            self._data = json.loads(self.registry_path.read_text())
        else:
            self._data = {"versions": [], "current": None}

    def register(
        self,
        prototype_url: str,
        state_screenshots: dict[str, Path],
    ) -> tuple[CaptureVersion, bool]:
        """
        注册新的采集版本。
        返回：(版本对象, 是否检测到漂移)
        """
        digests = {
            state_id: self._digest_file(path)
            for state_id, path in state_screenshots.items()
        }

        version_id = hashlib.sha256(
            json.dumps(digests, sort_keys=True).encode()
        ).hexdigest()[:12]

        version = CaptureVersion(
            version_id=version_id,
            captured_at=time.time(),
            state_digests=digests,
            prototype_url=prototype_url,
            total_states=len(digests),
        )

        # 检测漂移
        drift_detected = False
        current_id = self._data.get("current")

        if current_id:
            prev_versions = [
                v for v in self._data["versions"]
                if v["version_id"] == current_id
            ]

            if prev_versions:
                prev_digests = prev_versions[0]["state_digests"]
                changed_states = [
                    sid for sid, digest in digests.items()
                    if prev_digests.get(sid) != digest
                ]

                if changed_states:
                    drift_detected = True
                    print(
                        f"[PROTOTYPE_DRIFT] 以下状态的截图发生变化："f"{changed_states}"
                    )

        # 持久化
        self._data["versions"].append({
            "version_id": version.version_id,
            "captured_at": version.captured_at,
            "state_digests": version.state_digests,
            "prototype_url": version.prototype_url,
            "total_states": version.total_states,
        })

        # 保留最近 N 个版本
        if len(self._data["versions"]) > self.max_versions:
            self._data["versions"] = self._data["versions"][-self.max_versions:]

        self._data["current"] = version.version_id
        self.registry_path.write_text(json.dumps(self._data, indent=2))

        return version, drift_detected

    @staticmethod
    def _digest_file(path: Path) -> str:
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
```

---

## 第2/5 部分完整结论

| 问题 | GPT 方案 | Opus 方案 |
|---|---|---|
| 状态发现 | BFS爬链接 | 路由静态分析 + 交互状态矩阵 + 自动发现器 |
| 滚动内容 | fullPage截图 | 分段滚动采集 +懒加载等待 |
| 侧边栏状态 | 未专项覆盖 | 专项采集序列 + transition等待 |
| 原型漂移 | 无检测 | digest版本对比，检测到漂移阻断并报告 |
| 截图稳定性 | 固定等待时间 | 几何采样稳定性检测 + 动画强制禁用 |

---

# 第3/5 部分：视觉评分系统的根本性重构

> **核心分歧**：GPT 用SSIM/感知哈希作为主评分指标。我认为这两个指标对UI 还原质量的判断是**系统性失准的**。
>
> SSIM 对颜色偏移不敏感，对几何偏移过度敏感（1px 偏移导致大量误报）。感知哈希对字体渲染差异完全失盲。**正确的评分应该是面向还原目标的多维度评分，每个维度用最适合的指标。**

---

## 一、当前评分失准的具体案例

```text
案例1：背景色差原型：background: #F5F7FA
  实现：background: #FFFFFF
  SSIM 评分：0.97（"几乎完全相同"）
  实际视觉：背景明显偏白，用户能看出来

案例2：1px 边框偏移
  SSIM 评分：0.88（"较大差异"）
  实际视觉：几乎无法察觉

案例3：字重差异
  原型：font-weight: 600
  实现：font-weight: 500
  感知哈希：差异极小（pass）
  实际视觉：标题不够突出，设计师能看出来

案例4：圆角缺失
  SSIM 评分：0.995（"几乎完全相同"）
  实际视觉：按钮方角，与设计稿明显不符
```

---

## 二、分维度评分系统

替代单一 SSIM，用五个独立维度打分，每个维度有独立权重和独立方法：

```python
# scripts/ui_autopilot/scoring/multi_dim_scorer.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image


@dataclass(frozen=True, slots=True)
class DimensionScore:
    name: str
    score: float        # 0-1
    weight: float       # 在总分中的权重
    detail: dict[str, Any]
    method: str         # 使用的评估方法


@dataclass(slots=True)
class CompositeScore:
    target_id: str
    state_id: str
    total: float                # 加权总分
    dimensions: list[DimensionScore]
    passed: bool
    threshold: float
    dominant_failure: str | None          # 得分最低的维度
    actionable_diagnosis: str             # 直接给Worker 的诊断文本

    @classmethod
    def from_dimensions(
        cls,
        target_id: str,
        state_id: str,
        dimensions: list[DimensionScore],
        threshold: float,) -> "CompositeScore":
        total = sum(d.score * d.weight for d in dimensions)
        weight_sum = sum(d.weight for d in dimensions)
        total = total / weight_sum if weight_sum > 0 else 0.0

        worst = min(dimensions, key=lambda d: d.score)
        dominant_failure = worst.name if worst.score < threshold else None

        return cls(
            target_id=target_id,
            state_id=state_id,
            total=total,
            dimensions=dimensions,
            passed=total >= threshold,
            threshold=threshold,
            dominant_failure=dominant_failure,
            actionable_diagnosis=_build_diagnosis(dimensions, threshold),
        )


def _build_diagnosis(
    dimensions: list[DimensionScore],
    threshold: float,
) -> str:
    failing = [d for d in dimensions if d.score < threshold]
    if not failing:
        return "所有维度通过"

    failing.sort(key=lambda d: d.score)
    lines = []

    for d in failing[:3]:  # 最多报告3个失败维度
        detail_str = ", ".join(
            f"{k}={v}" for k, v in d.detail.items()
            if not isinstance(v, (list, dict))
        )
        lines.append(
            f"[{d.name}] 得分={d.score:.3f}（方法={d.method}）: {detail_str}"
        )

    return "\n".join(lines)


class MultiDimScorer:
    """
    五维度评分器：

    1. geometry(权重 0.30)── 元素位置、尺寸、间距
    2. color       (权重 0.25) ── 背景色、前景色、边框色
    3. typography  (权重 0.20) ── 字体、字重、行高、字距
    4. decoration  (权重 0.15) ── 圆角、阴影、边框
    5. layout      (权重 0.10) ── flex/grid 对齐、overflow

    与 SSIM 的关键区别：
    - geometry 用像素级区域IoU，不用 SSIM
    - color 用 LAB 色彩空间 Delta-E，不用 RGB 差值
    - typography 用 computed style比对，不用图像比对
    - decoration 用 computed style + 局部截图双重验证
    - layout 纯computed style，完全不依赖截图
    """

    DIMENSION_WEIGHTS = {
        "geometry": 0.30,
        "color": 0.25,
        "typography": 0.20,
        "decoration": 0.15,
        "layout": 0.10,
    }

    def score(
        self,
        prototype_img: Image.Image,
        actual_img: Image.Image,
        prototype_styles: dict[str, str],
        actual_styles: dict[str, str],
        prototype_box: dict[str, float],
        actual_box: dict[str, float],
        target_id: str,
        state_id: str,
        threshold: float = 0.97,
    ) -> CompositeScore:
        dimensions = [
            self._score_geometry(
                prototype_img, actual_img,
                prototype_box, actual_box,
            ),
            self._score_color(
                prototype_img, actual_img,
                prototype_styles, actual_styles,
            ),
            self._score_typography(
                prototype_styles, actual_styles,
            ),
            self._score_decoration(
                prototype_img, actual_img,
                prototype_styles, actual_styles,
            ),
            self._score_layout(
                prototype_styles, actual_styles,
            ),
        ]

        return CompositeScore.from_dimensions(
            target_id=target_id,
            state_id=state_id,
            dimensions=dimensions,
            threshold=threshold,
        )

    #──────────────────────────────────────────────
    # 维度1：几何评分（IoU-based，不用 SSIM）
    # ──────────────────────────────────────────────

    def _score_geometry(
        self,
        proto_img: Image.Image,
        actual_img: Image.Image,
        proto_box: dict[str, float],
        actual_box: dict[str, float],
    ) -> DimensionScore:
        """
        用 IoU 评估几何还原度。
        不用 SSIM 的原因：SSIM 对1px 位移高度敏感，
        但 1px 对人眼几乎不可见。
        IoU 以视觉区域重叠为标准，更符合设计评审直觉。
        """

        def box_to_rect(b: dict) -> tuple[float, float, float, float]:
            return b['x'], b['y'], b['x'] + b['width'], b['y'] + b['height']

        px1, py1, px2, py2 = box_to_rect(proto_box)
        ax1, ay1, ax2, ay2 = box_to_rect(actual_box)

        inter_x1 = max(px1, ax1)
        inter_y1 = max(py1, ay1)
        inter_x2 = min(px2, ax2)
        inter_y2 = min(py2, ay2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            iou = 0.0
        else:
            inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
            proto_area = (px2 - px1) * (py2 - py1)
            actual_area = (ax2 - ax1) * (ay2 - ay1)
            union_area = proto_area + actual_area - inter_area
            iou = inter_area / union_area if union_area > 0 else 0.0

        width_delta = abs(actual_box['width'] - proto_box['width'])
        height_delta = abs(actual_box['height'] - proto_box['height'])

        return DimensionScore(
            name="geometry",
            score=iou,
            weight=self.DIMENSION_WEIGHTS["geometry"],
            detail={
                "iou": round(iou, 4),
                "width_delta_px": round(width_delta, 1),
                "height_delta_px": round(height_delta, 1),
                "x_delta_px": round(actual_box['x'] - proto_box['x'], 1),
                "y_delta_px": round(actual_box['y'] - proto_box['y'], 1),
            },
            method="iou",
        )

    # ──────────────────────────────────────────────
    # 维度2：颜色评分（LAB Delta-E，不用 RGB）
    # ──────────────────────────────────────────────

    def _score_color(
        self,
        proto_img: Image.Image,
        actual_img: Image.Image,
        proto_styles: dict[str, str],
        actual_styles: dict[str, str],
    ) -> DimensionScore:
        """
        用 CIE76 Delta-E 评估颜色还原度。
        LAB 色彩空间的差值更符合人眼对颜色差异的感知。
        Delta-E < 2：人眼无法察觉
        Delta-E 2-10：明显差异
        Delta-E > 10：强烈差异
        """

        key_color_props = [
            'color',
            'background-color',
            'border-top-color',
        ]

        deltas: list[float] = []

        for prop in key_color_props:
            proto_val = proto_styles.get(prop, '')
            actual_val = actual_styles.get(prop, '')

            if not proto_val or not actual_val:
                continue

            proto_rgb = self._parse_rgb(proto_val)
            actual_rgb = self._parse_rgb(actual_val)

            if proto_rgb and actual_rgb:
                delta_e = self._rgb_delta_e(proto_rgb, actual_rgb)
                deltas.append(delta_e)

        if not deltas:
            # 没有可比较的颜色属性，退回到图像区域平均色差
            score = self._fallback_color_score(proto_img, actual_img)
            return DimensionScore(
                name="color",
                score=score,
                weight=self.DIMENSION_WEIGHTS["color"],
                detail={"method": "image_average_lab"},method="image_lab_fallback",
            )

        avg_delta_e = sum(deltas) / len(deltas)
        max_delta_e = max(deltas)

        # 将 Delta-E 映射到 0-1 分数
        # Delta-E=0 → 1.0，Delta-E=10 → 0.0
        score = max(0.0, 1.0 - avg_delta_e / 10.0)

        return DimensionScore(
            name="color",
            score=score,
            weight=self.DIMENSION_WEIGHTS["color"],
            detail={
                "avg_delta_e": round(avg_delta_e, 2),
                "max_delta_e": round(max_delta_e, 2),
                "compared_properties": len(deltas),
            },
            method="cie76_delta_e",
        )

    # ──────────────────────────────────────────────
    # 维度3：排版评分（纯 computed style 比对）
    # ──────────────────────────────────────────────

    def _score_typography(
        self,
        proto_styles: dict[str, str],
        actual_styles: dict[str, str],
    ) -> DimensionScore:
        """
        排版评分完全不依赖截图，只比较computed style。
        原因：字体渲染差异（字重、行高）在截图上极难检测，
        但在 computed style 上是精确的数值差异。
        """

        typo_props = {
            'font-size': {'weight': 0.3, 'tolerance': '2px'},
            'font-weight': {'weight': 0.25, 'tolerance': '100'},
            'line-height': {'weight': 0.2, 'tolerance': '4px'},
            'letter-spacing': {'weight': 0.1, 'tolerance': '0.5px'},
            'font-family': {'weight': 0.15, 'tolerance': None},
        }

        prop_scores: dict[str, float] = {}

        for prop, config in typo_props.items():
            proto_val = proto_styles.get(prop, '')
            actual_val = actual_styles.get(prop, '')

            if not proto_val or not actual_val:
                prop_scores[prop] = 1.0  # 未检测到的属性不扣分
                continue

            if config['tolerance'] is None:
                # 字符串精确比对（font-family）
                prop_scores[prop] = 1.0 if proto_val == actual_val else 0.6
            else:
                # 数值容差比对
                proto_num = self._parse_px(proto_val)
                actual_num = self._parse_px(actual_val)
                tolerance = self._parse_px(config['tolerance'])

                if proto_num is None or actual_num is None:
                    prop_scores[prop] = 1.0 if proto_val == actual_val else 0.7
                else:
                    delta = abs(actual_num - proto_num)
                    prop_scores[prop] = max(0.0, 1.0 - delta / (tolerance * 5))

        total_weight = sum(c['weight'] for c in typo_props.values())
        weighted_score = sum(
            prop_scores.get(p, 1.0) * config['weight']
            for p, config in typo_props.items()
        ) / total_weight

        return DimensionScore(
            name="typography",
            score=weighted_score,
            weight=self.DIMENSION_WEIGHTS["typography"],
            detail={
                k: round(v, 3) for k, v in prop_scores.items()
            },
            method="computed_style_diff",
        )

    # ──────────────────────────────────────────────
    # 维度4：装饰评分（圆角、阴影、边框）
    # ──────────────────────────────────────────────

    def _score_decoration(
        self,
        proto_img: Image.Image,
        actual_img: Image.Image,
        proto_styles: dict[str, str],
        actual_styles: dict[str, str],
    ) -> DimensionScore:
        deco_props = {
            'border-top-left-radius': 0.25,
            'border-top-right-radius': 0.25,
            'border-bottom-right-radius': 0.25,
            'border-bottom-left-radius': 0.25,'box-shadow': 0.3,
            'border-top-width': 0.1,
            'border-top-style': 0.1,
        }

        total_weight = sum(deco_props.values())
        weighted_score = 0.0
        details: dict[str, float] = {}

        for prop, weight in deco_props.items():
            proto_val = proto_styles.get(prop, '')
            actual_val = actual_styles.get(prop, '')

            if not proto_val:
                weighted_score += weight
                continue

            if prop == 'box-shadow':
                # 阴影用语义相似度，不严格比对
                score = 1.0 if proto_val == actual_val else (
                    0.7 if ('none' in proto_val) == ('none' in actual_val) else 0.3
                )
            elif'radius' in prop:
                proto_num = self._parse_px(proto_val)
                actual_num = self._parse_px(actual_val)

                if proto_num is None:
                    score = 1.0 if proto_val == actual_val else 0.7
                else:
                    delta = abs((actual_num or 0) - proto_num)
                    #圆角容差：2px 以内不扣分
                    score = max(0.0, 1.0 - delta / 10.0)
            else:
                score = 1.0 if proto_val == actual_val else 0.6

            details[prop] = round(score, 3)
            weighted_score += score * weight

        final_score = weighted_score / total_weight

        return DimensionScore(
            name="decoration",
            score=final_score,
            weight=self.DIMENSION_WEIGHTS["decoration"],
            detail=details,
            method="computed_style_diff",
        )

    # ──────────────────────────────────────────────
    # 维度5：布局评分（flex/grid 对齐）
    # ──────────────────────────────────────────────

    def _score_layout(
        self,
        proto_styles: dict[str, str],
        actual_styles: dict[str, str],
    ) -> DimensionScore:
        layout_props = [
            'display',
            'flex-direction',
            'justify-content',
            'align-items',
            'flex-wrap',
            'grid-template-columns',
            'overflow-x',
            'overflow-y',
        ]

        matched = 0
        total = 0
        mismatches: list[str] = []

        for prop in layout_props:
            proto_val = proto_styles.get(prop, '')
            actual_val = actual_styles.get(prop, '')

            if not proto_val:
                continue

            total += 1
            if proto_val == actual_val:
                matched += 1
            else:
                mismatches.append(
                    f"{prop}: expected={proto_val!r} actual={actual_val!r}"
                )

        score = matched / total if total > 0 else 1.0

        return DimensionScore(
            name="layout",
            score=score,
            weight=self.DIMENSION_WEIGHTS["layout"],
            detail={
                "matched": matched,
                "total": total,
                "mismatches": mismatches[:5],
            },
            method="computed_style_exact",
        )

    # ──────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────

    @staticmethod
    def _parse_rgb(css_color: str) -> tuple[int, int, int] | None:
        import re
        m = re.match(
            r'rgba?\((\d+),\s*(\d+),\s*(\d+)',
            css_color.strip(),
        )
        if m:
            return int(m.group(


# 第3/5 部分续完

接上文 `_parse_rgb` 中断处，补全工具方法并完成第3部分：

```python
    @staticmethod
    def _parse_rgb(css_color: str) -> tuple[int, int, int] | None:
        import re
        m = re.match(
            r'rgba?\((\d+),\s*(\d+),\s*(\d+)',
            css_color.strip(),
        )
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))

        # hex 格式
        hex_match = re.match(r'#([0-9a-fA-F]{6})', css_color.strip())
        if hex_match:
            hex_str = hex_match.group(1)
            return (
                int(hex_str[0:2], 16),
                int(hex_str[2:4], 16),
                int(hex_str[4:6], 16),
            )

        return None

    @staticmethod
    def _rgb_delta_e(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
        """
        CIE76 Delta-E 计算（RGB → LAB → Delta-E）。
        """
        from skimage import color
        import numpy as np

        lab1 = color.rgb2lab(np.array([[rgb1]], dtype=np.uint8) / 255.0)[0, 0]
        lab2 = color.rgb2lab(np.array([[rgb2]], dtype=np.uint8) / 255.0)[0, 0]

        return float(np.linalg.norm(lab1 - lab2))

    @staticmethod
    def _parse_px(css_value: str) -> float | None:
        """
        从 CSS 值提取像素数。
        支持：'16px', '1.5rem'（按16倍率）, '100' (裸数字按 font-weight)
        """
        import re

        if not css_value:
            return None

        css_value = css_value.strip()

        # 裸数字（font-weight）
        if css_value.isdigit():
            return float(css_value)

        # px 单位
        m = re.match(r'([\d.]+)px', css_value)
        if m:
            return float(m.group(1))

        # rem 单位（假设 1rem = 16px）
        m = re.match(r'([\d.]+)rem', css_value)
        if m:
            return float(m.group(1)) * 16.0

        return None

    def _fallback_color_score(
        self,
        proto_img: Image.Image,
        actual_img: Image.Image,
    ) -> float:
        """
        当没有可用的 computed style 颜色时，
        回退到图像区域平均色差。
        """
        import numpy as np
        from skimage import color

        proto_arr = np.array(proto_img.convert('RGB'))
        actual_arr = np.array(actual_img.convert('RGB'))

        # 确保尺寸一致
        if proto_arr.shape != actual_arr.shape:
            from PIL import Image as PILImage
            actual_img_resized = actual_img.resize(proto_img.size)
            actual_arr = np.array(actual_img_resized.convert('RGB'))

        # 转 LAB
        proto_lab = color.rgb2lab(proto_arr / 255.0)
        actual_lab = color.rgb2lab(actual_arr / 255.0)

        # 平均 Delta-E
        delta_e_map = np.linalg.norm(proto_lab - actual_lab, axis=2)
        avg_delta_e = float(np.mean(delta_e_map))

        # 映射到 0-1
        return max(0.0, 1.0 - avg_delta_e / 10.0)
```

---

## 三、视觉评分的阈值自适应

GPT 用固定阈值 0.97。我认为阈值应该按区域类型和修复阶段动态调整：

```python
# scripts/ui_autopilot/scoring/adaptive_threshold.py

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RegionType(StrEnum):
    SHELL = "shell"            # 页面骨架（header/sidebar/footer）
    CONTENT = "content"        # 主内容区域
    ELEMENT = "element"        # 交互元素（button/card/input）
    DECORATION = "decoration"  # 装饰元素（icon/divider）


class RepairPhase(StrEnum):
    SHELL = "shell"
    REGION = "region"
    ELEMENT = "element"
    POLISH = "polish"


@dataclass(frozen=True, slots=True)
class AdaptiveThreshold:
    """
    动态阈值配置。
    
    与 GPT 固定 0.97 的区别：
    1. Shell 阶段只看几何，阈值宽松（0.92）
    2. Element 阶段看所有维度，阈值严格（0.98）
    3. 装饰元素阈值最宽松（0.90），避免卡在icon细节
    4. 关键交互元素阈值最严格（0.99）
    """
    
    region_type: RegionType
    phase: RepairPhase
    
    # 各维度的单独阈值
    geometry_threshold: float
    color_threshold: float
    typography_threshold: float
    decoration_threshold: float
    layout_threshold: float
    
    # 综合阈值
    composite_threshold: float
    
    # 是否阻断后续阶段（false 则记录但继续）
    blocking: bool


# 阈值矩阵：(region_type, phase) → threshold
THRESHOLD_MATRIX: dict[tuple[RegionType, RepairPhase], AdaptiveThreshold] = {
    # Shell 阶段：只看几何和布局，不看装饰
    (RegionType.SHELL, RepairPhase.SHELL): AdaptiveThreshold(
        region_type=RegionType.SHELL,
        phase=RepairPhase.SHELL,
        geometry_threshold=0.92,
        color_threshold=0.85,        # 宽松，Shell阶段不严格要求
        typography_threshold=0.85,
        decoration_threshold=0.80,
        layout_threshold=0.95,
        composite_threshold=0.90,
        blocking=True,
    ),
    
    # Region 阶段：关注几何和布局
    (RegionType.CONTENT, RepairPhase.REGION): AdaptiveThreshold(
        region_type=RegionType.CONTENT,
        phase=RepairPhase.REGION,
        geometry_threshold=0.95,
        color_threshold=0.90,
        typography_threshold=0.88,
        decoration_threshold=0.85,
        layout_threshold=0.96,
        composite_threshold=0.93,
        blocking=True,
    ),
    
    # Element 阶段：严格要求所有维度
    (RegionType.ELEMENT, RepairPhase.ELEMENT): AdaptiveThreshold(
        region_type=RegionType.ELEMENT,
        phase=RepairPhase.ELEMENT,
        geometry_threshold=0.97,
        color_threshold=0.96,
        typography_threshold=0.95,
        decoration_threshold=0.94,
        layout_threshold=0.97,
        composite_threshold=0.96,
        blocking=True,
    ),
    
    # Polish 阶段：最终精修，极严格
    (RegionType.ELEMENT, RepairPhase.POLISH): AdaptiveThreshold(
        region_type=RegionType.ELEMENT,
        phase=RepairPhase.POLISH,
        geometry_threshold=0.99,
        color_threshold=0.98,
        typography_threshold=0.98,
        decoration_threshold=0.96,
        layout_threshold=0.99,
        composite_threshold=0.98,
        blocking=False,  # Polish 阶段不阻断，记录即可
    ),
    
    # 装饰元素：宽松阈值，避免卡死
    (RegionType.DECORATION, RepairPhase.ELEMENT): AdaptiveThreshold(
        region_type=RegionType.DECORATION,
        phase=RepairPhase.ELEMENT,
        geometry_threshold=0.90,
        color_threshold=0.88,
        typography_threshold=0.85,
        decoration_threshold=0.85,
        layout_threshold=0.88,
        composite_threshold=0.88,
        blocking=False,
    ),
}


def get_threshold(
    region_type: RegionType,
    phase: RepairPhase,
) -> AdaptiveThreshold:
    """
    查询当前区域和阶段对应的阈值配置。
    如果没有精确匹配，返回保守的默认值。
    """
    key = (region_type, phase)
    
    if key in THRESHOLD_MATRIX:
        return THRESHOLD_MATRIX[key]
    
    # 默认：中等严格
    return AdaptiveThreshold(
        region_type=region_type,
        phase=phase,
        geometry_threshold=0.94,
        color_threshold=0.92,
        typography_threshold=0.90,
        decoration_threshold=0.88,
        layout_threshold=0.94,
        composite_threshold=0.92,
        blocking=True,
    )
```

---

## 四、评分结果的可解释性输出

GPT 方案的评分输出是数字。Worker 模型拿到0.89 不知道该改什么。

我的输出必须包含**直接可操作的诊断文本**：

```python
# scripts/ui_autopilot/scoring/explainer.py

from __future__ import annotations

from .multi_dim_scorer import CompositeScore, DimensionScore


def generate_worker_diagnosis(
    score: CompositeScore,
    prototype_styles: dict[str, str],
    actual_styles: dict[str, str],
) -> str:
    """
    将评分结果翻译成 Worker 模型可直接执行的诊断文本。
    
    与 GPT 方案的区别：
    不只说"颜色不对"，而是说"背景色应为 #F5F7FA，当前为 #FFFFFF，
    建议使用 Token var(--ui-bg-secondary)"。
    """
    
    if score.passed:
        return f"✓ 所有维度通过（综合分={score.total:.3f}）"
    
    lines = [f"目标区域 {score.target_id} 未通过（综合分={score.total:.3f}，阈值={score.threshold}）\n"]
    
    failing_dims = [d for d in score.dimensions if d.score < score.threshold]
    failing_dims.sort(key=lambda d: d.score)
    
    for dim in failing_dims[:3]:  # 最多报告3个失败维度
        lines.append(f"\n## {dim.name.upper()} 维度失败 (得分={dim.score:.3f})")
        
        if dim.name == "geometry":
            lines.append(_explain_geometry(dim))
        elif dim.name == "color":
            lines.append(_explain_color(dim, prototype_styles, actual_styles))
        elif dim.name == "typography":
            lines.append(_explain_typography(dim, prototype_styles, actual_styles))
        elif dim.name == "decoration":
            lines.append(_explain_decoration(dim, prototype_styles, actual_styles))
        elif dim.name == "layout":
            lines.append(_explain_layout(dim))
    
    lines.append("\n## 建议修复优先级")
    lines.append(f"1. 优先修复 {failing_dims[0].name}（影响最大）")
    
    if len(failing_dims) > 1:
        lines.append(f"2. 然后修复 {failing_dims[1].name}")
    
    return "\n".join(lines)


def _explain_geometry(dim: DimensionScore) -> str:
    detail = dim.detail
    iou = detail.get("iou", 0.0)
    
    parts = [f"区域重叠度（IoU）={iou:.2%}"]
    
    width_delta = detail.get("width_delta_px", 0)
    height_delta = detail.get("height_delta_px", 0)
    x_delta = detail.get("x_delta_px", 0)
    y_delta = detail.get("y_delta_px", 0)
    
    if abs(width_delta) > 5:
        direction = "偏宽" if width_delta > 0 else "偏窄"
        parts.append(f"宽度{direction} {abs(width_delta):.0f}px")
    
    if abs(height_delta) > 5:
        direction = "偏高" if height_delta > 0 else "偏矮"
        parts.append(f"高度{direction} {abs(height_delta):.0f}px")
    
    if abs(x_delta) > 5:
        direction = "偏右" if x_delta > 0 else "偏左"
        parts.append(f"水平位置{direction} {abs(x_delta):.0f}px")
    
    if abs(y_delta) > 5:
        direction = "偏下" if y_delta > 0 else "偏上"
        parts.append(f"垂直位置{direction} {abs(y_delta):.0f}px")
    
    parts.append("\n建议检查：padding/margin/width/height/flex-basis")
    
    return "\n".join(parts)


def _explain_color(
    dim: DimensionScore,
    proto_styles: dict[str, str],
    actual_styles: dict[str, str],
) -> str:
    detail = dim.detail
    avg_delta_e = detail.get("avg_delta_e", 0)
    
    parts = [f"平均色差 Delta-E={avg_delta_e:.1f}（>2 人眼可察觉）"]
    
    # 找出偏差最大的属性
    color_props = ["color", "background-color", "border-top-color"]
    
    for prop in color_props:
        proto_val = proto_styles.get(prop, "")
        actual_val = actual_styles.get(prop, "")
        
        if proto_val and actual_val and proto_val != actual_val:
            parts.append(
                f"\n{prop}:\n"
                f"  期望: {proto_val}\n"
                f"  实际: {actual_val}\n"
                f"  建议: 检查 src/styles/tokens/_colors.scss 中是否有近似值"
            )
    
    return "\n".join(parts)


def _explain_typography(
    dim: DimensionScore,
    proto_styles: dict[str, str],
    actual_styles: dict[str, str],
) -> str:
    detail = dim.detail
    
    parts = ["排版属性差异："]
    
    typo_props = {
        "font-size": "字号",
        "font-weight": "字重",
        "line-height": "行高",
        "letter-spacing": "字距",
        "font-family": "字体",
    }
    
    for prop, label in typo_props.items():
        score = detail.get(prop, 1.0)
        
        if score < 0.9:
            proto_val = proto_styles.get(prop, "")
            actual_val = actual_styles.get(prop, "")
            
            parts.append(
                f"\n{label} ({prop}):\n"
                f"  期望: {proto_val}\n"
                f"  实际: {actual_val}\n"
                f"  得分: {score:.2f}"
            )
    
    parts.append("\n建议检查 src/styles/tokens/_typography.scss")
    
    return "\n".join(parts)


def _explain_decoration(
    dim: DimensionScore,
    proto_styles: dict[str, str],
    actual_styles: dict[str, str],
) -> str:
    detail = dim.detail
    
    parts = ["装饰属性差异："]
    
    deco_props = {
        "border-top-left-radius": "左上圆角",
        "border-top-right-radius": "右上圆角",
        "border-bottom-right-radius": "右下圆角",
        "border-bottom-left-radius": "左下圆角",
        "box-shadow": "阴影",
        "border-top-width": "边框宽度",
    }
    
    for prop, label in deco_props.items():
        score = detail.get(prop, 1.0)
        
        if score < 0.9:
            proto_val = proto_styles.get(prop, "")
            actual_val = actual_styles.get(prop, "")
            
            parts.append(
                f"\n{label} ({prop}):\n"
                f"  期望: {proto_val}\n"
                f"  实际: {actual_val}"
            )
    
    return "\n".join(parts)


def _explain_layout(dim: DimensionScore) -> str:
    detail = dim.detail
    mismatches = detail.get("mismatches", [])
    
    if not mismatches:
        return "布局属性无明显偏差"
    
    parts = ["布局属性不匹配："]
    
    for mismatch in mismatches[:5]:
        parts.append(f"  - {mismatch}")
    
    parts.append("\n建议检查 display/flex/grid/overflow 等布局属性")
    
    return "\n".join(parts)
```

---

## 第3/5 部分完整结论

| 问题 | GPT 方案 | Opus 方案 |
|---|---|---|
| 主评分指标 | SSIM + 感知哈希 | 五维度独立评分（IoU + Delta-E + Computed Style） |
| 阈值策略 | 固定 0.97 | 按区域类型和阶段动态调整（0.88-0.99） |
| 评分输出 | 数字 | 可操作诊断文本 + 优先级建议 |
| 颜色评估 | RGB 差值 | LAB Delta-E（符合人眼感知） |
| 几何评估 | SSIM（对1px过敏） | IoU（容忍人眼不可见偏差） |

---

**第4/5 部分预告**：Worker 模型的 Prompt 工程、补丁生成的约束系统、以及如何防止Worker "用hardcode 数字快速通过评分"这种作弊行为。

# 第4/5 部分：Worker 模型的 Prompt 工程与补丁约束系统

> **第3部分回顾**：已完成五维度评分系统，解决了SSIM对UI还原的系统性失准问题。
>
> **第4部分核心分歧**：GPT 用通用 Prompt 让模型"根据评分结果修复"。我认为这种 Prompt 会导致 Worker 用 hardcode 数字快速通过评分（作弊行为）。正确的做法是**用约束系统把作弊路径全部堵死，只留下正确的修复路径**。

---

## 一、Worker 作弊行为的四种典型模式

```text
模式1：Hardcode 精确数值
  评分说"宽度偏大8px"
  Worker 直接写 width: 342px（原型宽度350px - 8px）
  下次迭代评分说"宽度偏小3px"
  Worker 再写 width: 345px
  → 最终收敛到精确数值，但完全没用 Token

模式2：局部 !important 强制通过
  评分说"颜色不对"
  Worker 加 background-color: #F5F7FA !important;
  → 评分通过，但破坏了全局 Token 体系

模式3：绝对定位绕过布局问题
  评分说"元素位置偏右20px"
  Worker 改成 position: absolute; left: 100px;
  → 评分通过，但在响应式布局下崩溃

模式4：复制原型的 inline style
  Worker 直接从原型截图的 DOM snapshot 中复制 style 属性
  → 评分高分，但完全未使用项目的组件和样式系统
```

这四种行为在传统"根据反馈修复"的 Prompt 下**极其常见**，因为模型的目标函数是"让评分通过"，而不是"正确还原"。

---

## 二、约束系统：在 Prompt 层面堵死作弊路径

```python
# scripts/ui_autopilot/worker/constraints.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ViolationType(StrEnum):
    HARDCODE_PX = "hardcode_px"
    HARDCODE_COLOR = "hardcode_color"
    IMPORTANT_ABUSE = "important_abuse"
    ABSOLUTE_POSITION = "absolute_position"
    INLINE_STYLE = "inline_style"
    GLOBAL_SELECTOR = "global_selector"
    ANTD_OVERRIDE = "antd_override"
    MAGIC_NUMBER = "magic_number"
    NON_TOKEN_VALUE = "non_token_value"


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    type: ViolationType
    file: str
    line: int | None
    snippet: str
    severity: str  # 'error' | 'warning'
    explanation: str
    suggested_fix: str


@dataclass(slots=True)
class PatchConstraints:
    """
    Worker 生成的补丁必须通过的约束检查。
    
    与 GPT 方案的区别：
    GPT 只有"不要用 hardcode"这种软性建议。
    这里是硬性检查，违反直接拒绝补丁并重新生成。
    """
    
    # 禁止模式（正则）
    forbidden_patterns: dict[str, str] = field(default_factory=dict)
    
    # 必需模式（至少一个匹配）
    required_patterns: list[str] = field(default_factory=list)
    
    # Token 白名单（修改值必须来自此列表或 Token 变量）
    allowed_tokens: set[str] = field(default_factory=set)
    
    # 允许修改的文件白名单
    allowed_files: set[str] = field(default_factory=set)
    
    # 禁止修改的文件黑名单
    forbidden_files: set[str] = field(default_factory=set)
    
    # 允许的 CSS 属性（在特定阶段限制修改范围）
    allowed_properties: set[str] | None = None
    
    # 最大改动行数（防止大范围重构）
    max_changed_lines: int = 50
    
    # 是否允许新增文件
    allow_new_files: bool = False
    
    # 是否允许删除文件
    allow_delete_files: bool = False

    def __post_init__(self) -> None:
        # 默认禁止模式
        if not self.forbidden_patterns:
            self.forbidden_patterns = {
                # 禁止裸 px 数值（必须用 Token 或计算）
                r'\b(width|height|margin|padding|top|left|right|bottom|font-size):\s*\d+px\s*;': 
                    'hardcode_px',
                
                # 禁止裸色值（必须用 Token）
                r'(color|background|border-color):\s*#[0-9a-fA-F]{3,6}\s*;':
                    'hardcode_color',
                r'(color|background|border-color):\s*rgb\([^)]+\)\s*;':
                    'hardcode_color',
                
                # 禁止 !important
                r'!important':
                    'important_abuse',
                
                # 禁止绝对定位（除非明确允许）
                r'position:\s*absolute':
                    'absolute_position',
                
                # 禁止 :global
                r':global':
                    'global_selector',
                
                # 禁止直接覆盖 Ant Design 内部类
                r'\.ant-[a-z-]+\s*\{':
                    'antd_override',
            }


class ConstraintChecker:
    """
    检查 Worker 生成的补丁是否违反约束。
    """
    
    def __init__(self, constraints: PatchConstraints) -> None:
        self.constraints = constraints
    
    def check_patch(
        self,
        changed_files: dict[str, str],  # file_path → new_content
        diff: str,
    ) -> list[ConstraintViolation]:
        """
        对补丁进行全面约束检查。
        返回所有违规项，任何 error 级别违规都会导致补丁被拒绝。
        """
        violations: list[ConstraintViolation] = []
        
        for file_path, new_content in changed_files.items():
            # 检查文件白名单
            if self.constraints.allowed_files:
                if file_path not in self.constraints.allowed_files:
                    violations.append(ConstraintViolation(
                        type=ViolationType.INLINE_STYLE,
                        file=file_path,
                        line=None,
                        snippet='',
                        severity='error',
                        explanation=f'不允许修改此文件（不在白名单中）',
                        suggested_fix='只修改任务明确允许的文件',
                    ))
                    continue
            
            # 检查文件黑名单
            if file_path in self.constraints.forbidden_files:
                violations.append(ConstraintViolation(
                    type=ViolationType.INLINE_STYLE,
                    file=file_path,
                    line=None,
                    snippet='',
                    severity='error',
                    explanation=f'禁止修改此文件（Token 生成文件）',
                    suggested_fix='修改 Token 源文件，而不是生成文件',
                ))
                continue
            
            # 逐行检查禁止模式
            lines = new_content.splitlines()
            for line_num, line in enumerate(lines, start=1):
                for pattern, violation_type in self.constraints.forbidden_patterns.items():
                    import re
                    if re.search(pattern, line):
                        violations.append(self._create_violation(
                            violation_type,
                            file_path,
                            line_num,
                            line.strip(),
                        ))
        
        # 检查改动行数
        changed_lines = self._count_changed_lines(diff)
        if changed_lines > self.constraints.max_changed_lines:
            violations.append(ConstraintViolation(
                type=ViolationType.MAGIC_NUMBER,
                file='<全局>',
                line=None,
                snippet='',
                severity='error',
                explanation=(
                    f'改动行数 {changed_lines} 超过限制 '
                    f'{self.constraints.max_changed_lines}。'
                    f'单次补丁应该是局部精确修复，不应大范围重构。'
                ),
                suggested_fix='缩小修改范围，只改当前任务相关的代码',
            ))
        
        return violations
    
    def _create_violation(
        self,
        type_str: str,
        file: str,
        line: int,
        snippet: str,
    ) -> ConstraintViolation:
        """
        根据违规类型生成详细的违规报告。
        """
        type_enum = ViolationType(type_str)
        
        explanations = {
            ViolationType.HARDCODE_PX: (
                '禁止使用裸 px 数值。必须使用 Token 变量或 calc() 计算。'
            ),
            ViolationType.HARDCODE_COLOR: (
                '禁止使用裸色值。必须使用 Token 变量（var(--ui-xxx)）。'
            ),
            ViolationType.IMPORTANT_ABUSE: (
                '禁止使用 !important。这会破坏样式优先级体系。'
            ),
            ViolationType.ABSOLUTE_POSITION: (
                '禁止使用 position: absolute 绕过布局问题。'
                '应该修复 flex/grid 布局本身。'
            ),
            ViolationType.GLOBAL_SELECTOR: (
                '禁止使用 :global 选择器。应该用 CSS Modules 局部作用域。'
            ),
            ViolationType.ANTD_OVERRIDE: (
                '禁止直接覆盖 Ant Design 内部类名。'
                '应该用 Ant Design 的 ConfigProvider 或组件 props。'
            ),
        }
        
        fixes = {
            ViolationType.HARDCODE_PX: (
                '查找 src/styles/tokens/ 中是否有对应的间距 Token。'
                '如果没有，在任务报告中建议新增 Token，而不是用裸值。'
            ),
            ViolationType.HARDCODE_COLOR: (
                '查找 src/styles/tokens/_colors.scss 中最接近的颜色 Token。'
            ),
            ViolationType.IMPORTANT_ABUSE: (
                '提高选择器优先级（如：.parent .child）而不是用 !important。'
            ),
            ViolationType.ABSOLUTE_POSITION: (
                '用 margin/padding/flex/grid 属性调整位置。'
            ),
            ViolationType.GLOBAL_SELECTOR: (
                '使用 CSS Modules 的 :local 作用域（默认）。'
            ),
            ViolationType.ANTD_OVERRIDE: (
                '用 ConfigProvider 的 theme.components 配置覆盖样式。'
            ),
        }
        
        return ConstraintViolation(
            type=type_enum,
            file=file,
            line=line,
            snippet=snippet,
            severity='error',
            explanation=explanations.get(type_enum, '违反约束'),
            suggested_fix=fixes.get(type_enum, '请参考约束文档'),
        )
    
    @staticmethod
    def _count_changed_lines(diff: str) -> int:
        """
        从 unified diff 计算实际改动行数（不含上下文）。
        """
        import re
        changed = 0
        for line in diff.splitlines():
            if re.match(r'^[+-](?![+-])', line):
                changed += 1
        return changed
```

---

## 三、Worker Prompt 的三层结构

与 GPT 的通用 Prompt 不同，我的 Worker Prompt 分三层：

```text
Layer 1：任务上下文（what to fix）
  → 目标区域、根因诊断、量化偏差

Layer 2：约束系统（how NOT to fix）
  → 禁止模式、允许文件、Token 白名单

Layer 3：修复策略库（how to fix correctly）
  → 针对不同根因的标准修复模板
```

```python
# scripts/ui_autopilot/worker/prompt_builder.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..scoring.multi_dim_scorer import CompositeScore
from ..visual.evidence_builder import ActionableEvidence
from .constraints import PatchConstraints


@dataclass(frozen=True, slots=True)
class WorkerPrompt:
    task_context: str
    constraints: str
    repair_strategies: str
    output_format: str
    
    def render(self) -> str:
        return f"""# UI 还原修复任务

{self.task_context}

---

## 约束系统（硬性要求，违反则补丁无效）

{self.constraints}

---

## 修复策略库

{self.repair_strategies}

---

## 输出格式

{self.output_format}
"""


class PromptBuilder:
    """
    构建 Worker 模型的 Prompt，强制其遵守约束。
    """
    
    def build(
        self,
        task_id: str,
        target_id: str,
        evidence: ActionableEvidence,
        score: CompositeScore,
        constraints: PatchConstraints,
        phase: str,
    ) -> WorkerPrompt:
        
        task_context = self._build_task_context(
            task_id, target_id, evidence, score, phase,
        )
        
        constraints_text = self._build_constraints(constraints)
        
        strategies = self._build_repair_strategies(
            score, evidence, phase,
        )
        
        output_format = self._build_output_format()
        
        return WorkerPrompt(
            task_context=task_context,
            constraints=constraints_text,
            repair_strategies=strategies,
            output_format=output_format,
        )
    
    def _build_task_context(
        self,
        task_id: str,
        target_id: str,
        evidence: ActionableEvidence,
        score: CompositeScore,
        phase: str,
    ) -> str:
        lines = [
            f"**任务 ID**: {task_id}",
            f"**目标区域**: {target_id}",
            f"**修复阶段**: {phase}",
            f"**当前评分**: {score.total:.3f}（阈值 {score.threshold}）",
            "",
            "## 量化偏差",
            "",
        ]
        
        # 几何偏差
        if evidence.geometry_delta:
            gd = evidence.geometry_delta
            lines.append(f"**几何**:")
            lines.append(f"  - 宽度偏差: {gd.get('widthDelta', 0):.1f}px")
            lines.append(f"  - 高度偏差: {gd.get('heightDelta', 0):.1f}px")
            lines.append(f"  - 水平位置偏差: {gd.get('xDelta', 0):.1f}px")
            lines.append(f"  - 垂直位置偏差: {gd.get('yDelta', 0):.1f}px")
            lines.append("")
        
        # 样式偏差
        if evidence.style_deltas:
            lines.append("**样式偏差**:")
            for delta in evidence.style_deltas[:5]:
                lines.append(
                    f"  - `{delta.property_name}`: "
                    f"期望 `{delta.expected}`, 实际 `{delta.actual}` "
                    f"({delta.delta_description})"
                )
                if delta.token_candidate:
                    lines.append(f"    → 建议Token: `{delta.token_candidate}`")
            lines.append("")
        
        # 代码定位
        if evidence.probable_source_files:
            lines.append("## 最可能的源文件位置")
            lines.append("")
            for i, hit in enumerate(evidence.probable_source_files[:3], 1):
                lines.append(
                    f"{i}. `{hit.file}`{f':{hit.line}' if hit.line else ''}"
                )
                lines.append(f"   - 选择器: `{hit.selector}`")
                lines.append(f"   - 属性: `{hit.property_name}`")
                lines.append(f"   - 当前值: `{hit.declared_value}`")
                lines.append(f"   - 置信度: {hit.confidence:.0%}")
                lines.append("")
        
        # 历史失败
        if evidence.previous_attempts:
            lines.append("## 历史尝试（避免重复）")
            lines.append("")
            for attempt in evidence.previous_attempts:
                status = "✓ 接受" if attempt.was_accepted else "✗ 拒绝"
                lines.append(
                    f"- 第{attempt.attempt_number}次: {attempt.patch_description} "
                    f"({status}, 分数 {attempt.score_before:.3f}→{attempt.score_after:.3f})"
                )
                if not attempt.was_accepted and attempt.failure_reason:
                    lines.append(f"  失败原因: {attempt.failure_reason}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_constraints(self, constraints: PatchConstraints) -> str:
        lines = [
            "### 1. 禁止使用裸数值",
            "",
            "- ❌ `width: 240px;`",
            "- ✅ `width: var(--ui-spacing-60);`",
            "- ✅ `width: calc(var(--ui-spacing-base) * 15);`",
            "",
            "### 2. 禁止使用裸色值",
            "",
            "- ❌ `background: #F5F7FA;`",
            "- ❌ `color: rgb(51, 51, 51);`",
            "- ✅ `background: var(--ui-bg-secondary);`",
            "",
            "### 3. 禁止使用 !important",
            "",
            "- ❌ `margin: 0 !important;`",
            "- ✅ 提高选择器优先级：`.container .button { margin: 0; }`",
            "",
            "### 4. 禁止使用绝对定位绕过布局",
            "",
            "- ❌ `position: absolute; left: 120px;`",
            "- ✅ 修复 flex/grid 布局本身",
            "",
            "### 5. 禁止使用 :global 选择器",
            "",
            "- ❌ `:global(.ant-btn) { ... }`",
            "- ✅ 使用 CSS Modules 局部作用域",
            "",
            "### 6. 禁止直接覆盖 Ant Design 内部类",
            "",
            "- ❌ `.ant-modal-content { padding: 20px; }`",
            "- ✅ 用 ConfigProvider 或组件 props",
            "",
            "### 7. 允许修改的文件",
            "",
        ]
        
        if constraints.allowed_files:
            for file in sorted(constraints.allowed_files):
                lines.append(f"- `{file}`")
        else:
            lines.append("- （未限制）")
        
        lines.append("")
        lines.append("### 8. 禁止修改的文件")
        lines.append("")
        
        if constraints.forbidden_files:
            for file in sorted(constraints.forbidden_files):
                lines.append(f"- `{file}` ← Token 生成文件，不可手动改")
        
        lines.extend([
            "",
            f"### 9. 最大改动行数: {constraints.max_changed_lines}",
            "",
            "单次补丁应该是**局部精确修复**，不应大范围重构。",
            "",
        ])
        
        return "\n".join(lines)
    
    def _build_repair_strategies(
        self,
        score: CompositeScore,
        evidence: ActionableEvidence,
        phase: str,
    ) -> str:
        """
        根据失败维度，提供针对性的修复模板。
        """
        lines = []
        
        failing_dims = [
            d for d in score.dimensions
            if d.score < score.threshold
        ]
        
        if not failing_dims:
            return "（所有维度通过，无需修复）"
        
        for dim in failing_dims[:2]:  # 最多展示2个
            if dim.name == "geometry":
                lines.extend(self._strategy_geometry(evidence))
            elif dim.name == "color":
                lines.extend(self._strategy_color(evidence))
            elif dim.name == "typography":
                lines.extend(self._strategy_typography(evidence))
            elif dim.name == "decoration":
                lines.extend(self._strategy_decoration(evidence))
            elif dim.name == "layout":
                lines.extend(self._strategy_layout(evidence))
        
        return "\n".join(lines)
    
    def _strategy_geometry(self, evidence: ActionableEvidence) -> list[str]:
        return [
            "### 几何偏差修复策略",
            "",
            "1. **检查盒模型**: `box-sizing: border-box` vs `content-box`",
            "2. **检查 flex 收缩**: `flex-shrink: 0` 防止意外收缩",
            "3. **检查最小尺寸**: `min-width` / `min-height`",
            "4. **检查父容器**: 父元素的 `gap` / `padding` 影响",
            "5. **检查 Token 映射**: 当前 spacing Token 是否对应原型值",
            "",
            "**模板**:",
            "```scss",
            ".target {",
            "  width: var(--ui-width-xxx);        // 从 Token 查",
            "  padding: var(--ui-spacing-4);      // 不用裸值",
            "  box-sizing: border-box;            // 明确盒模型",
            "}",
            "```",
            "",
        ]
    
    def _strategy_color(self, evidence: ActionableEvidence) -> list[str]:
        return [
            "### 颜色偏差修复策略",
            "",
            "1. **查 Token 库**: 在 `src/styles/tokens/_colors.scss` 中搜索接近色值",
            "2. **检查语义映射**: 如 `--ui-text-primary` 是否映射到正确的基础色",
            "3. **检查 Ant Design 主题**: 是否需要在 ConfigProvider 中覆盖",
            "4. **检查透明度**: `rgba` 的 alpha 值差异",
            "",
            "**模板**:",
            "```scss",
            ".target {",
            "  color: var(--ui-text-primary);",
            "  background-color: var(--ui-bg-secondary);",
            "  border-color: var(--ui-border-default);",
            "}",
            "```",
            "",
        ]
    
    def _strategy_typography(self, evidence: ActionableEvidence) -> list[str]:
        return [
            "### 排版偏差修复策略",
            "",
            "1. **查 Token 库**: `src/styles/tokens/_typography.scss`",
            "2. **检查字重映射**: `font-weight: 500` vs `600` vs `700`",
            "3. **检查行高单位**: 裸数字（如 `1.5`）vs `px` vs `%`",
            "4. **检查 Ant Design 覆盖**: `ConfigProvider.theme.token`",
            "",
            "**模板**:",
            "```scss",
            ".target {",
            "  font-size: var(--ui-font-size-base);",
            "  font-weight: var(--ui-font-weight-medium);",
            "  line-height: var(--ui-line-height-normal);",
            "}",
            "```",
            "",
        ]
    
    def _strategy_decoration(self, evidence: ActionableEvidence) -> list[str]:
        return [
            "### 装饰偏差修复策略",
            "",
            "1. **圆角**: 用 Token `--ui-radius-sm` / `--ui-radius-md` / `--ui-radius-lg`",
            "2. **阴影**: 用 Token `--ui-shadow-sm` / `--ui-shadow-md` / `--ui-shadow-lg`",
            "3. **边框**: 用 Token `--ui-border-width` + `--ui-border-color-xxx`",
            "",
            "**模板**:",
            "```scss",
            ".target {",
            "  border-radius: var(--ui-radius-md);",
            "  box-shadow: var(--ui-shadow-sm);",
            "  border: var(--ui-border-width) solid var(--ui-border-default);",
            "}",
            "```",
            "",
        ]
    
    def _strategy_layout(self, evidence: ActionableEvidence) -> list[str]:
        return [
            "### 布局偏差修复策略",
            "",
            "1. **检查 flex 对齐**: `justify-content` / `align-items`",
            "2. **检查 gap**: flex/grid 的 `gap` 属性",
            "3. **检查 overflow**: 内容溢出时的滚动行为",
            "4. **检查子元素 flex**: `flex-grow` / `flex-shrink` / `flex-basis`",
            "",
            "**模板**:",
            "```scss",
            ".container {",
            "  display: flex;",
            "  gap: var(--ui-spacing-4);",
            "  justify-content: space-between;",
            "  align-items: center;",
            "}",
            "```",
            "",
        ]
    
    def _build_output_format(self) -> str:
        return """请以 JSON 格式输出修复方案：

```json
{
  "diagnosis": "一句话根因总结",
  "changed_files": [
    {
      "file": "src/features/Dashboard/Header.module.scss",
      "changes": [
        {
          "line": 42,
          "before": "padding: 12px 24px;",
          "after": "padding: var(--ui-spacing-3) var(--ui-spacing-6);",
          "reason": "使用 Token 替换裸值"
        }
      ]
    }
  ],
  "token_usage": [
    {
      "token": "var(--ui-spacing-3)",
      "value": "12px",
      "source": "src/styles/tokens/_spacing.scss"
    }
  ],
  "risks": [
    "可能影响相邻元素的间距"
  ],
  "test_plan": "重新截图验证 padding 是否符合原型"
}
```

**关键要求**:
1. `changed_files` 必须明确指出修改的文件、行号、修改前后内容
2. `token_usage` 必须列出所有使用的 Token 及其来源
3. 不允许输出任何违反约束的代码
4. 如果无法在约束内修复，明确说明并建议调整 Token 或约束
"""
```

---

## 四、补丁验证器：应用前的最后一道防线

Worker 生成的补丁在实际应用前，必须通过验证器：

```python
# scripts/ui_autopilot/worker/patch_validator.py

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constraints import ConstraintChecker, ConstraintViolation, PatchConstraints


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    violations: list[ConstraintViolation]
    lint_errors: list[str]
    type_errors: list[str]
    build_errors: list[str]
    rejection_reason: str | None


class PatchValidator:
    """
    在应用补丁前验证其合法性。
    
    验证层级（任一失败则拒绝）：
    1. 约束检查（禁止模式、文件白名单）
    2. Lint 检查（ESLint / Stylelint）
    3. 类型检查（TypeScript）
    4. 构建检查（能否成功编译）
    """
    
    def __init__(
        self,
        project_root: Path,
        constraints: PatchConstraints,
    ) -> None:
        self.project_root = project_root
        self.constraint_checker = ConstraintChecker(constraints)
    
    def validate(
        self,
        patch_json: dict[str, Any],
    ) -> ValidationResult:
        """
        完整验证流程。
        """
        # 提取改动文件
        changed_files = self._extract_changes(patch_json)
        
        if not changed_files:
            return ValidationResult(
                valid=False,
                violations=[],
                lint_errors=[],
                type_errors=[],
                build_errors=[],
                rejection_reason


# 第4/5 部分续完 + 第5/5 部分

接上文 `PatchValidator.validate` 中断处，补全验证器并完成整个系统：

```python
    def validate(
        self,
        patch_json: dict[str, Any],
    ) -> ValidationResult:
        """
        完整验证流程。
        """
        # 提取改动文件
        changed_files = self._extract_changes(patch_json)
        
        if not changed_files:
            return ValidationResult(
                valid=False,
                violations=[],
                lint_errors=[],
                type_errors=[],
                build_errors=[],
                rejection_reason="补丁未包含任何文件改动",
            )
        
        # 第1层：约束检查
        diff_str = self._build_diff_string(patch_json)
        constraint_violations = self.constraint_checker.check_patch(
            changed_files, diff_str,
        )
        
        if any(v.severity == 'error' for v in constraint_violations):
            return ValidationResult(
                valid=False,
                violations=constraint_violations,
                lint_errors=[],
                type_errors=[],
                build_errors=[],
                rejection_reason=(
                    f"约束检查失败：{len(constraint_violations)} 个错误"
                ),
            )
        
        # 第2层：Lint 检查
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 写入临时文件
            for file_path, content in changed_files.items():
                full_path = tmpdir_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            lint_errors = self._run_lint(tmpdir_path, changed_files.keys())
            
            if lint_errors:
                return ValidationResult(
                    valid=False,
                    violations=constraint_violations,
                    lint_errors=lint_errors,
                    type_errors=[],
                    build_errors=[],
                    rejection_reason=(
                        f"Lint 检查失败：{len(lint_errors)} 个错误"
                    ),
                )
            
            # 第3层：类型检查
            type_errors = self._run_type_check(tmpdir_path)
            
            if type_errors:
                return ValidationResult(
                    valid=False,
                    violations=constraint_violations,
                    lint_errors=lint_errors,
                    type_errors=type_errors,
                    build_errors=[],
                    rejection_reason=(
                        f"类型检查失败：{len(type_errors)} 个错误"
                    ),
                )
            
            # 第4层：构建检查
            build_errors = self._run_build(tmpdir_path)
            
            if build_errors:
                return ValidationResult(
                    valid=False,
                    violations=constraint_violations,
                    lint_errors=lint_errors,
                    type_errors=type_errors,
                    build_errors=build_errors,
                    rejection_reason=(
                        f"构建检查失败：{len(build_errors)} 个错误"
                    ),
                )
        
        # 全部通过
        return ValidationResult(
            valid=True,
            violations=constraint_violations,  # warning 级别的
            lint_errors=[],
            type_errors=[],
            build_errors=[],
            rejection_reason=None,
        )
    
    def _extract_changes(
        self,
        patch_json: dict[str, Any],
    ) -> dict[str, str]:
        """
        从 Worker 输出的 JSON 中提取改动文件。
        """
        changed_files: dict[str, str] = {}
        
        for file_change in patch_json.get('changed_files', []):
            file_path = file_change.get('file')
            
            if not file_path:
                continue
            
            # 读取原始文件
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            original_content = full_path.read_text()
            
            # 应用改动
            modified_content = self._apply_changes(
                original_content,
                file_change.get('changes', []),
            )
            
            changed_files[file_path] = modified_content
        
        return changed_files
    
    def _apply_changes(
        self,
        original: str,
        changes: list[dict[str, Any]],
    ) -> str:
        """
        将改动列表应用到原始文件内容。
        """
        lines = original.splitlines(keepends=True)
        
        # 按行号倒序排列，避免行号偏移
        sorted_changes = sorted(
            changes,
            key=lambda c: c.get('line', 0),
            reverse=True,
        )
        
        for change in sorted_changes:
            line_num = change.get('line')
            before = change.get('before', '')
            after = change.get('after', '')
            
            if line_num is None or line_num < 1:
                continue
            
            # 行号从1开始，列表从0开始
            idx = line_num - 1
            
            if idx < len(lines):
                # 验证 before 匹配
                if lines[idx].rstrip('\n') == before.rstrip('\n'):
                    lines[idx] = after + '\n'
        
        return ''.join(lines)
    
    def _build_diff_string(self, patch_json: dict[str, Any]) -> str:
        """
        从 patch JSON 构建 unified diff 格式字符串。
        """
        lines = []
        
        for file_change in patch_json.get('changed_files', []):
            file_path = file_change.get('file', '')
            lines.append(f"--- a/{file_path}")
            lines.append(f"+++ b/{file_path}")
            
            for change in file_change.get('changes', []):
                before = change.get('before', '')
                after = change.get('after', '')
                
                if before:
                    lines.append(f"-{before}")
                if after:
                    lines.append(f"+{after}")
        
        return '\n'.join(lines)
    
    def _run_lint(
        self,
        tmpdir: Path,
        files: list[str],
    ) -> list[str]:
        """
        运行 ESLint / Stylelint。
        """
        errors = []
        
        # ESLint for .ts/.tsx/.js
        ts_files = [f for f in files if f.endswith(('.ts', '.tsx', '.js'))]
        
        if ts_files:
            try:
                result = subprocess.run(
                    ['npx', 'eslint', '--max-warnings', '0'] + ts_files,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                if result.returncode != 0:
                    errors.extend(result.stdout.splitlines())
            except Exception as e:
                errors.append(f"ESLint 执行失败: {e}")
        
        # Stylelint for .scss/.css
        style_files = [f for f in files if f.endswith(('.scss', '.css'))]
        
        if style_files:
            try:
                result = subprocess.run(
                    ['npx', 'stylelint'] + style_files,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                if result.returncode != 0:
                    errors.extend(result.stdout.splitlines())
            except Exception as e:
                errors.append(f"Stylelint 执行失败: {e}")
        
        return errors
    
    def _run_type_check(self, tmpdir: Path) -> list[str]:
        """
        运行 TypeScript 类型检查。
        """
        try:
            result = subprocess.run(
                ['npx', 'tsc', '--noEmit'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                return result.stdout.splitlines()
        except Exception as e:
            return [f"TypeScript 检查失败: {e}"]
        
        return []
    
    def _run_build(self, tmpdir: Path) -> list[str]:
        """
        运行构建检查。
        """
        try:
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                return result.stdout.splitlines() + result.stderr.splitlines()
        except Exception as e:
            return [f"构建失败: {e}"]
        
        return []
```

---

# 第5/5 部分：完整的 Loop 编排与防作弊机制

> **最后一层防线**：即使 Worker 通过了所有验证，还要防止它在多轮迭代中"学会作弊"。

---

## 一、Loop 的完整编排

```python
# scripts/ui_autopilot/loop/orchestrator.py

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..discovery.state_script import StateScript
from ..scoring.multi_dim_scorer import CompositeScore, MultiDimScorer
from ..visual.evidence_builder import ActionableEvidence
from ..worker.constraints import PatchConstraints
from ..worker.patch_validator import PatchValidator, ValidationResult
from ..worker.prompt_builder import PromptBuilder, WorkerPrompt


class LoopPhase(StrEnum):
    DISCOVERY = "discovery"        # 第1阶段：状态采集
    SHELL_REPAIR = "shell_repair"  # 第2阶段：页面骨架修复
    REGION_REPAIR = "region_repair"# 第3阶段：区域修复
    ELEMENT_REPAIR = "element_repair"  # 第4阶段：元素修复
    POLISH = "polish"              # 第5阶段：精修
    COMPLETE = "complete"          # 完成


@dataclass(slots=True)
class LoopIteration:
    iteration_num: int
    phase: LoopPhase
    target_id: str
    state_id: str
    
    prompt: WorkerPrompt | None = None
    worker_response: dict[str, Any] | None = None
    validation_result: ValidationResult | None = None
    patch_applied: bool = False
    score_before: float = 0.0
    score_after: float = 0.0
    
    # 防作弊指标
    hardcode_score_improvement: float = 0.0
    token_usage_ratio: float = 0.0
    constraint_violations: int = 0
    
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LoopState:
    """
    整个 Loop 的全局状态。
    """
    task_id: str
    page_id: str
    state_id: str
    
    iterations: list[LoopIteration] = field(default_factory=list)
    current_phase: LoopPhase = LoopPhase.DISCOVERY
    
    # 防作弊：历史尝试记录
    attempted_patches: dict[str, int] = field(default_factory=dict)
    
    # 防作弊：Worker 的"作弊倾向"评分
    worker_cheat_score: float = 0.0
    
    # 防作弊：是否检测到作弊行为
    cheat_detected: bool = False
    cheat_evidence: list[str] = field(default_factory=list)


class LoopOrchestrator:
    """
    UI 还原 Loop 的完整编排器。
    
    核心职责：
    1. 按阶段驱动修复（Shell → Region → Element → Polish）
    2. 每轮迭代后评分，决定是否进入下一阶段
    3. 检测 Worker 的作弊行为，并动态调整约束
    4. 记录完整的修复历史，用于事后审计
    """
    
    # 各阶段的通过阈值
    PHASE_THRESHOLDS = {
        LoopPhase.SHELL_REPAIR: 0.90,
        LoopPhase.REGION_REPAIR: 0.93,
        LoopPhase.ELEMENT_REPAIR: 0.96,
        LoopPhase.POLISH: 0.98,
    }
    
    # 最大迭代次数（防止无限循环）
    MAX_ITERATIONS_PER_PHASE = 5
    
    def __init__(
        self,
        project_root: Path,
        scorer: MultiDimScorer,
        validator: PatchValidator,
        prompt_builder: PromptBuilder,
        worker_model_fn,  # async fn(prompt: str) -> dict
    ) -> None:
        self.project_root = project_root
        self.scorer = scorer
        self.validator = validator
        self.prompt_builder = prompt_builder
        self.worker_model_fn = worker_model_fn
    
    async def run_loop(
        self,
        task_id: str,
        page_id: str,
        state_id: str,
        prototype_screenshot: Path,
        actual_screenshot: Path,
        prototype_styles: dict[str, str],
        actual_styles: dict[str, str],
        constraints: PatchConstraints,
    ) -> LoopState:
        """
        运行完整的修复 Loop。
        """
        loop_state = LoopState(
            task_id=task_id,
            page_id=page_id,
            state_id=state_id,
        )
        
        # 初始评分
        from PIL import Image
        proto_img = Image.open(prototype_screenshot)
        actual_img = Image.open(actual_screenshot)
        
        initial_score = self.scorer.score(
            proto_img, actual_img,
            prototype_styles, actual_styles,
            {}, {},  # box 信息暂略
            target_id=f"{page_id}/{state_id}",
            state_id=state_id,
        )
        
        print(f"[初始评分] {initial_score.total:.3f}")
        
        # 按阶段循环
        for phase in [
            LoopPhase.SHELL_REPAIR,
            LoopPhase.REGION_REPAIR,
            LoopPhase.ELEMENT_REPAIR,
            LoopPhase.POLISH,
        ]:
            loop_state.current_phase = phase
            threshold = self.PHASE_THRESHOLDS[phase]
            
            # 该阶段的最大迭代次数
            for iter_num in range(1, self.MAX_ITERATIONS_PER_PHASE + 1):
                # 检查是否已通过
                if initial_score.total >= threshold:
                    print(f"[{phase}] 已通过阈值 {threshold}，跳过")
                    break
                
                # 执行一次迭代
                iteration = await self._run_iteration(
                    loop_state,
                    iter_num,
                    phase,
                    initial_score,
                    constraints,
                    proto_img,
                    actual_img,
                    prototype_styles,
                    actual_styles,
                )
                
                loop_state.iterations.append(iteration)
                
                # 检测作弊
                if self._detect_cheat(loop_state, iteration):
                    loop_state.cheat_detected = True
                    print(f"[警告] 检测到可能的作弊行为")
                    break
                
                # 更新评分
                if iteration.patch_applied:
                    initial_score = CompositeScore.from_dimensions(
                        target_id=initial_score.target_id,
                        state_id=initial_score.state_id,
                        dimensions=iteration.metadata.get('new_dimensions', []),
                        threshold=initial_score.threshold,
                    )
                    print(
                        f"[{phase} #{iter_num}] "
                        f"评分: {iteration.score_before:.3f} → {iteration.score_after:.3f}"
                    )
                
                if initial_score.total >= threshold:
                    print(f"[{phase}] 通过阈值 {threshold}")
                    break
        
        loop_state.current_phase = LoopPhase.COMPLETE
        return loop_state
    
    async def _run_iteration(
        self,
        loop_state: LoopState,
        iter_num: int,
        phase: LoopPhase,
        current_score: CompositeScore,
        constraints: PatchConstraints,
        proto_img,
        actual_img,
        proto_styles: dict[str, str],
        actual_styles: dict[str, str],
    ) -> LoopIteration:
        """
        执行单次迭代。
        """
        iteration = LoopIteration(
            iteration_num=iter_num,
            phase=phase,
            target_id=f"{loop_state.page_id}/{loop_state.state_id}",
            state_id=loop_state.state_id,
            score_before=current_score.total,
        )
        
        # Step 1：生成 Prompt
        evidence = self._build_evidence(current_score)
        
        prompt = self.prompt_builder.build(
            task_id=loop_state.task_id,
            target_id=iteration.target_id,
            evidence=evidence,
            score=current_score,
            constraints=constraints,
            phase=phase.value,
        )
        
        iteration.prompt = prompt
        
        # Step 2：调用 Worker 模型
        try:
            worker_response = await self.worker_model_fn(prompt.render())
            iteration.worker_response = worker_response
        except Exception as e:
            print(f"[错误] Worker 模型调用失败: {e}")
            return iteration
        
        # Step 3：验证补丁
        validation = self.validator.validate(worker_response)
        iteration.validation_result = validation
        
        if not validation.valid:
            print(f"[验证失败] {validation.rejection_reason}")
            iteration.constraint_violations = len(validation.violations)
            return iteration
        
        # Step 4：应用补丁
        try:
            self._apply_patch(worker_response)
            iteration.patch_applied = True
        except Exception as e:
            print(f"[应用失败] {e}")
            return iteration
        
        # Step 5：重新评分
        new_score = self.scorer.score(
            proto_img, actual_img,
            proto_styles, actual_styles,
            {}, {},
            target_id=iteration.target_id,
            state_id=loop_state.state_id,
        )
        
        iteration.score_after = new_score.total
        iteration.metadata['new_dimensions'] = new_score.dimensions
        
        # Step 6：计算防作弊指标
        iteration.hardcode_score_improvement = (
            iteration.score_after - iteration.score_before
        )
        
        token_count = len(
            worker_response.get('token_usage', [])
        )
        iteration.token_usage_ratio = (
            token_count / len(worker_response.get('changed_files', [])) 
            if worker_response.get('changed_files') else 0
        )
        
        return iteration
    
    def _detect_cheat(
        self,
        loop_state: LoopState,
        iteration: LoopIteration,
    ) -> bool:
        """
        检测 Worker 的作弊行为。
        """
        cheat_signals = []
        
        # 信号1：连续高分提升，但没用 Token
        if (
            iteration.hardcode_score_improvement > 0.08
            and iteration.token_usage_ratio < 0.5
        ):
            cheat_signals.append(
                f"高分提升 {iteration.hardcode_score_improvement:.3f} "
                f"但 Token 使用率仅 {iteration.token_usage_ratio:.1%}"
            )
        
        # 信号2：改动行数远少于改动文件数（可能是 hardcode）
        changed_files_count = len(
            iteration.worker_response.get('changed_files', [])
        )
        total_changed_lines = sum(
            len(f.get('changes', []))
            for f in iteration.worker_response.get('changed_files', [])
        )
        
        if changed_files_count > 0 and total_changed_lines < changed_files_count:
            cheat_signals.append(
                f"改动文件数 {changed_files_count} "
                f"但改动行数仅 {total_changed_lines}"
            )
        
        # 信号3：同一补丁被重复提交
        patch_hash = self._hash_patch(iteration.worker_response)
        
        if patch_hash in loop_state.attempted_patches:
            prev_iter = loop_state.attempted_patches[patch_hash]
            cheat_signals.append(
                f"补丁与第 {prev_iter} 次迭代重复"
            )
        
        loop_state.attempted_patches[patch_hash] = iteration.iteration_num
        
        # 信号4：约束违规数增加
        if iteration.constraint_violations > 0:
            cheat_signals.append(
                f"存在 {iteration.constraint_violations} 个约束违规"
            )
        
        if cheat_signals:
            loop_state.cheat_evidence.extend(cheat_signals)
            loop_state.worker_cheat_score += 0.2
            return loop_state.worker_cheat_score > 0.5
        
        return False
    
    def _build_evidence(self, score: CompositeScore) -> ActionableEvidence:
        """
        从评分结果构建可操作的证据。
        """
        # 简化实现，实际需要完整的 evidence builder
        return ActionableEvidence(
            geometry_delta=None,
            style_deltas=[],
            probable_source_files=[],
            previous_attempts=[],
        )
    
    def _apply_patch(self, patch_json: dict[str, Any]) -> None:
        """
        应用补丁到实际代码。
        """
        for file_change in patch_json.get('changed_files', []):
            file_path = self.project_root / file_change['file']
            
            if not file_path.exists():
                continue
            
            content = file_path.read_text()
            
            for change in file_change.get('changes', []):
                before = change.get('before', '')
                after = change.get('after', '')
                content = content.replace(before, after, 1)
            
            file_path.write_text(content)
    
    @staticmethod
    def _hash_patch(patch_json: dict[str, Any]) -> str:
        """
        计算补丁的哈希值，用于检测重复。
        """
        import hashlib
        
        canonical = json.dumps(
            patch_json.get('changed_files', []),
            sort_keys=True,
        )
        
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

---

## 二、完整的系统架构总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    UI 无人化还原系统架构                         │
└─────────────────────────────────────────────────────────────────┘

Phase 0: 原型采集（人工 + 自动）
  ├─ 路由静态分析 → 发现所有页面
  ├─ 交互状态矩阵 → 发现所有状态
  ├─ 优先级驱动发现器 → 扩展状态图
  └─ 采集稳定化 → 生成高质量截图
       ↓
Phase 1: 视觉评分（五维度）
  ├─ Geometry（IoU）
  ├─ Color（LAB Delta-E）
  ├─ Typography（Computed Style）
  ├─ Decoration（Computed Style）
  └─ Layout（Computed Style）
       ↓
Phase 2: Worker Prompt 工程
  ├─ 任务上下文（量化偏差）
  ├─ 约束系统（禁止模式）
  └─ 修复策略库（标准模板）
       ↓
Phase 3: 补丁验证（四层）
  ├─ 约束检查
  ├─ Lint 检查
  ├─ 类型检查
  └─ 构建检查
       ↓
Phase 4: Loop 编排 + 防作弊
  ├─ 按阶段驱动（Shell → Region → Element → Polish）
  ├─ 作弊检测（高分提升 + Token 使用率 + 补丁重复）
  └─ 完整审计日志
```

---

## 三、与 GPT 方案的最终对比

| 维度 | GPT 方案 | Opus 方案 |
|---|---|---|
| **状态发现** | BFS 爬链接 | 路由分析 + 交互矩阵 + 优先级发现 |
| **滚动内容** | fullPage 截图 | 分段滚动采集 + 懒加载等待 |
| **评分指标** | SSIM + 感知哈希 | 五维度独立评分（IoU + Delta-E + Style） |
| **阈值策略** | 固定 0.97 | 按阶段动态调整（0.88-0.99） |
| **约束系统** | 软性建议 | 硬性检查，违反直接拒绝 |
| **作弊防护** | 无 | 四层验证 + 作弊检测 + 审计日志 |
| **Loop 编排** | 单一循环 | 五阶段递进（Shell → Region → Element → Polish） |
| **改动行数限制** | 无 | 单次最多 50 行，防止大范围重构 |
| **Token 追踪** | 无 | 完整 Token 使用率统计 |

---

## 四、最后的防线：审计与回滚

```python
# scripts/ui_autopilot/audit/audit_trail.py

@dataclass(frozen=True, slots=True)
class AuditEntry:
    timestamp: float
    phase: str
    iteration: int
    action: str  # 'prompt_generated' | 'worker_called' | 'patch_validated' | 'patch_applied'
    details: dict[str, Any]
    signature: str  # 用于防篡改


class AuditTrail:
    """
    记录所有修复步骤，支持完整回滚。
    """
    
    def __init__(self, audit_file: Path) -> None:
        self.audit_file = audit_file
        self.entries: list[AuditEntry] = []
    
    def record(
        self,
        phase: str,
        iteration: int,
        action: str,
        details: dict[str, Any],
    ) -> None:
        """
        记录一条审计条目。
        """
        import hashlib
        import time
        
        entry = AuditEntry(
            timestamp=time.time(),
            phase=phase,
            iteration=iteration,
            action=action,
            details=details,
            signature=hashlib.sha256(
                json.dumps(details, sort_keys=True).encode()
            ).hexdigest()[:16],
        )
        
        self.entries.append(entry)
        self._persist()
    
    def rollback_to_iteration(
        self,
        phase: str,
        iteration: int,
    ) -> None:
        """
        回滚到指定迭代。
        """
        # 找出该迭代之后的所有补丁
        patches_to_revert = [
            e for e in self.entries
            if (
                e.phase == phase
                and e.iteration > iteration
                and e.action == 'patch_applied'
            )
        ]
        
        # 倒序应用反向补丁
        for entry in reversed(patches_to_revert):
            self._revert_patch(entry.details)
    
    def _persist(self) -> None:
        self.audit_file.write_text(
            json.dumps(
                [
                    {
                        'timestamp': e.timestamp,
                        'phase': e.phase,
                        'iteration': e.iteration,
                        'action': e.action,
                        'details': e.details,
                        'signature': e.signature,
                    }
                    for e in self.entries
                ],
                indent=2,
            )
        )
```

---

## 完整系统结论

这个五部分系统的核心创新：

1. **第1部分**：从 BFS 转向**优先级驱动的混合遍历**，解决状态发现的系统性盲区
2. **第2部分**：从固定等待转向**几何采样稳定性检测**，解决截图不稳定问题
3. **第3部分**：从 SSIM 转向**五维度独立评分**，解决评分失准问题
4. **第4部分**：从软性建议转向**硬性约束系统**，堵死作弊路径
5. **第5部分**：从单一循环转向**五阶段递进 + 防作弊检测**，实现完整的无人化编排

**最关键的差异**：GPT 方案把"修复"看作"根据反馈调整"，我的方案把"修复"看作"在约束系统内的有限搜索空间中找最优解"。

前者容易被 Worker 作弊（用 hardcode 快速通过评分），后者通过约束系统从根本上消除了作弊的收益。