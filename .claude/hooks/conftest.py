"""conftest.py — 测试隔离：真实审批票不得影响门禁断言。

P0 治理加固（2026-10-18）：治理写入改为「无票即拒绝」后，如果开发者本地留着一张
真实审批票，同一个测试在不同机器/不同时刻会得到不同结果。测试必须确定性，所以这里
默认把票指向一个不存在的路径；需要票的测试自行用 monkeypatch 覆盖。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# 2026-10-18：测试 spawn 的 hook 不得写真实审计 / 重定向状态。
# 必须在 pretool_gates.constants 被导入前设置（conftest 先于测试模块加载）。
os.environ.setdefault(
    "CARROROS_AUDIT_DIR", str(Path(tempfile.mkdtemp(prefix="carroros-audit-"))))
os.environ.setdefault(
    "CARROROS_REDIRECT_STREAK",
    str(Path(tempfile.mkdtemp(prefix="carroros-streak-")) / "redirect-streak.json"))

# 2026-10-27：测试不得在仓库里留字节码缓存。
# 实证：部分 hook 测试会导入 packaging/template 下的脚本，生成的 __pycache__/*.pyc
# 落在已提交的模板目录里 → test_template_matches_source 报「模板多出文件」假红，
# 且脏文件有被误提交的风险。父/子进程一起关，子进程继承 os.environ。
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


@pytest.fixture(autouse=True)
def _isolate_governance_ticket(monkeypatch, tmp_path):
    monkeypatch.setenv("CARROROS_GOV_TICKET", str(tmp_path / "no-ticket.json"))


@pytest.fixture(autouse=True)
def _offline_judge(monkeypatch):
    """测试默认离线：移除判官 key，避免真实网络调用/花钱/非确定性。"""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
