"""test_error_dna_retry_gate.py — 确定性错误提前阻断重试（提案 p-...-002 落地）

bash_path_not_found 类错误重试无益（error-dna 实测同一路径重试 67 次）。
确定性根因（路径不存在/语法/导入/命令缺失/权限）出现 ≥2 次即阻断并给修复指引。
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

_LIB = Path(__file__).resolve().parent / "lib" / "error_dna.py"
_spec = importlib.util.spec_from_file_location("error_dna", _LIB)
_error_dna = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_error_dna)
check_retry_gate = _error_dna.check_retry_gate


def _mk_dna(tmp: Path, rows: list[dict]) -> Path:
    p = tmp / "error-dna.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def test_deterministic_path_error_blocks_early():
    """bash_path_not_found 连续出现(带 retry_count) → 提前阻断并给修复指引。"""
    with tempfile.TemporaryDirectory() as td:
        rows = [
            {"ts": 1, "step": "S1", "error_type": "bash_path_not_found", "retry_count": 1, "cmd": "cat /nope", "error": "x"},
            {"ts": 2, "step": "S1", "error_type": "bash_path_not_found", "retry_count": 2, "cmd": "cat /nope", "error": "x"},
        ]
        _mk_dna(Path(td), rows)
        allowed, cnt, msg = check_retry_gate(Path(td), "S1")
        assert allowed is False, f"确定性错误应提前阻断: {msg}"
        assert "路径" in msg or "确定性" in msg or "根因" in msg, f"应给修复指引: {msg}"


def test_non_deterministic_errors_not_prematurely_blocked():
    """非确定性错误(如 network_error)不因 1-2 次就提前阻断(交给 MAX 通用闸)。"""
    with tempfile.TemporaryDirectory() as td:
        rows = [
            {"ts": 1, "step": "S1", "error_type": "network_error", "retry_count": 1, "cmd": "curl", "error": "x"},
            {"ts": 2, "step": "S1", "error_type": "network_error", "retry_count": 1, "cmd": "curl", "error": "x"},
        ]
        _mk_dna(Path(td), rows)
        allowed, cnt, msg = check_retry_gate(Path(td), "S1")
        assert allowed is True, f"网络类不提前阻断(未到 MAX): {msg}"


def test_deterministic_single_occurrence_not_blocked():
    """仅 1 次确定性错误不阻断(容忍偶发)，≥2 次才判定。"""
    with tempfile.TemporaryDirectory() as td:
        rows = [{"ts": 1, "step": "S1", "error_type": "bash_path_not_found", "retry_count": 1, "cmd": "cat /nope", "error": "x"}]
        _mk_dna(Path(td), rows)
        allowed, _, msg = check_retry_gate(Path(td), "S1")
        assert allowed is True, f"单次不应阻断: {msg}"
