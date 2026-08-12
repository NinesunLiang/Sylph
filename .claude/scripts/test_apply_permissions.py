"""Regression: apply-permissions.py merge is a union, idempotent, preserves order.

index17 F1 落地：headless 权限契约可移植。测试 merge_allow 语义与脚本幂等。
"""
import json
import subprocess
import sys
from pathlib import Path

import apply_permissions as ap

CONTRACT = {
    "schema_version": "carros.permissions_contract.v1",
    "permissions": {"allow": ["Bash(python3 *)", "Bash(ls *)", "Bash(pwd)"]},
}


def test_merge_union_dedup_preserves_order():
    existing = ["Bash(git status)", "Bash(python3 *)"]  # python3 * already present
    merged = ap.merge_allow(existing, CONTRACT["permissions"]["allow"])
    assert merged == ["Bash(git status)", "Bash(python3 *)", "Bash(ls *)", "Bash(pwd)"]


def test_merge_empty_existing():
    merged = ap.merge_allow([], CONTRACT["permissions"]["allow"])
    assert merged == ["Bash(python3 *)", "Bash(ls *)", "Bash(pwd)"]


def test_script_idempotent_no_rewrite(tmp_path):
    contract = tmp_path / "contract.json"
    target = tmp_path / "target.json"
    contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
    target.write_text(json.dumps({"permissions": {"allow": ["Bash(git status)"]}, "keep": 1}),
                      encoding="utf-8")
    base = Path(__file__).resolve().parents[2]
    script = base / ".claude" / "scripts" / "apply_permissions.py"
    def run():
        return subprocess.run(
            [sys.executable, str(script), "--contract", str(contract), "--target", str(target)],
            capture_output=True, text=True,
        )
    r1 = run()
    assert r1.returncode == 0, r1.stderr
    assert "WROTE" in r1.stdout
    mtime1 = target.stat().st_mtime_ns
    r2 = run()
    assert r2.returncode == 0, r2.stderr
    assert "no changes" in r2.stdout  # idempotent: no second write
    assert target.stat().st_mtime_ns == mtime1
    # unknown fields preserved
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["keep"] == 1
    assert "Bash(python3 *)" in data["permissions"]["allow"]
    assert "Bash(git status)" in data["permissions"]["allow"]


def test_missing_contract_fails(tmp_path):
    missing = tmp_path / "nope.json"
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    base = Path(__file__).resolve().parents[2]
    script = base / ".claude" / "scripts" / "apply_permissions.py"
    r = subprocess.run(
        [sys.executable, str(script), "--contract", str(missing), "--target", str(target)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "missing file" in r.stderr
