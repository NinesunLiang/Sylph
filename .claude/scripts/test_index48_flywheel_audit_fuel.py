"""index48：飞轮换燃料 —— error-dna → 门禁审计遥测。

背景（人类裁决「接活：换真燃料」）：
  `lib/flywheel.py` 原唯一输入为 `error-dna.jsonl`。该机制已于同日整体移除
  （83 条记录 100% pending、`.omc/knowledge/` 产出 0、数据 81% 为测试噪声）。
  且整条链历史产出为 0：`.omc/knowledge/claude-next.md` 与
  `.omc/state/anti-pattern-redirects.jsonl` 均不存在。

新燃料：`.omc/state/audit/*.jsonl` —— 真实存在（近 4000 条）、由 pretool-gate 每次
拦截/放行时写入。其中「反复出现的拦截原因」即值得固化的反模式原料。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "flywheel_under_test", ROOT / ".claude" / "scripts" / "lib" / "flywheel.py")
assert _spec is not None and _spec.loader is not None
FW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FW)


def _mk_audit(project: Path, events: list[dict]) -> None:
    d = project / ".omc" / "state" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    (d / "2026-09-10.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")


def _ev(gate: str, decision: str, reason: str = "") -> dict:
    return {"actor": "hook:pretool-gate", "event_type": "gate_decision", "gate": gate,
            "decision": decision, "reason": reason, "timestamp": "2026-09-10T00:00:00+00:00"}


def test_read_audit_events_reads_jsonl(tmp_path):
    _mk_audit(tmp_path, [_ev("sensitive-read", "ASK_USER"), _ev("action", "BLOCK")])
    events = FW.read_audit_events(tmp_path / ".omc" / "state", n=10)
    assert len(events) == 2


def test_read_audit_events_missing_dir_is_empty(tmp_path):
    assert FW.read_audit_events(tmp_path / "nope") == []


def test_extract_patterns_clusters_recurring_interventions():
    events = [_ev("doc-reference-before-delete", "REDIRECT") for _ in range(5)]
    events += [_ev("action", "BLOCK")]
    patterns = FW.extract_patterns(events)
    recurring = [p for p in patterns if p["count"] >= 3]
    assert len(recurring) == 1, f"应仅 1 个反复模式: {patterns}"
    assert "doc-reference-before-delete" in recurring[0]["error"]


def test_run_flywheel_writes_claude_next_from_audit_fuel(tmp_path):
    _mk_audit(tmp_path, [_ev("doc-reference-before-delete", "REDIRECT") for _ in range(4)])
    result = FW.run_flywheel(tmp_path)
    assert result["patterns_found"] >= 1, result
    assert result["knowledge_entries"] >= 1, result
    assert (tmp_path / ".omc" / "knowledge" / "claude-next.md").exists()


def test_run_flywheel_no_fuel_is_graceful(tmp_path):
    result = FW.run_flywheel(tmp_path)
    assert result["patterns_found"] == 0
    assert not (tmp_path / ".omc" / "knowledge" / "claude-next.md").exists()


def test_run_flywheel_ignores_legacy_error_dna(tmp_path):
    """燃料已换：即使存在 error-dna.jsonl，也不得再被消费。"""
    state = tmp_path / ".omc" / "state"
    state.mkdir(parents=True)
    (state / "error-dna.jsonl").write_text(
        json.dumps({"error_type": "x", "resolution": "pending"}) + "\n", encoding="utf-8")
    result = FW.run_flywheel(tmp_path)
    assert result["patterns_found"] == 0, "error-dna 不得再作为燃料"
