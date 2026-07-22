#!/usr/bin/env python3
"""lx-code-review: Policy enforcer 测试（Phase 2）"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from policy_enforcer import AutofixPolicyEnforcer, VerifierDegradationEnforcer, ModeConflictResolver
except ImportError:
    # Fallback: direct import
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "policy_enforcer",
        os.path.join(os.path.dirname(__file__), '..', 'scripts', 'policy_enforcer.py')
    )
    policy_enforcer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy_enforcer)
    AutofixPolicyEnforcer = policy_enforcer.AutofixPolicyEnforcer
    VerifierDegradationEnforcer = policy_enforcer.VerifierDegradationEnforcer
    ModeConflictResolver = policy_enforcer.ModeConflictResolver

REF_DIR = os.path.join(os.path.dirname(__file__), '..', 'references')


def get_enforcer():
    return AutofixPolicyEnforcer(os.path.join(REF_DIR, 'autofix-policy.yaml'))


def get_verifier():
    return VerifierDegradationEnforcer(os.path.join(REF_DIR, 'verifier-rules.yaml'))


def get_resolver():
    return ModeConflictResolver(os.path.join(REF_DIR, 'mode-rules.yaml'))


def test_safe_rejects_multi_file():
    """safe级禁止多文件修改"""
    enforcer = get_enforcer()
    ok, reason = enforcer.check_safe({"type": "formatting-only", "files_changed": 3, "lines_changed": 10})
    assert not ok, f"Expected reject, got: {reason}"
    assert "多文件" in reason or "文件" in reason
    print("✅ test_safe_rejects_multi_file")


def test_safe_rejects_large_change():
    """safe级禁止大范围修改"""
    enforcer = get_enforcer()
    ok, reason = enforcer.check_safe({"type": "formatting-only", "files_changed": 1, "lines_changed": 1000})
    assert not ok, f"Expected reject, got: {reason}"
    assert "行" in reason
    print("✅ test_safe_rejects_large_change")


def test_safe_allows_small_format():
    """safe级允许小范围格式化"""
    enforcer = get_enforcer()
    ok, reason = enforcer.check_safe({"type": "formatting-only", "files_changed": 1, "lines_changed": 10})
    assert ok, f"Expected allow, got: {reason}"
    print("✅ test_safe_allows_small_format")


def test_build_not_degradable():
    """build不可降级"""
    enforcer = get_verifier()
    assert not enforcer.can_degrade("build", "fast"), "build should not be degradable in fast"
    assert not enforcer.can_degrade("build", "full"), "build should not be degradable in full"
    print("✅ test_build_not_degradable")


def test_schema_not_degradable():
    """schema不可降级"""
    enforcer = get_verifier()
    assert not enforcer.can_degrade("schema", "fast")
    print("✅ test_schema_not_degradable")


def test_typecheck_degradable_in_fast():
    """typecheck在fast模式下可降级"""
    enforcer = get_verifier()
    assert enforcer.can_degrade("typecheck", "fast"), "typecheck should be degradable in fast"
    print("✅ test_typecheck_degradable_in_fast")


def test_typecheck_not_degradable_in_strict():
    """typecheck在strict模式下不可降级"""
    enforcer = get_verifier()
    assert not enforcer.can_degrade("typecheck", "strict")
    print("✅ test_typecheck_not_degradable_in_strict")


def test_report_only_conflict():
    """report-only与fix-safe冲突"""
    resolver = get_resolver()
    result = resolver.resolve(["report-only", "fix-safe"])
    assert result["resolution"] == "reject", f"Expected reject, got: {result}"
    print("✅ test_report_only_conflict")


def test_higher_priority_wins():
    """更高优先级模式胜出"""
    resolver = get_resolver()
    result = resolver.resolve(["fix-safe", "strict"])
    assert result["resolution"] == "strict", f"Expected strict, got: {result}"
    print("✅ test_higher_priority_wins")


def test_degrade_effect():
    """降级效果正确"""
    enforcer = get_verifier()
    result = enforcer.degrade("typecheck", "fast")
    assert result["action"] == "degrade"
    assert "confidence" in result.get("effect", "")
    print("✅ test_degrade_effect")


def test_undegradable_blocks():
    """不可降级的执行degrade应返回block"""
    enforcer = get_verifier()
    result = enforcer.degrade("build", "fast")
    assert result["action"] == "block"
    print("✅ test_undegradable_blocks")


if __name__ == "__main__":
    tests = [
        test_safe_rejects_multi_file,
        test_safe_rejects_large_change,
        test_safe_allows_small_format,
        test_build_not_degradable,
        test_schema_not_degradable,
        test_typecheck_degradable_in_fast,
        test_typecheck_not_degradable_in_strict,
        test_report_only_conflict,
        test_higher_priority_wins,
        test_degrade_effect,
        test_undegradable_blocks,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{len(tests)} passed")
