#!/usr/bin/env python3
"""
TDD test: posttool-claim-audit.py — edit_mode / edit_scope / patience_score

直接测试 edit-churn 数据分类逻辑（不依赖 hook 管线启动）。
Run: python3 tests/test-edit-churn-quality.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


# ── error-dna.py 内 edit_mode / edit_scope / patience_score 计算逻辑的复制 ──

def detect_edit_mode(tool_name: str, old_str: str, new_str: str) -> str:
    """复现 posttool-claim-audit.py 中 edit_mode 检测逻辑"""
    if tool_name == 'Edit':
        if not old_str and new_str:
            return 'insert'
        if old_str and not new_str:
            return 'delete'
        if old_str and new_str:
            ratio = len(new_str) / max(1, len(old_str))
            if ratio > 3.0 or ratio < 0.33:
                return 'refactor'
            return 'replace'
    elif tool_name == 'Write':
        return 'write_new' if not old_str else 'write_overwrite'
    return 'unknown'


def compute_edit_scope(old_str: str, new_str: str, content: str = '') -> str:
    """复现 edit_scope 计算逻辑"""
    char_count = max(len(old_str), len(new_str), len(content))
    if char_count < 100:
        return 'small'
    if char_count < 1000:
        return 'medium'
    return 'large'


def compute_patience_score(edit_count: int, unique_hash_count: int) -> float:
    """复现 patience_score 计算逻辑"""
    return round(edit_count / max(1, unique_hash_count), 2)


# ── 辅助 ──

def assert_eq(actual, expected, label: str):
    if actual != expected:
        raise AssertionError(f"FAIL {label}: expected={expected!r}, actual={actual!r}")
    print(f"  PASS {label}")


def assert_true(cond: bool, label: str):
    if not cond:
        raise AssertionError(f"FAIL {label}: condition False")
    print(f"  PASS {label}")


# ── Test 1: edit_mode 分类 ──

def test_edit_mode_insert():
    """Edit: old=空, new=有内容 → insert"""
    mode = detect_edit_mode('Edit', '', 'def foo(): pass')
    assert_eq(mode, 'insert', 'insert')


def test_edit_mode_replace():
    """Edit: old+new 长度比在 [0.33, 3.0] 内 → replace"""
    mode = detect_edit_mode('Edit', 'line1', 'line2')
    assert_eq(mode, 'replace', 'replace same length')

    mode2 = detect_edit_mode('Edit', 'short', 'still_short_ok')
    assert_eq(mode2, 'replace', 'replace ratio=2')


def test_edit_mode_refactor_growth():
    """Edit: new >> old（ratio > 3）→ refactor"""
    mode = detect_edit_mode('Edit', 'short', 'a' * 200)
    assert_eq(mode, 'refactor', 'refactor growth')


def test_edit_mode_refactor_shrink():
    """Edit: new << old（ratio < 0.33）→ refactor"""
    mode = detect_edit_mode('Edit', 'a' * 200, 'short')
    assert_eq(mode, 'refactor', 'refactor shrink')


def test_edit_mode_delete():
    """Edit: old + new=空 → delete"""
    mode = detect_edit_mode('Edit', 'something', '')
    assert_eq(mode, 'delete', 'delete')


def test_edit_mode_write_new():
    """Write: 无 old 内容 → write_new"""
    mode = detect_edit_mode('Write', '', '{"key": "val"}')
    assert_eq(mode, 'write_new', 'write new file')


def test_edit_mode_write_overwrite():
    """Write: 有旧内容 → write_overwrite"""
    mode = detect_edit_mode('Write', 'old content', 'new content')
    assert_eq(mode, 'write_overwrite', 'write overwrite')


def test_edit_mode_unknown():
    """非 Edit/Write 工具 → unknown"""
    mode = detect_edit_mode('Read', '', '')
    assert_eq(mode, 'unknown', 'unknown tool → unknown mode')


# ── Test 2: edit_scope 规模 ──

def test_edit_scope_small():
    """<100 字符 → small"""
    assert_eq(compute_edit_scope('hello', 'world'), 'small', 'small edit')


def test_edit_scope_medium():
    """100-999 字符 → medium"""
    body = 'x' * 150
    assert_eq(compute_edit_scope(body, ''), 'medium', 'medium edit')


def test_edit_scope_large():
    """≥1000 字符 → large"""
    body = 'x' * 1000
    assert_eq(compute_edit_scope(body, ''), 'large', 'large edit exactly 1000')

    body2 = 'x' * 2000
    assert_eq(compute_edit_scope('', body2), 'large', 'large edit 2000 chars')


def test_edit_scope_uses_max():
    """scope 取 old/new/content 的最大值"""
    # old=50, new=200 → 取 200 → medium
    assert_eq(compute_edit_scope('x' * 50, 'y' * 200), 'medium', 'scope picks max')


# ── Test 3: patience_score 收敛度 ──

def test_patience_perfect():
    """每次编辑 hash 都不同 → patience=1.0"""
    # 3 次编辑, 3 个唯一 hash
    score = compute_patience_score(3, 3)
    assert_eq(score, 1.0, 'perfect convergence')


def test_patience_bad():
    """同一内容反复编辑 → 编辑多但唯一 hash 少 → patience > 1"""
    score = compute_patience_score(10, 2)
    assert_eq(score, 5.0, 'poor convergence (10 edits, 2 unique)')


def test_patience_idempotent():
    """单次编辑 → patience=1.0"""
    score = compute_patience_score(1, 1)
    assert_eq(score, 1.0, 'single edit')


def test_patience_zero_protection():
    """避免除零错误"""
    score = compute_patience_score(100, 0)
    assert_eq(score, 100.0, 'zero unique hash → safe')


# ── Test 4: 集成场景 ──

def test_scenario_code_review():
    """模拟 code review 多轮修改场景"""
    # 第一轮: replace small
    m1 = detect_edit_mode('Edit', 'old_func()', 'new_func(x)')
    s1 = compute_edit_scope('old_func()', 'new_func(x)')
    assert_eq(m1, 'replace', 'review: replace line')
    assert_eq(s1, 'small', 'review: small edit')

    # 第二轮: refactor large
    old_block = '\n'.join(f'line{i}' for i in range(30))
    new_block = old_block + '\n# extra comment\n# more comments'
    m2 = detect_edit_mode('Edit', old_block, new_block)
    s2 = compute_edit_scope(old_block, new_block)
    assert_eq(m2, 'replace', 'review: small addition stays replace')
    assert_eq(s2, 'medium', 'review: medium scope')

    # 大幅重写
    huge_new = '\n'.join(f'new_line{i}' for i in range(100))
    m3 = detect_edit_mode('Edit', old_block, huge_new)
    s3 = compute_edit_scope(old_block, huge_new)
    assert_eq(m3, 'refactor', 'review: huge rewrite → refactor')
    assert_eq(s3, 'large', 'review: huge rewrite → large')


# ── 入口 ──

if __name__ == "__main__":
    print("=== test-edit-churn-quality: edit_mode / edit_scope / patience_score ===")

    print("\n--- edit_mode 分类 ---")
    test_edit_mode_insert()
    test_edit_mode_replace()
    test_edit_mode_refactor_growth()
    test_edit_mode_refactor_shrink()
    test_edit_mode_delete()
    test_edit_mode_write_new()
    test_edit_mode_write_overwrite()
    test_edit_mode_unknown()

    print("\n--- edit_scope 规模 ---")
    test_edit_scope_small()
    test_edit_scope_medium()
    test_edit_scope_large()
    test_edit_scope_uses_max()

    print("\n--- patience_score 收敛度 ---")
    test_patience_perfect()
    test_patience_bad()
    test_patience_idempotent()
    test_patience_zero_protection()

    print("\n--- 集成场景 ---")
    test_scenario_code_review()

    print("\n✅ 全部 test-edit-churn-quality 通过")
    sys.exit(0)
