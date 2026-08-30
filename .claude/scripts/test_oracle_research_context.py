"""test_oracle_research_context.py — 双法官看 research 红测试

修复问题 B：Mate-Oracle（runtime review）当前看不到 research.md，
导致它不知道"plan/executor 承诺了什么"，无法判断实际 diff 是否越界。

Oracle (static) 同样需要 research：判断"承诺范围"vs"实际改动"是不是最小。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/scripts")

import oracle_agent as module


# ─── helpers ───

def _capture_target_text(monkeypatch, review_fn, **kwargs):
    """捕获 _try_llm_model 接收的 target_text（验证 research 是否被注入）。"""
    seen = []
    def fake_try_llm(task_id, target_text, system_prompt=""):
        seen.append(target_text)
        return (False, "")  # 返回 False 走 rule-based fallback，target_text 已被捕获
    monkeypatch.setattr(module, "_try_llm_model", fake_try_llm)
    review_fn(task_id="t1", **kwargs)
    return seen[0] if seen else ""


# ─── Oracle (review_static) 看 research ───

def test_oracle_injects_research_text(monkeypatch):
    """review_static 应将 research_text 注入 target_text。"""
    research = "## 依赖树\n- a.py ← b.py\n## 范围: 仅改 src/foo.py"
    target = _capture_target_text(monkeypatch, module.review_static,
                                   plan_text="", executor_text="", diff_text="",
                                   research_text=research)
    assert "Research" in target, f"Oracle 应注入 research。target:\n{target}"
    assert "依赖树" in target, f"research 内容应在 target 中。target:\n{target}"
    assert "范围: 仅改 src/foo.py" in target


def test_oracle_research_truncation(monkeypatch):
    """research 过长应截断（避免超过 LLM 上下文）。"""
    long_research = "x" * 10000
    target = _capture_target_text(monkeypatch, module.review_static,
                                   research_text=long_research)
    assert "x" * 5000 in target or "x" * 3000 in target, "应有部分 research 内容"
    # 截断保护：总长度不应超过 8000（review_static 现有 8000 截断）
    assert len(target) < 15000, f"target 不应过长: {len(target)}"


# ─── Mate-Oracle (review_runtime) 看 research ───

def test_mate_injects_research_text(monkeypatch):
    """review_runtime 应将 research_text 注入 target_text（修复问题 B）。"""
    research = "## 依赖树\n- a.py ← b.py\n## 测试策略: pytest tests/"
    target = _capture_target_text(monkeypatch, module.review_runtime,
                                   executor_text="", logs_text="",
                                   research_text=research)
    assert "Research" in target, f"Mate 应注入 research。target:\n{target}"
    assert "依赖树" in target
    assert "测试策略: pytest tests/" in target


def test_mate_without_research_still_works(monkeypatch):
    """不传 research 时不应报错（向后兼容）。"""
    target = _capture_target_text(monkeypatch, module.review_runtime,
                                   executor_text="executor content",
                                   logs_text="logs content")
    assert "Executor" in target
    assert "Research" not in target, "未传 research 不应注入空内容"


# ─── 双法官 prompt 显式提及 research ───

def test_oracle_static_prompt_mentions_research():
    """ORACLE_STATIC_PROMPT 应提及 research 用于判断"承诺 vs 实际"是否最小。"""
    assert "research" in module.ORACLE_STATIC_PROMPT.lower(), (
        f"ORACLE_STATIC_PROMPT 应提及 research:\n{module.ORACLE_STATIC_PROMPT[:500]}"
    )


def test_mate_prompt_mentions_research():
    """ORACLE_MATE_PROMPT 应提及 research 用于判断测试覆盖承诺的依赖树。"""
    assert "research" in module.ORACLE_MATE_PROMPT.lower(), (
        f"ORACLE_MATE_PROMPT 应提及 research:\n{module.ORACLE_MATE_PROMPT[:500]}"
    )