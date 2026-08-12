"""S7 治理补引导回归：拦截输出附加"正确做法"引导段（还债项）。

拦截不应只给"拒绝 + 绕过选项"，还要给"下一步怎么做才对"的引导。
"""
import io
import json
import sys

from . import helpers


def _capture_block(reason: str, suggestion: str = "") -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        helpers._block(reason, suggestion)
    finally:
        sys.stdout = old
    out = json.loads(buf.getvalue())
    return out["hookSpecificOutput"]["additionalContext"]


def test_block_action_loop_attaches_guidance():
    ctx = _capture_block("action_loop: 已连续 3 次长命令执行", "1. 使用临时 bypass")
    assert "正确做法" in ctx
    assert "停止重试" in ctx


def test_block_unknown_reason_has_no_guidance():
    ctx = _capture_block("某未知名原因", "1. 调整计划")
    assert "正确做法" not in ctx


def test_redirect_attaches_guidance():
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        helpers._redirect("cd_churn: 连续 cd", "请确认目标目录")
    finally:
        sys.stdout = old
    out = json.loads(buf.getvalue())
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "REDIRECT:" in ctx
    assert "正确做法" in ctx


def test_next_better_step_uses_dynamic_redirect_rules(monkeypatch, tmp_path):
    """S8：动态 anti-pattern-redirects.jsonl（flywheel 学习源）被 helper 消费。"""
    import json as _json

    from . import oracle

    rule_file = tmp_path / "anti-pattern-redirects.jsonl"
    rule_file.write_text(
        _json.dumps({"pattern_key": "bash_retry_repeat", "guidance": "动态引导: 先归因再重试"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_PATH", rule_file)
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_CACHE", None)
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_CACHE_AT", 0.0)
    assert helpers._next_better_step("bash_retry_repeat 触发") == "动态引导: 先归因再重试"


def test_next_better_step_static_priority_over_dynamic(monkeypatch, tmp_path):
    """静态映射优先于动态规则（少即是多：高频场景走稳定引导）。"""
    import json as _json

    from . import oracle

    rule_file = tmp_path / "anti-pattern-redirects.jsonl"
    rule_file.write_text(
        _json.dumps({"pattern_key": "cd_churn", "guidance": "动态: 不要空 cd"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_PATH", rule_file)
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_CACHE", None)
    monkeypatch.setattr(oracle, "_ANTI_PATTERN_REDIRECTS_CACHE_AT", 0.0)
    assert helpers._next_better_step("cd_churn 触发") == "确认目标目录后直接执行目标命令，不要连续空 cd 导航。"
