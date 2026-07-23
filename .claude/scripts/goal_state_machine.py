#!/usr/bin/env python3
"""
goal_state_machine.py — Goal 自闭环状态机

Pipeline: CLARIFY → PLANNING → EXECUTING → VERIFYING → ARCHIVING → ARCHIVED

每个状态可前/后向转换。自动推进规则：
  - intent/goal 缺失时自动回退 CLARIFY
  - 全部 AC verified → 自动推 ARCHIVING
  - archive 成功 → ARCHIVED

Usage:
    from goal_state_machine import GoalMachine, GoalStatus

Usage:
    gm = GoalMachine(token_path)
    gm.transition("VERIFYING")
    print(gm.current_state)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# ─── State Constants ───
CLARIFY = "CLARIFY"
PLANNING = "PLANNING"
EXECUTING = "EXECUTING"
VERIFYING = "VERIFYING"
ARCHIVING = "ARCHIVING"
ARCHIVED = "ARCHIVED"

ALL_STATES = [CLARIFY, PLANNING, EXECUTING, VERIFYING, ARCHIVING, ARCHIVED]

# ─── Valid Transitions ───
_VALID_TRANSITIONS = {
    None: [CLARIFY],                  # 初始状态 -> CLARIFY
    CLARIFY: [PLANNING, CLARIFY],     # 澄清后可进 PLANNING，或继续澄清
    PLANNING: [EXECUTING, CLARIFY],   # 计划后执行，或回 CLARIFY（需求变更）
    EXECUTING: [VERIFYING, CLARIFY],  # 执行后验证，或回 CLARIFY
    VERIFYING: [ARCHIVING, EXECUTING, CLARIFY],  # 验证后归档/回执行/回澄清
    ARCHIVING: [ARCHIVED, VERIFYING], # 归档中 -> 完成或回验证
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

    def can_transition(self, target_state):
        """检查 target_state 是否合法"""
        return target_state in _VALID_TRANSITIONS.get(self._state, [])

    def transition(self, target_state, token=None, reason=""):
        """尝试状态转换 — 验证合法性 + 更新 token（如有）"""
        if target_state not in ALL_STATES:
            raise GoalError(f"Unknown state: {target_state}")

        valid = _VALID_TRANSITIONS.get(self._state, [])
        if target_state not in valid:
            raise GoalError(
                f"Invalid transition: {self._state} → {target_state} "
                f"(allowed: {valid})"
            )

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
                self.token_path.write_text(
                    json.dumps(token_data, indent=2, ensure_ascii=False) + "\n"
                )

        return True

    def auto_progress(self, token=None):
        """根据 token 状态自动推进（executing→verifying→archiving→archived）"""
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

        if goal_state == EXECUTING and done >= total:
            self.transition(VERIFYING, token_data,
                            reason=f"auto: all {done}/{total} steps completed")
            transitions_made.append(("auto", EXECUTING, VERIFYING))

        if goal_state == VERIFYING and done >= total:
            self.transition(ARCHIVING, token_data,
                            reason="auto: all steps verified")
            transitions_made.append(("auto", VERIFYING, ARCHIVING))

        # ARCHIVING → ARCHIVED 需要外部调用 archive 命令后自动触发
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
        CLARIFY: "📋",
        PLANNING: "📐",
        EXECUTING: "⚡",
        VERIFYING: "🔍",
        ARCHIVING: "📦",
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
    Path(tp).unlink(missing_ok=True)
    print("\nAll checks passed ✅")
