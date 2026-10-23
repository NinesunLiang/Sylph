"""D-019 回归锚点：Mate-Oracle 必须排在 Oracle 静态通过之后。离线，无网络。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle_agent  # noqa: E402


def _write(dir_: Path, name: str, verdict: dict) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / name).write_text(
        json.dumps({"target": dir_.name, "verdict": verdict}), encoding="utf-8")


def test_no_static_verdict_blocks_mate(monkeypatch, tmp_path):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    assert oracle_agent._static_pass_exists("t1") is False


def test_static_accept_unlocks_mate(monkeypatch, tmp_path):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    _write(tmp_path / "t1", "1.json", {"mode": "static", "verdict": "ACCEPT"})
    assert oracle_agent._static_pass_exists("t1") is True


def test_static_advisory_also_unlocks(monkeypatch, tmp_path):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    _write(tmp_path / "t1", "1.json", {"mode": "static", "verdict": "ADVISORY"})
    assert oracle_agent._static_pass_exists("t1") is True


def test_static_reject_does_not_unlock(monkeypatch, tmp_path):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    _write(tmp_path / "t1", "1.json", {"mode": "static", "verdict": "REJECT"})
    assert oracle_agent._static_pass_exists("t1") is False


def test_runtime_verdict_does_not_count_as_static(monkeypatch, tmp_path):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    _write(tmp_path / "t1", "1.json", {"mode": "runtime", "verdict": "ACCEPT"})
    assert oracle_agent._static_pass_exists("t1") is False


def test_duo_mode_refused_without_static_pass(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(oracle_agent, "ORACLE_VERDICTS_DIR", tmp_path)
    rc = oracle_agent.cmd_review(["--task-id", "t1", "--mode", "duo"])
    out = capsys.readouterr().out
    assert rc == 2, out
    assert "mate_requires_static_pass" in out
