#!/usr/bin/env python3
"""oracle_models.py — Oracle 模型路由（跟随当前模型 + 分档）。

设计目标：
- 默认跟随当前会话模型（ANTHROPIC_MODEL），兜底 deepseek-v4-flash。
- 有分档（ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL 至少两档存在且取值
  不同）时：静态 Oracle agent 用 sonnet（缺则 haiku），动态 Mate Oracle
  用 opus。
- 无分档（如 deepseek 三档同值）：全部用当前模型。

纯函数模块，不发起网络调用；接入点在调用方（oracle_gate_light /
oracle_agent）。
"""
from __future__ import annotations

import os
from typing import Dict

DEFAULT_MODEL = "deepseek-v4-flash"

TIER_ENV = {
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}

# 动态（运行时验证 / Mate / meta 聚合）→ opus；静态（plan/diff 预检）→ sonnet/haiku
DYNAMIC_ROLES = {"mate", "runtime", "meta"}


def current_model() -> str:
    """当前会话模型。ANTHROPIC_MODEL 优先，兜底 deepseek-v4-flash。"""
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL


def tiered_models() -> Dict[str, str]:
    """读取分档模型名；缺失档位跳过。"""
    return {
        tier: os.environ.get(env, "").strip()
        for tier, env in TIER_ENV.items()
        if os.environ.get(env, "").strip()
    }


def has_tiered_models() -> bool:
    """≥2 档存在且取值不同 → 视为有分档能力。"""
    tiers = tiered_models()
    if len(tiers) < 2:
        return False
    return len(set(tiers.values())) >= 2


def resolve_oracle_model(role: str = "static") -> str:
    """按角色解析 Oracle 应使用的模型名。

    - 无分档 → 当前模型（所有 role 一致）
    - 有分档：
      - 动态角色（mate/runtime/meta）→ opus
      - 静态角色（static/其余）→ sonnet，缺则 haiku
    """
    if not has_tiered_models():
        return current_model()

    tiers = tiered_models()
    if role in DYNAMIC_ROLES:
        return tiers.get("opus") or current_model()
    return tiers.get("sonnet") or tiers.get("haiku") or current_model()
