from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / ".claude/skills/lx-stepwise/scripts/lx-stepwise.py"
spec = importlib.util.spec_from_file_location("lx_stepwise_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_card(cards_dir: Path, card_id: str, next_card: str | None = None) -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)
    (cards_dir / f"{card_id}.yaml").write_text(
        "card:\n"
        f"  id: {card_id}\n"
        "  title: test\n"
        "  exit_criteria:\n"
        "    - one\n"
        "  outputs:\n"
        "    required: []\n"
        f"  next_card: {next_card or 'null'}\n",
        encoding="utf-8",
    )


def _write_state(state_dir: Path, task_id: str = "stepwise-test") -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{task_id}.json"
    path.write_text(
        json.dumps({
            "task_id": task_id,
            "current_card": "C08",
            "passed": [],
            "status": "active",
            "outputs": {},
            "confirmed": {},
            "evidence": {},
            "validation_results": [],
        }, indent=2),
        encoding="utf-8",
    )
    return path


def test_pass_card_gate_failure_keeps_state_bytes(tmp_path, monkeypatch):
    cards = tmp_path / "cards"
    state_dir = tmp_path / "state"
    _write_card(cards, "C08")
    state_path = _write_state(state_dir)
    monkeypatch.setattr(module, "CARDS_DIR", cards)
    monkeypatch.setattr(module, "STATE_DIR", state_dir)

    args = argparse.Namespace(card="C08", confirm=[], output=[], evidence="")
    before = state_path.read_bytes()
    with pytest.raises(SystemExit):
        module.cmd_pass(args)

    assert state_path.read_bytes() == before


def test_pass_card_render_failure_does_not_commit_next_card(tmp_path, monkeypatch):
    cards = tmp_path / "cards"
    state_dir = tmp_path / "state"
    _write_card(cards, "C08", next_card="C09")
    state_path = _write_state(state_dir)
    monkeypatch.setattr(module, "CARDS_DIR", cards)
    monkeypatch.setattr(module, "STATE_DIR", state_dir)

    args = argparse.Namespace(card="C08", confirm=[1], output=[], evidence="verified")
    before = state_path.read_bytes()
    with pytest.raises(SystemExit):
        module.cmd_pass(args)

    assert state_path.read_bytes() == before
