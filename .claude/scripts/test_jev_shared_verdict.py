"""Contract tests for shared semantic verdict normalization."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".claude/scripts/jev_sweep.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_shared_classifier_matches_noul_and_choice_edges():
    jev = _load("jev_shared_verdict")
    assert jev.classify_answer({"type": "noul", "noul": 0.9}, 0.85, 0.3)["verdict"] == jev.VERDICT_OK
    assert jev.classify_answer({"type": "noul", "noul": "bad"}, 0.85, 0.3)["verdict"] == jev.VERDICT_UNAVAILABLE
    assert jev.classify_answer({"type": "choice", "choice": "符合", "confidence": 0.4}, 0.85, 0.3, 0.55)["verdict"] == jev.VERDICT_UNDECIDED
    assert jev.classify_answer({"type": "choice", "choice": "不符合", "confidence": 0.9}, 0.85, 0.3, 0.55)["verdict"] == jev.VERDICT_BAD


def test_shared_classifier_unknown_primitive_is_insufficient():
    jev = _load("jev_shared_unknown")
    result = jev.classify_answer({"type": "score", "score": 1}, 0.85, 0.3)
    assert result["verdict"] == jev.VERDICT_INSUFFICIENT
