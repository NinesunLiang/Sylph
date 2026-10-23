#!/usr/bin/env python3
"""state_transitions.py — 任务级状态机转换契约（ADR 0015）。

从 schemas/contract/state_transitions.yaml 读取合法转换表，提供：
  - is_legal(from, to): 查询是否合法
  - require_transition(from, to): 非法转换抛 ValueError（强制 gate）
  - states(): 返回声明状态集

fail-fast: YAML 缺失 / 无 transitions 段直接抛错，不静默 fallback。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "contract" / "state_transitions.yaml"


def _load() -> dict[str, Any]:
    path = _SCHEMA_PATH
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "transitions" not in data:
        raise ValueError(f"state_transitions.yaml missing 'transitions' section: {path}")
    return data


_data = _load()
_LEGAL: set[tuple[str, str]] = {(t["from"], t["to"]) for t in _data.get("transitions", [])}
_STATES: list[str] = list(_data.get("states", []))


def is_legal(from_state: str, to_state: str) -> bool:
    """查询 (from, to) 是否在合法转换表内。"""
    return (from_state, to_state) in _LEGAL


def require_transition(from_state: str, to_state: str) -> None:
    """强制 gate：非法转换抛 ValueError。

    在 verify/archive 的完成判定处调用：任务完成转换必须是 YAML 声明的合法转换。
    """
    if not is_legal(from_state, to_state):
        raise ValueError(f"illegal state transition: {from_state} -> {to_state}")


def states() -> list[str]:
    """返回 YAML 声明的状态集。"""
    return list(_STATES)
