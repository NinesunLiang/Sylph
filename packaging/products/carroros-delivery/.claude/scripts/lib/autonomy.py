#!/usr/bin/env python3
"""
autonomy.py — CarrorOS 无人模式

Autonomy Contract: 权责范围 + 最大无人轮次 + 异常上报策略
Loop 硬化: 最大循环次数 + 状态漂移检测 + 自动 handoff
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List


# ── Autonomy Contract ──

def load_contract(project_root: Path) -> dict:
    """Load or create default autonomy contract."""
    contract_path = project_root / ".omc" / "knowledge" / "autonomy-contract.yaml"
    if contract_path.exists():
        import yaml
        return yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    # Default contract
    contract = {
        "schema_version": "carros.autonomy.v1",
        "created": datetime.now(timezone.utc).isoformat(),
        "boundaries": {
            "max_autonomy_turns": 30,
            "max_loop_iterations": 5,
            "max_retries_per_step": 3,
        },
        "permitted_actions": [
            "read_only",
            "one_file_edit",
            "test_execution",
            "documentation_write",
        ],
        "blocked_actions": [
            "delete",         # 删除操作必须确认
            "multi_file_refactor",  # 多文件重构须上报
            "release",        # 发布须人类
            "deploy",        # 部署须人类
            "permission_change",  # 权限变更须人类
        ],
        "reporting": {
            "error_threshold": 3,
            "loop_detection": True,
            "handoff_on_block": True,
        },
    }
    return contract


def save_contract(project_root: Path, contract: dict):
    """Save autonomy contract."""
    import yaml
    contract_path = project_root / ".omc" / "knowledge" / "autonomy-contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(yaml.dump(contract, default_flow_style=False), encoding="utf-8")


# ── Loop Hardening ──

class LoopDetector:
    """检测循环模式 — store tick intent history and detect stalls."""

    def __init__(self, max_loops: int = 5):
        self.history: List[dict] = []
        self.max_loops = max_loops

    def record_tick(self, step_id: str, action: str, intent: str = ""):
        """Record a tick action for loop detection."""
        self.history.append({
            "step": step_id,
            "action": action[:100],
            "intent": intent[:100],
            "time": datetime.now(timezone.utc).isoformat(),
        })

    def detect_loop(self) -> Optional[dict]:
        """Check if the same action repeats more than max_loops times."""
        recent = self.history[-self.max_loops:]
        if len(recent) < self.max_loops:
            return None

        # Check for same step + same action repeating
        actions = [(t["step"], t["action"][:30]) for t in recent]
        if len(set(actions)) <= 2:
            return {
                "type": "loop_detected",
                "ticks": len(self.history),
                "recent_actions": actions[-self.max_loops:],
                "suggestion": "write handoff, reconsider approach",
            }

        return None

    def detect_stall(self, tick_count: int, verified_count: int) -> Optional[dict]:
        """Detect stall: ticks increase but verified steps don't."""
        if tick_count > 10 and verified_count == 0:
            return {
                "type": "stall_detected",
                "ticks": tick_count,
                "verified": verified_count,
                "suggestion": "write handoff, check plan feasibility",
            }
        return None


def check_autonomy_gate(
    token: dict,
    loop_detector: LoopDetector,
) -> Optional[str]:
    """
    Check if autonomy should be paused.

    Returns None = continue, str = reason to pause.
    """
    # Max turns exceeded?
    stats = token.get("stats", {})
    tick = stats.get("tick", 0)
    contract = token.get("budget", {})
    hard = contract.get("max_turns_hard", 0) or 30

    if hard > 0 and tick >= hard:
        return f"max_turns_hard reached ({tick}/{hard})"

    # Loop detected?
    loop = loop_detector.detect_loop()
    if loop:
        return f"loop_detected: {loop['suggestion']}"

    # Stall?
    verified = stats.get("done", 0)
    stall = loop_detector.detect_stall(tick, verified)
    if stall:
        return f"stall_detected: ticks={tick} verified={verified}"
    
    return None


def auto_handoff(
    task_dir: Path,
    token: dict,
    reason: str,
    project_root: Path,
) -> Path:
    """自动写 handoff 当 autonomy 被暂停."""
    try:
        import sys
        sys.path.insert(0, str(project_root / ".omc" / "scripts"))
        from lib.handoff_writer import write_handoff

        handoff_path = write_handoff(
            task_dir=task_dir,
            task_id=token.get("session", {}).get("id", "unknown"),
            token=token,
            plan_path=task_dir / "plan.md",
            executor_path=task_dir / "executor.md",
        )
        return handoff_path
    except Exception:
        # Fallback: write minimal handoff
        h = task_dir / "handoff.md"
        h.write_text(f"# Auto Handoff\nreason: {reason}\ntime: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
        return h
