# Claude Code (Opus) 终审

## 审核范围

`convergence.py` × `domain.py` × `measure_implementation.py`

前两轮已覆盖 orchestrator / gate chain / state_store / phase_rules，本轮聚焦 **测量–收敛–评分三角**。三角的任何一条边断裂，整个 overnight 优化就是在错误目标上空转。

---

## 最终判决

```yaml
reviewer: claude-opus-5
verdict: NO-GO

confirmed_sound:- convergence.py EMA 状态机设计正确
  - domain.Score.uif_composite() fail-closed 正确
  - state_store 原子写逻辑可信
  - StrategyState 方向锁定思路正确

confirmed_broken:
  - D6 + D7 占UIF-99 权重 42%，measurement producer 完全缺席
  - StrategyState.locked_until 用monotonic → checkpoint 不可恢复
  - StrategyState 无 to_dict()/from_dict() → LoopController 序列化不完整
  - Gate 失败 → score=0.0 → EMA 瞬间 DIVERGING →虚假紧急回滚级联
  - measure_implementation.py 与 measure_prototype.py 99% 重复 + 同一资源泄漏
  - scroll_coverage 默认 0.0 → 早期阶段得分人工压制，无法达到 0.99 目标

structural_risk:
  "D6/D7 缺失导致 UIF-99 目标在数学上不可达，
   或scorer 默认高值导致评分是 facade，二者必居其一。"
```

---

## P0-1：UIF-99 数学目标不可达（D6/D7 缺失）

这是三个模型审核意见里**结构性最强**的一条。

`domain.py` 定义的权重：

```python
visual = (
    self.geometry* 0.16   # D1
    + self.color* 0.12   # D2
    + self.typography * 0.10 # D3
    + self.decoration * 0.08 # D4
    + self.layout   * 0.12   # D5
    + self.token_align * 0.18  # D6 ← 测量器未实现
    + self.interaction * 0.24  # D7 ← 测量器未实现
)
composite = visual * 0.85 + completeness * 0.15
```

`measure_prototype.py` 和 `measure_implementation.py` 实际提供的字段：

```json
{ "bbox", "colors", "fonts", "borders", "shadows", "layout" }
```

D6（`token_align`）和 D7（`interaction`）的measurement producer **完全不存在**。

### 两种后果都是 P0

**路径 A（诚实默认值= 0.0）**：

```
D1=1.0, D2=1.0, D3=1.0, D4=1.0, D5=1.0, D6=0.0, D7=0.0
visual = 0.16+0.12+0.10+0.08+0.12 = 0.58
completeness = 1.0 (假设所有 coverage 均满)
composite = 0.58 × 0.85 + 1.0 × 0.15 = 0.493 + 0.15 = 0.643
```

**最高只能达到 0.64，目标 0.99 在数学上不可达**。LoopController 永远不会收到 CONVERGED，overnight 会跑满整个 budget然后 EXHAUSTED。

**路径 B（scorer 对未测量维度默认 1.0）**：  
分数虚高，可以"触达"0.99，但 D6/D7 从未被实际验证，gate 通过的是一个假评分。整个 overnight 修复的目标变成"骗过评分器"而非真正还原 UI。

### 最小可行的 D6 producer

D6 是 token对齐率，不需要 Playwright。需要一个静态分析器：

```python
# token_align_producer.py
import re
from pathlib import Path
from typing import Iterator

# 不允许出现的原始值模式（应全部被 token替换）
RAW_HEX_RE= re.compile(r'(?<!["\w])#(?:[0-9a-fA-F]{3,4}){1,2}\b')
RAW_RGBA_RE   = re.compile(r'rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+')
RAW_PX_SIZE_RE = re.compile(r'(?<!\w)(?:font-size|gap|padding|margin)\s*:\s*\d+px')

def scan_file(path: Path) -> dict:
    src = path.read_text(encoding="utf-8")
    raw_hits = (
        len(RAW_HEX_RE.findall(src))
        + len(RAW_RGBA_RE.findall(src))
        + len(RAW_PX_SIZE_RE.findall(src))
    )
    # token引用数= CSS var() 出现次数
    token_refs = len(re.findall(r'var\(--', src))
    total = raw_hits + token_refs
    rate = token_refs / total if total > 0 else 1.0
    return {
        "file": str(path),
        "raw_value_hits": raw_hits,
        "token_refs": token_refs,
        "alignment_rate": rate,
    }

def compute_d6(component_dir: Path, token_catalog: set[str]) -> float:
    """D6: token 命中率，对所有 .scss/.tsx 文件取平均"""
    rates = []
    for path in component_dir.rglob("*.scss"):
        rates.append(scan_file(path)["alignment_rate"])
    for path in component_dir.rglob("*.tsx"):
        rates.append(scan_file(path)["alignment_rate"])
    return sum(rates) / len(rates) if rates else 0.0
```

D7 的最小可行形式是一个 assertion catalog runner，要求 Playwright 在可运行实现上执行：

