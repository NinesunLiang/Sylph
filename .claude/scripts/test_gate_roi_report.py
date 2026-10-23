"""test_gate_roi_report.py — 门禁 ROI 仪表（审计 A3：gate-pass-count 1.3MB 零消费的解药）

回归锚点：2026-09-08 审计 A3「gate-pass-count 无人消费，僵尸门禁只减不查」；
index47 曾靠一次性脚本做过 12 天审计删 9 道门，但无常态仪表，僵尸会再长回来。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".claude" / "scripts"))
import gate_roi_report as g  # noqa: E402


def _mk(root: Path, hook_src: str, events: list[dict]) -> None:
    (root / ".omc" / "state").mkdir(parents=True)
    (root / ".claude" / "hooks").mkdir(parents=True)
    (root / ".omc" / "state" / "gate-pass-count.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
    )
    (root / ".claude" / "hooks" / "pretool-gate.py").write_text(hook_src, encoding="utf-8")


HOOK = '''
_GATE_CORE = [
    ("sensitive-write", _check_a),
    ("quiet-gate", _check_b),
]
_GATE_L2_EXTRA = [
    ("never-fires", _check_c),
]
'''


def test_summarize_zombie_and_stale(tmp_path):
    _mk(tmp_path, HOOK, [
        {"date": "2026-10-01", "gate": "sensitive-write", "mode": "l1", "count": 3},
        {"date": "2026-10-18", "gate": "quiet-gate", "mode": "l1", "count": 1},
        {"date": "2026-10-18", "gate": "deleted-old", "mode": "l1", "count": 9},
    ])
    rep = g.summarize(g.load_events(tmp_path / ".omc/state/gate-pass-count.jsonl"),
                      g.load_registry(tmp_path / ".claude/hooks/pretool-gate.py"), 30)
    # quiet-gate 有 10-18 事件（=as_of）→ 活跃；never-fires 无事件 → 僵尸
    assert "never-fires" in rep["zombies"]
    assert "quiet-gate" not in rep["zombies"]
    assert rep["stale"] == ["deleted-old"]
    assert rep["ranking"][0]["gate"] == "deleted-old"
    assert rep["as_of"] == "2026-10-18"


def test_window_excludes_old_events(tmp_path):
    _mk(tmp_path, HOOK, [
        {"date": "2026-08-01", "gate": "quiet-gate", "mode": "l1", "count": 5},
        {"date": "2026-10-18", "gate": "sensitive-write", "mode": "l1", "count": 1},
    ])
    rep = g.summarize(g.load_events(tmp_path / ".omc/state/gate-pass-count.jsonl"),
                      g.load_registry(tmp_path / ".claude/hooks/pretool-gate.py"), 30)
    # quiet-gate 最后触发 8-01，窗口 30 天外 → 僵尸
    assert "quiet-gate" in rep["zombies"]
    assert "sensitive-write" not in rep["zombies"]


def test_real_repo_report_runs():
    """真实数据端到端：能出报告且不崩（断言形状，非具体数量——数据会增长）。"""
    import subprocess
    out = subprocess.run(
        [sys.executable, str(REPO / ".claude/scripts/gate_roi_report.py"),
         "--root", str(REPO), "--window", "30", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    rep = json.loads(out.stdout)
    assert rep["events"] > 0 and rep["registered"] > 0
    assert isinstance(rep["ranking"], list) and rep["ranking"]
    assert isinstance(rep["zombies"], list)
