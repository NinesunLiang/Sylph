#!/usr/bin/env python3
"""降噪回归（index15）：格式契约放宽但核心防线不弱化。

红→绿目标：
  1. 自然语言 executor（无机器格式字面）通过 validate_step_evidence
  2. 中英断言语义匹配（rule 英文 / EV 断言中文）通过 match_verify_rule
  3. 核心防线保留：空 TDD / 软完成断言仍被拒；Decisions 段已精简不再校验
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from step_contracts import validate_step_evidence
from verify_gate import match_verify_rule, _normalize_i18n


# ── 1. 自然语言 executor 应通过（降噪） ──────────────────────────────
NATURAL_EXECUTOR = """# Executor
## Conditions
任务范围与硬边界已记录。
## Key Changes
改动了 A 文件，新增 B 测试。
## Decisions
- 决策: 采用 TDD 先行，先写红测试再实现，避免重复重试。
## Acceptance Checklist
- [x] 完成基线审计
- [x] 跑通全量回归
## TDD Evidence
- 依赖测试: 运行了 test_x.py 通过，退出码 0
- 回归测试: 全量回归通过，0 失败

### EV-S1
- step: S1
- type: test
- exit_code: 0
- assertion: done
"""


def test_natural_language_executor_passes() -> None:
    errors = validate_step_evidence(NATURAL_EXECUTOR, "S1")
    assert errors == [], f"自然语言 executor 不应被格式拒绝: {errors}"


def test_empty_tdd_still_rejected() -> None:
    """核心防线：TDD 段无命令/无 exit 0 证据仍拒。"""
    executor = NATURAL_EXECUTOR.replace(
        "- 依赖测试: 运行了 test_x.py 通过，退出码 0\n- 回归测试: 全量回归通过，0 失败",
        "- 依赖测试: 待补充\n- 回归测试: 待补充",
    )
    errors = validate_step_evidence(executor, "S1")
    assert any("tdd" in e for e in errors), f"空 TDD 应被拒: {errors}"


def test_placeholder_decisions_no_longer_required() -> None:
    """契约精简（6→3）：Decisions 段不再校验，占位内容不拒。"""
    executor = NATURAL_EXECUTOR.replace(
        "- 决策: 采用 TDD 先行，先写红测试再实现，避免重复重试。",
        "- 待填写",
    )
    errors = validate_step_evidence(executor, "S1")
    assert not any("decisions" in e for e in errors), f"Decisions 段精简后不应再拒: {errors}"


# ── 2. 中英断言语义匹配（降噪） ─────────────────────────────────────
def test_i18n_assertion_match() -> None:
    """rule 英文 'baseline snapshot exists'，EV 断言中文 '基线快照落盘' 应匹配。"""
    evidence = [
        {
            "type": "test", "exit_code": 0,
            "assertion": "baseline snapshot exists and old task states untouched（基线快照落盘且未改任何旧任务状态）",
            "evidence_level": "E2",
        }
    ]
    ok, reason, _ = match_verify_rule(
        "assertion: baseline snapshot exists and old task states untouched", evidence
    )
    assert ok, f"中英断言应匹配: {reason}"


def test_i18n_pure_chinese_assertion_match() -> None:
    """EV 断言纯中文（无英文对照）仍应匹配英文 rule。"""
    evidence = [
        {
            "type": "test", "exit_code": 0,
            "assertion": "基线快照已落盘，且未改动任何旧任务状态",
            "evidence_level": "E2",
        }
    ]
    ok, reason, _ = match_verify_rule(
        "assertion: baseline snapshot exists and old task states untouched", evidence
    )
    assert ok, f"纯中文断言应匹配: {reason}"


def test_soft_completion_still_rejected() -> None:
    """核心防线：软完成断言（'应该好了'）仍拒，即使含中英术语。"""
    evidence = [
        {
            "type": "test", "exit_code": 0,
            "assertion": "baseline snapshot exists 应该好了 我大概确认完成",
            "evidence_level": "E2",
        }
    ]
    ok, _, warnings = match_verify_rule(
        "assertion: baseline snapshot exists and old task states untouched", evidence
    )
    assert not ok, "软完成断言应被拒"
    assert any("soft completion" in w for w in warnings), "应产生 soft-completion 警告"


def test_normalize_i18n_maps_synonyms() -> None:
    assert "baseline" in _normalize_i18n("基线快照落盘")
    assert "evidence" in _normalize_i18n("证据链完整")


def test_partial_term_coverage_rejected() -> None:
    """核心防线：rule 3 术语 clause，断言只含 1 术语 → 拒（部分覆盖不通过）。"""
    ok, reason, _ = match_verify_rule(
        "assertion: baseline snapshot; evidence recorded; report generated",
        [{"type": "test", "assertion": "基线快照落盘了", "evidence_level": "E2", "exit_code": 0}],
    )
    assert not ok, f"部分术语覆盖不应通过: {reason}"


def test_all_terms_reordered_matches() -> None:
    """语义匹配：全术语乱序 + 结构词缺失仍通过（跨语言覆盖）。"""
    ok, reason, _ = match_verify_rule(
        "assertion: baseline snapshot; evidence recorded",
        [{"type": "test", "assertion": "证据已记录，基线快照也落盘了", "evidence_level": "E2", "exit_code": 0}],
    )
    assert ok, f"全术语乱序应通过: {reason}"


if __name__ == "__main__":
    test_natural_language_executor_passes()
    test_empty_tdd_still_rejected()
    test_placeholder_decisions_no_longer_required()
    test_i18n_assertion_match()
    test_i18n_pure_chinese_assertion_match()
    test_soft_completion_still_rejected()
    test_normalize_i18n_maps_synonyms()
    test_partial_term_coverage_rejected()
    test_all_terms_reordered_matches()
    print("ALL DENOISE TESTS PASS")
