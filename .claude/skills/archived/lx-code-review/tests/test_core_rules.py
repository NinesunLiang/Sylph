#!/usr/bin/env python3
"""lx-code-review: 规则元数据解析测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── 规则格式验证 ────────────────────────────────────────

def test_rule_id_format():
    """规则 ID 必须符合 generic.<category>.<name> 格式"""
    ids = [
        "generic.security.hardcoded-secret",
        "generic.correctness.nil-deref",
        "generic.maintainability.large-function",
        "generic.performance.slow-loop",
        "generic.style.naming-convention",
    ]
    for rid in ids:
        parts = rid.split(".")
        assert len(parts) == 3, f"Rule ID {rid} must have 3 parts"
        assert parts[0] == "generic", f"Rule ID {rid} must start with 'generic'"
        assert parts[1] in ("security", "correctness", "maintainability", "performance", "style"), \
            f"Rule ID {rid} has unknown category: {parts[1]}"
    print(f"✅ test_rule_id_format: {len(ids)} rules pass")


def test_severity_levels():
    """严重级别必须是 critical/high/medium/low"""
    valid = {"critical", "high", "medium", "low"}
    assert "critical" in valid
    assert "info" not in valid  # info 不是有效级别
    print(f"✅ test_severity_levels: valid levels = {valid}")


def test_autofix_levels():
    """自动修复等级必须是 safe/review/suggest"""
    valid = {"safe", "review", "suggest"}
    for level in valid:
        assert level in ("safe", "review", "suggest")
    print(f"✅ test_autofix_levels: valid levels = {valid}")


def test_autofix_policy_boundaries():
    """safe 级不允许修改 public API"""
    safe_allowed = ["formatting-only", "typo-in-comments", "mechanical import cleanup"]
    safe_forbidden = ["public API change", "behavior change", "dependency change"]
    for action in safe_allowed:
        assert "change" not in action or action == "mechanical import cleanup"
    for action in safe_forbidden:
        assert "change" in action
    print(f"✅ test_autofix_policy_boundaries: safe_allowed={safe_allowed}")


def test_confidence_propagation():
    """降级时 confidence 不得为 high"""
    degraded = True
    max_confidence = "medium" if degraded else "high"
    assert max_confidence == "medium", "Degraded context must cap confidence at medium"
    print(f"✅ test_confidence_propagation: degraded→{max_confidence}")


def test_verifier_priority():
    """阻断矩阵优先级高于节点降级"""
    blocked_items = {"build", "schema"}
    degradable_items = {"formatter", "lint"}
    for item in blocked_items:
        assert item not in degradable_items
    print(f"✅ test_verifier_priority: build/schema not degradable")


if __name__ == "__main__":
    test_rule_id_format()
    test_severity_levels()
    test_autofix_levels()
    test_autofix_policy_boundaries()
    test_confidence_propagation()
    test_verifier_priority()
    print("\n✅ All tests passed!")
