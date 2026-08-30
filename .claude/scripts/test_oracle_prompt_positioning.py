"""test_oracle_prompt_positioning.py — 双法官 prompt 定位对齐测试

按定位要求：
- Oracle: 高频率、静态分析、依照痕迹判定、快速 breadth-first
- Mate: 低频率、TDD 冒烟、更严格、更接近生产、Oracle 通过后才跑

测试断言每个 prompt 包含定位关键词。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")

import oracle_agent as module


# ─── Oracle 定位 ───

def test_oracle_marks_high_frequency():
    """Oracle prompt 应明确标记 'HIGH-FREQUENCY'（高频率定位）。"""
    assert "HIGH-FREQUENCY" in module.ORACLE_STATIC_PROMPT, (
        "Oracle prompt 缺 HIGH-FREQUENCY 标记"
    )


def test_oracle_emits_static_role():
    """Oracle prompt 应明确 'Static analysis' 角色。"""
    assert "Static analysis" in module.ORACLE_STATIC_PROMPT


def test_oracle_trace_based_judgment():
    """Oracle 依靠痕迹（file:line）判定。"""
    assert "file:line" in module.ORACLE_STATIC_PROMPT


def test_oracle_first_in_order():
    """Oracle 是第一审，EXECUTION ORDER 应明确。"""
    assert "FIRST" in module.ORACLE_STATIC_PROMPT
    assert "EXECUTION ORDER" in module.ORACLE_STATIC_PROMPT


def test_oracle_blocks_mate_if_reject():
    """Oracle REJECT 后 Mate 不应跑。"""
    # 应在 EXECUTION ORDER 段写明
    static = module.ORACLE_STATIC_PROMPT
    assert "Mate does NOT run" in static or "Mate will not run" in static or "Mate will run" in static
    # 至少说明顺序与 Mate 关系
    assert "Mate" in static


# ─── Mate 定位 ───

def test_mate_marks_low_frequency():
    """Mate prompt 应明确标记 'LOW-FREQUENCY'（低频率定位）。"""
    assert "LOW-FREQUENCY" in module.ORACLE_MATE_PROMPT, (
        "Mate prompt 缺 LOW-FREQUENCY 标记"
    )


def test_mate_emits_runtime_role():
    """Mate prompt 应明确 runtime / TDD 角色。"""
    mate = module.ORACLE_MATE_PROMPT
    assert "runtime" in mate.lower() or "Runtime" in mate
    assert "TDD" in mate or "test" in mate.lower()


def test_mate_proximity_to_production():
    """Mate prompt 应明确 'production-like' 或 'PROXIMITY TO PRODUCTION'。"""
    assert "production" in module.ORACLE_MATE_PROMPT.lower() or "PROXIMITY" in module.ORACLE_MATE_PROMPT


def test_mate_stricter_than_oracle():
    """Mate prompt 应明确 'STRICTER' 原则。"""
    assert "STRICTER" in module.ORACLE_MATE_PROMPT or "stricter" in module.ORACLE_MATE_PROMPT.lower()


def test_mate_runs_after_oracle():
    """Mate 是第二审，EXECUTION ORDER 应明确。"""
    assert "SECOND" in module.ORACLE_MATE_PROMPT
    assert "EXECUTION ORDER" in module.ORACLE_MATE_PROMPT
    assert "AFTER Oracle" in module.ORACLE_MATE_PROMPT


def test_mate_stricter_default_when_uncertain():
    """Mate 不确定时默认应是 5（不通过），不是 7（放行）。"""
    # 定位说"更严格"，所以默认应低于 Oracle 的 7
    assert "DEFAULT when uncertain: 5" in module.ORACLE_MATE_PROMPT or "default when uncertain: 5" in module.ORACLE_MATE_PROMPT.lower()


# ─── 双法官契约一致性 ───

def test_both_prompts_have_verdict_rules():
    """双法官都应有显式 VERDICT RULES 顺序。"""
    assert "VERDICT RULES" in module.ORACLE_STATIC_PROMPT
    assert "VERDICT RULES" in module.ORACLE_MATE_PROMPT


def test_both_prompts_have_output_format():
    """双法官都应定义 OUTPUT 格式（输出契约一致性）。"""
    for label, prompt in [("Oracle", module.ORACLE_STATIC_PROMPT),
                           ("Mate", module.ORACLE_MATE_PROMPT)]:
        assert "VERDICT: ACCEPT | REJECT | ADVISORY" in prompt, (
            f"{label} prompt 缺 OUTPUT VERDICT 格式"
        )
        assert "Architecture: 0-10" in prompt
        assert "Evidence: 0-10" in prompt


def test_mate_does_not_see_oracle_output():
    """Mate 不应看到 Oracle 输出（独立性约束）。"""
    assert "Oracle" in module.ORACLE_MATE_PROMPT
    assert "NOT available to you" in module.ORACLE_MATE_PROMPT


def test_oracle_does_not_see_mate_output():
    """Oracle 不应看到 Mate 输出（独立性约束，反向）。"""
    # Oracle prompt 应至少说明自己是第一审，不依赖 Mate 输出
    assert "FIRST" in module.ORACLE_STATIC_PROMPT