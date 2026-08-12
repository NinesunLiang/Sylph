#!/usr/bin/env python3
"""
goal_state_machine.py — Goal 严格向前状态机

Pipeline: CLARIFY → PLANNING → EXECUTING → VERIFYING → ARCHIVING → ARCHIVED

严格向前（Task74）：所有倒退转换非法。需要 recovery 时使用专门的
API（普通 transition 不提供倒退能力）。

Gate 集成：
  - goal token 进入 PLANNING 必须提供并通过 research_path
  - goal token 进入 EXECUTING 必须提供并通过 research_path + plan_path
  - 非 goal token 保留纯状态转换，供低层任务兼容

Usage:
    from goal_state_machine import GoalMachine, GoalStatus

    gm = GoalMachine(token_path)
    gm.transition("VERIFYING")
    print(gm.current_state)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from error_dna_logger import log_error

# ─── Gate contracts (optional — enables ResearchGate / PlanGate validation) ───
try:
    from goal_contracts import ResearchGate, ResearchGateError, PlanGate, PlanGateError
except ImportError:
    ResearchGate = None
    ResearchGateError = Exception
    PlanGate = None
    PlanGateError = Exception
try:
    from phase_contracts import validate_contract_ready
except ImportError:
    validate_contract_ready = None

# ─── State Constants ───
CLARIFY = "CLARIFY"
PLANNING = "PLANNING"
EXECUTING = "EXECUTING"
VERIFYING = "VERIFYING"
ARCHIVING = "ARCHIVING"
ARCHIVED = "ARCHIVED"

ALL_STATES = [CLARIFY, PLANNING, EXECUTING, VERIFYING, ARCHIVING, ARCHIVED]

# ─── Valid Transitions (strict forward-only) ───
# Task74: All backward transitions are illegal. Recovery requires
# dedicated API (not through ordinary transition).
_VALID_TRANSITIONS = {
    None: [CLARIFY],                  # 初始状态 -> CLARIFY
    CLARIFY: [PLANNING],              # 澄清后可进 PLANNING
    PLANNING: [EXECUTING],            # 计划后执行
    EXECUTING: [VERIFYING],           # 执行后验证
    VERIFYING: [ARCHIVING],           # 验证后归档
    ARCHIVING: [ARCHIVED],            # 归档后完成
    ARCHIVED: [],                     # 终态
}


class GoalError(Exception):
    """GoalMachine 状态转换异常"""
    pass


class GoalMachine:
    """Goal 状态机 — 管理任务生命周期状态转换"""

    def __init__(self, token_path=None, spec_path=None):
        self.token_path = Path(token_path) if token_path else None
        self.spec_path = spec_path
        self._state = None

        # 尝试从 token 恢复状态
        if self.token_path and self.token_path.exists():
            try:
                token = json.loads(self.token_path.read_text())
                self._state = token.get("goal", {}).get("state")
            except (json.JSONDecodeError, OSError):
                pass

        if self._state not in ALL_STATES:
            self._state = None  # 还未初始化

    @property
    def current_state(self):
        return self._state

    @property
    def is_terminal(self):
        return self._state == ARCHIVED

    def _read_token(self) -> dict | None:
        """Read token file, return dict or None."""
        if self.token_path and self.token_path.exists():
            try:
                return json.loads(self.token_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def can_transition(self, target_state):
        """检查 target_state 是否合法（含 stats 门禁：EXECUTING→VERIFYING 需 done>=total）"""
        if target_state not in _VALID_TRANSITIONS.get(self._state, []):
            return False

        # Gate: EXECUTING→VERIFYING 需要所有 step 已完成
        if self._state == EXECUTING and target_state == VERIFYING:
            token = self._read_token()
            if token:
                stats = token.get("stats", {})
                done = stats.get("done", 0)
                total = stats.get("total", 0)
                if total <= 0 or done != total:
                    return False

        return True

    def transition(self, target_state, token=None, reason="", research_path=None, plan_path=None):
        """尝试状态转换 — 验证合法性 + gate validation + 更新 token

        Args:
            target_state: 目标状态
            token: 可选的 token 字典（用于更新）
            reason: 转换原因
            research_path: 如果目标为 PLANNING，在此路径上的 research.md
                           会被 ResearchGate 验证
            plan_path: 如果目标为 EXECUTING，在此路径上的 plan.md
                       会被 PlanGate 验证

        注：gate 验证仅在提供了文档路径时触发。不传路径时保持纯状态后退兼容，
        供低层 state-only 测试使用。生产 lifecycle wrapper 必须传路径。
        """
        if target_state not in ALL_STATES:
            raise GoalError(f"Unknown state: {target_state}")

        valid = _VALID_TRANSITIONS.get(self._state, [])
        if target_state not in valid:
            raise GoalError(
                f"Invalid transition: {self._state} -> {target_state} "
                f"(allowed: {valid})"
            )

        # Stats gate: EXECUTING->VERIFYING requires all steps done
        if self._state == EXECUTING and target_state == VERIFYING:
            effective_token = token if token is not None else self._read_token()
            if effective_token:
                stats = effective_token.get("stats", {})
                done = stats.get("done", 0)
                total = stats.get("total", 0)
                if total <= 0 or done != total:
                    raise GoalError(
                        f"Cannot transition to VERIFYING: not all steps done "
                        f"({done}/{total})"
                    )

        # ── Gate validation ──────────────────────────────────────────
        token_data = token if token is not None else (self._read_token() or {})
        is_goal = token_data.get("mode") == "goal"
        task_dir = token_data.get("task_dir")

        if is_goal and target_state in (VERIFYING, ARCHIVING) and not task_dir:
            raise GoalError("Goal lifecycle requires task_dir for schema validation")

        if is_goal and target_state == PLANNING and research_path is None:
            raise GoalError("Goal research_path is required before PLANNING")
        if is_goal and target_state == EXECUTING and plan_path is None:
            raise GoalError("Goal research_path and plan_path are required before EXECUTING")
        if is_goal and task_dir and target_state in (PLANNING, EXECUTING, VERIFYING, ARCHIVING):
            if validate_contract_ready is None:
                raise GoalError("phase handoff validator unavailable; cannot advance Goal")
            previous_phase = {
                PLANNING: CLARIFY,
                EXECUTING: PLANNING,
                VERIFYING: EXECUTING,
                ARCHIVING: VERIFYING,
            }[target_state]
            try:
                validate_contract_ready(task_dir, previous_phase)
            except ValueError as exc:
                raise GoalError(
                    f"phase handoff blocked before {target_state}: {exc}"
                ) from exc

        if is_goal and target_state == PLANNING:
            if research_path is None:
                raise GoalError(
                    "Goal research gate requires research_path before entering PLANNING"
                )
            if ResearchGate is None:
                raise GoalError("ResearchGate unavailable; Goal cannot enter PLANNING")
        if is_goal and target_state == EXECUTING:
            if research_path is None or plan_path is None:
                raise GoalError(
                    "Goal plan gate requires research_path and plan_path before entering EXECUTING"
                )
            if ResearchGate is None or PlanGate is None:
                raise GoalError("ResearchGate/PlanGate unavailable; Goal cannot enter EXECUTING")

        if target_state == PLANNING and research_path is not None and ResearchGate is not None:
            try:
                ResearchGate.validate(research_path)
            except ResearchGateError as e:
                log_error(
                    "ResearchGateError",
                    str(e),
                    fix="填写 research.md 的 8 个必需 section（背景/约束/已知信息/不确定性/全貌/依赖树/方案/Dependency TDD），依赖树至少 1 条",
                    context={"research_path": str(research_path), "target_state": "PLANNING"}
                )
                raise GoalError(
                    f"ResearchGate blocked transition to PLANNING: {e}"
                ) from e

        if target_state == EXECUTING and research_path is not None and ResearchGate is not None:
            try:
                ResearchGate.validate(research_path)
            except ResearchGateError as e:
                log_error(
                    "ResearchGateError",
                    str(e),
                    fix="先完成 research.md，再填写 plan.md",
                    context={"research_path": str(research_path), "target_state": "EXECUTING"}
                )
                raise GoalError(
                    f"ResearchGate blocked transition to EXECUTING: {e}"
                ) from e

        if target_state == EXECUTING and plan_path is not None and PlanGate is not None:
            try:
                PlanGate.validate(plan_path)
            except PlanGateError as e:
                log_error(
                    "PlanGateError",
                    str(e),
                    fix="在 plan.md 添加 ## Phase N 声明（N=1,2,3...），Steps 中每项需包含 acceptance 字段",
                    context={"plan_path": str(plan_path), "target_state": "EXECUTING"}
                )
                raise GoalError(
                    f"PlanGate blocked transition to EXECUTING: {e}"
                ) from e

        old_state = self._state
        self._state = target_state

        # 更新 token
        token_data = token
        if token_data is None and self.token_path and self.token_path.exists():
            try:
                token_data = json.loads(self.token_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        if token_data is not None:
            if "goal" not in token_data:
                token_data["goal"] = {}
            token_data["goal"]["state"] = target_state
            token_data["goal"]["previous_state"] = old_state
            token_data["goal"]["transitions"] = token_data["goal"].get("transitions", 0) + 1
            token_data["goal"]["last_transition"] = datetime.now(timezone.utc).isoformat()
            if reason:
                token_data["goal"]["last_reason"] = reason
            if self.token_path:
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = self.token_path.with_suffix(
                    self.token_path.suffix + f".{os.getpid()}.tmp"
                )
                try:
                    tmp_path.write_text(
                        json.dumps(token_data, indent=2, ensure_ascii=False) + "\n"
                    )
                    os.replace(tmp_path, self.token_path)
                finally:
                    tmp_path.unlink(missing_ok=True)

        return True

    def auto_progress(self, token=None):
        """根据 token 状态自动推进（executing -> verifying -> archiving）"""
        token_data = token
        if token_data is None and self.token_path and self.token_path.exists():
            try:
                token_data = json.loads(self.token_path.read_text())
            except (json.JSONDecodeError, OSError):
                return []

        if not token_data:
            return []

        stats = token_data.get("stats", {})
        done = stats.get("done", 0)
        total = stats.get("total", 0)
        goal_state = token_data.get("goal", {}).get("state")

        transitions_made = []

        if goal_state == EXECUTING and total > 0 and done >= total:
            self.transition(VERIFYING, token_data,
                            reason=f"auto: all {done}/{total} steps completed")
            transitions_made.append(("auto", EXECUTING, VERIFYING))

        # VERIFYING -> ARCHIVING requires external verify results
        # auto_progress() intentionally stops at VERIFYING

        # ARCHIVING -> ARCHIVED 需要外部调用 archive 命令后自动触发
        return transitions_made

    def reset(self, token=None):
        """重置状态机 — 回到 CLARIFY"""
        self._state = None
        return self.transition(CLARIFY, token, reason="reset")

    def get_summary(self):
        """获取状态机摘要"""
        return {
            "current_state": self._state,
            "is_terminal": self.is_terminal,
            "valid_transitions": _VALID_TRANSITIONS.get(self._state, []),
        }


def get_state_header(state, color=True):
    """获取带颜色的状态头"""
    icons = {
        CLARIFY: "\U0001f4cb",
        PLANNING: "\U0001f4d0",
        EXECUTING: "⚡",
        VERIFYING: "\U0001f50d",
        ARCHIVING: "\U0001f4e6",
        ARCHIVED: "✅",
    }
    icon = icons.get(state, "❓")
    label = state or "INIT"
    if not color:
        return f"[{icon} {label}]"
    return f"\033[1m{icon} {label}\033[0m"


# ─── Self-test ───
if __name__ == "__main__":
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps({
            "stats": {"done": 0, "total": 3},
            "goal": {"state": None}
        }))
        tp = f.name

    gm = GoalMachine(tp)
    print("Initial:", gm.current_state)
    gm.transition(CLARIFY)
    print("After CLARIFY:", gm.current_state)
    gm.transition(PLANNING)
    print("After PLANNING:", gm.current_state)
    print("Summary:", gm.get_summary())

    # Test forward-only: backward should raise
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
        f2.write(json.dumps({
            "stats": {"done": 0, "total": 3},
            "goal": {"state": None}
        }))
        tp2 = f2.name

    gm2 = GoalMachine(tp2)
    gm2.transition(CLARIFY)
    gm2.transition(PLANNING)
    gm2.transition(EXECUTING)
    try:
        gm2.transition(CLARIFY)  # EXECUTING -> CLARIFY, should raise
        print("ERROR: backward transition did not raise!")
    except GoalError:
        print("OK: backward transition correctly blocked")
    Path(tp2).unlink(missing_ok=True)

    Path(tp).unlink(missing_ok=True)
    print("\nAll checks passed")