```python
# interaction_assertion_runner.py
@dataclass
class Assertion:
    id: str
    trigger: str    # "hover" | "click" | "keyboard"
    selector: str
    expect_selector: str | None = None
    expect_class: str | None = None
    expect_aria: str | None = None

def run_assertion(page: Page, a: Assertion) -> bool:
    try:
        el = page.locator(a.selector).first
        if a.trigger == "hover":
            el.hover()
        elif a.trigger == "click":
            el.click()
        page.wait_for_timeout(150)
        if a.expect_selector:
            return page.locator(a.expect_selector).is_visible(timeout=1000)
        if a.expect_class:
            return a.expect_class in (el.get_attribute("class") or "")
        return True
    except Exception:
        return False

def compute_d7(page: Page, assertions: list[Assertion]) -> float:
    if not assertions:
        return 0.0
    passed = sum(run_assertion(page, a) for a in assertions)
    return passed / len(assertions)
```

**在 D6/D7 有真实producer 之前，`h2_evidence_pass` 必须强制为 False**，score 返回 0.0，系统如实反映"测量不完整"。

---

## P0-2：Gate 失败 → score=0.0 → EMA 误判 DIVERGING

`domain.Score.uif_composite()` 的 fail-closed 设计是正确的：

```python
if not self.h1_engineering_pass or not self.h2_evidence_pass:
    return 0.0
```

但这与 `ConvergenceTracker` 之间有一个致命的交互：

```python
#假设上一轮 score = 0.85
# 本轮 C2 tsc 编译失败 → h1=False → score = 0.0
delta = 0.0 - 0.85 = -0.85
self._ema =0.3 × (-0.85) + 0.7 × prev_ema

# 结果: _ema << -0.005 → DIVERGING → EMERGENCY ROLLBACK
```

这会把任何一次编译错误都变成"紧急回滚"，而不是"修编译错误然后继续"。

修复：在 `record_and_decide()` 中区分 gate 失败和真实分数下降：

```python
# convergence.py —LoopController.record_and_decide() 修正版
def record_and_decide(
    self,
    score: float,
    phase: str,
    *,
    gates_passed: bool = True,# 新增参数
    gate_failure_reason: str | None = None,
) -> LoopAction:
    """Only feed EMA with scores from passing-gate iterations."""
    
    if not gates_passed:
        # Gate 失败不是收敛信号，单独计数
        self._consecutive_gate_failures = getattr(self, "_consecutive_gate_failures", 0) + 1
        if self._consecutive_gate_failures >= 3:
            return LoopAction.ESCALATE_TO_ROOT_CAUSE
        return LoopAction.RETRY_WITH_MORE_MEASUREMENTS
    
    # 门通过才重置 gate 失败计数，更新 EMA
    self._consecutive_gate_failures = 0
    status = self.tracker.record(score)
    return self._decide_from_status(status, phase)
```

---

## P0-3：StrategyState 序列化缺失，locked_until 是 monotonic

`StrategyState` 在 `LoopController.to_dict()` 中会被序列化，但自身没有 `to_dict()`/`from_dict()`：

```python
@dataclass(slots=True)
class StrategyState:
    current: str = "normal"
    locked_direction: str | None = None
    locked_until: float = 0.0          # ← monotonic!跨进程无效
    
    def lock(self, direction: str, duration_seconds: float) -> None:
        self.locked_direction = direction
        self.locked_until = __import__("time").monotonic() + ...# ← 反模式
```

两个问题：

1. `__import__("time")` 是隐藏全局副作用，应是模块级 import
2. `locked_until` 用 monotonic 时间戳存入checkpoint，进程重启后无意义

### 完整修复

```python
import time
from datetime import datetime, timezone


@dataclass(slots=True)
class StrategyState:
    current: str = "normal"
    locked_direction: str | None = None
    locked_until_utc: float = 0.0      # Unix timestamp (UTC), survives restart

    def lock(self, direction: str, duration_seconds: float) -> None:
        self.locked_direction = direction
        self.locked_until_utc = datetime.now(timezone.utc).timestamp() + duration_seconds
        self.current = "locked"

    def unlock(self) -> None:
        if datetime.now(timezone.utc).timestamp() >= self.locked_until_utc:
            self.locked_direction = None
            self.current = "normal"

    @property
    def is_locked(self) -> bool:
        return (
            self.locked_direction is not None
            and datetime.now(timezone.utc).timestamp() < self.locked_until_utc
        )

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "locked_direction": self.locked_direction,
            "locked_until_utc": self.locked_until_utc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StrategyState:
        s = cls()
        s.current = data.get("current", "normal")
        s.locked_direction = data.get("locked_direction")
        s.locked_until_utc = data.get("locked_until_utc", 0.0)
        return s
```

---

## P1-1：Score 公式中 `scroll_coverage` 默认 0.0 造成早期阶段人工压制

```python
completeness = min(
    self.interaction_coverage,
    self.state_coverage,
    self.route_coverage,
    self.scroll_coverage,   # 默认 0.0
)
composite = visual * 0.85 + completeness * 0.15
```

SHELL/REGIONS阶段不做滚动测试，`scroll_coverage` 天然是 0.0，`completeness` 强制为 0，`composite` 被压至 `visual × 0.85`。

这会让LoopController 在早期阶段看到持续低分，触发不必要的 STAGNANT/DECELERATING 判断。

修复：按阶段限定参与min() 的维度：