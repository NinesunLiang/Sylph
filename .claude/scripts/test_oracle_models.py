"""Oracle 模型路由模块测试（依赖先行）。

覆盖 lib/oracle_models.py 的 current_model / has_tiered_models /
resolve_oracle_model。设计：跟随当前模型；有分档（opus/sonnet/haiku）时
静态 Oracle 用 sonnet/haiku、动态 Mate 用 opus；无分档全部用当前模型。
"""
import importlib.util
from pathlib import Path

import pytest


LIB = Path(__file__).resolve().parent / "lib" / "oracle_models.py"
spec = importlib.util.spec_from_file_location("oracle_models_under_test", LIB)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """每个用例清空模型相关 env，保证确定性起点。"""
    for key in [
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_current_model_fallback_to_deepseek():
    """无任何 env → 兜底 deepseek-v4-flash。"""
    assert module.current_model() == "deepseek-v4-flash"


def test_current_model_follows_anthropic_model(monkeypatch):
    """ANTHROPIC_MODEL 设置 → 跟随当前模型。"""
    monkeypatch.setenv("ANTHROPIC_MODEL", "opus")
    assert module.current_model() == "opus"


def test_current_model_strips_cc_suffix(monkeypatch):
    """Claude Code 模型带 [1m] 后缀 → 清洗为裸模型名(API 端点不认后缀)。"""
    monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-v4-flash[1m]")
    assert module.current_model() == "deepseek-v4-flash"


def test_tiered_models_strips_suffix(monkeypatch):
    """分档模型值带后缀 → 清洗。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m[1m]")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "sonnet-m[1m]")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "haiku-m")
    tiers = module.tiered_models()
    assert tiers["opus"] == "opus-m"
    assert tiers["sonnet"] == "sonnet-m"
    assert tiers["haiku"] == "haiku-m"


def test_has_tiered_models_false_when_same_value(monkeypatch):
    """三档同值（如 deepseek 全指向同一模型）→ 无分档。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "m")
    assert module.has_tiered_models() is False


def test_has_tiered_models_true_when_distinct(monkeypatch):
    """三档取值不同 → 有分档。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "sonnet-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "haiku-m")
    assert module.has_tiered_models() is True


def test_has_tiered_models_partial_distinct(monkeypatch):
    """两档不同、一档缺失 → 仍为有分档（≥2 档存在且不同）。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "sonnet-m")
    assert module.has_tiered_models() is True


def test_resolve_no_tier_follows_current(monkeypatch):
    """无分档 → 所有 role 都用当前模型。"""
    monkeypatch.setenv("ANTHROPIC_MODEL", "qwen-max")
    for role in ("static", "mate", "runtime", "meta"):
        assert module.resolve_oracle_model(role) == "qwen-max"


def test_resolve_static_uses_sonnet(monkeypatch):
    """有分档 + 静态 → sonnet。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "sonnet-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "haiku-m")
    assert module.resolve_oracle_model("static") == "sonnet-m"


def test_resolve_static_falls_back_haiku(monkeypatch):
    """有分档 + 静态 + sonnet 缺失 → haiku。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "haiku-m")
    assert module.resolve_oracle_model("static") == "haiku-m"


def test_resolve_mate_uses_opus(monkeypatch):
    """有分档 + mate → opus。"""
    monkeypatch.setenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "opus-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "sonnet-m")
    monkeypatch.setenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "haiku-m")
    assert module.resolve_oracle_model("mate") == "opus-m"
    assert module.resolve_oracle_model("runtime") == "opus-m"
    assert module.resolve_oracle_model("meta") == "opus-m"
