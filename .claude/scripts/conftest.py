"""conftest.py — 测试默认离线，不调用真实判官。

背景（2026-10-18）：JEV 判官接通真实 key 后，
`test_state_transitions_gate_integration` 等端到端测试会真的发网络请求：
全量测试 9s → 84s，且每跑一次都花钱、结果依赖网络。

纪律：测试必须确定、离线、可重复。需要真实调用的测试自行 monkeypatch.setenv。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# 账本隔离：必须在 jev_fit / jev_verify_loop 被导入前设置，
# 否则测试会把「step 验收」记录写进真实案例史（实测污染 9 条）。
os.environ.setdefault(
    "CARROROS_JEV_LEDGER",
    str(Path(tempfile.mkdtemp(prefix="carroros-jev-")) / "reviews.jsonl"),
)


@pytest.fixture(autouse=True)
def _offline_judge(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
