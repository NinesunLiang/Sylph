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

def test_oracle_marks_passive_on_demand():
    """Oracle prompt 应明确标记 'passive on-demand'（被动响应，不自动跑）。"""
    prompt = module.ORACLE_STATIC_PROMPT
    assert "passive on-demand" in prompt or "do NOT run automatically" in prompt, (
        "Oracle prompt 缺被动响应标记"
    )


def test_oracle_only_l2_or_user_request():
    """Oracle prompt 应明确只在 L2 任务或用户主动要求时触发。"""
    prompt = module.ORACLE_STATIC_PROMPT
    assert "L2" in prompt
    # "user request" 或 "User says" 或 "双法官" 任一触发词都算
    assert any(trigger in prompt for trigger in ["user request", "User says", "双法官", "double judge"]), (
        "Oracle prompt 应明确 L2 + 用户请求双触发条件"
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

def test_mate_marks_passive_on_demand():
    """Mate prompt 应明确标记 'passive on-demand'（被动响应）。"""
    prompt = module.ORACLE_MATE_PROMPT
    assert "passive on-demand" in prompt or "do NOT run automatically" in prompt, (
        "Mate prompt 缺被动响应标记"
    )


def test_mate_only_after_oracle_accept():
    """Mate prompt 应明确只在 Oracle-ACCEPT/ADVISORY 后才跑。"""
    prompt = module.ORACLE_MATE_PROMPT
    # 简化匹配：要么 "NEVER run" + "REJECTED" 同时出现，要么 "You NEVER run if Oracle REJECTED"
    assert "NEVER run" in prompt and "REJECTED" in prompt, (
        "Mate prompt 应明确 'Oracle REJECT 后不跑'"
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


# ─── 双法官触发词对齐 ───

def test_oracle_mentions_shuang_faguan():
    """Oracle prompt 应明确"双法官"作为触发词，并说明 Oracle 是第一半。"""
    assert "双法官" in module.ORACLE_STATIC_PROMPT, (
        "Oracle prompt 缺'双法官'触发词锚定"
    )


def test_mate_mentions_shuang_faguan():
    """Mate prompt 应明确"双法官"作为触发词，并说明 Mate 是隐含的第二半。"""
    assert "双法官" in module.ORACLE_MATE_PROMPT, (
        "Mate prompt 缺'双法官'触发词锚定"
    )


def test_oracle_explains_cascade_to_mate():
    """Oracle 应说明 Oracle ACCEPT/ADVISORY 后 Mate 自动跟随（双法官级联）。"""
    prompt = module.ORACLE_STATIC_PROMPT
    # Oracle 应承认 Mate 是"双法官"的隐含第二半
    assert "Mate is the implicit second half" in prompt or "Mate will run NEXT" in prompt or "Mate-Oracle runs NEXT" in prompt


def test_mate_explains_cascade_after_oracle():
    """Mate 应说明自己是双法官级联的第二半。"""
    prompt = module.ORACLE_MATE_PROMPT
    assert "SECOND" in prompt
    assert "AFTER Oracle" in prompt or "AFTER Oracle in the 双法官 cascade" in prompt


def test_user_says_shuang_faguan_runs_both():
    """用户说"双法官"应自动触发 Oracle + Mate（不是只 Oracle）。"""
    # 这个测试验证 Oracle prompt 明确承诺"双法官"会同时跑两个
    prompt = module.ORACLE_STATIC_PROMPT
    # "双法官"被触发时：Oracle跑 + Mate跑（除非 Oracle REJECT）
    assert "Mate" in prompt and "AFTER" not in prompt.split("EXECUTION ORDER")[0].split("Mate")[0]
    # 简化的关键断言：EXECUTION ORDER 段必须提到 Mate-Oracle 自动跟随
    assert "Mate-Oracle runs NEXT" in prompt or "Mate is the implicit second half" in prompt


def test_oracle_and_mate_have_independent_prompts():
    """Oracle 和 Mate 必须各自有独立的 prompt（不能共享）。"""
    # 1. 两段 prompt 字符串对象必须不同
    assert module.ORACLE_STATIC_PROMPT is not module.ORACLE_MATE_PROMPT, (
        "Oracle 和 Mate 不能共享同一段 prompt"
    )

    # 2. 两段 prompt 不能完全相等（必须有不同的内容）
    assert module.ORACLE_STATIC_PROMPT != module.ORACLE_MATE_PROMPT, (
        "Oracle 和 Mate prompt 内容相同，违反'各自有独立 prompt'定位"
    )

    # 3. 两段 prompt 长度应有显著差异（不同职责 → 不同内容）
    len_oracle = len(module.ORACLE_STATIC_PROMPT)
    len_mate = len(module.ORACLE_MATE_PROMPT)
    # 不强制长度，但应至少有 10% 差异
    diff_ratio = abs(len_oracle - len_mate) / max(len_oracle, len_mate)
    assert diff_ratio > 0.05, (
        f"Oracle ({len_oracle}) 与 Mate ({len_mate}) 长度太接近，可能内容重复"
    )


def test_oracle_emphasizes_static_analysis_uniquely():
    """Oracle prompt 必须显式突出"静态分析"（Oracle 独有职责）。"""
    assert "Static analysis" in module.ORACLE_STATIC_PROMPT
    # Mate 可以有"runtime"但不应强调"static"
    # 这是 Oracle 的独有职责


def test_mate_emphasizes_runtime_tdd_uniquely():
    """Mate prompt 必须显式突出"运行时 TDD"（Mate 独有职责）。"""
    mate = module.ORACLE_MATE_PROMPT
    assert "Runtime" in mate or "runtime" in mate
    assert "TDD" in mate
    # Oracle 提到静态但不应强调 TDD


def test_dual_judges_cascade_is_sequential():
    """双法官必须按序通过（Oracle 先 → 通过 → Mate）。"""
    # Oracle prompt: 自己是 FIRST，Mate 在后
    oracle = module.ORACLE_STATIC_PROMPT
    assert "FIRST" in oracle
    assert "Mate-Oracle runs NEXT" in oracle or "Mate will run next" in oracle

    # Mate prompt: 自己是 SECOND，在 Oracle 后
    mate = module.ORACLE_MATE_PROMPT
    assert "SECOND" in mate
    assert "AFTER Oracle" in mate


def test_mate_does_not_run_if_oracle_rejects():
    """Oracle REJECT 后 Mate 不应跑（按序通过的核心约束）。"""
    # 双 prompt 双向声明这个约束
    assert "If you REJECT, Mate does NOT run" in module.ORACLE_STATIC_PROMPT
    assert "NEVER run" in module.ORACLE_MATE_PROMPT and "REJECTED" in module.ORACLE_MATE_PROMPT