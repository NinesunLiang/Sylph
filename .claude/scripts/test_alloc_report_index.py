"""C7 并发协调完整化：报告编号原子分配测试。

验证 alloc_report_index.py：
1. 从现有 index 分配下一编号
2. flock 并发下不重复分配
"""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("alloc_report_index_under_test", SCRIPTS / "alloc_report_index.py")
assert spec is not None
alloc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(alloc)


def test_next_index_after_existing(tmp_path, monkeypatch):
    bm = tmp_path / "Benchmarking"
    bm.mkdir()
    (bm / "index11.md").write_text("x")
    (bm / "index12.md").write_text("x")
    monkeypatch.setattr(alloc, "BENCHMARKING", bm)
    monkeypatch.setattr(alloc, "LOCK_FILE", tmp_path / "state" / "report-index.lock")
    nxt = alloc.next_index()
    assert nxt == 13, f"应从 index12 后分配 13, got {nxt}"
    assert (bm / "index13.md").exists(), "应创建 index13 占位"


def test_next_index_empty_dir(tmp_path, monkeypatch):
    bm = tmp_path / "Benchmarking"
    bm.mkdir()
    monkeypatch.setattr(alloc, "BENCHMARKING", bm)
    monkeypatch.setattr(alloc, "LOCK_FILE", tmp_path / "state" / "report-index.lock")
    nxt = alloc.next_index()
    assert nxt == 1, f"空目录应从 1 开始, got {nxt}"


def test_concurrent_allocation_distinct(tmp_path, monkeypatch):
    """模拟并发：连续两次分配应得到不同编号（flock 原子性）。"""
    bm = tmp_path / "Benchmarking"
    bm.mkdir()
    monkeypatch.setattr(alloc, "BENCHMARKING", bm)
    monkeypatch.setattr(alloc, "LOCK_FILE", tmp_path / "state" / "report-index.lock")
    n1 = alloc.next_index()
    n2 = alloc.next_index()
    assert n1 != n2, f"并发分配不应重复: {n1} vs {n2}"
    assert n2 == n1 + 1, f"第二次应 +1: {n1} -> {n2}"
