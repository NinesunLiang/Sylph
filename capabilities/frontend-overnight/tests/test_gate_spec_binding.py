"""test_gate_spec_binding.py — P7 门禁 spec↔实现绑定（审计 D10 根因：门禁通过但判据未实现）

先红后绿（2026-10-23）：
  红 = 实现脚本少声明一个判据 → check_spec 报 GATE_SPEC_MISMATCH 缺项
  绿 = 真实仓库 gate-spec.yaml 的全部 gate 实现⊇spec（run_gate 标记行 + evidence_check）
"""
from __future__ import annotations
import sys
from pathlib import Path

WF_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WF_ROOT / "scripts" / "carroros-gates"))
import gate_spec_check as gsc  # noqa: E402


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_red_missing_check_is_mismatch(tmp_path):
    """实现少声明 no-console-error → 必须报缺项（红灯）。"""
    _write(tmp_path / "gate-spec.yaml",
           "gates:\n  C6:\n    impl: c6_impl.py\n    checks: [worst-regions-converged, no-console-error]\n")
    _write(tmp_path / "gates" / "c6_impl.py",
           '#!/usr/bin/env python3\n# GATE_CHECKS C6: worst-regions-converged\n')
    missing, report = gsc.check_spec(tmp_path / "gate-spec.yaml", tmp_path / "gates")
    assert any("no-console-error" in m and "C6" in m for m in missing), missing
    assert report["C6"]["ok"] is False


def test_green_full_coverage(tmp_path):
    """实现 ⊇ spec → 零缺项（绿灯）。"""
    _write(tmp_path / "gate-spec.yaml",
           "gates:\n  C6:\n    impl: c6_impl.py\n    checks: [worst-regions-converged, no-console-error]\n")
    _write(tmp_path / "gates" / "c6_impl.py",
           "# GATE_CHECKS C6: worst-regions-converged no-console-error\n")
    missing, report = gsc.check_spec(tmp_path / "gate-spec.yaml", tmp_path / "gates")
    assert missing == [] and report["C6"]["ok"] is True


def test_missing_impl_file_is_mismatch(tmp_path):
    _write(tmp_path / "gate-spec.yaml",
           "gates:\n  C9:\n    impl: ghost.py\n    checks: [x]\n")
    missing, _ = gsc.check_spec(tmp_path / "gate-spec.yaml", tmp_path / "gates")
    assert any("C9" in m and "实现文件缺失" in m for m in missing), missing


def test_real_repo_spec_bound():
    """真实仓库：gate-spec.yaml 存在且全部 gate 实现⊇spec（C6 注册行在 run_gate.py）。"""
    spec = WF_ROOT / "gate-spec.yaml"
    assert spec.is_file(), "gate-spec.yaml 缺失"
    missing, report = gsc.check_spec(spec, WF_ROOT / "scripts" / "carroros-gates")
    assert missing == [], f"GATE_SPEC_MISMATCH: {missing}"
    assert set(report) >= {"C2", "C4", "C5", "C6", "C7"}
    assert "no-console-error" in report["C6"]["declared"]
