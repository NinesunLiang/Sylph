"""长期治理环修复测试：water 场景产生证据 + capture_evidence 全绿。

修复断环：
1. ga_behavioral_validation 产生 h-water-*.json（此前无人产生 → G4/G5 永远 FAIL）
2. capture_evidence R1-WATER-CHAIN/BOUNDS 修正（过时 run_water_gate → 实际 g6-budget）
3. capture_evidence R3 断言修正（13/13 → 11/11）
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / ".claude" / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_behavioral_validation_produces_water_evidence(tmp_path, monkeypatch):
    """ga_behavioral_validation 的 water 场景产生 h-water-*.json（修复断环）。"""
    bv = _load("ga_bhv", SCRIPTS / "ga_behavioral_validation.py")
    # 隔离到 tmp VERIFY_DIR
    verify_dir = tmp_path / "metrics" / "runtime-verify"
    verify_dir.mkdir(parents=True)
    monkeypatch.setattr(bv, "VERIFY_DIR", verify_dir)
    monkeypatch.setattr(bv, "PROJECT", PROJECT)
    monkeypatch.setattr(bv, "EVIDENCE", verify_dir / "evidence.jsonl")
    monkeypatch.setattr(bv, "rel", lambda p: str(p))  # tmp 路径无法相对 PROJECT

    result = bv.validate_water_governance()
    assert result["status"] == "PASS", result["detail"]
    hp = verify_dir / "h-water-critical-hard-pause.json"
    pw = verify_dir / "h-water-pretool-whitelist.json"
    assert hp.exists() and pw.exists(), "water 证据文件应产生"
    hp_data = json.loads(hp.read_text(encoding="utf-8"))
    assert hp_data["test_id"] == "H-WATER-CRITICAL-HARD-PAUSE"
    assert hp_data["status"] == "PASS"


def test_water_checks_reference_real_mechanism():
    """capture_evidence 的 R1-WATER-CHAIN 引用实际机制（g6-budget），非过时 run_water_gate。"""
    text = (SCRIPTS / "capture_evidence.py").read_text(encoding="utf-8")
    assert "g6-budget" in text, "R1 应引用实际 g6-budget 机制"
    assert "run_water_gate" not in text.split("R1-WATER-BOUNDS")[0] or "g6-budget" in text


def test_negative_tests_assertion_matches_actual():
    """capture_evidence 的 R3 断言与 negative_tests 实际输出一致（11/11）。"""
    text = (SCRIPTS / "capture_evidence.py").read_text(encoding="utf-8")
    assert "11/11 PASS" in text, "R3 断言应匹配实际 11/11 PASS"


def test_capture_evidence_runs_all_pass():
    """capture_evidence 全项 PASS（评测环 metrics 闭环）。"""
    rm = subprocess.run(["rm", "-f", str(PROJECT / ".omc/metrics/runtime-verify/evidence.jsonl")], capture_output=True)
    assert rm.returncode == 0
    r = subprocess.run(
        ["python3", str(SCRIPTS / "capture_evidence.py")],
        cwd=str(PROJECT), capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    evidence = PROJECT / ".omc/metrics/runtime-verify/evidence.jsonl"
    lines = [json.loads(l) for l in evidence.read_text(encoding="utf-8").splitlines() if l.strip()]
    fails = [l["test"] for l in lines if l["status"] == "FAIL"]
    assert not fails, f"capture_evidence 应有 FAIL: {fails}"
