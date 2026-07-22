#!/usr/bin/env python3
"""policy_enforcer.py — 运行时校验：autofix边界/verifier降级/模式冲突"""

import yaml
import os


class AutofixPolicyEnforcer:
    """校验autofix操作是否超出安全边界"""

    def __init__(self, policy_path: str):
        with open(policy_path) as f:
            self.policy = yaml.safe_load(f)["autofix_policy"]

    def check_safe(self, fix_action: dict) -> tuple[bool, str]:
        """safe级操作校验"""
        # 检查禁止操作
        action_type = fix_action.get("type", "")
        forbidden = self.policy["safe"]["forbidden_patterns"]
        for pattern in forbidden:
            if action_type == pattern or action_type.startswith(pattern.replace("-", "_")):
                return False, f"禁止操作: {action_type} (safe级不允许)"

        # 检查文件数
        files = fix_action.get("files_changed", 1)
        if files > self.policy["safe"]["constraints"]["max_files"]:
            return False, f"safe级禁止多文件修改 (最多{self.policy['safe']['constraints']['max_files']}个)"

        # 检查行数
        lines = fix_action.get("lines_changed", 0)
        if lines > self.policy["safe"]["constraints"]["max_lines_changed"]:
            return False, f"safe级禁止大范围修改 (最多{self.policy['safe']['constraints']['max_lines_changed']}行)"

        return True, "ok"

    def check_review(self, fix_action: dict) -> tuple[bool, str]:
        """review级前置校验"""
        if not fix_action.get("diff_displayed", False):
            return False, "review级必须展示diff"
        if not fix_action.get("user_confirmed", False):
            return False, "review级必须用户确认"
        return True, "ok"

    def check_report_only(self, fix_action: dict) -> tuple[bool, str]:
        """report-only下任何写操作都被阻断"""
        if fix_action.get("type") or fix_action.get("files_changed", 0) > 0:
            return False, "report-only禁止任何写操作"
        return True, "ok"


class VerifierDegradationEnforcer:
    """判断verifier是否可降级并执行降级"""

    def __init__(self, rules_path: str):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)["verifier_degradation"]

    def can_degrade(self, verifier: str, mode: str) -> bool:
        """判断verifier在给定模式下是否可降级"""
        v = self.rules.get(verifier)
        if not v:
            return False
        if not v["degradable"]:
            return False
        conditions = v.get("conditions", [])
        if "*" in conditions or mode in conditions:
            return True
        return False

    def degrade(self, verifier: str, mode: str) -> dict:
        """执行降级并返回效果"""
        if not self.can_degrade(verifier, mode):
            return {"action": "block", "reason": f"{verifier}在当前模式{mode}下不可降级"}
        v = self.rules[verifier]
        return {"action": "degrade", "effect": v["on_degrade"]}


class ModeConflictResolver:
    """解析多模式冲突"""

    def __init__(self, modes_path: str):
        with open(modes_path) as f:
            data = yaml.safe_load(f)
        self.priorities = data["mode_priorities"]
        self.rules = data["resolution_rules"]
        self.machine = data["mode_state_machine"]

    def resolve(self, modes: list[str]) -> dict:
        """解析多模式冲突"""
        # 检查冲突规则
        for rule in self.rules:
            if "when" in rule:
                if all(m in modes for m in rule["when"]):
                    return {
                        "conflict": True,
                        "resolution": "reject",
                        "reason": rule["action"],
                    }

        # 按优先级排序
        sorted_modes = sorted(modes, key=lambda m: self.priorities.get(m, 0), reverse=True)
        winner = sorted_modes[0]
        suppressed = [m for m in modes if m != winner]
        return {
            "conflict": len(suppressed) > 0,
            "resolution": winner,
            "suppressed": suppressed if suppressed else None,
        }

    def can_transition(self, from_mode: str, to_mode: str) -> bool:
        """验证mode切换是否合法"""
        transitions = self.machine.get("transitions", {}).get(from_mode, {})
        allowed = transitions.get("to", [])
        forbidden = transitions.get("forbidden", [])
        return to_mode in allowed and to_mode not in forbidden
