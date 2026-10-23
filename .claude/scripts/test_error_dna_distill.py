"""test_error_dna_distill.py — 错误 DNA 蒸馏闭环（审计 C1：学习飞轮断链的解药）

回归锚点：index48（2026-09-10）移除 error-dna hook 后 `.omc/state/error-dna.jsonl`
断流，83 条存量永久无人提炼 → 失败模式只进不出。archive 挂钩后每次归档自动蒸馏。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".claude" / "scripts"))
import error_dna_distill as ed  # noqa: E402


def _mk(root: Path, n: int, etype: str = "bash_path_not_found"):
    (root / ".omc" / "state").mkdir(parents=True)
    recs = [{
        "signature": f"sig{i:04d}", "error_type": etype, "cmd": f"ls /bad{i}",
        "message": f"ls: /bad{i}: No such file or directory", "exit_code": 2,
        "retry_count": i % 5,
    } for i in range(n)]
    (root / ".omc" / "state" / "error-dna.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")


def test_below_threshold_no_draft(tmp_path):
    _mk(tmp_path, 5)
    rc = ed.main(["--root", str(tmp_path), "--threshold", "20"])
    assert rc == 0
    assert not (tmp_path / ".omc" / "state" / "error-dna-distill").exists()


def test_above_threshold_draft_and_marker(tmp_path):
    _mk(tmp_path, 25)
    rc = ed.main(["--root", str(tmp_path)])
    assert rc == 0
    dist = tmp_path / ".omc" / "state" / "error-dna-distill"
    drafts = list(dist.glob("draft-*.md"))
    assert len(drafts) == 1 and drafts[0].read_text().count("## bash_path_not_found") == 1
    marker = (dist / "last-distilled.jsonl").read_text().split()
    assert len(marker) == 25
    # 再次运行 → 未蒸馏 0 条 → 不再产出新草案（幂等）
    ed.main(["--root", str(tmp_path)])
    assert len(list(dist.glob("draft-*.md"))) == 1
    assert ed.undistilled(ed.load_entries(tmp_path / ".omc" / "state" / "error-dna.jsonl"),
                          dist / "last-distilled.jsonl") == []


def test_dry_run_does_not_mark(tmp_path):
    _mk(tmp_path, 21)
    rc = ed.main(["--root", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert not (tmp_path / ".omc" / "state" / "error-dna-distill" / "last-distilled.jsonl").exists()


def test_missing_file_exit2(tmp_path):
    assert ed.main(["--root", str(tmp_path)]) == 2


def test_archive_wired():
    """cmd_archive 已挂钩 distill（C1 闭环的接线证据）。"""
    src = (REPO / ".claude" / "scripts" / "carros_base.py").read_text(encoding="utf-8")
    assert "error_dna_distill" in src
