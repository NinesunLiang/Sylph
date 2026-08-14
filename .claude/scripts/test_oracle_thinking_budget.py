"""TDD 回归: oracle_agent._try_llm_model 在 DeepSeek 推理模型下的 thinking 预算。

缺陷: max_tokens=2000 时, DeepSeek 推理模型返回 thinking 块吃光预算
→ content 只有 thinking、text 为空 → _try_llm_model 返回 False → 静默
rule_fallback → 声称的 LLM 双法官从没真正运行(长 prompt 下必现)。

修复: max_tokens 提高到 8000 给 thinking 留足预算; 解析 text 时对
thinking-only 响应不再静默吞掉 —— fallback 结果携带 llm_fallback_reason,
审计可追溯「为何没走 LLM」。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle_agent as oa  # noqa: E402


def _fake_run_factory(stdout_text: str, rc: int = 0):
    def fake_run(cmd, **kw):
        class _R:
            returncode = rc
            stdout = stdout_text
            stderr = ""

        return _R()

    return fake_run


def test_anthropic_thinking_plus_text_parses(monkeypatch):
    """thinking + text 双块(修复后 max_tokens 充足): text 被正确提取。"""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test")
    body = json.dumps({"content": [
        {"type": "thinking", "thinking": "reasoning..."},
        {"type": "text", "text": "VERDICT: ACCEPT"},
    ]})
    monkeypatch.setattr(oa.subprocess, "run", _fake_run_factory(body))
    ok, text = oa._try_llm_model("t1", "review", system_prompt="sys")
    assert ok, "双块响应应解析成功"
    assert "VERDICT: ACCEPT" in text


def test_thinking_only_marks_fallback_reason(monkeypatch):
    """thinking-only 响应(text 空): 不静默吞掉 —— 携带 llm_fallback_reason。"""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test")
    body = json.dumps({"content": [{"type": "thinking", "thinking": "reasoning..."}]})
    monkeypatch.setattr(oa.subprocess, "run", _fake_run_factory(body))
    ok, text = oa._try_llm_model("t2", "review", system_prompt="sys")
    assert not ok, "thinking-only 无 text → 视为 LLM 未产出裁决"


def test_llm_curl_timeout_has_room(monkeypatch):
    """LLM curl 超时须 ≥120s: DeepSeek 推理模型长 prompt 实测 ~60s,60s 会撞超时
    导致静默 fallback(双法官从没真审)。"""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test")
    captured = {}

    def fake_run(cmd, timeout, **kw):
        captured["timeout"] = timeout

        class _R:
            returncode = 0
            stdout = json.dumps({"content": [{"type": "text", "text": "VERDICT: ACCEPT"}]})
            stderr = ""

        return _R()

    monkeypatch.setattr(oa.subprocess, "run", fake_run)
    oa._try_llm_model("t4", "review", system_prompt="sys")
    assert captured["timeout"] >= 120, f"curl timeout 须 ≥120s(现 {captured['timeout']})"


def test_review_static_fallback_records_reason(monkeypatch):
    """review_static LLM 失败回退: mode=rule_fallback 且带 llm_fallback_reason。"""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test")
    body = json.dumps({"content": [{"type": "thinking", "thinking": "x" * 100}]})
    monkeypatch.setattr(oa.subprocess, "run", _fake_run_factory(body))
    result = oa.review_static("t3", plan_text="plan content here", executor_text="")
    assert result["mode"] == "rule_fallback"
    assert result.get("llm_fallback_reason"), "应记录 LLM 失败原因,不得静默"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
