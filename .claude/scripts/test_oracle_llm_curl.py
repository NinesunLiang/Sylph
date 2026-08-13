"""TDD 回归: oracle_agent._try_llm_model 的 curl 参数构造 — headers 必须带 -H。

缺陷: Anthropic 分支 headers 列表缺 -H 前缀,curl 未发送认证头 → "Authentication Fails (governor)"
→ LLM 恒失败 → 静默 rule_fallback。修复后回归保护。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle_agent as oa  # noqa: E402


def test_anthropic_curl_sends_h_headers(monkeypatch):
    """Anthropic 分支: curl cmd 必须含 -H 与 x-api-key 认证头。"""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test")
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd

        class _R:
            returncode = 0
            stdout = json.dumps({"content": [{"type": "text", "text": "hi"}]})
            stderr = ""

        return _R()

    monkeypatch.setattr(oa.subprocess, "run", fake_run)
    ok, text = oa._try_llm_model("t1", "say hi", system_prompt="sys")
    assert ok and text == "hi", "LLM 应成功"
    cmd = captured["cmd"]
    assert "-H" in cmd, "curl cmd 必须含 -H 前缀"
    assert "x-api-key: sk-test" in " ".join(cmd), "缺 x-api-key 认证头"


def test_deepseek_fallback_still_sends_h(monkeypatch):
    """DeepSeek 回退分支: 仍带 -H(不回归)。"""
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fallback")
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd

        class _R:
            returncode = 0
            stdout = json.dumps({"choices": [{"message": {"content": "ok"}}]})
            stderr = ""

        return _R()

    monkeypatch.setattr(oa.subprocess, "run", fake_run)
    ok, text = oa._try_llm_model("t2", "hi")
    assert ok and text == "ok"
    assert "-H" in captured["cmd"], "回退分支也必须带 -H"


def test_model_suffix_cleaned(monkeypatch):
    """oracle_models: [1m] 后缀清洗(模型名路由回归)。"""
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-v4-flash[1m]")
    from oracle_models import current_model
    assert current_model() == "deepseek-v4-flash"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
