#!/usr/bin/env python3
"""lx-code-review: 形式化不变量 + 绕过路径测试（Phase 4）"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from policy_enforcer import ModeConflictResolver, AutofixPolicyEnforcer, VerifierDegradationEnforcer
except ImportError:
    import importlib
    enforcer_mod = importlib.import_module('policy_enforcer')
    ModeConflictResolver = enforcer_mod.ModeConflictResolver
    AutofixPolicyEnforcer = enforcer_mod.AutofixPolicyEnforcer
    VerifierDegradationEnforcer = enforcer_mod.VerifierDegradationEnforcer

REF_DIR = os.path.join(os.path.dirname(__file__), '..', 'references')


def get_resolver():
    return ModeConflictResolver(os.path.join(REF_DIR, 'mode-rules.yaml'))


def get_enforcer():
    return AutofixPolicyEnforcer(os.path.join(REF_DIR, 'autofix-policy.yaml'))


def get_verifier():
    return VerifierDegradationEnforcer(os.path.join(REF_DIR, 'verifier-rules.yaml'))


# ── 状态机测试 ──────────────────────────────────────────

def test_mode_transition_legal():
    """合法切换"""
    resolver = get_resolver()
    assert resolver.can_transition('report-only', 'fix-safe')
    assert resolver.can_transition('fix-safe', 'fix-with-confirmation')
    assert resolver.can_transition('strict', 'full')
    assert resolver.can_transition('fast', 'full')
    print("✅ test_mode_transition_legal")


def test_mode_transition_forbidden():
    """非法切换"""
    resolver = get_resolver()
    assert not resolver.can_transition('report-only', 'strict')       # 跳级
    assert not resolver.can_transition('strict', 'report-only')       # 降安全级
    assert not resolver.can_transition('fix-safe', 'fast')            # safe不能变fast
    assert not resolver.can_transition('strict', 'fix-safe')          # strict不能降
    print("✅ test_mode_transition_forbidden")


# ── 不变量测试 ──────────────────────────────────────────

def test_invariant_write_permission_monotonic():
    """不变量: 模式优先级上升时写权限不可缩小"""
    resolver = get_resolver()
    # strict(80) > fix-safe(40) -> 写权限不可缩小
    lower_priority = resolver.priorities.get('fix-safe', 0)
    higher_priority = resolver.priorities.get('strict', 0)
    assert higher_priority >= lower_priority, \
        "strict must have priority >= fix-safe"
    # strict不能转到fix-safe (写权限缩小)
    assert not resolver.can_transition('strict', 'fix-safe'), \
        "strict -> fix-safe violates write permission monotonicity"
    print("✅ test_invariant_write_permission_monotonic")


def test_invariant_confidence_on_degrade():
    """不变量: 降级后confidence严格降低"""
    enforcer = get_verifier()
    confidence_before = "high"
    result = enforcer.degrade("typecheck", "fast")
    assert result["action"] == "degrade"
    effect = result.get("effect", "")
    # 降级后confidence必须降低
    assert "medium" in effect or "low" in effect, \
        f"Expected confidence drop, got: {effect}"
    assert "high" not in effect.replace("caps_at_", ""), \
        "Degrade must reduce confidence strictly"
    print("✅ test_invariant_confidence_on_degrade")


def test_invariant_report_only_blocks_writes():
    """不变量: report-only禁止所有写操作"""
    enforcer = get_enforcer()
    assert not enforcer.check_report_only({"type": "formatting-only"})[0]
    assert not enforcer.check_report_only({"type": "any_change", "files_changed": 1})[0]
    print("✅ test_invariant_report_only_blocks_writes")


def test_invariant_strict_blocks_core_degrade():
    """不变量: strict禁止核心验证降级"""
    enforcer = get_verifier()
    assert not enforcer.can_degrade("build", "strict")
    assert not enforcer.can_degrade("schema", "strict")
    assert not enforcer.can_degrade("typecheck", "strict")
    assert not enforcer.can_degrade("test", "strict")
    print("✅ test_invariant_strict_blocks_core_degrade")


# ── 绕过测试 ────────────────────────────────────────────

def test_bypass_direct_fs_write():
    """绕过: report-only下直接文件写入被阻断"""
    enforcer = get_enforcer()
    result = enforcer.check_report_only({"type": "formatting-only", "via_direct_fs": True})
    assert not result[0], "report-only must block all writes"
    print("✅ test_bypass_direct_fs_write")


def test_bypass_verifier_skip_in_strict():
    """绕过: strict模式下不能跳过build"""
    enforcer = get_verifier()
    # strict模式下build不可跳过
    assert not enforcer.can_degrade("build", "strict")
    result = enforcer.degrade("build", "strict")
    assert result["action"] == "block"
    print("✅ test_bypass_verifier_skip_in_strict")


def test_bypass_mode_spoof():
    """绕过: mode必须来自validated stack"""
    resolver = get_resolver()
    result = resolver.resolve(["report-only"])
    # report-only本身合法，但如果是被篡改的不会出现在允许的transitions里
    assert result["resolution"] is not None  # 至少返回有效结果
    # 验证不能从full直接跳到report-only之外的模式
    assert not resolver.can_transition("full", "strict"), "full -> strict should be forbidden"
    print("✅ test_bypass_mode_spoof")


if __name__ == "__main__":
    tests = [
        test_mode_transition_legal,
        test_mode_transition_forbidden,
        test_invariant_write_permission_monotonic,
        test_invariant_confidence_on_degrade,
        test_invariant_report_only_blocks_writes,
        test_invariant_strict_blocks_core_degrade,
        test_bypass_direct_fs_write,
        test_bypass_verifier_skip_in_strict,
        test_bypass_mode_spoof,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            import traceback
            print(f"❌ {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{len(tests)} passed")
